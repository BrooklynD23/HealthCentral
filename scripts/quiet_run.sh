#!/usr/bin/env bash
# quiet_run.sh [--max-wait S] <cmd>: claim the pytest slots FIRST (hold_slots.sh), then wait until the box is quiet
# (load1 < 1.5, no foreign playwright/vite/pytest/uvicorn, no listener on 3000/4173/5173/8000), then run <cmd>.
# Exit 75 = never quiet within S (default 3600). Memory quiet-run-build-lane. Recreated 2026-11-08 after a reboot.
# Quiet window (WF-QUIET-WINDOW, off unless set): QUIET_WINDOW="22:00-07:00" (local time, may wrap midnight) makes this refuse
# to start outside the window (exit 76) unless QUIET_FORCE=1. A forced run outside the window is capped at QUIET_MAX_MIN
# minutes (default 30) and killed (TERM, then KILL after 10 s) when the cap is hit; the locks are released when it exits.
# The cap times the command only, not the quiet precheck wait (that has --max-wait). Inside the window there is no cap.
export CAP=""
if [ -n "$QUIET_WINDOW" ]; then
  if [[ "$QUIET_WINDOW" =~ ^([0-9]{1,2}):([0-9]{2})-([0-9]{1,2}):([0-9]{2})$ ]]; then
    s=$((10#${BASH_REMATCH[1]}*60+10#${BASH_REMATCH[2]})); e=$((10#${BASH_REMATCH[3]}*60+10#${BASH_REMATCH[4]}))
    now=$((10#$(date +%H)*60+10#$(date +%M)))
    if [ "$s" -le "$e" ]; then [ "$now" -ge "$s" ] && [ "$now" -lt "$e" ]; else [ "$now" -ge "$s" ] || [ "$now" -lt "$e" ]; fi
    inwin=$?
  else
    echo "quiet_run: bad QUIET_WINDOW '$QUIET_WINDOW' (want HH:MM-HH:MM)" >&2; exit 64
  fi
  if [ "$inwin" -ne 0 ]; then
    if [ "$QUIET_FORCE" != 1 ]; then
      echo "quiet_run: outside QUIET_WINDOW $QUIET_WINDOW (now $(date +%H:%M)); set QUIET_FORCE=1 for a run capped at ${QUIET_MAX_MIN:-30} min" >&2; exit 76
    fi
    CAP=$(awk -v m="${QUIET_MAX_MIN:-30}" 'BEGIN{printf "%d", m*60}')
    echo "quiet_run: forced outside QUIET_WINDOW, command capped at ${CAP}s"
  fi
fi
MAX=3600; [ "$1" = "--max-wait" ] && { MAX=$2; shift 2; }
D="$(dirname "$(readlink -f "$0")")"
exec bash "$D/hold_slots.sh" bash -c '
  MAX=$1; shift; t0=$(date +%s)
  while :; do
    load=$(cut -d" " -f1 /proc/loadavg)
    busy=0; who=""; for p in $(pgrep -f "[p]laywright test|node .*[v]ite|[p]ytest|[u]vicorn"); do c=$(tr "\0" " " </proc/$p/cmdline 2>/dev/null); case "$c" in *quiet_run*|*hold_slots*|*quiet_batch*|"") ;; *) busy=$((busy+1)); who="$who $p";; esac; done
    ports=$(ss -ltn | grep -cE ":(3000|4173|5173|8000)\b")
    if awk -v l="$load" "BEGIN{exit !(l<1.5)}" && [ "$busy" -eq 0 ] && [ "$ports" -eq 0 ]; then
      echo "quiet_run: prechecks passed after $(( $(date +%s)-t0 ))s"; uptime; if [ -n "$CAP" ]; then exec timeout -k 10 "$CAP" "$@"; fi; exec "$@"
    fi
    [ $(( $(date +%s)-t0 )) -ge "$MAX" ] && { echo "quiet_run: never quiet in ${MAX}s (load=$load busy=$busy [$who] ports=$ports)"; exit 75; }
    sleep 10
  done' quiet "$MAX" "$@"
