#!/usr/bin/env bash
# quiet_run.sh [--max-wait S] <cmd>: claim the pytest slots FIRST (hold_slots.sh), then wait until the box is quiet
# (load1 < 1.5, no foreign playwright/vite/pytest/uvicorn, no listener on 3000/4173/5173/8000), then run <cmd>.
# Exit 75 = never quiet within S (default 3600). Memory quiet-run-build-lane. Recreated 2026-11-08 after a reboot.
MAX=3600; [ "$1" = "--max-wait" ] && { MAX=$2; shift 2; }
D="$(dirname "$(readlink -f "$0")")"
exec bash "$D/hold_slots.sh" bash -c '
  MAX=$1; shift; t0=$(date +%s)
  while :; do
    load=$(cut -d" " -f1 /proc/loadavg)
    busy=0; who=""; for p in $(pgrep -f "[p]laywright test|node .*[v]ite|[p]ytest|[u]vicorn"); do c=$(tr "\0" " " </proc/$p/cmdline 2>/dev/null); case "$c" in *quiet_run*|*hold_slots*|*quiet_batch*|"") ;; *) busy=$((busy+1)); who="$who $p";; esac; done
    ports=$(ss -ltn | grep -cE ":(3000|4173|5173|8000)\b")
    if awk -v l="$load" "BEGIN{exit !(l<1.5)}" && [ "$busy" -eq 0 ] && [ "$ports" -eq 0 ]; then
      echo "quiet_run: prechecks passed after $(( $(date +%s)-t0 ))s"; uptime; exec "$@"
    fi
    [ $(( $(date +%s)-t0 )) -ge "$MAX" ] && { echo "quiet_run: never quiet in ${MAX}s (load=$load busy=$busy [$who] ports=$ports)"; exit 75; }
    sleep 10
  done' quiet "$MAX" "$@"
