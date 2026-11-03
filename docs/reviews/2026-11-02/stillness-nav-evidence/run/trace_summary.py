#!/usr/bin/env python3
"""Name the main-thread work that fills a maximum gap, from a CDP Tracing trace.  Usage: trace_summary.py <results.jsonl>

For each RESULT row with a tracePath: map the page clock to trace time with the 'snl-anchor' user-timing mark
(performance.mark inside the traced page), take the gap window [triggeredAt + gapStartMs, triggeredAt + gapEndMs],
and list the renderer main-thread tasks (RunTask) that overlap it, with the nested events that hold the time
(FunctionCall with script URL and function, EvaluateScript, compile, layout, paint, GC, timers, event dispatch).
A trace adds overhead: it names work, it never counts misses.
"""
import collections
import json
import sys

WRAPPERS = {'ThreadControllerImpl::RunTask', 'RunTask', 'BlinkScheduler_PerformMicrotaskCheckpoint', 'EpollEvent',
            'SimpleWatcher::OnHandleReady', 'Receive mojo message', 'ThreadPool_RunTask'}


def label(e):
    a = (e.get('args') or {}).get('data') or {}
    n = e['name']
    if n == 'FunctionCall':
        return f"FunctionCall {a.get('functionName') or '(anonymous)'} @ {str(a.get('url') or '')[-70:]}:{a.get('lineNumber')}"
    if n in ('EvaluateScript', 'v8.compile', 'v8.compileModule', 'v8.produceCache', 'v8.parseOnBackgroundParsing'):
        return f"{n} {str(a.get('url') or a.get('fileName') or '')[-70:]}"
    if n == 'EventDispatch':
        return f"EventDispatch {a.get('type')}"
    if n == 'TimerFire':
        return f"TimerFire id={a.get('timerId')}"
    if n == 'RunMicrotasks' or n.startswith('V8.'):
        return n
    return n


def main(path):
    for line in open(path):
        r = json.loads(line)
        tp = r.get('tracePath')
        if not tp:
            continue
        import gzip
        import os
        # Raw traces are 2.5-4.5 MB: only the three baseline-miss traces are committed, gzipped next to the jsonl.
        gz = os.path.join(os.path.dirname(os.path.abspath(path)), os.path.basename(tp) + '.gz')
        d = json.load(gzip.open(gz)) if (not os.path.exists(tp) and os.path.exists(gz)) else json.load(open(tp))
        ev = d['traceEvents'] if isinstance(d, dict) else d
        anchor = next(e for e in ev if e['name'] == 'snl-anchor')
        a_ts, a_page = anchor['ts'], anchor['args']['data']['startTime']
        pid, tid = anchor['pid'], anchor['tid']
        to_ts = lambda page_ms: a_ts + (page_ms - a_page) * 1000.0
        w0 = to_ts(r['triggeredAt'] + r['gapStartMs'])
        w1 = to_ts(r['triggeredAt'] + r['gapEndMs'])
        rel = lambda ts: (ts - to_ts(r['triggeredAt'])) / 1000.0
        main_ev = sorted((e for e in ev if e.get('ph') == 'X' and e['pid'] == pid and e['tid'] == tid and 'dur' in e),
                         key=lambda e: (e['ts'], -e['dur']))
        tasks = [e for e in main_ev if e['name'] == 'RunTask' and e['ts'] < w1 and e['ts'] + e['dur'] > w0]
        busy = sum(min(t['ts'] + t['dur'], w1) - max(t['ts'], w0) for t in tasks) / 1000.0
        print(f"### {r['id']}")
        print(f"- maxGap {r['maxGap']} ms; gap window {r['gapStartMs']}..{r['gapEndMs']} ms after the trigger "
              f"({(w1 - w0) / 1000.0:.1f} ms); main-thread RunTask time inside it {busy:.1f} ms "
              f"({100 * busy / max((w1 - w0) / 1000.0, 1e-9):.0f}%); trace {tp.split('/')[-1]}")
        small = [t for t in tasks if t['dur'] < 1000]
        big = [t for t in tasks if t['dur'] >= 1000]
        if small:
            print(f"  - {len(small)} main-thread task(s) under 1 ms, {sum(t['dur'] for t in small) / 1000.0:.1f} ms in all")
        for t in big[:12]:
            kids = [e for e in main_ev if e is not t and e['ts'] >= t['ts'] and e['ts'] + e['dur'] <= t['ts'] + t['dur'] and e['name'] not in WRAPPERS]
            # self time: duration minus the durations of the events nested directly in it
            selfs = collections.Counter()
            stack = []
            for e in kids:
                while stack and stack[-1][1] <= e['ts']:
                    stack.pop()
                if stack:
                    selfs[stack[-1][2]] -= e['dur']
                selfs[label(e)] += e['dur']
                stack.append((e, e['ts'] + e['dur'], label(e)))
            top = ', '.join(f"{k} {v / 1000.0:.1f} ms" for k, v in selfs.most_common(5) if v > 0)
            print(f"  - task at {rel(t['ts']):+.1f} ms, {t['dur'] / 1000.0:.1f} ms long: {top or '(no nested events)'}")
        if len(big) > 12:
            print(f"  - ... {len(big) - 12} more tasks of 1 ms or more")
        ticks = [e for e in main_ev if e['name'] == 'FunctionCall' and (e['args'].get('data') or {}).get('functionName') == 'tick']
        near = [rel(e['ts']) for e in ticks if w0 - 60000 < e['ts'] < w1 + 30000]
        print(f"  - sampler tick calls around the gap (ms after trigger): {', '.join(f'{x:+.0f}' for x in near)}")
        print()


main(sys.argv[1])
