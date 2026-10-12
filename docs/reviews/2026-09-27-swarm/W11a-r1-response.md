R1 (codex) dispositions:
1. [BLOCKER] aware timestamp in guard-removal test -> ACCEPTED: core.time.utcnow() (naive UTC); scan the whole plan for datetime.now(timezone.utc)/utcnow misuse.
2. [MAJOR] pytest piped without pipefail (START/END/coverage) -> ACCEPTED (GLOBAL rules).
Apply reviews/GLOBAL-rules.md.
