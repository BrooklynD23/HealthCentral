# WEAR-RESEARCH — Codex review of the wearables research package (#87)

**Target:** `docs/research/2026-10-12/` as merged by PR #87, merge commit `7630aaa`, diffed against its first parent `f853308`. Run from a detached worktree at `7630aaa` on 2026-10-13.
**Tool:** `codex-companion.mjs` 1.0.4 (Codex default model; the companion `review` and `adversarial-review` subcommands take no model option).
**Response:** [WEAR-RESEARCH-response.md](WEAR-RESEARCH-response.md)

Both outputs below are verbatim stdout+stderr of the commands.

## Run 1 — native review

`node …/codex-companion.mjs review --base f853308d5f8c841eb692af195cfa09a8abd9864b --wait`

```text
[codex] Starting Codex review thread.
[codex] Thread ready (01a138fa-f4a1-7641-a67d-1e0a614ab037).
[codex] Reviewer started: changes against 'f853308d5f8c841eb692af195cfa09a8abd9864b'
[codex] Running command: /bin/bash -lc "rg -n -i \"hc-wear|wear-codex|HealthCentral|hc-w10\" /home/danny/.codex/memori...
[codex] Running command: /bin/bash -lc "printf '%s\\n' '--- refs ---'; git rev-parse HEAD; git rev-parse f853308d5f8c8...
[codex] Running command: /bin/bash -lc "git show -s --format='commit %H%nparents %P%ntree %T%nsubject %s' HEAD; git sh...
[codex] Command completed: /bin/bash -lc "printf '%s\\n' '--- refs ---'; git rev-parse HEAD; git rev-parse f853308d5f8c8... (exit 0)
[codex] Running command: /bin/bash -lc 'git diff --name-status f853308d5f8c841eb692af195cfa09a8abd9864b HEAD; echo DIF...
[codex] Command completed: /bin/bash -lc 'git diff --name-status f853308d5f8c841eb692af195cfa09a8abd9864b HEAD; echo DIF... (exit 0)
[codex] Running command: /bin/bash -lc 'git diff --no-ext-diff --unified=50 f853308d5f8c841eb692af195cfa09a8abd9864b H...
[codex] Command completed: /bin/bash -lc "git show -s --format='commit %H%nparents %P%ntree %T%nsubject %s' HEAD; git sh... (exit 0)
[codex] Command completed: /bin/bash -lc 'git diff --no-ext-diff --unified=50 f853308d5f8c841eb692af195cfa09a8abd9864b H... (exit 0)
[codex] Running command: /bin/bash -lc 'for f in docs/research/2026-10-12/*.md; do echo "--- $f ($(wc -l < "$f") lines...
[codex] Command completed: /bin/bash -lc 'for f in docs/research/2026-10-12/*.md; do echo "--- $f ($(wc -l < "$f") lines... (exit 0)
[codex] Running command: /bin/bash -lc "printf '%s\\n' '--- implementation map ---'; nl -ba docs/research/2026-10-12/0...
[codex] Command completed: /bin/bash -lc "printf '%s\\n' '--- implementation map ---'; nl -ba docs/research/2026-10-12/0... (exit 0)
[codex] Running command: /bin/bash -lc "printf '%s\\n' '--- safety privacy ---'; nl -ba docs/research/2026-10-12/04-sa...
[codex] Command completed: /bin/bash -lc "printf '%s\\n' '--- safety privacy ---'; nl -ba docs/research/2026-10-12/04-sa... (exit 0)
[codex] Running command: /bin/bash -lc "printf '%s\\n' '--- project instruction candidates ---'; for f in AGENT.md doc...
[codex] Command completed: /bin/bash -lc "printf '%s\\n' '--- project instruction candidates ---'; for f in AGENT.md doc... (exit 0)
[codex] Running command: /bin/bash -lc "git diff --unified=0 f853308d5f8c841eb692af195cfa09a8abd9864b HEAD -- docs/res...
[codex] Command completed: /bin/bash -lc "git diff --unified=0 f853308d5f8c841eb692af195cfa09a8abd9864b HEAD -- docs/res... (exit 0)
[codex] Review output captured.
[codex] Reviewer finished.
[codex] Assistant message captured: The documentation introduces actionable defects in the proposed metric semantics, implementat...
[codex] Turn completed.
# Codex Review

Target: branch diff against f853308d5f8c841eb692af195cfa09a8abd9864b

The documentation introduces actionable defects in the proposed metric semantics, implementation gate, and regulatory framing. The diff is documentation-only; `git diff --check` passed, and no application tests were run.

Full review comments:

- [P2] Aggregate step samples into daily totals — /mnt/c/Users/DangT/Documents/GitHub/hc-wear-codex/docs/research/2026-10-12/05-mvp-roadmap-tests.md:20-20
  Apple Health step records represent counts over intervals, so taking a per-day median and IQR of those records does not yield daily step totals and can substantially undercount steps. Define the daily value as the sum of the selected source’s non-overlapping intervals before using daily totals in trends or packet summaries.

- [P2] Resolve sleep overlap before authorizing implementation — /mnt/c/Users/DangT/Documents/GitHub/hc-wear-codex/docs/research/2026-10-12/06-decisions-go-nogo.md:37-37
  The go gate requires the three metrics and their offsets, but does not require resolving the sleep-record overlap question listed in §2 item 3. If an export contains overlapping sleep intervals or sources, summing them can overstate asleep minutes; make the overlap and stage-selection rule part of the evidence gate before parser work begins.

- [P2] Leave device classification pending legal review — /mnt/c/Users/DangT/Documents/GitHub/hc-wear-codex/docs/research/2026-10-12/00-README.md:35-35
  The quoted owner direction asks for a no-professional-advice disclaimer; it does not establish that the software is not a medical device. Since the package leaves the FDA/legal review open (OM-7 and OM-8), presenting this classification as settled could mislead downstream decisions; describe the intended use and leave classification pending review.

- [P2] Apply the export gate per vendor slice — /mnt/c/Users/DangT/Documents/GitHub/hc-wear-codex/docs/research/2026-10-12/00-README.md:50-51
  This blanket gate requires both Apple and Garmin exports before any code, which conflicts with the Apple-first rollout: the roadmap and go/no-go criteria require OM-2 only before the Garmin slice. This would block the Apple slice unnecessarily; require OM-1 before Apple work and OM-2 before Garmin work.
```

