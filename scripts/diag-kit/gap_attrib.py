#!/usr/bin/env python3
"""UIDOC-006A-FLAKE: attribute each stillnessProbe max sample gap to the renderer main-thread work inside it.
Usage: gap_attrib.py <dir with <name>.json + <name>.trace.json> [min_gap_ms]
Alignment: the afterEach performance.mark('hc-align') appears in the trace (blink.user_timing) with a monotonic ts;
offset = ts_ms - mark.startTime maps page performance.now() to trace time."""
import collections, glob, json, os, sys
D = sys.argv[1]; MIN = float(sys.argv[2]) if len(sys.argv) > 2 else 0
TOP = {"ThreadControllerImpl::RunTask"}
SHOW = {"TimerFire","FunctionCall","EventDispatch","Layout","UpdateLayoutTree","Paint","PrePaint","FireAnimationFrame","EvaluateScript",
        "RunMicrotasks","v8.run","XHRReadyStateChange","XHRLoad","ParseHTML","Commit","MajorGC","MinorGC","V8.GC_SCAVENGER","HitTest",
        "ResourceReceiveResponse","ResourceFinish","ParseAuthorStyleSheet","ScheduleStyleRecalculation","v8.compile","v8.compileModule",
        "IntersectionObserverController::computeIntersections","Layerize","UpdateLayer","ResizeObserverController::ShouldDeliverObservations",
        "BlinkGC.AtomicPhase","CpuProfiler::StartProfiling","v8.callFunction","PaintImage","ProfileCall"}
def load_trace(p):
    d = json.load(open(p, encoding="utf-8")); return d["traceEvents"] if isinstance(d, dict) else d
def prof_samples(ev, pid, tid):
    """V8 cpu profile samples -> list of (ts_us, stack[list of (fn,url,line)]) for the given thread."""
    nodes = {}; parent = {}; out = []
    profs = [e for e in ev if e.get("name") == "Profile" and e.get("pid") == pid and e.get("tid") == tid]
    ids = {e.get("id") for e in profs}
    chunks = sorted([e for e in ev if e.get("name") in ("Profile", "ProfileChunk") and e.get("pid") == pid and e.get("id") in ids], key=lambda e: e["ts"])
    start = None; t = None
    for e in chunks:
        data = e.get("args", {}).get("data", {})
        if e["name"] == "Profile":
            start = data.get("startTime"); t = start; continue
        cp = data.get("cpuProfile", {})
        for n in cp.get("nodes", []) or []:
            cf = n.get("callFrame", {}); nodes[n["id"]] = (cf.get("functionName") or "(anon)", (cf.get("url") or "").split("/")[-1].split("?")[0], f"{cf.get('lineNumber')}:{cf.get('columnNumber')}")
            if "parent" in n: parent[n["id"]] = n["parent"]
        if t is None: continue
        lines = data.get("lines") or []; cols = data.get("columns") or []
        for i, (sid, dt) in enumerate(zip(cp.get("samples", []) or [], data.get("timeDeltas", []) or [])):
            t += dt; st = []; x = sid
            while x in nodes: st.append(nodes[x]); x = parent.get(x)
            if st and i < len(lines): st[0] = (st[0][0], st[0][1], f"L{lines[i]}:C{cols[i] if i < len(cols) else '?'}")
            out.append((t, st))
    return out
