#!/usr/bin/env bash
# STILLNESS-NAV-LATE Task 1 (and Task 2's RED): one wrapped measurement. Run it ONLY through
#   /tmp/claude-1000/quiet_run.sh --max-wait 7200 run/run_wrap.sh <A|B|C> <logdir> > <log> 2>&1; echo EXIT=$? >> <log>
# quiet_run refuses a listener on 3000/4173/5173/8000, so this script starts vite dev / vite preview itself, after
# quiet_run's precheck, and stops only its own PIDs on exit.
#
#   A  baseline: warm-up (declared, uncounted), then 3 batches of probe set + bare-timer set (5 + 5 runs each)
#   B  variants: warm-up, then 3 batches of 16 units x (5 control + 5 variant runs)
#   C  trace: 10 cycles of the baseline probe with CDP Tracing (first 3 misses kept), then 5 runs counting
#      DEBUG=pw:protocol messages in the probe window
#
# Before EACH batch: wait (bounded, 30 min) for the 1-minute load < 1.5, then log uptime, pgrep, ss with own PIDs marked.
# The run/ directory is copied to a scratch dir with node_modules and src symlinked in; nothing is written in the tree
# except the log directory. Env: PREVIEW_DIST (a `vite build --outDir` of this tree), SCRATCH, MAX_LOAD_WAIT.
set -u
WRAP=${1:?wrap A|B|C}
LOGDIR=${2:?log dir}
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(git -C "$HERE" rev-parse --show-toplevel)
FE="$ROOT/src/frontend"
SCR=${SCRATCH:-/tmp/claude-1000/snl-scratch-$WRAP}
DIST=${PREVIEW_DIST:-/tmp/claude-1000/snl-dist}
MAX_LOAD_WAIT=${MAX_LOAD_WAIT:-1800}
export VITE_API_URL=http://127.0.0.1:8000/api/v1
export FORCE_COLOR=0 NO_COLOR=1
mkdir -p "$LOGDIR"
MYPIDS_FILE=$(mktemp)

echo "=== wrap $WRAP start $(date -Is) host=$(hostname) head=$(git -C "$ROOT" rev-parse HEAD) base=$(git -C "$ROOT" rev-parse origin/main)"
git -C "$ROOT" status --short src | head -3
uptime

# ---- scratch copy of run/, with the variants generated from the committed instrumented gates ----
rm -rf "$SCR"; mkdir -p "$SCR/e2e/support"
cp "$HERE/nav-sets.spec.ts" "$HERE/playwright.config.ts" "$SCR/"
cp "$HERE/gates.instrumented.ts" "$SCR/e2e/support/gates.ts"
python3 "$HERE/make_variants.py" "$HERE/gates.instrumented.ts" "$SCR/e2e/support" || exit 2
cp "$FE/e2e/support/mockApi.ts" "$SCR/e2e/support/mockApi.ts"
ln -s "$FE/node_modules" "$SCR/node_modules"
ln -s "$FE/src" "$SCR/src"
cat > "$SCR/vite.nohmr.config.ts" <<CFG
import { defineConfig } from 'vite';
import base from '$FE/vite.config';
export default defineConfig(async (env) => {
  const b = typeof base === 'function' ? await (base as any)(env) : base;
  return { ...b, server: { ...b.server, hmr: false } };
});
CFG
# the gates the sets run are the committed instrumented copy: show it differs from src only by logging lines
diff "$FE/e2e/support/gates.ts" "$SCR/e2e/support/gates.ts" | grep -c '^[<>]' | sed 's/^/gates diff lines vs src: /'
diff "$FE/e2e/support/gates.ts" "$SCR/e2e/support/gates.ts" | grep '^<' | head -3

# ---- own processes ----
mine() { pstree -p $$ 2>/dev/null | grep -o '([0-9]*)' | tr -d '()'; }
annotate() { awk -v mine="$(mine | tr '\n' ' ')" '{ tag = (index(" " mine " ", " " $1 " ") ? "[mine] " : "[FOREIGN] "); print tag $0 }'; }
cleanup() {
  echo "=== cleanup: stopping own servers: $(cat "$MYPIDS_FILE" | tr '\n' ' ')"
  for p in $(cat "$MYPIDS_FILE"); do pkill -TERM -P "$p" 2>/dev/null; kill -TERM "$p" 2>/dev/null; done
  sleep 2
  for p in $(cat "$MYPIDS_FILE"); do pkill -KILL -P "$p" 2>/dev/null; kill -KILL "$p" 2>/dev/null; done
  rm -f "$MYPIDS_FILE"
  echo "=== wrap $WRAP end $(date -Is)"; uptime
}
trap cleanup EXIT

