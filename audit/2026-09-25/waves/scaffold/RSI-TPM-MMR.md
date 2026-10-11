**GATED** — plan only, not approved. RL-EXPORT-EMPTY is a confirmed live bug (owner item below); telemetry, MMR and eval-score persistence are BLOCKED behind W-7, W-8 (+ W-3) and GATE-14.

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

## 2. Phases

| ID | Kind | Scope | Depends on (hard; *soft*) | Stop gates (owner) | Measured acceptance | Sign-off |
|---|---|---|---|---|---|---|
| RSI-AUDIT | DOCS (review) | Run the #68 handoff Phase A (ground-truth the claims) and Phase B (adversarial review of both MMR senses), `VERDICT: PASS\|REVISE` | #68 merged | none (read-only) | PASS verdict file under `audit/2026-09-25/swarm-2026-09-27/reviews/` | owner reads verdict |
| RL-EXPORT-EMPTY | PRODUCT (bug) | Populate `ResponseFeedback.prompt_snapshot` so `POST /feedback/export` writes rows | **RL-EXPORTS** (security row; see §3); *W-4, W-3* (share `api/assistant.py`) | RSI-Q1 (design), RSI-Q2 (order) | HTTP test via `route_client`: chat turn → feedback → export → `grpo_rewards.jsonl` has 1 row; red on main | owner merge |
| RSI-TEL | PRODUCT | Telemetry plumbing: `record_llm_call` in the existing `monitoring/metrics.py` (`MetricsCollector`), hooks in `ModelRunner` + `ExternalModelRunner`, cache hit/miss counters, `GET /settings/model/telemetry` (`RequireAuth`, counts only, no PHI) | **W-7** (shares `core/model_runner.py`); keeps W-6 fail-closed `external_runner.py` | RSI-Q3 (headline); `metrics_enabled` gate in or out (handoff B1) | route test over HTTP; counters move on a stubbed call; no new network call | owner merge |
| RSI-TEL-UI | PRODUCT (frontend) | `useLlmTelemetry` in `services/modelSettings.ts` + `components/settings/LlmTelemetryCard.tsx` on SettingsPage (recharts already installed) | RSI-TEL | none beyond RSI-Q3 | vitest for the card incl. "agent path: 0 LLM calls" state | owner merge |
| RSI-MMR | PRODUCT | Sense 1: memory gauge on the card. Sense 2: passive diversity@k metric, shows "unavailable" without embeddings. Active re-rank stays out | RSI-TEL-UI; **W-8** (bundled embeddings); RSI-AUDIT PASS | RSI-Q4 | flag off ⇒ retrieval order and agent golden set (74) identical | owner merge |
| RSI-MMR-RERANK | PRODUCT (deferred) | Lambda-tunable re-rank behind a default-off flag | **W-3**, **W-8**, RSI-MMR; overlaps G-C5 (HC-M11 cross-encoder) | new owner row; `[cite:N]` map must be unchanged (D11) | flag off byte-identical; flag on keeps the `[cite:N]` → source map | not planned |
| RSI-EVAL | PRODUCT | Persist `ScoreReport` (master DB only, never profile DBs) + per-subsystem health score | **GATE-14** (shares `scripts/agent_eval_gate.py`) | storage choice (JSONL vs master table) | gate run appends 1 record; collected = start + new tests | owner merge |

Hard deps not on `origin/main` today: W-7, W-3, W-8, W-4 (`git log origin/main --oneline --grep=<id>` → no merge commit); GATE-14 is an owner item. P5 is merged (PR #54; `git grep -c time_source_lint origin/main -- .github/workflows/ci.yml` → 1).

## 3. RL-EXPORT-EMPTY evidence (verified on `origin/main` `eb7de28`)

**Verdict: CONFIRMED.** No production path writes `prompt_snapshot`.

| Step | Location | What happens |
|---|---|---|
| Frontend payload | `src/frontend/src/pages/ExplainAssistant.tsx:209-217`, `:230-238` | sends `session_id, rating, response_text, feedback_tags, correction_text` only; no `prompt_snapshot`, `model_name`, `provider` |
| API | `src/backend/api/feedback.py:209-210`, `:228` | copies `prompt_snapshot` from the request body only; nothing derives it |
| Chat persistence | `src/backend/api/assistant.py:276` `_append_turns` | stores turns (role, content); does not touch `ResponseFeedback` |
| Other writers | `git grep -n -E 'prompt_snapshot\s*=' origin/main -- src/backend ':!*tests*'` | only `api/feedback.py:210`, `:228`, `:374` (a read) |
| Export | `src/backend/modules/rl_dataset.py:116`, `:120-121` (GRPO), `:167-168` (DPO), `:217-218` (SFT) | `if not prompt …: continue` skips every row → 3 empty JSONL files |
| Why tests are green | `src/backend/tests/test_rl_feedback.py:46`, `:183` inject `prompt_snapshot`; `:301-336` call `export_dataset(...)` as a function | recurring-failures #1 (no HTTP, injected fixture) |

Interaction with **RL-EXPORTS** (program owner item; `rl_exports/` not git-ignored, not swept by `DELETE /profiles`): fixing this bug makes the export write real (redacted) patient text into that directory. Land RL-EXPORTS first or in the same PR.

Smallest fix (proposal, RSI-Q1): in `upsert_feedback`, when the body has no `prompt_snapshot`, read the preceding user `ChatTurn` (same `session_id` + `profile_id`, `turn_index - 1`, `role == "user"`) from the profile DB. `ChatTurn` already has those columns (`models/chat_session.py:70`), so no migration. `model_name` / `provider` stay NULL (the export does not require them; stats already show "unknown").

## 4. Owner questions

1. **RSI-Q1 (fix design).** A. Server derives `prompt_snapshot` from the preceding user turn **(recommended: one function, no migration, does not trust client text)**. Downside: a second copy of the prompt lives in `response_feedback`. B. Frontend sends it. Downside: client-controlled training data, two call sites.
2. **RSI-Q2 (order).** A. RL-EXPORTS (git-ignore + profile-delete sweep) lands first **(recommended)**. Downside: the export stays empty longer. B. Same PR. Downside: a security fix rides inside a bug fix.
3. **RSI-Q3 (telemetry headline).** A. Lead with agent runs, cache hits and abstain rate; TPM/RPM for legacy LLM calls only **(recommended: truthful, TPM reads 0 on the agent path)**. Downside: more series on one card. B. TPM/RPM headline. Downside: looks broken in normal use.
4. **RSI-Q4 (MMR sense 2).** A. Passive diversity@k, named honestly, "unavailable" without embeddings, after W-8 and RSI-AUDIT PASS; re-rank not planned **(recommended)**. Downside: no retrieval-quality change this program. B. Plan flag-gated re-rank now. Downside: collides with W-3 in `modules/rag.py` and risks the `[cite:N]` map.

## 5. Merge position

This pack: after #60 (both edit `docs/capstone-report/implementation-program.md`; rebase onto main and re-run the docs gates). #68 lands after #58, #60, #64, #65; sequence is in the #68 PR comment.
