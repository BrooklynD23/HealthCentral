# WEAR-PLANS r1 — Codex review of the wearables plan set

**Target:** `docs/wearables-plans` @ `df5993f` against `origin/main` (`8234990`): program, 14 plans, tickets, research corrections. Run from the plans worktree on 2026-10-13.
**Tool:** `codex-companion.mjs` 1.0.4, Codex default model. The owner prefers "6.1 sol" then "6-luna high" for large plans; the companion `review` and `adversarial-review` subcommands expose no model option, so the default ran.
**Response:** [WEAR-PLANS-r1-response.md](WEAR-PLANS-r1-response.md)

Verbatim stdout+stderr below.

## Native review (`review --base origin/main --wait`)

```text
[codex] Starting Codex review thread.
[codex] Thread ready (01a13915-a9f5-74a2-9332-6e4477a6209d).
[codex] Reviewer started: changes against 'origin/main'
[codex] Running command: /bin/bash -lc "grep -n -i -E 'hc-w10|wear-plans|HealthCentral|Asclexis' /home/danny/.codex/me...
[codex] Running command: /bin/bash -lc 'git rev-parse 823499043fe91c628062e7c3f6b915d3c1c08e1f && git log --oneline --...
[codex] Command completed: /bin/bash -lc 'git rev-parse 823499043fe91c628062e7c3f6b915d3c1c08e1f && git log --oneline --... (exit 0)
[codex] Running command: /bin/bash -lc "for f in docs/plans/2026-10-13-wearables-*.md; do printf '%5s %s\\n' \""'$(wc ...
[codex] Command completed: /bin/bash -lc "for f in docs/plans/2026-10-13-wearables-*.md; do printf '%5s %s\\n' \""'$(wc ... (exit 0)
[codex] Running command: /bin/bash -lc 'for f in docs/plans/2026-10-13-wearables-01-flag-router.md docs/plans/2026-10-...
[codex] Command completed: /bin/bash -lc 'for f in docs/plans/2026-10-13-wearables-01-flag-router.md docs/plans/2026-10-... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-02-contract-migration.md | sed -n '1,16...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-02-contract-migration.md | sed -n '1,16... (exit 0)
[codex] Running command: /bin/bash -lc 'for f in docs/plans/2026-10-13-wearables-04-apple-parser.md docs/plans/2026-10...
[codex] Command completed: /bin/bash -lc 'for f in docs/plans/2026-10-13-wearables-04-apple-parser.md docs/plans/2026-10... (exit 0)
[codex] Running command: /bin/bash -lc 'for f in docs/plans/2026-10-13-wearables-05-aggregate-dedup.md docs/plans/2026...
[codex] Command completed: /bin/bash -lc 'for f in docs/plans/2026-10-13-wearables-05-aggregate-dedup.md docs/plans/2026... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-07-review-backend.md | sed -n '1,230p';"
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-07-review-backend.md | sed -n '1,230p';" (exit 0)
[codex] Running command: /bin/bash -lc 'for f in docs/plans/2026-10-13-wearables-08-trends.md docs/plans/2026-10-13-we...
[codex] Command completed: /bin/bash -lc 'for f in docs/plans/2026-10-13-wearables-08-trends.md docs/plans/2026-10-13-we... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-09-packet.md | sed -n '1,270p';"
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-09-packet.md | sed -n '1,270p';" (exit 0)
[codex] Running command: /bin/bash -lc 'for f in docs/plans/2026-10-13-wearables-11-garmin-parser.md docs/plans/2026-1...
[codex] Command completed: /bin/bash -lc 'for f in docs/plans/2026-10-13-wearables-11-garmin-parser.md docs/plans/2026-1... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-12-garmin-wiring.md | sed -n '1,190p'; ...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-12-garmin-wiring.md | sed -n '1,190p'; ... (exit 0)
[codex] Running command: /bin/bash -lc "git diff --no-ext-diff --unified=5 823499043fe91c628062e7c3f6b915d3c1c08e1f --...
[codex] Command completed: /bin/bash -lc "git diff --no-ext-diff --unified=5 823499043fe91c628062e7c3f6b915d3c1c08e1f --... (exit 0)
[codex] Running command: /bin/bash -lc "cat AGENT.md; printf '\\n--- docs instruction search ---\\n'; find docs -name ...
[codex] Command completed: /bin/bash -lc "cat AGENT.md; printf '\\n--- docs instruction search ---\\n'; find docs -name ... (exit 0)
[codex] Running command: /bin/bash -lc "printf '%s\\n' '--- accepted response ---'; cat docs/reviews/2026-10-13/WEAR-0...
[codex] Command completed: /bin/bash -lc "printf '%s\\n' '--- accepted response ---'; cat docs/reviews/2026-10-13/WEAR-0... (exit 0)
[codex] Running command: /bin/bash -lc "python3 scripts/docs_lint.py --link-graph; printf 'docs_lint_exit=%s\\n' \""'$...
[codex] Running command: /bin/bash -lc 'timeout 20s python3 scripts/docs_lint.py --link-graph; echo docs_lint=$?; time...
[codex] Command completed: /bin/bash -lc "python3 scripts/docs_lint.py --link-graph; printf 'docs_lint_exit=%s\\n' \""'$... (exit 0)
[codex] Command completed: /bin/bash -lc 'timeout 20s python3 scripts/docs_lint.py --link-graph; echo docs_lint=$?; time... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-11-garmin-parser.md | sed -n '1,135p'; ...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-11-garmin-parser.md | sed -n '1,135p'; ... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/research/2026-10-12/00-README.md | sed -n '43,70p'; printf '\\n---...
[codex] Command completed: /bin/bash -lc "nl -ba docs/research/2026-10-12/00-README.md | sed -n '43,70p'; printf '\\n---... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-05-aggregate-dedup.md | sed -n '38,110p...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-05-aggregate-dedup.md | sed -n '38,110p... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba src/frontend/src/services/api.ts | sed -n '12,25p;78,92p'; nl -ba docs/...
[codex] Command completed: /bin/bash -lc "nl -ba src/frontend/src/services/api.ts | sed -n '12,25p;78,92p'; nl -ba docs/... (exit 0)
[codex] Review output captured.
[codex] Reviewer finished.
[codex] Assistant message captured: The patch is documentation-only, so it does not change existing runtime behavior, but the pro...
[codex] Turn completed.
# Codex Review

Target: branch diff against origin/main

The patch is documentation-only, so it does not change existing runtime behavior, but the proposed plans leave actionable data-accuracy, resource-safety, rollout, and privacy-copy defects unresolved. These should be corrected before the plan set is treated as ready for execution.

Full review comments:

- [P2] Define handling for duplicate step records — /mnt/c/Users/DangT/Documents/GitHub/hc-wear-plans/docs/plans/2026-10-13-wearables-05-aggregate-dedup.md:69-69
  If OM-1 finds exact duplicate step records from the selected source on the same day, this rule sums both and inflates the daily total. The program explicitly leaves duplicate occurrence open, but WEAR-05 only asks to adjust fixture shapes; define a deduplication rule and test it, or block the slice until OM-1 confirms duplicates do not occur.

- [P2] Keep Garmin parsing memory bounded — /mnt/c/Users/DangT/Documents/GitHub/hc-wear-plans/docs/plans/2026-10-13-wearables-11-garmin-parser.md:86-86
  For a valid large Garmin export, `records: list[dict]` materializes every normalized record, and the planned JSON load materializes the whole member before aggregation. Under the proposed 500 MB upload cap and 8 GiB uncompressed limit, this can exhaust the 12 GB worker; the bomb test only measures a rejected input. Use a streaming result interface or set measured byte and record limits, then test peak memory at those limits.

- [P2] Update the upload copy when enabling Garmin — /mnt/c/Users/DangT/Documents/GitHub/hc-wear-plans/docs/plans/2026-10-13-wearables-12-garmin-wiring.md:23-23
  When WEAR-12 enables Garmin imports, the review UI still labels the file input `Apple Health export (.zip)` and describes parse failures as an Apple Health export error (WEAR-07b R2/R8). Showing Garmin export instructions without updating those strings makes the supported upload misleading; include generic or vendor-aware copy and tests, or gate the Garmin launch on that frontend follow-up.

- [P2] Remove the blanket pre-code Garmin gate — /mnt/c/Users/DangT/Documents/GitHub/hc-wear-plans/docs/research/2026-10-12/00-README.md:53-53
  The sentence still introduces the requirements with “Before any code,” which can make OM-2 appear to block the Apple slice and foundation work, despite the per-slice wording here and the later recommendation that only OM-1 gates the first slice. Replace the blanket lead-in with an explicit per-vendor gate so the research package agrees with the program milestones.

- [P2] Qualify the local-only upload claim — /mnt/c/Users/DangT/Documents/GitHub/hc-wear-plans/docs/plans/2026-10-13-wearables-10-ui-shell-disclaimer.md:91-92
  If the frontend is built with `VITE_API_URL` pointing to a remote backend, the planned raw-body upload sends the full export to that server, so these claims that it is processed “on this computer” and sends nothing over the network are false. The existing API client supports that configuration; describe the configured server destination or enforce and test a local-only API target.
```