start_server() { # name, port, cmd...
  local name=$1 port=$2; shift 2
  ( cd "$FE" && exec "$@" ) > "$LOGDIR/server-$WRAP-$name.log" 2>&1 &
  echo $! >> "$MYPIDS_FILE"
  for _ in $(seq 1 120); do curl -sf -o /dev/null "http://127.0.0.1:$port/" && { echo "server $name up on :$port pid=$! (mine)"; return 0; }; sleep 1; done
  echo "server $name did NOT come up on :$port"; return 1
}

precheck() { # label
  local end=$(( $(date +%s) + MAX_LOAD_WAIT )) l
  while :; do
    l=$(cut -d' ' -f1 /proc/loadavg)
    if awk "BEGIN{exit !($l < 1.5)}"; then break; fi
    if [ "$(date +%s)" -ge "$end" ]; then
      echo "PRECHECK TIMEOUT before $1: load $l after ${MAX_LOAD_WAIT}s"; pgrep -fa '[p]laywright|[v]ite|[p]ytest|[c]hrom|[c]argo|[r]ustc|[r]ust-lld' | annotate; return 1
    fi
    sleep 15
  done
  echo "--- precheck before $1 at $(date -Is)"
  uptime
  echo "pgrep (playwright|vite|pytest|chrom|cargo|rustc|rust-lld):"
  pgrep -fa '[p]laywright|[v]ite|[p]ytest|[c]hrom|[c]argo|[r]ustc|[r]ust-lld' | cut -c1-170 | annotate
  echo "ss (3000|4173|5173|8000):"
  ss -ltnp | grep -E ':(3000|4173|5173|8000)\b' | awk '{print}' | sed 's/^/  /'
  echo "(own server pids: $(cat "$MYPIDS_FILE" | tr '\n' ' '))"
}

run_batch() { # label plan-name batch [extra env...]
  local label=$1 plan=$2 batch=$3; shift 3
  local pf="$SCR/plan-$label.json" out="$LOGDIR/$label" filter="cat"
  [ "$plan" = Ccdp ] && filter="awk -f $HERE/cdp_count.awk"
  python3 "$HERE/gen_plan.py" "$plan" "$batch" > "$pf" || return 2
  : > "$out.jsonl"
  precheck "$label" > "$out.precheck.log" 2>&1; local rc=$?
  cat "$out.precheck.log"
  [ $rc -eq 0 ] || { echo "EXIT=75 (box not quiet before $label)" > "$out.log"; return 75; }
  {
    echo "=== batch $label plan=$plan batch=$batch start $(date -Is) cases=$(python3 -c "import json;print(len(json.load(open('$pf'))))")"
    uptime
    ( set -o pipefail; cd "$SCR" && env MEAS_PLAN_FILE="$pf" MEAS_OUT="$out.jsonl" MEAS_TRACE_DIR="$LOGDIR" "$@" \
        ./node_modules/.bin/playwright test -c playwright.config.ts --output "/tmp/claude-1000/snl-pwout-$WRAP-$label" 2>&1 | $filter )
    echo "playwright exit=$?"
    echo "=== batch $label end $(date -Is)"
    uptime
  } > "$out.log" 2>&1
  echo "batch $label done: $(grep -c '^RESULT' "$out.log") RESULT lines; $(grep -c . "$out.jsonl") jsonl rows"
}

case "$WRAP" in
A|B)
  precheck "pre-start" || exit 75
  start_server dev 3000 ./node_modules/.bin/vite --host 127.0.0.1 --port 3000 --strictPort || exit 3
  if [ "$WRAP" = B ]; then
    [ -f "$DIST/index.html" ] || { echo "no preview build at $DIST"; exit 3; }
    start_server preview 4173 ./node_modules/.bin/vite preview --host 127.0.0.1 --port 4173 --strictPort --outDir "$DIST" || exit 3
    start_server nohmr 3001 ./node_modules/.bin/vite --config "$SCR/vite.nohmr.config.ts" --host 127.0.0.1 --port 3001 --strictPort || exit 3
    run_batch warmB warmB 0 || exit $?
  else
    run_batch warmA warmA 0 || exit $?
  fi
  for b in 1 2 3; do run_batch "$WRAP$b" "$WRAP" "$b" || exit $?; done
  ;;
C)
  precheck "pre-start" || exit 75
  start_server dev 3000 ./node_modules/.bin/vite --host 127.0.0.1 --port 3000 --strictPort || exit 3
  run_batch warmC warmA 0 || exit $?
  run_batch C1 C 1 MEAS_TRACE_KEEP_MAX=3 || exit $?
  run_batch C2 Ccdp 1 DEBUG=pw:protocol || exit $?
  ;;
*) echo "unknown wrap $WRAP"; exit 2 ;;
esac
echo "=== all batches done"
