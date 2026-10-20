# Adversarial review: refutations and how each was resolved

**Last Updated:** 2026-10-20
**Owner:** repository owner
**Refresh Trigger:** a further review round on these verdicts; any owner answer that settles an item marked "owner question" below.

> **Point-in-time research (2026-10-20).** Each of the five verdicts was handed to an independent reviewer told to refute it against the code. The reviewer returned `upheld` (true/false), a revised verdict, refutations tagged BLOCKER / MAJOR / MINOR with evidence, and missed risks. This file lists every refutation and its resolution. "Adopted" means the correction is in [02-verdicts.md](02-verdicts.md). "Owner question" means it is listed in [04-owner-questions.md](04-owner-questions.md) and not decided here. The synthesizer re-read the load-bearing lines at `origin/main` `d5ca71d`; those are marked "re-checked".

## Summary

| § | Question | Upheld? | Refutations (B / M / m) | Outcome |
|---|---|---|---|---|
| 1 | Track 1: harness2 for the dev harness | Yes, with corrections | 0 / 4 / 5 | ADAPT stands; tier table, gate claims and S5 framing corrected |
| 2 | Agents reading patient items | Yes, with corrections | 0 / 3 / 4 | ADAPT stands; three factual corrections |
| 3 | File conversion | **No** | 1 / 4 / 7 | Revised verdict adopted: deterministic re-rendering in v1 |
| 4 | Analytics | **No** | 0 / 5 / 6 | Revised verdict adopted: templates as the primary wording control |
| 5 | Dev / expanded trace and HITL | Yes, with corrections | 0 / 3 / 4 | ADAPT stands; migration, retention and audit gaps added |

No refutation was rejected. Two were adopted with a narrower reading, noted in place.

## 1. Track 1 (upheld)