## Run 2 — adversarial review

`node …/codex-companion.mjs adversarial-review --wait --base f853308d5f8c841eb692af195cfa09a8abd9864b "<focus>"`, focus: vendor-claim accuracy, verified/inferred/assumed labelling, profile isolation, redaction, no-medical-advice, timezone handling, single-repo decision, code facts vs HEAD.

```text
[codex] Starting Codex task thread.
[codex] Thread ready (01a138fe-3669-72f0-a721-c1a866ca434e).
[codex] Turn started (01a138fe-3b64-7262-89ac-702fa2837ff9).
[codex] Assistant message captured: Step 1 of 3: I’m checking the exact diff and the cited vendor sources before judging the rese...
[codex] Running command: /bin/bash -lc 'rg -n -i "wearable|ProfileDbSession|timezone|visit-prep|vendor" /home/danny/.c...
[codex] Command completed: /bin/bash -lc 'rg -n -i "wearable|ProfileDbSession|timezone|visit-prep|vendor" /home/danny/.c... (exit 0)
[codex] Running command: /bin/bash -lc 'git diff --find-renames --no-ext-diff --unified=5 f853308d5f8c841eb692af195cfa...
[codex] Running command: /bin/bash -lc 'git status --short && git rev-parse HEAD && git diff --stat f853308d5f8c841eb6...
[codex] Command completed: /bin/bash -lc 'git diff --find-renames --no-ext-diff --unified=5 f853308d5f8c841eb692af195cfa... (exit 0)
[codex] Command completed: /bin/bash -lc 'git status --short && git rev-parse HEAD && git diff --stat f853308d5f8c841eb6... (exit 0)
[codex] Running command: /bin/bash -lc 'git branch -a --contains HEAD && git rev-parse origin/main && git show -s --on...
[codex] Running command: /bin/bash -lc 'nl -ba docs/research/2026-10-12/01-vendor-matrix.md'
[codex] Command completed: /bin/bash -lc 'nl -ba docs/research/2026-10-12/01-vendor-matrix.md' (exit 0)
[codex] Running command: /bin/bash -lc 'nl -ba docs/research/2026-10-12/04-safety-privacy.md && nl -ba docs/research/2...
[codex] Command completed: /bin/bash -lc 'nl -ba docs/research/2026-10-12/04-safety-privacy.md && nl -ba docs/research/2... (exit 0)
[codex] Running command: /bin/bash -lc 'nl -ba docs/research/2026-10-12/02-implementation-map.md && nl -ba docs/resear...
[codex] Command completed: /bin/bash -lc 'nl -ba docs/research/2026-10-12/02-implementation-map.md && nl -ba docs/resear... (exit 0)
[codex] Command failed: /bin/bash -lc 'git branch -a --contains HEAD && git rev-parse origin/main && git show -s --on... (exit 2)
[codex] Assistant message captured: Step 2 of 3: the package explicitly anchors its code map to `4884d38`, but `HEAD` includes la...
[codex] Running command: /bin/bash -lc 'git diff --unified=2 4884d38..HEAD -- src/backend/core/profile_database.py src...
[codex] Running command: /bin/bash -lc 'nl -ba docs/research/2026-10-12/03-architecture-contracts.md'
[codex] Command completed: /bin/bash -lc 'nl -ba docs/research/2026-10-12/03-architecture-contracts.md' (exit 0)
[codex] Running command: /bin/bash -lc "rg -n \"class ProfileDbSession|ProfileDbSession|def _parse_date|user_verified=...
[codex] Running command: /bin/bash -lc "nl -ba docs/research/2026-10-12/00-README.md | sed -n '65,105p'; nl -ba docs/r...
[codex] Command completed: /bin/bash -lc "nl -ba docs/research/2026-10-12/00-README.md | sed -n '65,105p'; nl -ba docs/r... (exit 0)
[codex] Command completed: /bin/bash -lc 'git diff --unified=2 4884d38..HEAD -- src/backend/core/profile_database.py src... (exit 0)
[codex] Command completed: /bin/bash -lc "rg -n \"class ProfileDbSession|ProfileDbSession|def _parse_date|user_verified=... (exit 0)
[codex] Searching:
[codex] Searching:
[codex] Running command: /bin/bash -lc "git show 7630aaa:docs/research/2026-10-12/02-implementation-map.md | sed -n '1...
[codex] Running command: /bin/bash -lc "nl -ba src/backend/api/documents.py | sed -n '400,505p;700,775p'; nl -ba src/b...
[codex] Command completed: /bin/bash -lc "nl -ba src/backend/api/documents.py | sed -n '400,505p;700,775p'; nl -ba src/b... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba src/backend/core/time.py | sed -n '1,55p'; nl -ba src/backend/core/prof...
[codex] Command completed: /bin/bash -lc "nl -ba src/backend/core/time.py | sed -n '1,55p'; nl -ba src/backend/core/prof... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba src/backend/modules/export.py | sed -n '502,685p'; nl -ba src/backend/a...
[codex] Command completed: /bin/bash -lc "nl -ba src/backend/modules/export.py | sed -n '502,685p'; nl -ba src/backend/a... (exit 0)
[codex] Command completed: /bin/bash -lc "git show 7630aaa:docs/research/2026-10-12/02-implementation-map.md | sed -n '1... (exit 0)
[codex] Running command: /bin/bash -lc 'rg -n "RedactionEngine|PERSON|name|first_name|last_name|Jane|strict" src/backe...
[codex] Running command: /bin/bash -lc 'rg -n -i "no medical advice|medical advice|medical device|diagnos|normal|abnor...
[codex] Command completed: /bin/bash -lc 'rg -n "RedactionEngine|PERSON|name|first_name|last_name|Jane|strict" src/backe... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba src/backend/modules/redaction.py | sed -n '1,220p'; nl -ba docs/researc...
[codex] Command completed: /bin/bash -lc "nl -ba src/backend/modules/redaction.py | sed -n '1,220p'; nl -ba docs/researc... (exit 0)
[codex] Command completed: /bin/bash -lc 'rg -n -i "no medical advice|medical advice|medical device|diagnos|normal|abnor... (exit 0)
[codex] Running command: /bin/bash -lc "rg --files src/backend/migrations/profile/versions | sort | tail -15; rg -n \"...
[codex] Command completed: /bin/bash -lc "rg --files src/backend/migrations/profile/versions | sort | tail -15; rg -n \"... (exit 0)
[codex] Searching:
[codex] Running command: /bin/bash -lc 'rg -n -i "redaction before anything|redaction before|D3.*full.fidelity|full.fi...
[codex] Command completed: /bin/bash -lc 'rg -n -i "redaction before anything|redaction before|D3.*full.fidelity|full.fi... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba CLAUDE.md | sed -n '55,62p'; nl -ba docs/capstone-report/owner-decision...
[codex] Command completed: /bin/bash -lc "nl -ba CLAUDE.md | sed -n '55,62p'; nl -ba docs/capstone-report/owner-decision... (exit 0)
[codex] Assistant message captured: { "verdict": "needs-attention", "summary": "The code anchors checked still match HEAD, but th...
[codex] Turn completion inferred after the main thread finished and subagent work drained.
# Codex Adversarial Review

Target: branch diff against f853308d5f8c841eb692af195cfa09a8abd9864b
Verdict: needs-attention

The code anchors checked still match HEAD, but the package has an unauthorized export exception, an ineffective redaction expectation, and unresolved daily aggregation rules.

Findings:
- [high] Wearable CSV incorrectly inherits the D3 redaction exception (docs/research/2026-10-12/04-safety-privacy.md:63-64)
  The package calls the proposed wearable CSV a D3 full-fidelity export. The governing rule in `CLAUDE.md:59` exempts only the existing `GET /export/csv` and `/export/json` endpoints and says no other export is exempt. Extending that exception would let a new route export wearable data without the required redaction, including user-controlled source names. Require redaction for this export or obtain an explicit owner decision and update the governing policy before implementation.
  Recommendation: Remove the D3 exemption for the new wearable CSV unless the owner explicitly approves and records a broader exception.
- [high] The stated strict-redaction test will not redact the example device name (docs/research/2026-10-12/04-safety-privacy.md:50)
  The acceptance criterion expects `Jane's Apple Watch` to be redacted, but the current strict `name_context` rule at `src/backend/modules/redaction.py:82-88` only matches names preceded by a context label and requires at least two name tokens. This example does not match, so the visit-prep packet can expose the name despite running the strict pass. Normalize or omit raw device names before rendering, or add a suitable sanitizer and verify the actual output.
  Recommendation: Do not rely on the existing strict pass for arbitrary `source_name` values; sanitize or replace them and test the rendered packet.