## Adversarial review (`adversarial-review --wait --base origin/main "<focus>"`)

Focus: profile isolation, redaction (D3 scope), no-medical-advice, timezone/DST and sleep rules, hostile files, unreviewed data reaching trends/RAG/timeline/packet, audit, migration ordering, tests that could not fail, ask-first gates, file:line accuracy.

```text
[codex] Starting Codex task thread.
[codex] Starting Codex task thread.
[codex] Thread ready (01a13915-f008-7fb0-a2cc-112916c51f57).
[codex] Turn started (01a13915-f501-7853-9d0f-2952b190255c).
[codex] Assistant message captured: I’ll inspect the branch diff and current backend/router/migration paths first, then verify ea...
[codex] Running command: /bin/bash -lc 'rg -n "wearable|ProfileDbSession|get_db|redact|D3|alembic|migration|zip|XML|DS...
[codex] Command completed: /bin/bash -lc 'rg -n "wearable|ProfileDbSession|get_db|redact|D3|alembic|migration|zip|XML|DS... (exit 0)
[codex] Running command: /bin/bash -lc 'pwd && rg --files | head -80'
[codex] Running command: /bin/bash -lc 'git status --short && git diff --stat origin/main...HEAD && git diff --name-on...
[codex] Command completed: /bin/bash -lc 'pwd && rg --files | head -80' (exit 0)
[codex] Command completed: /bin/bash -lc 'git status --short && git diff --stat origin/main...HEAD && git diff --name-on... (exit 0)
[codex] Running command: /bin/bash -lc 'rg -n "wearable|ProfileDbSession|get_db|strict|redact|D3|break.glass|migration...
[codex] Command completed: /bin/bash -lc 'rg -n "wearable|ProfileDbSession|get_db|strict|redact|D3|break.glass|migration... (exit 0)
[codex] Running command: /bin/bash -lc "rg -n \"class ProfileDbSession|ProfileDbSession|get_db\\(|def get_db|strict_re...
[codex] Running command: /bin/bash -lc 'git diff --find-renames --unified=3 origin/main...HEAD -- docs/plans/2026-10-1...
[codex] Command completed: /bin/bash -lc "rg -n \"class ProfileDbSession|ProfileDbSession|get_db\\(|def get_db|strict_re... (exit 0)
[codex] Command completed: /bin/bash -lc 'git diff --find-renames --unified=3 origin/main...HEAD -- docs/plans/2026-10-1... (exit 0)
[codex] Running command: /bin/bash -lc "rg -n \"class ProfileDbSession|def get_db|ProfileDbSession =|def get_profile_d...
[codex] Command completed: /bin/bash -lc "rg -n \"class ProfileDbSession|def get_db|ProfileDbSession =|def get_profile_d... (exit 0)
[codex] Running command: /bin/bash -lc 'git status --short && git rev-parse HEAD origin/main && git merge-base HEAD or...
[codex] Running command: /bin/bash -lc 'for f in docs/plans/2026-10-13-wearables-0*.md docs/plans/2026-10-13-wearables...
[codex] Command completed: /bin/bash -lc 'for f in docs/plans/2026-10-13-wearables-0*.md docs/plans/2026-10-13-wearables... (exit 0)
[codex] Command completed: /bin/bash -lc 'git status --short && git rev-parse HEAD origin/main && git merge-base HEAD or... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba src/backend/modules/redaction.py | sed -n '1,135p'; nl -ba src/backend/...
[codex] Command completed: /bin/bash -lc "nl -ba src/backend/modules/redaction.py | sed -n '1,135p'; nl -ba src/backend/... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-06-import-route.md | sed -n '1,230p'; n...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-06-import-route.md | sed -n '1,230p'; n... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba src/backend/core/auth.py | sed -n '280,350p'; nl -ba src/backend/tests/...
[codex] Command completed: /bin/bash -lc "nl -ba src/backend/core/auth.py | sed -n '280,350p'; nl -ba src/backend/tests/... (exit 0)
[codex] Running command: /bin/bash -lc 'rg -n "''^##|''^###|audit|log_wearable|details|count|profile_db|get_db|Profile...
[codex] Running command: /bin/bash -lc "rg -n \"ask.first|Ask.first|Do not|owner|approval|security/input_validator|cor...
[codex] Running command: /bin/bash -lc 'rg -n "foreign_keys|PRAGMA.*foreign|ask.first|Do not edit|ask-first|must ask|o...
[codex] Running command: /bin/bash -lc 'rg -n "''^##|''^###|timestamp|offset|timezone|DST|sleep|overlap|duplicate|sum|...
[codex] Command completed: /bin/bash -lc 'rg -n "''^##|''^###|timestamp|offset|timezone|DST|sleep|overlap|duplicate|sum|... (exit 0)
[codex] Command completed: /bin/bash -lc 'rg -n "''^##|''^###|audit|log_wearable|details|count|profile_db|get_db|Profile... (exit 0)
[codex] Command completed: /bin/bash -lc "rg -n \"ask.first|Ask.first|Do not|owner|approval|security/input_validator|cor... (exit 0)
[codex] Command failed: /bin/bash -lc 'rg -n "foreign_keys|PRAGMA.*foreign|ask.first|Do not edit|ask-first|must ask|o... (exit 2)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-04-apple-parser.md | sed -n '1,245p'; n...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-04-apple-parser.md | sed -n '1,245p'; n... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-05-aggregate-dedup.md | sed -n '1,200p'...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-05-aggregate-dedup.md | sed -n '1,200p'... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba src/backend/security/input_validator.py | sed -n '1,180p'; nl -ba docs/...
[codex] Command completed: /bin/bash -lc "nl -ba src/backend/security/input_validator.py | sed -n '1,180p'; nl -ba docs/... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-02-contract-migration.md | sed -n '1,31...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-02-contract-migration.md | sed -n '1,31... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-00-program.md | sed -n '35,55p;115,165p...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-00-program.md | sed -n '35,55p;115,165p... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba src/backend/tests/support/routes.py | sed -n '1,90p'; nl -ba src/backen...
[codex] Command completed: /bin/bash -lc "nl -ba src/backend/tests/support/routes.py | sed -n '1,90p'; nl -ba src/backen... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-04-apple-parser.md | sed -n '55,175p'; ...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-04-apple-parser.md | sed -n '55,175p'; ... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-05-aggregate-dedup.md | sed -n '15,125p...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-05-aggregate-dedup.md | sed -n '15,125p... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-01-flag-router.md | sed -n '30,110p;120...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-01-flag-router.md | sed -n '30,110p;120... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba CLAUDE.md | sed -n '1,55p'; nl -ba docs/capstone-report/owner-decisions...
[codex] Command completed: /bin/bash -lc "nl -ba CLAUDE.md | sed -n '1,55p'; nl -ba docs/capstone-report/owner-decisions... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-08-trends.md | sed -n '68,90p;110,140p;...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-08-trends.md | sed -n '68,90p;110,140p;... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba CLAUDE.md | sed -n '54,120p'; nl -ba docs/plans/2026-10-13-wearables-13...
[codex] Command completed: /bin/bash -lc "nl -ba CLAUDE.md | sed -n '54,120p'; nl -ba docs/plans/2026-10-13-wearables-13... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-12-garmin-wiring.md | sed -n '60,74p'; ...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-12-garmin-wiring.md | sed -n '60,74p'; ... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba src/backend/tests/test_audit_order.py | sed -n '78,110p;155,180p'; nl -...
[codex] Command completed: /bin/bash -lc "nl -ba src/backend/tests/test_audit_order.py | sed -n '78,110p;155,180p'; nl -... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-02-contract-migration.md | sed -n '185,...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-02-contract-migration.md | sed -n '185,... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba src/backend/api/profiles.py | sed -n '486,524p'; nl -ba docs/plans/2026...
[codex] Command completed: /bin/bash -lc "nl -ba src/backend/api/profiles.py | sed -n '486,524p'; nl -ba docs/plans/2026... (exit 0)
[codex] Assistant message captured: {"verdict":"needs-attention","summary":"Do not approve the plan set yet: free-text symptom no...
[codex] Turn completion inferred after the main thread finished and subagent work drained.
# Codex Adversarial Review

Target: branch diff against origin/main
Verdict: needs-attention

Do not approve the plan set yet: free-text symptom notes can leak names from visit-prep packets, hostile-file limits do not bound memory use, and several implementation contracts conflict or fail under concurrency.

Findings:
- [high] Strict packet redaction knowingly leaves names in symptom notes (docs/plans/2026-10-13-wearables-09-packet.md:235)
  The plan acknowledges that text such as “my wife Jane gets headaches” passes the current strict redactor, yet D2 accepts notes in the packet. The phone/email test does not cover this leak. Names can therefore leave in the response or downloaded packet despite the strict-redaction invariant. Exclude free-text notes or require a note-specific sanitizer and name-focused tests before allowing them into packet output.
  Recommendation: Block symptom notes from packet output until strict handling of natural-language names is implemented and tested.
- [high] Parser limits permit resource exhaustion on hostile archives (docs/plans/2026-10-13-wearables-04-apple-parser.md:100)
  The Apple parser permits an 8 GiB uncompressed member and total. It calls `zipfile.ZipFile` before validating individual member metadata, with only a 20,000-entry cap and no central-directory byte or extra-field limit. The Garmin plan then loads JSON eagerly and only catches recursion after parsing. A permitted archive can cause large metadata allocation or expand into JSON objects far larger than the input; the 64 MB fixture does not test the production limits. This can exhaust memory or keep the app busy parsing a hostile file.
  Recommendation: Set realistic hard limits from measured exports, bound central-directory metadata before constructing `ZipFile`, cap JSON bytes before decoding, and test those limits using the production defaults.
- [medium] Program upload contract conflicts with the selected streaming design (docs/plans/2026-10-13-wearables-00-program.md:44)
  This line requires hashing `upload.file` and seeking it before parsing, but D6 selects raw `Request.stream()` to an app-owned temp file; WEAR-06 specifies that helper and WEAR-07b sends a raw `File` body. A worker following this program contract may implement a multipart `UploadFile` route incompatible with the frontend and temp-file decision. Align the program with the raw-body, stream-to-temp contract.
  Recommendation: Replace the `upload.file`/`seek(0)` contract with the selected raw-stream-to-temp path and make all plans use that body format.
- [medium] Audit details exceed the stated counts-only policy (docs/plans/2026-10-13-wearables-06-import-route.md:112)
  The import audit is specified to include `import_id` and `vendor` in addition to counts; WEAR-02 also reserves these fields, while the program and WEAR-14 describe audit details as counts only. These values add per-import linkage and source category to the master audit log, contrary to the stated minimization rule. Resolve the policy before tests lock in the extra fields.
  Recommendation: For the stated counts-only policy, remove `import_id` and `vendor` from audit details and assert only count fields are retained.
- [medium] Concurrent duplicate imports can return 500 instead of the promised 409 (docs/plans/2026-10-13-wearables-06-import-route.md:158)
  The route checks for an existing hash and later inserts and flushes. Two same-profile requests can both pass the check; the unique `(profile_id, content_hash)` constraint then makes one flush fail. The plan specifies no uniqueness-error handling, and its duplicate test is sequential, so it will not expose this race. A normal retry or double-submit can receive an unhandled server error.
  Recommendation: Handle the unique-conflict path by re-reading the existing import and returning the documented 409; add a concurrent same-profile upload test.

Next steps:
- Disposition these five plan gaps before authorizing implementation.
```
