#!/usr/bin/env bash
# Run a command (pytest) in one of PYSLOTS machine-wide slots; waits when all are busy.
# Usage: scripts/pyslot.sh <command...>   e.g. scripts/pyslot.sh env HF_HUB_OFFLINE=1 python -m pytest tests/ -q
# ponytail: fixed slot count (default 3, ~2 GB each on the 22 GiB WSL box); raise PYSLOTS with more RAM.
n="${PYSLOTS:-3}"
while :; do
  for i in $(seq 1 "$n"); do
    flock -n -E 75 "/tmp/claude-1000/hc-pytest.$i.lock" "$@"
    rc=$?
    [ "$rc" -ne 75 ] && exit "$rc"
  done
  sleep 5
done
