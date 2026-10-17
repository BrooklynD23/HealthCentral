# Handoff Prompt — RSI-Loop Research Audit & MMR Adversarial Review

**To:** higher-reasoning review agent (audit → adversarial review → wave planning)
**Repo:** `/mnt/c/Users/DangT/Documents/GitHub/HealthCentral` (Asclexis — local-first, privacy-first medical desktop app; FastAPI `src/backend/`, React `src/frontend/`, per-profile SQLCipher DBs, local LLM via `core/model_runner.py`)
**Authority order:** `CLAUDE.md` + `AGENT.md` > `docs/00_architecture_plans_index.md` > this prompt.
**Base:** `origin/main` @ `eb7de28` or later. Measure everything on that tree — never on a stale local branch (the first draft of the report was measured 339 commits behind main).
**Mode:** read-only audit. Change nothing. Verify by running commands and quoting actual output — never assert. If a check is skipped, name it and why.

## Context

A 10-agent research sweep produced `docs/plans/2026-10-10-rsi-loop-applicability-report.md`, mapping Recursive Self-Improvement (RSI) loops (rsi-loop's Observe→Analyze→Fix→Verify, Dream-RSI, AlphaEvolve) onto this repo. Its verdict: Observe/Analyze strong, **Fix weakest** (every fix is human-triggered or dead-ends at JSONL), Verify pre-send-only. It proposes: a user-facing LLM telemetry card (TPM/RPM + memory + MMR-for-RAG), patient-facing improvement loops, dev-process session telemetry, and reports one live bug (§8 of the report).

Your job: **Phase A** audit the synthesis against ground truth → **Phase B** adversarially review the two MMR items → **Phase C** (PASS only) produce implementation waves. This repo has prior review rounds under `audit/2026-09-25/` using a `VERDICT: PASS|REVISE` contract — match it.

## Phase A — Audit the synthesis

Primary source under review: `docs/plans/2026-10-10-rsi-loop-applicability-report.md`. It was built from subagent output — treat every `file:line` citation as a claim to verify, not a finding. Spot-check ≥10 of the §2 mechanism catalog refs, then verify these load-bearing claims:

1. **BUG CLAIM (highest priority):** `ResponseFeedback.prompt_snapshot`, `model_name`, `provider` are never populated in production → `POST /feedback/export` yields three empty JSONL files.
   - Trace: `ExplainAssistant.tsx` feedback payload → `api/feedback.py` upsert handler → `rl_dataset.py` skip conditions (`if not prompt …: continue`) → what `test_rl_feedback.py` injects directly.
   - Confirm or refute with file:line evidence. If confirmed, this is a new instance of recurring-failure mode #1 (green suite can't see it) — say so.
2. **"Agent path never calls the LLM"** — `modules/agent/nodes/draft.py` composes deterministically; no `model_runner` reference anywhere in `modules/agent/`.
3. **RL-EXPORTS / PRIV-10 overlap:** confirm the §8 bug fix and the open RL-EXPORTS item (`docs/capstone-report/implementation-program.md:447`) touch the same feedback→export path, and say whether they should be one plan or two serial plans. (The earlier "`notification_scheduler` never started" claim was stale and is withdrawn — P2 wired it, `main.py:82-91`.)
4. **Telemetry claims:** `InferenceResult` lacks prompt_tokens/duration; llama.cpp `usage` and Ollama `eval_*`/`total_duration` fields are read-then-dropped; `MetricsCollector` is in-memory only; `agent.<node>` metrics drop the `tokens` param; `/api/v1/monitoring/metrics` exists with `metrics_enabled` gate + zero frontend consumers; `recharts` in `src/frontend/package.json`.
5. **Missing-mechanism claims:** no health score anywhere; `ScoreReport` written to stdout only; nothing consumes `rl_exports/*.jsonl`; `audit_logs` are write-only; `ChatTurn` has no `run_id`/`terminal`; cache hits emit no audit event.
6. **Doc claims:** `docs/features/04_self_improvement_loop.md` stages 1–2 shipped / 3–4 aspirational; `docs/agentic/recurring-failures.md` holds exactly 10 modes; `.claude/settings.json` is uncommitted/gitignored (check `.gitignore`, `ls .claude/`); PostToolUse hook spec at `docs/capstone-report/research/02-harness-techniques.md:75`; pending backlog items HC-M06/M07/M11 in `feature_list.json`.
7. **Command-checkable:** `cd src/backend && python -m pytest tests/ --collect-only -q` — does the collected count match the 1381 baseline in `CLAUDE.md`? Verify any grep counts the report cites.

**Output:** `| # | Claim | Verdict PASS/FAIL/PARTIAL | Evidence (file:line or command output) |` — then list claims found wrong or overstated, claims unverifiable, and any NEW recurring-failures.md-mode instance surfaced while auditing.

## Phase B — Adversarial review: the two "MMR" items

User decision (2026-10-10): **MMR means BOTH** — model memory footprint AND maximal-marginal-relevance for the RAG pipeline.

### B1 — Memory telemetry (attack)

- `psutil.Process().memory_info().rss` measures the *whole backend process*, not just the loaded model — honest to present as "model memory"? What's the honest label?
- Ollama `/api/ps` per-model `size`/`size_vram` — accurate? Behavior when no model loaded / provider = `template`?
- Per-poll probe overhead; should `/telemetry` live inside or outside the `metrics_enabled` gate?

### B2 — MMR for RAG (attack both designs)

MMR is implemented nowhere in `src/` today. Candidates: **(a) passive metric** — observe-only relevance/diversity score over retrieved chunks; **(b) active re-ranking** — retrieval order actually changes (lambda-tunable).

Attack vectors — investigate each against real code:

- **Embedding dependency:** MMR needs query + candidate embeddings. What embedding model exists locally — bundled, optional download (`scripts/download_models.py`)? `test_api_rag_index_002b` fails without one — so embeddings are NOT guaranteed. What does the metric do when absent: silent NaN, hidden row, or honest "unavailable"?
- **Citation stability:** since W-5 (D11, PR #34) `[cite:N]` is the validated citation marker; `[YOUR_RESULTS:N]`/`[REFERENCE:N]` are context labels (`modules/rag.py`). Does re-ranking change the `[cite:N]` → source map between what the model saw and what the user sees? Trace how citation IDs are assigned and whether re-rank breaks the map.
- **Program collisions:** W-3 (verified-only RAG) edits retrieval in `modules/rag.py`; W-8 bundles the embedding model. Neither is merged. Which MMR design can be planned before they land?
- **Eval determinism:** `agent_eval_gate.py` + 74 golden cases expect specific retrieval/abstain outcomes. Would re-ranking flip them? Does the deterministic agent path retrieve through the same code at all?
- **Metric honesty:** MMR needs a query, candidates, and lambda. For a patient-facing dashboard is it signal or noise? Weigh simpler honest alternatives — redundancy ratio, diversity@k, coverage@k — is "MMR" the accurate name or a borrowed buzzword?
- **Compute:** embedding N candidates per query on CPU-only hardware — cost vs value for single-user desktop.

**Output:** per item — attack list, which design survives (or neither), the honest version of the metric, whether it belongs in the telemetry card.

### B3 — Challenge the dashboard premise

If the agent path never calls the LLM, TPM/RPM read ~0 for agent-served chats. Is a TPM/RPM headline honest, or should the card lead with agent-run / cache-hit / abstain-rate metrics? Recommend the truthful framing.

## Phase C — implementation waves (only if A passes and B verdicts are stable)

Match the repo's wave convention (`docs/plans/2026-09-27-WXX-*.md`: independent waves, test-first, durable break-it controls, acceptance commands). Skeleton — adjust as audit demands:

- **Wave 0** — fix the empty-export bug (prerequisite: broken Observe stage)
- **Wave 1** — telemetry plumbing: `record_llm_call` in `monitoring/metrics.py`, `ModelRunner` + `ExternalModelRunner` hooks (external runner bypasses the facade), cache hit/miss counters, `GET /settings/model/telemetry`
- **Wave 2** — `services/modelSettings.ts` hook + `components/settings/LlmTelemetryCard.tsx` + SettingsPage mount + route test
- **Wave 3** — MMR item per Phase B verdict (passive metric or flag-gated re-rank)
- **Wave 4** — eval-score persistence (`ScoreReport.model_dump_json()` → master DB or JSONL) + per-subsystem health score

These are slots *inside* the execution program (`audit/2026-09-25/handoff-2026-09-28-execution-orchestrator.md` §3), not a parallel track. Respect shared-file order: Wave 0 serial with RL-EXPORTS; Wave 1 merges after W-7 (`core/model_runner.py`) and keeps W-6's fail-closed `external_runner.py` behavior; Wave 3 after W-8 (+ W-3 for any re-rank); Wave 4 after GATE-14 (`scripts/agent_eval_gate.py`).

Per wave list: files touched, tests required (routes via `tests/support/routes.py::route_client` HTTP, never handler-as-function), migration needs (state which Alembic chain), invariant checklist, UAT acceptance commands.

## Hard rules

- Read-only — no code changes, no commits.
- Never propose touching `modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, or guardrails semantics.
- Never propose lowering eval bars or the 0.7 embedding threshold.
- Re-read `docs/agentic/recurring-failures.md` before final verdicts; record any new instance of a listed mode.
- **Final output contract:** `VERDICT: PASS | REVISE` per phase → claims table → attack tables → wave plan (Phase C only on PASS). Write the review to `audit/` per convention or return inline, per orchestrator instruction.
