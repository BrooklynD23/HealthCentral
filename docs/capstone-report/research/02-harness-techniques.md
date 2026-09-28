# Research Scouting 02 — Agentic Harness & Context-Engineering Techniques

**Last Updated:** 2026-09-27 (§5.1 corrected per review F-10)

Scout of current practice in agentic-SWE harnesses: context layering, lifecycle enforcement, memory, orchestration, session handoff, and CI eval gating. Each entry ends with a **Proposed contract** (exact Asclexis integration point), a **Verdict** (`ADOPT` / `ADAPT` / `WATCH` / `REJECT`), and **Sources**. Verdicts without sources are flagged `UNVERIFIED`.

**Weighting rules** (applied to every verdict): (1) local-first — no telemetry, cloud dependencies, or remote tool calls in product or harness paths; (2) single-maintainer — prefer deterministic ~50-line scripts and CI flags over frameworks, daemons, or vector infra; (3) bonus weight if the technique fixes a weakness the 2026-09-25 audit named (fail-open security gate, phantom `.claude/agents/`, zero in-repo hooks, stale `.serena` memories, no coverage thresholds, no PR-size guard — audit §13–14, `audit/2026-09-25/Devin-Audit-report.md`).

**Source caveats:** Anthropic-authored items are authoritative for Claude Code mechanics but are vendor material. Field reports (Ultrathink, nyk.dev, personal blogs) are single-team experience, not studies. The MCP census is a single-author preprint (Sep 2026, Zenodo-archived data) — treated as directional, not conclusive.

---

## 1. Context layering & skills

### 1.1 Agent Skills spec + progressive disclosure

**What it is.** Anthropic published Agent Skills as an open spec (`agentskills.io`, reference impl in `anthropics/skills`): a directory with a `SKILL.md` whose YAML frontmatter requires `name` (≤64 chars, lowercase-hyphen) and `description` (≤1024 chars, "what it does **and when to use it**"). Three disclosure levels: metadata (~100 tokens, always loaded) → `SKILL.md` body (<5k tokens, on trigger) → bundled files/scripts (loaded or executed only as needed). Skill-creator guidance caps the body at ~500 lines and pushes variant detail into referenced files.

**Asclexis status.** Already conformant structurally: `.claude/skills/` (14 vendored process skills) + `skills/` (4 domain skills) use the SKILL.md + frontmatter shape, and `AGENT.md` carries the routing table. Nothing checks that conformance.

**Proposed contract.** Extend `scripts/docs_lint.py` (runs in the `docs-lint` CI job, `ci.yml:10`) with a `SKILL-*` rule family: every `*/SKILL.md` parses as YAML frontmatter; `name` matches `^[a-z0-9]+(-[a-z0-9]+)*$`, ≤64 chars; `description` present, ≤1024 chars; body ≤500 lines (warn, not fail); every file referenced from the body exists in the skill directory. ~80 lines of Python, no new dependencies.

**Verdict:** **ADOPT** (the lint, not the pattern — the pattern is already adopted). Cheapest possible conformance check; closes the same drift class that produced the phantom `.claude/agents/` claims — a spec whose only enforcement is convention.

**Sources:**
- https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx
- https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview.md
- https://github.com/anthropics/skills/blob/1ed29a03dc852d30fa6ef2ca53a67dc2c2c2c563/skills/skill-creator/SKILL.md

### 1.2 The control-plane taxonomy: CLAUDE.md vs rules vs skills vs hooks vs subagents

**What it is.** Anthropic's steering post enumerates seven steering mechanisms with different load times and token costs: CLAUDE.md (always-on, memoized, every line costs context every task), path-scoped rules (injected only when matching files are touched), skills (metadata always, body on invoke), subagents (zero main-context cost, isolated window, only the summary returns), hooks (fire on lifecycle events, bypass compaction entirely), output styles, and system-prompt appends. Community synthesis converges on one rule: **use the cheapest reliable control** — rules for persistent conventions, skills for repeatable procedures, hooks for deterministic lifecycle checks, subagents for isolation (not "parallelism theatre").

**Asclexis status.** The layers exist but the *selection rule* is implicit. The audit's symptom: "constraints that must never silently fail" are written as CLAUDE.md prose (advisory, model-dependent) instead of hooks (deterministic) — e.g. "always ask before touching `interpret_safety.py`" is a sentence, not an enforcement. Meanwhile `recurring-failures.md` is doing rules-work correctly.

