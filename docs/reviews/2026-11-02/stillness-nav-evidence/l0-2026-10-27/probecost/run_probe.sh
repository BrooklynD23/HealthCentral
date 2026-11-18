#!/usr/bin/env bash
# Usage: run_probe.sh branch|main [MAIN_TAG_T0]. One batch of the instrumented probe, wrapped in hold_slots.sh.
P=/tmp/claude-1000/-mnt-e-Programming-Github-Repo-HealthCentral/b8becc8c-4942-444f-9c3c-2a03f3900e75/scratchpad/probecost
cd "$P" || exit 2
echo "=== probe $1 tag=${2:-0} $(date +%T)"; uptime; echo pgrep:; pgrep -fa "playwright|vitest|pytest" | grep -v -e pgrep -e run_probe
if [ "$1" = branch ]; then
  /tmp/claude-1000/hold_slots.sh ./node_modules/.bin/playwright test -c playwright.config.ts e2e/ui-shell.spec.ts \
    -g "HC-UISH-009: the Safety Rail stays still through the navigation to /(timeline|search|medications/med-fixture-1|notifications|care-tasks)$" \
    --output $P/out 2>&1 | sed 's/\x1b\[[0-9;]*[A-Za-z]//g' | grep -E "PROBECOST|sampling gap|passed|failed"
else
  MAIN_TAG_T0=${2:-0} /tmp/claude-1000/hold_slots.sh ./node_modules/.bin/playwright test -c playwright.config.ts main-probe.spec.ts \
    --output $P/out 2>&1 | sed 's/\x1b\[[0-9;]*[A-Za-z]//g' | grep -E "PROBECOST|PROBEFAIL|passed|failed"
fi
