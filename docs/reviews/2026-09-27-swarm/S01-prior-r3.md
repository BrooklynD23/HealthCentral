R1 (codex) dispositions:
1. [MAJOR] plan must be on main for Task 0 -> ACCEPTED: prerequisite "the 2026-09-27 plan set is committed to main via an owner-approved docs commit (P0-B's approved text covers only audit/ + capstone-report/ + INDEX.md)".
2. [MAJOR] S1-A-only path: BI-2/BI-3 exempt but final gate requires every row red -> ACCEPTED: when S1-B unsigned, skip BI-2/3 and exclude them from the stop gate.
Apply reviews/GLOBAL-rules.md.
R2 (codex) dispositions:
1. [MAJOR] SQL_ECHO=true acceptance requires zero sentinels even without S1-B -> ACCEPTED: zero-sentinel under SQL_ECHO=true only if S1-B signed; A-only run records the expected opt-in leak (documented, dev opt-in only) and keeps the default-config zero-leak gate.
