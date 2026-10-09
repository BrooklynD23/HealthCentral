R1 (codex) dispositions:
1. [BLOCKER] aware timestamp in guard-removal test -> ACCEPTED: core.time.utcnow() (naive UTC); scan the whole plan for datetime.now(timezone.utc)/utcnow misuse.
2. [MAJOR] pytest piped without pipefail (START/END/coverage) -> ACCEPTED (GLOBAL rules).
Apply reviews/GLOBAL-rules.md.
R2 (codex) dispositions:
1. [MAJOR] HC-PGUARD-005 accepts any non-403 -> ACCEPTED: assert the expected downstream status (and a side effect where one exists) per route.
2. [MAJOR] npm ci failure doesn't stop the block -> ACCEPTED: `npm ci ... || exit 1` (or explicit check) before lint/build.
3. [MAJOR] coverage runs from /mnt/c though Task 5 uses a Linux scratch copy -> ACCEPTED: run coverage from the scratch copy (/tmp/w11a-gb4/src/backend) consistently; state the measured tree.
