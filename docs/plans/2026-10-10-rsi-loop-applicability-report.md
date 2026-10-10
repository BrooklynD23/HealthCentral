# RSI-Loop Applicability Research Report

**Date:** 2026-10-10 · **Status:** Research findings, no code changes · **Method:** 10 parallel read-only research agents (industry landscape + 9 repo domains), synthesized below.

> **Re-based 2026-10-10 on `origin/main` @ `eb7de28`.** The first draft was measured on `docs/p0b-plan-set`, 339 commits behind main. All `file:line` refs below were re-measured on main; the stale "notification_scheduler never started" finding was dropped (P2 wired it, `main.py:82-91`). Baseline on main: 1381 collected; `recurring-failures.md` holds 10 modes. Since W-5 (D11), `[cite:N]` is the validated citation marker and `[YOUR_RESULTS:N]`/`[REFERENCE:N]` are context labels.

> Repo vocabulary note: the repo's term is **"self-improvement loop"** (`docs/features/04_self_improvement_loop.md`), not "RSI". All proposals below extend that doc's framing rather than introducing a second loop concept.

## Executive summary

Asclexis is already ~3/4 of an RSI loop. Mapped onto rsi-loop's Observe→Analyze→Fix→Verify:

| Stage | State | Evidence |
|---|---|---|
| **Observe** | Strong | `audit_logs` stream (per-route + per-agent-node), `MetricsCollector` ring buffer + `/api/v1/monitoring/metrics`, `ResponseFeedback` rows, `RunLog` steps |
| **Analyze** | Strong | guard gates (advice/groundedness/confidence), `validate_response` + VerifierAgent + FaithfulnessScorer, 74-case golden eval scorer (6 axes) |
| **Fix** | Weakest | every fix is human-triggered (reprocess, verify/edit), narrow (adaptive reminder windows), or offline (RL export dead-ends at JSONL). **No mechanism turns a scored bad outcome into a changed behavior automatically — even behind approval.** |
| **Verify** | Present but pre-send only | guard node, `is_valid` gate, deterministic `graph.replay`, CI eval gate. Nothing verifies a *change* improved subsequent outputs (no post-change regression check, no score trend). |

**What the industry actually ships** (from landscape research): three tiers — (a) ops-level loops tuning routing/retries/thresholds (clawinfra/rsi-loop — alpha, JSONL outcome log + heuristic clustering + health score; ~200 lines to vendor/reimplement), (b) behavior-level loops improving prompts/skills/policies (Reflexion, Voyager, Dream-RSI), (c) code-level self-rewriting (AlphaEvolve, Darwin-Gödel Machine). Only (a) and gated slices of (b) fit a local-first medical app; (c) is a hard no (needs sandbox + objective evaluator + compute; self-modifying code violates the safety posture).

**Bug found during research:** `ResponseFeedback.prompt_snapshot`/`model_name`/`provider` are never populated in production → `POST /feedback/export` produces three empty JSONL files. Tests can't see it (they inject `prompt_snapshot` directly and call handlers as functions). New instance of recurring-failure mode #1 — see §8.

## 1. Industry landscape (what transfers)

| Framework | Loop | Maturity | Borrows cleanly? |
|---|---|---|---|
| **clawinfra/rsi-loop** (Apache-2.0, alpha) | JSONL outcome records → heuristic error clustering (rate_limit/timeout/empty/context_loss, recurrence ≥3) → safe-auto-fix table → recency-weighted health score | Shipping, alpha | Yes — the whole design is local-shaped: append-only log + watch-dir + non-LLM analysis. Its fix categories map onto our config knobs (timeouts, top_k, memory caps). It is telemetry + triage, **not** self-modification |
| **Dream-RSI** (arXiv:2609.14858) | logged discovery tree → exact replay simulator → offline policy eval → redeploy winner | Research | Partially — "replay logged traces to A/B a prompt/retrieval change against the golden set" is already half-built via `tests/agent/eval_harness.build_vault` |
| **AlphaEvolve / DGM** | LLM mutates code → objective evaluator → evolution archive | Production (DeepMind infra) / Research | No — needs machine-checkable `evaluate()` + sandbox + compute a GGUF desktop lacks; code self-rewriting conflicts with "never weaken a safety check" |
| **Reflexion / Self-Refine** | verbal self-critique into memory / generate→critique→refine | Research, zero infra | Yes — patterns work on small local LLMs |
| **STaR/ReST** | keep only correct rationales → fine-tune | Research | Partially — maps onto existing `rl_dataset` DPO/GRPO export; retrieval-time reuse needs no training |
| **OTel GenAI conventions** | standard span taxonomy (`invoke_agent`, `execute_tool`, token-usage events) | Development | Yes — free schema for the Observe layer |

