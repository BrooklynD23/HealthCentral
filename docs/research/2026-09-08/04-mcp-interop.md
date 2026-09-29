# Track 4 — Model Context Protocol & Health-Data Interoperability

Researched 2026-09-08. Knowledge cutoff May 2026; anything about the world after
that carries a fetched URL or is marked `[UNVERIFIED]`, per the brief
([`00-brief.md`](00-brief.md) §4). Repo claims carry a `file.py:line`. This
document is read-only research — no source under `src/backend/` was modified.

## Summary

MCP moved fast in the four months since cutoff: the spec has gone through two
more revisions (2025-11-25, then 2026-07-28), the second of which is a genuine
architectural break — stateless core, mid-call "Multi Round-Trip Requests"
replacing server-initiated elicitation/sampling, and formal OAuth-Resource-Server
authorization hardening. None of that changes the shape of Asclexis's 8 read-only
agent tools (`src/backend/modules/agent/tools/`) — they are already typed,
validated-before-execution, and profile-scoped, which is most of the work an MCP
tool definition needs. What's missing is the boundary around them: today they
are only reachable from the in-process agent graph
(`src/backend/modules/agent/graph.py`), never from outside the FastAPI process.
Exposing them over MCP is a new **egress path over PHI**, full stop, even when
the client is local and user-owned — this document argues that concretely rather
than asserting it, then gives a specific, narrow default.