| Sev | Claim refuted | Evidence | Resolution |
|---|---|---|---|
| MAJOR | Track 1 is "off" by default; rsi-loop does not run | `.claude/workflows/build-program.js:26` `const RSI = !(args && args.rsi === false)`; `:177-183` calls `rsi-loop` without `dry_run` (re-checked) | Adopted. 02 §1.1 now shows standing (RSI-BUILD) as the default. |
| MAJOR | The gate is "pure, deterministic" and keeps the proposer from editing its evaluator | `rsi-loop.js:124-125`, `:134-135`: `diff_names` and `numstat` are "verbatim stdout" reported by agents; consumed at `:213`, `:225`, `:227`; no workflow runs a shell primitive itself | Adopted. 02 §1.3 item 2: the gate is deterministic code over agent-reported strings; the owner's diff read is the only independent check. |
| MAJOR | Additions-only protects the ALLOW files | `rsi-loop.js:32` ALLOW includes `docs/agentic/recurring-failures.md`; `:72` `gateNumstat` checks only `rules.ts` and `cases.ts` (re-checked) | Adopted as critical gate 4 in 02 §1.2; fix option is owner question OQ-7. |
| MAJOR | S5 belongs to the Track-2 advice judge, not Track 1 | `rsi-in-development-and-application.md:48` (Track-1 replay gate names OW-3/S5); research `00-README.md:77` (RSI-4 asks for OW-3's sealed set) vs `00-README.md:54` (S5 is for the advice judge) | Adopted. The repo is inconsistent; 02 §1.3 item 6 no longer asserts either reading. Owner question OQ-3. |
| MINOR | "6 rules" | `hooks/rules.ts:23`, `:34`, `:45`, `:57`, `:71` | Adopted: 5 rules. |
| MINOR | Accepted archive written per merged promotion | No Measure phase (`rsi-loop.js:5-11`); Mine already lists merged PRs (`:157`) | Adopted: the next run writes the row. |
| MINOR | Critic rejects reflections below N distinct sessions | `MINE_SCHEMA` (`rsi-loop.js:85-90`) has no sessions field | Adopted: schema change listed. |
| MINOR | Tripwire on S5's sha256 | Only sha256 and counts are committed (`lane-B-interpretation-eval.md:103`) | Adopted: tripwire on path and content, not hash. |
| MINOR | Dry run keeps everything local | `rsi-loop.js:157` calls `gh pr list` and reads review comments; `:197`, `:203` create worktrees and commits | Adopted in the tier table. |

**Missed risks, resolved:** over-broad deny rule passes the gate and fails closed → critic corpus check (02 §1.3 item 3). `recurring-failures.md` as an instruction channel → gate 4, OQ-7. Unconstrained `evidence` and PR-comment text flowing into later prompts → tripwire length and content cap (item 4). No measured Track-1 delta yet → stated in [05-report-angle.md](05-report-angle.md). S5 ambiguity → OQ-3.

## 2. Reading patient items (upheld)

| Sev | Claim refuted | Evidence | Resolution |
|---|---|---|---|
| MAJOR | T0 is verified-only | `tools/query_care_tasks.py:60-68` selects every task with only a status filter (re-checked); `nodes/draft.py:197-214` composes title and quote verbatim | Adopted in 02 §2.1; disclosed in OQ-9. |
| MAJOR | Nothing is kept beyond the in-memory RunLog | `api/assistant.py:1016-1023`, `:338-347` persist the answer as a `ChatTurn`; `:829` caches it; DON-SOURCE (:282) makes rated turns donatable | Adopted as rule X5. |
| MAJOR | Gated outcomes fail closed | `api/assistant.py:914-923` catches any agent exception and runs legacy `rag.query` with `model_runner=runner` (re-checked); `AgentTerminal.terminal` is a three-value Literal | Adopted as rule X3, applied to §§2-4. Owner question OQ-19. |
| MINOR | Evidence base `5415071` | Main moved (PR #215 changed the legacy path) | Adopted: all verdicts re-based; synthesizer re-checked at `d5ca71d`. |
| MINOR | Track-1 staleness was [I] | `rsi-in-development-and-application.md:17`, `:27` vs its own §6 (mod #127, rsi-loop #126/#129 merged) | Adopted as [V]. |
| MINOR | Every node writes an audit row | `nodes/act.py:34-61` emits none; tools self-emit; no test checks emission | Adopted as rule X7 and a design requirement for new tools. |
| MINOR | Handle-only payloads are a viable fix | `state.py:2-4` requires replay; `graph.py:237-306` and `draft.py:29-42` read values from the log | Adopted: OQ-14 option (b) is marked as needing a redesign of draft and replay. |

**Missed risks, resolved:** DON-SOURCE does not cover RunLog traces → OQ-24. No patient opt-out of T0 → rule X10, OQ-9. `retrieve_chunks` no-match fallback widens a values trace → 02 §2.4 and OQ-13. External runner resolved on every request with a commit side effect → 02 §2.3 item 8. Audit commit ordering on exception → X3 and X7 design notes. harness2's selector anonymises labels for a judge, not candidates from a proposer → [01-harness2.md](01-harness2.md) §2.1.

## 3. File conversion (NOT upheld)

| Sev | Claim refuted | Evidence | Resolution |
|---|---|---|---|
| BLOCKER | The draft node writes a plain-language view through `ModelRunner`, vetted by today's guard chain | No `ModelRunner` or `interpret_safety` reference in `modules/agent` (re-checked); `groundedness.py:44-56` positional; `guard.py:44-73` returns 1.0 or 0.0; `assistant.py:684-705` says faithfulness is not called; classifier is question-shaped while `interpret_safety.py:49-52` catches declarative claims | Revised verdict adopted: v1 is deterministic re-rendering; any LLM rewrite needs `validate_interpretation`, `gate_external_payload` and a content-level faithfulness check first (02 §3.3 item 3; OQ-17, OQ-18). |
| MAJOR | RunStep payloads are handles; dev mode shows handles | `nodes/act.py:49-59` stores full output (re-checked); `ObservationRow` has value and unit; `ChunkRef` has text | Adopted: default trace is a handle-only projection, tested for no float value or chunk text (02 §3.1 T4). |
| MAJOR | `agent_expanded_mode` needs no migration | `migrations/profile/versions/009_agent_enabled.py` added `agent_enabled` as a column | Adopted as rule X8. |
| MAJOR | A locally shown view needs no redaction | `draft.py:112-126` sanitizes extraction-derived text; `redaction_gate.py:27-33` requires `gate_external_payload` for any LLM drafter | Adopted *narrowly*: no redaction is needed for the patient's own screen (D3 rationale holds), but `sanitize_untrusted_field` is required on every extracted field and the seam is required for any LLM. |
| MAJOR | The ADAPT delivers conversion for a new upload | `query_observations.py:73` pins `user_verified`; `retrieve_chunks.py:77-80` needs `Document.status == 'verified'` | Adopted: 02 §3 states v1 returns counts only for unverified files; transcription option in OQ-17. |
| MINOR | Chat "faithfulness" counts | It is a surviving/total ratio; authority is always 0.0 | Adopted as rule X9; panel must not overstate it. |
| MINOR | `ChatResponse` at `:136-147` | Class is at `:149-161` | Adopted. |
| MINOR | Base `ca3e319` | Main moved; cited lines hold | Adopted. |
| MINOR | Requests carry a `document_id` filter | `ChatRequest` and `ChatFilters` have none; `CacheKey` is frozen; cache hit skips the graph | Adopted in 02 §3.3 items 1 and 4. |
| MINOR | Provenance has snippet ids | Only `source_page` / `source_bbox_json` are stored; snippet text is in-memory at extraction | Adopted: handles are page and bbox. |
| MINOR | "Vertex models" as a core harness2 property | Vertex appears in `third_party/` runners and `config.py`, not `core/` or `substrate/` | Adopted *narrowly*: [01-harness2.md](01-harness2.md) cites `config.py:92-102` for the Vertex requirement. |
| MINOR | Migration after #211's 015 | Main ends at `014`; 015 is only on the #211 branch | Adopted as rule X11. |

**Missed risks, resolved:** legacy fallback bypasses "never the external runner" → X3, 02 §3.3 item 5. Trace donation would persist raw PHI → OQ-24. Bulk verify widens the evidence base → 02 §3.2. Prompt injection through document content → 02 §3.4. Per-action consent is UI state only → stated in 02 §3.1 T2 and limited to non-irreversible actions. A trace showing the discarded advice draft → excluded in 02 §3.1 T4.

## 4. Analytics (NOT upheld)

| Sev | Claim refuted | Evidence | Resolution |
|---|---|---|---|
| MAJOR | SG-6 covers a new tool; base.py is a contract | `tests/agent/test_agentic_queries.py:65-71` hard-codes three tools and string-greps `run()` (re-checked); Protocol checks shape only | Adopted as rule X2 and design item 2. |
| MAJOR | Nothing is saved | `ChatTurn` persistence (`assistant.py:311-345`, `:1016`); DON-SOURCE | Adopted as rule X5; OQ-25. |
| MAJOR | Adherence answers are current | `_profile_version` (`assistant.py:638-680`) ignores dose tables; cache has no TTL | Adopted as rule X6 and design item 3. |
| MAJOR | harness2 does not adopt automatically | `harness2:README.md:31-33`, `:161-162`; `selection.py:402-440`; `recursion.py:108-126`; `library.py:16-24` | Adopted: automatic adoption is now the stated reason to reject the runtime. |
| MAJOR | Banned-words test is a stopgap | `interpret_safety` is not on the agent path (re-checked); classifier patterns are question-shaped | Adopted: it is the primary control and a hard CI test. |
| MINOR | Base `ca3e319` | Main moved | Adopted. |
| MINOR | Migration after 015 | 015 only on #211 | Adopted (X11). |
| MINOR | Range status always "per report" | `modules/analytics.py:180` "(within reference range)" | Adopted in 02 §4.3 item 5. |
| MINOR | Patient can turn the agent off | No frontend reference to `agent_enabled` (re-checked) | Adopted as rule X10. |
| MINOR | Trace filled from the in-memory RunLog | `graph.py:176`, `:229` return only the terminal | Adopted: needs a `run_agent` contract change. |
| MINOR | Audit rows are ids and enums by design | `compute_trend.py:103` sends `analyte`; dropped silently by the master scrubber | Adopted: new tools emit ids only rather than relying on the scrubber. |

**Missed risks, resolved:** legacy fallback defeats "analytics never off-device" → X3, OQ-19. Analytics answers as durable PHI and donation candidates → OQ-25. Stale adherence from cache → X6. Replay contract → 02 §4.3 item 4. No UI toggle → X10, OQ-9. Declarative sentences pass the on-draft gate → primary banned-words test. Empty trace on pre-model escalate → marker in 02 §4.1 and §5.1. Medication identity in RunStep payloads → 02 §4.4.

## 5. Dev / expanded trace and HITL (upheld)

| Sev | Claim refuted | Evidence | Resolution |
|---|---|---|---|
| MAJOR | Phase A needs no migration | `models/model_settings.py:18`, `:31`; `009_agent_enabled.py:26-29` | Adopted (X8). |
| MAJOR | "Never stored" is compatible with "rated-turn traces only" | RunLog is local (`graph.py:176`); only the answer persists (`assistant.py:1016-1022`); feedback attaches later | Adopted: 02 §5.3 states the conflict; OQ-24 asks the owner. |
| MAJOR | `rsi-loop.js` ALLOW/DENY covers Track-2 promotions | ALLOW is three dev-harness files; `nodes/plan.py` is outside it | Adopted: Track 2 needs its own allow list and gate (OQ-27). |
| MINOR | `VerificationInfo` is counts and scores only | `assistant.py:145-146` `summary` and `issues` carry claim text | Adopted. |
| MINOR | Trace shows model outputs | No model on the agent path (X9) | Adopted: "no model called" marker. |
| MINOR | harness2 Python floor at `pyproject.toml:18` | It is `:11` | Adopted in [01-harness2.md](01-harness2.md). |
| MINOR | Base `b661992` | Main is `d5ca71d`; cited lines hold | Adopted. |

**Missed risks, resolved:** cache-hit and pre-model escalate audit gaps (re-checked: within `chat`, the only direct audit call is the legacy one at `assistant.py:1004`) → X7, OQ-23. `/feedback/export` without consent today → 02 §5.3. Consent-version drift between backend and frontend → 02 §5.4 B. Memory auto-extraction is an existing write on the chat path → shown in the trace table (02 §5.1). Cache serves stale terminals across consent changes → X6.
