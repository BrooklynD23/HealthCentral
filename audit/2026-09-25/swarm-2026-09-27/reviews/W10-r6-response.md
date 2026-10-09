# W-10 Codex round 6 — L1-C response (2026-10-08)

Reviewed: the plan at `648240a` (r5 amendments plus the round-5 fixes). Last round allowed (2 per amendment set).
Runner and model: as round 5 (`codex-companion.mjs task --fresh`, no `--write`; configured `gpt-6-luna` at `xhigh`; runtime reported "GPT-6 / HIGH").
Read-only check: `git status --short` and `git rev-parse HEAD` were identical before and after the job (`?? …/W10-r6-prompt.md`, `648240a`).

Verdict: **REVISE** (0 BLOCKER, 5 MAJOR). The five round-5 fixes were not re-raised. Each new finding was checked against the files.

| # | Finding | Check | Disposition |
|---|---|---|---|
| 1 | [MAJOR] DP-5 says the prompt is redacted before it is sent, without the break-glass exception | True: `core/external_runner.py:252-257` forces strict only when `redaction_bypass_active()` (`:95-109`) is false; under break-glass the prompt goes out with weaker or no redaction (`:259-279`) | ACCEPTED. DP-5 now starts "Unless break-glass is active (see the PHI redaction bullet below), the prompt is redacted at `strict` before it is sent." |
| 2 | [MAJOR] HC-2 names profile deletion as the sole exception to insert-only audit rows; a whole-install restore replaces the master DB | True: `scripts/backup.py:505-521`, copy loop `:570-599` (the master DB is skipped only when `profile_id` is set), CLI `:763-774`. The API restore is profile-scoped and holds the master back (`api/backup.py:364`, `:440`) | ACCEPTED, wording changed, not stopped. HC-2 no longer says "only … with one exception"; it lists both paths and says the database does not enforce immutability. Codex proposed stopping under S9. L1 judgement: the owner row W10-HIPAA asks for the line "to match the code", the new sentence adds a second true fact and removes a claim, and nothing in it needs a new decision. **Flagged to L0 as a judgement call.** |
| 3 | [MAJOR] Task 1 Step 3 still pipes pytest through `tail -3` | True | ACCEPTED. Full output goes to a scratch file and the exit code is printed |
| 4 | [MAJOR] A6/A7/A8 accept any P/U/I status, so the script can pass with the wrong variant | True | ACCEPTED. `--variants=<W-2>,<W-3>,<W-6>[:<sha>]` is part of `W10_ARGS`; new assertions A6v, A7v, A8v require exactly the measured status wording (and the sha for U / I). The script now has 12 assertions; RED on the unpatched tree is `2/12` (measured) |
| 5 | [MAJOR] F1 checks DP-5 phrases anywhere in the file; F3 checks fragments | True | ACCEPTED. F1 reads only the "Optional External API" subsection and checks the three sentence anchors; F3 compares the complete HC-1 row |

These five fixes land after the last allowed plan round, so no plan round re-reviewed them. The Codex diff review of the finished branch (step 8) covers the resulting text.