**Universal shape across all of them:** append-only outcome log → offline analyzer → gated change mechanism (auto only for provably-safe knobs) → score tracked over time. The differentiator is never the loop shape — it's evaluator quality and the safety gate on what may change. Asclexis already has the best-gated pieces (golden evals, HITL verification, audit allowlists); what's missing is aggregation and the proposal leg.

## 2. Existing in-repo assets (the skeleton)

22 loop-like mechanisms cataloged. Load-bearing ones:

- **Agent graph** `plan→act→reflect→(loop|draft)→guard→terminal` (`modules/agent/graph.py:145-235`) — fully deterministic today; **no LLM call on the agent path** (`nodes/draft.py` composes templates).
- **Guard node** (`guardrails/guard.py:68-206`) — advice→groundedness→confidence→audit; emits `agent.guard` with `gate_fired`/`dropped_count`.
- **Verification loops with human gate** — `POST /observations/{id}/verify` snapshots `original_value_json` (`api/observations.py:381-430`); entity rejections persist and survive reprocess (`api/documents.py:1147-1236`); care-task candidates are computed-on-read, accept re-derives server-side.
- **Feedback** — `POST /feedback/turns/{id}` upserts rating/tags/correction per turn (`api/feedback.py:182-257`); `GET /feedback/stats` is flat counts only — no clustering, no persistence, no health score.
- **Scheduled-job precedent for an Analyzer** — `modules/backup_scheduler.py:94-206` (lifespan task, honest `skipped_locked`, per-failure isolation); `notification_scheduler` follows the same shape (`main.py:82-91`).
- **Eval gate** — `modules/agent/eval/scorer.py` `ScoreReport` (6 axes, absolute bars) → `scripts/agent_eval_gate.py` in CI. Scores land on **stdout only** — `model_dump_json()` is serializable-ready, persistence is one line away.
- **`docs/features/04_self_improvement_loop.md`** — stages 1–2 (capture, export) shipped; 3–4 (fine-tune, redeploy) aspirational; §6 skill-rewriting with "safety modules never auto-rewritten" gate. **RSI work = closing a gap the docs already name** — clean capstone narrative.
- **`docs/agentic/recurring-failures.md`** — a curated postmortem ledger = rsi-loop "Analyze" output in doc form; every entry ends with a command-answerable recheck. Currently maintained by hand; nothing is machine-readable (no IDs, no last-seen, no failure→test linkage).

## 3. Gap analysis (what a working loop needs)

| Gap | Detail |
|---|---|
| **Observe is incomplete** | `prompt_snapshot`/`model_name`/`provider` never written → exports empty (§8 bug). `RunLog` discarded after `run_agent` returns; `ChatTurn` has no `run_id`/`terminal`/`served_path` — a turn can't be joined to its audit rows or feedback. Cache hits short-circuit with **no audit event** (`api/assistant.py:702-704`). Agent-node `tokens` param accepted then dropped (`modules/agent/metrics.py:26`). |
| **No aggregate analyzer** | `audit_logs` are write-only — nothing reads them back. `/feedback/stats` is flat. No clustering of negative turns by tag×model, no recurring-failure detection, no extraction-correction analytics. |
| **No proposal seam** | Safe knobs exist (`RAGModule.SYSTEM_PROMPT`, planner keyword tables `nodes/plan.py:123-162`, `top_k`, memory caps, `normalize_question`) but nothing proposes changes to them. Precedent for the approval seam: `UserModelSettings` + `api/model_settings.py` PATCH pattern — proposals as DB rows, explicit accept. |
| **No health score** | Eval bars are binary absolute (==1.0/==0); degradation inside the pass band is invisible. No score persistence → no trend → no rsi-loop-style health score per subsystem. |
| **No post-change verify** | No A/B or replay of logged traces against a candidate config. `graph.replay` exists but nothing persists to replay in production. |
| **No consumer of exports** | No trainer script reads `rl_exports/*.jsonl`; fine-tuning is a documented manual/placeholder step. |

