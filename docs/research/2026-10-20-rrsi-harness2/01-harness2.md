# google-research/harness2: what the repo is

**Last Updated:** 2026-10-20
**Owner:** repository owner
**Refresh Trigger:** a new harness2 commit, tag or release; arXiv 2609.24972 or 2610.14224 becomes reachable and is read; the owner answers OQ-1 or OQ-2 in [04-owner-questions.md](04-owner-questions.md).

> **Point-in-time research (2026-10-20).** The repo was cloned read-only and read as text. None of its code, scripts, setup steps or demo was run. Paths below are relative to `google-research/harness2` at commit `1cfe254` (2026-10-13), written `harness2:<path>:<line>`. Markers: **[V]** read in the file or command output at that commit; **[I]** inferred from what was read; **[U]** could not be checked.

## 1. The short answer: this is not the RRSI code

The owner said the RRSI research pass "is based off this repo". The repo does not implement RRSI.

| | What HealthCentral's notes cite | What `harness2` is |
|---|---|---|
| Paper | RRSI: Regularized Recursive Self-Improvement of Agent Harnesses, arXiv 2609.24972, "Xia, Han, … Lee" ([01-rsi-self-improving-agents.md](../2026-10-17-rsi-opt-in-data/01-rsi-self-improving-agents.md) row 15, line 23) | Harness²: Recursive Agent Harnessing for an Open World, arXiv 2610.14224, Xu, Chen, CuiZhu, Dalvi Mishra, Ming, Yu, Han, Lee, Pfister [V] `harness2:README.md:3`, `:7`, `:185-191` |
| Critic that rejects benchmark-specific edits | claimed | absent [V] grep for `critic`, `prune`, `pruner`, `OOD`, `out-of-distribution`, `held-out`, `regulariz`, `RRSI`, `2609.24972` over `.py/.md/.toml/.yaml` hits only `harness2:harness2/benchmarks/jobbench.py:296` ("safety-critical conflicts") |
| Pruner | claimed | absent [V] same grep |
| OOD check | claimed (+4.3 OOD) | absent; only an optional train/test split script [V] `harness2:docs/EXPERIMENTS.md:75-85`, `harness2:scripts/split_tasks.py` |
| Regularisation | the core idea | the opposite: the GENERALIZE prompt tells the editor to "WRITE THE FACT ITSELF" about the workspace into the harness [V] `harness2:harness2/core/prompts.py:295-306` |

The two papers share two authors (Han, Lee) [V by author lists]. arXiv was unreachable from this session for both IDs (proxy CONNECT 403; DNS ENOTFOUND), so neither abstract was read and it is **[U]** whether RRSI has released code anywhere. The earlier note's [V] on RRSI (row 15) could not be re-checked in this pass.

## 2. What it is

| Fact | Evidence |
|---|---|
| Apache-2.0 Python package `harness2` v0.1.0, by Google LLC | [V] `harness2:pyproject.toml:6-7`, `:10`; `harness2:LICENSE:1-2` |
| Python `>=3.12,<3.14` (HealthCentral targets 3.11+) | [V] `harness2:pyproject.toml:11` |
| Third-party code keeps upstream licences; contributions need a Google CLA | [V] `harness2:README.md:201-204`; `harness2:CONTRIBUTING.md:9-10` |
| "Not an officially supported Google product" | [V] `harness2:README.md:208` |
| 3 commits: `e0fb650` and `2152977` on 2026-10-08, `1cfe254` "Fix arXiv link" on 2026-10-13; no tags; heads are `main` plus one dependabot branch | [V] `git log`, `git ls-remote` |
| One test file, 5 unittest tests, all on the deterministic demo adapter; no CI directory | [V] `harness2:tests/test_workflow.py:50`, `:108`, `:148`, `:187`, `:208` |

### 2.1 The method

Model weights stay fixed. The thing that improves is a per-task "harness" of 8 editable components: system prompt, guardrails, memory, tool guidance, subagents, skills, scripts and plugins [V] `harness2:README.md:70-71`. Recursion runs at two levels [V] `harness2:README.md:27-33`.

**Task level: Propose, Probe, Compose.** An INV editor (how the agent works) and a DOM editor (domain knowledge) propose edits. Each candidate is rolled out once on the same task, and a composer merges them with no ground-truth feedback.
- Parallel mode: 2k INV/DOM candidates, each rolled out, then k independent compositions [V] `harness2:harness2/core/recursion.py:357`, `:368`, `:408-415`.
- Sequential mode: k nested inv/dom/compose passes that carry the current harness forward [V] `recursion.py:466`, `:478-562`.
- A proposed tree is validated (editable surface, always-on character cap, py-compile, hooks schema, script references, grader-verdict markers) before acceptance [V] `recursion.py:108-132`; `harness2:harness2/core/tree.py:336-378`. Caps: 24,000 characters for OpenCode, 8,000 for Codex [V] `harness2:harness2/substrate/opencode.py:50`; `harness2:harness2/substrate/codex.py:42`.
- An invalid proposal gets one retry with the rejection fed back, then the current harness is kept (`STAGE_ATTEMPTS=2`) [V] `recursion.py:36`, `:180-251`.

