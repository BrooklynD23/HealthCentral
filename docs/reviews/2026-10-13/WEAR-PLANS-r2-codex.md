# WEAR-PLANS r2 — Codex adversarial review of the wearables plan set

**Target:** `docs/wearables-plans` @ `e8cce7c` against `origin/main` (`8234990`), after the r1 amendments. 2026-10-13. Codex default model (no model option on `adversarial-review`).
**Response:** [WEAR-PLANS-r2-response.md](WEAR-PLANS-r2-response.md)

Verbatim stdout+stderr of `adversarial-review --wait --base origin/main "<round-2 focus>"`; focus: verify each r1 fix, then remaining defects (isolation, redaction, wording, timezone, hostile files, unreviewed-data paths, audit, migrations, tests that could not fail, ask-first, cross-plan contracts).

```text
[codex] Starting Codex task thread.
[codex] Thread ready (01a1391d-9cb8-7283-881e-b6db21c1f443).
[codex] Turn started (01a1391d-9f07-7e22-bef6-ef60abd50258).
[codex] Assistant message captured: Step 1 of 4: I’m checking the branch diff and Round 1 dispositions, then I’ll trace each acce...
[codex] Running command: /bin/bash -lc 'git status --short --branch && git rev-parse HEAD && git rev-parse origin/main...
[codex] Running command: /bin/bash -lc 'rg -n -i "wear|Asclexis|HealthCentral" /home/danny/.codex/memories/MEMORY.md'
[codex] Command completed: /bin/bash -lc 'rg -n -i "wear|Asclexis|HealthCentral" /home/danny/.codex/memories/MEMORY.md' (exit 0)
[codex] Running command: /bin/bash -lc 'cat docs/reviews/2026-10-13/WEAR-PLANS-r1-response.md'
[codex] Command completed: /bin/bash -lc 'cat docs/reviews/2026-10-13/WEAR-PLANS-r1-response.md' (exit 0)
[codex] Command completed: /bin/bash -lc 'git status --short --branch && git rev-parse HEAD && git rev-parse origin/main... (exit 0)
[codex] Running command: /bin/bash -lc 'rg -n -i "profile|redact|D3|D2|medical advice|timezone|time zone|DST|daylight|...
[codex] Running command: /bin/bash -lc 'git diff origin/main...HEAD -- docs/plans/2026-10-13-wearables-*.md docs/revie...
[codex] Running command: /bin/bash -lc 'cat docs/reviews/2026-10-13/WEAR-PLANS-r1-codex.md'
[codex] Command completed: /bin/bash -lc 'cat docs/reviews/2026-10-13/WEAR-PLANS-r1-codex.md' (exit 0)
[codex] Command completed: /bin/bash -lc 'rg -n -i "profile|redact|D3|D2|medical advice|timezone|time zone|DST|daylight|... (exit 0)
[codex] Command completed: /bin/bash -lc 'git diff origin/main...HEAD -- docs/plans/2026-10-13-wearables-*.md docs/revie... (exit 0)
[codex] Assistant message captured: Step 2 of 4: Round 1 records nine accepted fixes and one partial disposition; I’m checking th...
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-00-program.md | sed -n '1,210p'"
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-02-contract-migration.md | sed -n '1,31...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-00-program.md | sed -n '1,210p'" (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-11-garmin-parser.md | sed -n '1,190p'"
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-02-contract-migration.md | sed -n '1,31... (exit 0)
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-11-garmin-parser.md | sed -n '1,190p'" (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-04-apple-parser.md | sed -n '1,245p'"
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-04-apple-parser.md | sed -n '1,245p'" (exit 0)
[codex] Running command: /bin/bash -lc "sed -n '65,186p' docs/reviews/2026-10-13/WEAR-PLANS-r1-codex.md"
[codex] Command completed: /bin/bash -lc "sed -n '65,186p' docs/reviews/2026-10-13/WEAR-PLANS-r1-codex.md" (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-02-contract-migration.md | sed -n '20,1...
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-04-apple-parser.md | sed -n '45,145p'"
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-04-apple-parser.md | sed -n '145,225p'"
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-04-apple-parser.md | sed -n '45,145p'" (exit 0)
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-04-apple-parser.md | sed -n '145,225p'" (exit 0)
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-02-contract-migration.md | sed -n '20,1... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-02-contract-migration.md | sed -n '136,...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-02-contract-migration.md | sed -n '136,... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-00-program.md | sed -n '35,80p;105,170p'"
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-00-program.md | sed -n '35,80p;105,170p'" (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-08-trends.md | sed -n '1,215p'"
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-08-trends.md | sed -n '1,215p'" (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-06-import-route.md | sed -n '1,215p'"
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-06-import-route.md | sed -n '1,215p'" (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-07b-review-frontend.md | sed -n '1,205p'"
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-07b-review-frontend.md | sed -n '1,205p'" (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-07-review-backend.md | sed -n '1,180p'"
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-07-review-backend.md | sed -n '1,180p'" (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-03-time-units.md | sed -n '1,190p'"
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-03-time-units.md | sed -n '1,190p'" (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-06-import-route.md | sed -n '73,150p'"
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-06-import-route.md | sed -n '73,150p'" (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-02-contract-migration.md | sed -n '58,2...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-02-contract-migration.md | sed -n '58,2... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-05-aggregate-dedup.md | sed -n '1,180p'"
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-05-aggregate-dedup.md | sed -n '1,180p'" (exit 0)
[codex] Running command: /bin/bash -lc 'rg -n "API contract|GET /wearables|POST /wearables|import_id|skipped_reasons|s...
[codex] Running command: /bin/bash -lc "rg -n -i \"profile_id|ProfileDbSession|tenant|profile B|profile b|D3|redact|st...
[codex] Running command: /bin/bash -lc 'rg -n "redact|redaction|D3|D7|sends nothing|processed by|advice|medical|doctor...
[codex] Command completed: /bin/bash -lc 'rg -n "redact|redaction|D3|D7|sends nothing|processed by|advice|medical|doctor... (exit 0)
[codex] Command completed: /bin/bash -lc "rg -n -i \"profile_id|ProfileDbSession|tenant|profile B|profile b|D3|redact|st... (exit 0)
[codex] Command completed: /bin/bash -lc 'rg -n "API contract|GET /wearables|POST /wearables|import_id|skipped_reasons|s... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-09-packet.md | sed -n '1,70p;82,150p;15...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-09-packet.md | sed -n '1,70p;82,150p;15... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-13-patient-export.md | sed -n '1,165p'"
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-13-patient-export.md | sed -n '1,165p'" (exit 0)
[codex] Running command: /bin/bash -lc 'rg -n -i "redaction before anything leaves|only.*export/csv|D3|redact" CLAUDE....
[codex] Command completed: /bin/bash -lc 'rg -n -i "redaction before anything leaves|only.*export/csv|D3|redact" CLAUDE.... (exit 0)
[codex] Running command: /bin/bash -lc 'rg -n "duplicate_record|HC-WRB-518|exact duplicate|duplicates|duplicate rows|d...
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-11-garmin-parser.md | sed -n '82,118p;1...
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-05-aggregate-dedup.md | sed -n '58,118p'"
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-09-packet.md | sed -n '8,22p;165,197p;2...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-11-garmin-parser.md | sed -n '82,118p;1... (exit 0)
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-09-packet.md | sed -n '8,22p;165,197p;2... (exit 0)
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-05-aggregate-dedup.md | sed -n '58,118p'" (exit 0)
[codex] Command completed: /bin/bash -lc 'rg -n "duplicate_record|HC-WRB-518|exact duplicate|duplicates|duplicate rows|d... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-03-time-units.md | sed -n '58,112p'"
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-03-time-units.md | sed -n '58,112p'" (exit 0)
[codex] Running command: /bin/bash -lc 'rg -n "SKIP|skip reason|skipped|allowed.*reason|duplicate_record" docs/plans/2...
[codex] Command completed: /bin/bash -lc 'rg -n "SKIP|skip reason|skipped|allowed.*reason|duplicate_record" docs/plans/2... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-02-contract-migration.md | sed -n '130,...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-02-contract-migration.md | sed -n '130,... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-12-garmin-wiring.md | sed -n '1,148p'"
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-07-review-backend.md | sed -n '17,25p;6...
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-07b-review-frontend.md | sed -n '47,57p...
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-06-import-route.md | sed -n '105,114p;1...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-07-review-backend.md | sed -n '17,25p;6... (exit 0)
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-12-garmin-wiring.md | sed -n '1,148p'" (exit 0)
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-07b-review-frontend.md | sed -n '47,57p... (exit 0)
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-06-import-route.md | sed -n '105,114p;1... (exit 0)
[codex] Assistant message captured: Step 3 of 4: Three accepted fixes are incomplete in the plan text: remote upload disclosure, ...
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-00-program.md | sed -n '39,51p;117,130p...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-00-program.md | sed -n '39,51p;117,130p... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-10-ui-shell-disclaimer.md | sed -n '72,...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-10-ui-shell-disclaimer.md | sed -n '72,... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba src/frontend/src/services/api.ts | sed -n '12,28p;78,96p;260,300p'"
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-06-import-route.md | sed -n '18,27p;66,...
[codex] Command completed: /bin/bash -lc "nl -ba src/frontend/src/services/api.ts | sed -n '12,28p;78,96p;260,300p'" (exit 0)
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-06-import-route.md | sed -n '18,27p;66,... (exit 0)
[codex] Running command: /bin/bash -lc 'rg -n -C 3 "opaque `import_id`|M2|counts plus|counts only|metric`|vendor enum"...
[codex] Command failed: /bin/bash -lc 'rg -n -C 3 "opaque `import_id`|M2|counts plus|counts only|metric`|vendor enum"... (exit 2)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-14-docs.md | sed -n '58,78p'"
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-14-docs.md | sed -n '58,78p'" (exit 0)
[codex] Running command: /bin/bash -lc "rg -n -C 2 -e 'M2' -e 'counts plus' -e 'counts only' -e 'vendor enum' -e 'impo...
[codex] Command completed: /bin/bash -lc "rg -n -C 2 -e 'M2' -e 'counts plus' -e 'counts only' -e 'vendor enum' -e 'impo... (exit 0)
[codex] Running command: /bin/bash -lc "rg -n -e 'M2' -e 'Audit details' -e 'import_id.*vendor' docs/plans/2026-10-13-...
[codex] Command completed: /bin/bash -lc "rg -n -e 'M2' -e 'Audit details' -e 'import_id.*vendor' docs/plans/2026-10-13-... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-00-program.md | sed -n '50,63p'; nl -ba...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-00-program.md | sed -n '50,63p'; nl -ba... (exit 0)
[codex] Assistant message captured: {"verdict":"needs-attention","summary":"Do not approve yet: the packet can leak named symptom...
[codex] Turn completion inferred after the main thread finished and subagent work drained.
# Codex Adversarial Review

Target: branch diff against origin/main
Verdict: needs-attention

Do not approve yet: the packet can leak named symptom notes, the upload copy misstates where data goes, and several accepted safeguards are missing from the test plans.

Findings:
- [high] Visit-prep notes can pass through strict redaction with names intact (docs/plans/2026-10-13-wearables-09-packet.md:18-20)
  The plan inserts free-text symptom notes into the visit-prep packet before strict redaction. Its own limitation says names such as “my wife Jane” pass unchanged (line 235), and the plan header still labels D2’s default as (a) despite the program’s default (c). Visit prep is not one of the two D3 export exemptions, so an opted-in note can leave the app with a person’s name intact. Keep notes disabled until a name-capable sanitizer is implemented and tested; correct the D2 header as well.
  Recommendation: Remove the note path or require tested name sanitization before notes can enter the packet.
- [high] Privacy copy still promises local-only handling with a remote API URL (docs/plans/2026-10-13-wearables-10-ui-shell-disclaimer.md:87-92)
  C2 says records are “kept on this computer,” and C7 says importing sends nothing to any online service. The production API client uses configurable `VITE_API_URL` (`src/frontend/src/services/api.ts:17-20`), while the frontend plan sends the ZIP as the raw request body (`docs/plans/2026-10-13-wearables-07b-review-frontend.md:63`). With a remote URL, the full export reaches that server before parsing. Patients could transmit their complete Health export under copy that denies online transmission.
  Recommendation: Disclose the configured HealthCentral server and raw upload, or enforce and test a local-only API target.
- [medium] The concurrent duplicate-upload test is referenced but not specified (docs/plans/2026-10-13-wearables-06-import-route.md:158-160)
  Task 2 says HC-WRB-620 will exercise simultaneous same-profile uploads, but the test table contains only HC-WRB-601–619 and acceptance expects 19 tests. The promised race test can therefore be omitted while the plan still passes its stated count; a unique-hash conflict could regress to an unhandled 500 on a normal double-submit.
  Recommendation: Add HC-WRB-620 to the test table and acceptance count, using synchronized concurrent requests and asserting one 201 plus one 409.
- [medium] The claimed Garmin production-memory test is absent (docs/plans/2026-10-13-wearables-11-garmin-parser.md:86)
  The data contract claims HC-WRB-1117 measures peak memory for a valid export at production caps, but the test table ends at HC-WRB-1116 and acceptance still expects 16 tests. The 64 MiB per-member cap does not itself verify Python object expansion during `json.loads`, so the accepted memory safeguard can be missing while acceptance passes.
  Recommendation: Specify HC-WRB-1117 in the test table, define a production-cap valid fixture and peak-memory ceiling, and update the expected count.
- [medium] The exact-duplicate step rule has no planned test (docs/plans/2026-10-13-wearables-05-aggregate-dedup.md:69)
  The contract says exact step duplicates collapse and references HC-WRB-518, but the test table ends at HC-WRB-517 and the expected count remains 17. If an export contains duplicate rows, aggregation can still double-count steps without any test failing, inflating trends and packet values.
  Recommendation: Add HC-WRB-518 with repeated same-source records and assert one contribution plus the `duplicate_record` skip count.
- [medium] Audit details exceed the program’s accepted minimization contract (docs/plans/2026-10-13-wearables-07-review-backend.md:81)
  WEAR-07 permits `metric` in audit details, while program M2 limits events to counts plus opaque `import_id` and the `vendor` enum only (program line 61). WEAR-02 also reserves `metric`, and WEAR-07’s audit test accepts the allowlist, so events may expose whether the patient reviewed sleep, steps, or heart-rate data. WEAR-06 and WEAR-07 summaries also still call audit counts-only, conflicting with their detailed field lists.
  Recommendation: Remove `metric` from audit details and related assertions, or obtain explicit approval and align the program’s minimization contract.

Next steps:
- Correct the packet and upload privacy contracts, then add the three omitted tests and align audit fields before treating the plan set as executable.
```
