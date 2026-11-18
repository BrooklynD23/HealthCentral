#!/usr/bin/env bash
# Usage: run_batch.sh RUN   (RUN=0 is warm-up). Runs one interleaved batch of the bare timer, wrapped in hold_slots.sh.
M=/tmp/claude-1000/-mnt-e-Programming-Github-Repo-HealthCentral/b8becc8c-4942-444f-9c3c-2a03f3900e75/scratchpad/baretimer
RUN=$1
export MEAS_PLAN=$(python3 - "$RUN" <<'PY'
import json, sys
run = int(sys.argv[1])
routes = ['/timeline', '/search', '/medications/med-fixture-1', '/notifications', '/care-tasks']
trees = [('main-dev', 'http://127.0.0.1:3001'), ('branch-dev', 'http://127.0.0.1:3000'), ('branch-preview', 'http://127.0.0.1:4190')]
if run % 2 == 0:  # alternate which tree goes first
    trees = [trees[1], trees[0], trees[2]]
print(json.dumps([{'tree': t, 'base': b, 'route': r, 'run': run} for r in routes for t, b in trees]))
PY
)
echo "=== batch $RUN $(date +%T)"; uptime; echo "pgrep:"; pgrep -fa "playwright|vitest|pytest" | grep -v -e pgrep -e run_batch
cd "$M" && /tmp/claude-1000/hold_slots.sh ./node_modules/.bin/playwright test -c playwright.config.ts 2>&1 | grep -E "MEAS|passed|failed|Error" 
