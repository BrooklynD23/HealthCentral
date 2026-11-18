#!/usr/bin/env python3
"""Apply Task 1's fixed decision rule (plan step 5) to the variant batches.  Usage: verdict.py <B1.jsonl> <B2.jsonl> <B3.jsonl>

A candidate is the cause when
  (i)  removing it alone brings the probe set to 15 of 15 at <= 40 ms, in batches where the baseline probe
       misses 5 or more of 15 (read as the unit's own pooled control, 15 runs over 3 batches; also shown per batch); AND
  (ii) where a bottom-up variant exists, adding it alone to the bare timer brings the bare timer to 5 or more of 15.
The table defines a bottom-up variant for candidate 2 only (c2b). s1 and s3 are supplementary bare-timer variants
that are not in the plan's table; they are printed but are not part of rule (ii).
Candidates 4 and 8 are diagnostic only (never a fix) and are marked so.
"""
import collections
import json
import sys

BOUND = 40
rows = []
for f in sys.argv[1:]:
    rows += [json.loads(l) for l in open(f) if l.strip()]
by = collections.defaultdict(list)
for r in rows:
    by[(r['unit'], r['role'])].append(r)


def miss(rs):
    ok = [r for r in rs if r.get('measured') and r['maxGap'] == r['maxGap']]
    return sum(1 for r in ok if r['maxGap'] > BOUND), len(ok)


def perbatch(rs):
    d = collections.OrderedDict()
    for r in sorted(rs, key=lambda r: r['batch']):
        d.setdefault(r['batch'], []).append(r)
    return ' '.join(f'b{b}:{miss(x)[0]}/{miss(x)[1]}' for b, x in d.items())


def mx(rs):
    v = [r['maxGap'] for r in rs if r.get('measured') and r['maxGap'] == r['maxGap']]
    return max(v) if v else float('nan')


DIAG = {'c4a-raf': 'diagnostic only', 'c4b-unrounded': 'diagnostic only', 'c8-preload': 'diagnostic only'}
BOTTOM_UP = {'c2a-lazy-false': 'c2b-bare-track'}
units = [u for (u, role) in by if role == 'variant']
units = list(dict.fromkeys(units))
units.sort()
print('| unit | set | control misses (pooled; per batch) | variant misses (pooled; per batch) | control max | variant max | (i) | (ii) | note |')
print('|---|---|---|---|---|---|---|---|---|')
ver = {}
for u in units:
    c, v = by[(u, 'control')], by[(u, 'variant')]
    cm, cn = miss(c)
    vm, vn = miss(v)
    st = v[0]['set']
    ci = f"{cm}/{cn} ({perbatch(c)})"
    vi = f"{vm}/{vn} ({perbatch(v)})"
    ctrl_ge5 = cm >= 5
    i_ok = st == 'probe' and ctrl_ge5 and vn == 15 and vm == 0
    ver[u] = (st, cm, vm, vn)
    print(f"| {u} | {st} | {ci} | {vi} | {mx(c):g} | {mx(v):g} | {'yes' if i_ok else ('n/a (bare)' if st == 'bare' else 'no')} | | {DIAG.get(u, '')} |")
print()
for probe_u, bare_u in BOTTOM_UP.items():
    st, cm, vm, vn = ver[bare_u]
    print(f"(ii) for {probe_u}: bottom-up {bare_u}: bare timer with the factor added misses {vm}/{vn}; needs >= 5 -> {'met' if vm >= 5 else 'NOT met'}")
