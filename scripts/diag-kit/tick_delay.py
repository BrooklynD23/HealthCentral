#!/usr/bin/env python3
"""MEDS-G: for the largest gap of each traced run, when the sampler's next setInterval tick was due (gap start + 20 ms)
versus when it ran, what ran on the main thread between those two moments, and how much of that wait the main thread
was idle. Usage: tick_delay.py <dir>..."""
import glob, json, os, sys, statistics
rows = []
for D in sys.argv[1:]:
    for jp in sorted(glob.glob(os.path.join(D, "*.json"))):
        if jp.endswith(".trace.json"): continue
        rec = json.load(open(jp)); tp = jp[:-5] + ".trace.json"
        if not os.path.exists(tp) or not rec.get("calls"): continue
        d = json.load(open(tp)); ev = d["traceEvents"] if isinstance(d, dict) else d
        m = [e for e in ev if e.get("name") == "hc-align"][-1]; pid = m["pid"]
        mains = [e["tid"] for e in ev if e.get("name") == "thread_name" and e.get("args", {}).get("name") == "CrRendererMain" and e["pid"] == pid]
        tid = mains[0] if mains else m["tid"]; off = m["ts"] / 1000 - rec["align"]
        th = [e for e in ev if e.get("pid") == pid and e.get("tid") == tid and e.get("ph") == "X" and "dur" in e]
        tasks = sorted([e for e in th if e["name"] == "ThreadControllerImpl::RunTask"], key=lambda e: e["ts"])
        gap = rec["calls"][-1]["top"][0]
        a = (gap["a"] + off) * 1000; b = (gap["b"] + off) * 1000; due = a + 20000
        def kinds(t):
            s, en = t["ts"], t["ts"] + t["dur"]; out = set()
            for k in th:
                if s <= k["ts"] <= en:
                    dd = k.get("args", {}).get("data", {}) or {}
                    if k["name"] == "FunctionCall" and dd.get("functionName") == "ae": out.add("react-scheduler")
                    elif k["name"] == "EventDispatch" and dd.get("type") in ("pointerdown", "mousedown", "pointerup", "mouseup", "click", "pointerout"): out.add("input")
                    elif k["name"] in ("Paint", "Commit"): out.add("frame")
            return out
        between = [t for t in tasks if t["ts"] + t["dur"] > due and t["ts"] < b - 100]
        busy = sum(min(t["ts"] + t["dur"], b) - max(t["ts"], due) for t in between)
        longest = max((t["dur"] for t in tasks if t["ts"] < b and t["ts"] + t["dur"] > a), default=0)
        ks = set().union(*[kinds(t) for t in between]) if between else set()
        rows.append((rec["name"][-26:], rec["cpu"], gap["g"], round((b - due) / 1000, 1), round(busy / 1000, 1), round(longest / 1000, 1), ",".join(sorted(ks))))
print("run cpu gap_ms tick_late_ms busy_while_late_ms longest_task_in_gap_ms ran_ahead_of_tick")
for r in rows: print(" ", *r)
if rows:
    print("median gap %.1f, median late %.1f, median busy-while-late %.1f, median longest task %.1f" % tuple(statistics.median([r[i] for r in rows]) for i in (2, 3, 4, 5)))