**Proposed contract.** Add a 10-line "Which layer?" decision table to `docs/agentic/harness.md` (after the Evidence rules section): *hard constraint (never bypass) → hook or CI gate; convention (default behavior) → CLAUDE.md/rule; repeatable multi-step procedure → skill; isolated exploration → subagent.* Then audit existing invariants against it — the protected-files rule migrates to a hook (§2.1); the rest stays prose.

**Verdict:** **ADOPT** as a written selection framework. Zero infrastructure; it converts an implicit practice into a reviewable rule and directly motivated the two highest-value contracts below.

**Sources:**
- https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more
- https://www.nyk.dev/blog/agent-rules-skills-hooks-subagents-guide
- https://github.com/futhgar/agent-memory-architecture/blob/main/docs/architecture.md (layered-context reference impl: CLAUDE.md <200 lines, path-scoped rules, memory index)

### 1.3 AGENTS.md portability standard

**What it is.** `AGENTS.md` is the cross-vendor open convention for repo-level agent instructions — 60k+ projects, hierarchical nearest-file precedence, read by Codex, Copilot, Cursor, Gemini CLI, Jules, etc. Plain Markdown, no required schema.

**Asclexis status.** The repo ships `AGENT.md` (singular) — the same idea under a name non-Claude tooling does not discover.

**Proposed contract.** Add root `AGENTS.md` containing a pointer line (`# Agent onboarding → see AGENT.md` as a relative link) plus the 3 hardest invariants duplicated inline (per-profile DB isolation, `core.time.utcnow`, no medical advice). Two files, one source of truth — `docs_lint` already validates the link.

**Verdict:** **ADOPT**. ~15 minutes of work for real cross-tool portability; aligns with the report's "the harness is the deliverable" thesis (the briefing should be tool-agnostic).

**Sources:**
- https://agents.md/
- https://deepwiki.com/openai/agents.md/5.1-format-overview-and-specification

---

## 2. Enforcement: hooks, permissions, sandboxing

### 2.1 Committed lifecycle hooks (`.claude/settings.json` + `PreToolUse`/`PostToolUse`)

**What it is.** Claude Code hooks are shell commands fired on lifecycle events (`PreToolUse`, `PostToolUse`, `SessionStart`, `Stop`, `PreCompact`, `SubagentStop`, …) matched by tool-name regex. Exit code semantics: `0` allow, `1` non-blocking error, `2` block — stderr is fed back to the model as the error to route around. Structured output supports `permissionDecision: "deny"` for surgical blocking. Hooks live in committed `.claude/settings.json` (project) or `~/.claude/settings.json` (user) — **the project file is the one that survives the repo boundary and code review.** Hooks bypass compaction entirely (they are config, not conversation), so they are the only steering layer that cannot be summarized away.

**Asclexis status.** Audit finding H6/§13: zero hooks in-repo; the CS4610 report claimed an "AgentShield" PreToolUse PHI hook that was never installed at any level; `.gitignore:44` blocks `.claude/*` except `skills/`. This is the cleanest "make the claim real" fix available.

**Proposed contract.**

1. `.gitignore`: add `!.claude/settings.json`, `!.claude/hooks/`, `!.claude/agents/` (keep `settings.local.json` ignored).
2. `.claude/settings.json` → `hooks.PreToolUse`, matcher `"Edit|Write|MultiEdit|NotebookEdit"`, command `python .claude/hooks/protect_safety_modules.py`: deny (exit 2) when `tool_input.file_path` resolves under `modules/{interpret_safety,redaction,faithfulness,verifier_agent}.py`, `core/security*`, or `migrations/**` — unless env `HC_ALLOW_SAFETY_EDIT=1` is set for the session. This makes CLAUDE.md's "always ask before touching" deterministic instead of advisory, while preserving the human-approval semantics.
3. Second `PreToolUse` rule on `Bash`: deny `git push --force`, `rm -rf`, and `pip install` outside the venv (the three highest-blast-radius commands for a solo repo).
4. `PostToolUse` on `Write|Edit` → append `tool_name, file_path, session_id` to `docs/agentic/tool-audit.jsonl` — cheap provenance trail, answers "which agent session touched safety code" for the claims ledger.
5. CI backstop: `docs-lint` asserts `.claude/settings.json` parses and every `command` path exists (a hook that 404s is a phantom gate — the same failure class as the fail-open security gate).