The interoperability research lands on a similarly narrow, honest conclusion:
FHIR R4 is correctly what `modules/fhir_export.py` already emits (R5 has "seen
limited adoption... not adopted by major EHR vendors" and R6 is still in normative
ballot — [Health Samurai, 2026](https://www.health-samurai.io/articles/fhir-r4-vs-fhir-r5-choosing-the-right-version-for-your-implementation)).
Pulling a patient's *own* records with zero cloud intermediary is possible in one
narrow, standards-track lane (SMART Health Links, resolved client-side, handed to
the FHIR bundle importer the app already has) and not realistically possible in
the broad lane most people mean when they ask this question (a desktop app OAuth
handshake straight into a hospital's live Epic instance) — that lane is gated by
institutional sponsorship, not cryptography. Every open-source FHIR MCP server
surveyed assumes the FHIR-access problem is already solved; none of them solve
*getting* access, only *querying* it once you have it.

Recommendations (§7) are deliberately small: a gated, opt-in MCP HTTP surface
mounted inside the existing FastAPI app and reusing its existing auth/vault
dependencies rather than a parallel stdio process; a scoped personal-access-token
model instead of OAuth (the wrong-shaped tool for a single-user desktop app); and
an explicit *non-recommendation* to build direct EHR OAuth this cycle, with the
regulatory/institutional evidence for why.

---

## 1. Current MCP spec state (as of September 2026)

The full published revision history is **2024-11-05 → 2025-03-26 → 2025-06-18 →
2025-11-25 → 2026-07-28** (2026-07-28 is current/GA, confirmed via the official
blog and changelog; the release candidate for it was published 2026-05-21 and it
became the current version on its target date —
[MCP spec version timeline](https://hidekazu-konishi.com/entry/mcp_specification_version_timeline.html),
[2026-07-28 Specification blog post](https://blog.modelcontextprotocol.io/posts/2026-07-28/)).

**2025-03-26** (pre-cutoff, for anchoring): introduced **Streamable HTTP**,
replacing the original HTTP+SSE transport. stdio was unaffected.

**2025-06-18** (pre-cutoff, confirmed by search):
- JSON-RPC batching support was **removed**.
- **Structured tool output** added — tools can return a standardized,
  machine-parseable result shape, not just free text.
- MCP servers formally classified as **OAuth 2.1 Resource Servers**; clients
  must implement RFC 8707 Resource Indicators so a malicious server can't get an
  access token scoped beyond itself.
- **Elicitation** added: a server can ask the end user for more input mid-call.
- **Resource links** in tool-call results; a `title` field added alongside the
  programmatic `name` for display purposes.
- ([x-cmd overview](https://www.x-cmd.com/blog/250623/), [ForgeCode summary](https://forgecode.dev/blog/mcp-spec-updates/))

**2025-11-25** — post-cutoff. I could not reach the official changelog directly
(`modelcontextprotocol.io` is blocked by this session's egress proxy); everything
about this specific revision is `[UNVERIFIED]` beyond its existence as an
intermediate step in the version timeline above.

**2026-07-28** — post-cutoff, fetched directly from the MCP project's own blog
([Model Context Protocol Blog, 2026-07-28](https://blog.modelcontextprotocol.io/posts/2026-07-28/);
release-candidate announcement:
[2026-07-28 Release Candidate](https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/)).
This is a genuine architectural break, not an incremental update:

- **Stateless protocol core.** The `initialize`/`initialized` handshake and the
  `Mcp-Session-Id` header are **removed**. Every request self-describes its
  protocol version, client identity, and capabilities in `_meta`. An optional
  `server/discover` RPC replaces the old handshake for clients that want upfront
  capability discovery, but it's no longer required.
- **Header-based routing.** Method and tool names now travel in `Mcp-Method` and
  `Mcp-Name` HTTP headers so a gateway can route/authorize without parsing the
  JSON body.
- **Multi Round-Trip Requests (MRTR)** replace the old server-initiated
  `elicitation/create` / `sampling/createMessage` / `roots/list` calls that
  needed an open bidirectional stream. A tool can now return
  `resultType: "input_required"` with a set of `inputRequests` plus an opaque
  `requestState`; the client collects answers and **re-issues the original call**
  with `inputResponses`. This turns what used to be a persistent-connection
  pattern into ordinary request/response — friendlier to stateless HTTP gateways
  and load balancers, and (relevant here) friendlier to a desktop app that can't
  guarantee a long-lived socket to an external client.
- **Authorization hardening:** RFC 9207 issuer validation is now required before
  a client redeems an authorization code; a new `application_type` parameter is
  required during Dynamic Client Registration; client credentials are bound to
  the issuing authorization server; and **Dynamic Client Registration (DCR)
  itself is formally deprecated** in favor of **Client ID Metadata Documents
  (CIMD)** — a client publishes a JSON document at a URL instead of registering
  interactively.
- **Cacheable list responses.** `tools/list`, `prompts/list`, `resources/list`,
  and `resources/read` now carry `ttlMs`/`cacheScope` so a client can cache
  without re-querying every turn.
- **Extensions framework.** Tasks (long-running/async work), MCP Apps (UI
  surfaces), and Enterprise Managed Authorization (EMA) are formalized as
  official extensions rather than experimental add-ons.
- **Deprecations, with a 12-month minimum support window:** Roots, Sampling, and
  Logging as top-level primitives (superseded by MRTR and the Extensions
  framework), plus the legacy HTTP+SSE transport.
- SDK support: all four Tier-1 SDKs (TypeScript, Python, Go, C#) plus a beta Rust
  SDK reportedly support 2026-07-28 "immediately" per the blog post — this is the
  vendor's own claim; I did not independently verify Python SDK behavior against
  a live 2026-07-28 server, so treat ecosystem *maturity* (vs. bare
  spec-compliance) as `[UNVERIFIED]`.

**What did *not* change**, across every revision surveyed: the three-primitive
model (**tools** = model-invoked actions with arguments; **resources** =
addressable, listable/subscribable data a client attaches to context;
**prompts** = reusable prompt templates) is intact through 2026-07-28. stdio as a
transport shape (newline-delimited JSON-RPC over stdin/stdout, same-process-tree
trust boundary) is unaffected by the statelessness rewrite — MRTR and header
routing are protocol-layer concerns that apply over stdio too, but stdio still
carries no network-layer identity of its own, which matters for §2.2 below.

**Recommendation for this project specifically:** target **2025-06-18**, not
2026-07-28, for a first implementation. It already has everything Asclexis needs
(structured output, OAuth-Resource-Server framing for the *hypothetical* HTTP
case, elicitation if ever needed) and is a full year more battle-tested than a
spec that reached GA seven weeks before this research ran. `docs/agentic/mcp-tools.md`
rule 1 — "MCP servers are privileged code. Vet before adding; pin versions where
possible" — argues for the boring, widely-implemented revision over the bleeding
edge for anything that touches PHI.

**Sources for this section:**
[MCP spec version timeline](https://hidekazu-konishi.com/entry/mcp_specification_version_timeline.html) ·
[2025-06-18 changelog overview (x-cmd)](https://www.x-cmd.com/blog/250623/) ·
[MCP 2025-06-18 spec update summary (ForgeCode)](https://forgecode.dev/blog/mcp-spec-updates/) ·
[The 2026-07-28 Specification (official blog)](https://blog.modelcontextprotocol.io/posts/2026-07-28/) ·
[The 2026-07-28 MCP Specification Release Candidate](https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/) ·
[Beta SDKs for 2026-07-28](https://blog.modelcontextprotocol.io/posts/sdk-betas-2026-07-28/) ·
[Google Developers Blog — MCP stateless updates](https://developers.googleblog.com/scaling-ai-agent-infrastructure-with-the-mcp-stateless-updates/)

---

## 2. Asclexis as an MCP server

### 2.0 What exists to build on

The repo's 8 tools (`src/backend/modules/agent/tools/`) already satisfy most of
what an MCP tool definition needs, verified by reading every one:

| Tool | File | Reads | Verified-only? | Free-text sanitized? |
|---|---|---|---|---|
| `query_observations` | `query_observations.py` | Lab/vital observations, filterable by analyte | Yes — `Observation.user_verified == True` is baked into the query; output model pins `verified: Literal[True]` so an unverified row **cannot be represented** even by a bug downstream | N/A (numeric values, coded units) |
| `compute_trend` | `compute_trend.py` | Direction + points for one analyte over a window | Yes, same filter | N/A |
| `check_verification` | `check_verification.py` | Status only (`absent`/`unverified`/`verified`) by id or analyte | Returns **status, never the value** — this is the tool that lets the agent say "not yet verified" without leaking an unverified number | N/A |
| `lookup_reference` | `lookup_reference.py` | Curated reference ranges from the **master DB** (`BiomarkerKnowledge`) | Not PHI at all — this is the one tool that touches zero patient data | N/A |
| `retrieve_chunks` | `retrieve_chunks.py` | Verbatim document text, substring-matched, `Document.status == "verified"` only | Document-level, not row-level | **No** — returns raw `chunk.text` |
| `query_care_tasks` | `query_care_tasks.py` | Care-plan tasks, optional status filter, capped at 50 | Tasks are user-accepted by construction (no verification gate needed) | Yes — `title`/`source_quote` through `sanitize_untrusted_field` |
| `query_medication_changes` | `query_medication_changes.py` | Medication-change entities since a date, capped at 50 | Yes — `verified_by_user == True` only | Yes — `entity_value`/`quote` sanitized |
| `query_timeline` | `query_timeline.py` | Derived cross-type timeline (delegates to `modules/timeline.build_timeline`), capped at 50 | Per-event `verification_status` field carried through, not filtered | Yes — `title` sanitized |

Every tool emits exactly one `agent.act` audit event per call
(`emit_audit_event` from `modules/agent/audit.py`), carrying handles/counts, never
raw values — e.g. `query_observations` audits `observation_ids` and a `count`,
never the lab value itself. The registry (`registry.py`) asserts no write path
exists (invariant SG-6) and validates args against each tool's Pydantic
`InputModel` **before** `run()` is ever called (`base.py`, `registry.py`). This
is architecturally the right shape for an MCP tool: MCP's own JSON-Schema
`inputSchema` validation is exactly this same guarantee, restated in the wire
protocol. Wrapping these 8 for MCP is mostly an **adapter**, not new logic — the
guardrail work is already done.

### 2.1 Tools vs. resources

MCP resources are for content a client lists and reads by URI without needing
the model to reason about arguments — the client (or a human) picks a resource
off a list. Tools are for model-invoked, argument-bearing operations. All 8 of
Asclexis's tools take real filter arguments (`analyte`, `status_filter`,
`since_date`, `date_from`/`date_to`, `k`) that only make sense chosen by
reasoning about the question being asked — so **all 8 map to MCP tools first**,
not resources. That said, two of them are also legitimate **resource templates**
for a non-agentic client (e.g., a client that just wants to browse, not reason):

- `lookup_reference` → `asclexis://reference/{analyte}` — safe to expose this way
  since it's non-PHI curated content, and a resource template lets a dumb client
  (a note-taking app, a spreadsheet plugin) pull one analyte's reference range
  without needing an LLM in the loop at all.
- `query_observations` → `asclexis://profile/{profile_id}/observations/{analyte}`
  — a browsable per-analyte resource is a reasonable secondary surface, but it
  must inherit the exact same `user_verified == True` filter the tool has; do
  not build a second code path for this, template it over the same tool
  implementation.

The other 6 stay tool-only. `retrieve_chunks` in particular should **never**
become a resource — a resource-list-and-subscribe pattern implies "give me
everything," which is precisely the whole-vault-in-one-call shape this document
argues against in §2.4.

### 2.2 Transport: stdio vs. localhost HTTP

The repo is **not** a single packaged desktop binary — `AGENT.md` describes two
separate dev processes (`dev.ps1` runs the FastAPI backend and the Vite
frontend, "auto-selects free ports"), with auth as a JWT bearer session token
(`core/auth.py:133` `create_session_token`) issued at profile login and a
per-profile SQLCipher connection opened at that same moment
(`core/auth.py:361` `open_profile_database_on_login`) and torn down at logout
(`core/auth.py:405` `close_profile_database_on_logout`). Both facts point the
same direction:

**Recommendation: mount MCP as Streamable HTTP inside the existing FastAPI app**
(a new `api/mcp.py` router registered in `main.py`), not as a separate stdio
binary a client host launches. Reasons, concretely:

1. **Ports are dynamic.** A stdio-launched process that needs to talk to "the
   running backend" would have to rediscover a port that changes per run. An
   in-process router has no such problem — it *is* the backend.
2. **Auth infrastructure already exists and already fails closed correctly.**
   `core/auth.py:298` `_get_required_profile_connection` raises **HTTP 403**
   "Profile database not available. Please log in again." the moment the vault
   isn't open — this is exactly the "what happens when the vault is locked?"
   answer the brief asks for, and it's already implemented and presumably
   tested. An MCP router that reuses the `RequireAuth`/`ProfileDbSession`
   FastAPI dependencies (`core/auth.py:294`, `:339`) inherits this for free.
   A separate stdio process would have to reimplement vault-lock detection from
   scratch, and get it exactly as right.
3. **This repo has already been burned by not doing this.** `docs/agentic/recurring-failures.md`
   §1 records a restore endpoint that returned 400 for every request because its
   tests "called the handler as a plain function, and FastAPI's dependency graph
   never ran." The lesson generalizes directly: an MCP tool-dispatch handler
   **must** be a real mounted route using `Depends(require_auth)` /
   `ProfileDbSession`, and its own tests must go through HTTP
   (`tests/support/routes.py::route_client`, per `CLAUDE.md` §1), not construct
   a `ToolContext` by hand and call `registry.get(name).run()` directly — that
   would be the exact same bug class with a different route.
4. **stdio's own trust model doesn't fit "an agent client the patient points at
   their own data" as cleanly as it first sounds.** stdio's security boundary is
   "whatever can spawn this child process" — fine when the client and server
   are configured by the same person in the same config file (this is exactly
   how `.mcp.json` uses Serena today, `.mcp.json:1-13`). But the target user
   here is explicitly "the patient's own agent client," which is a **different
   process, possibly a different vendor's app** (Claude Desktop, some other MCP
   host) reaching into a running Asclexis instance it did not launch. That's an
   inter-process, not a parent-child, relationship — HTTP is the correct shape
   for that regardless of whether the parties happen to be on the same machine.

That said, "localhost HTTP" is **not** an inert trust boundary — this is the
concrete threat-model point the brief asks not to hand-wave. **CVE-2025-49596**
(MCP Inspector) is the proof: "the vulnerability allowed attackers to run
arbitrary code on the host machine running MCP Inspector, without being on the
same network" via **DNS rebinding** — a malicious webpage's origin resolves
first to a public IP, then (after the browser trusts it) to `127.0.0.1`, and the
browser still permits the fetch because the *origin* didn't change, reaching an
unauthenticated local MCP endpoint straight from a browser tab
([Oligo Security writeup](https://www.oligo.security/blog/critical-rce-vulnerability-in-anthropic-mcp-inspector-cve-2025-49596),
[Recorded Future disclosure](https://www.recordedfuture.com/blog/anthropic-mcp-inspector-cve-2025-49596)).
The fix pattern Anthropic shipped is exactly what Asclexis's `api/mcp.py` must
copy: bind loopback-only, and **validate the `Origin`/`Host` header** against an
allowlist rather than trusting "it's on localhost" as authentication. The pattern
recurred generically enough that a follow-on advisory (CVE-2026-11624, title:
"MCP DNS Rebinding Vulnerability — AI Agent Infrastructure at Risk" —
[threat-modeling.com](https://threat-modeling.com/cve-2026-11624-mcp-dns-rebinding/),
`[UNVERIFIED]` beyond the search snippet, could not fetch the advisory directly)
suggests this is a known-recurring class across MCP HTTP implementations, not a
one-off Inspector bug — treat Origin validation as mandatory, not optional
hardening.

### 2.3 Authorization: proving the client may read profile X, and the locked-vault case

The vault is SQLCipher-encrypted and profile-scoped by construction — there is
no ambient "logged in" state independent of which profile's DB was unlocked.
Two shapes were considered:

- **Full OAuth 2.1** (what 2025-06-18+ formally expects of an MCP *server*, and
  what the general-purpose open-source FHIR MCP servers surveyed in §5 all
  implement) is the right tool when the resource server and the authorization
  decision-maker are different parties across a network — a hospital's FHIR
  server authorizing a third-party app on the patient's behalf. That is **not**
  this shape: here, the resource server (Asclexis's backend) and the person
  deciding whether to grant access (the patient, sitting at the same keyboard)
  are the same party on the same machine. Building a real authorization-server
  flow (client registration, redirect URIs, consent screens) to mediate a
  decision that's actually "am I willing to paste a token into my own MCP
  client's config file" is exactly the kind of "abstraction for single-use code"
  `CLAUDE.md` §2 asks not to build.
- **A scoped personal-access-token model** — a new token type, distinct from the
  web-session JWT, minted from Settings (`mcp:read` scope, profile-bound,
  shown once, revocable, with mint/use/revoke each producing an audit event) —
  fits the actual trust boundary. This is the same shape GitHub/GitLab use for
  CLI and MCP-client credentials, and it costs far less than an OAuth server:
  one new token table, one new dependency alongside `RequireAuth`, no consent
  UI beyond "generate token" / "revoke token."

**Locked-vault behavior, concretely:** because the MCP router should reuse
`ProfileDbSession` (§2.2), the existing `_get_required_profile_connection`
403 (`core/auth.py:298`) fires automatically for any MCP tool call made while
the profile is locked or was never unlocked this run. The MCP tool-call result
should surface this as a structured, typed error (not a bare 403 the client has
to interpret), so the patient's agent client can render "the vault is locked —
open Asclexis and unlock profile X" rather than a generic failure. This is new
work (a small error-mapping layer), but the underlying lock-detection is free.

### 2.4 The threat model: does "redaction before egress" apply to a client the user themselves connected?

**Yes — and the fact that the user connected it themselves is not a reason to
skip redaction, it's a reason the *default* can afford to be permissive later,
never a reason the *mechanism* is optional.** Three independent arguments, not
one:

1. **"The user connected it" describes consent, not content-safety.** Consent
   answers "may this data leave the process at all" — the redaction boundary
   answers "what shape is the data in when it does." A patient who opts in to
   pointing their own agent at their own vault has not thereby verified that
   every document chunk in that vault is free of, say, another family member's
   name accidentally captured in a scanned document, or a provider's direct
   phone extension. `modules/redaction.py` exists precisely because that
   judgment is not something to ask a patient to make document-by-document —
   it's the same reason `modules/fhir_export.py` runs every free-text field
   through `RedactionEngine(policy_level="strict")` even though the *user
   themselves* clicked "export" and confirmed it (`fhir_export.py:1-20`,
   `api/export.py:1163` "All free-text content is redacted... before the
   bundle is stored"). The export feature already treats "the user asked for
   this" and "therefore no redaction is needed" as two different questions, and
   answers them differently. MCP should follow the same precedent it already
   set, not a weaker one.
2. **The client is a new, non-Asclexis-controlled prompt-injection surface.**
   `retrieve_chunks` returns literal OCR'd document text
   (`retrieve_chunks.py:465-518` — the tool's own docstring is explicit that
   this is unvetted substring-matched text, not a sanitized field). Today that
   text only ever reaches Asclexis's own draft/guard/groundedness pipeline
   (`modules/agent/guardrails/`), which was built and evaluated (74 golden
   cases, `injection_resistance` as a scored axis per `00-brief.md`) against
   exactly this kind of content. An external MCP client has none of those
   guardrails — a scanned document containing hostile instructional text
   (a known document-based prompt-injection pattern) would reach the patient's
   own external agent completely unfiltered if `retrieve_chunks` is exposed
   without the same sanitization the other 3 free-text tools already apply.
   This is precisely `docs/agentic/mcp-tools.md` rule 5 ("external output is
   untrusted input... never overrides system/developer/CLAUDE.md rules") run in
   reverse: the repo already treats content flowing *in* from external MCP
   tools as untrusted; content flowing *out* to an external MCP client through
   `retrieve_chunks` deserves the same suspicion, because the client is going
   to treat it as ground truth about the patient's own body.
3. **"Local" and "network call" are not synonyms for "safe."** §2.2 already
   showed a local, same-machine HTTP endpoint is reachable from a browser tab
   the user never intended to grant access, via DNS rebinding. If the MCP
   surface is on and unauthenticated-by-origin, "the user connected it
   themselves" was never true for that particular request — a page they merely
   *visited* connected it. The redaction/authz mechanism has to hold regardless
   of who the researcher believes is on the other end, because MCP itself
   cannot verify that belief.

**Default, concretely (my prior, defended): off by default; explicit
per-profile opt-in; audit every call.**

- **Off by default.** `docs/agentic/mcp-tools.md` rule 3 already sets this
  precedent for the repo's *dev*-tooling database MCP ("read-only by default...
  write access is a per-use human approval"); the product-facing case is higher
  stakes (real PHI vs. synthetic dev data) and should be at least as
  conservative. A brand-new PHI egress path defaulting to *on* is not
  defensible for a health app whose CLAUDE.md invariant #1 is local-first.
- **Explicit per-profile opt-in**, not a single global toggle — profiles are
  the repo's actual isolation unit (`CLAUDE.md` "Per-profile data isolation");
  a household running Asclexis for two people should be able to let one
  agent-curious adult opt in without silently exposing the other profile.
- **Audit every call**, reusing the existing `agent.act` audit-event shape
  (`modules/agent/audit.py`) rather than inventing a second audit path — every
  one of the 8 tools already emits one event per call with handles/counts; an
  MCP-originated call should carry an explicit `source: "mcp"` (or similar)
  field in `details` so a future audit UI (gap #7 in the brief) can show a
  patient "your own agent read your LDL trend 4 times this week" distinctly
  from "the in-app assistant did."

### 2.5 What MUST NOT be exposed

- **Nothing write-capable.** All 8 tools are already read-only by registry
  invariant (SG-6, `registry.py`); the MCP surface must not add a 9th
  capability beyond what these 8 already permit — no write, no delete, no
  document upload, no profile-management action, ever, regardless of how the
  general-purpose open-source FHIR MCP servers in §5 are designed (several of
  them are explicitly full-CRUD — that is the wrong shape here and must not be
  copied).
- **Nothing that returns the whole vault in one call.** Every one of the 8
  tools is already bounded (`limit`/`k` capped ≤ 100 or ≤ 10; the three
  record-navigation tools cap at `_MAX_ROWS = 50`) — this is a real, existing
  guard against single-call exfiltration, and the MCP adapter must not "helpfully"
  add a bulk/no-limit variant or a bundle-everything meta-tool. If a client
  wants a full FHIR export, the existing confirmed, redacted, audited
  `POST /api/export/fhir` flow (`api/export.py:1148` `generate_fhir_export`,
  requires `confirm=true`, strict-policy redaction, one audit event per
  generation) is the correct path for that — not a new MCP shortcut around it.
- **Nothing that bypasses the guard node.** The guard/groundedness/redaction
  gate (`modules/agent/guardrails/`) sits between tool output and the terminal
  answer *inside* the in-app assistant flow — MCP tool calls, by construction,
  skip that gate entirely, because the MCP client is composing the final answer
  itself, not Asclexis. That is unavoidable (it's the whole point of exposing
  tools externally) and is exactly why §2.4's redaction-at-the-tool-boundary
  argument matters: when the guard node isn't downstream, the tool's own output
  sanitization is the *only* remaining safety layer, so it cannot be weaker
  than what the in-app path already has. Concretely: `query_care_tasks`,
  `query_medication_changes`, and `query_timeline` already run their free-text
  fields through `sanitize_untrusted_field` before the draft node ever sees
  them (each file's docstring says so explicitly) — an MCP adapter gets this
  for free by calling the same `run()` method, and must never call a
  lower-level, unsanitized data-access path "for efficiency."
- **No medical-advice framing leaking into tool descriptions or MCP prompts.**
  The `interpret_safety` prohibition on diagnosis/dosing language applies to
  anything the product asserts, including MCP tool/resource descriptions and
  any bundled MCP "prompt" primitive — these should describe data shape only
  ("returns verified lab observations for this profile"), never suggest
  interpretation ("check if your results are concerning").

---

## 3. Asclexis as an MCP client

The honest answer, arrived at after actually looking for a counter-example: **very
little, and it should stay that way — the "no network calls in product code
paths" constraint prunes almost the entire useful MCP-client design space by
itself**, because the MCP servers worth consuming (GitHub, web search, ticketing,
most SaaS-shaped connectors) are inherently networked, and the ones that
genuinely aren't networked mostly don't need MCP's protocol indirection to be
useful to this specific product.

Working through the brief's own candidates:

- **A locally-run reference-knowledge server** (e.g., a fully offline
  RxNorm/LOINC terminology mirror, or a curated drug-interaction database
  exposed as an MCP server). This is the one theoretically-legitimate case: it
  could run with zero product-code network calls, exactly like Ollama's
  localhost-only carve-out (`core/llm/ollama_provider.py`, `.env` docs: "must
  stay localhost"). But it's marginal value here for two reasons. First,
  `modules/knowledge_lookup.py` + the master-DB `BiomarkerKnowledge` table
  (seeded by `scripts/seed_knowledge_base.py`) already solve the same problem
  with content the *project* curates and controls — swapping that for a
  third-party MCP server's output means that content is now someone else's,
  and per `docs/agentic/mcp-tools.md` rule 5 it must be treated as untrusted
  and routed through the exact same `faithfulness`/groundedness gates as
  document-derived content before it can appear in an answer — real design
  cost for a wrapper that replaces something already working. Second, and more
  simply: `CLAUDE.md` §2 ("no abstractions for single-use code... prefer
  extending an existing module") argues for extending `knowledge_lookup.py`
  with a local, offline terminology *file* import if broader coverage is ever
  needed, not standing up an MCP client/server pair to reach the same local
  disk.
- **A local FHIR server.** Only relevant if Asclexis itself ran one (it
  doesn't — it's a document-import target, not a FHIR server) or if the *user*
  runs one locally (e.g., a personal HAPI FHIR instance). The latter is a real
  but vanishingly rare setup for a patient-facing app's actual user base, and
  even then, the product already has a working, simpler path into that data:
  the user exports a `Bundle` from their own local FHIR server and feeds it to
  the existing `parse_fhir_bundle` (`modules/import_structured.py:338`) via the
  document-upload flow — no MCP client needed, because the transfer is already
  file-based and already local-first by construction.
- **A filesystem server scoped to the user's own documents folder.** The
  official reference `server-filesystem` (part of
  [`modelcontextprotocol/servers`](https://github.com/modelcontextprotocol/servers))
  is exactly this, and it's local, read-only-capable, and well-vetted. But it
  solves a problem Asclexis's existing upload UI already solves (the user picks
  a file from a folder) — adding MCP here would be indirection without a new
  capability, the same "no speculative flexibility" argument as above.

**Conclusion:** do not build an MCP client into the product this cycle. If a
genuine local-only need for third-party MCP content ever appears (a fully
offline terminology corpus is the most plausible future candidate), treat its
output exactly like `retrieve_chunks` output today — untrusted, sanitized, and
gated by the same guard node — rather than adding a second, parallel trust
tier.

---

## 4. Health-data interoperability — the real opportunity

### 4.1 FHIR R4/R5/R6, and what `modules/fhir_export.py` actually emits

`modules/fhir_export.py` is a pure, DB-free R4 mapper (confirmed by reading the
full 432-line file) with three hard invariants worth restating because they're
already exactly right:

1. **Unverified-data exclusion is re-checked at the export boundary**, not just
   trusted from the caller — `build_fhir_bundle` filters
   `obs.get("user_verified") is not True` and
   `ent.get("verified_by_user") is not True` itself (`fhir_export.py:301-330`),
   even though `api/export.py`'s `_fetch_*` helpers already pre-filter. This is
   defense in depth against exactly the SQL-three-valued-logic class of bug
   `docs/agentic/recurring-failures.md` §7 documents elsewhere in this repo
   (a `!=`/`NOT IN` on a nullable column silently keeping `NULL` rows) — the
   module doesn't trust a single filter site to get that right.
2. **Every free-text field is redacted** (`RedactionEngine(policy_level="strict")`)
   before it reaches the bundle — display name, analyte/unit text, medication
   name/instructions, condition text and quotes, document titles, care-task
   titles and quotes.
3. **No invented dates** — `_iso()` returns `None` rather than defaulting to
   "now," so a missing date is *omitted* from the FHIR resource, never
   fabricated.

Resources produced: `Patient` (synthetic id, no dedicated row), `Observation`
(from verified labs), `MedicationStatement`, `Condition` (explicitly framed with
`verificationStatus: "unconfirmed"` — "a record of what a document said, not a
medical determination," `fhir_export.py:216-218`), `DocumentReference`,
`Encounter` (visit-notes documents only), `CarePlan` (one, with an activity per
accepted task), `DiagnosticReport` (imaging/pathology docs with verified
findings). This is a solid, defensible R4 subset — R4 is the correct target:
"FHIR R4 is the most widely adopted release... US Core IG is built on R4, which
is required by regulations," while "R5... has seen limited adoption" and is "not
adopted by major EHR vendors," and R6's normative ballot only started in January
2026 with no EHR vendor support yet
([Health Samurai — FHIR R4 vs R5 vs R6](https://www.health-samurai.io/articles/fhir-r4-vs-fhir-r5-choosing-the-right-version-for-your-implementation),
[Nirmitee — FHIR R4 vs R5 vs R6 2026](https://nirmitee.io/blog/fhir-r4-vs-r5-vs-r6-developer-decision-framework-2026/)).
**No version migration is warranted here.**

Import is the mirror image and already exists:
`modules/import_structured.py:338` `parse_fhir_bundle` parses `Observation`,
`MedicationStatement`, and `Condition` resources from an uploaded `Bundle`
(stdlib JSON only, no `eval`, every free-text field length-capped at 2000 chars
against a hostile huge value, unparseable resources counted in `skipped` rather
than failing the whole import). Imported facts always land as
`user_verified=False` (`api/documents.py:735-750` region, `_run_structured_import_pipeline`)
— they re-enter the same human-verification queue as OCR'd data, which is the
right call: a FHIR bundle is still untrusted input (`docs/plans/2026-07-10-post-visit-record-intelligence-roadmap.md:106`
scoped this deliberately). Export-only, no write-back, no network calls
anywhere in either module — both are already exactly local-first-shaped.

### 4.2 SMART on FHIR, SMART Health Cards, and SMART Health Links

**SMART on FHIR** is the OAuth 2.0-based authorization layer nearly every
certified EHR implements — "supported by Epic, Oracle Health (Cerner),
Athenahealth, and virtually every certified EHR in the United States"
([search summary, corroborated across multiple 2026 sources](https://docs.imprivata.com/ipa/content/topics/implementation/epic_smartonfhir.html)).
SMART App Launch v2 adds **Backend Services Authorization** — a
`system/`-scoped, no-user-present flow using signed JWT client assertions, meant
for server-to-server bulk access, not an individual patient's own desktop app
([HL7 SMART App Launch v2.2.0 — Backend Services](https://hl7.org/fhir/smart-app-launch/backend-services.html)).

**SMART Health Cards (SHC)** are portable, cryptographically-verifiable records
(vaccination status, lab results) as a signed JWS payload, typically shared as a
QR code — think "verifiable credential for one specific clinical fact," not a
general record-access mechanism.

**SMART Health Links (SHL)** are the more relevant primitive for this track's
"killer question": a SHL is a shareable URL/QR that resolves to a **manifest**
pointing at one or more FHIR resources (or a `DocumentReference`), optionally
password-protected, with the decryption key carried **in the link itself** (a
JWE construction) rather than held by whoever hosts the manifest — "SMART Health
Links (SHL) are for flexible sharing of FHIR data, including patient-supplied
information, dynamic records, and authorization delegation"
([spec.smarthealth.cards](https://spec.smarthealth.cards/),
[SMART Health Links — Kill the Clipboard](http://smarthealthlinks.com/)). Both
specs are actively moving through HL7 balloting in 2026 — the "Kill the
Clipboard" working group updated the patient-shared-documents SHL spec on
2026-02-18 ([HackMD — Patient-Shared Health Documents via SMART Health Links](https://hackmd.io/@Jyncr3iQS1iJA09xcuh7QA/rkGeS5cIZe)),
and a formal HL7 FHIR IG proposal for SHC+SHL together is in progress
([HL7 Confluence — SMART Health Cards and Links FHIR IG Proposal](https://confluence.hl7.org/spaces/FHIR/pages/230557128/SMART+Health+Cards+and+Links+FHIR+IG+Proposal)).

**Why this matters for Asclexis specifically:** resolving a SHL is a client-side
operation — fetch the manifest, decrypt with the key from the link fragment,
land a plain FHIR `Bundle` — which is a small, well-specified, one-shot
operation, not an ongoing OAuth session or a standing integration. It is the one
realistic path that gets a patient their own records **without Asclexis
operating a cloud intermediary**, because the intermediary (if any) is whoever
the health system already uses to host the manifest — not a service this project
would need to run. This is not a zero-network path (§4.6 is explicit about
that), but it is the smallest, most bounded network surface available, and its
output (a FHIR `Bundle`) is a format `modules/import_structured.py` already
parses. This is the single most concrete, buildable interoperability win this
track found.

### 4.3 US regulatory: information blocking, USCDI, CMS

The 21st Century Cures Act's information-blocking rule requires that patients
(and their delegated apps) get electronic access to their EHI on request, absent
a specific exception; since October 2022 the scope is "all EHI," not just a
USCDI subset ([HIMSS — Cures Act Part Two](https://www.himss.org/resources/21st-century-cures-act-part-two-information-blocking-and-interoperability/)).
**Current baseline standard for 2026 is USCDI v3**, adopted as the certification
baseline effective January 1, 2026. USCDI v4 was proposed (targeting a 2028
requirement) in the HTI-2 proposed rule, but **the non-finalized USCDI-v4
provisions of HTI-2 were formally withdrawn**, effective 2025-12-29
([Federal Register — HTI-2 patient engagement withdrawal](https://www.federalregister.gov/documents/2025/12/29/2025-23890/health-data-technology-and-interoperability-patient-engagement-information-sharing-and-public-health)).
Practical read: **USCDI v3 is the operative regulatory floor through 2026**; v4
is not currently a binding near-term requirement. `[UNVERIFIED]` beyond what the
Federal Register notice and secondary summaries state — I did not independently
confirm every provision the withdrawal covers.

**CMS interoperability rules** (patient-access API, provider-directory API) sit
alongside ONC's certification rules and are the reason every certified EHR
already exposes a FHIR-based patient-access API at all — this is the regulatory
floor that makes §4.4/§4.6 even possible in principle.

### 4.4 Epic on FHIR / MyChart, Oracle Health (Cerner)

Both major EHR vendors support FHIR R4 patient-facing APIs as required by ONC
certification. Specifics that matter for a small, unaffiliated developer:

- **Epic** splits credentials into two flows — "MyChart credentials for
  patient-facing access and SMART on FHIR for provider-facing, which have
  different scopes and different data surfaces"
  ([Medblocks — Epic EHR Guide](https://medblocks.com/blog/epic-ehr-guide)).
  Self-service **sandbox** registration is genuinely open: "register your app on
  Epic on FHIR, where the system generates a production and a non-production
  client ID automatically" — no payment, no formal relationship required to
  build and test. **Production is the blocker**: "you cannot self-serve your
  way to production. Your app stays inert until a real Epic health-system
  customer switches it on inside their environment. No sponsor, no go-live"
  ([Nirmitee — How to Get Your App Into Epic (2026)](https://nirmitee.io/blog/how-to-get-your-app-into-epic/)).
  Epic's marketplace itself changed shape recently: App Orchard was retired in
  favor of **Showroom** (2024), with a paid "Connection Hub" listing tier
  (~$500/yr) whose review alone "usually runs 8 to 16 weeks."
- **Oracle Health (Cerner)** ended DSTU2 FHIR support in December 2025 — "any
  legacy Cerner integration still on DSTU2... is unsupported and needs migrating
  to R4," which further cements R4 as the correct, current target (§4.1). Oracle's
  marketplace has "fewer pre-built integrations" than Epic's but a broadly
  similar OAuth-gated model.

Net: **the technical API is open; the production activation is not.** A patient
at an Epic-affiliated hospital can already authenticate through *MyChart* itself
(that flow is designed for patients and works today, no developer relationship
needed) — but a *third-party app* reading that data on the patient's behalf, in
production, needs either an existing sponsoring relationship with that specific
health system or the health system to have already turned the app on. This is
the crux of §4.6.

### 4.5 Apple HealthKit and Android Health Connect as local import sources

**Apple HealthKit** has no server-side API at all — "the only way to read
HealthKit data is on-device," meaning any integration needs a mobile SDK running
on the phone itself; Apple's own on-device export is described as slow and
"easy to interrupt." There is no direct desktop-to-HealthKit channel — any
import path necessarily goes through an export file the user generates on their
phone and moves to the desktop themselves (already exactly the shape
`modules/import_structured.py`'s CSV path was built for).

**Android Health Connect** is more directly useful, and changed materially after
this model's cutoff: in **March 2025**, Health Connect added a **"Medical
Records (FHIR)"** mode — "Medical Records data is stored in the HL7 FHIR
format," covering "vaccines and immunizations, allergies and intolerances,
conditions and problem-list history, laboratory results, medications and
prescriptions" pulled from a linked EHR connection on the phone
([Android Developers — Medical Records data format](https://developer.android.com/health-and-fitness/health-connect/medical-records/data-format),
[Android Police — Health Connect medical records in Android 16](https://www.androidpolice.com/health-connect-medical-records-android-16/)).
Health Connect also supports scheduled encrypted-ZIP backups (daily/weekly/
monthly) to a cloud location of the user's choosing, though — per the search
summary — that specific mechanism is scheduled-export-only, not an ad hoc manual
export. **This is a genuinely useful, concrete fact for this project**: an
Android user's Health Connect medical-records export is *already FHIR R4-shaped*
by construction, meaning **no new parser is needed** — a file pulled off the
phone (by whatever means the user chooses) and fed into the existing upload flow
lands on the same `parse_fhir_bundle` path already used for any other FHIR
bundle. This is the second most concrete, low-effort interoperability win this
track found, after SHL resolution.

### 4.6 The killer question: can a patient pull their own records with no cloud intermediary?

**Two distinct lanes, evaluated honestly and separately:**

**Lane A — SMART Health Link / Health Connect FHIR export, resolved or moved by
the patient, fed into the existing importer.** Real, buildable, standards-track,
and small. The patient triggers it (scans/pastes a SHL they were handed after a
visit, or copies a file off their own phone) — this is explicit, one-shot, and
user-initiated, which is exactly the shape `CLAUDE.md`'s local-first invariant
already carves an exception for: "Any hosted service is either dev-time tooling
or an explicit, redacted, opt-in path — never a default." **Honesty check:**
resolving a SHL *is* an outbound HTTPS fetch from product code — the first one
this codebase would ever make in a non-Ollama, non-dev-tooling context. It must
be framed and reviewed as exactly that (§7 recommendation #6), not smuggled in
under "it's just parsing a file."

**Lane B — a desktop app OAuth handshake straight into a hospital's live Epic or
Cerner instance, general-purpose, for any patient at any affiliated hospital.**
Technically implementable (public client + PKCE, system-browser redirect per the
RFC 8252 native-app pattern SMART's own docs endorse) but **not a near-term win
for this project**, for institutional reasons, not cryptographic ones:

- Epic requires **per-developer app registration**, and separately, **per-health-
  system production activation** — "no sponsor, no go-live." A patient at an
  unaffiliated hospital cannot get a small indie app switched on for them; that
  requires a business relationship between the app's developer and that specific
  hospital system, which is out of scope for a local-first side project.
- This is a **per-health-system** cost, not a per-vendor one — even "just
  support Epic" doesn't transfer across two different Epic-run hospitals unless
  both have separately sponsored the app. A patient realistically has records
  scattered across 3-5+ distinct health-system relationships over a lifetime;
  Lane B doesn't scale down to an individual developer without becoming exactly
  the kind of cloud-intermediary aggregation business (1upHealth-shaped) this
  question is trying to avoid.
- Desktop OAuth needs a redirect URI — either a registered custom URI scheme
  (e.g. `asclexis://oauth/callback`, requiring OS-level registration; `AGENT.md`
  notes Windows is the native dev environment, which has its own scheme-
  registration mechanics) or a loopback-HTTP redirect. Both are implementable,
  but neither exists in the repo today, and both are meaningful new platform
  plumbing for a payoff that Epic's own activation gate makes largely moot
  without a sponsor.

**Conclusion:** the honest differentiator is Lane A (SHL / Health-Connect-FHIR,
patient-triggered, file/link-based, no standing OAuth relationship, works
identically regardless of which EHR the data originated from because the output
is always a plain FHIR `Bundle`), not Lane B (direct-to-EHR OAuth, which is
real but gated by a business relationship this project doesn't have and
shouldn't need). §7 recommends building the former and explicitly not building
the latter this cycle.

**Sources for §4.2-§4.6:**
[Censinet — SMART on FHIR OAuth 2.0 guide](https://censinet.com/perspectives/smart-on-fhir-oauth-2-0-implementation-guide) ·
[Imprivata — Epic SMART on FHIR patient access](https://docs.imprivata.com/ipa/content/topics/implementation/epic_smartonfhir.html) ·
[spec.smarthealth.cards](https://spec.smarthealth.cards/) ·
[smarthealthlinks.com](http://smarthealthlinks.com/) ·
[HL7 Confluence — SHC/SHL IG proposal](https://confluence.hl7.org/spaces/FHIR/pages/230557128/SMART+Health+Cards+and+Links+FHIR+IG+Proposal) ·
[HackMD — Patient-Shared Health Documents via SHL](https://hackmd.io/@Jyncr3iQS1iJA09xcuh7QA/rkGeS5cIZe) ·
[HIMSS — Cures Act Part Two](https://www.himss.org/resources/21st-century-cures-act-part-two-information-blocking-and-interoperability/) ·
[Federal Register — HTI-2 withdrawal, 2025-12-29](https://www.federalregister.gov/documents/2025/12/29/2025-23890/health-data-technology-and-interoperability-patient-engagement-information-sharing-and-public-health) ·
[Medblocks — Epic EHR Guide](https://medblocks.com/blog/epic-ehr-guide) ·
[Nirmitee — How to Get Your App Into Epic (2026)](https://nirmitee.io/blog/how-to-get-your-app-into-epic/) ·
[EHR Source — Epic vs Oracle Health 2026](https://www.ehrsource.com/compare/epic-vs-oracle-health/) ·
[Android Developers — Medical Records data format](https://developer.android.com/health-and-fitness/health-connect/medical-records/data-format) ·
[Android Police — Health Connect medical records, Android 16](https://www.androidpolice.com/health-connect-medical-records-android-16/) ·
[Sahha — HealthKit vs Health Connect](https://sahha.ai/blog/healthkit-vs-healthkit-connect/) ·
[Health Samurai — FHIR R4 vs R5 vs R6 (2026)](https://www.health-samurai.io/articles/fhir-r4-vs-fhir-r5-choosing-the-right-version-for-your-implementation) ·
[Nirmitee — FHIR R4 vs R5 vs R6 developer guide](https://nirmitee.io/blog/fhir-r4-vs-r5-vs-r6-developer-decision-framework-2026/) ·
[HL7 SMART App Launch v2.2.0 — Backend Services](https://hl7.org/fhir/smart-app-launch/backend-services.html)

---

## 5. Existing health MCP servers and agent tooling — survey

None of these should be adopted wholesale (several are write-capable, all
assume the FHIR-access problem is already solved), but they're worth surveying
so nothing here gets rebuilt from scratch, and because their design choices are
useful negative examples for §2.5.

| Project | License | What it does | Read/write | Deployment | Relevance |
|---|---|---|---|---|---|
| [`xSoVx/fhir-mcp`](https://github.com/xSoVx/fhir-mcp) | MIT (confirmed by direct fetch) | MCP server over FHIR servers + HL7 terminology services; capabilities/search/read/create/update + terminology lookup/expand/translate; "PHI protection, audit logging, token-efficient operations" | **Read + write** (create/update) | Works against HAPI FHIR, Firely, "other R4/R4B servers"; Docker for local dev | Closest architectural cousin, but its CRUD + `system/`-scope client-credentials model assumes you already operate/own the FHIR server — irrelevant to *getting* access, and its write path is exactly what §2.5 says Asclexis must not copy |
| [`the-momentum/fhir-mcp-server`](https://github.com/the-momentum/fhir-mcp-server) | MIT | Natural-language interface to FHIR; full CRUD on major resources; document ingestion (TXT/CSV/JSON/PDF) with vector-embedding semantic search via Pinecone; OAuth2 token management | **Read + write** | Built on FastMCP; "works with popular FHIR backends like Medplum out of the box" | Same shape as above — general-purpose, write-capable, cloud-embedding-dependent (Pinecone), the opposite of local-first |
| [`wso2/fhir-mcp-server`](https://github.com/wso2/fhir-mcp-server) | `[UNVERIFIED]` — not independently confirmed (WSO2's other OSS is typically Apache-2.0, not verified for this repo specifically) | "Expose any FHIR Server or API as an MCP Server" | `[UNVERIFIED]` | `[UNVERIFIED]` | Enterprise-integration-vendor entry; same "you already have a FHIR server" assumption |
| [`awslabs/mcp` → `healthlake-mcp-server`](https://awslabs.github.io/mcp/servers/healthlake-mcp-server) | Apache-2.0 (confirmed — whole `awslabs/mcp` repo is Apache-2.0) | 11 tools over **AWS HealthLake** specifically — FHIR search, patient-level operations, import/export jobs, "read-only operations," automatic datastore discovery | Read-only per the AWS blog framing | AWS-managed FHIR datastore only — inherently cloud, not local | Good design reference for a *read-only-by-construction* MCP-FHIR server, but architecturally the opposite of local-first (requires an AWS HealthLake datastore to exist at all) |
| Official [`modelcontextprotocol/servers`](https://github.com/modelcontextprotocol/servers) `server-filesystem` | MIT (project standard) | Generic local-filesystem read/list/write MCP server, scopable to a directory | Configurable read/write | Fully local, stdio | The only *directly* locally-runnable, well-vetted server surveyed — relevant to §3's filesystem-client discussion, not to the FHIR question |
| Anthropic **Claude for Healthcare** (announced 2026-01-12/15, JPM Healthcare Conference) | N/A — hosted product, not an OSS project | HIPAA-ready Claude tools/connectors for providers/payers/patients: CMS Coverage Database, ICD-10 lookup, National Provider Identifier registry, PubMed; prior-authorization and claims workflows named as flagship use cases | N/A | Cloud/hosted (Anthropic-run) | **Not applicable to this project's local-first constraint** — included for completeness since it's the most-cited "health + Claude" development in this window, but it is exactly the cloud-intermediary shape `CLAUDE.md` rules out for product code paths. `[reasonably corroborated — multiple independent secondary sources incl. TechCrunch; primary anthropic.com page not directly fetchable in this session]` |
| Academic: open MCP-FHIR agent framework (arXiv 2506.13800) | `[UNVERIFIED]` — could not fetch arxiv.org in this session (egress-blocked) | "Agent-based framework integrat[ing] LLMs with HL7 FHIR data via MCP for dynamic extraction and reasoning over EHRs" | `[UNVERIFIED]` | `[UNVERIFIED]` | Research-grade prior art; flagged for completeness, not vetted enough to inform a decision |

**Sources for §5:**
[xSoVx/fhir-mcp](https://github.com/xSoVx/fhir-mcp) ·
[the-momentum/fhir-mcp-server](https://github.com/the-momentum/fhir-mcp-server) ·
[wso2/fhir-mcp-server](https://github.com/wso2/fhir-mcp-server) ·
[AWS HealthLake MCP Server](https://awslabs.github.io/mcp/servers/healthlake-mcp-server) ·
[AWS blog — building healthcare AI agents with HealthLake MCP](https://aws.amazon.com/blogs/industries/building-healthcare-ai-agents-with-open-source-aws-healthlake-mcp-server/) ·
[modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) ·
[TechCrunch — Anthropic announces Claude for Healthcare, 2026-01-12](https://techcrunch.com/2026/01/12/anthropic-announces-claude-for-healthcare-following-openais-chatgpt-health-reveal/) ·
[FierceHealthcare — JPM26 Claude for Healthcare](https://www.fiercehealthcare.com/ai-and-machine-learning/jpm26-anthropic-launches-claude-healthcare-targeting-health-systems-payers) ·
[arXiv 2506.13800 — MCP-FHIR framework](https://arxiv.org/html/2506.13800v1) (unreachable this session; citation from search snippet only)

---

## 6. Proposed MCP server tool/resource manifest

Everything below is **read-only over the exact same 8 tools that already
exist** — this table adds an access surface, never a capability. Every row's
"default state" assumes the top-level, per-profile "Enable MCP server" setting
(§2.4) is itself **off** until the patient opts in; the last column describes
what happens for that tool once the profile-level switch is turned on.

| Name | Maps to (source) | Read-only? | PHI exposure | Default state once MCP is opted in |
|---|---|---|---|---|
| `query_observations` | `agent/tools/query_observations.py` (+ optional resource template `asclexis://profile/{id}/observations/{analyte}`) | Yes | **Medium** — structured lab values tied to an identifiable profile; verified-only | Enabled |
| `compute_trend` | `agent/tools/compute_trend.py` | Yes | **Medium** — derived numeric series, no narrative text | Enabled |
| `check_verification` | `agent/tools/check_verification.py` | Yes | **Low** — status/count only, the underlying value is never returned by design | Enabled |
| `lookup_reference` | `agent/tools/lookup_reference.py` (+ resource template `asclexis://reference/{analyte}`) | Yes | **None** — master-DB curated content, not patient data | Enabled (safe to ship first; this is the tool to pilot the whole surface with) |
| `retrieve_chunks` | `agent/tools/retrieve_chunks.py` | Yes | **High** — returns verbatim OCR'd document text; the one tool that is also an unfiltered document-based prompt-injection surface for the *external* client (§2.4 point 2) | **Off** even when the profile-level MCP switch is on — require a second, explicitly-labeled opt-in ("also let my agent read my document text") before this specific tool activates |
| `query_care_tasks` | `agent/tools/query_care_tasks.py` | Yes | **Medium** — sanitized extraction-derived free text (title, source quote) | Enabled |
| `query_medication_changes` | `agent/tools/query_medication_changes.py` | Yes | **Medium-High** — medication data is an especially sensitive category even sanitized | Enabled |
| `query_timeline` | `agent/tools/query_timeline.py` | Yes | **Medium, but broadest single-call yield of the 8** — an aggregate cross-type view (labs + meds + documents + tasks) in one call, even though each field is individually sanitized | Enabled, but subject to the per-connection call budget below |
| *(new, proposed)* `vault_status` | Not one of the 8 — a small new read: `{locked: bool, profile_id, profile_name}` | Yes | **None** | Always available once the MCP router is mounted, even before profile opt-in — lets an external client fail gracefully ("vault is locked") instead of guessing from a bare 403 |

**Cross-cutting controls, not per-tool:** (a) a per-MCP-connection call budget,
reusing the shape of `modules/agent/state.py`'s existing `MAX_STEPS = 5` rather
than inventing a second budget concept; (b) one `agent.act`-shaped audit event
per call with a `source: "mcp"` marker, through the existing
`emit_audit_event`; (c) `Origin`/`Host` header allowlisting on the HTTP
listener (§2.2); (d) the personal-access-token auth model (§2.3), never full
OAuth, never the web-session JWT reused directly for a third-party client.

---

## 7. Recommendations

| # | Change | Integration point | Impact | Effort | Risk | Compliance review needed? |
|---|---|---|---|---|---|---|
| 1 | Mount a gated MCP HTTP router (`api/mcp.py`) inside the existing FastAPI app, reusing `RequireAuth`/`ProfileDbSession`; wrap the 8 existing tools via a thin adapter, not new query logic | New `api/mcp.py`, new `modules/agent/mcp_adapter.py` wrapping `registry.py`; `main.py` router registration | Opens the product's first MCP surface (closes brief gap #6); the *only* new PHI egress path this cycle | Medium — mostly adapter + settings/audit wiring; tool logic is untouched | Medium — new egress path over PHI, even though local | **Yes** — same review track `HC-M22` (FHIR export) already went through; also touches `core/auth.py`, which `CLAUDE.md` requires asking-before-touching on |
| 2 | Scoped personal-access-token model (`mcp:read`, profile-bound, revocable, shown once) instead of a web-session JWT or an OAuth authorization server | `core/auth.py` (new token type — flagged auth/encryption, ask first), new `api/mcp_tokens.py` or extend `api/profiles.py` | Right-sized auth for "same person, same machine, different process" instead of over- or under-building | Medium | Medium — token leakage while the vault is unlocked = read access to that profile's MCP surface | Yes, bundle with #1 |
| 3 | `Origin`/`Host` header allowlist + loopback-only bind on the MCP listener | `api/mcp.py` middleware | Closes the CVE-2025-49596-class DNS-rebinding gap (§2.2) — a browser tab must not be able to reach this endpoint | Small | Low if done; **High if skipped** | Bundle with #1, don't split out |
| 4 | Per-connection call budget (reuse `MAX_STEPS`-shape) + `source: "mcp"` audit marker on every MCP-originated `agent.act` event | `modules/agent/state.py`, `modules/agent/audit.py` | Keeps MCP calls inside the one audit trail a future audit UI (gap #7) can show the patient, and bounds single-connection exfiltration volume | Small | Low | Bundle with #1 |
| 5 | Exclude `retrieve_chunks` from the default-enabled MCP tool set; require a second, separately-labeled opt-in | Settings flag + MCP router tool filter | Shrinks the single highest-PHI, highest-injection-risk tool's blast radius without blocking the other 7 | Small | Low | Bundle with #1 |
| 6 | Add a user-initiated **SMART Health Link resolver**, feeding its decrypted `Bundle` straight into the existing `parse_fhir_bundle` import path; also accept an Android **Health Connect FHIR medical-records** export file through the same path with no new parser | `modules/import_structured.py` (new: SHL manifest fetch + JWE decrypt, small and well-specified — not a new abstraction layer), `api/documents.py` | The actual "pull my own records with no cloud intermediary" win (§4.6 Lane A) | Medium — SHL resolution is a bounded, well-specified crypto/HTTP operation, not an integration platform | Low-Medium — **this is the first outbound network call from product code**; must be framed exactly as `CLAUDE.md`'s own carve-out language requires: "explicit, redacted, opt-in... never a default," one-shot, user-triggered only | **Yes** — first-ever product-code network call; needs explicit sign-off that it fits the local-first invariant's stated exception, not an implicit pass |
| 7 | **Do not** build direct Epic/Cerner OAuth-to-EHR this cycle (§4.6 Lane B) — record this as a documented decision, not a silent omission | New entry in `docs/plans/` or `docs/agentic/` decision log | Prevents opening a network code path for a flow that mostly can't reach production without an institutional sponsor anyway (8-16 week Epic listing review, "no sponsor, no go-live") | N/A — a decision, not code | N/A | N/A — document the reasoning so it isn't re-litigated without new facts (e.g., Asclexis actually landing a sponsoring health-system relationship) |
| 8 | Target **MCP spec revision 2025-06-18** for the first implementation, not 2026-07-28 | Whatever MCP SDK/library choice backs `api/mcp.py` | Avoids building against a spec that reached GA seven weeks before this research, whose SDK ecosystem maturity is `[UNVERIFIED]` | N/A (a version pin, not a feature) | Low | Bundle with #1 — pin the version explicitly in whatever dependency manifest is used, per `docs/agentic/mcp-tools.md` rule 1 |

---

## Sources

- [MCP spec version timeline — hidekazu-konishi.com](https://hidekazu-konishi.com/entry/mcp_specification_version_timeline.html)
- [MCP 2025-06-18 changelog overview — x-cmd blog](https://www.x-cmd.com/blog/250623/)
- [MCP 2025-06-18 spec update — ForgeCode](https://forgecode.dev/blog/mcp-spec-updates/)
- [The 2026-07-28 Specification — official MCP blog](https://blog.modelcontextprotocol.io/posts/2026-07-28/)
- [The 2026-07-28 MCP Specification Release Candidate — official MCP blog](https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/)
- [Beta SDKs for the 2026-07-28 MCP Spec — official MCP blog](https://blog.modelcontextprotocol.io/posts/sdk-betas-2026-07-28/)
- [Scaling AI Agent Infrastructure with the MCP Stateless updates — Google Developers Blog](https://developers.googleblog.com/scaling-ai-agent-infrastructure-with-the-mcp-stateless-updates/)
- [How AgentCore Gateway supports the MCP 2026-07-28 spec — AWS ML Blog](https://aws.amazon.com/blogs/machine-learning/how-agentcore-gateway-supports-the-mcp-2026-07-28-spec/)
- [Critical RCE in Anthropic MCP Inspector (CVE-2025-49596) — Oligo Security](https://www.oligo.security/blog/critical-rce-vulnerability-in-anthropic-mcp-inspector-cve-2025-49596)
- [Anthropic MCP Inspector CVE-2025-49596 disclosure — Recorded Future](https://www.recordedfuture.com/blog/anthropic-mcp-inspector-cve-2025-49596)
- [CVE-2026-11624: MCP DNS Rebinding — threat-modeling.com](https://threat-modeling.com/cve-2026-11624-mcp-dns-rebinding/) (snippet only; not independently fetched)
- [MCP Registry — official registry.modelcontextprotocol.io](https://registry.modelcontextprotocol.io/)
- [modelcontextprotocol/registry — GitHub](https://github.com/modelcontextprotocol/registry)
- [xSoVx/fhir-mcp — GitHub](https://github.com/xSoVx/fhir-mcp)
- [the-momentum/fhir-mcp-server — GitHub](https://github.com/the-momentum/fhir-mcp-server)
- [wso2/fhir-mcp-server — GitHub](https://github.com/wso2/fhir-mcp-server)
- [AWS HealthLake MCP Server](https://awslabs.github.io/mcp/servers/healthlake-mcp-server)
- [Building healthcare AI agents with AWS HealthLake MCP server — AWS blog](https://aws.amazon.com/blogs/industries/building-healthcare-ai-agents-with-open-source-aws-healthlake-mcp-server/)
- [modelcontextprotocol/servers — GitHub](https://github.com/modelcontextprotocol/servers)
- [arXiv 2506.13800 — open-source MCP-FHIR framework](https://arxiv.org/html/2506.13800v1) (unreachable this session; from search snippet)
- [TechCrunch — Anthropic announces Claude for Healthcare, 2026-01-12](https://techcrunch.com/2026/01/12/anthropic-announces-claude-for-healthcare-following-openais-chatgpt-health-reveal/)
- [FierceHealthcare — JPM26: Anthropic launches Claude for Healthcare](https://www.fiercehealthcare.com/ai-and-machine-learning/jpm26-anthropic-launches-claude-healthcare-targeting-health-systems-payers)
- [MobiHealthNews — JPM: Anthropic launches Claude for Healthcare](https://www.mobihealthnews.com/news/jpm-anthropic-launches-claude-healthcare)
- [Censinet — SMART on FHIR OAuth 2.0 Implementation Guide](https://censinet.com/perspectives/smart-on-fhir-oauth-2-0-implementation-guide)
- [Imprivata — Epic SMART on FHIR patient access](https://docs.imprivata.com/ipa/content/topics/implementation/epic_smartonfhir.html)
- [SMART Health Cards Framework](https://spec.smarthealth.cards/)
- [SMART Health Links — Kill the Clipboard](http://smarthealthlinks.com/)
- [HL7 Confluence — SMART Health Cards and Links FHIR IG Proposal](https://confluence.hl7.org/spaces/FHIR/pages/230557128/SMART+Health+Cards+and+Links+FHIR+IG+Proposal)
- [HackMD — Patient-Shared Health Documents via SMART Health Links](https://hackmd.io/@Jyncr3iQS1iJA09xcuh7QA/rkGeS5cIZe)
- [HL7 SMART App Launch v2.2.0 — Backend Services](https://hl7.org/fhir/smart-app-launch/backend-services.html)
- [HIMSS — 21st Century Cures Act Part Two: Information Blocking and Interoperability](https://www.himss.org/resources/21st-century-cures-act-part-two-information-blocking-and-interoperability/)
- [Federal Register — HTI-2 patient-engagement provisions withdrawal, 2025-12-29](https://www.federalregister.gov/documents/2025/12/29/2025-23890/health-data-technology-and-interoperability-patient-engagement-information-sharing-and-public-health)
- [Medblocks — Epic EHR: Architecture, FHIR APIs, and Integration Guide](https://medblocks.com/blog/epic-ehr-guide)
- [Nirmitee — How to Get Your App Into Epic (2026)](https://nirmitee.io/blog/how-to-get-your-app-into-epic/)
- [EHR Source — Epic vs Oracle Health (Cerner): Full EHR Comparison 2026](https://www.ehrsource.com/compare/epic-vs-oracle-health/)
- [Android Developers — Medical Records data format (Health Connect)](https://developer.android.com/health-and-fitness/health-connect/medical-records/data-format)
- [Android Police — Health Connect adding medical records support in Android 16](https://www.androidpolice.com/health-connect-medical-records-android-16/)
- [Sahha — Apple HealthKit vs Google Health Connect](https://sahha.ai/blog/healthkit-vs-health-connect/)
- [Health Samurai — FHIR R4 vs FHIR R5: Choosing the Right Version (2026)](https://www.health-samurai.io/articles/fhir-r4-vs-fhir-r5-choosing-the-right-version-for-your-implementation)
- [Nirmitee — FHIR R4 vs R5 vs R6: Developer Decision Guide 2026](https://nirmitee.io/blog/fhir-r4-vs-r5-vs-r6-developer-decision-framework-2026/)

### Repo evidence cited

- `src/backend/modules/agent/tools/{base,registry,__init__,query_observations,compute_trend,check_verification,lookup_reference,retrieve_chunks,query_care_tasks,query_medication_changes,query_timeline}.py`
- `src/backend/modules/agent/state.py` (`MAX_STEPS = 5`, `ToolContext`)
- `src/backend/modules/agent/audit.py` (referenced via each tool's `emit_audit_event` call)
- `src/backend/modules/fhir_export.py` (full file read)
- `src/backend/modules/import_structured.py` (`parse_fhir_bundle`, `parse_lab_csv`)
- `src/backend/api/export.py:1017-1296` (FHIR export/download routes)
- `src/backend/api/documents.py:690-745` (structured-import pipeline wiring)
- `src/backend/core/auth.py` (`Session`, `RequireAuth`, `ProfileDbSession`, `get_profile_db_session`, `_get_required_profile_connection`, `open_profile_database_on_login`, `close_profile_database_on_logout`)
- `.mcp.json` (Serena, dev-tooling only)
- `docs/agentic/mcp-tools.md` (binding dev-tooling MCP security rules)
- `docs/agentic/recurring-failures.md` §1, §7 (dependency-graph bypass; SQL three-valued-logic)
- `docs/agentic/harness.md` (MCP/tool rules pointer)
- `docs/dev/agent-code-knowledge.md` (Serena as LSP-over-MCP, dev-only precedent)
- `docs/plans/2026-07-10-post-visit-record-intelligence-roadmap.md:106` (FHIR/CSV import scoping, Apple Health explicitly deferred)
- `docs/plans/2026-07-02-architect-review-proposal-tickets.md:120` ("no portal network connectivity — the user downloads the file themselves")
- `AGENT.md` (stack/layout, dev process shape, dynamic ports)
- `CLAUDE.md` (hard invariants: local-first, redaction before egress, per-profile isolation, read-only agent, ask-before-touching auth/encryption)
