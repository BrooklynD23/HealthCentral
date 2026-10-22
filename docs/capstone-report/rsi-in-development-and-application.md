# RSI in Development and in the Application

**Last Updated:** 2026-10-17
**Owner:** repository owner
**Refresh Trigger:** any RSI-loop or Track-2 run lands (fill §6); the merge of #122 or the Track-1 mod PR; any owner change to RSI-1..RSI-4, RSI-BUILD or AUTO-MERGE.

Capstone report section. Status labels are strict: nothing here is described as merged unless the source says so. The research package it cites is in PR #122 (`docs/research/2026-10-17-rsi-opt-in-data/`, not yet merged), so it is cited by path and not linked. Owner decisions are recorded in [owner-decisions-2026-09-27.md](owner-decisions-2026-09-27.md) (rows RSI-1..RSI-4, RSI-BUILD, AUTO-MERGE, dated 2026-10-17; on the handoff branch at time of writing).

## 1. What RSI means here

In this project, recursive self-improvement (RSI) is a bounded, human-gated loop: observe how a system fails, propose a small change, test the change against gates the proposer cannot edit, and let the owner decide whether it ships. It is not autonomous model training and not code self-rewriting. The applicability report (`docs/plans/2026-10-10-rsi-loop-applicability-report.md`) places fully self-rewriting designs (AlphaEvolve, Darwin-Godel Machine) out of scope for a local-first medical app, and keeps only ops-level and gated behaviour-level loops. The repository's own term for the idea is the "self-improvement loop" (`docs/features/04_self_improvement_loop.md`).

The owner's direction (2026-10-17) is that one opt-in dataset should serve three uses: fine-tuning small local models, seeding synthetic data, and driving a harness that improves itself from logged runs (`docs/research/2026-10-17-rsi-opt-in-data/00-README.md`). The work is split into two tracks (owner row RSI-4): Track 1 improves the harness that builds the repository; Track 2 improves the application's own local-model behaviour.

## 2. Track 1: development harness

**Status: merged. The Track-1 mod is in main via #127; the `rsi-loop` workflow via #126 and #129. The workflow has not yet been run (see §6).**

Per the handoff (`docs/plans/2026-10-17-session-handoff.md` §2 items 2-3, on the handoff branch), Track 1 has two parts.

**The Claude Code mod `.claude/mods/asclexis-rsi/`.**
- *Observe.* `tool.call` hooks record metadata only (tool, success or failure, duration, retries, denials, edit-then-test-failure cycles) to the git-ignored `.claude/logs/rsi/`. It reuses the conventions of the session-log hook `.claude/hooks/session_log.py`, which already records metadata only (never file contents, command text or tool output, because these may hold PHI or secrets) and always exits 0 so telemetry cannot block work.
- *Report.* A status-line counter and an `/rsi` scoreboard command.
- *Guard and hint rules.* Rules are promoted from mined failures. The initial seeds are the failures measured in the session of 2026-10-17 (table in §5).
- A general-purpose template copy outside the repo is planned; its location is not yet confirmed with the owner.

**The workflow `.claude/workflows/rsi-loop.js`.** It runs as the last stage after every build-program run (owner row RSI-BUILD). The research package defines the loop as six steps (`00-README.md`, section B): (1) log; (2) mine failures; (3) propose; (4) sealed-eval gate; (5) human gate; (6) merge and re-gate. The handoff names the workflow's stages as mine (Haiku clusters failures), reflect (Opus writes GEPA-style reflections), propose (small single-purpose edits only), gate, PR, and measure (before and after per-tool failure rate, retries and tokens per item, with an archive of rejected candidates). The two descriptions cover the same loop; the handoff splits mining from reflection and treats the final merge-and-re-gate as measure. The workflow is merged on main (#126, #129).

Build order set by the owner (RSI-BUILD): mod first, then the workflow, then the application track, in parallel where the workflow allows.

## 3. Track 2: the application

**Status: planned. No Track-2 code exists.**

