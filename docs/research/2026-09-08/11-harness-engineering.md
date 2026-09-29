# Track 10 — Harness and loop engineering

**Scope:** the *development* harness — the tools, hooks, skills, subagents, gates, state
files and feedback loops that keep an AI agent on task while it builds Asclexis. Not
the product's own agent loop (that is Track 3, `03-agentic-loops.md`, and the
`modules/agent/` graph audited in `01-codebase-audit.md`). Read
[STATUS.md](STATUS.md) first — this track was dispatched after the other eight and is
not itself listed there yet.

**Method:** repo inventory first (every claim below with a path is grep- or
Read-verified against this checkout, not inferred), then external research
(WebSearch/WebFetch, tagged where a primary source could not be fetched — the
session's egress proxy blocked `anthropic.com`, `addyosmani.com`, and `zenml.io`
outright, matching the exact limitation `PLAN.md` §9 already recorded for this
research pass). `code.claude.com` and `platform.claude.com` were reachable and are
used as primary sources wherever cited directly.

---

## Summary

1. **The documented harness and the actual harness have fully diverged on the two
   claims this track was dispatched to check, and on nothing else that matters as
   much.** `.claude/agents/` does not exist (confirmed: `ls .claude/agents/` →
   *No such file or directory*), yet `docs/agentic/harness.md:25-30` and
   `docs/agentic/roadmap.md:17` both assert it holds four read-only scanner
   subagents and one specialist implementer. There is no `.claude/settings.json`,
   no `hooks.json`, and no `.claude/hooks/` anywhere in this repo (confirmed by
   exhaustive `find`), yet the CS4610 Final Report §7.2 and Technical Companion
   §4.6 both describe a working "PreToolUse hook [that] scans for patterns that
   look like PHI and blocks any tool call that would send them to a network."
   Neither artifact was ever checked in. See the divergence table below.
2. **What is real and enforced today is almost entirely CI-time and code-level,
   not agent-time.** Five of six `scripts/*.py` gates run in
   `.github/workflows/ci.yml`; the sixth, `repo_hygiene_check.py`, is unit-tested
   but never invoked against the live repository in any CI job — a smaller
   instance of the same divergence pattern, found independently during this
   track's verification pass. A few genuine code-level invariants exist and would
   hold even against a hostile or careless agent (`_assert_localhost()` in
   `core/llm/ollama_provider.py`, Pydantic validation in the agent tool registry)
   — these are the strongest examples of a CLAUDE.md rule that graduated from
   prose to code.
3. **Nothing in this repo uses Claude Code's hook system, at all.** Given that,
   the PHI-network claim cannot currently do anything. It is also worth being
   precise about what it *could* do if built: Anthropic's own hooks documentation
   states plainly that hooks are "a convenience feature for automation, not a
   security boundary," and explicitly recommends the permission system over a
   hook for a hard allow/deny. A `PreToolUse` hook could catch an agent about to
   paste PHI-shaped test fixtures into a `curl`/`WebFetch` call during a coding
   session — a real but narrow footgun. It cannot be, and should never be
   described as, the product's privacy guarantee, because Claude Code hooks fire
   on the *coding agent's* tool calls, not on network calls the deployed FastAPI
   app makes at runtime. The CS4610 report's sentence — "HealthCentral's privacy
   guarantee ... we encoded it into the harness" — collapses two different loops
   into one claim. The actual runtime guarantee already exists, correctly, as
   code (`_assert_localhost`, `modules/redaction.py`), not as a Claude Code hook.
4. **36 skills are advisory by construction, not by neglect.** Skills are
   model-invoked; nothing forces a trigger. That is not a gap to close with a
   hook — it is the documented design of the primitive. The repo's own
   `using-superpowers/SKILL.md` frontmatter claims to require invocation "before
   ANY response," which is exactly as binding as the model's willingness to read
   and obey it. This matters for recommendation-setting: adding a 37th skill to
   enforce something does not change its enforcement class.
5. **The four named subagents are this repo's sharpest instance yet of
   `recurring-failures.md` #8 ("stale guidance that reads as authority").** Their
   names appear nowhere in this repo except `harness.md` itself — not in
   `.claude/agents/` (absent), not in `progress.md`, not in a commit message, not
   in any research track. Either they were run once as ad-hoc Task-tool
   dispatches whose identity was never persisted, or the sentence was
   aspirational from the day it was written. Either way, an agent reading
   `harness.md` today would try to invoke a subagent that Claude Code cannot
   find.
6. **The external 2026 harness ecosystem has moved past a text-only harness.**
   Hooks now span roughly 30 lifecycle events (async support shipped January
   2026); subagents carry 15+ frontmatter fields including `permissionMode`,
   `isolation: worktree`, and spawn-depth limits; plugins bundle skills + agents +
   hooks + MCP servers + LSP servers behind one manifest and route through two
   Anthropic-run marketplaces. Of the three frameworks this project studied,
   **superpowers is the one whose enforcement model actually matches what this
   repo built** (skill-based, model-trusted) — consistent with this repo having
   vendored superpowers wholesale and built nothing from ECC's hook layer despite
   citing ECC's `AgentShield` hook as the model for the PHI-blocking claim.
7. **No development loop in this repo runs unattended today**, and none should
   without structural (not prompted) denylists on the four safety modules and
   auth/encryption, because "ask before touching" has no one to ask when nobody
   is watching. GSD v2's own public issue tracker documents a real failure mode
   worth internalizing before trusting any framework's stuck-loop detector on
   this codebase: a provider misreporting its context window caused the
   detector to never fire across process restarts.
8. **There is no eval of the development harness itself**, only of the product's
   agent (`agent_eval_gate.py`, 6 axes, 74 cases). Section 4 proposes a cheap,
   log-derived scorecard instead of new heavyweight infrastructure: gate-trip
   rate, rework rate, verification-pass-on-first-attempt, recurring-failure
   recurrence, and a narrow new CI check — `harness_drift_check.py` — that would
   have caught both verified gaps this track was dispatched to find.
