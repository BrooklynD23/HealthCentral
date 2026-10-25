# Asclexis

**Local-First Medical Results Companion**

A privacy-first desktop application for patients to import medical documents, extract structured information with user verification, visualize trends, and generate grounded explanations with citations. The app, its databases, and model inference run on the user's machine; each profile has its own SQLCipher vault. Outputs are education only: no diagnosis, dosing, or treatment recommendations.

> **Research and educational open-source project. Not professional medical or legal advice, not a medical device, and not for emergencies.** See [Disclaimer](#disclaimer).

What it does, its principles, the system diagrams and the technology stack: [`docs/architecture/overview.md`](docs/architecture/overview.md).

## Quick Start

Windows is the native development environment. From the repository root:

```powershell
.\dev.bat        # one-click launcher (or .\dev.ps1)
```

On WSL/Linux, clone into your Linux home (not under `/mnt/c`) and run `./dev.sh`.

Prerequisites, what the launchers do, model setup, SQLCipher, migrations, tests and manual development are in **[`docs/dev/setup.md`](docs/dev/setup.md)**. End-user instructions are in [`docs/user/getting-started.md`](docs/user/getting-started.md); contributor workflow is in [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Where to find things

| Looking for | Go to |
|---|---|
| Overview, core principles, system diagrams, tech stack, project structure | [`docs/architecture/overview.md`](docs/architecture/overview.md) |
| Full architecture diagram set (backend, pipelines, frontend, CI gates) | [`docs/architecture/README.md`](docs/architecture/README.md) · [performance & scalability review](docs/architecture/performance-scalability-review.md) |
| Developer setup and commands | [`docs/dev/setup.md`](docs/dev/setup.md) |
| Agent / new-contributor briefing, definition of done, skills table | [`AGENT.md`](AGENT.md) ([Definition of done](AGENT.md#definition-of-done), [Skills](AGENT.md#skills)) |
| Behavioural rules and hard invariants (safety, privacy, local-first, redaction, audit, migrations) | [`CLAUDE.md`](CLAUDE.md) |
| Safety and privacy control-flow | [`docs/architecture/pipelines.md`](docs/architecture/pipelines.md) · [privacy boundaries](docs/architecture/overview.md#privacy-boundaries) |
| Compliance posture (HIPAA-aligned design, data privacy, disaster recovery) | [`docs/compliance/README.md`](docs/compliance/README.md) · [`SECURITY.md`](SECURITY.md) |
| Testing, eval gates, recurring failure modes | [`docs/dev/setup.md#running-tests`](docs/dev/setup.md#running-tests) · [CI & quality gates](docs/architecture/ci-and-quality-gates.md) · [recurring failures](docs/agentic/recurring-failures.md) |
| API reference | [`docs/api/README.md`](docs/api/README.md) · [live endpoints](docs/api/endpoints.md) |
| Build program and backlog | [`queue.md`](docs/plans/2026-10-15-build-program/queue.md) · [RUNBOOK](docs/plans/2026-10-15-build-program/RUNBOOK.md) · [contracts](docs/plans/2026-10-15-build-program/contracts.md) |
| Owner decisions | [`docs/capstone-report/owner-decisions-2026-09-27.md`](docs/capstone-report/owner-decisions-2026-09-27.md) |
| Agentic workflow and RSI | [orchestration](docs/agentic/orchestration.md) · [harness](docs/agentic/harness.md) · [evals](docs/agentic/evals.md) · [RSI runs](docs/agentic/rsi-runs/README.md) · [domain skills](skills/README.md) · [process skills](.claude/skills/README.md) |
| Research notes | [`docs/research/`](docs/research/) |
| Capstone report | [`docs/capstone-report/README.md`](docs/capstone-report/README.md) |
| User guides | [`docs/user/README.md`](docs/user/README.md) |
| Every doc | [documentation index](docs/00_architecture_plans_index.md) · [roles index](docs/roles/00_roles_index.md) · [generated flat map](docs/INDEX.md) · [archive](docs/archive/README.md) |

## Current status

- **Backlog:** the build-program [`queue.md`](docs/plans/2026-10-15-build-program/queue.md) is the single execution queue (its header says so). Each planning section ends with a **Ready to build now** line; the newest is under [Planned 2026-10-24, Safety Mode build](docs/plans/2026-10-15-build-program/queue.md#planned-2026-10-24-safety-mode-build), and owner-gated work is under [Owner-blocked and model-machine items](docs/plans/2026-10-15-build-program/queue.md#owner-blocked-and-model-machine-items). This README does not copy queue rows.
- **Latest session handoff:** [`docs/plans/2026-10-24-session-handoff.md`](docs/plans/2026-10-24-session-handoff.md).
- **Remaining-work tracker and session notes:** [`docs/features/TASK_LIST.md`](docs/features/TASK_LIST.md).
- **Test baseline:** the collected backend test count and the known environment-only failures are in [`CLAUDE.md`](CLAUDE.md) and [`AGENT.md`](AGENT.md#commands-windows-is-the-native-dev-environment).

## Documentation Source of Truth

1. `README.md` (this file — repo entrypoint)
2. `docs/api/endpoints.md` (exact mounted API route inventory and auth requirements)
3. `docs/00_architecture_plans_index.md` (full documentation index; see also `docs/roles/00_roles_index.md` for a domain-based entry point)
4. `docs/features/TASK_LIST.md` (remaining-work tracker and session notes; the live build backlog is `docs/plans/2026-10-15-build-program/queue.md`)
5. `docs/05_backend_integration_status.md` (Historical Reference — Sprint 06 snapshot retained for audit context only)

Docs gates (also run in CI): `python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph`
regenerates the index and link graph, and `python3 scripts/docs_lint.py` checks ownership fields,
required sections, canonical-order consistency, links, orphans, and historical banners.

## API Overview

The backend exposes a REST API via FastAPI at `http://localhost:8000/api/v1`. The exact path-level source of truth is [`docs/api/endpoints.md`](docs/api/endpoints.md); router groups, authentication and error codes are in [`docs/api/README.md`](docs/api/README.md).

## License

[TBD]

## Disclaimer

This application is for informational and educational purposes only. It does not provide medical advice, diagnosis, or treatment recommendations. Always consult with qualified healthcare professionals for medical concerns.

- **Research and educational project.** Asclexis is open-source software for people curious about their own health and fitness records who want to track them in one place and build personal software on top of them. It is a research study, not a clinical product.
- **Not professional medical or legal advice.** Nothing it shows, summarizes, or exports is medical advice or legal advice. Talk to a qualified professional before acting on anything it displays.
- **Not a medical device.** It is not cleared or approved by any regulator, and it is not intended to diagnose, treat, cure, monitor, or prevent any disease or condition.
- **Not for diagnosis, treatment, or emergencies.** Do not use it to make treatment decisions. In an emergency, contact your local emergency number.
- **Your data, your risk.** You run it on your own device, with your own data, at your own risk. The software is provided as is, without warranty of any kind.