1. **Evaluation harness on four local models.** The MM-1 script is to be generalised and run on `gemma4:e4b`, `llama3.1:8b`, `qwen3:8b` and `gemma3:12b`. Planned metrics are abstain rate and cited-answer rate (handoff §2 item 4a). The MM-1 baseline is in §5.
2. **LEGACY-CITE-PROMPT via constrained decoding (RSI-3).** MM-1 abstentions occur because the models skip the `[cite:N]` marker and invent references. The cheapest fix in the research is an Ollama `format` JSON schema or a llama.cpp GBNF grammar that forces each sentence to carry a cite index from the valid set. The faithfulness gate stays unchanged and still checks support. Prompt-only two-pass methods and QLoRA on rejection-sampled cited answers are the more expensive alternatives (`00-README.md`, section C). The research notes that no 2024-2026 paper it found measures citation-marker fine-tuning on medical text at 1-12B parameters, so the project's own MM-1 script is the measurement.
3. **RSI-1 opt-in donation pipeline.** The owner chose to build it (RSI-1, overriding the research-only default). The pipeline is:
   1. consent, per purpose and revocable, with revocation deleting the donated set;
   2. local `strict` redaction plus a second PHI detector as a recall check, with recall measured on the project's synthetic vaults; the pipeline calls `modules/redaction.py` and never edits it;
   3. a local-only store (RSI-2: no derived data leaves the device);
   4. a leak evaluation, with canaries planted in the donated set and extraction and membership probes run on the tuned model, any recovered canary blocking the run;
   5. a mix of real and synthetic data, never replacing real data, because replacement risks model collapse.

## 4. Gates and safety rails

- **Human merge.** The owner merges every RSI promotion. The AUTO-MERGE decision allows agents to merge green, review-approved build-program PRs but states that RSI-loop promotions are never agent-merged (RSI-4 human gate).
- **Write scope.** Ask-first modules (`interpret_safety`, `redaction`, `faithfulness`, `verifier_agent`, auth and encryption) are out of the loop's write scope, as are tests, gate scripts and thresholds. The gate rejects any candidate that edits them. This follows `CLAUDE.md` section 3: never weaken a safety check or lower a threshold to make something pass.
- **Replay gate.** A candidate is replayed against a set of past failures and must pass CI. The research adds a sealed held-out set the proposer never sees (owner item OW-3, sealed set S5) and a block on a rising reward-hacking rate even when the headline metric improves.
- **Local-first.** Collection, redaction, training and synthesis run on the user's machine (RSI-2).
- **Redaction invariant.** Anything exported for training or synthesis passes `strict` redaction first. The research treats redaction as a leaky filter, not a guarantee, which is why the leak evaluation is a separate gate.
- **Weights and evaluator.** The Track-1 loop edits harness code only (prompts, workflows, tool routing). The evaluator sits outside the proposer's write scope, following the pattern the research draws from the Darwin-Godel Machine, ADAS, AIDE2 and RRSI.

## 5. Measured baselines

**MM-1 (Track 2).** Abstentions out of 20 prompts, measured on the owner's RTX 3080 host through Ollama 0.40.5 (handoff §1; evidence in PR #72 comments 6226130965 and 6228253080). The handoff records the abstentions as correct: the REPORT FACTS carry no `[cite:N]`, and the models invent ADA/AHA references.

| Model | Abstained (of 20) |
|---|---|
| `gemma4:e4b` | 20 |
| `llama3.1:8b` | 20 |
| `gemma3:12b` | 19 |
| `qwen3:8b` | 15 |

**Track-1 seed failures.** Tool failures encountered in one session (handoff §4 and §2 item 2). These are observations, not rates; they seed guard and hint rules and are not a baseline failure rate.

| Failure | Handling planned |
|---|---|
| `pkill -f "<pattern>"` matched the agent's own shell (exit 144) | Stop servers by port with `lsof -ti:PORT -sTCP:LISTEN \| xargs kill` |
| Playwright bundled browser revision differed from the installed one | Launch with `executablePath` set to the cached chromium |
| `gh pr edit` failed on Projects classic | Use `gh api -X PATCH` |
| Checked-in venv husk files exited 0 without running anything | Re-link the venv after checkout or merge |
| `llama-cpp-python` build with no C compiler | `build-essential` installed on the host; hint rule |

## 6. Results