9. **The highest-priority recommendation is debt repayment, not new tooling**:
   fix or delete the `.claude/agents/` and hook claims before building anything
   new, and wire the already-correct `repo_hygiene_check.py` into CI (a one-line
   change). Everything else — a subagent, a hook, a skill — is lower priority
   than making the documented harness stop lying about what exists.
10. **Be skeptical of ceremony, as instructed.** This track's concrete
    recommendation is to define **one** subagent, not four, and to build the
    PHI hook only as a narrowly-scoped, explicitly-limited dev-time net — never
    as a restatement of the privacy guarantee the product already enforces
    correctly in code. Do not add a 37th skill.

---

## 1. Enforcement classification

Legend: **Enforced** = an agent (or a careless human) mechanically cannot
proceed. **Checked** = CI fails, but only after the fact, and only if something
downstream (branch protection) actually blocks the merge — which cannot be
verified from a repo checkout alone; GitHub's branch-protection rules are not
stored in git. **Advisory** = prose an agent may read, and may ignore, with
nothing else stopping it.

| Mechanism | Class | What it actually stops |
|---|---|---|
| `core/llm/ollama_provider.py::_assert_localhost` | **Enforced** | Any non-local `base_url` raises `ValueError` at construction (`ollama_provider.py:40-52`, called at `:73`). Holds regardless of what CLAUDE.md says, or whether an agent read it. |
| Agent tool registry input validation | **Enforced** | Malformed tool-call args are never executed — the first guardrail layer, per `skills/asclexis-agent/SKILL.md:33-37`. Currently moot in practice because no node calls a model yet (`00-brief.md` gap G1), but the mechanism itself is real code, not prose. |
| `scripts/feature_list_lint.py` (CI: `docs-lint` job) | **Checked** | Malformed / duplicate / structurally incomplete `feature_list.json` entries fail CI before merge (`ci.yml:28`). Cannot detect a *dishonestly* `completed` entry — only structure. |
| `scripts/docs_lint.py` + `generate_docs_index.py --check` (CI: `docs-lint`) | **Checked** | 14 categories of doc drift: stale banners, broken relative links, canonical-order mismatch across 3 files, orphaned docs, frontend README script drift (`ci.yml:22-25`). Does **not** check that a doc's claim about *code or config existing* is true — see the divergence table; this is the exact gap `harness_drift_check.py` (§4, §Recommendations) would close. |
| `scripts/agent_eval_gate.py` (CI: `agent-evals`) | **Checked** | Regressions in the **product's** agent on 6 axes / 74 golden cases. This gates the thing Track 3 researched, not the dev harness this track researches — listed here because CLAUDE.md and this repo's docs sometimes cite it as harness evidence generally. |
| `scripts/security_gate.py` (CI: `security-scan`) | **Checked, with a silent-pass gap** | High/critical Bandit/pip-audit findings block CI *if the report file exists and parses*. `check_bandit`/`check_pip_audit` (`security_gate.py:44-51, 71-78`) catch `FileNotFoundError`/`JSONDecodeError`, print a `WARNING`, and return `[]` — treated identically to "scanner ran clean." Combined with `ci.yml`'s `\|\| true` on the scan steps (so a crashing scanner does not itself fail the job), a scanner that crashes before writing its report would make this gate **pass with zero findings**, not fail. Not confirmed to have happened; confirmed to be possible by reading the code. |
| `scripts/repo_hygiene_check.py` | **Advisory in practice** | The script's *logic* is regression-tested against synthetic `tmp_path` fixtures by `test_repo_hygiene_check.py`, and that test file does run in CI (it's part of `bash scripts/run-backend-tests.sh -q`). But the script is never invoked with `--repo-root .` against the real tree in any CI job — `grep -n "repo_hygiene_check" .github/workflows/ci.yml` returns nothing. An agent can drop a scratch `PLAN.md` at repo root today and every CI job stays green. The only enforcement is a human/agent voluntarily running it per `README.md:393` / `CONTRIBUTING.md:75,187,196`. |
| 36 skills (`.claude/skills/` × 32, `skills/` × 4) | **Advisory, by design** | Skills are model-invoked: "Claude automatically uses them based on the task context," per Anthropic's own skill docs, unless a skill sets `disable-model-invocation`. None here do. Nothing forces a trigger; a skill not triggered simply never runs. |
| `.claude/agents/` subagents (4 named scanners + 1 implementer) | **Does not exist** | Nothing — the directory is absent. |
| PreToolUse PHI/network-egress hook | **Does not exist** | Nothing — no hook infrastructure of any kind is present in this repo. |
| CLAUDE.md "ask before touching" (safety modules, auth/encryption) | **Advisory** | Nothing mechanically prevents an `Edit` to `modules/redaction.py`; it is prose loaded as project memory, honored only if the agent reads and complies. |
| CLAUDE.md "no network calls in product code paths" (general form) | **Enforced for the one verified instance, advisory as a blanket rule** | `_assert_localhost` enforces it for the Ollama provider specifically. Nothing scans a diff for a *new* `requests.get(...)`/`httpx` call added anywhere else in the codebase — the general rule depends entirely on the next agent reading CLAUDE.md. |
| `docs/agentic/progress.md` (append every session) | **Advisory** | Nothing checks it was updated, and nothing cross-references its prose against `feature_list.json` status transitions. |
| `AGENT.md` "Definition of Done" checklist | **Advisory** | A self-certification checklist; no automation verifies any line of it. |
| CI required-status-checks / branch protection | **Unverifiable from this checkout** | GitHub branch-protection settings live in repo settings, not in git. Whether a red CI run actually blocks a merge to `main` cannot be confirmed from the files alone. Worth an owner confirming directly in GitHub settings — this single fact determines whether "Checked" above is functionally closer to "Enforced" or is actually just "Advisory with extra steps." |