**Verdict:** **ADOPT** — highest-value item in this document. Fixes two named audit weaknesses (no hooks layer; unverifiable AgentShield claim) at ~150 lines total, fully local, no dependencies beyond Python.

**Sources:**
- https://code.claude.com/docs/en/hooks.md (event list, matchers, blocking semantics)
- https://code.claude.com/docs/en/agent-sdk/hooks (`permissionDecision` contract)
- https://deepwiki.com/trailofbits/claude-code-config/4.4-writing-custom-hooks (exit-code discipline, block-vs-log pattern)
- https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more (hooks bypass compaction)

### 2.2 Declarative permissions + OS sandboxing

**What it is.** Two enforcement depths now standard across agent CLIs. (a) *Declarative permissions*: `permissions.allow/deny/ask` rules in `settings.json` scoped per tool + path/glob, plus session modes (`default`, `acceptEdits`, `plan`, `bypassPermissions`). (b) *OS sandboxing*: the field converged on kernel primitives over containers — Seatbelt (`sandbox-exec`) on macOS, Landlock LSM + seccomp or vendored bubblewrap on Linux, restricted tokens + DACL on Windows (Codex). Deny-by-default filesystem, workspace-only writes, network through an allowlist proxy. Third-party wrappers (greywall, temenos) productize the same primitives.

**Asclexis status.** Windows-first dev environment, single interactive maintainer, agent runs are supervised. The realistic threat model is the agent editing `modules/interpret_safety.py` or leaking `.env` — covered by §2.1 hooks + a permissions block, not by kernel isolation. Full sandboxing solves a threat (unsupervised agent on a network-connected multi-user box) this project doesn't have, and the Windows DACL path is the least mature of the three platform implementations.

**Proposed contract.** Commit only the declarative layer: a `permissions` block in `.claude/settings.json` — `deny` on `Read`/`Edit`/`Write` for `.env*`, `**/secrets/**`, `backups/**` (deliberately unredacted vault backups — deny *agent* writes; human restores unaffected); `ask` for `Bash` `git push*` and `pip install*`. Everything else stays default (interactive approval). Revisit OS sandboxing only if the project ever runs unattended agents — note Codex's `--sandbox` policy enum as the reference design.

**Verdict:** **ADAPT** — take the permissions block (committed, reviewed, free); skip kernel sandboxing as disproportionate at single-maintainer scale. `WATCH` the space if unattended/CI agents are ever introduced.

**Sources:**
- https://openai-codex.mintlify.app/architecture/sandboxing (policy enum, protected paths, per-platform drivers)
- https://codex.danielvaughan.com/2026/05/03/codex-cli-sandbox-internals-seatbelt-bubblewrap-landlock-windows-dacl/ (incl. Windows DACL pipeline)
- https://crabtalk.ai/blog/agent-sandbox-permissions (cross-tool convergence survey; Claude Code permission modes)
- https://github.com/tta-lab/temenos/ and https://github.laiyagushi.com/GreyhavenHQ/greywall (container-free wrappers)

---

## 3. MCP server ecosystem

**What it is.** MCP won the integration-layer argument: >10,000 active public servers at the December 2025 Linux Foundation (Agentic AI Foundation) donation, ~97M monthly SDK downloads (Mar 2026), all major vendors shipping first-party support, 41% of surveyed software orgs running MCP in production (Stacklok 2026 survey). **But** quality lags the hype: a Sep-2026 random-sample probe of 400 registry servers found only 48.8% completed an `initialize` handshake — 37.5% simply never start (vs 13.3% blocked by credentials); remote-only servers are the fastest-growing and healthiest slice (82.8% reachable in a July 2026 census of 9,326 remote servers). Security stack (gateways, scanners, runtime policy) exists but adoption, not invention, is the bottleneck.

**Asclexis fit.** `docs/agentic/mcp-tools.md` already states the right rules (project-scoped config, read-only DB default, tool output = untrusted input). The local-first constraint prunes most of the ecosystem: remote servers are disqualified by definition; per-profile vaults are SQLCipher — a stock `sqlite` MCP server can't open them anyway. What remains useful: **Serena** (LSP semantic code tools + its own memory system) and a docs-scoped `filesystem` server for research agents.

