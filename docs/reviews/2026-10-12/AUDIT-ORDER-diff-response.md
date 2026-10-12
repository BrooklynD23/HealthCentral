# AUDIT-ORDER — execution diff review response

**Last Updated:** 2026-10-12
**Branch:** `fix/audit-order`. Reviews: code-reviewer (Opus 5.5) and security-reviewer (Opus 5.5) at `5aa8450`; Codex diff review at `d5ae8e5` (`gpt-6.1-sol` returned HTTP 400 "not supported when using Codex with a ChatGPT account"; ran on `gpt-6-luna`, `model_reasoning_effort=high`). Prompt: `AUDIT-ORDER-diff-prompt.md`. Outputs: `AUDIT-ORDER-diff-codereview.md`, `AUDIT-ORDER-diff-secrev.md`, `AUDIT-ORDER-diff-codex.txt`.

| Source | # | Sev | Disposition | Where |
|---|---|---|---|---|
| CR | 1 | MEDIUM | Accepted, fixed: dynamic-site scan covers every handler's reachable set; a def passed as a call argument counts as dynamic | `d5ae8e5` |
| CR | 2 | MEDIUM | Accepted, fixed: vault-write check requires a commit on the vault session itself | `d5ae8e5` |
| CR | 3 | MEDIUM | Accepted, fixed: break-its committed as tests over a tmp tree (6 cases) | `d5ae8e5` |
| CR | 4 | MEDIUM | Accepted as documentation: fixed window and lost-tail ceiling in the `ponytail:` comment; plan §12 item 8 | `97c042f` |
| CR 5 / SR 1, 2 | — | LOW | Accepted, fixed: counter updated before awaits; failed write frees its slot (HC-AUD-ORD-041b, RED `assert 20 == 0` before) | `97c042f` |
| CR | 6 | LOW | **Rejected:** `audit_rows_purged` counts the `started` row because it is a purged row; the count stays accurate | — |
| CR | 7 | LOW | Accepted: `ponytail:` note on the check-then-act window | `97c042f` |
| CR | 8 | LOW | **Rejected for this PR:** agent rows on the `agent_failed` fallback path are pre-existing and outside AO-SCOPE B | — |
| CR | 9, 10 | LOW | Accepted, fixed: revoke-not-called assertion; batch 001b/002; restore partial ordering | `d5ae8e5` |
| CR | 11 | LOW | Accepted: collected count and §13 checkboxes updated in the PR's last commit | last commit |
| SR | 3 | LOW | **Rejected:** accepted residual, plan §13 decision 4 (no allowlist change in this PR) | — |
| SR | 4-6 | INFO | No action | — |
| Codex | 1 | MINOR | Accepted as documentation: the A2 guard test states it checks presence only; order is pinned per route by HC-AUD-ORD-001a over HTTP. A static ordering check is not added | last commit |

Codex: "The scoped routes' `started` rows precede their first irreversible mutations; I found no PHI or out-of-scope edits." No BLOCKER or MAJOR open.
