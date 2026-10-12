**READY (2 PRs, serial, after #60)** — RL-EXPORTS then RL-EXPORT-EMPTY; owner answered RSI-Q1…Q4 on 2026-10-10. Telemetry, MMR and eval-score persistence stay BLOCKED behind W-7, W-8 + RSI-AUDIT, and GATE-14.

# RSI-TPM-MMR — research-to-program integration pack (scaffold, 2026-10-10)

**Source:** PR #68 (`docs/rsi-loop-research`, head `de5b700`, open): `docs/plans/2026-10-10-rsi-loop-applicability-report.md` (the report) and `docs/plans/2026-10-10-rsi-audit-handoff-prompt.md` (the handoff). Those paths exist on main only after #68 merges.
**Measured on:** `origin/main` = `eb7de28`, worktree `hc-rsi-plan`. Nothing under `src/`, `scripts/` or any plan file was edited.
**Prior research (PR #21 corpus, `docs/research/2026-09-08/`):** `git grep -ciE '\bTPM\b|\bMMR\b|maximal marginal' origin/main -- docs/research docs/agentic docs/plans` → no hits. Its only related finding: the legacy RAG has no reranker (`01-codebase-audit.md:388-402`), and "no telemetry" is an invariant (`docs/agentic/roadmap.md:36`). #68 is the first source for TPM and MMR.

## 1. Terms

| Term | Meaning here | Source |
|---|---|---|
| TPM / RPM | Tokens per minute and requests per minute through `ModelRunner` and `ExternalModelRunner`, shown on a local Settings card. On-device only (C-LOCAL-1) | report §6 |
| MMR (both senses, owner decision 2026-10-10) | (1) **model memory**: RSS/VRAM via psutil + Ollama `/api/ps`; (2) **maximal marginal relevance** for RAG retrieval. Sense 2 is a build, not a gauge: `grep mmr\|marginal_relevance src/` = 0 | report §6 `:116` |
| Eval-score persistence | `ScoreReport.model_dump_json()` → master DB or JSONL → per-subsystem trend (Verify substrate; feeds HC-M07) | report §9 item 4 |

Honesty caveat (report `:113`): the agent path composes deterministically and never calls the LLM, so TPM/RPM read about 0 for agent-served chats. The card must show agent runs, cache hits and legacy LLM calls as separate series.

## 2. Phases and dispatch readiness

Owner answered RSI-Q1…Q4 on 2026-10-10 (rows recorded on PR #60; not on `origin/main` until #60 merges, so every Task 0 grep for them waits on #60).

| ID | Kind | Scope | Depends on (hard; *soft*) | Stop gates (owner) | Measured acceptance | Dispatch |
|---|---|---|---|---|---|---|
| RL-EXPORTS (PR-1) | PRODUCT (security, ask-first delete path) | git-ignore `src/backend/rl_exports/`; remove `rl_exports/profile_{id}/` in `DELETE /profiles/{id}`; fix the false docstring `api/profiles.py:799-803` | #60 merged (RSI-Q2 row) | RSI-Q2 **answered: RL-EXPORTS first**, read as the licence for this sweep. Stop if the change has to reorder the crypto-erase steps (C-KEY-2) | §3 task list PR-1 | **READY after #60** |
| RL-EXPORT-EMPTY (PR-2) | PRODUCT (bug) | `upsert_feedback` fills `prompt_snapshot` from the preceding user `ChatTurn` | **PR-1 merged**; *W-4, W-3* (share `api/assistant.py`; PR-2 should not need it) | RSI-Q1 **answered: server copies prior turn** | §3 task list PR-2 | **READY after PR-1** (serial) |
| RSI-AUDIT | DOCS (review) | #68 handoff Phase A + Phase B (MMR), `VERDICT: PASS\|REVISE` | **#68 merged** | none (read-only) | verdict file `docs/reviews/<date>/RSI-AUDIT-r<N>-{prompt.md,codex.txt,response.md}` + a row in `docs/reviews/README.md` | BLOCKED: #68 |
| RSI-TEL | PRODUCT | `record_llm_call` in existing `monitoring/metrics.py` (`MetricsCollector`); hooks in `ModelRunner` + `ExternalModelRunner`; counters for agent runs, cache hit/miss, abstain; `GET /settings/model/telemetry` (`RequireAuth`, counts only) | **W-7** (shares `core/model_runner.py`); keeps W-6 fail-closed `external_runner.py` | RSI-Q3 **answered**; open: `metrics_enabled` gate in or out (handoff B1) | HTTP route test; counters move on a stubbed call; no network call | BLOCKED: W-7 |
| RSI-TEL-UI | PRODUCT (frontend) | `useLlmTelemetry` + `LlmTelemetryCard.tsx`; headline = agent runs, cache hits, abstain rate; TPM/RPM shown for legacy LLM calls only (RSI-Q3) | RSI-TEL | none | vitest incl. the "agent path: 0 LLM calls" state | BLOCKED: RSI-TEL |
| RSI-MMR | PRODUCT | Memory gauge (RSS/VRAM) + passive diversity@k over retrieved chunks; "unavailable" without embeddings (RSI-Q4) | RSI-TEL-UI; **W-8**; **RSI-AUDIT PASS** | RSI-Q4 **answered: passive metric** | retrieval order and agent golden set (74) identical | BLOCKED: W-8, RSI-AUDIT |
| RSI-MMR-RERANK | — | Active re-rank | — | RSI-Q4: **unplanned** | — | NOT PLANNED |
| RSI-EVAL | PRODUCT | Persist `ScoreReport` (master DB only, never profile DBs) + per-subsystem health score | **GATE-14** (shares `scripts/agent_eval_gate.py`) | open: storage (JSONL vs master table) | gate run appends 1 record | BLOCKED: GATE-14 |

Hard deps not on `origin/main` today: W-7, W-3, W-8, W-4 (`git log origin/main --oneline --grep=<id>` → no merge commit); GATE-14 is an owner item. P5 is merged (PR #54; `git grep -c time_source_lint origin/main -- .github/workflows/ci.yml` → 1).

## 3. RL-EXPORT-EMPTY evidence (verified on `origin/main` `eb7de28`)

**Verdict: CONFIRMED.** No production path writes `prompt_snapshot`.

Re-checked at `origin/main` `a4b62b2` (2026-10-12): every line cited below is unchanged. #76 (chat-restore race) edited `ExplainAssistant.tsx`, but not the feedback payload (`:209`, `:230` still send no prompt). #75 (medication routes 500) is outside the RL path.

| Step | Location | What happens |
|---|---|---|
| Frontend payload | `src/frontend/src/pages/ExplainAssistant.tsx:209-217`, `:230-238` | sends `session_id, rating, response_text, feedback_tags, correction_text` only; no `prompt_snapshot`, `model_name`, `provider` |
| API | `src/backend/api/feedback.py:209-210`, `:228` | copies `prompt_snapshot` from the request body only; nothing derives it |
| Chat persistence | `src/backend/api/assistant.py:276` `_append_turns` | stores turns (role, content); does not touch `ResponseFeedback` |
| Other writers | `git grep -n -E 'prompt_snapshot\s*=' origin/main -- src/backend ':!*tests*'` | only `api/feedback.py:210`, `:228`, `:374` (a read) |
| Export | `src/backend/modules/rl_dataset.py:116`, `:120-121` (GRPO), `:167-168` (DPO), `:217-218` (SFT) | `if not prompt …: continue` skips every row → 3 empty JSONL files |
| Why tests are green | `src/backend/tests/test_rl_feedback.py:46`, `:183` inject `prompt_snapshot`; `:301-336` call `export_dataset(...)` as a function | recurring-failures #1 (no HTTP, injected fixture) |

Interaction with **RL-EXPORTS** (program owner item; `rl_exports/` not git-ignored, not swept by `DELETE /profiles`): fixing this bug makes the export write real (redacted) patient text into that directory. Owner (RSI-Q2): RL-EXPORTS lands first, as PR-1 below.

### Task list (ordered; two PRs, serial)

Both RED tests go through HTTP with `tests/support/routes.py::route_client`; neither calls `export_dataset` or `delete_profile` as a function (the existing `tests/test_profile_deletion.py` calls `delete_profile` directly, so it cannot see this). Each test must fail on the branch's starting tree before the fix; paste that red output.

**PR-1 — RL-EXPORTS** (`fix(privacy): ignore and erase per-profile RL exports`)
1. RED: `route_client(profiles_router, "/profiles", profile_id=P)`; seed `<tmp>/profile_P/grpo_rewards.jsonl` and `<tmp>/profile_Q/…` with `api.feedback._DEFAULT_EXPORT_DIR` monkeypatched to `<tmp>`; `DELETE /profiles/P` → 204, `profile_P/` gone, `profile_Q/` untouched. Pass a real master session or patch `_load_profile_for_delete` / `authenticate_profile` as `test_profile_deletion.py` does, but send the request over HTTP.
2. RED: `git check-ignore -q --no-index src/backend/rl_exports/profile_x/a.jsonl` → rc 0 (rc 1 on main).
3. GREEN: one `.gitignore` line; in `delete_profile`, `shutil.rmtree(_DEFAULT_EXPORT_DIR / f"profile_{profile_id}", ignore_errors=True)` after the crypto-erase commit point, reusing the existing constant (no new config). Correct `api/profiles.py:799-803`.
4. Collected = start + 2; update the CLAUDE.md / AGENT.md slots (SLOT-RULE).

**PR-2 — RL-EXPORT-EMPTY** (`fix(feedback): derive prompt_snapshot from the preceding user turn`), after PR-1 merges
1. RED: seed a `ChatSession` with user turn (index 0) and assistant turn (index 1) in the profile DB; `route_client(feedback_router, "/feedback")` with `get_profile_db_session` overridden (precedent `tests/test_agent_cache_isolation.py:64`); `POST /feedback/turns/{assistant_turn_id}` with no `prompt_snapshot`; then `POST /feedback/export` → `grpo_rewards.jsonl` has 1 row whose prompt is the (redacted) user text. Red on main (0 rows).
2. RED: assistant turn with no preceding user turn → feedback accepted, row skipped on export (no 500).
3. GREEN: in `upsert_feedback` (`api/feedback.py:188`), when `body.prompt_snapshot` is None, load the `ChatTurn` with same `session_id` + `profile_id`, `turn_index = assistant.turn_index - 1`, `role == "user"`. No migration (`models/chat_session.py:70` has the columns). `model_name` / `provider` stay NULL.
4. Collected = start + 2; slots updated. Redaction is untouched: `rl_dataset._redact` already runs on export; `modules/redaction.py` diff must be empty.

## 4. Owner answers (2026-10-10)

| Q | Answer | Effect |
|---|---|---|
| RSI-Q1 fix design | **Server copies prior turn** | PR-2 step 3 |
| RSI-Q2 order | **RL-EXPORTS first** (git-ignore + cleanup on profile delete) | PR-1 before PR-2 |
| RSI-Q3 telemetry headline | **Agent runs, cache hits, abstain rate** lead; TPM only for legacy LLM calls | RSI-TEL, RSI-TEL-UI scope |
| RSI-Q4 MMR sense 2 | **Passive diversity metric** (diversity@k, unavailable without embeddings, after W-8 + RSI-AUDIT PASS); re-rank unplanned | RSI-MMR scope; RSI-MMR-RERANK dropped |

Still open: `metrics_enabled` gate placement (RSI-TEL), eval-score storage (RSI-EVAL).

## 5. Merge position

This pack: after #60 (both edit `docs/capstone-report/implementation-program.md`; rebase onto main and re-run the docs gates). #68 lands after #58, #60, #64, #65; sequence is in the #68 PR comment.
