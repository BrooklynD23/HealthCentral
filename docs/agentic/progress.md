# Agent Progress Log

Session-by-session record of agent work: what changed, what was verified, what failed, and the next priority. This supplements git history with verification evidence — it does not replace it. Newest entries first.

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
