# WEAR-PLANS D1-D8 — Opus adversarial review (substituting for Codex per owner instruction 2026-10-14)

**This is not a Codex review.** Owner instruction 2026-10-14, relayed by L0, verbatim: "Codex failed. Continue with opus in place of Codex". Reviewer: `Agent` `model: "opus"`, `general-purpose`, read-only, adversarial. Focus: the symptom journal's privacy/redaction path, migration ordering (P6 013, G-C1 014, AUDIT-ORDER 015, GAM2 2b), the `garmin-fit-sdk` dependency and licence gate, and the 14-day threshold.
**Target:** `docs/wearables-plans` @ `29d165c` against `origin/main` (`8234990`).
**Response:** [WEAR-PLANS-D1D8-opus-response.md](WEAR-PLANS-D1D8-opus-response.md)

Output verbatim below.

```text
VERDICT: needs-attention

I read all 4 plans, the owner rows, and the source lines each finding cites. I edited nothing and ran no tests.

1. [BLOCKER] docs/plans/2026-10-13-wearables-09-packet.md:195-199 — The OW-W9 gate is written in prose only, so the journal part can ship before the owner answers. Evidence: §1:19 says "the journal part of 09a/09b does not start until the owner answers OW-W9". The Status line (:6) and Task 0 (:195-199) never check OW-W9. Tasks 1-4 build the journal wiring and tests 906, 915 and 924-931 in the same 09a PR. tickets.md:49 weakens the gate to "risk acceptance before M4". — fix: add a Task 0 STOP on the OW-W9 owner row. Split 09a into 09a-metrics and 09a-journal, with the journal fields, preview route, tests and journal allow-list only in 09a-journal. Make tickets.md:49 a blocker for 09a-journal.

2. [HIGH] docs/plans/2026-10-14-wearables-15-symptom-journal.md:216,238 — Plan 15 contradicts its own §0, and following the acceptance criteria literally breaks HC-AUD-004. Evidence: §0:19-21 requires 4 `ALLOWED_ACTIONS` strings plus 4 action_map entries in `core/audit.py`. These lines still say the opposite:
   - §1:32 "does NOT license any edit to core/audit.py"
   - §2:63 says the fallback needs "no core/audit.py edit"
   - §5:124 "No new vocabulary: the action falls back"
   - HC-WRB-1512 (:171) asserts "an action equal to the event type"
   - Task 4 :216 and §10 :238 require `git diff --stat ... core/audit.py` to print nothing
   - §14 Q3 :267 is stale

   An implementer who meets the acceptance criteria must skip the OW-W11 diff, which breaks HC-AUD-004 (`tests/test_audit_phi_minimization.py:140-185`) or forces an exemption (recurring-failures #9). — fix: rewrite those 7 sites to the §0 design. 1512 asserts `row.action in ALLOWED_ACTIONS`. The Task 4 and §10 diff check expects exactly the OW-W11 lines in `core/audit.py` and an empty diff for `redaction.py`.

3. [HIGH] docs/plans/2026-10-14-wearables-15-symptom-journal.md:244 — Deleted journal text survives in generated packets, so "they exist nowhere else" is false. Evidence: `_packet_store` (`api/export.py:48`) has no expiry and no purge. It is written only at :801 and read at :842, and profile reset/delete never clears it. G-C1's `014_export_artifacts` persists visit_prep packets as `payload_json` in the profile DB (`docs/plans/2026-09-27-W11b-roadmap-items-gc1-gc4.md:431`). That text has passed strict redaction, but names written in sentences are still in it. Copy J11 (:145) says "This cannot be undone" and implies the entry is gone. — fix: in 15 §12 and §11, state that packets keep the snapshot text. On journal PUT/DELETE, drop preview snapshots holding that id, and add a test for it. Raise the G-C1 interaction as a refresh item, and reword J11 or have the owner accept the gap under OW-W8.

4. [MEDIUM] docs/plans/2026-10-13-wearables-09-packet.md:88 — `_journal_preview_store` keeps redacted PHI in memory with no bound. Evidence: expiry is "not expired (15 min)" and is checked only when a preview is used. There is no sweep, no per-profile cap and no single-use pop. Profile delete/reset does not purge it. :20 still says "Nothing is stored", which contradicts the snapshot design. — fix: on each insert, purge expired snapshots and cap at N per profile. Pop the snapshot on successful packet generation and purge it on profile reset/delete. Test 915 adds "reuse after success → 400" and "store size after 20 previews". Fix the wording at :20.

5. [MEDIUM] docs/plans/2026-10-13-wearables-09-packet.md:174,182 — HC-WRB-920 and 929 assert on a patched `log_export_event`, so they cannot fail on the real audit path. Evidence: `create_audit_log` scrubs details against `ALLOWED_DETAIL_KEYS`, and `metrics_included` is absent today (`core/audit.py:89-110`), so a scrubbed-away key passes the test. The preview route returns entry text but the plan never says whether it goes through `audit_and_commit` before responding, so a failed audit could still return text. The action becomes "Exported data" (`core/audit.py:466`) for a preview that exports nothing. — fix: write rows to a real master DB, the 15's HC-WRB-1510 pattern. Assert the persisted `details_json` holds `metrics_included`, `item_count` and `count`. Add a 1511-style test where `audit_and_commit` raises: the preview returns 500 with no text. Decide the action string and get owner sign-off.

6. [MEDIUM] docs/plans/2026-10-13-wearables-09-packet.md:149,151 — No packet test pins the 14-day threshold (WEAR-D3). Evidence: only 20 days (901) and 3 days (903) are tested. The program (:160) requires the 13/14 boundaries, and plans 07 (705) and 08 (809) have them. A packet route that passes a literal 7, or uses `>`, stays green. — fix: add a pure 13-vs-14 boundary test. Add an HTTP test that seeds 13 days and asserts C12 renders "at least 14", which proves the route passes `settings.wearables_min_days`.

7. [MEDIUM] docs/plans/2026-10-13-wearables-11-garmin-parser.md:139 — The 11b sub-plan cannot be executed as written. Evidence:
   - §0 (:17-22) has no task list, RED/GREEN steps or rollback for 11b.
   - Task 0 item 4 (:139) says "If any metric is FIT-only, STOP and ask", which contradicts §0's route to 11b.
   - HC-WRB-1104 (:113) and mutation 3 require `.fit` members never to be opened, which 11b must break, and nothing says how 1104 gets scoped.
   - The acceptance line "16 passed" (:157) conflicts with "start + 17" (:158).

   — fix: add 11b tasks:
   - Task 0: the `WEAR-FIT-LIC` row is on main, the exact `==` pin, and a check that the wheel supports Python 3.11 and is pure-python.
   - Confirm the dependency installs and `pip-audit` passes in the `.github/workflows/ci.yml` 3.11 jobs.
   - Re-scope 1104 to out-of-scope FIT members, delete item 4, and fix the counts.

8. [MEDIUM] docs/plans/2026-10-13-wearables-11-garmin-parser.md:128 — HC-WRB-1119's socket patch does not prove the parser stays offline. Evidence: it patches `socket.socket` and `create_connection` during the parse only. `garmin_fit_sdk` is imported at module load, before the patch, so import-time I/O goes unseen. `from socket import socket` aliases, `getaddrinfo` and `subprocess` are not covered. It also exercises only one synthetic file's code path. Supply chain is weak too: `requirements.txt` has 0 hashes, so "version ≥2 weeks old" is the only control. — fix:
   - Import or reload `modules.wearables.garmin_fit` inside the patched context, and also patch `socket.getaddrinfo` and `subprocess.Popen`.
   - Add a static scan of the installed package's `.py` files for `socket`, `urllib`, `http.client`, `requests` and `subprocess` imports.
   - Record the wheel's sha256 and confirm zero transitive dependencies in the PR.

9. [MEDIUM] docs/plans/2026-10-14-wearables-15-symptom-journal.md:102,160 — The migration numbers in the other plans collide with the wearables "next free number" rule, and nothing tests for a single Alembic head. Evidence:
   - G-C1 hard-codes `PREV_HEAD=013_fk_cascade_alignment` and `NEW_HEAD=014_export_artifacts`, and says STOP if another PR is open (W11b:396, :471, :889).
   - AUDIT-ORDER fixes `015`'s `down_revision` to P6 then G-C1 (`docs/plans/2026-10-09-AUDIT-ORDER.md:249`).
   - If WEAR-02 or 15 lands first, those literals go stale.
   - HC-WRB-1501 asserts the downgrade lands on "WEAR-02's" revision, which is wrong once any other migration merges between WEAR-02 and 15.
   - `get_heads` appears only in `core/migrations.py:158,315`, and no test asserts a single head. Two branches whose migration files have different names merge without a git conflict unless both also edited the head literals.

   — fix: add an owner-ordered migration ledger row covering P6, G-C1, AUDIT-ORDER, GAM2-2b, WEAR-02 and WEAR-15. In 1501, downgrade to the `down_revision` read from the migration file. Add a test asserting `len(ScriptDirectory.from_config(profile_cfg).get_heads()) == 1`.

10. [LOW] docs/plans/2026-10-13-wearables-09-packet.md:169,184 — Deleting an entry after previewing it is untested. Evidence: 915 and 931 cover a bad or expired preview_id and an edit after preview, but not a delete after preview. Packet generation re-reads only to compare `updated_at`, while the snapshot keeps the text. — fix: add to 931: preview, DELETE the entry, generate → 404 with no packet stored.

11. [LOW] docs/plans/2026-10-14-wearables-15-symptom-journal.md:137 — Copy J3 can be false when 15b ships. Evidence: J3 says "You choose which entries go into a doctor-visit packet." 15b depends only on 15a, WEAR-10 and OW-W8, while the journal-in-packet feature waits on OW-W9 and may never ship. — fix: drop J3's second sentence until 09a-journal merges, or make 15b depend on it.

Next action: rewrite plan 15's 7 contradictory sites from finding 2 to match §0, then add the OW-W9 STOP to plan 09 Task 0 (`docs/plans/2026-10-13-wearables-09-packet.md:195`).
```