---

## 2. Research: the current state of harness building

### 2.1 Hooks — lifecycle events and what they can (and cannot) block

Fetched directly from `code.claude.com/docs/en/hooks` (primary source):

- **Roughly 30 lifecycle events**, grouped as per-session (`SessionStart`,
  `SessionEnd`, `Setup`), per-turn (`UserPromptSubmit`, `Stop`, `StopFailure`),
  tool-execution (`PreToolUse`, `PermissionRequest`, `PermissionDenied`,
  `PostToolUse`, `PostToolUseFailure`, `PostToolBatch`), and others
  (`SubagentStart`/`SubagentStop`, `PreModelSwitch`/`PostModelSwitch`,
  `FileChanged`, `Notification`, …).
- A command hook receives JSON on stdin (`tool_name`, `tool_input`,
  `session_id`, `cwd`, …) and blocks by either exiting `2` (always blocks,
  overrides any JSON) or emitting
  `{"hookSpecificOutput": {"permissionDecision": "deny", ...}}` with exit `0`.
- **The load-bearing limitation for this track**, quoted directly from the docs:
  hooks "run with full user permissions," are "not sandboxed," provide
  "best-effort filtering only, not enforcement," and the documentation
  explicitly says to "use the permission system rather than a hook to enforce a
  hard allow or deny." Bash-pattern matchers can be defeated by variable
  expansion or command substitution the hook didn't anticipate. Async hooks
  (shipped January 2026 per multiple 2026 hook guides — [UNVERIFIED] exact
  ship date, corroborated by 3 independent 2026 blog summaries but not a
  primary changelog) bypass timeout enforcement entirely.
- **Direct implication for the PHI-hook claim**: even a well-built
  `PreToolUse` PHI scanner is a best-effort net, not the enforcement layer the
  CS4610 report implies. This is not a reason not to build it — narrow,
  well-scoped dev-time guardrails are worth having — but it is a reason never
  to describe it as satisfying the "redaction before egress" hard invariant,
  which is a product-code responsibility already handled correctly by
  `modules/redaction.py` and `_assert_localhost`.
- **Regex/pattern-based PHI detection has known, structural false-negative
  and false-positive rates** independent of Claude Code specifics: strict
  patterns (e.g., requiring "MRN" or "patient number" literally precede a
  digit string) have low false-positive rates but let unlabeled identifiers
  through; loose patterns catch more but bury real hits in noise. Clinical-NLP
  literature reports the majority of de-identification errors are *false
  negatives*, and single-word names are especially hard to catch without
  context. A hook built on the cheapest version of this (a handful of regexes)
  will under-catch; a hook built on the more careful version (context-aware
  rules, a curated term dictionary) is real engineering effort, not an
  afternoon's work — this repo's own `modules/redaction.py` is 217 lines
  precisely because this problem is not trivial, and any hook-side detector
  duplicates that logic in a second, harder-to-keep-current place.

### 2.2 Skills authoring and progressive disclosure

- Progressive disclosure means Claude Code loads only a skill's frontmatter
  (`name` + `description`) at session start; the full `SKILL.md` body loads
  only once the skill triggers, and files a skill references (e.g.
  `reference/finance.md`) load only when the model reads them via a tool call.
  This is exactly the mechanism this repo's own 36 skills already use — no
  gap here, the repo's skill layer matches documented best practice
  (frontmatter-first, body under ~500 lines, split long content into
  linked files).
- The frontier addition since a May-2026 cutoff is **skills becoming a
  plugin-distributable unit with a namespace** (`/plugin-name:skill-name`) —
  see §2.4. This repo's skills are still purely standalone (`.claude/skills/`,
  `skills/`), never packaged as plugins, which is consistent with them being
  local process/domain conventions rather than something meant to be shared
  outside this repo.
- Nothing in the research surfaced a documented mechanism to make a skill's
  invocation *mandatory* beyond the model's own judgment, other than removing
  the choice entirely via `disable-model-invocation: true` (which only means
  "never auto-trigger," the opposite of "always trigger") or wiring the skill
  behind a hook that fires regardless of the model's intent. This confirms
  point 4 in the Summary: skills cannot be upgraded to "enforced" by writing a
  stronger description.

### 2.3 Subagent definitions and scoping

Fetched directly from `code.claude.com/docs/en/sub-agents` (primary source).
Only `name` and `description` are required frontmatter fields; the rest is
optional and has grown substantially:

| Field | Purpose |
|---|---|
| `tools` / `disallowedTools` | Allow/deny-list of tools — the mechanism `harness.md:27` implicitly relies on ("read-only scanners") but that this repo never actually configured, since the files don't exist |
| `model` | Route to a specific model (`sonnet`, `opus`, `haiku`, or a full ID) — the "cheap models" `harness.md:27` names |
| `permissionMode` | `default` / `acceptEdits` / `auto` / `dontAsk` / `bypassPermissions` / `plan` — `plan` gives genuine read-only exploration |
| `isolation: worktree` | Runs the subagent in an isolated git worktree — directly relevant to `using-git-worktrees` skill already vendored here |
| Spawn depth limit | Subagents nest up to 3 layers by default, configurable via `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`; `1` disables nesting |

Storage is priority-ordered: managed org settings > `--agents` CLI flag >
`.claude/agents/` (project, checked into version control) >
`~/.claude/agents/` (personal, cross-project) > a plugin's bundled `agents/`
directory. **This repo's documented intent (`harness.md:25`, "project-specific
scanners kept out of the main context") maps cleanly onto the project-scoped
tier** — the mechanism to do exactly what the docs describe exists and is
well-specified; it was simply never built.

