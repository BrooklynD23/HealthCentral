# Agentic Project Roadmap

Why this project exists as an agentic-engineering exercise, and what "done well" looks like. The working loop is in [harness.md](harness.md); verification is in [evals.md](evals.md); the live task inventory is [feature_list.json](../../feature_list.json).

## Goals

1. **Production-grade product engineering** on a real, safety-sensitive domain: local-first health data organization, trend visualization, and source-grounded explanation — explicitly *not* diagnosis, treatment, or dosing (see [ai-safety.md](../compliance/ai-safety.md)).
2. **Modern agentic workflow as a first-class skill**: orchestrator + scoped subagents (`.claude/agents/`), evidence-gated progress, CI eval gates, and MCP/tool discipline. Industry usage research (Anthropic, 2026) shows the division of labor settling as humans making planning decisions and agents making execution decisions, with work shifting toward deployment, operation, and documentation — this repo is built to practice exactly that split.
3. **Data Science rigor**: measurable extraction quality, golden-set evals with tracked metrics, data-quality tests, and eval cards rather than anecdotes.

## Why this is portfolio-relevant

| Skill signal | Repo artifact |
|--------------|---------------|
| Agent orchestration | `.claude/agents/`, [harness.md](harness.md) |
| Harness engineering | [feature_list.json](../../feature_list.json), [progress.md](progress.md), CI eval gates (`scripts/agent_eval_gate.py`) |
| Data Science | extraction golden sets and eval cards (planned: HC-M06), RL dataset export pipeline |
| SWE production readiness | CI (tests, type-check, e2e, security gate), release checklist, observability baseline (planned: HC-M07/M08) |
| AI safety | 4-axis agent eval gate, `modules/interpret_safety.py` adversarial tests, redaction pipeline, planned injection/PHI-leakage corpus (HC-M05) |
| Healthcare judgment | Non-diagnostic boundary, [docs/compliance/](../compliance/README.md) privacy-by-design suite |

## Milestones

Near-term (verified state as of 2026-07-07 — HC-M01…HC-M04 complete):

1. **Consistent runtime baseline** — Python 3.11+, Node 22+ everywhere, enforced by grep-able policy and CI. *(done)*
2. **One-click Windows bootstrap** — dev.ps1 auto-installs Python via winget with graceful fallback. *(done)*
3. **Documented agent harness** — this directory + feature inventory. *(done)*

Next (ordered; details and verification in `feature_list.json`):

4. **Adversarial eval expansion (HC-M05)** — prompt-injection corpus (instructions embedded in uploaded documents / memory items) and PHI-leakage probes on export paths, wired into the CI eval gate. Existing base: ~58 golden cases scored on groundedness / citation / abstention / advice-leakage.
5. **Extraction eval card (HC-M06)** — synthetic labeled lab-PDF golden set; precision/recall on analyte, unit, and date extraction with versioned metrics. This is the flagship Data Science artifact.
6. **Observability baseline (HC-M07)** — structured logs with request IDs, audit-coverage tests, local-only metrics (no telemetry; local-first is an invariant).
7. **Distribution (HC-M08)** — installable desktop build verified on a clean Windows VM.
8. **Narrow agent tools (HC-M09)** — credential-free script tools per [mcp-tools.md](mcp-tools.md).

Reported by subagent survey and worth verifying before scheduling (evidence not yet confirmed by the orchestrator): RL dataset export may use `standard` rather than `strict` redaction (lab values/dates survive into training exports), and production faithfulness scoring is rule-based with no NLI model wired despite scaffolding for one. Both would slot in around milestone 4 if confirmed.

## Brand risk (flagged for owner decision)

"HealthCentral" is an existing public health-media brand (healthcentral.com). Treat the current name as an internal codename; clear or replace it before any public release (tracked as HC-M10). No user action is needed for private development.
