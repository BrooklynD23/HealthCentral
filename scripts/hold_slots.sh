#!/usr/bin/env bash
# Hold every pyslot lock for a run, so no new pyslot work starts meanwhile: first the exclusive hold lock
# (hc-pytest.hold.lock, which scripts/pyslot.sh checks before every slot attempt, so it covers ANY PYSLOTS),
# then slots 1..max(8, PYSLOTS). Usage: scripts/hold_slots.sh <command...>
# Bounded: waits HOLD_WAIT s per lock (default 900), then exits 75 naming the holders (memory quiet-run-stall-leaked-lock).
# The command runs with the lock fds closed, so an orphaned child cannot leak a lock (the #490 class); the locks
# last until this script exits. Exports TMPDIR=/dev/shm (memory wsl-disk-fsync-playwright).
# Lives in the repo since HOLD-SLOTS-IN-REPO; the lock files stay in /tmp/claude-1000 (a reboot wipes only the locks).
L=/tmp/claude-1000/hc-pytest; W=${HOLD_WAIT:-900}; export TMPDIR=/dev/shm
n=${PYSLOTS:-3}; [ "$n" -lt 8 ] && n=8
mkdir -p /tmp/claude-1000; fds=()
for i in hold $(seq 1 "$n"); do
  exec {fd}>"$L.$i.lock"; fds+=("$fd")
  if ! flock -w "$W" "$fd"; then
    echo "hold_slots: $([ "$i" = hold ] && echo "hold lock" || echo "slot $i") not free after ${W}s; holders:"; fuser -v "$L.$i.lock" 2>&1 | sed 's/^/  /'; exit 75
  fi
done
echo "hold_slots: holding pytest slots 1-$n, TMPDIR=$TMPDIR"
( for fd in "${fds[@]}"; do exec {fd}>&-; done; exec "$@" )
