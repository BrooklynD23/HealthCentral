# WEAR-PLANS D1-D8 — Opus review (substituting for Codex per owner instruction 2026-10-14)

**This is not a Codex review.** Owner instruction 2026-10-14, relayed by L0, verbatim: "Codex failed. Continue with opus in place of Codex". Reviewer: `Agent` `model: "opus"`, `general-purpose`, read-only, native-style plan review.
**Target:** `docs/wearables-plans` @ `29d165c` against `origin/main` (`8234990`), concentrating on `ad8e191` (owner answers WEAR-D1..D8 applied) and `29d165c` (Codex r3 fixes).
**Note:** the Codex r3 runs on `ad8e191` did complete (exit 0); their verbatim output and response stay in [WEAR-PLANS-r3-codex.md](WEAR-PLANS-r3-codex.md) and [WEAR-PLANS-r3-response.md](WEAR-PLANS-r3-response.md). This Opus review replaces Codex for this round as instructed.
**Response:** [WEAR-PLANS-D1D8-opus-response.md](WEAR-PLANS-D1D8-opus-response.md)

Output verbatim below.

```text
VERDICT: needs-attention

1. [P1] docs/plans/2026-10-14-wearables-15-symptom-journal.md:32 — The plan contradicts itself on `core/audit.py`. §0 (:17-21) and §4 (:85) require 4 new `ALLOWED_ACTIONS` strings, 4 event→action map entries and an HC-AUD-004 extension. The rest of the plan still forbids or ignores that work. Evidence:
   - §1 (:32) says the plan does not license "Any edit to `core/audit.py`".
   - :63 and :124 keep "No new vocabulary: the action falls back to the event type".
   - The HC-WRB-1512 row (:171) is still the fallback version.
   - Task 4 (:216) and acceptance (:238) require `git diff --stat ... core/audit.py` to print nothing.
   - No Task step adds the vocabulary. §3 (:65-81) lists neither `core/audit.py` nor `tests/test_audit_phi_minimization.py`.
   - §14 Q3 (:267) still asks whether WEAR-02 should add `log_wearable_event` to HC-AUD-004, but WEAR-02 HC-WRB-216 already does.

   An L1 that follows the checklist either STOPs or ships a diff that fails its own acceptance. — fix: Rewrite :32, :63, :124, :171, :216 and :238 to match §0. Add the vocabulary + HC-AUD-004 step to Task 2. Add both files to §3. Delete Q3.

2. [P2] docs/plans/2026-10-13-wearables-09-packet.md:178 — HC-WRB-925 expects 404 on the packet when B sends A's entry id. Under §5's check order (:86), an id list without a valid `journal_preview_id` returns 400 (C27) before the 404 id check. B cannot get a preview for A's id, because the preview route returns 404. So the packet call can only return 400. — fix: Make 925 expect 400 (C27) on the packet and 404 only on the preview. Or move the foreign-id 404 ahead of the preview check in §5 and say so.

3. [P2] docs/plans/2026-10-13-wearables-09-packet.md:6 — §1 (:19) and program M4 (`00-program.md:63`) say the journal half waits for OW-W9 and WEAR-09 otherwise ships metrics only. The plan never says how that works. Evidence:
   - Status (:6) does not mention OW-W9.
   - Task 0 (:195-199) does not check it.
   - Counts (:188, :217, :247) fix the total at start + 31, which includes the journal tests 915 and 924-931.
   - The tickets make 09a depend on 15a unconditionally.

   — fix: Add an OW-W9 check to Task 0. Define a metrics-only 09a with its own test subset and count (drop 915, 924-931 and the journal parts of 918-920). Make 15a a dependency only of the journal part.

4. [P2] docs/plans/2026-10-13-wearables-13-patient-export.md:18 — WEAR-D7 was "(a) Add to /export/json now", which the owner's own note glosses as "Wearable data portable from day one". Plan 13 builds an opt-in `?include_wearables=true` with no UI (:157: "No UI exists for the parameter"; it does not touch `ExportPage.tsx`). The frontend call `services/export.ts:141` (`apiGet('/export/json', params)`) never sends the parameter, so a patient's normal JSON export still has no wearable rows. Its own owner follow-up (:161, "confirm the opt-in envelope") is missing from the program §10 queue and the tickets. — fix: Add an OW item to program §10 and the tickets for the opt-in envelope, or add a 09b/ExportPage checkbox to WEAR-13's scope.

5. [P2] docs/plans/2026-10-13-wearables-00-program.md:49 — A10 still describes the rejected default. It says "the route passes `upload.file` to `zipfile.ZipFile` directly" and "D6 chooses between accepting that and streaming…". That contradicts A5b (:44: raw body, `request.stream()` to an app-owned temp file, never multipart), D6 (:163, signed (b)) and plan 06:19. R6 (:142) still says "disclaimer copy matches whichever option is signed". — fix: Rewrite A10 as the signed (b) design (stream to `app_data_path/tmp`, `finally` delete, startup sweep). Drop "whichever option" from R6 and "default" from A5b.

6. [P2] docs/plans/2026-10-13-wearables-11-garmin-parser.md:1 — Stale JSON-only text and a test-count mismatch. Evidence:
   - The title still says "(JSON only)".
   - Evidence row :46 says "JSON-only recommended, FIT not added" and cites `00-program.md:132` (R2) and `:153` (D5). Those are now :138 and :162.
   - Task 5 (:146) says "Collected = start + 16", but acceptance (:158) says "+17 for 11a", and 1101-1117 is 17 tests.
   - The size target is a single M of ~400.
   - Tasks 0-5 have no 11b steps (requirements pin, `garmin_fit.py`, RED/GREEN for 1118-1120).

   — fix: Retitle the plan. Update the :46 row and its line refs. Set Task 5 to +17. Give 11a/11b separate sizes and add an 11b task block.

7. [P2] docs/plans/2026-10-13-wearables-14-docs.md:10 — Line 10 still says "D7 (b) not in patient export", while :76 says WEAR-D7 (a). The Codex r3 fix only reached :76. The TASK_LIST work (:21, :56, :81, :156) and HC-WRB-1407 (:97, `grep "OW-W[0-6]"`, 7 ids) cover only OW-W0..W6, so the new owner items OW-W7..W11 (program §10, :180-184) never reach `docs/features/TASK_LIST.md`. The program (:87) and tickets (:26) give WEAR-14 dependencies "06, 09", yet plan 14's own :9 now documents the WEAR-13 and WEAR-15 routes. — fix: Change :10 to "D7 (a) signed". Extend the rows, the HC-WRB-1407 regex and the count to OW-W0..W11. Add 13 and 15a to WEAR-14's dependencies in the program and tickets.

8. [P3] docs/plans/2026-10-13-wearables-00-program.md:159 — Remnants of the confirmation flag that the r3 server-issued `preview_id` replaced. Evidence:
   - The D2 effect still says "preview + confirmation".
   - Plan 09 :11 says "and an explicit confirmation" and :260 says "explicit confirmation".
   - Task 6 (:227) still adds `journalConfirmed` state and "resets `journalConfirmed`".

   That contradicts 959, where the reset clears `journal_preview_id`. — fix: Replace "confirmation" with "server-issued preview snapshot (`journal_preview_id`)" in all three places. Rename the state to `journalPreviewId`.

9. [P3] docs/plans/2026-10-14-wearables-15-symptom-journal.md:80 — 15b mounts the journal in "WEAR-10 placeholder slot in `pages/WearablesPage.tsx`". WEAR-07b (`07b-review-frontend.md:70`) drops that placeholder and lands earlier (wave WC; 15b is in WD). — fix: Mount the journal as a section after the 07b/08b components. Say 15b edits the post-07b page.

10. [P3] docs/plans/2026-10-13-wearables-09-packet.md:184 — HC-WRB-931 edits the entry through `PUT /wearables/journal/{id}`. The test file only mounts `route_client(export.router, "/export", ...)` (:160), so that route is not reachable there. — fix: Update the row directly in the profile DB in the test, or mount `wearables.router` alongside.

11. [P3] docs/plans/2026-10-13-wearables-10-ui-shell-disclaimer.md:10 — Small stale or garbled lines:
   - Plan 10 :10 and :107 still say "D6 default (b) … if the owner picks (a)", though D6 is signed (b).
   - Plan 10 :5 and `06-import-route.md:5` read "merged, ;" (garbled).
   - Tickets :42 lists OW-W4 suites "07b, 08, 09, 10" and omits 15b; program :177 includes 15b.

   — fix: Mark D6 as signed. Remove ", ;". Add 15b to tickets :42.

Owner answers D1-D8 are quoted verbatim and correctly in program §9 (checked against `c53ba44` rows 161-168). The D3 changes to 14 days are complete in 07, 08 and 09; no 7-day or `symptom_notes` text is left.

Next action: fix finding 1 in `docs/plans/2026-10-14-wearables-15-symptom-journal.md` (§1 :32, :63, :124, :171, Task 4 :216, acceptance :238) before asking for OW-W11.
```
