# Verdicts after adversarial review

**Last Updated:** 2026-10-20
**Owner:** repository owner
**Refresh Trigger:** any owner answer in [04-owner-questions.md](04-owner-questions.md); the merge of PR #211 (RSI1-DONATE); any change to `src/backend/modules/agent/`, `api/assistant.py` or `.claude/workflows/rsi-loop.js`.

> **Point-in-time research (2026-10-20).** Design only. Nothing here is built, and nothing here answers a gate: every "recommended" item waits for the owner. HealthCentral paths are relative to the repo root at `origin/main` `d5ca71d`; harness2 paths are written `harness2:<path>:<line>` (see [01-harness2.md](01-harness2.md)). Markers: **[V]** read at that commit; **[I]** inferred. Where a verdict was not upheld by the adversarial reviewer, the revised verdict is adopted below. How each refutation was resolved is in [03-adversarial-review.md](03-adversarial-review.md).

## 0. Shared vocabulary and cross-cutting rules

### 0.1 Consent tiers (Track 2, in-app agent)

| Tier | Meaning |
|---|---|
| **T0 Baseline** | What ships today: the read-only chat agent answers the patient's own question. On by default (`AGENT_ENABLED_DEFAULT = True`, `src/backend/modules/agent/settings.py:19`) [V]. |
| **T1 Off** | The default for every *new* capability. A gated tool fails closed with a fixed abstain text. |
| **T2 Per-action ask** | One gated action on one named target, run only after the patient clicks Approve on a card. |
| **T3 Standing per-purpose consent** | A revocable, versioned consent per purpose; routine actions inside that purpose run without a per-click prompt. |
| **T4 Dev / expanded mode** | Visibility only. Orthogonal to T0-T3. Grants no capability and passes no gate. |

### 0.2 Rules every Track-2 verdict below depends on

These came out of the adversarial review. Each one is a fact about `origin/main` that changes a design.

| # | Rule | Why (evidence) |
|---|---|---|
| X1 | **No tier grants** a write to clinical data, a verify, a delete, an export, an off-device call, or a consent change. | Registry is read-only by design, SG-6 (`modules/agent/tools/registry.py:1-7`) [V]. |
| X2 | **SG-6 is narrower than its name.** The test checks three hard-coded tools by string-grepping `run()`; `compute_trend`, `query_observations` and any new tool are not covered, and the `ReadOnlyTool` protocol enforces nothing at runtime. Any new tool must come with the test extended to iterate the whole registry. | `src/backend/tests/agent/test_agentic_queries.py:65-71` [V]; `tools/base.py:25-37` [V reviewer]. |
| X3 | **Gated outcomes are terminals, never exceptions.** Any exception on the agent path falls back to legacy `rag.query` with `model_runner=runner`, and `runner` is the opt-in external runner when the patient enabled it. A consent check that raises would send the question to the legacy LLM path. `AgentTerminal.terminal` is `Literal["answer","abstain","escalate"]`, so `needs_approval` is a schema change. | `api/assistant.py:914-923`, `:932-947` [V]; `:866-870`, `core/external_runner.py:408-420`, `modules/agent/schemas.py:56` [V reviewer]. |
| X4 | **The trace holds raw PHI.** `RunStep.payload` is commented "handles, never raw PHI", but `act` stores the full tool output (values, units, dates, chunk text), and `draft` and `replay` read values back from it. | `modules/agent/state.py:64` vs `modules/agent/nodes/act.py:49-59` [V]; `nodes/draft.py:63-80`, `graph.py:237-306` [V reviewer]. |
| X5 | **Answers are already persisted.** Every agent answer is stored as a `ChatTurn` in the profile DB and cached in process. Rated turns are the DON-SOURCE donation set. | `api/assistant.py:1016-1023`, `:338-347`, `:829` [V reviewer]; [owner-decisions](../../capstone-report/owner-decisions-2026-09-27.md):282 [V]. |
| X6 | **The cache does not know about consent or doses.** `CacheKey` has no consent component, and `_profile_version` fingerprints only verified observations and documents. A cached answer survives a revoke or a new dose log. | `modules/agent/cache.py:40-45`, `:62`; `api/assistant.py:638-680` [V reviewer]. |
| X7 | **Audit gaps exist today.** A semantic-cache hit and a pre-model advice escalate both return with no audit row; `act` emits nothing itself and relies on each tool to self-emit. | `api/assistant.py:811-814` and `modules/agent/graph.py:170-174` [V]; within `chat` (from `:840`) the only direct audit call is the legacy `audit_and_commit` at `:1004` [V]; `nodes/act.py:34-61` [V reviewer]. |
| X8 | **A new per-profile setting needs a profile migration.** `agent_enabled` is a column added by `009_agent_enabled`; main's latest profile migration is `014_streaks_hidden`. | `migrations/profile/versions/009_agent_enabled.py:26-29` [V reviewer]; `ls migrations/profile/versions` [V]. |
| X9 | **No LLM runs on the agent path today.** The planner and draft are deterministic; `interpret_safety` and `modules/faithfulness.py` are not called on it. The "faithfulness" number in chat is a surviving/total sentence ratio, and groundedness is positional. | `git grep ModelRunner\|interpret_safety -- src/backend/modules/agent`: no hits [V]; `nodes/plan.py:8-11` [V]; `api/assistant.py:684-705`, `guardrails/groundedness.py:44-56` [V reviewer]. |
| X10 | **The patient has no UI switch for the agent.** The PATCH route exists, but the frontend never references `agent_enabled`. | `git grep agent_enabled -- src/frontend/src` (non-test): no hits [V]; `api/model_settings.py:1204-1229` [V reviewer]. |
| X11 | **Consent storage depends on PR #211.** It is open and not merged (head `07866ed`, no longer a draft, 2026-10-20). Its migration `015_data_donation` exists only on that branch. | gh REST `pulls/211` [V]. |