**Proposed contract.**

1. Commit `.mcp.json` (project-scoped) allowlisting `serena` (stdio, code navigation — see §4.1) and `filesystem` rooted at `docs/` read-only. No remote URLs, no credential-bearing servers.
2. `docs_lint` rule: `.mcp.json` must contain no `http`/`sse` transport entries and no env-var references outside an allowlist — local-first enforced at the tool-config layer, not just in prose.
3. Do **not** build a custom Asclexis MCP server over the vault (tempting, wrong): it adds an unreviewed privileged-code path to PHI; the existing FastAPI + `route_client` tests are the audited surface.

**Verdict:** **ADAPT** — adoption is real (evidence above), but the contract is a *short allowlist + a no-remote lint*, not ecosystem embrace. `REJECT` remote MCP servers outright (local-first invariant). `WATCH` MCP security tooling (gateways/scanners) — unnecessary today, relevant if the server list ever grows.

**Sources:**
- https://research.codelake.dev/reports/state-of-mcp-2026/ (97M SDK downloads/mo; 41% Stacklok production survey; LF donation; security-stack gap)
- https://www.beri.net/article/mcp-registry-random-sample-benchmark-duplication-server-start-rate (400-server random probe: 48.8% init success, 37.5% dead-on-arrival; preprint caveat)
- https://www.digitalapplied.com/blog/mcp-adoption-statistics-2026-model-context-protocol (registry counts, repo activity, corrected adoption figures)
- https://www.oreilly.com/radar/mcp-is-not-just-another-api-standard/ (primitives and where the abstraction leaks)
- https://jiaweing.com/blog/mcp-wont-save-your-agents (counterpoint: connector standard ≠ reliability)

---

## 4. Memory, ledgers & handoff

### 4.1 Memory shapes: curated files vs structured stores vs LSP memories

**What it is.** Three production shapes. (a) *Curated markdown*: a short index (`MEMORY.md`, ≤200 lines, survives compaction) over model-maintained topic files — what Claude Code, Cline, Cursor ship; "don't store what's derivable from repo state" is the discipline. (b) *Structured stores* (mem0, Zep, Letta): every turn mined into atomic facts, embedded, graphed — right when memory is the product. (c) *LSP-side memories*: Serena's onboarding writes project notes to `.serena/memories/*.md` — same failure surface as (a) but written by a tool, refreshed only on re-onboarding. Field evidence for the key risk: Ultrathink rewrote an agent's instructions but not its memory — "**stale learnings override fresh rules**."

**Asclexis status.** The audit rated `progress.md` / `recurring-failures.md` / `implementation-log/` "exemplary" — Asclexis already runs shape (a) well, with provenance (each failure mode carries commit-hash evidence). The named weakness is shape (c): `.serena/memories/` frozen Jan-2026, pre-`models/`, pre-Alembic — "a second, contradicting context source that docs_lint never checks." Seven stale files confirmed in-repo today (`project_overview.md`, `critical_01_07.md`, …).

**Proposed contract.** Two-part fix (owner picks per `plans/03` decision):
- *Gate option:* add `.serena/memories/*.md` to `docs_lint` — each file requires `verified: YYYY-MM-DD` frontmatter; CI fails when any file is >60 days unverified. Freshness becomes checkable instead of assumed.
- *Delete option:* remove the directory and add Serena's "re-onboard" step to `AGENT.md` onboarding; memory then has exactly one home (`docs/agentic/`).
Either way: **one canonical memory layer**. Structured/vector stores rejected — needs embedding infra this project deliberately treats as optional (`test_api_rag_index_002b` already env-fails without one), and grep-able markdown wins at this scale.

**Verdict:** **ADOPT** the freshness gate or deletion (both resolve the audit finding; gate recommended — memories are valuable *when fresh*). **REJECT** structured memory stores (mem0/Zep class): infrastructure cost disproportionate to a single-maintainer repo, and the file shape is what the audit already validated.

**Sources:**
- https://pinglin.tw/blog/the-shapes-of-agent-memory/ (three-shape taxonomy; file memory is what shipping coding agents use)
- https://github.com/luzhenqian/claude-harness/blob/main/content/articles/en/09-memory-system.mdx (MEMORY.md index mechanics, 4-type taxonomy, derivable-state exclusion)
- https://dikrana.dev/blog/agent-memory-architecture/ (CoALA working/episodic/semantic/procedural mapping)
- https://ultrathink.art/blog/multi-agent-orchestration-lessons ("stale learnings override fresh rules" — the exact Asclexis failure, observed in production)
- https://github.com/oraios/serena (LSP tools + onboarding/memories system — the source of the stale files)

