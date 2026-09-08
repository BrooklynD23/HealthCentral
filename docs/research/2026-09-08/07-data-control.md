# Track 7 — Data science, user data control, and compliance

Research for the Asclexis (formerly HealthCentral) agentic-expansion effort.
Produced 2026-09-08 against [`00-brief.md`](00-brief.md). Read-only on source;
this file is the only write. Every repo claim below carries a `path:line` or
the command that produced it — per `docs/agentic/recurring-failures.md`, a
written decision is not proof, and a number without the command that produced
it is not a finding.

Model knowledge cutoff is May 2026; this research ran September 2026.
Regulatory and HCI-literature claims are backed by a fetched/searched source
with a URL in **Sources**; anything I could not verify against a source is
marked `[UNVERIFIED]`. I am not giving legal advice — §5 and the compliance
table summarize sourced regulatory positions and name where counsel review is
required, per the task's constraints.

---

## Summary

The central gap is exactly what the brief states, and it is worse in one
specific way once you look past the audit route: **`core/audit.py` writes
rows that already contain everything needed for a legible activity log — the
schema has indexed `profile_id`, `event_type`, `timestamp`, `entity_type`,
`entity_id` (`src/backend/models/audit.py:20-71`) — and in the entire backend
exactly one route reads them back (`api/profiles.py`, to count rows before
purging on profile deletion; `grep -rln "AuditLog" src/backend --include=*.py`
returns six files, none of them a listing endpoint).** Building `GET
/audit-log` is not a design problem, it is an afternoon of work sitting on
top of a schema that was built correctly the first time. That asymmetry — a
well-designed backend primitive with zero user-facing surface — repeats
across this whole track:

- **Provenance is real but inconsistent.** Document *entities* (visit-note
  diagnoses, medication changes, referrals) carry `char_start`/`char_end`/
  `quote` — exact-substring provenance (`modules/document_category.py:45-48`,
  `modules/extract_spans.py`). Lab *observations* — the numbers this app
  exists to explain — carry only `source_page` and `source_bbox_json`
  (`models/observation.py:91-92`). `extract_spans.with_span()` is never
  called from the lab-extraction path (`grep -rln "extract_spans" modules/`
  finds only `extract_imaging.py`, `extract_pathology.py`,
  `extract_visit_notes.py`). A displayed lab value traces to a page; a
  displayed diagnosis mention traces to an exact quote.
- **Deletion is cryptographically real at the profile level and structurally
  clean at the document level, but the answer cache has a genuine gap.**
  Document deletion cascades `Document → Chunk → Embedding` via `ondelete=
  "CASCADE"` (`models/chunk.py:46`, `models/embedding.py:43`), confirmed at
  the call site's own comment (`api/documents.py:1859`: "cascades to
  observations, chunks"). Embeddings live as blobs in the same SQLCipher
  database as everything else — there is no separate FAISS/Chroma index to
  go stale (`grep -rln "faiss\|chromadb" modules/ core/` — empty). But the
  agent's answer cache invalidates on `profile_version`, which is defined as
  `COUNT(Observation WHERE user_verified = True)` for the profile
  (`api/assistant.py:552-564`). **Deleting a document with no verified
  observations, an unverified observation, or a memory item does not change
  that count** — so a previously cached agent answer built from now-deleted
  content can still be served verbatim within the same process, after the
  deletion the user asked for. This is a specific, previously-unflagged leak
  vector, not the one the brief's premise about embeddings suggested (that
  one is already handled correctly by the FK cascade).
- **The RL feedback loop and the verification loop do not talk to each
  other.** `modules/rl_dataset.py` exports feedback-derived DPO/SFT/GRPO
  files correctly and redacts them correctly (RL-REDACT-001, strict policy,
  non-configurable). But `modules/normalize.py`'s `ANALYTE_SYNONYMS` is a
  static hardcoded dict, and `verify_observation()`
  (`api/observations.py:381-460`) never writes to it. The brief's framing —
  "verification corrections feed synonym maps" — describes a loop that does
  not exist in code yet; I'm correcting the premise rather than designing
  around it as if it were built.
- **`api/memory.py` has no audit logging at all.** No route in that file
  imports `core.audit` — create/list/get/update/delete of a `MemoryItem` (up
  to `settings.max_memory_items_per_profile` per profile) leave no trace,
  which also means a "what do you know about me" surface has one silent
  category to fix before it can claim completeness.
- **Observability infrastructure is further along than the audit surface.**
  Correlation-ID middleware, a bounded in-memory metrics ring buffer, and an
  auth-gated `/api/v1/monitoring/metrics` route already exist
  (`monitoring/correlation.py`, `monitoring/metrics.py`,
  `monitoring/health.py:33-65`) with per-agent-node timing wired in
  (`modules/agent/metrics.py`). What's missing is a frontend surface (there
  is none — `find src/frontend/src -iname "*diagnostic*"` is empty) and the
  correlation ID never actually reaching a log line or an audit row:
  `get_correlation_id()` is defined and read only inside its own middleware
  file (`grep -rln "get_correlation_id"` returns two files, both
  `monitoring/`) — it decorates the HTTP response header and nothing else.
- **Compliance conclusion, stated precisely rather than defensively:**
  HIPAA does not directly apply to Asclexis as built (no covered entity, no
  business associate relationship — §5), which is good news but not a
  compliance program by itself. The obligations that *do* bite are the FTC
  Health Breach Notification Rule (patient-facing PHR posture), FDA's CDS
  guidance's **patient-facing carve-out** (the Non-Device CDS exclusion is
  HCP-only — a fact the brief did not surface and that materially changes
  the FDA analysis), and state consumer-health-data laws (Washington MHMDA
  and its three successors) whose "regulated entity" definitions do not
  obviously exempt a vendor that never receives the data. None of this
  requires re-architecture; it requires disclosures, a few product
  boundaries kept intact, and counsel review before any hosted/server mode
  ships.

---

## 1. The user-facing data control plane

### 1.1 Audit log UX

**Where the rows live, verified.** `core/audit.py:26-32` and
`docs/compliance/hipaa-controls.md:57-60` agree and are internally
consistent: audit rows go into the **master database, which is not
encrypted** — it is the one place patient-linked data crosses the SQLCipher
boundary, which is exactly why `AUDIT-PHI-001`'s allowlist scrubbing exists
(`_scrub_action`/`_scrub_details`, `core/audit.py:170-189` and `115-167`).
Actions are drawn from a fixed 40-ish-entry `ALLOWED_ACTIONS` set; `details`
values must match `^[A-Za-z0-9_.:/\-]{1,64}$` — no spaces, so no filename,
analyte name, or free text can survive into a row. **They are PHI** in the
sense that matters for this task (linked to a profile, describing clinical
activity), even though their content is deliberately minimized to
ids/counts/enums.

**What a patient should see.** Not the raw rows — `event_type: "agent.act"`,
`details: {"tool_name": "compute_trend", "step_index": 2}` is not legible to
anyone without the codebase open next to it. Three tiers, all derivable from
the existing schema without a migration:

1. **Timeline view** (default): one line per session/interaction —
   "Sept 8, 2:14 PM — Asked about cholesterol trend — read 3 lab results
   from LabCorp_2026-03.pdf, cited 1 reference article" — built by grouping
   audit rows on a shared `run_id`/session marker (agent runs already have
   one: `entity_id=event.run_id`, `modules/agent/audit.py`) and translating
   `event_type` + `entity_type` into a small phrase table, the same pattern
   `modules/export.py`'s `QuestionPrompt` and `ExportModule` already use for
   turning structured data into patient-facing sentences.
2. **Expandable detail**: per-step breakdown for a session — which tool ran,
   which document/observation `entity_id`s were touched (already present
   verbatim in every row) — resolved against the *current* per-profile DB at
   render time (never stored redundantly) so a filename or analyte name can
   be shown without ever having been written to the unencrypted master DB.
   This is the right division of labor: master DB carries the fact "document
   X was read"; profile DB is asked "what is document X called" only when a
   human is looking, and only for their own profile.
3. **Raw/export**: a "download my activity log" CSV/JSON for the
   security-conscious minority, gated the same way `api/export.py`'s other
   downloads are (`audit_and_commit` + rate limiting already exist as
   patterns to copy).