Automatic delegation is description-driven (the same "advisory unless a hook
backs it" pattern as skills); explicit invocation via `@-mention` or
`--agent` at session start guarantees it. A subagent given `tools: Read, Grep,
Glob` cannot escalate itself — that allowlist is enforced by Claude Code
itself, not by the subagent's own good behavior, which is the one place in
this whole survey where "read-only scanner" can be a structural guarantee
rather than a written promise, **if the subagent file is actually built with
an explicit `tools:` allowlist** (a `.claude/agents/*.md` with no `tools:`
field at all inherits everything, including `Edit`/`Write` — worth stating
explicitly in any future definition, since `harness.md:29-30`'s promise that
"subagents never touch the safety-critical modules" needs the `tools:`/
`disallowedTools:` field set to be true rather than merely intended).

### 2.4 Plugins and marketplaces

Fetched directly from `code.claude.com/docs/en/plugins` (primary source). A
plugin is a directory with an optional `.claude-plugin/plugin.json` manifest
that can bundle `skills/`, `agents/`, `hooks/hooks.json`, `.mcp.json`,
`.lsp.json`, `monitors/monitors.json`, `bin/` (added to `PATH`), and a
`settings.json` that can force-activate one of the plugin's agents as the
session's main agent. Two Anthropic-run marketplaces exist:
`claude-plugins-official` (curated, no application process, Anthropic's
discretion) and `claude-community` (public submissions, reviewed, validated
via `claude plugin validate`, pinned to a commit SHA once approved). Community
market size by mid-2026 was reported in the thousands of third-party entries
(one 2026 review cited "over 9,000... with roughly 100 first-party and
partner plugins" — [UNVERIFIED], single-source figure, directionally
plausible but not independently corroborated).

**Relevance to this repo**: none of its skills or (nonexistent) subagents/hooks
are packaged as a plugin. That is a reasonable choice — these are
project-specific conventions (`asclexis-*` skills), not something meant to be
installed elsewhere — but it does mean this repo gets none of a plugin's
version-pinning or `claude plugin validate` safety net for free. If the
`asclexis-*` skills or a future subagent set ever need to travel with the
repo in a more portable way (e.g. for a CI-run headless agent), packaging them
as a single local plugin with a pinned `version` would be a cheap way to get
that validation step without a marketplace.

### 2.5 Output styles

Output styles change the system prompt's tone/role/format (`Default`,
`Explanatory`, `Learning`, `Concise`, or a custom Markdown file selected via
`/output-style`). **This is not an enforcement primitive** and this track
found no way it could be — it changes *how* an agent talks, not *what it is
permitted to do*. Zero references to output styles exist anywhere in this
repo (`grep -rn "output-style\|outputStyle"` → nothing). Consistent with
Track 2's "MoE is not the win here" finding: naming this because the task
asked for coverage, not because it belongs in the Recommendations section.

### 2.6 Claude Agent SDK

The SDK (renamed from "Claude Code SDK" in late 2025) exposes the same tool
loop, context management, and compaction Claude Code itself runs, as a Python
or TypeScript library, so a team can build a **custom** harness rather than
configure Claude Code's. Relevant to this track only as an alternative *not*
worth pursuing here: this repo's harness needs are met by configuring Claude
Code's existing primitives (skills, and — if built — subagents/hooks), not by
standing up a separate SDK-based orchestrator. The SDK is the right tool when
you need a bespoke agent product (e.g. Track 3's *product* agent, if it ever
grows a generative planner) — it is the wrong tool for "make the coding agent
that builds Asclexis behave better," which is squarely Claude Code's own
configuration surface. [UNVERIFIED] specific PyPI/npm version numbers
returned by search (`claude-agent-sdk` "0.2.139," `@anthropic-ai/claude-agent-sdk`
"0.3.233") are single-source and not verified against the actual registries in
this pass; the qualitative claim (rename, active weekly releases) is
corroborated across multiple 2026 sources.

### 2.7 The three studied frameworks — what changed since the May 2026 reports

The Technical Companion's own comparison table (`CS4610_Report_Demo/…Technical_Companion.pdf`,
p.12, reproduced faithfully here since it is the most precise existing
statement of each framework's enforcement model at the time it was written)
gives the May-2026 baseline:

| Dimension | superpowers (May 2026) | GSD v2 (May 2026) | everything-claude-code (May 2026) |
|---|---|---|---|
| Primary enforcement | Skill-based mandatory invocation | File-driven orchestrator + fresh-context agents | Skills + extensive PreToolUse/PostToolUse hooks |
| Planning artifact | `docs/superpowers/specs/*-design.md` + `plan.md` | `PROJECT.md`/`REQUIREMENTS.md`/`ROADMAP.md`/`STATE.md`/`DECISIONS.md` | `AGENTS.md` + per-skill `SKILL.md` |
| Review step | Spec Reviewer + Code Reviewer subagents (mandatory) | Plan Checker + Verifier + Debugger | code-reviewer + language reviewers + security-reviewer + AgentShield |
| Isolation | git worktree + fresh subagent context per task | Fresh 200K-token context per atomic task | Hook profiles (minimal/standard/strict) + subagent scoping |
| Stuck-loop detection | Human spots it | Sliding-window pattern analyzer; one retry then halt | loop-operator agent + Stop hook |

**What this track verified has changed since then**, each with a search
source (all corroborated across ≥2 independent 2026 sources unless noted):