### 4.2 Feature ledger + session artifacts (the `feature_list.json` pattern)

**What it is.** Anthropic's long-running-agent harness work converged on: an *initializer* agent writes `feature_list.json` + `init.sh` + first commit; every later session is a *coding agent* that reads `claude-progress.txt` + ledger + git log, implements one feature, verifies, commits, leaves artifacts. Two load-bearing details: the ledger is **JSON, not Markdown** (models corrupt Markdown lists; JSON schemas lint), and every criterion starts `"passes": false` — a **default-FAIL contract** where flipping requires evidence. The follow-up `cwc-long-running-agents` repo adds a *fresh-context evaluator*: a separate agent with no Write/Edit tools grades completion from a context that never saw the work.

**Asclexis status.** Independent convergence — `feature_list.json` + `docs/agentic/progress.md` + `feature_list_lint` in CI is the same architecture, arrived at before/parallel to the Nov-2025 post. (Good §7 material: the project re-derived the published reference pattern.) Gap: `feature_list_lint` checks schema, not evidence — "completed" still rides on self-report (the hole Ultrathink measured: 97% of tasks shipped unverified before mandatory QA chains; "self-reported quality gates have zero enforcement value").

**Proposed contract.** Extend `feature_list_lint.py`: any item with `status: "completed"` requires a non-empty `evidence` field (list of commands run / test IDs) — codifying `harness.md`'s existing "no claim without a command" rule into the ledger itself. Optionally add `verification_steps` (Anthropic's field name) for features with UI/runtime behavior. Defer the fresh-context evaluator subagent — valuable, but second-order; note it in `docs/agentic/roadmap.md`.

**Verdict:** **ADOPT** the evidence-field lint (one-file change, closes the self-attestation hole at the exact surface the ledger guards). **WATCH** the evaluator-subagent primitive.

**Sources:**
- https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents (initializer/coding split, `feature_list.json`, `claude-progress.txt`, JSON-not-Markdown, default-false)
- https://github.com/anthropics/cwc-long-running-agents (default-FAIL contract; fresh-context evaluator with no write tools; agent-maintained handoff)
- https://ultrathink.art/blog/multi-agent-orchestration-lessons (97%-unverified measurement; mandatory QA chains)

### 4.3 Context compaction vs reset, and session handoff

**What it is.** Anthropic's March-2026 harness post distinguishes **compaction** (summarize-in-place; CLAUDE.md/rules reload, hooks unaffected) from **context resets** (new window + structured handoff artifact) — resets beat compaction for long tasks because models show "context anxiety" (premature wrap-up as the window fills); Sonnet 4.5 needed resets, not just compaction, for strong long-task performance. Third-party plugins automate the handoff: `PreCompact`/`SessionEnd` hooks that snapshot task state + open decisions + files touched, `SessionStart` hooks that restore it as `additionalContext` (who96/claude-code-context-handoff, ddaanet/handoff). Claude Code's own guidance: new task → new session; `/clear` beats `/compact` when a clean slate suffices.

**Asclexis status.** The manual norm already exists (`progress.md` entries + `executing-plans` skill + feature ledger = a human-driven handoff protocol); what's missing is a *just-in-time* capture — the state that lives only in the dying session's context (open decisions, partial diffs, "the test that was still red").

**Proposed contract.** Add `skills/session-handoff/SKILL.md` (project domain skill): triggered before `/clear`, `/compact`, or session end — writes `docs/agentic/handoff-latest.md` with fixed fields (task, branch, open decisions, verification status incl. commands run, next action). Alternative heavier option, deferred: a `SessionEnd` hook extracting last-N user prompts + touched files from the session JSONL (the ddaanet mechanism). Skip installing third-party plugins — unaudited dependencies for a ~60-line skill's worth of behavior.

**Verdict:** **ADAPT** — formalize the existing manual norm into one committed skill; cheap, local, and it removes the last context source that exists only inside a session. **WATCH** the plugin ecosystem (the `PreCompact`→`SessionStart` capture/restore loop is the right mechanism if the manual skill proves insufficient).