**Retention.** `docs/compliance/data-privacy.md:56-64` currently states
"Indefinite" for audit logs with no user-facing control. That's defensible
for accountability but is itself worth a knob: a rolling window (e.g. 12
months, configurable, never shorter than what a still-open FDA/FTC complaint
window would need) with the same "log-and-continue" pruning pattern
`scripts/backup.py`'s `prune()` already implements for backups
(`api/backup.py:497-518`). Do not default to unlimited retention without a
UI-visible statement of that choice — right now there is no UI at all, so
the *user* has made no choice; the code has, silently.

**Deletion — the tension, addressed rather than dodged.** The repo has
already made this call once, correctly, and consistently: profile deletion
**purges** that profile's audit rows and writes one anonymized tombstone
(`docs/compliance/data-privacy.md:144-156`, `api/profiles.py:792-935`). The
stated rationale — retaining a full audit trail for a person who asked to be
erased "contradicts the guarantee this feature exists to provide" — is the
right call for a *local, patient-held, single-tenant* system, and it should
extend to **partial** deletion too, for the same reason: this is not a
multi-tenant SaaS where the audit trail protects other parties from the
deleting user, it protects the *same* person from disputing what the *agent*
did with their data. There's no adversary between the user and their own
audit log. Concretely: allow deleting a document to also let the user purge
that document's audit rows (its `entity_id` join key becomes an orphan
either way once the document is gone), keep the *count* of what was purged
(exactly the pattern `audit_rows_purged` already uses,
`core/audit.py:96`/`api/profiles.py:935`) so the trail says "N rows removed
with this document" rather than silently shrinking. What must **not** be
user-deletable: audit rows for *other* profiles (already structurally
impossible — every row is `profile_id`-scoped) and rows describing the
deletion event itself mid-transaction (same ordering discipline the profile
delete already uses: audit-then-commit before destructive action, not after,
`api/backup.py:447-461`'s "audit BEFORE raising" comment is the right
pattern to copy).

### 1.2 Data inventory — "what do you know about me"

No such surface exists (`src/frontend/src/pages/` has no page named
anything like it; `SettingsPage.tsx` and the two `components/settings/`
files are backup/deletion only). What it needs to enumerate, verified
against the actual models:

| Category | Source model | Provenance available today |
|---|---|---|
| Documents | `models/document.py` | filename, category, import date |
| Observations | `models/observation.py` | `doc_id`, `source_page`, `source_bbox_json`, `user_verified`, `extraction_confidence` — **no char span** |
| Document entities (diagnoses, meds, referrals) | `models/document_category.py` | `doc_id`, `char_start`/`char_end`/`quote`, `verified_by_user` |
| Memory items | `models/memory_item.py` | `key`, `value`, `category` — **no source at all**, user-authored, no audit trail (`api/memory.py`) |
| Care plan tasks | `models/care_plan_task.py` | `source_quote` (verbatim), acceptance is itself the verification |
| Interpretations | `models/interpretation.py` | linked 1:1 to an `Observation` |