## 1. Track 1: adopt, adapt or reject harness2 for the development harness?

**Final verdict: ADAPT, patterns only.** Never vendor, install or run harness2. Re-implement four of its ideas as small deterministic checks: a budget identity assertion, a `KEEP_BASE`-style critic, a leak tripwire, and an archive of accepted promotions. Correct the record: harness2 is Harness², not RRSI, and has no critic, pruner or OOD check.
**Adversarial review: upheld, with corrections adopted** (see [03](03-adversarial-review.md) §1).

### 1.1 Tier table for Track 1 (corrected)

The first draft said Track 1 is off by default. It is not: `build-program.js` runs `rsi-loop` non-dry-run after every run unless `rsi: false` is passed [V] `.claude/workflows/build-program.js:26`, `:177-183`; `rsi-loop.js:21`.

| Mode | What runs | Human sees / approves |
|---|---|---|
| Mod not loaded | No telemetry. The mod loads only via `--plugin-dir` or `CLAUDE_CODE_PLUGIN_DIRS` (mod README). | Nothing. |
| Mod loaded, no loop | Metadata-only rows to git-ignored `.claude/logs/rsi/`; fail-closed deny rules, fail-open logging. | Status line and `/rsi` scoreboard. |
| **Default: standing (RSI-BUILD)** | `rsi-loop` after every build-program run; opens READY PRs for survivors and never merges (`rsi-loop.js:252`; owner rows RSI-BUILD :204, AUTO-MERGE :206). | Owner merges each promotion by hand after reading reflection, diff, gate tails and replay result. **The owner's diff read is the only independent write-scope check** (see 1.3 item 2). |
| Dry run | Mine, reflect, propose (max 3, in worktrees, with commits) and gate; no PRs. Still calls GitHub (`gh pr list`, PR review comments; `rsi-loop.js:157`). | Owner reads summary JSON, reflections, gate output, `archive.jsonl`. |
| Expanded view | Whole transcript, clusters, critic verdicts (new), budget ledger (new), archive. | Visibility only; same gates and same human merge. |

### 1.2 Critical gates (Track 1)

