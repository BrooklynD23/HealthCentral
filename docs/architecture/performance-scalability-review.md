# Performance & Scalability Review

**Last Updated:** 2026-07-27
**Owner:** Project Lead
**Refresh Trigger:** A hot path changes, or any limit below is hit in practice

Part of the [architecture diagram set](README.md).

An honest assessment of where this system's performance stands and what breaks
first as data grows. It is deliberately not a marketing page: the items below
are real, several were already known and admitted in PR #17's report, and two
were found while writing this review.

## The frame: what "scale" means here

HealthCentral is a **local-first, single-user desktop application**. There is no
multi-tenancy, no concurrent request load, and no horizontal scaling story —
and none of those are missing features. The meaningful scaling axis is
**one person's record growing over years**: hundreds of documents, thousands of
observations, tens of thousands of text chunks.

Judging this codebase by server-application standards would produce a list of
"problems" that are correct engineering choices here. The questions that
actually matter are:

1. What degrades as one profile's record grows?
2. What grows without bound within a single session?
3. Where does the local-first constraint genuinely cap us, and where is it just
   an excuse?

---

## Findings, worst first

### 1. Search rebuilds its FTS index on every query — `modules/search.py`

**Status: known, admitted in PR #17, unchanged.**

`search_records` constructs its SQLite FTS5 index per query rather than
maintaining it. Cost is O(corpus) per keystroke-triggered search rather than
O(log n).

- At 50 documents: imperceptible.
- At 5,000 documents / ~50k chunks: this is the first thing a user will call
  "the app got slow", and it will feel worst on the feature that should feel
  fastest.

**Fix direction:** maintain the FTS table as a real table in the profile DB
with triggers on insert/update/delete, populated by a one-time backfill
migration. This stays entirely inside the encrypted vault, so it costs nothing
in privacy terms. Deferred because it needs a profile migration and a
correctness story for rebuilds after restore — not because it is hard.

### 2. In-memory stores with no TTL — visit-prep packets, doctor summaries, FHIR exports

**Status: known, admitted in PR #17, unchanged.**

Generated packets are held in process-local dicts keyed by an export id, with
no expiry and no eviction. In a long-running desktop session, generating many
exports grows the process heap monotonically until restart.

The volumes are small (a packet is text), so this is a slow leak rather than an
acute one — but it is unbounded, and "the app gets heavier the longer you use
it" is a real user-visible property.

**Fix direction:** a bounded LRU with a TTL, or spill to the vault's `docs/`
directory with the existing document encryption. The second option also
survives a restart, which is what users would expect of a generated packet they
haven't downloaded yet.

### 3. Timeline is a derived read-model with no materialization — `modules/timeline.py`

**Status: deliberate, with a threshold worth naming.**

The timeline recomputes from `observations`, `document_category`,
`document_entity` and `medications` on every request. This was the right call:
a materialized `timeline_event` table would need invalidation on every write to
four tables, and staleness bugs in a health timeline are worse than latency.

The threshold to watch is roughly **a few thousand events**, where the
multi-table aggregate plus Python-side merge starts to be noticeable on a cold
cache. Materialize only when a real measurement says so — the derived model is
simpler and cannot go stale.

### 4. LLM inference occupies the worker {#llm-inference}

**Status: inherent to the architecture, correctly chosen.**

`llama.cpp` runs in-process and is CPU-bound, so a generation holds the asyncio
worker. On a single-user desktop this is invisible: there is one user, and they
are waiting for that answer anyway.

It is worth stating explicitly because it is the property that would have to
change first if this ever became multi-user — and it should not, because moving
inference off-device would break the local-first guarantee that is the
product's entire premise. This is a genuine, deliberate cap.

The `OllamaProvider` path partially sidesteps it (Ollama is a separate
localhost process), which is a reasonable escape hatch for users on stronger
hardware.

### 5. Per-profile SQLCipher: unlock cost is real and intentional

Every profile unlock runs PBKDF2 at **600,000 iterations** (OWASP minimum) to
derive the key that unseals the DEK. That is a deliberate ~0.3–1 s cost — it is
the thing making an offline brute-force expensive.

Two consequences worth knowing:

- **Profile creation now runs two derivations** (password seal + recovery seal,
  SEC-RECOV-001), so creation is roughly twice the cost it was. The client
  timeout is already generous (180 s); no change needed, but it is why creation
  feels slower than login.
- **Recovery attempts are rate-limited for this reason** (5 per 15 minutes), not
  because a 160-bit code is guessable. An unbounded `/recover` endpoint would be
  a local CPU-exhaustion primitive.

Runtime query cost on an open vault is ordinary SQLite plus a page-level cipher
— fine at this scale.

### 6. Embedding and RAG retrieval

Chunk embeddings are computed on ingest and stored per profile. Retrieval is a
similarity scan rather than an ANN index, which is correct at these volumes
(thousands of chunks, not millions) and avoids a heavyweight vector-store
dependency in a local-first app.

**Caveat to be honest about:** the one persistently failing test in the suite is
`test_api_rag_index_002b`, an embedding-similarity assertion that needs a real
embedding model to run. It is an environment gap, not a product bug, and the
0.7 threshold is deliberately not lowered to make it pass — but it does mean
embedding quality is less regression-covered than the rest of the pipeline.

### 7. Document extraction is the slowest single operation

OCR on a scanned PDF dominates every other cost in the system by orders of
magnitude. It is already handled correctly: OCR-unavailable degrades to a
`pending_ocr` status rather than a 500, and extraction is a one-time cost per
document rather than a per-read cost.

No action. Noted so it does not get "optimised" ahead of the items above.

### 8. Audit rows accumulate in the master DB

The 2026-07 expansion of audit coverage to GET routes increased row volume
substantially — every timeline view, search, and document read writes a row.
There is no rotation or retention policy.

Since AUDIT-PHI-001 these rows are minimized (ids, counts, enums only), so the
growth is cheap per row and no longer a privacy concern — but it is still
unbounded, in the one database that is not encrypted. Profile deletion purges a
profile's rows; nothing else does.

**Fix direction:** an age-based retention policy is a compliance decision, not
an engineering one — it needs an owner call on how long an audit trail must be
kept.

---

## Summary table

| # | Finding | Severity | Bounded by | Action |
|---|---|---|---|---|
| 1 | FTS index rebuilt per query | **High** at scale | document count | Maintain a real FTS table |
| 2 | TTL-less in-memory export stores | Medium | session length | LRU + TTL, or spill to vault |
| 3 | Timeline not materialized | Low | event count | Measure before changing |
| 4 | In-process blocking inference | Inherent | — | Accept; it is the local-first trade |
| 5 | PBKDF2 unlock cost | By design | — | Accept; rate-limit recovery (done) |
| 6 | Similarity scan retrieval | Low | chunk count | Fine at this scale |
| 7 | OCR cost | Inherent | — | Already degrades gracefully |
| 8 | Unbounded audit rows | Low | usage over time | Needs a retention decision |

## What this system does *not* need

Stated explicitly so nobody adds them: horizontal scaling, a caching tier, a
message queue, connection pooling beyond SQLAlchemy's defaults, a vector
database, or an observability backend. Each would add operational surface to an
application whose defining property is that it runs entirely on one machine
with no network.