def main():
    rows = []
    for jp in sorted(glob.glob(os.path.join(D, "*.json"))):
        if jp.endswith(".trace.json"): continue
        rec = json.load(open(jp)); tp = jp[:-5] + ".trace.json"
        if not os.path.exists(tp) or rec.get("align") is None: print("SKIP", os.path.basename(jp), "no trace/align"); continue
        ev = load_trace(tp)
        marks = [e for e in ev if e.get("name") == "hc-align"]
        if not marks: print("SKIP no hc-align in trace", jp); continue
        m = marks[-1]; pid = m["pid"]
        mains = [(e["pid"], e["tid"]) for e in ev if e.get("name") == "thread_name" and e.get("args", {}).get("name") == "CrRendererMain" and e["pid"] == pid]
        tid = mains[0][1] if mains else m["tid"]
        off = m["ts"] / 1000 - rec["align"]  # trace_ms = perf_ms + off
        th = sorted([e for e in ev if e.get("pid") == pid and e.get("tid") == tid and e.get("ph") == "X" and "dur" in e], key=lambda e: e["ts"])
        samples = None
        for ci, call in enumerate(rec["calls"]):
            for gi, gap in enumerate(call["top"][:1]):
                if gap["g"] < MIN: continue
                a = (gap["a"] + off) * 1000; b = (gap["b"] + off) * 1000
                print(f"\n=== {rec['name']} cpu={rec['cpu']} status={rec['status']} call#{ci} gap {gap['g']} ms [{gap['a']}..{gap['b']}] nodes={gap['nodes']} err={(rec.get('error') or '')[:90]}")
                tops = [e for e in th if e["name"] in TOP and e["ts"] < b and e["ts"] + e["dur"] > a]
                for t in tops:
                    if t["dur"] < 2000: continue
                    s, en = t["ts"], t["ts"] + t["dur"]
                    kids = [e for e in th if e is not t and e["ts"] >= s and e["ts"] + e["dur"] <= en and e["name"] in SHOW]
                    print(f"  TASK start {(s-a)/1000:+7.1f} ms rel gap-start, dur {t['dur']/1000:6.1f} ms")
                    agg = collections.defaultdict(float)
                    for k in kids:
                        if k["dur"] >= 1500:
                            d = k.get("args", {}).get("data", {}) or {}; bd = k.get("args", {}).get("beginData", {}) or {}
                            info = d.get("functionName") or d.get("type") or d.get("timerId") or ""
                            url = (d.get("url") or bd.get("url") or "").split("/")[-1].split("?")[0]
                            extra = f"dirty={bd.get('dirtyObjects')}/{bd.get('totalObjects')}" if bd.get("dirtyObjects") else (f"elements={d.get('elementCount')}" if d.get("elementCount") else "")
                            print(f"     {(k['ts']-s)/1000:6.1f} {k['dur']/1000:6.1f} {k['name'][:24]:24} {str(info)[:28]:28} {url[:34]:34} {extra}")
                    if samples is None: samples = prof_samples(ev, pid, tid)
                    win = sorted([(ts, st) for ts, st in samples if s <= ts <= en and st], key=lambda x: x[0])
                    inwin = [st for ts, st in win]
                    wts = [((win[i + 1][0] if i + 1 < len(win) else en) - win[i][0]) / 1000 for i in range(len(win))]
                    if inwin:
                        self_c = collections.Counter()
                        for st, w in zip(inwin, wts): self_c[f"{st[0][0]} {st[0][1]}:{st[0][2]}"] += round(w, 2)
                        comp = collections.Counter()
                        for st, w in zip(inwin, wts):
                            # innermost app frame from src/ (not node_modules, not chunk-*), else innermost named frame
                            app = next((f for f in st if f[1] and not f[1].startswith("chunk-") and "node_modules" not in f[1] and f[1].endswith((".tsx",".ts",".js")) and f[1] not in ("react-dom.js",)), None)
                            comp[f"{app[0]} {app[1]}:{app[2]}" if app else "(no app frame)"] += round(w, 2)
                        tot = len(inwin)
                        print(f"     cpu-profile samples {tot}, time-weighted ms; top self: " + "; ".join(f"{k} {v:.1f}ms" for k, v in self_c.most_common(6)))
                        print(f"     innermost app frame (ms): " + "; ".join(f"{k} {v:.1f}" for k, v in comp.most_common(8)))
                rows.append((rec["name"], rec["cpu"], rec["status"], ci, gap["g"], len(tops), max((t["dur"] for t in tops), default=0) / 1000))
    print("\nSUMMARY name cpu status call gap tasks_in_gap longest_task_ms")
    for r in rows: print(" ", *r)
main()
