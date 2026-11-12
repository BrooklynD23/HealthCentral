# Diagnosis kit

Tools for finding why a timing-sensitive Playwright test is flaky. No product code.

Start with a bare timer and 20 traced runs before anything else.

## Files

| File | What it does |
|---|---|
| `diag-hooks.ts` | Playwright file-level hooks. Throttles CPU, records a Chromium trace with the V8 sampler, and dumps each stillnessProbe's largest sample gaps plus long-task and long-animation-frame entries to JSON. |
| `gap_attrib.py` | Reads the JSON and trace files and says which main-thread work sat inside each largest gap. |
| `tick_delay.py` | For the largest gap of each traced run, shows when the next sampler tick was due, when it ran, and what ran in between. |

## Env vars (read by `diag-hooks.ts`)

| Var | Meaning |
|---|---|
| `HC_PROBE_CPU` | CDP CPU throttle factor for the whole test (default 1). |
| `HC_DIAG_TRACE` | `1` records a Chromium trace with the V8 sampling profiler. |
| `HC_DIAG_OUT` | Output dir (default `/dev/shm/uidoc-diag`). |
| `HC_DIAG_WARM` | `1` warms the page before the measured run. |

## Usage

```
python3 scripts/diag-kit/gap_attrib.py <dir with <name>.json + <name>.trace.json> [min_gap_ms]
python3 scripts/diag-kit/tick_delay.py <dir>...
```

## Rules

- Diag runs go through `scripts/quiet_run.sh`.
- Never change a test bound or a spec body.
- Paste `diag-hooks.ts` into a spec in a throwaway worktree only. Never commit it into a spec.
- Diagnosis budget: 60 run-minutes or 3 lines of 20 runs, then report.