- **superpowers** was accepted into the official Anthropic plugin marketplace
  (reported January 15, 2026 — [UNVERIFIED] exact date, single strong source)
  and expanded from a Claude-Code-only skill set to working across "eight
  coding-agent harnesses" including Cursor, OpenAI Codex, GitHub Copilot CLI,
  Gemini CLI, and OpenCode. Its enforcement model did **not** change — it is
  still skill-based, still trusts the model to invoke the right skill, still
  relies on the Iron Law being *read* rather than mechanically imposed. The
  author has also published about "the agentic slop PR problem the project
  has exposed as it has scaled" ([UNVERIFIED] characterization from a single
  aggregator source, not the primary post, which was unreachable) — worth
  flagging as an open question about whether skill-based enforcement holds up
  at scale, which is directly relevant to whether this repo's 36-skill,
  purely-advisory model will keep working as the repo grows.
- **GSD v2** matured into a real production tool with a public issue tracker
  (`github.com/gsd-build/gsd-2`), and that tracker is more valuable evidence
  than any marketing claim: it documents **an actual stuck-loop-detection
  failure** — a `claude-code` provider that reports a 1M-token context window
  when the real API limit is ~200K caused GSD's wrap-up signal to never fire,
  producing infinite retry loops across process restarts (issue #4676), and a
  separate report of the auto-loop reliably crashing on its second iteration
  against that same provider (issue #5403). This is concrete, verifiable
  (via GitHub issue numbers, not paraphrase) evidence that **a framework's
  stuck-loop detector is only as good as its assumptions about the provider
  it's driving** — a load-bearing caution for §3 below, since this repo's
  loop, if ever built, would be driving Claude Code against the exact kind of
  context-window/limit mismatches these issues describe.
- **everything-claude-code** shipped v1.9.0 (reported March 2026 — 212
  commits, six new agents, 15+ new skills, 12 language ecosystems —
  [UNVERIFIED] precise counts, single strong source) and added **hook runtime
  controls** (`ECC_HOOK_PROFILE=minimal|standard|strict`,
  `ECC_DISABLED_HOOKS=...`) specifically in response to community complaints
  about hook conflicts — i.e., the framework whose entire pitch is
  "unskippable enforcement via hooks" needed to add an escape hatch because
  hooks were colliding with each other and with users' own workflows in
  practice. New harness-observability commands (`/harness-audit`,
  `/loop-start`, `/loop-status`, `/quality-gate`, `/model-route`) suggest the
  project itself concluded that hooks alone weren't legible enough without a
  status/audit layer on top — a useful design lesson for anyone building a
  narrow hook here: pair it with a way to see that it fired, not just that it
  exists.

**Net read for this repo**: this repo already made, in practice if not in so
many words, the same bet the comparison table's own conclusion states —
"For a solo developer who wants a disciplined workflow inside Claude Code,
superpowers is the lightest weight and easiest to adopt" (Technical Companion,
p.12). It vendored superpowers wholesale (14 skills) and the closest
comparable Pocock set (18 skills), and built zero of ECC's hook layer despite
citing ECC's `AgentShield` as the model for the PHI claim. The gap this track
found is not "we chose the wrong framework" — it is "the docs describe
adopting pieces of GSD's subagent model and ECC's hook model that were never
actually built."

---

## 3. Loop engineering for development

**No autonomous, multi-hour, unattended loop exists in this repo today.**
Everything in `docs/agentic/harness.md`'s 6-step loop assumes a human or
single-session agent working synchronously, checking in at each step. This
section answers what would need to be true before that changed, specifically
for a health codebase.

**What already works, and is worth naming as a working example** (this
research pass practiced it on itself): `PLAN.md` §3 dispatched 8 parallel
Sonnet researchers, each read-only, each writing only its own numbered file —
exactly the "fresh-context subagent dispatch" pattern GSD v2 and superpowers
both formalize. `PLAN.md` §9's execution record is honest about a real
failure mode within that pattern: 5 of 8 researchers hit an account-level
rate limit (HTTP 429) *after* writing their files, and the orchestrator's
recovery was to inspect the actual files rather than trust the failed
session's status message. That is the correct instinct — CLAUDE.md's
"an agent's report is a lead, not a finding" applied to infrastructure
failure, not just content — and it generalizes directly to any future loop:
**verify against the artifact, never against the runner's own exit status.**

**Ralph-style loops** (the technique, not a specific product): an agent is
re-fed the same prompt/spec repeatedly, each iteration in a fresh context,
until a defined completion signal (passing tests, a specific output token,
a file marker) is reached. The technique's own documented failure mode,
reported by its practitioners, is exactly the one CLAUDE.md already
guards against by a different name: "running loops too long without a tight
exit criterion cost more in tokens than it was worth" (CS4610 Final Report
§8, this repo's own document) — the lesson being that "autonomous" only pays
off when the loop has a *real* stop condition, not merely "keep going until
told to stop."

**What a safe unattended loop on this codebase specifically requires,**
synthesized from the research above and this repo's own hard invariants:

1. **Structural denylists, not prompted ones, on the four safety modules and
   auth/encryption.** CLAUDE.md's "ask before touching" works when a human is
   present to be asked. An unattended loop has nobody to ask — so the "ask"
   must become a `disallowedTools`/deny-permission rule a subagent or hook
   enforces mechanically (§2.3, §2.1), not a sentence the loop's own prompt
   repeats to itself every iteration. This is the single highest-leverage
   change available if this repo ever builds an unattended loop, and it is
   cheap: a `permissions.deny` rule naming those four files plus any
   `auth`/`security`/`encrypt` path glob.
2. **The eval gates as blocking preconditions between phases, not just at PR
   time.** `agent_eval_gate.py` and `security_gate.py` should gate the loop's
   own advance to the next unit of work, not merely gate the final PR. A loop
   that writes ten commits before ever running `agent_eval_gate.py` has ten
   commits' worth of exposure if commit three broke groundedness.
3. **A real exit criterion that is a governance check, not just "tests
   green."** The single most dangerous unattended-loop failure mode this
   repo's own CLAUDE.md is written to prevent — "never weaken a safety check,
   lower a test threshold ... to make something pass" — is *easier* for an
   unattended loop to fall into than for a supervised one, because the loop's
   only feedback signal is whatever check it's told to satisfy. If "tests
   green" is the only signal, a loop under pressure to converge will find the
   shortest path to green, and lowering `test_api_rag_index_002b`'s 0.7
   threshold is exactly that shortest path. The exit criterion must
   explicitly include "no threshold, assertion, or waiver was weakened" as a
   checked condition, not an assumed one — this is checkable today by diffing
   against known thresholds (the 0.7 in `test_api_rag_index_002b`, the
   `WAIVERS` dict in `security_gate.py`, the four eval-gate bars in
   `agent_eval_gate.py`) before the loop is allowed to call itself done.
4. **Named escalation triggers specific to this repo**, not a generic "ask a
   human when unsure": any diff touching
   `modules/interpret_safety.py`/`redaction.py`/`faithfulness.py`/`verifier_agent.py`
   or auth/encryption code; any change to a numeric threshold or an assertion
   in a test; any change to `security_gate.py`'s `WAIVERS`; any
   `feature_list.json` status flip to `completed`. Each of these is
   mechanically detectable (a file-path check, a numeric-literal diff, a
   status-field diff) and each maps directly to something this repo's own
   recurring-failures doc has already been burned by.
5. **A step/turn budget analogous to the product's own `MAX_STEPS`.** The
   product's agent caps itself at ≤5 tool calls per question and treats
   budget exhaustion as a graceful terminal (`skills/asclexis-agent/SKILL.md:42-44`).
   A development loop with no analogous cap either burns budget uselessly
   (the GSD v2 infinite-retry issues above) or, worse, keeps iterating on a
   red check until it finds a way to make the check pass rather than the
   underlying thing true.
6. **Verify a framework's own stuck-loop detector against the actual
   provider before trusting it**, per the GSD v2 issue-tracker evidence above
   — a detector that trusts a provider-reported context window can silently
   never fire.

None of this requires adopting GSD v2 or ECC wholesale. It requires the same
discipline this repo already applies to the *product's* agent — a step
budget, a fixed set of terminal states, an audit trail per step — applied to
whatever development loop this repo eventually runs.

---

## 4. Evals for the development loop

The product has `agent_eval_gate.py`: 6 axes, 74 golden cases, gates CI.
**Nothing measures whether the development harness keeps agents on task.**
The following is deliberately cheap — none of it requires new
infrastructure beyond what already exists (`git log`, `gh run list`,
existing lint-script patterns) — because a heavyweight eval suite for the
harness itself would be the exact ceremony this track was told to be
skeptical of.

| Metric | What it would show | How to compute it cheaply |
|---|---|---|
| **Gate-trip rate** | Which CI gate catches the most problems, and whether that rate is falling (harness improving) or flat (harness not learning) | `gh run list --json conclusion,name,createdAt` parsed per job name, no new code |
| **Rework rate** | How often a `fix:` commit immediately follows a `feat:`/`fix:` commit touching the same file(s) within a short window — a proxy for "the first attempt didn't hold" | `git log --name-only` grep, no new code |
| **Verification-pass-on-first-attempt** | Whether a feature's first verification run passed or needed a RED→GREEN cycle — currently buried in `progress.md` prose (e.g. "RED before fixes... PASS after," already present in the 2026-07-07 entry) | Formalize as two required fields on a completed `feature_list.json` entry (`first_verification_result`, `final_verification_result`) and extend `feature_list_lint.py` (same shape as its existing 7 checks) to require them when `status` flips to `completed` |
| **Recurring-failure recurrence** | Whether the harness is actually learning — new entries added to `recurring-failures.md` over time, and whether the *same* failure mode's recheck ever fires again after being documented | Literally count entries/quarter; pair with gate-trip rate as a sanity check (a recurring failure that a gate should have caught but didn't is itself a gate-design bug) |
| **Stale-authority half-life** | How long a doc claim survives after becoming false before something catches it | `STATUS.md` is already doing this by hand for the 2026-09-08 tracks; formalizing it just means tracking the gap, in days, between a shipping commit and the doc-fix commit that corrects the line it made stale |
| **Harness drift check (proposed, concrete)** | Whether `docs/agentic/*.md`, `CLAUDE.md`, `AGENT.md` claim a harness artifact (a path, a script, a CI wiring) that does or doesn't actually exist | A new `scripts/harness_drift_check.py`, ~50-80 lines, same shape as the 14 existing `docs_lint.py` `DOC-*` checks: a small table of `(doc, line-pattern, path-that-must-exist-or-not)` assertions. This single script, if it had existed on 2026-09-08, would have caught **both** verified gaps this track was dispatched to find, on the first CI run after `harness.md` was written. |

