# STATUS — Senior report Claude doc (SENIOR-REPORT-DOC), 2026-11-14

Doc: "Asclexis — Senior Report (MVP)" https://claude.ai/artifact/3dmFD3B2zsWcvF2d4J8tEm
(doc id [redacted]; tab [redacted]; body node [redacted]; chart widget [redacted])
As-of chip 2026-11-14. Numbers refreshed to origin/main c60be508 where stated; otherwise the draft's dated values (basis e5c7bf80).

## Sections (numbering matches PR #614)
| Section | Covers |
|---|---|
| Executive summary | What Asclexis is, MVP status table, headline numbers (n/window/source), what changed 11-11..11-14, what is not shown |
| 1.1-1.7 | Problem, architecture table, documents/extraction, assistant, safety layers, meds/export/backup, change since 09-27 |
| 1.8 (new) | Windows support: #316, #653 (+ Opus review, 2 owner runs), #657, #658, #660 (owner real-hardware catch); limits |
| 2, 3 | ModelRunner, local-only providers, D12 external runner, local-model baseline (n=20); product eval table |
| 4.1-4.7 | Eras, Claude Code, Codex, Devin, Cursor, others, lessons (+ owner-on-hardware lesson) |
| 5.1-5.5 | 24 failure modes (22-24 added), green-suite lesson, measure-then-claim, quiet box + 3 flake diagnoses (UIDOC-006A, MEDS-G font #640/#621, pass-3 clock #664), test-count chart |
| 5.6 (new) | Agentic alignment eval: licence, weaken, evidence, scorecard, judge (#662, designed, calibration pending) |
| 6.1-6.5 | Tiers (dated 09-28), build program, routing history, 6.4 cost/stops + response status, 6.5 workflow options + CI before/after + scorecard |
| 7, 8 | Context, MCP, skills, hooks, token efficiency; RSI tracks, replay gate, runs, RRSI, donation gate |
| 9-12 | Related work, limitations, future work/open items, conclusion |
| 13, App A-D | Short references, May-claims status, reproduce-numbers table (c60be508), owner decisions (ids + verbatim), sources/method |

## Sources used
part-1-draft-map.md, part-2-landed.md, part-3-metrics.md; report artifact [redacted] (markdown extracted); workflow artifact [redacted] (linked, not re-read in full); gh pr view 660-665, 264, 614, 239; plans-1112/owner-answers-1112b.md; live git on origin/main c60be508 (commits, trailers, modes, CI jobs, slot, PYSLOTS, modules, skills, migrations, golden; slot history via git log -G).

## Refresh after the 7-day perf re-run (~2026-11-20)
- §6.5 CI before/after table (after n=8 -> 7-day window), "Read with care" paragraph, exec-summary CI row.
- §6.5 scorecard rows (add W46/W47 full weeks).
- Exec summary + App B: merged PRs (651), commits (3993/2653), count slot (5114), latest measured count.
- §5.4 stillness: add CI confirmation if available. §1.8: #657 owner re-run.
- §5.6: judge calibration result once the owner labels PRs.
Command: python3 ~/hc-quiet-logs/perf-monitor/measure.py --since 2026-11-13T09:19:18Z --until 2026-11-20T09:19:18Z --local

## Open placeholders / [unverified] in the doc
- Audit-coverage route re-check (§1.5); backup master-copy re-check after #603 (§1.6, App A).
- D12 warning UI component not opened (§2).
- Compliance matrix not re-scored; AUD-05/GATE-13 parse issue (§3).
- Trailer counts per model at c60be508 (§6.3); RSI rule/fixture counts and promotions after #341 (§8.2, 8.3).
- QUIET_WINDOW owner value (§6.5); #657 owner re-run (§1.8).
- Off-repo: 7 h quiet-box freeze, tool-call analysis, perf logs, stillness/clock logs.
- PHASE 2 placeholders from #614 were dropped from the doc (not stakeholder-facing).
