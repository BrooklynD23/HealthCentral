## Summary
Synthetic PR body for HC-EVH tests.
Evidence head: abc1234def

## Verification
$ pytest tests/test_widget.py -q
RED
3 failed in 0.40s
GREEN
[32m12 passed[0m in 1.10s

$ ../../scripts/pyslot.sh env HF_HUB_OFFLINE=1 python -m pytest tests/ -p no:cacheprovider -q
5164 passed, 3 skipped, 1732 warnings in 588.11s
5167 tests collected (+11)

$ npx vitest run
 Test Files  40 passed (40)
      Tests  412 passed (412)

$ npx vitest run src/pages/Widget.test.tsx
      Tests  5 passed (5)

CI Backend Tests: 5170 passed (quoted from the run).
CI is SUCCESS on the head.
Tests passed locally somehow.
