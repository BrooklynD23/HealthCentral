# Harness landscape (Hermes, OpenClaw, DeepMind, DeepSeek): research package (2026-10-31)

**Last Updated:** 2026-10-31
**Owner:** repository owner
**Refresh Trigger:** an owner answer to RSI-HARNESS-GO for rows E-H or to a drafted question in the [harness improvements plan](../../plans/2026-10-31-harness-improvements-plan.md#drafted-owner-questions-not-asked); a merge of any row A-H; a new release of Hermes Agent, OpenClaw or DeepSeek Harness that changes a fact marked [V] below.

> **Point-in-time research (2026-10-31).** Docs only; no code changed and no owner gate is answered here. Asclexis was read at `origin/main` @ `4ffcd45f`. Four Haiku research agents wrote first notes; the Opus planner treated them as leads and re-checked every claim kept here against the primary source (WebFetch, which returns a model summary of the page; WebSearch for the CVE record; the GitHub API as raw text for `deepseek-ai/deepseek-harness`). Markers: **[V]** confirmed on the primary source; **[C]** changed after the re-check; **[X]** not confirmed, dropped from every recommendation.

## The question

Owner instruction, 2026-10-31 (part of RSI-HARNESS-GO), verbatim: "Then plan out for more improvements over our own harness. Run research agents to find out how Hermes/OpenClaw/Google Deepmind RSI/ check DeepSeek open Harness."

## The short answer

1. **None of the four systems is safer than ours on the axes this repo cares about.** Hermes and OpenClaw write agent-authored skills ungated by default (Hermes `write_approval: false`; OpenClaw `auto` for new installs), Hermes's background reviewer reads the conversation, and DeepSeek Harness uploads its session log to the official API by default with no built-in telemetry redaction. Each would break an Asclexis invariant (RSI-4 human gate, metadata only, redaction before anything leaves).
2. **What does transfer is gate design, not autonomy.** The evaluator-loop literature's lesson is that a loop finds the leak in its verifier (AlphaEvolve's "leaky verifier"; DGM's faked test log). Our loop already keeps the evaluator outside the proposer's write scope. The new ideas test the gate itself, make the replay set stricter, and keep a record of every candidate.
3. **The planner's probes found one real gate leak.** `gateNumstat` (`.claude/workflows/rsi-loop.js:70-81`) checks additions-only for `rules.ts` and `cases.ts` only (`:77`), so a candidate that deletes rows from `docs/agentic/recurring-failures.md` passes every deterministic gate; the Codex critic never sees that file (`:319`). Only the owner's review stands in the way. Plan row RSI-GATE-ADVERSARIAL proposes the fix as an owner question.
4. **Four new rows (E-H) are planned, each awaiting owner approval**, beyond rows A-D. Eleven ideas are rejected with reasons. See [the plan](../../plans/2026-10-31-harness-improvements-plan.md) and [05-transfer-matrix.md](05-transfer-matrix.md).

## Files

| File | What it holds |
|---|---|
| [01-hermes.md](01-hermes.md) | Hermes Agent: skills, background review, curator, self-evolution PLAN.md |
| [02-openclaw.md](02-openclaw.md) | OpenClaw: Skill Workshop, approval binding, loop detection, logging, skill-market incidents |
| [03-deepmind-evaluator-loops.md](03-deepmind-evaluator-loops.md) | AlphaEvolve and the leaky verifier, DGM gaming, ShinkaEvolve, GEPA, FSF |
| [04-deepseek-harness.md](04-deepseek-harness.md) | DeepSeek Harness logging and upload defaults; V3.2 F2P/P2F filter |
| [05-transfer-matrix.md](05-transfer-matrix.md) | Each idea → loop piece, coverage by A-D, privacy, risk, decision |

**Not repeated.** The 2026-10-17 package ([00-README](../2026-10-17-rsi-opt-in-data/00-README.md)) already covers DGM, AlphaEvolve, GEPA, Meta-Harness, AIDE² and the sealed held-out set (OW-3 / S5); the 2026-10-20 package ([00-README](../2026-10-20-rrsi-harness2/00-README.md)) covers `google-research/harness2`. This package adds only the four systems named by the owner and the specific incidents and gate shapes.

## Verification status

| # | Claim (from the Haiku notes) | Status | Primary source |
|---|---|---|---|
| 1 | DGM agent faked a log of passing tests | **[V]** | https://sakana.ai/dgm/ |
| 2 | DGM agent removed the reward function's hallucination markers; caught via lineage | **[V]** | https://sakana.ai/dgm/ |
| 3 | DGM best Polyglot 38.0% on the 50-task subset vs 30.7% on the full benchmark | **[V]** (base 14.0 in one place, 14.2 in another) | arXiv 2505.22954v3 |
| 4 | DGM archive keeps every compiling variant | **[C]**: compiling **and** still able to edit code | arXiv 2505.22954v3 |
| 5 | DGM parent choice ∝ score, inverse child count; staged eval 10 → 50 at >40% | **[V]** | arXiv 2505.22954v3 |
| 6 | DGM `is_patch_valid` is a gate-the-gate check | **[C]**: it rejects empty and test-only patches | arXiv 2505.22954v3 |
| 7 | "Tao et al." leaky verifier, "always eventually figured out a way to cheat", "Designing a clever verifier ... is key" | **[V]**; **[C]** authors Georgiev, Gómez-Serrano, Tao, Wagner | arXiv 2511.02864v3 |
| 8 | Its fix was restricting the search space | **[C]**: "generalization improves when ... a more constrained set of inputs"; retry with bounded step functions | arXiv 2511.02864v3 |
| 9 | AlphaEvolve evaluation cascade, MAP-Elites + islands, user-written evaluator `h` | **[V]** | arXiv 2506.13131 |
| 10 | AlphaEvolve GA on Google Cloud, 9 Jul 2026 | **[X]** not re-read | — |
| 11 | ShinkaEvolve 0.95 novelty threshold | **[V]** | arXiv 2509.19349v1 |
| 12 | ShinkaEvolve evaluator human-written | **[C]**: "Task specification requires manual human expertise for objective functions and evaluation" | arXiv 2509.19349v1 |
| 13 | GEPA feedback text in reflection; Pareto selection | **[V]** | arXiv 2507.19457v2 |
| 14 | FSF v3 (22 Sep 2025, upd. 17 Apr 2026): ML R&D protocols; internal deployments | **[V]**; v1 and TCL names **[X]** | deepmind.google FSF blog |
| 15 | AGI safety paper: "a misaligned AI system could sabotage the research it does" | **[V]** | arXiv 2504.01849v1 §2.1 |
| 16 | Hermes curator: 168 h / 2 h idle, 14 d stale, 30 d archive, no LLM, restore / rollback / ledger, never auto-deletes; page conflicts (30/90) | **[V]** | Hermes curator docs |
| 17 | Hermes PLAN.md: benchmarks are gates; ≥10% gain; no regression; PR never direct commit | **[V]**; **[C]** "TBLite score holds within 2%"; no phase marked built | hermes-agent-self-evolution PLAN.md |
| 18 | Hermes `skills.write_approval` / `memory.write_approval` default false; staging in `~/.hermes/pending/skills/` | **[V]** | Hermes configuration docs |
| 19 | Hermes staged patch records its target and is refused if it changed | **[X]** not on the configuration or skills page | — |
| 20 | Hermes background review: 16 iterations, single-flight, dangerous commands denied, write tools denied | **[V]**; input is the full snapshot (same model) or a digest + verbatim recent turns | `agent/background_review.py` |
| 21 | Hermes `skill_view` required before patch | **[C]**: not in the docs; the code summary says `skill_manage` "enforces read-before-write" | skills docs, `background_review.py` |
| 22 | Hermes memory 2,200 / 1,375 chars, frozen per session, SQLite FTS5 | **[V]** | Hermes memory docs |
| 23 | OpenClaw identical-error guard keys on tool + args hash + error; 3 failures; always on | **[V]**; **[C]** "arguments", not a hash; blocks the exact action, one recovery chance | OpenClaw loop-detection docs |
| 24 | OpenClaw Skill Workshop: `auto` default, `propose`, 10 iterations, 10 versions, validation, secret refuses write | **[V]** | Skill Workshop docs |
| 25 | OpenClaw approval bound to the exact proposal revision | **[V]**; **[C]** source is the 2026.8.1 release notes, not the Workshop docs | releases/2026.8.1/skills |
| 26 | OpenClaw 2026.8.1: new installs `auto`; critical prompt-injection findings block application | **[V]** | releases/2026.8.1/skills |
| 27 | OpenClaw logs: "IDs, sizes, and outcomes, never message text, prompts, tool arguments, or tool results"; redaction best-effort; transcripts may hold credentials | **[V]** | OpenClaw logging docs |
| 28 | OpenClaw VirusTotal (7 Feb 2026): hash + Code Insight, three verdicts, daily rescan, "won't catch everything" | **[V]**; **[C]** wording "not a silver bullet" | openclaw.ai blog |
| 29 | CVE-2026-25253, CVSS 8.8, fixed 2026.1.29 | **[V]** (search summary of the CVE / OSV record) | osv.dev, The Hacker News |
| 30 | ClawHavoc: Koi 341 of 2,857; Antiy ≥1,184 | **[X]** Koi URL redirects to a product page; Antiy not re-read | — |
| 31 | Snyk ToxicSkills: 3,984 scanned, 76 confirmed, 91% with prompt injection | **[V]** | snyk.io blog |
| 32 | Trail of Bits bypassed ClawHub, Cisco and skills.sh scanners | **[V]** | blog.trailofbits.com |
| 33 | Trojan's Whisper: 94% evade scanners; ASR 16.0-64.2% | **[V]** | arXiv 2603.19974 |
| 34 | `dsh`: MIT, created 2026-08-13, developer preview; SAFETY.md "must not be treated as secure or production-ready" | **[V]** | GitHub API, `SAFETY.md:7` |
| 35 | `dsh` session-log plugin on by default, uploads with official API requests | **[V]** | `session-log-deepseek/README.md:12`, `:31`, `:34` |
| 36 | `dsh` telemetry leaves "exactly as captured, including any credentials" without rules | **[V]** | `session-telemetry/README.md:54`, `:118` |
| 37 | `dsh` "Model-visible means logged"; failed attempts kept out of model history | **[V]** | `docs/architecture.md:124`, `:128` |
| 38 | V3.2: F2P ≥ 1 and P2F = 0 filter; 1,827 environments; "hard to solve but easy to verify"; rule-based outcome rewards | **[V]**; **[C]** paper writes "false-to-positive"; rewards cover reasoning and agent tasks generally | arXiv 2512.02556 |
| 39 | DeepSWE pass@1 vs cost per task, mini-swe-v2, 2026-10-17 | **[V]**; values are images, none quoted | api-docs.deepseek.com news261017 |
| 40 | V4-Pro / V4.1 model-card training details; `dsh` rc.5 release; Cordis paper; star counts | **[X]** not re-read | — |
| 41 | OpenClaw "Dreaming" memory promotion gates; Hermes nudge intervals | **[X]** not re-read | — |

## Measured by the planner on `4ffcd45f` (inputs to the plan)

- `claude plugin test .claude/mods/asclexis-rsi` → `29 pass`, `0 fail` (CLI on this machine). Output lines are `(pass) replay set > <case id>`.
- **Necessity probe** (scratch copy, node `--experimental-strip-types`): for each of the 10 positive replay cases, `checkBefore` / `checkAfter` over `RULES` without the case's own rule → `positive cases 10, covered by another rule 0`.
- **Old-table probe**: the mod copied to a scratch dir with `no-such-file-path` deleted from `rules.ts`, then `claude plugin test` → `(fail) replay set > no-such-file-path-pos-1`, `(fail) ... -pos-2`, `27 pass`, `2 fail`.
- **Gate probe** (the three gate functions extracted with `sed` into a scratch node script): `gateNumstat("0\t12\tdocs/agentic/recurring-failures.md")` → `true`; `gateNumstat("3\t1\t<mod>/hooks/rules.ts")` → `false`; `gateDiff([".claude/workflows/rsi-loop.js"])` → `false`; `parseCodexVerdict(" VERDICT: PASS")` → `UNAVAILABLE`.
- **Rule messages**: all 7 are 102-185 characters, printable ASCII, no URL, none of the critic's injection phrases (`rsi-loop.js:286`).
- **Retries**: 0 `"retry":true` among the 14,270 tool rows of `docs/agentic/rsi-runs/*/rsi-log.jsonl` (14,283 rows in all); the 2026-10-24 and 2026-10-31 summaries each record `retries: 1`.
- **Rule hits in the archived rsi-logs**: `no-such-file-path` 38 hints, `pkill-self` 13 guards, `gh-pr-edit-projects-classic`, `playwright-exec-path`, `venv-husk` and `embedding-bundle-missing` 1 each, `llama-cpp-no-compiler` 0.