- [medium] The upsert key contradicts the documented row grain and can replace non-equivalent imports (docs/research/2026-10-12/03-architecture-contracts.md:68-74)
  The contract says one row per source document and stores `doc_id` (`03-architecture-contracts.md:28-34`), but this upsert key omits both `doc_id` and device identity. A second Apple or Garmin import for the same metric/date therefore replaces the earlier row even when its records or selected source differ; the hash warning only handles an identical file. This can discard values and their provenance. Define one consistent row grain and replacement rule.
  Recommendation: Include stable source/import identity in the key or explicitly model immutable imports plus a separately selected current daily row.
- [medium] Daily sleep bucketing has no overnight interval rule (docs/research/2026-10-12/03-architecture-contracts.md:39-41)
  The contract defines a record's local date and offset, but the MVP includes asleep minutes derived from sleep intervals that can cross midnight. It does not say whether to assign the interval to its start date, end date, or split it, or how to calculate duration across DST. The proposed offset tests use point timestamps, so they will not catch this ambiguity; daily totals can land on different dates across implementations.
  Recommendation: Specify a metric-specific overnight attribution and duration rule, then add fixtures spanning local midnight and a DST offset change.
- [medium] The package states an FDA policy conclusion while its evidence gate is still open (docs/research/2026-10-12/04-safety-privacy.md:9-16)
  This section says the design keeps the feature inside general-wellness policy, while labeling the guidance content as secondary and leaving the full FDA text for OM-8. The [FDA guidance](https://www.fda.gov/media/90652/download) conditions its policy on intended use and low risk; a disclaimer and absence of alerts do not establish that a specific product is outside device regulation. The README also states that the tool is “not a medical device.” Keep that as an unresolved regulatory hypothesis until the cited guidance and legal review are complete.
  Recommendation: Replace the categorical policy conclusion with a conditional statement and gate any product classification claim on OM-8 and legal review.

Next steps:
- Resolve the two export-redaction findings and the row/date rules in the cited research docs, then request a focused re-review.
```
