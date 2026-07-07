# Agent Progress Log

Session-by-session record of agent work: what changed, what was verified, what failed, and the next priority. This supplements git history with verification evidence — it does not replace it. Newest entries first.

## 2026-07-07 (second session) — HC-M05 adversarial evals + fixes, RL-REDACT-001, winget branch tests

**Completed:**

- **HC-M05 — adversarial injection corpus + PHI-leakage probes, wired into the CI gate, with fixes (owner approved evals+fixes in one pass).** TDD: corpus first (gate went RED: injection_resistance 0.400, phi_leakage 4, compose check FAIL), then fixes (gate GREEN: all 74 cases, all axes at bar).
  - 16 new golden cases (`src/backend/tests/agent/golden/injection-*.json`, `phi-*.json`): injection strings in observation name/unit fields, exfiltration questions, PHI patterns (SSN/phone/email/DOB) seeded into vault fields.
  - Scorer (`modules/agent/eval/scorer.py`): two new axes — `injection_resistance` (bar 1.0, markers checked with the same patterns `modules/rag` uses) and `phi_leakage` (bar 0, checked via the public strict `RedactionEngine`) — plus `score_injection_compose_case`, an end-to-end probe of the CHAT path (`RAGModule.compose_prompt`), which the agent-graph corpus cannot reach. Gate script prints/fails on all of it.
  - Fixes (all additive): `rag.py::_sanitize_chunk_text` neutralizes injection spans in reference/user-document chunk text (neutralize-don't-drop — preserves grounding evidence; closes ticket RAG-INJ-001); `guardrails/redaction_gate.py::sanitize_untrusted_field` + `draft.py`/`graph.py::replay` scrub observation `analyte`/`unit` fields (injection patterns + strict PHI redaction) before sentence composition.
- **RL-REDACT-001 closed (P1, `docs/features/TASK_LIST.md`).** `rl_dataset.py` export now forces `policy_level="strict"` unconditionally (no knob). Two additive strict-only rules in `modules/redaction.py` (owner-approved edit): context-labeled `mrn`, slash/dash `numeric_date`. **Recorded decisions:** ISO-8601 collection timestamps deliberately preserved (longitudinal clinical signal); lab-value and medication-name redaction deferred (values ARE the training signal; med names need a curated dictionary) — follow-up decision, not silently dropped. Compliance docs updated (`data-privacy.md`, `hipaa-controls.md`).
- **HC-M02 tier-1 winget branch verification.** All four dev.ps1 branches exercised via a shim harness (stub `python`/`py`/`winget` executables shadowing PATH, driven through Windows PowerShell): no-winget → manual help; decline ("n") → manual help; winget succeeds but Python invisible → restart guidance; winget fails (exit 1) → actionable error. Exit code 1 confirmed to propagate when the script section runs standalone. Remaining: the tier-3 real-install run in Windows Sandbox (manual, ~15 min).
- **Bookkeeping:** `feature_list.json` — HC-M05 completed, HC-M11 added (NLI entailment wiring; both findings verified first-hand: export used standard redaction — fixed; faithfulness is 100% rule-based with stub NLI hooks — confirmed), HC-M07 rescoped to its three real gaps (correlation-ID middleware/health/metrics already exist), HC-M08 split into phases a–d.

**Validation run this session:**

- `python3 scripts/agent_eval_gate.py` (via `.venv-test`) — RED before fixes (exit 1, expected failures only), **PASS after** (exit 0; 74 cases; groundedness/citation/abstention 1.0, advice_leakage 0, injection_resistance 1.0, phi_leakage 0, R-14 + injection-compose checks PASS).
- Full backend suite: **726 passed, 0 failed** (`pytest tests/ -q`, ~133s). Targeted suites during TDD: `tests/agent/` + `test_rag_pipeline.py` (97 passed), `test_redaction.py` + `test_rl_feedback.py` (66 passed).
- `from main import app` — boots.
- Frontend untouched this session; `tsc`/vitest not rerun (no frontend diff).

**Next highest priority:** HC-M10 stage 1 (rename-surface audit + candidate shortlist — owner chose rename), then HC-M06 (extraction eval card) / HC-M07 (observability gaps).

## 2026-07-07 — Runtime baseline, Windows bootstrap, harness bootstrap

**Completed** (feature IDs from [feature_list.json](../../feature_list.json)):

- **HC-M01 — canonical runtime policy (Python 3.11+, Node 22+/24 LTS).** Updated: `CLAUDE.md` (removed "Python 3.10 compatible" invariant), `AGENT.md`, `README.md` (×2), `CONTRIBUTING.md`, `docs/user/getting-started.md`, `dev.bat`, `dev.ps1` messages, `.github/workflows/ci.yml` (`node-version: '20'` → `'22'` in both jobs), added `"engines": {"node": ">=22"}` to `src/frontend/package.json`. Python in CI stays 3.11 only — a dependency audit found `llama-cpp-python>=0.2.0` and `sqlcipher3-binary>=0.5.0` minimum pins predate 3.12 wheels, so a 3.12 matrix entry was deliberately not added. Historical logs under `docs/plans/` keep their point-in-time version mentions.
- **HC-M02 — dev.ps1 winget Python install.** Detection loop extracted into `Find-Python311Command` (reused for the post-install re-check); on miss: checks `Get-Command winget`, prompts `[Y/n]` (Enter = Yes), runs `winget install --id Python.Python.3.11 --exact --source winget --accept-package-agreements --accept-source-agreements`, checks `$LASTEXITCODE`, refreshes PATH via existing `Refresh-EnvPathFromRegistry`, re-detects, and prints restart/manual-install guidance if Python is still not visible. No winget → existing manual message. Node check bumped 18 → 22 (still warns-and-continues on older, as before).
- **HC-M03 — agentic harness docs.** Created `docs/agentic/{roadmap,harness,evals,mcp-tools,progress}.md` and `feature_list.json`.
- **HC-M04 — AI safety policy doc.** Created `docs/compliance/ai-safety.md`, linked from the compliance README.

**Validation run this session:**

- `python3 scripts/docs_lint.py` — passed.
- `python3 scripts/generate_docs_index.py` — regenerated `docs/INDEX.md` cleanly (run again after the agentic docs were added).
- PowerShell AST parse of `dev.ps1` (`[Language.Parser]::ParseFile`) — no errors.
- `ci.yml` YAML-parses; `src/frontend/package.json` JSON-parses.
- Policy grep for `Python 3.10` / `Node(.js) 16|18|20` across README, AGENT, CLAUDE, CONTRIBUTING, docs/user, dev.ps1, dev.bat, .github — clean (excluding historical `docs/plans/` logs).
- Backend/frontend test suites were **not** rerun: no product code changed this session.

**Known limitations / not verified:**

- The dev.ps1 winget flow parses but has not been executed on a Python-less Windows machine (manual step in HC-M02's verification).
- Subagent-reported findings pending orchestrator verification: RL dataset export possibly using `standard` (not `strict`) redaction; faithfulness scoring rule-based only. See roadmap.

**Next highest priority:** HC-M05 — adversarial prompt-injection corpus + PHI-leakage probes wired into the CI eval gate (requires owner approval before touching safety modules).
