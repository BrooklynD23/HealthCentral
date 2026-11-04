#!/usr/bin/env python3
"""Tally the RESULT jsonl files of a wrap.  Usage: tally.py [--runs] <file.jsonl>...

A miss is a run whose maximum gap (PROBECOST maxGap, or the bare timer's max gap) is over 40 ms. Nothing is
re-run, dropped or reclassified: runs without a measurement are listed as 'unmeasured' and counted as neither.
--runs prints every run on one line (the raw RED/GREEN lines).
"""
import collections
import json
import sys

BOUND = 40
args = [a for a in sys.argv[1:] if not a.startswith('--')]
show_runs = '--runs' in sys.argv
rows = []
for f in args:
    for line in open(f):
        line = line.strip()
        if line:
            rows.append(json.loads(line))
rows = [r for r in rows if 'skippedBecause' not in r]
SHORT = {'/timeline': 'timeline', '/search': 'search', '/medications/med-fixture-1': 'med', '/notifications': 'notif', '/care-tasks': 'care'}


def fmt(g):
    return f'{g:g}'


def tally(rs):
    ok = [r for r in rs if r.get('measured') and r.get('maxGap') == r.get('maxGap')]
    miss = [r for r in ok if r['maxGap'] > BOUND]
    return len(miss), len(ok), len(rs) - len(ok)


def runline(r):
    lt = ';'.join(f"{t['startMs']}+{t['durMs']}" for t in r.get('longtasks', [])) or '-'
    return (f"{r['id']}\tgap={fmt(r.get('maxGap', float('nan')))}\tgapStart={r.get('gapStartMs')}\tgapEnd={r.get('gapEndMs')}"
            f"\tlongtasks={lt}\tload1={r.get('load1Start')}/{r.get('load1End')}"
            + (f"\tERROR={r['error']}" if r.get('error') else '') + (f"\tprobe={r['probeError'][:60]}" if r.get('probeError') else ''))


groups = collections.OrderedDict()
for r in rows:
    groups.setdefault((r['unit'], r['set'], r['role']), []).append(r)

units = collections.OrderedDict()
for (unit, st, role), rs in groups.items():
    units.setdefault(unit, []).append((st, role, rs))

for unit, parts in units.items():
    print(f'### {unit}')
    for st, role, rs in parts:
        m, n, bad = tally(rs)
        per = collections.OrderedDict()
        for r in rs:
            per.setdefault(r['batch'], []).append(r)
        perb = ' '.join(f'b{b}:{tally(x)[0]}/{tally(x)[1]}' for b, x in per.items())
        gaps = ' '.join(f"{SHORT.get(r['route'], r['route'])}={fmt(r.get('maxGap', float('nan')))}" for r in rs)
        sub = [r for r in rs if r.get('measured')]
        mx = max((r['maxGap'] for r in sub), default=float('nan'))
        print(f'- {st} {role}: {m} of {n} over {BOUND} ms (pooled); per batch {perb}; unmeasured {bad}; max {fmt(mx)}')
        print(f'  gaps: {gaps}')
    if show_runs:
        for st, role, rs in parts:
            for r in rs:
                print('  ' + runline(r))
    print()
