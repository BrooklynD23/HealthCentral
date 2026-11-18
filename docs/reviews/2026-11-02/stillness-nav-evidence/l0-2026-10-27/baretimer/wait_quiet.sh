#!/usr/bin/env bash
# Waits (max $1 s, default 1800) until 1-min load < 1.5 and no playwright/vitest/pytest is running.
end=$(( $(date +%s) + ${1:-1800} ))
while [ $(date +%s) -lt $end ]; do
  l=$(cut -d' ' -f1 /proc/loadavg)
  f=$(pgrep -fa "playwright|vitest|pytest" | grep -v -e pgrep -e wait_quiet | wc -l)
  if awk "BEGIN{exit !($l < 1.5)}" && [ "$f" = 0 ]; then echo "quiet at $(date +%T) load=$l"; exit 0; fi
  sleep 15
done
echo "NOT quiet after wait: $(uptime)"; pgrep -fa "playwright|vitest|pytest" | grep -v -e pgrep -e wait_quiet; exit 1