The honest version of this page groups by document (most patients think "my
March labs," not "observation #482"), shows verification status as a first-
class badge (verified / unverified / edited-then-verified, using the
`original_value_json` diff that `verify_observation` already writes,
`api/observations.py:413-423`), and is explicit about the one row type with
no provenance at all: memory items are user-typed facts, not extracted from
anything, and the inventory should say so rather than implying they came
from a document.

### 1.3 Provenance and lineage

`modules/extract_spans.py` is a small, well-built primitive: `with_span()`
takes a regex match, trims whitespace off the span, asserts
`text[char_start:char_end] == quote` as an invariant, and — the detail worth
calling out — **caps confidence at 0.5 when the span can't be resolved**
(`extract_spans.py:39-41`), i.e., it treats "I can't show my work" as itself
a confidence penalty. That's the right instinct for a patient-facing
extraction system and it should be the model for observation provenance too,
not just document-entity provenance.

What's capturable today, and what isn't:

- **Fully capturable now, not wired up**: analyte/value/unit spans in the
  same lab-PDF text `extract_spans` already walks for other extractors.
  `models/observation.py` would need two nullable integer columns
  (`char_start`, `char_end`) added via a profile migration — small, additive,
  no backfill required (nullable + populated only for new extractions,
  exactly how `source_page`/`source_bbox_json` already behave for
  pre-existing rows).
- **Page-level today, and that's a reasonable floor**: the PDF page render
  endpoint already exists (`api/documents.py`'s page-image route, audited at
  `api/documents.py:1792-1800`), so "click the number, see the page it came
  from" is buildable today even without char spans — it just can't
  highlight the exact substring yet.
- **Chunk-level RAG lineage exists but serves a different purpose**:
  `models/chunk.py:58-60` carries `page_number`/`start_char`/`end_char` for
  retrieval citations (`[REFERENCE:N]`/`[YOUR_RESULTS:N]`), which is a
  separate provenance chain from "this displayed lab value came from this
  substring." Both matter; they should not be conflated into one UI
  affordance, because a chunk citation supports a *sentence the agent wrote*
  and an observation span supports *a number the extractor read*.

Full lineage — "trace a displayed number back through extraction to the
source PDF page" — is therefore two-thirds built. The missing third is the
char-span columns on `Observation` plus wiring `extract_spans.with_span()`
into whichever module currently produces `source_page`/`source_bbox_json`
for lab values (outside this track's read-only scope to name precisely, but
`grep -rn "source_page" modules/` will find it in one pass).

### 1.4 Export and portability

Verified inventory of what exists:

| Path | What it produces | Redacted? | Persists across restart? |
|---|---|---|---|
| `GET /export/csv`, `GET /export/json` | Observations only | No (structured data, not narrative — no redaction pass) | N/A, streamed |
| `POST /export/doctor-summary` | 1-2 page clinical summary, HTML/PDF | No | **No** — `_summary_store: dict` is an in-memory MVP store (`api/export.py:43`, docstring: "would be DB in production") |
| `POST /export/visit-prep` | Packet with meds/observations/questions/source docs | **Yes, strict** (`modules/export.py:637`) | No — `_packet_store` same pattern |
| `POST /export/fhir` | FHIR R4 Bundle | **Yes, strict**, verified-only (`modules/fhir_export.py:9-23`) | No — `_fhir_store` same pattern |
| `POST /backup/` + `GET /backup/{id}/download` | Full-fidelity zip: vault DB + sealed keys | **Deliberately not** (correct, per module docstring) | Yes — on disk |

Two real portability gaps, not cosmetic ones:

1. **Generated exports don't survive a restart.** A doctor summary or FHIR
   bundle a patient generated yesterday to bring to an appointment is gone
   if the app restarted in between — `_summary_store`/`_packet_store`/
   `_fhir_store` are bare in-process dicts by the code's own admission. This
   is the one place "MVP shortcut" and "data portability promise" collide;
   it should move to the profile DB (small table: `export_id`, `type`,
   `generated_at`, `payload_json` or a file path under the vault), which
   also gives the audit-log timeline something real to link to ("Exported
   FHIR bundle" already has an `entity_id` — right now it can't resolve to
   anything after a restart).
2. **FHIR is the only structured interoperability path, and it's
   export-only by design** (`modules/fhir_export.py:1-6`: "there is no
   import or write-back path"). That's the correct scope for *this* app
   (Track 4 covers MCP/interop more fully) but it means "portability" today
   means "leave," never "round-trip with another system," which is worth
   being explicit about in any data-control marketing copy — the FHIR
   export is a one-way door, and the `meta.tag` on the bundle
   (`FHIR_SOURCE = "urn:healthcentral:local-export"`,
   `fhir_export.py:34`) correctly signals that to a receiving system.

A genuine portability story for a local-first app needs one more thing
neither export nor backup currently provides: **a full-fidelity, *portable*
export that is not the encrypted backup format.** The backup zip is
restorable only by this app (it contains sealed SQLCipher keys); a user who
wants to hand their entire verified record to a new clinician or a different
tool needs the FHIR path to cover *everything* FHIR export already excludes
by design (documents' raw text, unverified-but-real extracted data flagged
as such rather than dropped). That's a scope decision for the product, not
a bug — flagging it as the actual shape of the remaining gap.

### 1.5 Deletion

**Profile-level (verified, and well-built):** `DELETE /profiles/{id}`
(`docs/compliance/data-privacy.md:110-178`) is a genuine crypto-erase —
sealed key deleted first as the commit point, vault swept, backups swept,
audit purged with tombstone, all before the master row is touched, ordered
so an interruption leaves a recoverable rather than corrupt state. This is
good work and the write-up is honest about its limits (no byte-overwrite
claim, SSD wear-leveling named explicitly).

**Document-level (verified clean):** `DELETE /documents/{id}`
(`api/documents.py:1812-1871`) explicitly deletes `DocumentEntity` and
`DocumentCategory` rows first (comment: SQLite FK enforcement is off, so
`ondelete="CASCADE"` alone won't reach them — this echoes recurring-failure
#7's "PRAGMA foreign_keys is inert" lesson, correctly applied here), deletes
the encrypted file off disk, then `profile_db.delete(document)` cascades
`Chunk`→`Embedding` structurally. **This closes the specific leak the brief
asked about**: a deleted document's embeddings do not survive in any
queryable form, because there is no out-of-band vector index — the blobs
live in the same table set that just got cascaded.

**Where re-indexing does NOT happen, verified**: the agent's semantic cache
(§ summary above; `modules/agent/cache.py` + `api/assistant.py:552-564`).
`profile_version` is `COUNT(verified observations)`. Walk the actual
sequence:

1. User asks a question; the agent retrieves chunks from Document A among
   others; the answer is cached under `CacheKey(question, profile_version=N)`.
2. User deletes Document A. It had zero verified observations (or none that
   changes the count). `profile_version` is still `N`.
3. User asks the same (normalized) question again within the same running
   process. `get_cached()` returns the old answer — built from content that
   the delete flow just told the user was gone.

This is in-process-only and dies on restart (`cache.py`'s own docstring:
"no cross-process/cross-restart persistence"), so it is not a durable leak,
but "the user asked to delete this and can, within the same session, be
shown an answer derived from it" is a real correctness gap against the
product's own stated invariant ("a stale cached explanation of changed data
is a correctness bug," `cache.py:3-6`) — it's just that the invariant's
enforcement mechanism (observation-count-based versioning) doesn't cover the
document/memory-item deletion case it wasn't designed for. The fix is
narrow: bump the version key on document deletion and memory-item deletion
too (a monotonic counter stored per profile, rather than deriving version
from a count that can coincidentally repeat, would also close a smaller
theoretical collision the COUNT-based scheme has — delete one verified
observation and verify a different one nets the same count).

**Granular deletion of one observation or one memory item**: structurally
trivial (both already have `DELETE` routes or would follow the same pattern
as document entities), but downstream effects are currently un-audited for
two of the three: `models/memory_item.py` deletion has no audit row at all
(§ summary), and neither deletion path touches `profile_version` (above).
Trends (`modules/analytics.py`) are computed live from a query at request
time — deleting an observation simply removes it from the next
`calculate_trend()` call, no caching to invalidate there. That part is
already correct by construction (deterministic, no LLM, no cache layer of
its own).

---

## 2. Personal health statistics done responsibly

This is the most evidence-driven section per the brief's instruction. Claims
below are sourced; repo claims carry paths as elsewhere.

### 2.1 What `modules/analytics.py` does today, precisely

Deterministic, no LLM (`analytics.py:1-9`, confirmed by reading the whole
module — it imports only `dataclasses`/`datetime`/`statistics`). Computes:
delta and delta-percent vs. the immediately prior value, a 5-point rolling
average, "stable" defined as `|delta%| < 5.0` (a fixed, unexplained
threshold — `STABLE_THRESHOLD_PERCENT = 5.0`, `analytics.py:70`), new-high/
new-low flags, and a templated `summary_text` that deliberately uses
non-alarming phrasing ("above the reference range **per report**" —
attributing the flag to the lab, not asserting a clinical judgment,
`analytics.py:173-179`). `TrendDataPoint`/`prepare_chart_data` hand recharts
a series plus a single reference-range band taken from the *latest* point
only (`analytics.py:251-253`) — if reference ranges changed between lab
draws (different lab, updated assay), the chart shows only the current
range, silently.

### 2.2 What the literature says is safe and what actually helps

- **Reference ranges are widely misunderstood on their own; graphical framing
  helps more than restating the number.** A 2024 systematic review of
  presentation-format studies (Ghanbari Jolfaei et al., *JMIR* companion —
  see PMC11347896) found the bulk of the evidence base is about graphical
  vs. numeric presentation, and flags that **whether high/low flags help at
  all, and whether categorical severity bands would help low-numeracy
  patients, remain open research questions** — i.e., this is not settled
  enough to justify a confident severity-labeling UI. [Sources: PMC11347896]
- **Numeracy and literacy independently predict whether a patient can even
  tell a result is out-of-range**, not just whether they understand *why*
  (Zikmund-Fisher et al., *JMIR* 2013, still the anchor citation this newer
  work builds on) — meaning a UI that assumes "if I show the reference range,
  the user will notice abnormal" is not a safe default; the abnormal/normal
  judgment needs to be rendered explicitly (a badge, a color, a line — not
  left to the reader to compute from two numbers). `analytics.py` already
  does this correctly (`is_abnormal`/`flag` are explicit fields, not
  inferred client-side) — worth preserving as the frontend evolves.
  [Source: doi.org/10.2196/jmir.3241]
- **Direct portal access to results does not reliably increase anxiety, but
  the evidence is thin and format-dependent** — a BC (Canada) patient survey
  on web-based lab access examined this directly; results were mixed enough
  that "faster access with a bad format" and "faster access with a good
  format" are not shown to have the same effect. [Source: PubMed 26242801]
  Separately, **cyberchondria (compulsive symptom-searching driven by
  anxiety) is empirically distinct from ordinary health anxiety but strongly
  correlated with it**, and is associated with measurably higher healthcare
  utilization — i.e., a bad presentation doesn't just produce a bad feeling,
  it produces more downstream contact with the health system. [Source:
  PMC13274916] This is the sharpest argument for the project's founding
  premise (avoid the anxiety spiral) being a *design constraint on
  visualization*, not just on the LLM's language.
- **Portal comprehension research keeps finding low numeracy/eHealth literacy
  in the population actually using these tools** (2025 JAMIA Open study:
  "moderate lab test comprehension," predominantly low numeracy/eHealth
  literacy sample) — the implication for Asclexis specifically is that the
  *median* user of a self-service lab-results tool should be assumed
  low-numeracy by default, not a power user. [Source: JAMIA Open ooaf009]

### 2.3 Concrete recommendations for `analytics.py`'s output, staying inside "deterministic, not diagnostic"

1. **Communicate uncertainty as a first-class field, not an omission.**
   `TrendSummary` has no field for "this trend is based on 2 points, both
   pending verification" — a rolling average of 2-5 values presented with
   the same visual weight as one built on a year of consistent testing is
   overclaiming precision the data doesn't have. Add
   `sample_size`/`data_confidence` (n≥3 unverified, n≥3 verified, n<3 =
   "not enough data for a trend" — the module should be willing to *say
   nothing* rather than compute a direction off two points) and surface it
   in `summary_text` the same neutral way flags already are.
2. **Missing-data honesty**: if the gap between two consecutive points is
   large relative to typical testing cadence for that analyte, say so
   ("last measured 14 months ago") rather than silently plotting a straight
   line implying continuous monitoring — this is squarely a "variability
   and honesty about gaps" ask from the brief and costs one more field on
   `TrendDataPoint`.
3. **Fix the single-reference-range chart bug** noted above
   (`prepare_chart_data` uses only the latest point's range) — when ranges
   differ across the series (lab change, assay update), either band each
   segment against its own range or flag the inconsistency explicitly;
   silently applying today's range to yesterday's value is a correctness
   issue, not just a presentation one.
4. **Do not add a severity/risk score.** The literature above is explicit
   that this is unresolved research territory even for clinician-designed
   systems; a home-grown severity heuristic on top of lab flags would be
   exactly the "clever fix" `CLAUDE.md` §1 warns against, and it would cross
   from "trend direction and rate-of-change" into something that reads as a
   clinical judgment — the app's own `interpret_safety.py` boundary exists
   to prevent this, and `analytics.py` should stay on its side of it by
   construction, not by relying on a downstream guard to catch it.
5. **Reuse the existing "per report" attribution pattern everywhere a flag
   is shown** (`analytics.py:173-179` already models this correctly) — it's
   a small phrasing choice with real evidentiary backing (the whole point of
   the abnormal/normal literature above is that patients conflate "flagged
   by the lab's threshold" with "clinically significant," and the module
   already avoids that conflation once; it should be the house style
   everywhere trends surface, including any future frontend components).

---

## 3. Extraction quality as a data-science artifact (HC-M06)

**Verified status**: `docs/agentic/roadmap.md:33` lists it as milestone 5,
not done; `docs/agentic/progress.md:55` still names it as next-priority work
as of the last progress entry. No golden-set file, eval-card script, or
metrics file exists in the repo today (`find . -iname "*golden*" -o -iname
"*eval_card*"` under `src/backend` turns up nothing named for this
milestone specifically — the only golden-set infrastructure that exists is
the agent's own 74-case eval gate, `modules/agent/eval/scorer.py`, which
evaluates *answers*, not *extraction*).

### 3.1 Design

**Golden set composition.** Synthetic lab-PDF documents, generated (not
scraped from real reports) at three difficulty tiers:

- **Tier 1 — clean single-panel reports** (CBC, CMP, lipid, thyroid): one
  panel per PDF, standard table layout, no OCR noise. Establishes the
  ceiling.
- **Tier 2 — realistic multi-panel, multi-page** reports with header/footer
  noise, varying lab letterhead layouts (mimic LabCorp/Quest/hospital-system
  visual styles without copying real templates), units mixed (mg/dL vs
  mmol/L) to exercise `modules/normalize.py`'s conversion table.
- **Tier 3 — adversarial**: scanned-and-rotated pages, low-contrast text,
  tables that break across a page boundary, an analyte name that's a
  synonym not yet in `ANALYTE_SYNONYMS`, a reference range given as text
  ("<5.0") rather than two numbers, a value flagged critical with no
  numeric reference range at all. This tier is what actually predicts
  production failure — Tier 1 alone would produce a misleadingly high
  headline number.

**Labels needed per fixture**, matching exactly what `modules/analytics.py`
and `api/observations.py` consume: `analyte_canonical`, `analyte_raw`,
`value`, `unit`, `ref_low`/`ref_high`, `flag`, `collected_at`, plus — once §1.3's
recommendation lands — `char_start`/`char_end` so the eval can also score
provenance accuracy, not just field accuracy.

**Metrics**, versioned (`SCHEMA_VERSION`-style constant, mirroring the
pattern `modules/rl_dataset.py:42` already uses for its own export schema):

| Metric | Definition | Why it's the right cut |
|---|---|---|
| Field-level precision/recall | Per analyte, per field (value/unit/date/ref-range) | A wrong unit with a right value is a *worse* failure than a missed row (silently wrong beats visibly missing) — aggregate precision/recall hides this |
| Per-analyte breakdown | Same metrics grouped by `analyte_canonical` | Extraction quality is not uniform — a CBC table is easier than a free-text pathology impression; a single blended number hides which panels are unsafe to trust |
| Date parsing accuracy | Exact match after normalization | Silent date errors are uniquely dangerous here: they corrupt `modules/analytics.py`'s trend ordering without producing any visibly wrong number |
| Confidence calibration | Expected Calibration Error (ECE) between `extraction_confidence` and empirical correctness, binned | `extract_spans.py` already caps confidence at 0.5 when provenance can't be resolved (`extract_spans.py:39-41`) — the eval card should verify that confidence *number* actually predicts correctness, not just that it exists |
| Provenance accuracy | `text[char_start:char_end] == quote` holding, and the span actually containing the claimed value | Directly tests the invariant `extract_spans.py`'s own docstring asserts |
| Drift | Same metrics re-run against the same frozen golden set on every model/prompt/regex change, diffed against the last recorded run | Catches silent regressions from unrelated changes (a redaction-pattern tweak that accidentally eats a decimal point, a normalize.py table edit that shifts a unit factor) |

**Confidence calibration, specifically**: ECE is the standard metric for
"does the model's stated confidence match its empirical accuracy," computed
by binning predictions by confidence and comparing bin accuracy to bin mean
confidence [Source: arxiv.org/pdf/2501.19047, "Understanding Model
Calibration"]. Given `modules/extract_spans.py` is **rule-based**
(`EXTRACTION_VERSION = "rule-v2"`, `extract_spans.py:13` — regex matches, not
model logits), "confidence" here is a heuristic score, not a softmax
probability, so ECE should be computed against *that* heuristic's bins, and
the eval card should say explicitly that this measures whether the
heuristic is honest, not whether an LLM is calibrated — a different claim
than the ECE literature usually supports, and worth stating precisely rather
than borrowing the term's authority without the underlying assumption.

**Synthetic corpus generation — safe and realistic.**

- **Synthea** (Apache-2.0, MITRE) generates fully synthetic patient
  histories including lab observations, with no real-PHI provenance —
  "roughly grouped by Encounter," FHIR/CSV/OMOP output
  [Source: github.com/synthetichealth/synthea, synthea.mitre.org/about].
  It does not natively produce *PDF* lab reports (its output is structured
  FHIR/CSV), so the practical pipeline is: **Synthea for clinically coherent
  values and reference ranges → a small local template-rendering step
  (reuse `modules/export.py`'s existing `render_html_summary` +
  WeasyPrint-to-PDF path, `export.py:290-381`, which already renders
  structured data to a styled PDF) → optional noise injection (rotation,
  JPEG-compress-then-rescan, synthetic OCR artifacts) for the Tier 3
  adversarial set.** This keeps the whole pipeline local, license-clean, and
  reuses code already in the repo rather than adding a new rendering
  dependency.
- **Do not use MIMIC-IV or any real de-identified clinical dataset** for
  this golden set — de-identified is not the same guarantee as synthetic,
  and using it would import a data-use-agreement obligation into a
  local-first, no-network-calls project for no benefit Synthea doesn't
  already provide for this specific use case (structurally correct labs,
  not narrative realism).
- **Faker/mimesis** (MIT-licensed) can supplement patient-facing metadata
  (names, DOB, MRNs) that Synthea doesn't emphasize, if the fixtures need
  those fields present so the redaction-gate tests (a natural adjacent use
  of the same golden set) have something to redact.

### 3.2 What "done" looks like

A `scripts/extraction_eval_card.py` (naming to match the existing
`scripts/agent_eval_gate.py` convention) that runs the current extractor
against the frozen fixture set, writes a versioned JSON report (metrics
table above, per-analyte breakdown, calibration bins), and — mirroring how
`scripts/agent_eval_gate.py` gates CI on the 74-case agent eval — fails CI
if precision/recall on any Tier 1/2 metric regresses past a stored baseline.
Tier 3 (adversarial) should be tracked but *not* gate CI at first — it's a
target to improve against, and gating on an intentionally hard tier before
the extractor is tuned for it would either block unrelated work or invite
lowering the bar, which is exactly the failure mode `CLAUDE.md` §3 forbids
("never... lower a test threshold... to make something pass").

---

## 4. The human-in-the-loop feedback loop as a data asset

### 4.1 What exists, verified

`modules/rl_dataset.py` groups `response_feedback` rows by normalized
prompt, pairs a negative turn's correction (priority 1) or a positive turn
in the same group (priority 2) into DPO pairs, falls back unpaired positives
to SFT, and always applies `RedactionEngine(policy_level="strict")` with no
configuration knob (`rl_dataset.py:19-23`, matching
`docs/compliance/hipaa-controls.md:159-162`'s description exactly — repo and
doc agree here). Export requires `confirmed=true`
(`docs/compliance/data-privacy.md:83,106`) and is audit-logged
(`api/feedback.py:40-42,240-241,390-391`).

### 4.2 Correcting the brief's premise

The brief frames this section as "verification corrections feed synonym
maps." **That loop does not exist in code.** `modules/normalize.py`'s
`ANALYTE_SYNONYMS` is a static dict built once at class-init time
(`normalize.py:250-254`); `verify_observation()`
(`api/observations.py:381-460`) edits `value`/`value_text`/`unit`/`ref_low`/
`ref_high`/`collected_at`/`notes` and tracks before/after in
`original_value_json`, but never touches `analyte_canonical` and never
writes to the synonym table. The two systems that *do* learn from human
correction are the RL dataset export (feeds an external fine-tuning
pipeline, not this app's own runtime) and nothing else. This matters for
scoping recommendation 4 below correctly — it's a proposal for new work, not
a description of an existing pipeline that merely needs measurement.

### 4.3 Measuring whether the loop improves accuracy for a given patient

Three separate things get conflated under "does feedback help," and they
need separate metrics:

1. **Does the *cache/answer* layer get measurably better?** Not really
   measurable per-patient today — there's no held-out eval set *per
   profile* (the 74-case agent eval gate is global, not personalized), and
   building one would mean asking a patient to label their own assistant's
   answers as a research task, which is a real UX cost for a health app.
   The honest answer: **within a single profile, "improvement" is better
   measured as *reduction in negative-feedback rate over time for
   semantically similar questions*** (cluster `prompt_snapshot`s by
   normalized-question similarity — the same normalization
   `modules/agent/cache.py:34-40` already uses — and track the ± ratio per
   cluster across sessions), not as an absolute accuracy score, because
   there is no ground truth to score against for open-ended explanation
   text.
2. **Does the extraction/verification loop get better?** This one *is*
   measurable, against the HC-M06 golden set (§3): if verification
   corrections eventually feed `ANALYTE_SYNONYMS` or a per-profile analyte
   alias table, precision/recall on the golden set (plus, more importantly,
   on that patient's *own* historical documents re-run through the updated
   normalizer) is a real before/after metric.
3. **Overfitting to one patient's idiosyncratic labs is the real risk in
   (2), not (1).** A synonym learned from one patient's odd lab-report
   phrasing ("Hgb A1c" vs. their specific lab's "HbA1c (DCCT)") is *supposed*
   to be patient-specific — that's a feature, not a bug, as long as it's
   scoped to that profile's alias table and never promoted to the global
   `ANALYTE_SYNONYMS` without review. The risk is the opposite direction:
   silently promoting one patient's correction into the shared static table
   used by every profile, which is exactly the kind of speculative,
   single-use-driven generalization `CLAUDE.md` §2 warns against. If this
   gets built, keep it **per-profile** (a new small table in the profile
   DB, not a write to the module-level `ANALYTE_SYNONYMS` dict), which also
   keeps it inside the per-profile-isolation invariant for free.

### 4.4 Is local LoRA fine-tuning worth it vs. better retrieval — a real opinion

**No, not as the next investment, and the evidence points the same
direction for this specific product shape.** A February 2025 study directly
comparing RAG to domain-specific fine-tuning found RAG ahead by a wide
margin on knowledge-grounding metrics (17% ROUGE, 13% BLEU, 36% Coverage
Score, averaged) [Source: doi.org/10.3390/make7010015], and a separate
study specifically on *less-popular* (long-tail) factual knowledge found
RAG's advantage grows for exactly that case [Source: arxiv.org/abs/2403.01432]
— which is the regime this app lives in: one patient's specific lab values,
by definition never in any base model's training data, are the definition
of long-tail. Fine-tuning cannot teach a model *this patient's* glucose
history; retrieval already does, correctly, today.

Where LoRA *could* help — and where it's a genuinely different claim than
"know this patient's data" — is teaching the model this **patient's
preferred communication style or vocabulary** (how much detail they want,
which units they think in) from repeated feedback. Even there, the small
per-profile dataset size this app would ever realistically produce (dozens
to low hundreds of feedback rows, not thousands) is exactly the regime
where parameter-efficient methods like LoRA are reported to *reduce*
overfitting risk relative to full fine-tuning, but do not eliminate it —
practical guidance for small-dataset LoRA still recommends low learning
rates and aggressive early stopping specifically because overfitting
remains a live risk under ~1,000 examples [Source:
dialzara.com/blog/fine-tuning-llms-with-small-data-guide]. Given Sprint 7
already scopes LoRA as a **deferred stretch**, that scoping is correct: it's
a plausible future personalization feature, not a substitute for retrieval
quality work, and the retrieval-quality work (better chunking, the
provenance gaps in §1.3, task-aware routing from Track 2) has a much higher
expected return per engineering-hour for a system whose core promise is
grounded citation, not stylistic adaptation. If this is picked up later, it
should be scoped as "adapt tone/vocabulary," evaluated against a held-out
set of that patient's own prior questions, and never framed internally or
to the user as "the model learned your medical history" — that's retrieval's
job and should stay retrieval's job for the groundedness guarantee to hold.

---

## 5. Compliance, currently

I am summarizing sourced regulatory positions, not providing legal advice.
Every applicability call below should be confirmed with counsel before it
is relied on in a release decision, especially before any hosted/server
mode ships (the compliance docs already scope "local and server" deployment
modes, `docs/compliance/README.md:38-42`, and several of these regimes
change posture materially between the two).

### 5.1 HIPAA — does it apply?

**Precisely: no, not to Asclexis as built, and the reasoning matters more
than the conclusion.** HIPAA's Privacy and Security Rules bind *covered
entities* (health plans, clearinghouses, providers who transmit health
information electronically in covered transactions) and their *business
associates*. A direct-to-consumer app that a patient uses to organize their
own uploaded documents — never operating on behalf of, or under contract
with, a covered entity — is neither. HHS's own guidance is direct on this:
once a covered entity has handed data to an app *at the individual's
direction*, "the information is no longer subject to the protections of the
HIPAA Rules," and a standalone PHR-type app "is generally not a covered
entity and is not a business associate" [Source: hhs.gov/hipaa — Access
Right, Health Apps & APIs; hipaajournal.com "Who Does HIPAA Apply To?"].
`docs/compliance/hipaa-controls.md` and `data-privacy.md` build a genuinely
strong *voluntary* HIPAA-aligned technical-safeguards posture (audit
controls, encryption at rest, access control) — that's good practice and
good marketing, but it is not a legal obligation triggered by this
architecture, and the docs should say so explicitly rather than implying
HIPAA coverage by mapping to its section numbers without the applicability
caveat.

**HIPAA Security Rule NPRM — status, verified current as of this research.**
The proposed rule (mandatory MFA, encryption, more granular access
controls) was published January 6, 2025, comment period closed March 7,
2025, and — this is the update the brief's May-2026 knowledge cutoff would
miss — **HHS moved it to the "Long-Term Actions" agenda with July 2027 now
the anticipated final-action date**, delayed from an earlier spring-2026
target [Source: hipaajournal.com "HIPAA Security Rule Update Postponed";
clarkhill.com "delayed until 2027"]. Not directly relevant to Asclexis
(§5's conclusion above) but relevant context: even entities that *are*
covered have more runway than the brief's cutoff would suggest.

### 5.2 FDA — CDS guidance and the non-device line

**The single most important correction to make to how this track's premise
was framed**: FDA finalized an updated CDS guidance January 6, 2026
(superseded January 29, 2026) [Source: covingtondigitalhealth-adjacent
search result, cov.com "5 Key Takeaways"], and its four Non-Device CDS
criteria (no analysis of images/IVD signals; display/analysis of existing
information only; support rather than replace judgment; the user can
independently review the basis) **apply only to software intended for use
by a healthcare professional**. Software that "supports or provides
recommendations to patients or caregivers" — which is exactly Asclexis's
audience — **meets the device definition and does not qualify for the
Non-Device CDS exclusion at all** [Source: search summary of the January
2026 guidance's patient-facing scope]. This is a meaningfully different
posture than "CDS guidance gives us an exemption if we don't diagnose."

**What actually keeps Asclexis out of device territory, more precisely:**
not the CDS non-device exclusion (unavailable to patient-facing software),
but the narrower and separate exclusion for software that only
**displays, stores, transfers, or formats** existing clinical results
without analysis or interpretation (21st Century Cures Act §3060, FD&C Act
520(o)(1)) — which is a clean fit for `api/export.py`'s CSV/JSON export and
the raw observation list, but is a **genuinely closer call** for
`modules/analytics.py`'s trend computation (rolling average, delta-percent,
new-high/low classification) and the LLM-explanation layer, both of which
are doing more than "display" in a way that could read as "analysis." The
project's actual safety posture — abstain rather than conclude, cite
sources, `interpret_safety.py`'s prohibited-pattern gate on diagnosis/dosing
language — is the right mitigant for this, but it is a mitigant supporting
an *enforcement-discretion* argument, not a clean statutory exclusion the
way the brief's framing assumed. **This needs FDA regulatory counsel
review before any claim is made publicly that the app "isn't a medical
device,"** specifically because of the patient-facing carve-out limitation
just described.

### 5.3 EU AI Act — timeline and classification

If Asclexis is ever offered in the EU, the classification question is
whether it lands in Annex III (use-based high-risk — the healthcare-adjacent
entries are narrow: safety components, eligibility for essential public
services, insurance risk-scoring; a patient-facing educational tool that
explicitly refuses diagnosis/treatment recommendations does not obviously
fit any Annex III health entry) versus the default limited-risk tier
(Article 50 transparency duties only — disclose that the user is
interacting with AI). `[UNVERIFIED, recommend counsel confirmation]`: I
could not fetch the primary EU text directly (network egress to the
detailed timeline article was blocked in this environment), but multiple
2026 secondary sources agree on the shape: **Article 50 transparency
obligations apply from August 2, 2026 and were not deferred; Annex III
(use-based) high-risk obligations were postponed from August 2026 to
December 2027; Annex I (product-regulated, e.g., AI as a medical-device
safety component) obligations were postponed from August 2027 to August
2028** [Source: search summary citing insideglobaltech.com/Inside Privacy,
May 2026]. **Practical read for this product**: if Asclexis stays
non-diagnostic and does not become a component of a regulated medical
device, Article 50 transparency (disclose AI involvement — something the
export footers and chat UI should already be doing, and per
`modules/export.py:347-350`'s footer already partially do: "This is an
AI-assisted summary... not medical advice") is the likely-applicable tier,
not the much heavier Annex III/I regime. Confirm with counsel before EU
release; this is a favorable read, not a certain one.

### 5.4 GDPR / CCPA — data-subject rights over local-only data

**GDPR**: the household exemption (Article 2(2)(c)) removes GDPR obligations
for processing "by a natural person in the course of a purely personal or
household activity" — which is arguably what a patient organizing their own
records on their own device *is*, from the patient's side. The harder
question is the **developer's** side: current legal commentary holds that
where a device's processing is genuinely local with **no access by the
manufacturer**, the user is the only plausible controller and the
manufacturer falls outside controllership — but this is an area "smart"/
edge-computing devices are actively pressuring, and is not settled black-
letter law [Source: sciencedirect.com S0267364922001054 abstract;
academic.oup.com/idpl device-manufacturers-as-controllers discussion]. For
Asclexis specifically: as long as **no health data or derived data ever
leaves the device to the developer** (true today per the constraints this
research operated under — no telemetry, Ollama localhost-only, redaction
before any egress), the strongest-available position is that the developer
is not a GDPR controller for the profile data at all, because it never
processes it. `[UNVERIFIED, recommend counsel confirmation before any EU
marketing claim]`.

**CCPA/CPRA**: applies to "businesses" meeting revenue/volume/data-sale
thresholds that **collect** California residents' personal information —
2026 commentary is explicit that mere *local* storage does not exempt an
app if the *developer's business* otherwise collects, processes, or syncs
that data in any way [Source: vucense.com "CCPA Compliance Checklist for
Self-Hosted Apps (2026)"]. Read precisely: Asclexis's architecture (data
never transmitted to the developer, no account/cloud sync as currently
built) means the developer is not "collecting" personal information in the
sense CCPA regulates *today* — but this conclusion is architecture-
dependent, not name-dependent: the day any sync, crash-report, or account
feature is added that sends *any* field back to the developer, this
analysis needs to be redone, because CCPA's threshold analysis is about the
business's practices, not the device's storage location.

### 5.5 State consumer-health-data laws — the ambiguous one

Washington's **My Health My Data Act** (2023, in force, first class action
filed February 2025) is the one regime in this table where the "we never
receive the data" architecture argument is **least clean**, and it's worth
being precise about why: MHMDA's "regulated entity" definition and its
"processing" definition are broader than GDPR's controller/processor
framework and broader than CCPA's collection-based trigger — it explicitly
reaches entities that "process" consumer health data, and its private right
of action (via the state Consumer Protection Act) means a plaintiff's
attorney gets to make the first argument about scope, not a regulator
exercising discretion [Source: goodwinlaw.com MHMDA alert;
wilmerhale.com "First Lawsuit Filed"]. Three successor states — Connecticut,
Nevada, New York — have passed similar laws; none currently carry a private
right of action [Source: calawyers.org "Not Just Washington (Or Health)"].
**Concrete obligation if any of these apply**: MHMDA requires a specific
consumer-health-data privacy policy (separate from a general privacy
policy), opt-in consent before collecting/sharing "consumer health data,"
and — the provision most worth building for regardless of the applicability
question — **a mechanism for the consumer to withdraw consent and have
their data deleted**, which Asclexis already has in a stronger form than
the statute requires (crypto-erase, §1.5). `[UNVERIFIED, recommend counsel
review of "processing" scope against this specific local-only architecture
before any WA/CT/NV/NY-directed marketing]` — but the deletion posture
already exceeds what any of these four laws would require, which is the
one piece of this section that doesn't need new engineering regardless of
how the applicability question resolves.

### 5.6 FTC Health Breach Notification Rule

Amended rule in effect since July 29, 2024, expanded specifically to reach
health-app developers who are not HIPAA-covered — a "vendor of personal
health records" is defined by what the product *is* (draws information
from multiple sources, managed by/for the individual) more than by whether
the vendor ever receives the data [Source: alston.com; venable.com "Final
Changes to Health Breach Notification"]. Asclexis — multi-document-source,
patient-managed — plausibly fits the *product* definition of a PHR even
though the vendor architecture never receives the underlying data. What
that means concretely: **if this app or its infrastructure (not the
patient's own device) ever experiences unauthorized access to health data
it does hold** — which today would only be true for optional cloud sync,
crash reporting, or hosted/server mode, none of which are default per the
constraints — HBNR's breach-notification triggers could apply to that
component. Today, with zero developer-side data at rest, there's nothing to
breach in the sense the rule regulates; this is worth stating in
`docs/compliance/data-privacy.md` explicitly rather than leaving HBNR
unaddressed, because it's the one federal regime a truly local-only PHR
product plausibly needs to name and dismiss on the record, not just satisfy
by architecture.

---

## 6. Observability without telemetry

### 6.1 What already exists, verified

- **Correlation IDs**: `monitoring/correlation.py` — ASGI middleware, reads
  or generates a UUID4 per request, stores it in a `contextvars.ContextVar`,
  echoes it on the response as `X-Correlation-ID`. **It is not wired into
  anything downstream**: `grep -rln "get_correlation_id"` finds it used only
  inside its own middleware module — not in `logging`'s formatters/filters,
  not in `core/audit.py`'s `create_audit_log`. It decorates the HTTP
  response and nothing else today.
- **Metrics**: `monitoring/metrics.py`'s `MetricsCollector` — thread-safe,
  bounded ring buffer (`deque(maxlen=10000)`), route-template-keyed (avoids
  UUID-cardinality blowup by design), computes p50/p95/p99/error-rate/RPS.
  Exposed at auth-gated `GET /api/v1/monitoring/metrics`
  (`monitoring/health.py:33-65`), gated behind `settings.metrics_enabled`.
  **In-memory only — resets on every restart** (`data-privacy.md:34,63`
  confirms this is the documented, intentional retention posture: "In-memory
  (session) | Cleared on restart").
- **Per-agent-step timing**: `modules/agent/metrics.py` feeds the same
  collector under `agent.<node>` keys — plan/act/reflect/draft/guard timing
  is already measurable via the same endpoint, no separate system.
- **No frontend surface at all**: `find src/frontend/src -iname
  "*diagnostic*"` is empty; nothing in `src/frontend/src/pages/` consumes
  `/api/v1/monitoring/metrics`.

### 6.2 What a genuinely local diagnostics story needs

1. **Wire the correlation ID into logs and audit rows** — the cheapest,
   highest-leverage fix here. A `logging.Filter` that reads
   `get_correlation_id()` and attaches it to every log record (standard
   pattern, a dozen lines), plus adding a nullable `correlation_id` column to
   `AuditLog` (small profile-migration-adjacent — this one's in the master
   chain — addition, matches the existing `entity_id` join-key pattern)
   turns "what did the agent do in this one request" from a manual
   `run_id`-grep exercise into a single filter.
2. **A local-only "Diagnostics" settings panel**, third alongside
   `BackupCard`/`DangerZone`, reading the existing `/monitoring/metrics`
   endpoint: current p95 latency per route, error rate, uptime — all data
   that already exists and already never leaves the device. This is close
   to a pure frontend task against an endpoint that's already built and
   already auth-gated correctly.
3. **Persist metrics snapshots locally**, since the in-memory-only posture
   is a real gap for "did this get slower after the last update" — a
   periodic (e.g., hourly) snapshot of `MetricsCollector.get_summary()`
   appended to a small local SQLite table or JSONL file under the app-data
   directory (not the encrypted vault — this is operational, not clinical,
   data, matching the existing Tier 3 classification in
   `data-privacy.md:29-36`) gives cross-restart trend without adding any
   network dependency or changing the retention-Tier classification the
   compliance docs already establish.
4. **Opt-in, user-initiated, redacted bug reports** — the one place this
   section has to be honest about a real tension: **no telemetry means no
   aggregate quality signal**, full stop. The best available substitute for
   a local-first app is not simulated telemetry, it's making the *manual*
   report path as low-friction and as safe as possible: a "Report a
   problem" action that bundles (a) the current correlation ID, (b) the
   last N log lines *for that correlation ID only* (not the whole log), (c)
   app version and hardware tier, (d) an optional user-typed description —
   all four passed through `modules/redaction.py` at strict policy before
   the bundle is even shown to the user for review (never auto-sent — this
   app has no server to send it to by default; "share" means the user
   copies/exports the redacted bundle themselves, the same trust model
   `api/export.py`'s other redacted exports already use). This directly
   reuses `RedactionEngine` and the strict-policy pattern already proven out
   in `modules/rl_dataset.py` and `modules/fhir_export.py` — no new privacy
   primitive, just a new consumer of the existing one.
5. **The honest limit, stated rather than engineered around**: without
   telemetry, there is no way to know in aggregate whether extraction
   quality or agent groundedness is drifting *across the user base* — only
   within one profile, and only for whatever that one user notices and
   reports. The HC-M06 golden set (§3) is the actual substitute for that
   missing aggregate signal: it can't tell you how *this patient's*
   documents are extracting, but it's the only local, no-telemetry way to
   catch a regression *before* it reaches any patient's documents at all,
   which is a different and complementary kind of coverage, not a
   replacement for per-user visibility.

---

## Data control plane — spec table

| Surface | What the user sees | Backend needed | PHI risk | Effort |
|---|---|---|---|---|
| Audit timeline | Plain-language per-session activity feed, expandable to per-step detail | New `GET /audit-log` route + phrase-table translator; resolve entity names against profile DB at render time only | Low — rows already PHI-minimized (AUDIT-PHI-001); risk is in the *translator* re-joining ids to names, must stay per-request, never cached to master DB | S (schema and rows already exist; route + UI only) |
| Audit export | Downloadable CSV/JSON of the timeline | Reuse `audit_and_commit` + existing export auth/rate-limit patterns | Low, same as above | S |
| Data inventory ("what do you know about me") | Documents grouped view; observation/entity verification badges; explicit "user-authored, no source" label for memory items | New aggregation endpoint across `Document`/`Observation`/`DocumentEntity`/`MemoryItem`/`CarePlanTask` per profile | Low — read-only, per-profile-scoped, no new storage | M |
| Provenance / lineage viewer | Click a lab value → see PDF page (today) or exact highlighted substring (after §1.3) | Page-image route exists; char-span columns on `Observation` + `extract_spans` wiring for the new capability | Low — spans are extracted text already inside the encrypted vault; no new egress | M (page-level today = S; span-level = M, needs a profile migration) |
| Portable exports (durable) | "My past exports" list that survives restart | Move `_summary_store`/`_packet_store`/`_fhir_store` from in-process dicts to a profile-DB table | Medium — these are the *un*-encrypted-in-transit-by-design redacted exports; storing them adds a new at-rest artifact, should live in the encrypted vault, not master DB | M |
| Granular deletion (observation/memory item) | Delete button per row, with an audit-purge option | `MemoryItem` deletion needs an audit call added (currently none); both need to bump the answer-cache's version key | Medium — closing the cache-staleness gap in §1.5 is the real deliverable here, not the delete route itself (mostly exists) | S–M |
| Diagnostics panel | Local p95/error-rate/uptime; opt-in redacted bug-report bundler | Frontend only for metrics view; new redacted-bundle assembly (reuses `RedactionEngine`) for bug reports | Low — everything sourced is already local-only; the redaction step is the safety boundary and must not be bypassable | S (metrics view) / M (bug-report bundler) |

## Compliance table

| Regime | Applies? | Why | Concrete obligation | Confidence |
|---|---|---|---|---|
| HIPAA Privacy/Security Rules | **No** | No covered entity, no business-associate relationship; data received "at the individual's direction," per HHS guidance | None legally; voluntary alignment is good practice, current docs already do this well | High — directly sourced, HHS guidance is unambiguous on this pattern |
| HIPAA Security Rule NPRM (2025) | N/A (not final, and inapplicable regardless) | Proposed rule moved to HHS's Long-Term Actions agenda, ~July 2027 anticipated final action | None yet for anyone; not binding | Medium — timeline is a planning estimate per the source, could move again |
| FDA — device / CDS | **Ambiguous, needs counsel** | Non-Device CDS exclusion is HCP-only per Jan 2026 guidance and does not cover patient-facing software; the fallback "display only" exclusion is a closer fit for raw data views than for `analytics.py`'s trend computation or the LLM explanation layer | If pursued as non-device: keep strictly to display/format of existing results; document the enforcement-discretion argument; do not market as "not a medical device" without counsel sign-off | Medium-High on the CDS-exclusion-is-HCP-only fact (directly sourced); Medium on how Asclexis's specific features map, which needs counsel |
| EU AI Act | **Likely limited-risk (Article 50 transparency), not Annex III high-risk** | Non-diagnostic, no Annex III health entry obviously fits (not a safety component, not essential-services eligibility, not insurance scoring) | Disclose AI involvement to users (already partially done via export footers); confirm before any EU release | Low-Medium — could not fetch primary EU text directly in this session; based on secondary-source consensus |
| GDPR | **Likely not, for the developer** | No processing of personal data by the developer under the current no-egress architecture; user's own local use plausibly falls under the household exemption from the user's side | None currently; re-evaluate immediately if any sync/telemetry/account feature is added | Medium — legally reasoned position, not a bright-line rule; this is an actively contested area for edge-computing devices generally |
| CCPA/CPRA | **Likely not, today** | No "collection" by the business under a strictly local, no-account architecture | None currently; re-evaluate the moment any field is transmitted to the developer for any reason (crash reports, sync, support) | Medium — architecture-contingent, not name-contingent |
| Washington MHMDA (+ CT/NV/NY successors) | **Ambiguous, least clean of the group — needs counsel** | Broader "processing" definition than GDPR/CCPA; WA carries a private right of action already exercised once | If applicable: dedicated consumer-health-data privacy policy, opt-in consent for any collection/sharing, consumer deletion right — already exceeded by the existing crypto-erase | Low-Medium — genuinely open question given the statute's breadth; flagged, not resolved |
| FTC Health Breach Notification Rule | **Plausibly, in shape, but nothing to trigger it today** | Product fits the multi-source, patient-managed PHR definition even though the vendor never holds the data | Name and address HBNR explicitly in `data-privacy.md`; re-evaluate the moment any hosted component holds health data | Medium |

## Recommendations

| Change | Integration point | Impact | Effort | Risk | Legal review needed? |
|---|---|---|---|---|---|
| Build `GET /audit-log` (paginated, filterable by date/event_type/entity_type) + phrase-table translator | New route beside existing `api/*.py` routers; reuses `AuditLog` schema as-is | High — closes the brief's named central gap directly | S | Low — read-only, per-profile scoped by existing session auth | No |
| Fix answer-cache staleness on document/memory-item deletion (bump `profile_version` on those deletes, or move to a monotonic per-profile counter) | `api/assistant.py:552-564`, `modules/agent/cache.py`, `api/documents.py` delete route, `api/memory.py` delete route | High — closes a real, verified correctness/leak gap this research found, not a hypothetical one | S | Low — additive invalidation, cannot make caching *more* stale | No |
| Add audit logging to `api/memory.py`'s five routes | `api/memory.py` — currently imports no `core.audit` at all | Medium — closes the one silent category in any future data-inventory/audit-timeline surface | S | Low — same pattern as every other route in the codebase | No |
| Add `char_start`/`char_end` to `Observation`, wire `extract_spans.with_span()` into lab extraction | New profile migration; whichever module sets `source_page` today (`grep -rn source_page modules/`) | Medium — completes the provenance story from page-level to exact-substring for the numbers the app exists to explain | M | Low — additive nullable columns, no backfill required | No |
| Move `_summary_store`/`_packet_store`/`_fhir_store` from in-process dicts to profile-DB-backed storage | `api/export.py:43-49` | Medium — makes "generated exports" actually durable, closes a real portability gap | M | Low-Medium — new at-rest artifact inside the already-encrypted vault, not a new trust boundary | No |
| Build the HC-M06 extraction eval card (synthetic Synthea-derived golden set, versioned metrics, CI gate on Tier 1/2 only) | New `scripts/extraction_eval_card.py`, mirrors `scripts/agent_eval_gate.py`'s pattern | High — closes a named, overdue flagship DS deliverable; also becomes the substitute for missing aggregate telemetry signal (§6.5) | L | Low — synthetic data only, reuses existing WeasyPrint rendering path | No |
| Wire `get_correlation_id()` into the logging formatter and into `create_audit_log` | `monitoring/correlation.py`, `core/audit.py`, `core/logging` config | Medium — turns per-request tracing from unused plumbing into an actual debugging tool | S | Low | No |
| Build a local Diagnostics settings panel on top of the existing `/monitoring/metrics` endpoint | Frontend `components/settings/`, third card beside `BackupCard`/`DangerZone` | Medium — user-visible transparency with zero new backend surface | S | Low | No |
| Add opt-in redacted bug-report bundler (correlation-scoped logs + version + user text, redacted, never auto-sent) | New settings action, reuses `RedactionEngine(policy_level="strict")` | Medium — the best available substitute for missing telemetry (§6) | M | Low-Medium — must never bypass the redaction step or default to any network send | No |
| Add `docs/compliance/` sections naming FTC HBNR and EU AI Act explicitly, with the applicability reasoning in §5 | `docs/compliance/data-privacy.md`, `hipaa-controls.md` | Medium — currently silent on two regimes that plausibly touch this product shape | S (doc-only) | Low | **Yes** — have counsel confirm the applicability reasoning before publishing it as the compliance team's position |
| Add MHMDA/state-consumer-health-data-law section to compliance docs | `docs/compliance/` new file or section | Medium — currently entirely unaddressed, and it's the regime with the least clean local-only-architecture defense | S (doc-only) | Low | **Yes** — genuinely ambiguous "processing" scope, and WA carries an active private right of action |
| Confirm FDA non-device posture given the patient-facing CDS carve-out, before any "not a medical device" claim | Product/marketing copy, `docs/compliance/` | High if wrong — this is the one item on this list with real regulatory exposure if asserted incorrectly | — | — | **Yes, before any public claim** |
| Do **not** build a home-grown severity/risk score on top of lab flags | `modules/analytics.py` | N/A — this is a "don't" | — | Would cross the diagnosis boundary `interpret_safety.py` exists to hold | N/A |
| Do **not** promote per-patient analyte-synonym corrections into the shared `ANALYTE_SYNONYMS` dict without review; if built, scope per-profile | `modules/normalize.py` | N/A — this is a "don't," scoped as guidance for if/when the correction-feedback loop described in §4.2 is actually built | — | Cross-profile generalization from one patient's idiosyncratic correction | N/A |

---

## Sources

Repo evidence is cited inline throughout with `path:line`; not repeated here.
External sources, by section:

**§2 — lab-result presentation / health-numeracy literature**
- [Enhancing Patient Understanding of Laboratory Test Results: Systematic Review of Presentation Formats (PMC11347896)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11347896/)
- [Numeracy and Literacy Independently Predict Patients' Ability to Identify Out-of-Range Test Results — JMIR 2013](https://doi.org/10.2196/jmir.3241)
- [The Effects of Web-Based Patient Access to Laboratory Results in British Columbia: comprehension and anxiety survey (PubMed 26242801)](https://pubmed.ncbi.nlm.nih.gov/26242801/)
- [Cyberchondria: Overlap with health anxiety and unique relations with impairment, quality of life, and service utilization (PMC13274916)](https://pmc.ncbi.nlm.nih.gov/articles/PMC13274916/)
- [Enhancing patient engagement and understanding via patient portals — JAMIA Open 2025 (ooaf009)](https://academic.oup.com/jamiaopen/article/8/2/ooaf009/8092606)

**§3 — extraction eval / synthetic data / calibration**
- [Synthea — MITRE, synthetic patient generator, Apache-2.0](https://synthea.mitre.org/about)
- [Synthea GitHub repository](https://github.com/synthetichealth/synthea)
- [Understanding Model Calibration — a visual introduction to ECE (arXiv 2501.19047)](https://arxiv.org/pdf/2501.19047)

**§4 — RAG vs. fine-tuning, LoRA overfitting**
- [Investigating the Performance of RAG and Domain-Specific Fine-Tuning (MDPI, doi.org/10.3390/make7010015)](https://doi.org/10.3390/make7010015)
- [Fine Tuning vs. Retrieval Augmented Generation for Less Popular Knowledge (arXiv 2403.01432)](https://arxiv.org/abs/2403.01432)
- [Fine-tuning LLMs with small data — practical overfitting guidance](https://dialzara.com/blog/fine-tuning-llms-with-small-data-guide)

**§5 — compliance**
- [HHS — The Access Right, Health Apps, and APIs](https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/access-right-health-apps-apis/index.html)
- [Who Does HIPAA Apply To? — HIPAA Journal, 2026](https://www.hipaajournal.com/who-does-hipaa-apply-to/)
- [HIPAA Security Rule Update Postponed — HIPAA Journal](https://www.hipaajournal.com/hipaa-security-rule-update-postponed/)
- [HIPAA Security Rule Update Delayed Until 2027 — Clark Hill](https://www.clarkhill.com/news-events/news/hipaa-security-rule-update-delayed-until-2027/)
- [Federal Register — HIPAA Security Rule NPRM, Jan 6, 2025](https://www.federalregister.gov/documents/2025/01/06/2024-30983/hipaa-security-rule-to-strengthen-the-cybersecurity-of-electronic-protected-health-information)
- [5 Key Takeaways from FDA's Revised CDS Software Guidance — Covington & Burling](https://www.cov.com/en/news-and-insights/insights/2026/01/5-key-takeaways-from-fdas-revised-clinical-decision-support-cds-software-guidance)
- [FDA Clinical Decision Support Software: Device vs Non-Device Guide](https://meddeviceguide.com/blog/fda-clinical-decision-support-cds-guide)
- [FDA — Clinical Decision Support Software guidance documents](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software)
- [EU AI Act Update: Timeline Relief, Targeted Simplification, and New Prohibitions — Inside Global Tech](https://www.insideglobaltech.com/2026/05/28/eu-ai-act-update-timeline-relief-targeted-simplification-and-new-prohibitions/)
- [EU AI Act explained: what healthcare organisations need to know — Tandem Health](https://tandemhealth.ai/resources/knowledge/eu-ai-act-explained-what-healthcare-organisations-need-to-know)
- [EU AI Act for Medical Devices: Healthcare Deadlines, 2026 and 2028](https://www.healthseed.vc/insights/vital-signs-ai-healthcare-august-2026)
- [Device manufacturers as controllers — expanding GDPR controllership (ScienceDirect S0267364922001054)](https://www.sciencedirect.com/science/article/abs/pii/S0267364922001054)
- [Who is responsible for data processing in smart homes? — household exemption analysis, Oxford IDPL](https://academic.oup.com/idpl/article/10/4/279/5900395)
- [CCPA Compliance Checklist for Self-Hosted Apps (2026)](https://vucense.com/privacy-sovereignty/law-policy/ccpa-compliance-checklist-for-self-hosted-apps-2026/)
- [Washington's My Health My Data Act Comes Into Force — Goodwin](https://www.goodwinlaw.com/en/insights/publications/2024/03/alerts-technology-hltc-my-health-my-data-act-mhmda)
- [First Lawsuit Filed Under Washington's My Health My Data Act — WilmerHale](https://www.wilmerhale.com/en/insights/blogs/wilmerhale-privacy-and-cybersecurity-law/20250220-first-lawsuit-filed-under-washingtons-my-health-my-data-act)
- [The Washington My Health My Data Act: Not Just Washington (Or Health) — California Lawyers Association](https://calawyers.org/privacy-law/the-washington-my-health-my-data-act-not-just-washington-or-health/)
- [FTC Issues Final Rule to Expand Scope of the Health Breach Notification Rule — Covington Digital Health](https://www.covingtondigitalhealth.com/2024/05/ftc-issues-final-rule-to-expand-scope-of-the-health-breach-notification-rule/)
- [FTC's Updated Health Breach Notification Rule Now in Effect — Alston & Bird](https://www.alston.com/en/insights/publications/2024/08/ftc-updated-health-breach-notification-rule)