## 4. Patient-facing proposals (in-product loops)

All follow Observe→Analyze→**propose**→human-approve→Verify. None touch `interpret_safety`/`redaction`/`faithfulness`/`verifier_agent`.

| Rank | Proposal | Loop in one line | Effort / Risk |
|---|---|---|---|
| 1 | **Data-health score** (`GET /insights/data-health`) | % verified, undated-obs count, extraction-confidence trend → actionable deep-links to workbench/reprocess → score recomputed on read | Low / Low — pure read-aggregation; mirrors `check_verification` counts-not-values precedent |
| 2 | **Correction analytics** (`modules/correction_analytics.py`) | diff `original_value_json` vs current by field/analyte → "dates misread on 40% of rows" card → user clicks reprocess → re-verify | Med / Med — needs new insights endpoint; observe side already persisted |
| 3 | **Feedback triage** | cluster `rating=-1` by tag×model×provider → patient-facing nudges ("answers lacked verified results — N unverified" → workbench; "too_technical" → propose memory item) | Low-Med / Low — stats endpoint exists, adds grouping + nudges |
| 4 | **Memory hygiene review** | flag stale/duplicate/injection-filtered `MemoryItem`s → merge/delete suggestions via existing CRUD | Low / Low |
| 5 | **Personal analyte alias table** | verified `analyte_raw`→canonical pairs → per-profile `analyte_alias` overlay consulted before `_synonym_to_canonical` → optional re-normalize on approve | Med-High / Med — new profile migration + normalizer overlay; highest patient value (trend fragmentation) |
| 6 | **Unit-conflict resolver** | surface obs excluded by unnormalizable units (`excluded_count`) → user edits unit → trend gains the point | Med / Low-Med — needs workbench edit modal widened (currently only `value`/`value_text`) |
| 7 | **Entity-rejection learning** | rejection rate per `(category, entity_type, extraction_version)` → "review carefully" banner / suppress always-rejected proposals | Med / Med — suppression must stay reversible |
| 8 | **Med-reconcile adoption outcomes** | persist accept/dismiss counts keyed by `suggestion_type` (not drug names) → tune suggestion classes | Med-High / Med — respects deliberate no-auto-apply design |

Cross-cutting prerequisites the agents surfaced: (a) `NormalizeModule` has no DB extension path despite the "extendable via database" comment — proposal 5 builds it; (b) the workbench edit modal only edits `value`/`value_text` though the verify endpoint accepts `unit`, `ref_*`, `collected_at` — widening it unblocks 2 and 6.

## 5. Dev-process proposals (RSI for the agents that build this repo)

The repo already runs a *manual* O→A→F→V loop: session notes/progress.md = Observe, `recurring-failures.md` + Codex review rounds = Analyze, skills + gates = Fix, CI = Verify. The missing stage is **machine-recorded session telemetry** — every existing artifact is hand-typed prose.