**Sources:**
- https://www.anthropic.com/engineering/harness-design-long-running-apps (reset-vs-compaction, context anxiety, handoff-artifact requirements)
- https://code.claude.com/docs/en/context-window (what survives compaction; hooks exempt)
- https://claude.com/blog/using-claude-code-session-management-and-1m-context (context rot; session-per-task guidance)
- https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools (compaction/tool-clearing/memory primitives)
- https://github.com/who96/claude-code-context-handoff and https://github.com/ddaanet/handoff (hook-driven capture/restore implementations)

---

## 5. Subagent orchestration

### 5.1 Orchestrator-worker (hub-and-spoke) vs swarms/blackboards

**What it is.** The settled pattern: one orchestrator owns the plan and context; workers are spawned per-task with a prompt, run in isolated context, return one message, die. No lateral worker-to-worker communication — coordination flows through the hub (Claude Code internally calls it `FORK_SUBAGENT`; the child's prompt opens "You are a forked worker process. You are NOT the main agent"). Evidence for the edges: Anthropic's multi-agent research system beat single-agent by ~90% on its internal eval but burned ~15× tokens, and **coding parallelizes far worse than research** (write-write dependencies vs read-parallelism). Ultrathink's 10-agent/2,500-task field report adds the production lessons: tool restrictions live in **frontmatter, not prompts** (blast-radius control — "a designer with write access is one hallucination from outage"), mandatory `next_tasks` QA chains (agents can't opt out), per-role memory files, and a 468-line governance file where every rule carries incident-date provenance. Claude Code subagents support `tools`, `disallowedTools`, `model`, `permissionMode`, `maxTurns`, `hooks` frontmatter — the restriction mechanism is first-class config.

**Asclexis status.** The repo already practices this (skills: `dispatching-parallel-agents`, `subagent-driven-development`; `harness.md` subagent rules; the 6-agent audit itself is evidence — M1: multi-agent reconciliation caught 3+4 real errors). The named weakness is embarrassing precisely because the practice is right: `harness.md:27` names five `.claude/agents/` files that exist **nowhere** — repo, git history, or user level — and `.gitignore:44` makes them impossible.

> **Correction 2026-09-27** ([review follow-up F-10](../../../audit/2026-09-25/review/2026-09-27-followup.md)): the original text below called "making it real" the *Branch-B* path. In [`plans/03-phantom-layer.md`](../../../audit/2026-09-25/plans/03-phantom-layer.md) that is **Branch A**; Branch B corrects the docs (the ~80%-built work on `7b2ff1f`), and plan 03 *recommends B* behind an owner STOP gate. Plan 03's Branch A also scopes 3 agents, not 5. The owner answer on record is "Not sure" (audit §21 Q2). This entry is therefore a **proposal for owner decision, not an adoption**.

**Proposed contract (owner-gated — plan 03 Branch A option).** If the owner selects Branch A: commit `.claude/agents/` definitions with read-only frontmatter (`tools: Read, Grep, Glob`) for the scanner roles and a bounded write scope for any implementer role, unignore that path in `.gitignore`, and add the rule to `harness.md`: *capability restrictions in frontmatter, never in prompt text.* Plan 03 cautions against authoring a roster only to match old doc text. If the owner selects Branch B, this contract lapses and only the frontmatter-restriction rule remains relevant as future guidance.

