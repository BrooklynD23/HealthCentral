#!/usr/bin/env python3
"""Write the gates-level variants of gates.instrumented.ts, one change each, into <outdir>/gates.<name>.ts.

Usage: make_variants.py <gates.instrumented.ts> <outdir>
Every anchor must match exactly once. Variants live only in this evidence copy, never in src/.
Variants that change the spec (not gates) are flags in nav-sets.spec.ts: lazy:false, noguard, mockdelay:N,
preload, reduced, track, nowait, guard.
"""
import sys

base = open(sys.argv[1]).read()
outdir = sys.argv[2]


def variant(name, *pairs):
    s = base
    for a, b in pairs:
        assert s.count(a) == 1, f"{name}: anchor not found exactly once: {a!r}"
        s = s.replace(a, b)
    open(f"{outdir}/gates.{name}.ts", "w").write(s)


# Candidate 1: the bare timer waits 100 ms between starting the timer and the trigger; so does this probe.
variant(
    "v1",
    ("  await page.evaluate(startSampler, { expected: options.expected, intervalMs: STILLNESS_SAMPLE_MS });\n",
     "  await page.evaluate(startSampler, { expected: options.expected, intervalMs: STILLNESS_SAMPLE_MS });\n  await sleep(100); // VARIANT v1: 100 ms between startSampler and the trigger\n"),
)

# Candidate 4a: ticks driven by requestAnimationFrame instead of setInterval (diagnostic only).
variant(
    "v4a",
    ("  state.timer = window.setInterval(tick, config.intervalMs);\n",
     "  // VARIANT v4a: rAF-driven ticks instead of setInterval (diagnostic only)\n  const raf = () => {\n    tick();\n    if (state.running) requestAnimationFrame(raf);\n  };\n  requestAnimationFrame(raf);\n"),
)

# Candidate 4b: unrounded stamps (diagnostic only).
variant("v4b", ("    const t = Math.round(tx);\n", "    const t = tx; // VARIANT v4b: unrounded stamp (diagnostic only)\n"))

# Candidate 5: snapshot() replaced by a bare stamp push. analyse() will then report failures; only the gap is read.
variant(
    "v5",
    ("    const t = Math.round(tx);\n",
     "    const t = Math.round(tx);\n    // VARIANT v5: a bare stamp push; no style, layout or DOM read\n    if (t >= 0) return { t, pathname: '', route: null, nodes: [], expectedHits: config.expected.map(() => false), dur: performance.now() - tx, n: 0 };\n"),
)

# Task 2 mutant: the navigation settle removed from stillnessProbe (Task 1's RED set must return). Skipped when the
# base is a pre-fix gates.ts that has no settle (the RED copy), so Task 1's wraps still run from the same script.
if "await settleStartPage(page)" in base:
    variant(
        "nosettle",
        ("  if (kind === 'navigation') await settleStartPage(page);\n",
         "  // VARIANT nosettle: the settle before startSampler removed (deliberate break)\n"),
    )
else:
    open(f"{outdir}/gates.nosettle.ts", "w").write(base)
print("ok")