| Rank | Proposal | Notes |
|---|---|---|
| 1 | **Session-log hook** — PostToolUse/SessionEnd hook appending `tool_name, file_path, session_id, exit codes, test red/green counts` to `.claude/logs/session-log.jsonl` (git-ignored, so the hook never dirties a tree — failure mode #5) | **Shipped** (owner HOOKS-COMMIT, 2026-10-10): `.claude/hooks/session_log.py` + committed `.claude/settings.json`, metadata only (no file content, command text or output), tests `tests/test_session_log_hook.py` |
| 2 | **Evidence-required lint** — `feature_list_lint.py`: `completed` requires non-empty `evidence` field | Already specced (`02-harness-techniques.md:155`); turns "no claim without a command" into a gate |
| 3 | **Weekly failure-miner routine** — read-only job grepping session-log for test-fail→fix→refail loops and ask-first-file touches → proposes `recurring-failures.md` entries | Reuses the doc-drift routine chassis (`docs/plans/2026-09-27-nightly-doc-drift-routine-spec.md`); proposes, never applies |
| 4 | **Recurrence counter** — `last_seen:` field per recurring-failures entry; miner bumps it → per-subsystem health score as lint-able markdown | The Verify leg for *process* fixes — currently nothing checks a failure mode stopped recurring |
| 5 | **Wave-report telemetry fields** — extend L1 report template (`orchestration.md:70`) with review-loops-used / re-failed-commands / tokens | Prose-paste not API plumbing (local-first weighting); Devin-side needs manual paste-back |

Pitfall the loop must itself avoid: session health scores must record environment + tree state, or they reproduce failure modes #4/#5 (env-dependent results, gates run in contaminated trees).

## 6. LLM telemetry dashboard — feasibility

**Answer: yes, and it's the cheapest item on this list.** A `components/settings/LlmTelemetryCard.tsx` in SettingsPage's right column (precedent: `BackupCard`, "Current Status" card `SettingsPage.tsx:634`), zero routing changes.

Current reality:
- `InferenceResult` carries only `tokens_generated` — no prompt tokens, no duration, no provider (`core/model_runner.py:42-47`). Callers drop even that.
- **Providers already return everything:** llama.cpp `usage` dict has prompt/completion tokens (`llama_cpp_provider.py:246` reads one field, drops the rest); Ollama returns `prompt_eval_count`, `eval_count`, `eval_duration`, `total_duration`, `load_duration` (`ollama_provider.py:211` keeps one). `Llama.timings` never accessed.
- `MetricsCollector` (10k-slot ring buffer, `monitoring/metrics.py`) + `GET /api/v1/monitoring/metrics` (`metrics_enabled` gate, `RequireAuth`, **zero frontend consumers**) already exist.
- `psutil` is already a dep; Ollama `/api/ps` gives per-model VRAM; `GET /settings/model/provider` exists (no frontend hook).

Minimal sketch (8 files):
1. `monitoring/metrics.py` — `record_llm_call(provider, model, prompt_tokens, completion_tokens, duration_ms, finish_reason, cache_hit)` on a second ring buffer (don't shoehorn into `RequestRecord`)
2. `core/model_runner.py` — record in `generate`/`generate_async` (the choke point)
3. `core/external_runner.py` — needs its own hook (bypasses the facade); must preserve W-6's audit-before-dispatch and fail-closed behavior (PR #32, D12)
4. `modules/agent/cache.py` — hit/miss counters
5. `api/model_settings.py` — `GET /telemetry` (provider/model/loaded, tpm, rpm, avg/p95, rss_mb, cache hit-rate; `RequireAuth`, non-PHI counts only)
6. `services/modelSettings.ts` — `useLlmTelemetry` with `refetchInterval` (precedent: `useDownloadProgress`, 2s)
7. `components/settings/LlmTelemetryCard.tsx` — Badge rows + small recharts `LineChart` (**recharts ^3.9.1 already installed**)
8. `tests/` — route test via `route_client` (never call handlers directly)

Two honest caveats:
- **Agent path never calls the LLM** — draft composes deterministically, so TPM/RPM will read ~0 for agent-served chats. The card must surface *agent runs*, *cache hits*, and *legacy-path LLM calls* as separate series or it will look broken.
- Persistence: in-process only = zero PHI on disk, lost on restart. If history is wanted → master DB table (system-level, not profile PHI), one `migrations/master/` revision.

**"MMR" resolved (user decision 2026-10-10):** MMR means BOTH — model memory footprint (RSS/VRAM via psutil + Ollama `/api/ps`) AND maximal-marginal-relevance for the RAG retrieval pipeline. Note: MMR is not implemented anywhere in `src/` today (grep `mmr|marginal_relevance` = 0 hits) — the RAG item is a *build* (passive metric vs. gated re-ranking), not just a gauge. Sent to adversarial review via `docs/plans/2026-10-10-rsi-audit-handoff-prompt.md`.

## 7. What NOT to do (invariant check)

- No self-modifying code or auto-rewritten safety modules — `interpret_safety`, `redaction`, `faithfulness`, `verifier_agent`, guardrails semantics stay human-owned (`04_self_improvement_loop.md:104` already encodes this).
- No network telemetry — "no telemetry" is a hard product rule (C-LOCAL-1); all Observe data stays on-device.
- Auto-apply only ever for provably-safe knobs (timeouts, top_k, toggles); anything touching prompts/safety = draft proposal + human approve. rsi-loop's own docs make the same split.
- Never lower eval bars or the 0.7 embedding threshold to make a score look better.
- Master DB only for any persisted system-level telemetry — never profile DBs (not patient data, avoids dual-chain complexity).

## 8. Bug discovered during research (action needed)

**RL export produces empty datasets in production.** `api/assistant.py:276` `_append_turns` stores only role/content; `ExplainAssistant.tsx:208-238` sends no prompt/model/provider; `api/feedback.py:209,228` only copies them from the request body; so `prompt_snapshot`, `model_name`, `provider` are always NULL → every row hits `if not prompt …: continue` in `rl_dataset.py:119` → `dpo_pairs.jsonl`/`sft_positives.jsonl`/`grpo_rewards.jsonl` all empty. Tests inject `prompt_snapshot` directly and call `export_dataset(...)` as a function (`tests/test_rl_feedback.py:301-326`) — the exact pattern `recurring-failures.md` #1 warns about.

**Related open item:** RL-EXPORTS / PRIV-10 (`docs/capstone-report/implementation-program.md:447`) — `rl_exports/` not git-ignored and not swept by `DELETE /profiles` (ask-first, crypto-erase path). Same export path; plan the two serially.

**Fix direction:** snapshot the composed prompt (or at minimum model/provider + message skeleton) server-side at turn persist or feedback-submit time; add an HTTP-level test through `route_client` that exercises feedback→export end-to-end. When fixed, record this instance in `recurring-failures.md` in the same commit.

## 9. Recommended sequencing

1. **Fix the export bug** (§8) — it's broken today; smallest diff, biggest honesty win.
2. **Telemetry card** (§6) — the explicit user ask; ~8 files, all conventions in place.
3. **Data-health score endpoint** (§4 #1) — the patient-facing "health score" that makes RSI visible.
4. **Persist eval scores** — `ScoreReport.model_dump_json()` → JSONL or master table → per-subsystem trend = the Verify substrate everything else needs (feeds pending backlog item HC-M07).
5. **Extend `04_self_improvement_loop.md`** into the canonical RSI spec: absorb §3 gaps, cross-link §4 proposals as new tickets (candidate HC items; correction-analytics isn't ticketed yet).
6. **Session-log hook** (§5 #1) — shipped 2026-10-10 (owner HOOKS-COMMIT).
7. **Fit with the execution program** (`audit/2026-09-25/handoff-2026-09-28-execution-orchestrator.md` §3; W-3, W-7, W-8 not yet merged):
   - Export-bug fix: plan now; serial with the RL-EXPORTS plan.
   - Telemetry: plan now; merge after W-7 (shares `core/model_runner.py`).
   - MMR passive metric (honest name e.g. diversity@k, shows "unavailable" without embeddings): plan after W-8 (bundled embedding model).
   - MMR active re-rank: deferred until W-3 (verified-only RAG, `modules/rag.py`) and W-8 land; must keep `[cite:N]` mapping and golden-eval outcomes stable, behind a flag.
   - Eval-score persistence: after GATE-14 (both touch `scripts/agent_eval_gate.py`).
8. Later/stretch: agent `terminal` audit event + `run_id` on `chat_turns` + persisted `agent_runs` table (enables real `replay()`); feedback-cluster analyzer as a backup_scheduler-shaped lifespan task; LoRA stretch goal per `PHASE_7_lora_stretch.md` (gate: ≥ base on all 4 axes).

**Capstone framing:** `docs/agentic/harness.md` already describes the dev harness as observe→fix→verify; an in-product self-improvement loop is the same loop pointed at patient data quality. "Gate-bounded self-modification in a local-first, safety-gated product" is a legitimate Part-2 original contribution per `capstone-report/research/04-papers-evals.md:440-456` — the Verify substrate (golden evals, HITL workbench, audit allowlists) is the differentiated asset.