**Verdict:** **WATCH — owner decision pending** (was: ADOPT the five agents; downgraded 2026-09-27 because it pre-empted plan 03's STOP gate). **REJECT** swarm/blackboard/peer-messaging topologies for this project: lateral coordination is the failure-prone part even at production scale (matzelle, inside-claude-code), agent-teams remains an experimental flag, and a single maintainer gains nothing from it.

**Sources:**
- https://www.learninternetgrow.com/orchestrator-worker-pattern/ (pattern anatomy; 15×-token and coding-parallelization caveats from Anthropic's research-agent write-up)
- https://ultrathink.art/blog/multi-agent-orchestration-lessons (frontmatter tool restrictions as blast-radius; QA chains; 97%-unverified baseline)
- https://www.matzelle.co/blog/2026-02-27-orchestrator-worker-architecture (stateless hub-and-spoke; why lateral comms lose)
- https://y-agent.github.io/inside-claude-code/07-multi-agent-orchestration.html (`FORK_SUBAGENT` internals, worktree isolation, budgets)
- https://code.claude.com/docs/en/sub-agents (frontmatter fields incl. `tools`, `permissionMode`, `hooks`, `skills`)
- https://soumik.blog/software-engineering/building-multi-agent-ai-coding-systems/ (2024–2026 pattern survey)

---

## 6. Eval gating & repo guards in CI

### 6.1 Baseline-delta eval gates + deterministic-first scoring

**What it is.** The converged CI pattern for agent output: golden cases versioned with the code → runner executes the real agent loop → composable scorers (exact-match/regex/JSON-schema first, LLM-judge only where semantics demand it) → **the gate is a delta against a stored baseline, not an absolute score** — "is this *worse than it was*?" is the only question CI answers objectively. Regressions post as PR comments; adversarial cases quarantine outside blocking until human-approved (agenteval). The `failOnEmpty` convention matters: a missing/empty eval report fails the job rather than silently passing.

**Asclexis status.** `agent-evals` job already runs `scripts/agent_eval_gate.py` (74 cases, 6 axes — advice leakage, groundedness, citation accuracy…). Stronger than most open-source eval setups. Two gaps this research names: (a) the **security gate fails open on main** — a crash reports zero findings (fail-closed fix `934a842` on `claude/healthcentral-agentic-research-r1n54x`, 7 tests, unmerged) — the `failOnEmpty` lesson applied to the wrong gate; (b) no stored baseline, so a slow-quality-rot regression across PRs is invisible (74 cases can all pass while trending down).

**Proposed contract.** (a) Merge the fail-closed security-gate branch — highest-severity confirmed defect in the audit; every unmerged day the signal is cosmetic. (b) `agent_eval_gate.py`: commit a `evals/baseline.json` of per-axis scores; the job fails on delta-drop >ε *or* absolute-threshold breach (both cheap since scorers are already deterministic). (c) Add a `failOnMissingReport` convention repo-wide: any gate whose input artifact is absent must exit non-zero — generalize the security-gate fix into a rule `docs_lint` can spot-check.

**Verdict:** **ADOPT** (a)+(b)+(c). (a) is a merge decision, not new work; (b) is ~50 lines; (c) codifies the flagship audit finding as a reusable invariant — the report can present this as "the field converged on the same gate discipline the audit found missing."

**Sources:**
- https://github.com/royalpinto007/evalgate (baseline-delta gating, PR delta comments, zero-key mock provider)
- https://github.com/numoru-ia/agent-evals-template (Promptfoo+DeepEval layers + regression guard; "deterministic for contracts, judge for fuzzy axes")
- https://github.com/MasRama/agenteval (versioned baselines, adversarial cases quarantined from blocking CI)
- https://github.com/LesterALeong/llm-evalgate (deterministic gates as CI backbone; judge only where needed)
- https://www.agent-native.com/docs/evals (eval-as-CI-primitive, non-zero exit = deploy gate)

### 6.2 Coverage thresholds + PR-size guards

**What it is.** Boring, standard, missing here: `pytest --cov --fail-under=N` / diff-cover `fail-under` on changed lines (fail only the *new* uncovered lines, so legacy debt doesn't block), and PR-size checks — Microsoft's PR-Metrics convention (XS ≤200 added lines, ~2× growth per size class) or a 15-line `git diff --stat` job that comments "large PR" above a threshold.

**Asclexis status.** Audit-named gaps: ruff/eslint/mypy configured but ungated; no coverage thresholds; no PR-size guard. The audit's own evidence argues for the size guard: the two unmerged branches run +15,050 and +1,660/−102 lines — exactly the diff sizes where review quality collapses and phantom claims slip through.

**Proposed contract.** (a) `backend-tests` job: add `pytest --cov=src/backend --cov-fail-under=<measured>` — set N to the *current measured* coverage minus ~2%, ratchet upward in TASK_LIST, never start aspirational. Add diff-cover `fail-under: 80` on changed lines only. (b) New `pr-size` job in `ci.yml`: `git diff --stat base...head` → comment (not block) above 800 total changed lines, block above 2,500 unless the PR body carries `size-justified:` — a guardrail, not a wall, sized to a solo maintainer. (c) Gate the existing-but-ungated linters in the same pass (ruff on backend job, eslint in frontend job — they're already configured).

**Verdict:** **ADOPT** all three — each is <30 lines of YAML/config, zero new dependencies, and they close three separate audit-named weaknesses. Comment-not-block for size respects the single-maintainer constraint while making big agent-generated diffs visible.

**Sources:**
- https://github.com/microsoft/PR-Metrics (size classes, test-factor ratio, comment-based UX)
- https://github.com/Affanmir/diff-cover-action (`fail-under` on diff lines; report-without-fail option)
- https://github.com/filippovskii09/diff-cov-guard (`failOnEmpty` convention — mirrors §6.1c)
- https://pkg.go.dev/github.com/cbrgm/pr-size-labeler-action (labeler alternative: xs/s/m/l/xl thresholds)
- https://github.com/bindertools/binder/blob/fb136fec7eaad1c82096c02740d625a374ce9204/.github/workflows/pr-checks.yml (minimal `git diff --stat` warning job — the 30-line version)

---

## Verdict summary

| # | Technique | Verdict | Fixes audit weakness? | Effort |
|---|---|---|---|---|
| 2.1 | Committed `.claude/settings.json` hooks (safety-file deny, dangerous-Bash deny, tool audit log) | **ADOPT** | ✅ no-hooks layer + AgentShield claim | ~150 LOC |
| 6.1 | Fail-closed gates + eval baseline delta + `failOnMissingReport` rule | **ADOPT** | ✅ fail-open security gate | merge + ~50 LOC |
| 5.1 | `.claude/agents/` only if owner picks plan 03 Branch A (corrected 2026-09-27); reject swarms | **WATCH (owner gate)** | ✅ phantom `.claude/agents/` | ~5 files + `.gitignore` |
| 4.1 | `.serena/memories` freshness gate (or deletion); reject vector memory stores | **ADOPT** / REJECT | ✅ stale second context source | 1 lint rule |
| 6.2 | Coverage threshold (ratcheted) + diff-cover + PR-size comment + gate existing linters | **ADOPT** | ✅ no coverage/size/lint gates | ~30 lines YAML |
| 4.2 | `feature_list.json` evidence-field lint (default-FAIL contract) | **ADOPT** | ◐ codifies "no claim without a command" | 1 lint rule |
| 1.1 | `SKILL.md` conformance lint (spec fields, 500-line body cap) | **ADOPT** | ◐ prevents future spec drift | ~80 LOC |
| 1.2 | Written layer-selection rule in `harness.md` (cheapest reliable control) | **ADOPT** | ◐ motivation for §2.1 | docs only |
| 1.3 | Root `AGENTS.md` pointer file | **ADOPT** | — portability | ~5 lines |
| 2.2 | Declarative `permissions` block (deny `.env`/`backups`, ask on push/pip) | **ADAPT** | ◐ complements §2.1 | ~20 lines JSON |
| 3 | MCP: project `.mcp.json` allowlist (serena, docs filesystem) + no-remote lint; reject remote servers | **ADAPT** / REJECT | ◐ makes mcp-tools.md enforceable | ~40 LOC |
| 4.3 | `session-handoff` skill (task state + open decisions + verification status) | **ADAPT** | — | ~60-line skill |
| 5.1b | Agent-teams / peer-messaging orchestration | **REJECT** (single maintainer) | — | — |
| 4.1b | mem0/Zep-class structured memory | **REJECT** (infra cost, scale) | — | — |
| 2.2b | OS sandboxing (Seatbelt/Landlock/DACL) | **WATCH** | — | revisit if unattended agents |
| 4.2b | Fresh-context evaluator subagent | **WATCH** | — | second-order |
| 3b | MCP gateways/scanners | **WATCH** | — | only if server list grows |
| 4.3b | Third-party handoff plugins | **WATCH** | — | unaudited deps vs 60-line skill |

**Pattern across verdicts:** every ADOPT is a *deterministic check committed to the repo* — a lint rule, a hook, a CI flag. Every REJECT/WATCH is a *runtime dependency, a remote service, or a framework*. That split is the local-first, single-maintainer weighting operating as designed, and it rhymes with the audit's own finding (M2): gates prevent drift; prose doesn't.

No entry is `UNVERIFIED` — every verdict carries sources. The MCP census claim (48.8% init success) is a single-author preprint; treat the number as directional.

Back to index: [../README.md](../README.md) · Scouting index: [README.md](README.md)