**Status (2026-10-18).** Track-1 mod merged (#127). The `rsi-loop` workflow is merged (#126, #129) but has not been run: no RSI logs existed before the mod was loaded, so it needs a session started with the mod. The Track-2 evaluation harness is merged (#150) and has produced the baseline below. No constrained-decoding change, leak evaluation or detector-recall measurement exists yet.

**Track-2 baseline (legacy chat citation, before any prompt change).** Measured by `scripts/legacy_cite_eval.py` on the owner's RTX 3080 host through Ollama, one run per model, n=20 questions, exit 0 in 11 m 7 s, with no pytest running. Questions file `questions_v1.json`, sha256 `ecb906035db228f1af9fc2d5698fe9bf9cf0e34bbd88296b5719a8a41c0d990e`. Source: PR #150 comment 6247765961; raw output on the host at `~/asclexis-evals/t2e-2e91ea2/`.

| Model | Abstained | Cited | Uncited | Escalated | Abstain rate | Cited-answer rate |
|---|---|---|---|---|---|---|
| `gemma4:e4b` | 19/20 | 0/20 | 0/20 | 1/20 | 0.95 | 0.00 |
| `llama3.1:8b` | 17/20 | 0/20 | 0/20 | 3/20 | 0.85 | 0.00 |
| `qwen3:8b` | 15/20 | 1/20 | 4/20 | 0/20 | 0.75 | 0.05 |
| `gemma3:12b` | 20/20 | 0/20 | 0/20 | 0/20 | 1.00 | 0.00 |

Against MM-1 (section 5), abstentions plus escalations agree within 2 of 20 for every model. `qwen3:8b` is the only model that produced an uncited answer (4/20) or a cite-value mismatch (1). This is the baseline `LEGACY-CITE-PROMPT` (constrained decoding) will be compared against. With one run per model and n=20 the table shows no ranking.

Results still to come:

| Result | Source of the number |
|---|---|
| Track-1 before and after per-tool failure rate, retries, tokens per item | `.claude/logs/rsi/` scoreboard (`/rsi`) and the `rsi-loop` workflow measure stage, per run |
| Track-2 abstain rate and cited-answer rate on four models, after constrained decoding (the "before" is the table above) | `scripts/legacy_cite_eval.py`; PR bodies carry the counts |
| Leak evaluation (canary recovery) | The RSI-1 leak-eval run; any recovered canary is a blocking result |
| PHI-detector recall | Measurement on the project's synthetic vaults |
| Rejected-candidate archive | The `rsi-loop` archive |

## 7. Limitations and threats to validity

- **Small sample.** MM-1 has n=20 prompts per model, one host and one run each; differences such as 19 versus 20 are not evidence of a ranking.
- **Abstention is not quality.** A correct abstention shows the guard works, not that the model answers well. The abstain count measures how often the citation marker is missing, which is the problem constrained decoding targets; it says nothing about answer correctness. The cited-answer rate is planned for this reason.
- **Measurement interference.** Running the pytest suite during a model run inflates abstain counts because of the 60 s generation timeout (handoff §4); MM-1 must be run alone.
- **Seed failures are anecdotal.** The Track-1 seeds come from one session and carry no frequency information.
- **Source quality.** The research package contains 58 sources, each marked [V] fetched, [S] snippet only, or [U] unverified; [S] and [U] items must be re-checked before citation outside the repo. The sweeps were run by Haiku agents and synthesised by the orchestrator. The package is point-in-time research (2026-10-17).
- **No direct prior evidence for the target setting.** The research found no measurement of citation-marker fine-tuning on medical text at 1-12B.
- **Evaluator risk.** Reward hacking is the main failure mode the research identifies; a self-judge cannot be the only signal in a health application, and any model judge must be calibrated against the sealed set, which is still waiting on the owner (OW-3).
- **Privacy is not guaranteed by redaction.** Clinical memorization can be severe and can survive further fine-tuning (up to 87% in the cited work), so the leak evaluation is a necessary gate but its coverage depends on the canaries chosen.
- **Not yet built.** Track 1 is in review and Track 2 is planned; this section documents a design and its first baselines, not outcomes.
