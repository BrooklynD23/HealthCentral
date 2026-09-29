# Wave 6 shared rules (integration pass, 2026-09-28)

Repo: /mnt/c/Users/DangT/Documents/GitHub/HealthCentral, branch `docs/p0b-plan-set` (snapshot commit 5d56557).
Refs: main 40f590e · A = origin/claude/asclexis-repo-audit-349pjq 692fdf3 · B = origin/claude/healthcentral-agentic-research-r1n54x 7b2ff1f.

Inputs (read these):
- audit/2026-09-25/swarm-2026-09-27/ledger.md — orchestrator ledger + RESUME POINT
- audit/2026-09-25/swarm-2026-09-27/wave3/3a-integration.md — collision/order audit (5 BLOCKER, 12 MAJOR, 13 MINOR) + §3 gate register + §5 program deltas
- audit/2026-09-25/swarm-2026-09-27/wave3/3b-evidence.md — evidence/number audit (10 MAJOR, 12 MINOR) + §2 matrix/contract deltas + §3 new rows
- audit/2026-09-25/swarm-2026-09-27/reviews/ — Codex review archive (<ID>-rN-codex.txt = reviewer output, <ID>-rN-response.md = author response)

Rules:
1. DOCS ONLY. Never edit product code, tests, CI, CLAUDE.md, AGENT.md, docs/INDEX.md, docs/agentic/*. Never regenerate INDEX.md.
2. Edit ONLY the files you own (listed in your prompt). If a finding needs an edit elsewhere, list it under "Handoffs" in your report — do not make it.
3. Never sign an owner gate. Register/reference gates by their canonical IDs from 3a §3 (P0-B2, D9-SRC, P1-DRIFT, SLOT-RULE, W4-EXPEDITE, P7-ROUTE, GOV-BG, GOV-D11, BG-REACH, P8-B2-ORDER, SQL-ECHO, EXPORT-QUESTIONS, D4-EXPORTS, VERIFIED-FALLBACK, EMB-REV, CI-SEED, P0-D-MOOT, INTERP-UNVERIFIED, MSG-UNVERIFIED, AUD-INTERP). Keep state labels: proposed / owner-approved / owner-gated. The only approvals are in docs/capstone-report/owner-decisions-2026-09-27.md and the ledger "OWNER:" lines.
4. Verify before applying. 3a/3b and Codex are leads, not truth. Re-check each cited line with `git show <ref>:<path> | sed -n` or grep before editing. If a finding is wrong or stale, don't apply it; say why.
5. Surgical edits. Change only the lines a finding targets. No reformatting, no rewording of adjacent text.
6. Do NOT run the backend test suite or anything that imports the backend (it silently downloads from HuggingFace and can write to the developer's real master DB). Read-only git/grep/sed only. `python3 scripts/docs_lint.py` is allowed.
7. Do NOT git add / commit / stash / switch branches. The orchestrator commits.
8. Codex reviews: round 4 is final (owner: "No round 5"). Do not start new Codex runs. For an unanswered round, write `<ID>-rN-response.md` next to it, mirroring prior response files: per finding → accepted+fixed (with plan line) / rejected (with evidence).
9. Write your report to audit/2026-09-25/swarm-2026-09-27/wave6/<your-agent-id>.md AND return it. Report = table: finding ID → applied / not applied (reason) / handoff (target file+owner) · then files changed · then new owner gates surfaced.