The `harness_drift_check.py` proposal is the flagship recommendation of this
section because it is the only one of the five that would have prevented the
exact failure this entire track exists to document, and it costs about the
same as one more `DOC-*` rule in a linter this repo already runs in CI.

---

## 5. Documented-vs-actual divergence

| Documented claim | Where | Actual state | Evidence |
|---|---|---|---|
| "Subagent definitions live in `.claude/agents/`," naming `docs-consistency-scanner`, `dependency-policy-auditor`, `agentic-roadmap-researcher`, `verification-engineer` (read-only scanners) and `windows-bootstrap-engineer` (specialist implementer) | `docs/agentic/harness.md:25-28` | Directory does not exist | `ls .claude/agents/` → *No such file or directory* |
| "Agent orchestration" listed as a portfolio-relevant skill, pointing at `.claude/agents/` | `docs/agentic/roadmap.md:17` | Same — nothing to point at | same |
| The four scanner names appear nowhere else in the repo — no subagent file, no `progress.md` entry, no commit message, no research-track file | (absence, checked across the whole repo) | Either used once as untracked ad-hoc Task dispatches, or aspirational from the start | `grep -rln "docs-consistency-scanner\|dependency-policy-auditor\|agentic-roadmap-researcher\|verification-engineer\|windows-bootstrap-engineer"` across `*.md`/`*.json` → only `docs/agentic/harness.md` itself |
| "A PreToolUse hook scans for patterns that look like PHI and blocks any tool call that would send them to a network" | `CS4610_Report_Demo/HealthCentral_CS4610_Final_Report.pdf`, §7.2, p.10 | No `.claude/settings.json`, no `hooks.json`, no `.claude/hooks/` anywhere | exhaustive `find … -iname "settings*.json"` / `-iname "hooks.json"` / `-path "*/.claude/hooks*"` → all empty |
| "AgentShield was wired as a PreToolUse hook scanning every edit for PHI patterns; any tool call that would emit identifiable medical data onto a network interface is blocked before it runs" | `CS4610_Report_Demo/HealthCentral_CS4610_Technical_Companion.pdf`, §4.6, p.7 | Same as above; `AgentShield` (an `everything-claude-code` component) is referenced nowhere else in this repo | `grep -rn "AgentShield"` across the repo → only inside the two CS4610 PDFs themselves |
| `scripts/repo_hygiene_check.py` documented as part of the pre-merge "proof bundle" | `README.md:393`, `CONTRIBUTING.md:75,187,196`, `docs/agile/GROUNDING.md:103` | Never invoked against the live repository in CI; only its unit tests (against synthetic `tmp_path` fixtures) run in CI | `grep -n "repo_hygiene_check" .github/workflows/ci.yml` → no matches |

