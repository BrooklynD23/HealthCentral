# 06 — Offline testing and quality tools

**Last Updated:** 2026-10-22
**Owner:** repository owner
**Refresh Trigger:** `.github/workflows/ci.yml` changes a job; a test dependency is added; owner answers Q7 in [07-owner-questions.md](07-owner-questions.md).

> **Point-in-time research (2026-10-22).** Markers as in [00-README.md](00-README.md).

## What exists (at `d2843e8`)

- CI jobs (`.github/workflows/ci.yml`): docs lint, backend tests (pytest + coverage, `--cov-fail-under=74`, no `--cov-branch`), ruff, frontend (tsc, eslint, vitest, build), security scan (bandit, pip-audit, `scripts/security_gate.py`), agent and legacy eval gates, Playwright e2e (chromium), RSI replay.
- Run 39843670560 on main **[A]**: critical path about 14.5 min. backend-tests 7m11s (deps 3m22s, tests 3m30s); e2e 7m05s (pip 4m30s). torch and the requirements are reinstalled in four jobs. Only the npm cache is configured (`ci.yml:104`, `:254`) **[V]**.
- No axe, toHaveScreenshot, Lighthouse, Hypothesis, mutation or schemathesis usage **[A]**.

Weak spots that matter more than new tools (L0 bug list, re-read **[V]**):

- `e2e/ui-full-verification.spec.ts:44-48`: the real-backend suite is `describe.skip` unless `HC_E2E_REAL_PDF` is set or the OS is Windows, so CI never runs it.
- `e2e/document-import.spec.ts:54-57`: E2E-DOC-002 matches `/test-report\.pdf|pending|needs review|parsed/i`, which the filename alone satisfies.
- `tests/test_ocr_bbox.py:141-145` is `assert True`, and `tests/test_extraction_pipeline.py:112-122` is `pass`.

## Tools

| Tool | Licence | Latest | Offline | CI cost | Risk it addresses | Verdict |
|---|---|---|---|---|---|---|
| `@axe-core/playwright` | MPL-2.0 **[V]** | 4.14.0 **[V]** | yes (local Chromium) | low; one spec in the existing e2e job | labels, names, contrast and focus on patient-facing pages | **adopt** (owner Q7) |
| vitest-axe / jest-axe | MIT **[A]** | 0.1.0 (old) **[A]** | yes | near zero | jsdom cannot compute contrast or layout **[A]** | skip |
| Playwright `toHaveScreenshot` | Apache-2.0 (Playwright) | built in | yes | medium: baselines per OS and browser, generated in CI **[A]** | visual regressions | after the showcase |
| Lighthouse CI | Apache-2.0 **[V]** | 0.15.1 **[V]** | only with `upload.target: filesystem`; the default temporary public storage uploads to Google **[A]** | medium | performance scores | defer |
| Hypothesis | MPL-2.0 **[V]** | 6.170.6, 2026-10-22 **[V]** | yes | low | input-space bugs in `extract.py` (numbers, qualifiers, units, dates) | **adopt** (owner Q7) |
| coverage.py `--cov-branch` | Apache-2.0 **[A]** | 7.17.0 **[A]** | yes | near zero | untested branches in verify and export | **adopt report-only**, then set a floor; do not lower the 74% line floor |
| mutmut | BSD-3-Clause **[V]** | 3.8.0, 2026-09-12 **[V]** | yes | high on the whole backend; fork-based, WSL on Windows **[A]** | tests that cannot fail | post-MVP, scheduled, scoped to `extract.py` |
| cosmic-ray | MIT **[A]** | 8.7.0 **[A]** | yes | higher than mutmut | same | not preferred |
| Stryker (vitest runner) | Apache-2.0 **[V]** | 10.0.0 **[V]** | yes | high | same for the frontend | post-MVP |
| schemathesis | MIT **[V]** | 4.32.4, 2026-10-22 **[V]** | yes, against the local app | medium (triage) | status codes and auth on every route | post-MVP; `route_client` tests first |
| pip-audit | Apache-2.0 **[A]** | 2.10.1 **[A]** | **no**: queries the PyPI or OSV APIs; no offline DB documented **[A]** | already in CI | — | keep as is |

## Recommendation (value per effort)

1. Fix the tests that cannot fail first: run the non-PDF part of the UI-full suite in CI with a committed synthetic PDF, and make E2E-DOC-002 assert a backend status.
2. Hypothesis property tests on the `extract.py` value, unit and date parsers.
3. One `@axe-core/playwright` spec over Inbox, Verify, Trends, Explain and Export.
4. `--cov-branch` in report-only mode.
5. CI caches: `setup-python` `cache: pip`, plus `actions/cache` for `~/.cache/huggingface` and `~/.cache/ms-playwright`. An estimated 2-3 min saved per job **[U]**; measure on one PR.

## Sources

- https://registry.npmjs.org/@axe-core/playwright/latest ; https://playwright.dev/docs/accessibility-testing ; https://github.com/dequelabs/axe-core-npm
- https://github.com/chaance/vitest-axe ; https://playwright.dev/docs/test-snapshots
- https://registry.npmjs.org/@lhci/cli/latest ; https://github.com/GoogleChrome/lighthouse-ci/blob/main/docs/configuration.md
- https://pypi.org/project/hypothesis/ ; https://hypothesis.readthedocs.io/en/latest/
- https://coverage.readthedocs.io/en/latest/branch.html
- https://pypi.org/project/mutmut/ ; https://github.com/boxed/mutmut ; https://pypi.org/project/cosmic-ray/
- https://stryker-mutator.io/docs/stryker-js/vitest-runner/ ; https://pypi.org/project/schemathesis/ ; https://github.com/pypa/pip-audit
