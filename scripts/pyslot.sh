#!/usr/bin/env bash
# Run a command (pytest) in one of PYSLOTS machine-wide slots; waits when all are busy.
# Usage: scripts/pyslot.sh <command...>   e.g. scripts/pyslot.sh env HF_HUB_OFFLINE=1 python -m pytest tests/ -q
# ponytail: fixed slot count (default 6, about 2 GB each; the box was measured at 24 logical CPUs / 37 GiB on 2026-11-11, WF-PYSLOTS-6); raise PYSLOTS with more RAM.
# A caller that has waited more than PYSLOT_WAIT_WARN_MIN minutes (default 20) gets ONE stderr line naming the wait and the
# slot-holder PIDs, and keeps waiting (WF-QUIET-WINDOW: report, do not fail).
n="${PYSLOTS:-6}"
warn_s=$(awk -v m="${PYSLOT_WAIT_WARN_MIN:-20}" 'BEGIN{printf "%d", m*60}'); t0=$(date +%s); warned=0
mkdir -p /tmp/claude-1000
# scripts/hold_slots.sh holds this lock for a quiet run: while it is held, start nothing (whatever PYSLOTS is).
H=/tmp/claude-1000/hc-pytest.hold.lock
while :; do
  for i in $(seq 1 "$n"); do
    flock -s -n -E 75 "$H" true; [ $? -eq 75 ] && break
    flock -o -n -E 75 "/tmp/claude-1000/hc-pytest.$i.lock" "$@"
    rc=$?
    [ "$rc" -ne 75 ] && exit "$rc"
  done
  if [ "$warned" -eq 0 ] && [ $(( $(date +%s)-t0 )) -ge "$warn_s" ]; then
    warned=1
    pids=$(fuser /tmp/claude-1000/hc-pytest.*.lock 2>/dev/null | tr -s ' \n' ' ')
    echo "pyslot: waited $(( ($(date +%s)-t0)/60 )) min for a slot (PYSLOTS=$n); slot-holder PIDs: ${pids:-unknown}; still waiting" >&2
  fi
  sleep 5
done
