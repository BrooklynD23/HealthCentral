# Owner gates, wave 1111I (four questions, one AskUserQuestion prompt)

Plan: `2026-11-11-batch-1111i-plan.md` (same folder). Base `origin/main` `89c3811e`. Each question carries its options; the first option is the Recommended one.

---

## RESTORE-FAIL-PURGE (row MEM-PURGE-RESTORE-FAIL)

**Question.** A restore closes the profile's vault before it touches any file. When the restore then fails partway (the vault and key files were already replaced from the backup) or fails outright, the profile's cached exports stay in memory. After PROFILE-MEMORY-PURGE, so do its page pictures and cached answers. Today only a successful restore clears them. Should every restore outcome clear them once the vault closes?

| Option | What happens |
|---|---|
| **(a) Clear as soon as the vault closes, every outcome (Recommended)** | The clear moves to just after the vault closes, so success, partial failure, failure and a restore that errors out all clear memory. A refused restore (wrong password, wrong phrase, corrupt backup) closes nothing and still keeps them (pinned by HC-ERP-003). |
| (b) Clear on partial failure only | Partial failure is the case where the data changed. A plain failure keeps the pre-restore exports in memory while the vault is closed. |
| (c) Leave it | A failed or partial restore keeps them in memory until the next lock, logout or expiry. |

Why (a): closing the vault is a lock in effect, and MEM-PURGE (a) already said a locked profile keeps no decrypted content in memory. It is one moved line in `api/backup.py`; the audit rows and error texts are unchanged.

---

## RECOVER-AUDIT-WORDING (row RECOVER-AUDIT-PRE-ROTATE)

**Question.** Recovering with a recovery code writes the audit row "recovered" with "recovery_rotated: true" and commits it before the recovery code is actually rotated (the order you chose in RECOVER-ORDER-COMMIT). If the rotation then fails, the request returns an error, the new password works, the old code still works, and the audit row says the code was rotated. Change the wording?

| Option | What happens |
|---|---|
| **(a) Stop claiming it in the first row (Recommended)** | The "recovered" row records only "password_reset: true". The rotation is recorded by the second row ("recovery code generated, after recovery"), which is written only after the rotation succeeds. Nothing else in recovery changes. |
| (b) Write "recovery_rotated: false" first, then true on the second row | The same truth, with one more field to read. |
| (c) Leave it | On a rotation failure the audit trail overstates what happened. |

Why (a): the audit trail then never claims a step that did not run, the order you chose stays exactly as it is, and the change is one line in `api/profiles.py` (auth code, hence this question). A test-strength concern raised on the same code (HC-RECOV-030b) turned out to be covered by HC-RECOV-030 (measured), so it needs no change.

---

## TEST-RESET-ORDER (row TEST-RESET-PARTIAL)

**Question.** The Playwright-only "reset synthetic test profile" route (404 in production) deletes the profile's document files before it commits the database reset. If that commit fails, the files are gone and no audit row is written. The only reorder that keeps the current tests produces the opposite half-state (database reset, files left, no audit row). What should happen?

| Option | What happens |
|---|---|
| **(a) Leave it; close as accepted (Recommended)** | No change. The route only runs for synthetic Playwright profiles; a retry, which Playwright setup does anyway, completes either half-state. |
| (b) Commit first, then delete files; on a file failure after the commit, write a "partial" audit row | A failed commit deletes nothing, and a later file failure is audited as partial. One existing test (HC-RESET-041, "no audit row on failure") is re-pinned to allow the partial row. |

Why (a): it is a test-only route with no patient data; (b) touches `api/profiles.py` and changes a pinned audit rule for little gain.

---

## DISCLAIMER-APPEND (row DISCLAIMER-GUARD-QUIRK)

**Question.** The safety guard adds its standard disclaimer only when an explanation has none of its three disclaimer signals (the word "consult"; the words "healthcare provider", "doctor" or "physician"; the words "educational" or "informational"). It then requires two of the three. So an explanation with exactly one signal, for example "Your healthcare provider can review it.", gets no disclaimer added and is withheld (the patient sees the "talk to your clinician" card instead). No built-in text triggers this today (measured: every seeded card passes), and existing tests already pin the behaviour. Change the guard?

| Option | What happens |
|---|---|
| **(a) Leave the guard; close as known (Recommended)** | No change to the medical-safety module. A one-signal text keeps being withheld, which fails safe. Built-in texts keep two signals, as the existing tests require. |
| (b) Add the disclaimer whenever fewer than two signals are present | Such cards show with the standard disclaimer appended instead of being withheld. It edits `interpret_safety.py`, and two tests that use a one-signal text to force a withhold need a new fixture. It would get its own plan. |

Why (a): the quirk only withholds, it never lets unsafe text through, and no built-in text triggers it (knowledge rows a user edited were not measured). (b) is a medical-safety change with no current patient-visible case.