1. Merging any RSI promotion. Never agent-merged (AUTO-MERGE :206; RSI-4 :203). harness2 adopts automatically; that is what must not be copied.
2. Any edit to ask-first modules, `core/auth.py`, encryption. The DENY list in `rsi-loop.js:34-49` must not shrink.
3. Any change to tests, thresholds, gate scripts, `.github/`, or `rsi-loop.js` itself (ALLOW, DENY, `gateNumstat`). A change to the gate cannot come from the loop; it goes through an owner-approved build-item PR.
4. **Any deletion or rewrite in an ALLOW file, including `docs/agentic/recurring-failures.md`.** Additions-only covers only `rules.ts` and `cases.ts` (`rsi-loop.js:72`) [V]. `recurring-failures.md` is in ALLOW (`:32`) and is read by every implementer and reviewer (CLAUDE.md §4; `build-item.js:306`), so today the loop can remove a failure mode or plant instructions there.
5. Creating, reading or reaching the sealed set S5 (OW-3). Owner-held outside every worktree; only its sha256 and counts are committed (owner-decisions :119; `lane-B-interpretation-eval.md:103`).
6. Anything leaving the device in product paths (D12 break-glass, D3 exports, any network call).

### 1.3 Design (Track 1, all under `.claude/` and `docs/`; nothing built)

