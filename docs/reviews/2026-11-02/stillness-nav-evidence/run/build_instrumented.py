#!/usr/bin/env python3
"""Build gates.instrumented.ts = src/frontend/e2e/support/gates.ts + the PROBECOST/REQLOG logging lines only.

Usage: build_instrumented.py <gates.ts> <out gates.instrumented.ts>
Every anchor must match exactly once, or the script stops (so a changed gates.ts is never silently half-patched).
L0's 2026-10-27 patch (4 replacements + the gapEndsAtMs/windowMs extension) re-applied on today's head, plus
gapStartsAtMs, triggeredAt, the wall-clock trigger and the request timeline (REQLOG) that candidate 6 asks for.
No bound, sample interval, gap arithmetic or analysis line is changed.
"""
import sys

src, out = sys.argv[1], sys.argv[2]
s = open(src).read()


def rep(a, b):
    global s
    assert s.count(a) == 1, f"anchor not found exactly once: {a!r}"
    s = s.replace(a, b)


# 1. Snap carries the per-tick cost.
rep("  expectedHits: boolean[];\n}", "  expectedHits: boolean[];\n  /** MEASUREMENT ONLY: snapshot() duration in ms and [data-t0] nodes visited */\n  dur?: number;\n  n?: number;\n}")
rep("    const t = Math.round(performance.now());\n", "    const tx = performance.now(); // MEASUREMENT ONLY\n    const t = Math.round(tx);\n")
rep("    return { t, pathname: location.pathname, route, nodes, expectedHits };", "    return { t, pathname: location.pathname, route, nodes, expectedHits, dur: performance.now() - tx, n: nodes.length };")

# 2. Request timeline (candidate 6): the tracker already sees every request; it also records when.
rep("  lastEventAt: number;\n  stop(): void;\n}", "  lastEventAt: number;\n  /** MEASUREMENT ONLY: [kind, Date.now(), url path] for every request event */\n  events: Array<[string, number, string]>;\n  stop(): void;\n}")
rep("const tracker: NetworkTracker = { inFlight, lastEventAt: Date.now(), stop: () => undefined };", "const tracker: NetworkTracker = { inFlight, lastEventAt: Date.now(), events: [], stop: () => undefined };")
rep("  const started = (request: Request) => {\n    tracker.lastEventAt = Date.now();\n", "  const started = (request: Request) => {\n    tracker.lastEventAt = Date.now();\n    tracker.events.push(['start', tracker.lastEventAt, new URL(request.url()).pathname]); // MEASUREMENT ONLY\n")
rep("  const ended = (request: Request) => {\n    tracker.lastEventAt = Date.now();\n", "  const ended = (request: Request) => {\n    tracker.lastEventAt = Date.now();\n    tracker.events.push(['end', tracker.lastEventAt, new URL(request.url()).pathname]); // MEASUREMENT ONLY\n")

# 3. stillnessProbe: keep the wall-clock trigger and the tracker's events for the log.
rep("  let triggeredAt = 0;\n  let elapsedMs = 0;\n", "  let triggeredAt = 0;\n  let elapsedMs = 0;\n  let measWall = 0; // MEASUREMENT ONLY\n  let measEvents: Array<[string, number, string]> = []; // MEASUREMENT ONLY\n")
rep("      const triggeredWall = Date.now();\n", "      const triggeredWall = Date.now();\n      measWall = triggeredWall; // MEASUREMENT ONLY\n")
rep("    } finally {\n      network?.stop();\n    }", "    } finally {\n      measEvents = network?.events ?? []; // MEASUREMENT ONLY\n      network?.stop();\n    }")

# 4. The PROBECOST line, after the sampler dump is read and before any check can throw.
rep("  const snaps = dump.snaps;\n", """  const snaps = dump.snaps;
  // MEASUREMENT ONLY: probe cost per run.
  {
    let mg = 0, gi = -1, maxDur = 0, maxN = 0, sumDur = 0, cnt = 0;
    snaps.forEach((s, i) => {
      if (s.t < triggeredAt) return;
      cnt++; sumDur += s.dur ?? 0;
      maxDur = Math.max(maxDur, s.dur ?? 0); maxN = Math.max(maxN, s.n ?? 0);
      if (i > 0 && s.t - snaps[i - 1].t > mg) { mg = s.t - snaps[i - 1].t; gi = i; }
    });
    const f = (x: number | undefined) => (x ?? NaN).toFixed(1);
    console.log(`PROBECOST\\t${snaps[snaps.length - 1]?.pathname}\\tmaxGap=${mg}\\tdurBeforeGap=${f(gi > 0 ? snaps[gi - 1].dur : undefined)}\\tdurAtGap=${f(gi >= 0 ? snaps[gi].dur : undefined)}\\tmaxDur=${f(maxDur)}\\tmeanDur=${f(cnt ? sumDur / cnt : 0)}\\tnodesMax=${maxN}\\tnodesAtGap=${gi >= 0 ? snaps[gi].n : -1}\\tpostSamples=${cnt}\\tgapStartsAtMs=${gi > 0 ? snaps[gi - 1].t - triggeredAt : -1}\\tgapEndsAtMs=${gi >= 0 ? snaps[gi].t - triggeredAt : -1}\\twindowMs=${snaps[snaps.length - 1].t - triggeredAt}\\ttriggeredAt=${triggeredAt}`);
    console.log(`REQLOG\\t${measEvents.map(([k, at, p]) => `${k}:${at - measWall}:${p}`).join(' ')}`);
  }
""")
open(out, "w").write(s)
print(f"wrote {out}")
