#!/usr/bin/env python3
"""Write the case list (JSON) for one batch.  Usage: gen_plan.py <plan> <batch>   -> stdout

plans:
  warmA / warmB   declared warm-up (uncounted): every set once per server used by that wrap
  A               baseline: per batch the probe set (5 routes) and the bare-timer set (5), back to back,
                  alternating which goes first (batch 1: probe first, 2: bare first, 3: probe first)
  B               variants: per batch, for every unit a control block and a variant block (5 routes each),
                  alternating which goes first; the unit order rotates by batch
  C               trace: baseline probe, 10 cycles over the 5 routes, CDP Tracing on (keeps the first 3 misses)
  Ccdp            baseline probe, one pass over the 5 routes, with SNL-MARK lines for the DEBUG=pw:protocol count
No randomness: the plan is reproducible from the committed copy.
"""
import json
import sys

ROUTES = ['/timeline', '/search', '/medications/med-fixture-1', '/notifications', '/care-tasks']
SHORT = {'/timeline': 'timeline', '/search': 'search', '/medications/med-fixture-1': 'med', '/notifications': 'notif', '/care-tasks': 'care'}
DEV, PREVIEW, NOHMR = 'http://127.0.0.1:3000', 'http://127.0.0.1:4173', 'http://127.0.0.1:3001'

# (unit, set, flags, base)  candidate numbers from the plan's table in the unit names
UNITS = [
    ('c1-wait100', 'probe', ['gates:v1'], DEV),
    ('c2a-lazy-false', 'probe', ['lazy:false'], DEV),
    ('c2b-bare-track', 'bare', ['track'], DEV),
    ('c3a-noguard', 'probe', ['noguard'], DEV),
    ('c3b-nolisteners', 'probe', ['noguard', 'lazy:false'], DEV),
    ('c4a-raf', 'probe', ['gates:v4a'], DEV),
    ('c4b-unrounded', 'probe', ['gates:v4b'], DEV),
    ('c5-barestamp', 'probe', ['gates:v5'], DEV),
    ('c6a-mock50', 'probe', ['mockdelay:50'], DEV),
    ('c6b-mock150', 'probe', ['mockdelay:150'], DEV),
    ('c7a-preview', 'probe', [], PREVIEW),
    ('c7b-hmr-off', 'probe', [], NOHMR),
    ('c8-preload', 'probe', ['preload'], DEV),
    ('c9-reduced', 'probe', ['reduced'], DEV),
    ('s1-bare-nowait', 'bare', ['nowait'], DEV),
    ('s3-bare-guard', 'bare', ['guard'], DEV),
]


def case(wrap, batch, unit, role, st, flags, base, route, extra=''):
    return {
        'id': f'{wrap}.b{batch}.{unit}.{role}.{st}.{SHORT[route]}{extra}',
        'set': st, 'unit': unit, 'role': role, 'batch': batch, 'route': route, 'base': base, 'flags': flags,
    }


def block(wrap, batch, unit, role, st, flags, base):
    return [case(wrap, batch, unit, role, st, flags, base, r) for r in ROUTES]


def main():
    plan, batch = sys.argv[1], int(sys.argv[2] if len(sys.argv) > 2 else 1)
    out = []
    if plan in ('warmA', 'warmB'):
        for base in ([DEV] if plan == 'warmA' else [DEV, PREVIEW, NOHMR]):
            for st in ('probe', 'bare'):
                flags = ['wscount'] if base in (NOHMR, DEV) else []
                port = base.rsplit(':', 1)[1]
                out += [case(plan, 0, f'warmup-{port}', 'warmup', st, flags if st == 'probe' else [], base, r) for r in ROUTES]
    elif plan == 'A':
        order = ['probe', 'bare'] if batch % 2 == 1 else ['bare', 'probe']
        for st in order:
            out += block('A', batch, 'baseline', 'base', st, [], DEV)
    elif plan == 'B':
        n = len(UNITS)
        rot = (batch - 1) * 5 % n
        units = UNITS[rot:] + UNITS[:rot]
        for k, (unit, st, flags, base) in enumerate(units):
            ctrl = block('B', batch, unit, 'control', st, [], DEV)
            var = block('B', batch, unit, 'variant', st, flags, base)
            out += (ctrl + var) if (batch + k) % 2 == 0 else (var + ctrl)
    elif plan == 'C':
        for cycle in range(10):
            for r in ROUTES:
                out.append(case('C', 1, 'trace', 'base', 'probe', ['trace'], DEV, r, f'.c{cycle + 1}'))
    elif plan == 'Ccdp':
        out += block('Ccdp', 1, 'cdpcount', 'base', 'probe', ['cdpcount'], DEV)
    else:
        raise SystemExit(f'unknown plan {plan}')
    json.dump(out, sys.stdout)


main()
