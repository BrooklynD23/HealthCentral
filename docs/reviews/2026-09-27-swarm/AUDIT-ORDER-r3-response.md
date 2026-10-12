# AUDIT-ORDER — Codex round 3 response

**Last Updated:** 2026-10-09
**Plan:** `docs/plans/2026-10-09-AUDIT-ORDER.md` (PR #56), reviewed at `f21e724`. The plan text is identical to `f141edd`. The code was measured at `98bd3c7`, and `git diff --name-only 98bd3c7 eb7de28 -- src/backend` is empty.
**Why round 3:** the owner approved the plan with "Approve, re-review first" (relayed by L0). Scope: plan §12, the round-2 and security-review diff (`317f613..f141edd`), the Option B relay match rule, and whether the combination D + AO-FAIL A + AO-SCOPE B + AD-DENIALS D-B holds together and can be tested.
**Runtime:** `gpt-6.1-sol` returned HTTP 400 ("not supported when using Codex with a ChatGPT account"). The review ran on `gpt-6-luna` with `model_reasoning_effort=high`. Prompt: `AUDIT-ORDER-r3-prompt.md`. Output: `AUDIT-ORDER-r3-codex.txt`.
**Verdict received:** REVISE, 1 BLOCKER and 2 MINOR.
**Result:** all 3 accepted after checking each against the plan text, all 3 fixed. Nothing was rejected, and no BLOCKER is still open.

| # | Sev | Finding (short) | Verified | Disposition | Where fixed |
|---|---|---|---|---|---|
| 1 | BLOCKER | HC-AUD-ORD-003 expects `started` + `completed` on every irreversible route, but row 27 writes no `completed` row (the tombstone is its completion marker) | plan HC-AUD-ORD-003 (§6 Option A tests) vs the row 27 note in Option D. As written, the test could not pass for row 27, or it would push an implementer to add a `completed` row that carries the erased profile id | **Accepted, fixed** | Option D **Tests**: row 27 is excluded from HC-AUD-ORD-003, and its success case is HC-AUD-ORD-007. Same class, found by the author: rows 26 and 27 have no profile-DB transaction (§3), so their HC-AUD-ORD-002 injects the failure into the file operation (`backup.py:442`, `profiles.py:882`) |
| 2 | MINOR | §12 item 3 says only option C leaves multi-transaction partial states unaudited. The approved D also uses C on reversible multi-transaction routes | plan §6 commit-boundaries table; Option D scope (rows 1, 22 and 25, and the first-generation branch of 19/20/23, fall under C) | **Accepted, fixed** | §12 item 3 now names the C branches of D. The owner accepted this risk by choosing AO-SCOPE B |
| 3 | MINOR | The B relay's four-field match could accept a conflicting row with a different `action` or `details_json` | Option B "Idempotent relay" text | **Accepted, fixed** | The match now covers the full persisted payload: `event_type`, `action`, `entity_type`, `entity_id`, `profile_id`, `details_json`, `client_info`. §12 item 5 updated. B is not chosen and D does not depend on the relay |

## Sign-off recording: not done

L0 asked for three edits that record the owner's approval:
1. Mark the §8 Q5 AO-ASKFIRST lines for `core/audit.py` and `core/auth.py:278-286` as SIGNED 2026-10-09.
2. Set the plan status to "approved for execution after r3".

The permission classifier blocked the status edit because it records owner consent that arrived through an agent message, not from the owner directly. The plan therefore still reads PROPOSED / UNSIGNED. The owner or L0 records the signatures directly.

No safety check, threshold or validation is weakened. No file under `src/` was edited.