1. **Budget ledger** (from `harness2:harness2/core/ledger.py:26-33`, `:89-113`). Count spawned agents per phase against 1 + 1 + ≤3 + ≤3 + 1 and fail on a duplicate label or mismatch. Today the budget of 9 is a comment (`rsi-loop.js:14`).
2. **State what the gate actually checks.** `gateDiff` and `gateNumstat` are deterministic code over strings the proposing and validating agents report as "verbatim stdout" (`rsi-loop.js:124-125`, `:134-135`, consumed at `:213`, `:225`, `:227`); no workflow runs a shell primitive itself [V reviewer]. The PR body must say this, and the owner's read of the real diff is the independent check. harness2's import boundary (`judge.py:15-19`) is a code-level separation that `rsi-loop` does not have.
3. **Deterministic critic** (from `KEEP_BASE` and the 1/k rule, `harness2:harness2/core/prompts.py:287-289`, `:919-921`). Reject a reflection backed by fewer than N distinct sessions (needs a `sessions` field in `MINE_SCHEMA`, `rsi-loop.js:85-90`; rows already carry `session`). Reject a candidate whose `match` embeds run-specific literals (PR numbers, branch or worktree names, queue ids, absolute paths). **Reject over-broad matches:** run every new `match` against a fixed corpus of ordinary commands and reject high hit rates, because a merged `deny` on `^git push` would fail closed and block the whole harness. Cap rule `message` length and reject imperative text aimed at other tools or files. "No change" is a valid logged outcome. Do not copy GENERALIZE.
4. **Leak tripwire** (from `harness2:harness2/core/context.py:399-427`). Before each propose prompt, scan the prompt for the sealed-set *path or content* (not its hash, which is public), CI gate file contents, another candidate's gate output, and over-long or command-like `evidence` strings copied from PR comments (`rsi-loop.js:89`, `:157`).
5. **Accepted archive.** One metadata-only row per merged promotion with cluster and before/after failure rate. There is no Measure phase (`rsi-loop.js:5-11`), so the *next* run writes it from merged PRs it already lists (`:157`).
6. **OOD check.** harness2 has none. A time split: cases mined after a candidate's window re-check it on a later run. Whether S5 should also gate Track 1 is an open owner question (OQ-3), because the repo says both things.
7. **CI gap.** The PR body says CI is "the second half of the gate" (`rsi-loop.js:252`), but `.github/workflows/ci.yml` has no step that runs the mod's replay test [V reviewer]. Adding one is an owner-gated build-item change (OQ-4).
8. **Pruner: none.** Deletions arrive only as ordinary owner-reviewed PRs (OQ-5). The rule table has **5** rules (`hooks/rules.ts:23`, `:34`, `:45`, `:57`, `:71`) and 14 replay cases.
9. **Docs.** `rsi-in-development-and-application.md:17` and `:27` still say Track 1 is not merged; its own §6 says the mod (#127) and `rsi-loop` (#126, #129) are merged. See [05-report-angle.md](05-report-angle.md).

**Stays ours, untouched:** human merge, the 3-file ALLOW and the DENY list, additions-only, `MAX_CANDIDATES = 3`, metadata-only logging, OW-3 owner custody, build-item's review limit and ask-first rule, every `src/` module.

### 1.4 Risks

- The proposer writes the rule *and* its replay cases (`rsi-loop.js:201`): the replay set is self-graded.
- CI does not exercise `rules.ts`, so a green survivor PR proves nothing about the rule.
- Persistent prompt injection through rule messages and through `recurring-failures.md`.
- Over-broad deny rules block the harness (fail-closed guard).
- Telemetry drops rows and stops at 4 MiB per day; mined rates are lower bounds.
- Importing harness2 would bring Python 3.12, Vertex network calls and permission-bypass flags.
- Citation error in the senior report if harness2 is cited as RRSI.

## 2. How should in-app agents read the patient's items?

**Final verdict: ADAPT.** Keep the existing read-only, profile-scoped agent as the base (T0). Put each new capability (full-document read, readable view, vault analytics) behind off-by-default, revocable consent with per-action approval cards. Dev mode adds visibility, never authority. harness2 is a development-harness pattern source only.
**Adversarial review: upheld, with three factual corrections adopted** (see [03](03-adversarial-review.md) §2): T0 is not entirely verified-only; answers are persisted, not only held in memory; the fallback makes "fails closed" untrue until X3 is designed in.

### 2.1 Per-tier table

| Tier | Allowed | Human sees / approves |
|---|---|---|
| T0 Baseline (exists) | The 8 read-only tools, `MAX_STEPS = 5` (`state.py:19`), active `ProfileDbSession` only, advice pre-check and guard. **Not entirely verified-only:** `query_care_tasks` returns every task regardless of verification (`tools/query_care_tasks.py:60-68`) [V], and draft composes title and source quote verbatim (`nodes/draft.py:197-214`) [V reviewer]; timeline labels unverified events (`draft.py:289-320`). Answers persist as `ChatTurn` (X5). | Answer with `[cite:N]`, counts, `is_valid` badge. No opt-out in the UI today (X10). |
| T1 Off (new capability default) | Nothing beyond T0. A tool with a `required_capability` returns a fixed abstain terminal (not an exception, X3). | Fixed text naming the capability and a Settings link. Audited with the capability as an allowlisted enum. |
| T2 Per-action ask | One gated read on one named target (for example document X pages 1-3). The run ends in a new `needs_approval` terminal holding a handle (tool, validated args, target ids, no PHI); approval runs that single action. No carry-over to other targets or sessions. | Card: tool, purpose, exact target, whether the source is verified, "nothing saved or sent". Approve once or Deny. Request, approve and deny are audited (started/completed on the approval route). Deny ends in abstain. |
| T3 Standing per-purpose | Per profile and purpose (for example `read_documents_full`, `analytics_vault`), revocable, versioned, on the PR #211 `DonationConsent` pattern. Never covers a critical gate. | Grant and revoke in Settings only, never through the agent. A "used: <purpose>" chip on each answer. Stale wording shows as stale (DON-STALE pattern). Grant or revoke clears the cache (X6). |
| T4 Dev / expanded | No permission change. A trace of this request only, never persisted, logged, cached or donated. Default content is a handle-only projection (X4; see §5). | Collapsible "What the agent did" panel. Toggling is audited. Gates still stop and the trace shows where. |

### 2.2 Critical gates

Any write to clinical data; promoting agent, OCR or converted values to verified; anything leaving the device (D12; break-glass is human-only); exports and saved files (D3); cross-profile access (no gate can approve it); granting, widening or revoking any consent; any read for training, synthetic or trace donation (separate DON consent); presenting unverified or OCR text as fact; advice-seeking questions (escalate cannot be bypassed); raising `MAX_STEPS`, relaxing groundedness or faithfulness, adding a write tool; delete, restore, prune.

### 2.3 Design (nothing built)

1. Optional `required_capability` on `ReadOnlyTool` (`tools/base.py`); existing tools keep `None`. New read-only tools `read_document_full`, `render_readable_view`, `summarize_vault_analytics`. **Each must self-emit its audit event** (X7) and be covered by a registry-wide SG-6 test (X2).
2. Consent check in `nodes/act.py` returns a terminal (X3). Narrow the `except Exception` fallback so gated intents can never reach `rag.query`. Approve/deny via `POST /assistant/approvals/{handle}` with `ProfileDbSession`, `audit_intent`, an audit-order-guard classification, and HTTP tests through `tests/support/routes.py::route_client`.
3. Storage: profile table `agent_capability_consents` on the #211 pattern, new linear migration after #211 lands (X11).
4. Cache: add a consent version to `CacheKey` or clear on grant/revoke (X6).
5. Trace: see §5.
6. A future LLM planner goes through `ModelRunner` locally and its output still passes `registry.validate_args`.
7. Add a Settings toggle for `agent_enabled` (X10).
8. Resolve the external runner only on the legacy branch, so a T0 request does not decrypt the API key for nothing (`assistant.py:866-870`; `core/external_runner.py:79-91`) [V reviewer].

### 2.4 Risks

PHI in the trace (X4); stale answers after revoke (X6); unverified care-task text reaching the patient today; prompt injection through whole-document reads; analytics drifting into inference; consent fatigue; dependency on unmerged #211; `retrieve_chunks` falls back to the k most recent verified chunks when nothing matches (`tools/retrieve_chunks.py:104-109`), so a values trace would show unrelated document text; DON-SOURCE (:282) does not cover RunLog traces, so trace donation needs a new owner row.

## 3. Converting files into a readable format

**Final verdict (revised): ADAPT, as deterministic re-rendering in v1.** The agent may re-render data the patient has already verified as a read-only, cited, unstored view next to the source page image. It must not run OCR to create records, verify, write files, export, call the external runner or delete. An LLM plain-language rewrite is a separate, later option with its own gates.
**Adversarial review: NOT upheld. The revised verdict is adopted** (see [03](03-adversarial-review.md) §3). The first draft assumed an LLM drafter checked by today's guard chain. There is no LLM on the agent path (X9), and the guard chain cannot vet LLM prose: groundedness is a positional zip, the 0.6 threshold is binary, `modules/faithfulness.py` is not called, and the advice classifier only matches question-shaped text while `interpret_safety` catches declarative "this indicates you have X" (`modules/interpret_safety.py:49-58`).

**What the patient gets from v1, stated plainly:** for a freshly uploaded scan, nothing but counts and a link. Its observations are unverified and the document status is not `verified`, so the tool and `retrieve_chunks` return no values (`tools/query_observations.py:73`; `tools/retrieve_chunks.py:77-80`) [V reviewer]. The value arrives after verification in VerificationWorkbench. A labelled "unverified transcription" of extracted text is a possible per-action option (OQ-17).

### 3.1 Per-tier table

| Tier | Allowed | Human sees / approves |
|---|---|---|
| T1 Off (default) | No conversion capability; T0 chat unchanged. Ingest, OCR, page viewer, glossary and exports stay on non-agent routes. | Today's gates: verify click (`api/documents.py:1255`), `confirm=true` on visit-prep and FHIR exports (`api/export.py:725-733`, `:1185-1193`). |
| T2 Per-action ask | One read-only `document_view` tool returns verified observations and entities with `source_page` handles; unverified items as status and counts only (`check_verification.py` pattern). Template sentences, `[cite:N]`, `sanitize_untrusted_field` on every extracted text field. Ephemeral; local only. | Preview card (document, pages, "verified values only", "nothing saved or sent"), then Convert. Result next to the page image (`documents.py:1716`), dropped-sentence count, unverified count with a Workbench link. The per-action prompt is UI state, so only the chat route's single audit row records it; acceptable only while nothing irreversible happens. |
| T3 Standing per-purpose | Same view without a per-click prompt for one named purpose. Never widens to verify, export, store, external runner or donation. Storage does not exist (OQ-11). | Grant/revoke in Settings, audited. Same provenance markers. |
| T4 Dev / expanded | Handle-only trace projection by default: tool names, ids, counts, gate decisions, "no model called". Not the raw `payload['output']`, and not the pre-guard draft that an advice gate discarded (`guardrails/guard.py:118-121`). | Seeing is not approving. Cannot override escalate or abstain. |

### 3.2 Critical gates

Marking an extracted or OCR value verified (human only; the verify route marks the whole document at once, `documents.py:1262-1283`, which also makes every chunk of that document agent-groundable); any third-party export (`confirm=true` plus strict redaction, D3); `/export/csv` and `/export/json` (patient only, never an agent); any external-runner call or break-glass (D12); writing a converted artifact to disk or the profile DB (breaks SG-6; needs an owner decision and a migration); escalate and critical-value templates reach the patient unchanged (`interpret_safety.check_critical_value`, `:160`); any consent change; deleting a document (`documents.py:1819`); any edit to ask-first modules or the 0.6 and 0.7 thresholds to make conversion pass.

### 3.3 Design (nothing built)

1. `modules/agent/tools/document_view.py`, read-only, self-emitting audit, in a registry-wide SG-6 test. There is no `document_id` on `ChatRequest` or `ChatFilters` today (`api/assistant.py:101-131`; `modules/agent/state.py:22-41`); adding one changes the frozen `CacheKey`.
2. Deterministic routing in `nodes/plan.py`. Fixed templates in `nodes/draft.py`.
3. **If an LLM rewrite is ever added:** call `interpret_safety.get_safety_guard().validate_interpretation` (called, not edited), pass the payload through `gate_external_payload` (`guardrails/redaction_gate.py:27-33`), and add a content-level faithfulness check before claiming the guard chain suffices. Owner decision first (OQ-17, OQ-18).
4. Trace: `ChatResponse.trace` filled from a handle-only projection when `agent_expanded_mode` is on; that setting needs a profile migration (X8). A cache hit returns a `{node: "cache"}` marker; the trace is excluded from `put_cached`.
5. Gated conversion intents never fall through to legacy `rag.query` (X3). Test it.
6. Tests first, through `route_client`: no trace when off; no float value or chunk text in the default trace; no unverified value in tool output; no export or verify route reachable from the agent.

**Untouched:** `interpret_safety.py`, `redaction.py`, `faithfulness.py`, `verifier_agent.py`, `extract.py`, `api/export.py`, `core/external_runner.py`, auth and encryption, the 0.6 and 0.7 thresholds.

### 3.4 Risks

A fluent rewrite of a mis-read OCR value looks more authoritative than the scan; automation bias from a trace nobody reads; bulk verify widens the evidence base; prompt injection through document content is the largest such surface and is untested on whole documents; the "faithfulness" label in chat is a sentence ratio, not the faithfulness module's score (X9), and a HITL panel must not present it as more; the DON-PURPOSES "app-agent run traces" purpose (:278) would persist payloads that hold raw PHI (X4).

## 4. Data analytics on the patient's data

**Final verdict (revised): ADAPT, deterministic templates only.** Lab trends and medication adherence can become read-only, cited agent tools with fixed template wording. Wearables-to-lab correlation is DEFERRED. harness2 is rejected as a runtime component, and the reason is that it adopts changes automatically with no human gate.
**Adversarial review: NOT upheld. The revised verdict is adopted** (see [03](03-adversarial-review.md) §4). Corrections: SG-6 does not cover new tools (X2); analytics answers are persisted and donation-eligible once rated (X5); a cached adherence answer survives new dose logs (X6); harness2 *does* adopt automatically (`harness2:README.md:31-33`, `harness2:harness2/core/selection.py:402-440`); `interpret_safety` is not on the agent path, so the banned-words template test is the **primary** wording control, not a stopgap (X9).

### 4.1 Per-tier table

| Tier | Allowed | Human sees / approves |
|---|---|---|
| T0 / T1 Off for new analytics | Today's `compute_trend` (verified rows, one analyte; `tools/compute_trend.py:56-60`) stays. No adherence, cross-series, wearables or saved values. The "off" tier for the agent itself is unreachable from the UI (X10). | Cited answer or fixed abstain/escalate text (`guardrails/templates.py:12-24`). |
| T2 Per-action ask | One analysis from a fixed list (trend over a window; adherence summary per medication), from verified rows or the dose log, inside `ProfileDbSession` and `MAX_STEPS`. Template sentences citing observation or dose ids. No LLM. | Preview card: tool, series, window, row count, method. Run or Cancel. Advice follow-ups still escalate. |
| T3 Standing per-purpose | Same fixed analyses for granted purposes ("trends", "adherence"), on request only: no background jobs, no notifications, no saved derived values, never the external runner. **The answer text is still persisted as a `ChatTurn`** (X5). | Settings card with exact wording (DON-COPY pattern), one-tap revoke, purpose named on each result, ids-and-enums audit. |
| T4 Dev / expanded | Trace of plan, tools, validated args, reflect, guard; default handle-only (§5). A pre-model escalate has no RunLog (`graph.py:170-174`), so the panel must show a "stopped before any tool: advice question" marker rather than nothing. | Visibility only; toggling audited (field names only, like AUDIT-EXT-ASKFIRST :264). |

### 4.2 Critical gates

Any write (saving a statistic, verifying, editing a dose); medication timing and reminders (`learn_patterns` writes and stays patient-triggered, `api/medications.py:1347`); describing a pattern must never become a recommendation; anything off-device; analytics in a third-party export (strict, patient-approved); analysis of unverified data; any comparison, correlation or causal wording (wearables non-goal, `docs/plans/2026-10-13-wearables-00-program.md:26`); advice questions; consent and dev-mode changes; adding analytics traces to a donation.

### 4.3 Design (nothing built)

1. `modules/agent/tools/compute_adherence.py`, read-only, reusing `streak_engine.compute_streak` and **not** `PatternLearner.learn` (which writes). Self-emitting audit with ids only; medication names are untrusted free text like analyte and unit (`draft.py:115-121`).
2. Extend the SG-6 test to iterate the whole registry and scan called helpers, not just `run()` (X2).
3. Add `DoseTaken` and `MedicationSchedule` to `_profile_version`, or bypass the cache for adherence (X6).
4. Extend `graph.replay` for adherence steps, or state that adherence is excluded from the replay guarantee (`state.py:1-6`).
5. A hard CI test over every analytics template and every tool field that reaches a sentence, against the repo's existing banned-words list (`docs/plans/2026-10-14-wearables-15-symptom-journal.md:133`). Note `modules/analytics.py:180` emits "(within reference range)" without "per report", so the precedent itself would fail that list.
6. One trend definition (OQ-21): today chat uses first-vs-last with strict equality (`compute_trend.py:83-89`) and the Trends page uses latest-vs-prior with a 5% band (`modules/analytics.py:70`, `:96-112`).
7. Gated analytics intents fail closed to `ABSTAIN_TEMPLATE` and never reach the legacy fallback (X3).
8. Consent: `agent_capability_consents` after #211 (X11). Trace: §5, which needs a `run_agent` return-contract change (`graph.py:176`, `:229`).

**Untouched:** ask-first modules, `core/external_runner.py`, `ALLOWED_DETAIL_KEYS` (no analyte names), guard order and `CONFIDENCE_THRESHOLD`.

### 4.4 Risks

A citation proves a source exists, not that a statistic is right (positional groundedness); neither guard catches causal wording; two definitions of "trend"; adherence wording sliding into medication advice; consumer-device data looking clinical next to labs; "off (default)" misleading while the agent is on and has no UI switch; dev-mode trust; a future LLM planner cherry-picking analyses; medication identity becomes a new PHI category in the trace.

## 5. Dev / expanded trace and HITL

**Final verdict: ADAPT.** Build expanded mode as a per-request, per-profile view of the agent's run, returned in the chat response, not stored by default. Every consent-gated or irreversible action stops for a human in every mode. Feed traces to any RSI loop only through the `agent_traces` donation purpose, and only after the owner rules on trace retention and source. Borrow harness2's patterns; reject its code, its permission-bypass runtime and its GENERALIZE prompt.
**Adversarial review: upheld, with four corrections adopted** (see [03](03-adversarial-review.md) §5): the toggle needs a migration (X8); "never stored" conflicts with "rated-turn traces only"; cache-hit and pre-model escalate have no audit rows (X7); `VerificationInfo` carries claim text, not only counts.

### 5.1 What the patient sees, and what is approval

| Step | Shown in expanded mode | Approval? |
|---|---|---|
| Pre-model advice check | "Stopped: advice question" marker (no RunLog exists) | Never approvable. Escalate is a safety stop, not a consent prompt. |
| Cache hit | "Served from cache; no fresh run" marker | Informational |
| Plan | Decision (call tool / draft / abstain) and remaining budget | Informational |
| Act | Tool name, validated args, ids and counts by default; values only if the owner approves a values view (OQ-13) | Informational; T2 actions stop at their card |
| Reflect | Loop / draft / abstain-budget decision | Informational |
| Draft | Template sentences that survived; count dropped. Not a discarded advice draft | Informational |
| Guard | Advice verdicts, groundedness result, terminal | Informational |
| Model call | "No model called" on the agent path today (X9); "fell back to legacy path" when X3 fires | Informational |
| Memory | Whether `_auto_extract_memory` wrote a fact (`api/assistant.py:1025-1034`) [V reviewer] | Informational |
| Any critical gate (§5.2) | Where the run stopped | **Mandatory, in every tier** |

Approval is mandatory only on critical gates and T2 actions. Everything else is informational, to avoid approval fatigue. Expanded mode never offers "approve all".

### 5.2 Critical gates

Off-device calls and break-glass (D12; own confirmation, audit row, UI warning; never pre-approved); the first write-capable tool (an owner gate) and every write after it; irreversible delete or revoke (AO-DESIGN D started/completed rows); any file leaving the vault (strict preview; CSV/JSON started by the patient only); donation collect for any purpose including `agent_traces` (`{confirmed: true}` plus a passing leak check); consent wording changes (DON-COPY, DON-STALE); verifying extracted values; promotion of any RSI change from either track; edits to ask-first modules or `core/audit.py` allowlists.

### 5.3 Storage

| Layer | Where | Status |
|---|---|---|
| RunLog | Local variable in `run_agent` (`graph.py:176`); only the terminal returns (`:229`) | [V] exists |
| Trace in response | Optional `ChatResponse.trace`, handle-only projection by default, per-profile toggle (needs migration, X8) | design |
| Persisted trace | Per-profile `agent_runs` table, deleted with the profile and source session | only if the owner chooses (OQ-12, OQ-24) |
| Audit rows | Master DB, handle-only (`modules/agent/audit.py`); never trace content (AUDIT-PHI-001) | [V] exists; gaps in X7 |

**Conflict to resolve before any trace donation:** a "never stored" trace cannot later be collected for a *rated* turn, because rating happens after the response, when the RunLog is gone. Collecting rated-turn traces requires persisting traces for every run while `agent_traces` consent is on and purging unrated ones (OQ-24). Separately, `POST /feedback/export` already writes strict-redacted rated turns to `rl_exports/` with no consent gate until DON-RLEXPORT ships with #211 (`api/feedback.py:340-437`) [V reviewer]; a Track-2 loop must not read that as a stand-in for `agent_traces`.

### 5.4 Design phases (nothing built)

- **A. Display.** `run_agent` hands back its RunLog; a typed `AgentTraceView` projection; the `state.py:64` comment corrected; `ChatResponse.trace`; a per-profile toggle with a profile migration; frontend panel in `ExplainAssistant.tsx`; route tests: no trace when off, none from another profile, cache marker on a hit. Add handle-only audit rows for cache hits and pre-model escalates (OQ-23).
- **B. Consent tiers.** `needs_approval` terminal plus approve route; functionality consents on the #211 pattern, sharing its single consent-text-version constant and its frontend pin test (HC-DON-005e).
- **C. Persisted traces.** Only if chosen.
- **D. Trace donation and a Track-2 loop.** Only after OQ-24. Strict redaction (called, not edited), Safe Harbor detector, canaries. The loop would propose edits to `nodes/plan.py` and replay cases, which are **outside** `rsi-loop.js` ALLOW, so Track 2 needs its own allow list and gate (OQ-27).

### 5.5 Risks

PHI in a trace whose comment says otherwise; trace content leaking into master-DB audit details; consent laundering through dev mode; approval fatigue; unmarked gaps (cache, fallback, pre-model escalate); shoulder-surfing; an RSI archive memorising patients (value plus date survives strict redaction); DON-CANARY "drop and continue" (:286) may be too weak for structured traces; harness2 has no held-out adoption gate, so HealthCentral must supply its own; report attribution (harness2 is not RRSI).