Note what is **not** in this table: `docs/agentic/evals.md` and `mcp-tools.md`
were checked line-by-line against the actual six scripts, `.mcp.json`, and
CI workflow, and every concrete claim in them (script names, CI job names,
what each gate checks) resolved correctly. The divergence in this repo is
narrow and specific — the subagent and hook claims — not a general pattern of
the docs being unreliable. That precision is itself useful: it means the fix
is two targeted corrections plus one new drift-detecting check, not a
docs-wide audit.

---

## Recommendations

Ordered by priority. Effort/maintenance are rough (XS/S/M/L) for a
one-person maintainer, per the constraint that anything proposed here must be
maintainable by one person.

| Change | What it enforces | Effort | Maintenance cost | Risk of ceremony |
|---|---|---|---|---|
| **Fix the `.claude/agents/` and hook claims in `harness.md`/`roadmap.md`** — either delete the false claims or build the minimum real version (see next two rows) | Doc-trustworthiness; directly closes `recurring-failures.md` #8's newest instance | S (docs-only) | Low once fixed | None — this is debt repayment |
| **Add `scripts/harness_drift_check.py`, wired into the `docs-lint` CI job** | That a doc claiming a specific harness path/script/CI-wiring exists is actually true, going forward | S (~50-80 lines, same shape as 14 existing `DOC-*` checks) | Low — same maintenance pattern as `docs_lint.py` already carries | Low — one more grep-shaped CI rule, not a new process |
| **Wire `repo_hygiene_check.py` into the `docs-lint` CI job** (one line: `python3 scripts/repo_hygiene_check.py`) | Repo-root scratch-file hygiene, for real, not just in a unit test | XS | ~0 | None |
| **Fail closed in `security_gate.py` when a report file is missing or malformed**, instead of treating it as zero findings | That `security-scan` actually fails when the scanner itself failed to run | XS (a few lines) | ~0 | None — closes a real "green suite that could not have failed" instance |
| **Define exactly one subagent for real** — `docs-consistency-scanner`, project-scoped, explicit `tools: Read, Grep, Glob` allowlist, cheap model — and prove it earns its keep on one real doc-drift hunt (logged in `progress.md`) before building any of the other three | Cheap-model repo survey actually happens on a fresh context instead of burning main-thread budget; makes `harness.md:27`'s "read-only" claim structurally true via `tools:`, not just asserted | S | Low-medium (prompts rot as the repo changes, same as any skill) | Medium if built and left unused — gate its existence on a demonstrated first use |
| **Do not define the other three named subagents** (`dependency-policy-auditor`, `agentic-roadmap-researcher`, `verification-engineer`) until the first one proves out | Nothing — a deliberate "do not build yet" | — | — | High if built prematurely: three more named-but-unrun files, exactly the pattern that produced this track's own finding |
| **Build the PHI/network `PreToolUse` hook only as a narrowly-scoped dev-time net**, matching Bash/WebFetch calls for PHI-shaped patterns (MRN-like IDs, name+DOB pairs, obvious synthetic-fixture leakage), with its limitations documented in the hook's own file and in CLAUDE.md: it is best-effort (Anthropic's own docs), it has a real false-negative rate (PHI-detection literature), and it is never a restatement of the "redaction before egress" invariant, which stays a product-code responsibility already met by `_assert_localhost`/`modules/redaction.py` | Catches an agent about to leak PHI-shaped text via its *own* coding-session tool calls (e.g., debugging with real-shaped fixtures pasted into a `curl`) — a real, narrow footgun distinct from the product's runtime guarantee | M — needs a real pattern set, test fixtures, and false-positive tuning, not a five-line regex | Medium-high — regex/pattern rot needs periodic review, same discipline `modules/redaction.py` already requires | Medium-high if oversold — must never be cited as satisfying CLAUDE.md's redaction invariant |
| **Formalize RED→GREEN as two `feature_list.json` fields** (`first_verification_result`, `final_verification_result`), required by `feature_list_lint.py` when `status` becomes `completed` | Verification-pass-on-first-attempt becomes a queryable metric instead of prose buried in `progress.md` | S | Low | Low — reuses an existing lint script's shape |
| **Track gate-trip rate and rework rate passively for one quarter** before building any dashboard (`gh run list` + a `git log` grep are enough to start) | Nothing yet, deliberately — a measurement-before-building step | XS | None | High avoided — do not build eval infrastructure for the dev harness before the passive numbers show something worth automating |
| **Do not add a 37th skill.** If an `asclexis-*` domain skill needs to grow, extend it in place (CLAUDE.md §2) rather than splitting a new one out | Nothing new; a deliberate ceiling | — | — | High avoided — 36 is already at the edge of what one person keeps current, and this track's own finding (a stale claim in a doc nobody re-checked) is exactly what a 37th skill risks becoming |
| **Confirm branch-protection / required-status-checks directly in GitHub settings** (cannot be done from this checkout) | Whether "Checked" gates in §1 are functionally "Enforced" or just "Advisory with extra steps" — the single fact this whole classification exercise cannot resolve on its own | XS (a settings check, not code) | None | None |

