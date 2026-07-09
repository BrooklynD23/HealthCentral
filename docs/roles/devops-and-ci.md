# DevOps & CI

**Owner:** Project Lead
**Refresh Trigger:** A CI job is added/removed, or `scripts/docs_lint.py`'s rule set changes

## Scope

GitHub Actions CI pipeline, documentation drift linting (`scripts/docs_lint.py`), repo hygiene checks,
and release process.

## Start here

- [`../../.github/workflows/ci.yml`](../../.github/workflows/ci.yml) — CI jobs: docs-lint, backend-tests, frontend-tests, security scan, agent-eval gate, e2e
- [`../../scripts/docs_lint.py`](../../scripts/docs_lint.py) — doc drift rules (10 checks, see module docstring); `--link-graph` flag emits `docs/_link_graph.json`
- [`docs/agile/RELEASE_CHECKLIST.md`](../agile/RELEASE_CHECKLIST.md) — release process
- [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md) — contribution guide

## Related roles

- [`security-and-compliance.md`](security-and-compliance.md) — the security-scan CI job currently runs with `continue-on-error: true` (bandit/pip-audit)