**Harnessing level: select, reflect, archive.**
- An LLM selector picks one of k anonymised finals using seeded, shuffled IDs, and falls back to a delivered base on failure [V] `harness2:harness2/core/selection.py:71-76`, `:268-357`. The anonymisation hides candidate labels from the selector; it does not hide candidates from the proposer [V] `selection.py:15`, `:71-80`.
- A reflector distils an "experience" (cue, lesson, evidence, confidence); an incomplete one is discarded [V] `selection.py:402-451`, `:494-501`.
- The adopted full tree plus that experience goes into a per-domain experience library. Library roots are scoped per run and mode, so each sweep starts empty [V] `harness2:harness2/core/library.py:15-23`, `:116-152`. An entry is added only when selection succeeded and the experience is complete [V] `harness2:harness2/core/schedule.py:529-563`.
- **Adoption is automatic.** The README says harnessing-level recursion "retains the adopted harness" [V] `harness2:README.md:31-33`, `:161-162`. A grep for `approv|human` in `harness2/core/schedule.py` returns nothing [V]. The line "The notes are read by a person, not applied by a machine" covers only a `<notes>` block [V] `prompts.py:291-292`.

### 2.2 The guard patterns worth knowing

| Pattern | Evidence |
|---|---|
| Fixed budget identity: R = 4k rollouts, P = 3k improver sessions; `assert_identity` raises `BudgetError` on a mismatch or a duplicate label | [V] `harness2:harness2/core/ledger.py:15`, `:26-33`, `:89-113`; used at `recursion.py:448`, `:565` |
| Evaluator outside the method: "Nothing in the method imports this module." A judge failure counts as None, not zero | [V] `harness2:harness2/core/judge.py:15-19`; imported only by `harness2/cli/judge.py:39` and `harness2/core/report.py:27` |
| Leak tripwires: grader-verdict markers (by file name and content) and an answer-key path guard on everything that reaches a model | [V] `harness2:harness2/core/context.py:399-416`, `:419-427`, `:454-490` |
| "No change" is a valid answer (`KEEP_BASE`); an edit aimed at a defect seen in 1 of k samples is called "overfitting to one sample" | [V] `prompts.py:287-289`, `:919-921` |

These guard benchmark-answer leakage into a workspace. They are not PHI controls [I]. Porting a tripwire to HealthCentral means defining what a "leak path" is here (the sealed set, gate output, vault files, `.claude/logs/rsi/` content).

## 3. What it needs to run

| Need | Evidence |
|---|---|
| Linux, Python 3.12, uv, Node 20+, gcloud CLI | [V] `harness2:docs/SETUP.md:9-23` |
| Vertex AI credentials (ADC, `GOOGLE_CLOUD_PROJECT`/`LOCATION`); solver, improver and judge models set by `HARNESS2_SOLVER_MODEL`, `HARNESS2_IMPROVER_MODEL`, `HARNESS2_JUDGE_MODEL` | [V] `harness2:harness2/config.py:92-102`, `:181-189`; `docs/SETUP.md:41-49` |
| Improver channels `opencode` or `claude_cli` | [V] `config.py:174-175` |
| Benchmarks: Pandoc/Poppler (LAB), Docker (WorkBuddy); setup clones pinned benchmark repos from GitHub and data from Hugging Face | [V] `README.md:83`, `:96-98`; `config.py:104-115`; `docs/SETUP.md:151` |
| A credential-free deterministic demo exists | [V] `README.md:93-94`; `harness2/demo.py:15` |

## 4. Safety posture

| Fact | Evidence |
|---|---|
| Executor network access is unrestricted; the docs tell users to add their own egress firewall | [V] `README.md:168-171`; `docs/EXPERIMENTS.md:100-109` |
| The Codex executor runs with `--dangerously-bypass-approvals-and-sandbox` and `--dangerously-bypass-hook-trust` | [V] `harness2/substrate/codex.py:166-167` |
| The `claude_cli` improver runs with `--dangerously-skip-permissions` | [V] `harness2/core/proposer.py:213-216` |
| OpenCode sessions get a directory fence (`'*': deny`, workspace allow) | [V] `proposer.py:270-272`; `substrate/opencode.py:276-281` |
| The docs report a Codex rollout that downloaded its own task rubric unprompted | [V] `docs/EXPERIMENTS.md:95-98` |
| The LiteLLM bridge can bind to 0.0.0.0 | [V] `docs/SETUP.md:131-133` |
| No human gate anywhere in selection, reflection or library adoption | [I] `schedule.py:480-563` read; no approval step found |

## 5. What this means for HealthCentral

- **As code or runtime: no.** Python 3.12, Vertex network calls, permission-bypass flags and open egress conflict with the 3.11 target, local-first, least privilege and the D12 rule that the opt-in external runner is the only off-device model path ([CLAUDE.md](../../../CLAUDE.md) Hard invariants) [I].
- **As a pattern source: yes, for the development harness only.** Budget identity, evaluator outside the method, leak tripwires, `KEEP_BASE`, and an archive of adopted changes. See [02-verdicts.md](02-verdicts.md) §1.
- **Do not copy:** GENERALIZE (`prompts.py:295-306`). In HealthCentral, writing "the fact about this workspace" into a reused harness means writing repo-run specifics into rules (Track 1) or patient facts into shared code (Track 2) [I].
- **Do not copy:** automatic adoption. HealthCentral promotions are owner-merged (owner row AUTO-MERGE, [owner-decisions-2026-09-27.md](../../capstone-report/owner-decisions-2026-09-27.md):206).

## 6. Unknowns

- [U] Whether arXiv 2609.24972 exists as the notes describe it, and whether it has code. arXiv was unreachable.
- [U] The arXiv abstract of 2610.14224, and whether the README's reported gains (`README.md:41-45`) reproduce. Reproduction needs paid Vertex runs.
- [U] Stars, issues and releases: the GitHub REST API returned 403 for this repo in this session.
- [U] `third_party/` runners and most of `prompts.py` (1163 lines); only the cited sections were read.
- [U] Whether the deterministic demo tests cover the model-backed paths. Nothing was executed.