---

## Sources

Repo evidence (path:line citations given inline above; not re-listed here).
External sources, in the order first cited:

- [Claude Code Hooks reference](https://code.claude.com/docs/en/hooks) — fetched directly; lifecycle events, blocking mechanism, "not a security boundary" limitation
- [Claude Code Sub-agents](https://code.claude.com/docs/en/sub-agents) — fetched directly; frontmatter fields, storage priority, tool/permission scoping, spawn depth
- [Claude Code Create plugins](https://code.claude.com/docs/en/plugins) — fetched directly; plugin structure, marketplaces, `claude plugin validate`
- [Claude Code Output styles](https://code.claude.com/docs/en/output-styles) — via search summary; built-in styles, custom style format
- [Claude Docs — Skill authoring best practices](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices) / [platform.claude.com equivalent](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) — via search summary; progressive disclosure, SKILL.md size guidance
- [Anthropic — Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) — cited via search summary only; direct fetch to `anthropic.com` blocked by this session's egress proxy
- Claude Agent SDK coverage: [claude.com/blog/building-agents-with-the-claude-agent-sdk](https://claude.com/blog/building-agents-with-the-claude-agent-sdk), [Hatchworks](https://hatchworks.com/blog/claude/agent-sdk/) — via search summary; rename history, capability surface; specific version numbers flagged [UNVERIFIED]
- [obra/superpowers](https://github.com/obra/superpowers/) and coverage at [blog.marcnuri.com](https://blog.marcnuri.com/superpowers-claude-code-skills-framework), [rywalker.com](https://rywalker.com/research/superpowers-skills-framework), [claudeskills.info](https://claudeskills.info/plugins/obra/superpowers/) — via search summary; marketplace acceptance, cross-harness expansion, star counts flagged [UNVERIFIED]
- [gsd-build/gsd-2](https://github.com/gsd-build/gsd-2) issues [#4676](https://github.com/gsd-build/gsd-2/issues/4676) and [#5403](https://github.com/gsd-build/gsd-2/issues/5403), discussion [#3909](https://github.com/gsd-build/gsd-2/discussions/3909) — via search summary of primary GitHub issue content; stuck-loop-detection failure against a context-window-misreporting provider
- [affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code) and coverage at [augmentcode.com](https://www.augmentcode.com/learn/everything-claude-code-hits-163k-stars), [apiyi.com](https://help.apiyi.com/en/everything-claude-code-plugin-guide-en.html) — via search summary; v1.9.0 changes, hook-profile runtime controls, `AgentShield`
- Ralph-technique coverage: [claudefa.st](https://claudefa.st/blog/guide/mechanics/ralph-wiggum-technique), [sidbharath.com](https://sidbharath.com/blog/ralph-wiggum-claude-code/), [codecentric.de](https://www.codecentric.de/en/knowledge-hub/blog/the-ralph-wiggum-loop-autonomous-code-generation-with-a-fresh-context) — via search summary; completion-signal mechanism, overnight-loop reports
- Stuck-loop detection patterns: [dev.to/alanwest](https://dev.to/alanwest/why-your-ai-agent-loops-forever-and-how-to-break-the-cycle-12ia), [Medium/kacperwlodarczyk](https://medium.com/@kacperwlodarczyk/stuckloopdetection-how-we-stopped-an-agent-burning-12-on-47-identical-calls-a12b5ea1f193) — via search summary; tool-call fingerprinting, sliding-window pattern detection
- PHI/PII detection limitations: [Fortra DLP](https://www.fortra.com/resources/guides/phi-identifiers-dbrm), [Prosearch](https://www.prosearch.com/beyond-regex-smarter-strategies-for-detecting-pii-and-phi-in-ediscovery/), [PMC — Automatic Detection of PHI from Clinic Narratives](https://pmc.ncbi.nlm.nih.gov/articles/PMC4989090/) — via search summary; regex false-positive/false-negative tradeoffs, clinical-NLP error rates
- Harness-effectiveness / rework-rate framing: [Faros — Harness Engineering](https://www.faros.ai/blog/harness-engineering), [Axify — AI coding tools' impact](https://axify.io/blog/ai-coding-tools-impact) — via search summary; quality-gate/rework framing used to shape §4's metric proposals
- `CS4610_Report_Demo/HealthCentral_CS4610_Final_Report.pdf` and `HealthCentral_CS4610_Technical_Companion.pdf` — this repo's own source documents, read directly (via `pypdf` text extraction, since `poppler-utils` could not be installed in this session — package fetch failed against the sandboxed apt mirror); §7.2 and §4.6 respectively, plus the three-framework comparison table on Companion p.12

Blocked during this pass (session egress proxy, not a source-availability
issue): `www.anthropic.com`, `addyosmani.com`, `www.zenml.io`. Anthropic's
"Effective harnesses for long-running agents" engineering post is real and
frequently cited by secondary sources but could not be fetched directly in
this session; claims attributed to it above are drawn from secondary-source
paraphrase and are flagged accordingly.
