# RSI harness 2026-10-31 — plans for RSI-ERRCLASS-NONBASH, RSI-RULE-TOOLFIELD, RSI-MINE-OUTCOMES and RSI-OWNER-NOTES

**Last Updated:** 2026-10-31 (Opus planner on `d6bc6643`: four RSI-loop improvements planned as queue rows, per owner row RSI-HARNESS-PLAN (answered 2026-10-31; recorded by a parallel docs PR). Each row is **planned, awaiting owner approval**, not ready)
**Owner:** repository owner
**Status:** PROPOSED (Opus planner). Docs only. **No owner approval is recorded here.** Every row needs its own owner yes (gate **RSI-HARNESS-GO**, one answer per row) before build-item may claim it. Every gate keeps its state in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md). The drafted owner questions at the end are not asked; L0 has them reviewed before AskUserQuestion.
**Base measured:** `origin/main` @ `d6bc6643` (2026-10-31, #422 merged). Every `file:line` below was re-read by the planner on that commit. `claude plugin validate .claude/mods/asclexis-rsi` → `Validation passed` (exit 0); `claude plugin test .claude/mods/asclexis-rsi` → `29 pass, 0 fail` (exit 0, CLI 2.1.316), measured by a Haiku (medium) test runner in the planner worktree.
**Refresh Trigger:** any edit before these rows are built to `.claude/mods/asclexis-rsi/hooks/logic.ts`, `hooks/register.ts`, `hooks/rules.ts`, `replay/cases.ts`, `rsi.test.ts` or `README.md`, `.claude/workflows/rsi-loop.js` or `.claude/workflows/build-program.js`; a change to the rsi-log row format; an owner answer to RSI-HARNESS-GO or to a question below; a Claude Code CLI upgrade that changes a tool's error text.

Queue rows: [queue.md, "Planned 2026-10-31, RSI harness"](2026-10-15-build-program/queue.md#planned-2026-10-31-rsi-harness). Rules: [RUNBOOK](2026-10-15-build-program/RUNBOOK.md), [contracts](2026-10-15-build-program/contracts.md) §b-§d. Prior art: lane E [§2.27 RSI-LOG-STDERR](2026-10-15-build-program/lane-E-privacy-gates-ci.md#227-rsi-log-stderr--most-bash-failures-log-as-error_class-other-so-rsi-loop-cannot-cluster-them) (the same `classifyError` extension for Bash), [§2.25a RSI-CODEX-PROPOSER](2026-10-15-build-program/lane-E-privacy-gates-ci.md#225a-rsi-codex-proposer--codex-cli-as-a-second-independent-proposer-and-critic-in-rsi-loop-supersedes-rrsi-h2-sandbox) (the pure-function fixture pattern for `rsi-loop.js`). Run evidence: [2026-10-31-gpubox summary](../agentic/rsi-runs/2026-10-31-gpubox/summary.json); capstone: [RSI in development and application](../capstone-report/rsi-in-development-and-application.md).

**Rules that hold for every row here.**
- **Privacy (mod README `:17`, unchanged):** metadata only. A row, a summary or an archive never holds command text, tool output, prompts or paths. Every new `error_class`, stop class and PR state is a fixed literal chosen by code; free text is read only in memory to pick a literal and is never copied. Each row ships a "never echoes input" test with planted secrets, a path and a name.
- **RSI-4's human gate is unchanged** (`owner-decisions-2026-09-27.md:203`): no row here is agent-merged; the owner merges. Rows A and B edit the mod's own code (`logic.ts`, `register.ts`, `rsi.test.ts`), which is outside rsi-loop's ALLOW list (`rsi-loop.js:34-38`), so rsi-loop can never promote them: they are normal build-item rows. Rows C and D edit `.claude/workflows/*.js`, which rsi-loop also cannot promote.
- **No row widens what rsi-loop may change.** ALLOW (`rsi-loop.js:34-38`), DENY (`:39-54`), `gateDiff` (`:55-67`), `gateNumstat` (`:70-81`), the target enum (`:161`, `:88`) and the Codex critic (`:284-289`) are unchanged by every row. Row D relaxes only what the loop may *suggest*.
- **No error string is invented.** Each error shape below is either quoted from the repo or measured by the planner on this machine (method in Row A, Fact 3). Shapes the planner could not see are measured in Task 0, and a class is added only for a measured shape.
- **Test running:** Sonnet 5.5 implements; Haiku 5.5 (medium) runs `claude plugin validate` / `claude plugin test` and the node fixtures (MODEL-ROUTING-SONNET-IMPL). No pytest runs in any row (expected collected delta 0), so no row takes a pyslot.
- **The rsi-loop JS test fixture:** there is no committed fixture for `rsi-loop.js` on `main` (`grep -rln "mergeReflections\|gateNumstat" --exclude-dir=node_modules .` finds only `rsi-loop.js` and plan docs). The repo's pattern (lane E §2.17, §2.25, §2.25a `:898`) is: `sed -n '/^function NAME/,/^}/p'` the pure function into a scratch file under `/tmp/claude-1000`, then a node script asserting a fixture table; RED on `main` is the `sed` printing nothing. Rows C and D use that pattern, and their pure functions must therefore be self-contained top-level `function` declarations (as `mergeReflections`, `rsi-loop.js:84-87`). Whether to commit the fixture is drafted as OQ-RSI-FIXTURE.

**Order.** A before B (same `logic.ts`, `rsi.test.ts`, `README.md`). D after C (same `rsi-loop.js`; D's notes are the outlet for C's outcome clusters, whose fixes are almost always outside ALLOW). A/B and C/D are file-disjoint, so A ‖ C may run at once, then B ‖ D. None of the four touches a product file, so none takes a code slot.

---

## RSI-ERRCLASS-NONBASH — fixed, privacy-safe error classes for non-Bash tool failures

**Source:** owner row RSI-HARNESS-PLAN, item A. The 2026-10-31 run (`summary.json` clusters) mined Read `other` 10, StructuredOutput `other` 8, ExitPlanMode `other` 1 and TaskStop `other` 1, so rsi-loop could not reflect on them. Kind: **HARNESS, RSI** (mod code; no slot).

**Facts (re-read on `d6bc6643`).**
1. `classifyError(text)` (`.claude/mods/asclexis-rsi/hooks/logic.ts:67-84`) takes no tool argument and matches only Bash-shaped text (`Exit code`, `No such file or directory`, `^fatal: `, …); anything else is `other`. It is called once, at `hooks/register.ts:83` (`rule?.errorClass ?? (failed ? classifyError(text) : null)`), where `text` is `ran.text` (`:71`) and is `''` for a denied call.
2. Its second check is `/timed out|timeout/i` (`logic.ts:69`), ahead of every other shape. A non-Bash validation error that names a `timeout` parameter therefore logs as `timeout`. Across the archived rsi-logs (`docs/agentic/rsi-runs/*/rsi-log.jsonl`), the non-Bash failures are: Read `other` 10, StructuredOutput `other` 8, Monitor `timeout` 5, TaskStop `other` 2, Skill `other` 2, Edit `edit-no-match` 2, AskUserQuestion, Write and ExitPlanMode `other` 1 each. The 5 Monitor `timeout` rows are consistent with Fact 3's Monitor `InputValidationError` shape; Task 0 confirms or refutes that.
3. **Measured error shapes (planner, 2026-10-31).** The repo and the mod hold no non-Bash error text (`grep -rnoE` for each prefix below over `*.md *.ts *.js *.py`: no hit), and the engine's `claude-code.d.ts` is not on disk (it ships inside the CLI binary). So the planner counted the first line of every non-Bash `tool_result` with `is_error: true` in this machine's Claude Code transcripts from the last 14 days (`~/.claude/projects/**/*.jsonl`, 2793 files), with paths, quoted strings and digits replaced by `<P>`, `<Q>` and `N`; nothing else was printed. Shapes seen at least twice:

   | Tool | Count | First line (normalised) |
   |---|---|---|
   | Read | 85 | `File does not exist. Note: your current working directory is <P> …` |
   | Read | 5 | `File content (N tokens) exceeds maximum allowed tokens (N). Use offset and limit p…` |
   | Monitor, RemoteTrigger, StructuredOutput | 41, 6, 4 | `<tool_use_error>InputValidationError: <Tool> failed due to the following issue:` / `… was called with input that could not b…` |
   | (unknown tool name) | 23 + 5 | `<tool_use_error>Error: No such tool available: <name>. …` |
   | Edit, Write | 17, 8 | `<tool_use_error>File has not been read yet. Read it first before writing to it.` |
   | Edit | 5 | `<tool_use_error>String to replace not found in file.` (already `edit-no-match`, `logic.ts:70`) |
   | StructuredOutput | 5 + 2 + 2 | `Output does not match required schema: …` |
   | AskUserQuestion | 6 | `The user doesn't want to proceed with this tool use. The tool use was rejected …` |
   | Workflow | 6 | `<tool_use_error>scriptPath must be a script path this tool returned, or a file you can alr…` |
   | Workflow | 2 | `<tool_use_error>Workflow "<Q>" not found. Available: …` |
   | Grep | 6 | `Search failed — ripgrep rejected the pattern, glob, or file type without searching:` |
   | Skill | 3 | `<tool_use_error>Skill <name> cannot be used with Skill tool due to disable-mode…` |
   | TaskStop | 2, 2 | `<tool_use_error>No task found with ID: …` / `<tool_use_error>Task <id> is not running (status: completed)` |
   | Agent | 2 | `Concurrent subagent limit reached. You can run N subagents at once. …` |

   **Not seen, so not designed here:** an MCP tool error (no failing `mcp__*` call in the transcripts or the archived rsi-logs), an auto-mode or permission-rule denial (no tool_result carries one, and the archived rsi-logs have **0** `denied: true` rows without a `guard`: all 13 denials are `pkill-self`), and a Workflow whose script stopped (a build-item `STOPPED …` result is a normal, successful Workflow result, `build-item.js:123-205`; it is Row C's data, not an error class).
4. The transcripts are this machine's; the rsi-log rows were written on the GPU box. Task 0 re-measures on the machine that runs the build, by the same method, and the class list follows its table, not this one.
5. `session_log.py` (`.claude/hooks/session_log.py:26-58`) mirrors `classifyError` but logs only `Edit|Write|MultiEdit|NotebookEdit|Bash` (`.claude/settings.json:5`, `:13`), and the archived session-logs hold no non-Bash failure row. This row does not edit it (drafted OQ-RSI-SESSIONLOG for `edit-not-read`).
6. The replay harness (`rsi.test.ts:24-43`) asserts `deny`, `hint`, `guard` and `hint` only, never `error_class`; a case is `{id, rule, tool, input, error_text?, failed?, expect}` (`replay/cases.ts:2`, README `:35`).

**Design (metadata only; no new row field).**
- `classifyError(text: string, tool = ''): string`. `register.ts:83` passes `tool`. Existing callers and tests that pass only `text` behave exactly as today.
- New checks run **first**, before `Exit code 144`, so a tool-error envelope can never fall through to a Bash shape. Each is anchored to the measured start of the text, and the tool-specific ones also require the tool:

  | Class | Match (regex over `text`) | Tool |
  |---|---|---|
  | `input-validation` | `^<tool_use_error>InputValidationError: ` | any |
  | `no-such-tool` | `^<tool_use_error>Error: No such tool available: ` | any |
  | `edit-not-read` | `^<tool_use_error>File has not been read yet\. ` | `Edit`, `Write`, `MultiEdit`, `NotebookEdit` |
  | `read-not-found` | `^File does not exist\.` | `Read` |
  | `read-too-large` | `^File content \(\d+ tokens\) exceeds maximum allowed tokens \(\d+\)` | `Read` |
  | `schema-mismatch` | `^Output does not match required schema: ` | `StructuredOutput` |
  | `user-rejected` | `^The user doesn't want to proceed with this tool use\.` | any |
  | `workflow-not-found` | `^<tool_use_error>Workflow "[^"\n]*" not found\.` | `Workflow` |
  | `workflow-bad-script` | `^<tool_use_error>scriptPath must be a script path` | `Workflow` |
  | `skill-disabled` | `^<tool_use_error>Skill \S+ cannot be used with Skill tool` | `Skill` |
  | `task-not-found` | `^<tool_use_error>No task found with ID: ` | `TaskStop` |
  | `task-not-running` | `^<tool_use_error>Task \S+ is not running \(status: ` | `TaskStop` |
  | `subagent-limit` | `^Concurrent subagent limit reached\.` | `Agent` |
  | `grep-pattern-rejected` | `^Search failed — ripgrep rejected` | `Grep` |
  | `mcp-error`, `permission-denied-auto` | **Task 0 decides**: added only if Task 0 measures the shape (see below); otherwise not added and the gap is recorded in the PR body | `mcp__*`; any |

  Then the existing Bash checks, unchanged and in today's order (`logic.ts:68-83`). Every return is one of these literals, an existing literal, or `exit-` plus at most three digits.
- `README.md:17` (Privacy) lists the new classes. `README.md:35` documents the optional replay field below.
- **Replay cases.** The replay test gains one optional field, `error_class`: when a case has it, the case also asserts `row.error_class === c.error_class` (one added line in `rsi.test.ts` after `:41`). Class cases use `"rule": ""` and `"expect": "pass"`, so the "every rule has a positive and a negative case" test (`:44-50`) is unaffected. They run the full `register.ts` path, so they fail if `register.ts:83` does not pass `tool`.

**Tasks (test-first).**
0. **Task 0 (measure, read-only, Opus).** (a) Re-run Fact 3's count on the build machine (counts and normalised first lines only; nothing else printed or saved in the repo) and paste the table; drop any class above whose shape is not seen, and add none that is not seen. (b) **MCP:** in a scratch session with the mod loaded, call an MCP tool so that it fails (for example a serena call with an invalid argument), then read only that row's `tool` and `error_class` and the first line of the tool result; if the result starts with a fixed engine prefix, add `mcp-error` for `tool.startsWith('mcp__')`. (c) **Auto-mode / permission denial:** in a scratch session with the mod loaded and a deny rule for one harmless command in a scratch settings file, run it once; record whether a row appears at all, whether `denied` is true (that is, `ran.deny` reached the hook, `register.ts:69`) or `ok` is false with text, and the first line. If no row appears, the denial happens before the hook chain and the mod cannot see it: no class is added, and the PR body says so. If the text has a fixed engine prefix, add `permission-denied-auto`. Stop and tell L0 if either measurement needs a change outside the file list.
1. **RED.** New `describe('classifyError, non-Bash')` in `rsi.test.ts`:
   - `fixed classes for measured tool errors`: for each class kept by Task 0, the measured first line (with neutral placeholders, for example `File does not exist. Note: your current working directory is /x.`) and its tool → that class. RED: `other` today (measured on a scratch copy of the function first).
   - `tool-scoped classes need the tool`: `File does not exist.` with tool `Bash` → not `read-not-found` (`other`); `Output does not match required schema: x` with tool `Read` → `other`.
   - `tool envelope wins over Bash shapes`: `<tool_use_error>InputValidationError: Monitor failed due to the following issue: timeout_ms …` with tool `Monitor` → `input-validation`, not `timeout`. RED: `timeout` today.
   - `never echoes input, non-Bash`: planted `SECRET-123`, `/home/x/patient.pdf` and `Jane` inside each measured shape; every result matches a new union regex of all literals and contains no planted string. The existing `never echoes input` test (`:73-92`) is not edited.
   - logger: `Read row classifies without the text`: a failing Read call (`file_path: '/home/x/patient.pdf'`) whose result is `File does not exist. Note: your current working directory is /home/x/Jane.` → the row's `error_class` is `read-not-found`, and the raw log contains neither `patient` nor `Jane`.
   - replay: one class case per kept class in `replay/cases.ts` (for example `{"id": "class-read-too-large", "rule": "", "tool": "Read", "input": {"file_path": "/x"}, "error_text": "File content (30000 tokens) exceeds maximum allowed tokens (25000). Use offset and limit parameters.", "error_class": "read-too-large", "expect": "pass"}`), plus one negative: a Bash case whose output contains `File does not exist.` with `"error_class": "other"`.
2. **GREEN.** `classifyError` as designed; `register.ts:83` passes `tool`; the replay assertion line; README `:17` and `:35`.
3. **Checks.** `claude plugin validate .claude/mods/asclexis-rsi` and `claude plugin test .claude/mods/asclexis-rsi`, RED run pasted first; `git diff origin/main -- .claude/mods/asclexis-rsi/hooks/rules.ts .claude/hooks/session_log.py .claude/workflows/` empty.

**Acceptance:** `Validation passed`; `claude plugin test` → `N pass, 0 fail` with N = 29 + 5 new tests + the number of class replay cases (Task 0 states N before GREEN), RED pasted; every existing test unchanged and green; the CI `rsi-replay` job (`.github/workflows/ci.yml:335-338`) green. Est 1.5 h.

**Files:** `.claude/mods/asclexis-rsi/hooks/logic.ts` (`classifyError` only, `:61-84`), `.claude/mods/asclexis-rsi/hooks/register.ts` (`:83`, one argument), `.claude/mods/asclexis-rsi/rsi.test.ts` (one line after `:41`; new describe; one logger test), `.claude/mods/asclexis-rsi/replay/cases.ts` (additions only), `.claude/mods/asclexis-rsi/README.md` (`:17`, `:35`).

**depends_on:** —. **Never beside:** RSI-RULE-TOOLFIELD (same files; this row goes first), any open rsi-loop RSI PR that edits `replay/cases.ts` (Task 0 checks `gh pr list --search "rsi: in:title" --state open` and `gh pr diff --name-only`). **Owner gates:** RSI-HARNESS-GO (open); owner merges (RSI-4). **Stops:** a shape that cannot be matched without reading past its fixed prefix; any need to log text, a path or a new row field.

---

## RSI-RULE-TOOLFIELD — rules can match one fixed input field per tool (Workflow, Skill, Agent, MCP server)

**Source:** owner row RSI-HARNESS-PLAN, item B. Kind: **HARNESS, RSI** (mod code; no slot).

**Facts (re-read on `d6bc6643`).**
1. `cmdOf` (`logic.ts:30-33`) returns `input.command` for Bash and `''` for every other tool. `checkBefore` (`:36-39`) tests `r.match` against it, and `checkAfter` (`:42-59`) tests `r.command` against it. So a `before` rule for any non-Bash tool can only match `''`, and an `after` rule's `command` refinement is useless off Bash.
2. A rule matches its tool by exact name (`r.tool === tool`, `:38`, `:53`), so there is no way to target one MCP server.
3. **Measured input keys** (planner, same 14-day transcripts as Row A Fact 3, keys only): Workflow `{name, args}` 246 calls, `{scriptPath, args}` 348, `{scriptPath, args, resumeFromRunId}` 26; Skill `{skill}` 36, `{skill, args}` 11. The Agent tool's schema names `subagent_type`, `model`, `prompt`, `description` (this session's tool list). MCP tools are named `mcp__<server>__<tool>`; the rsi-log already records the full name (`mcp__serena__initial_instructions`, 2026-10-31 `summary.json` metrics).
4. Fail modes (`register.ts:55-59`, `:94-96`): if anything before `next` throws, `.catch` denies the call (deny fails closed); everything after `next` is in its own `try/catch` (hints fail open). `fingerprint` (`logic.ts:23-28`) hashes the whole input in memory and is never logged.
5. `isTestCommand` (`:86`) uses `cmdOf` and must stay Bash-only.

**Design.**
- New `fieldOf(tool, input): string` in `logic.ts`, beside `cmdOf` (which stays, for `isTestCommand`). It returns exactly one fixed field, only when it is a string of at most 200 characters, else `''`:

  | Tool | Field | Notes |
  |---|---|---|
  | `Bash` | `command` | as today |
  | `Workflow` | `name` if a string, else the basename of `scriptPath` without `.js` (`[A-Za-z0-9._-]+` only, else `''`) | never `args`, never `resumeFromRunId` |
  | `Skill` | `skill` | never `args` |
  | `Agent` | `subagent_type` | never `prompt`, `description` or `model` |
  | `mcp__<server>__<tool>` | `<server>` (from the tool **name**, not the input) | never any input value |
  | any other tool | `''` | |

  Free-text fields (`prompt`, `args`, `description`, `content`, `old_string` …) are never read. The value lives in memory only, like `cmdOf` today; nothing new is logged.
- `checkBefore` and `checkAfter` use `fieldOf` where they use `cmdOf` today, so `before.match` and `after.command` test that field. No new `Rule` key.
- Tool match: `r.tool === tool`, or `r.tool === 'mcp__*'` and `tool.startsWith('mcp__')`. A rule is still exactly one tool or the MCP family; there is no other wildcard.
- `rules.ts` header comment (`:1-6`) says per tool which field `match` (before) and `command` (after) test, so rsi-loop proposers (who read the Rule type, `rsi-loop.js:300`) see it; README `:10` likewise. No seed rule is added, so `RULES` and `replay/cases.ts` are unchanged.
- Fail modes unchanged: `fieldOf` cannot throw on any input shape (null, non-object, non-string fields), and a deny rule on these tools still goes through the `.catch` that holds the call if the guard throws.

**Tasks (test-first).** New `describe('per-tool field')` in `rsi.test.ts`, using `checkBefore` / `checkAfter` with a test-local rule array (both already take `rules` as a parameter, `:36`, `:47`), plus two end-to-end tests through `$.tool.call`:
1. `fieldOf table`: each row of the table above, including `scriptPath: '/a/b/build-item.js'` → `build-item`; a `scriptPath` basename with a space → `''`; a 201-character `skill` → `''`; `null`, `[]`, `{skill: 3}` → `''`. RED: `fieldOf` does not exist.
2. `before deny matches the fixed field`: rule `{tool: 'Workflow', when: 'before', match: '^build-item$', action: 'deny'}` → denies `{name: 'build-item'}`; passes `{name: 'build-wave'}`. RED: never denies today.
3. `never matches free text`: the same rule against `{name: 'build-wave', args: {id: 'build-item'}}` → passes; an Agent rule matching `^Explore$` against `{subagent_type: 'general-purpose', prompt: 'Explore'}` → passes; a Skill rule against `{skill: 'tdd', args: 'build-item'}` → passes.
4. `after hint refines by field`: rule `{tool: 'Skill', when: 'after', command: '^tdd$', match: 'x', action: 'hint'}` fires for `{skill: 'tdd'}` with failed text `x`, not for `{skill: 'brainstorming'}`.
5. `mcp family`: rule `{tool: 'mcp__*', when: 'before', match: '^serena$'}` denies tool `mcp__serena__find_symbol`, passes `mcp__other__x`, and passes Bash with command `serena`.
6. `deny still fails closed`: `checkBefore('Workflow', {name: 'x'}, [ruleWithMatch('(')])` throws, so in the hook it throws before `next` and the `.catch` (`register.ts:94-96`) holds the call; `RULES` cannot be injected into `register.ts`, so the end-to-end half is pinned by reading (`register.ts:62` runs before `next`) and stated in the PR body.
7. `hint still fails open`: end-to-end, a Skill call whose bottom returns `isError` with text → the call result is returned unchanged when no rule matches, and the row has `hint: null`.

**Acceptance:** `claude plugin test` → `N pass, 0 fail` (N = RSI-ERRCLASS-NONBASH's merged count + 7), RED pasted; every existing replay case and test unchanged and green; `git diff origin/main -- .claude/mods/asclexis-rsi/replay/cases.ts .claude/workflows/` empty; in `rules.ts` only the header comment changes (`git diff` shows no line inside `RULES`). Est 1.5 h.

**Files:** `.claude/mods/asclexis-rsi/hooks/logic.ts` (`fieldOf`; `checkBefore` / `checkAfter` `:36-59`), `.claude/mods/asclexis-rsi/hooks/rules.ts` (header comment `:1-6` only), `.claude/mods/asclexis-rsi/rsi.test.ts` (new describe), `.claude/mods/asclexis-rsi/README.md` (`:10`, `:35`).

**depends_on:** RSI-ERRCLASS-NONBASH merged. **Never beside:** RSI-ERRCLASS-NONBASH; an open rsi-loop RSI PR that edits `rules.ts` (header comment hunk; rebase after it). **Owner gates:** RSI-HARNESS-GO (open); owner merges (RSI-4). **Stops:** a needed field that is free text; any change that would log the field.

---

## RSI-MINE-OUTCOMES — Mine reads workflow outcomes as fixed categories

**Source:** owner row RSI-HARNESS-PLAN, item C. On 2026-10-31 the TOAST-SHELL build-item stopped at its resume identity check because #410 kept a stale `[claim:claude]` title (the L0 retitle was refused by auto mode), and RAPIDOCR-BUNDLE stopped on a file-list gap (#421). Neither reached rsi-loop, which reads only the rsi-log, the session-log and PR reviews (`rsi-loop.js:217-224`). Kind: **HARNESS, RSI** (workflow scripts; no slot).

**Facts (re-read on `d6bc6643`).**
1. build-item returns a string on every stop: `STOPPED <id>: not found in …` (`build-item.js:123`), `… is owner or model-machine work` (`:130`), `… runtime is …` (`:133`), `STOPPED <id> at Task 0: <stop_reasons>` (`:168-176`; the resume identity checks are in the Task 0 prompt, `:150`), `… unexpected worktree … or branch …` (`:190`), `STOPPED <id> (PR #n, retitled [blocked:claude]): <why>` (`block`, `:195-206`), `ESCALATED <id> after N REVISE rounds` (`:349`); a finished item's first line is `<PR URL> READY | DRAFT (why) | FAILED | BLOCKED` (`:363`). build-program wraps a thrown error as `ERROR <id>: …` (`build-program.js:103`, `:112`). The `<stop_reasons>` / `<why>` tails are free text.
2. build-program already triages each result into a fixed `kind` enum, `done | plan_gap | owner_gate | env | review | other` (`TRIAGE_SCHEMA`, `build-program.js:28-37`, enum `:31`), and pushes `{wave, id, kind, summary, rerun}` to `report` (`:118`). It then calls `workflow('rsi-loop', { run_id })` (`:182`) and passes nothing else.
3. Workflow scripts have no file access ("No filesystem or Node.js API access", lane E §2.25 item 1b). So rsi-loop's JS cannot read the workflow journal; only an agent can, and whether a past run's result is readable on disk is not known.
4. Draft-PR state lives in the title prefix (RUNBOOK §3, §8): `[claim:<rt>]`, `[claim:<rt>:noslot]`, `[blocked:<rt>]`, `[escalated:<rt>]`, then `<ID> <slug>`.
5. Mine already reads PRs with `gh` (`rsi-loop.js:220`) and returns free-text `evidence` that the schema says must be metadata only (`:140`).

**Category sets (fixed literals; nothing else is ever written).**
- `stop_class` (one per build-item result): `done-ready`, `done-draft`, `failed`, `blocked-after-verify`, `not-found`, `owner-or-model-machine`, `runtime-mismatch`, `resume-identity`, `file-list-gap`, `lock-or-slot`, `plan-gap`, `owner-gate`, `task0-other`, `bad-worktree-shape`, `stopped-after-claim`, `escalated`, `error`, `unknown`. The prefix classes come from the fixed prefixes in Fact 1. `resume-identity`, `file-list-gap`, `lock-or-slot`, `plan-gap` and `owner-gate` subclass the free-text Task 0 / `block` tail by regex in memory, like `classifyError`; Task 0 fits those regexes to the real stop texts of #410 and #421 (read on the PRs' "blocked: tell L0" comments) and pastes the table. Anything unmatched is `task0-other` or `stopped-after-claim`.
- `pr_state` (one per PR whose title has a RUNBOOK §3 prefix, updated in the window): `claim-open`, `claim-noslot-open`, `claim-stale` (open, `[claim:` title, no commit or comment for 24 h, or a `[claim:` title on a closed PR), `blocked-open`, `escalated-open`, `ready-open` (not draft), `merged`, `closed-unmerged`.
- `kind` (build-program only): the existing triage enum (`build-program.js:31`).
- Identifiers kept: the queue id only if it matches `^[A-Z0-9][A-Z0-9-]{0,39}$`, and the PR number. Never the slug, the title, a stop reason, a comment or a branch name.

**Design.**
- **build-program.js:** a new self-contained `function outcomeClass(result)` returns a `stop_class` from the result string (non-strings → `unknown`). At `:182` it passes `outcomes: report.filter(r => r.kind not in {plan, merge}).map(r => ({ id, kind, stop_class }))` to rsi-loop, with `stop_class` from the item's original result (and the rerun's, as a second entry, when there is one).
- **rsi-loop.js:** a new self-contained `function validOutcomes(raw, kinds, classes, states)` keeps only entries whose every field is in its enum (ids by the regex above) and drops the rest with a count note. Standalone runs (no `outcomes` arg; most build-items run top-level today) get outcomes from Mine: `MINE_SCHEMA` (`:131-154`) gains `outcomes: [{id, pr, stop_class, pr_state}]` with `enum` on both classes, and the Mine prompt (`:217-224`) gains one step: list PRs with a RUNBOOK §3 title prefix updated since the window start (`gh pr list --state all --search "updated:>=<since>" --json number,title,isDraft,state,updatedAt`), map each title prefix to `pr_state`, and for `blocked-open`/`escalated-open` read only the latest "blocked: tell L0" or "escalation: owner" comment to choose a `stop_class` from the enum; never copy the title slug or comment text. JS passes both sources through `validOutcomes`, so a free-text value from an agent is dropped, not stored.
- Outcome counts become `outcome_clusters` (`{source: 'build-item' | 'pr-title', class, count, ids}`), kept apart from the tool clusters, so the top-3 tool clusters that Reflect and Propose use (`:229-235`) are unchanged. They go into the Reflect prompt as context, into `summary` (`:356-362`) and into every early return (`:227`, `:232`, `:278`). Without RSI-OWNER-NOTES they are reported, not acted on.
- **Journal:** Task 0 measures whether an agent can read a finished workflow run's result from disk (for example by `wf_` run id). If it can, the plan delta adds it as a third source through the same `validOutcomes`; if not, the PR body says so. This row does not depend on it.

**Tasks (test-first).**
0. **Task 0 (Opus).** Fit the subclass regexes to the stop texts on #410 and #421 and to each build-item stop shape in Fact 1, and paste the input → class table (texts shown in the PR body only as `<prefix>…`, never the whole reason). Measure the journal question.
1. **RED (fixture).** `sed -n '/^function outcomeClass/,/^}/p' .claude/workflows/build-program.js` and `sed -n '/^function validOutcomes/,/^}/p' .claude/workflows/rsi-loop.js` into scratch files; a node script asserts: (1) each Fact 1 shape → its class, including `STOPPED X at Task 0: resume of PR #410: title is not [blocked:claude]` → `resume-identity` (Task 0's real wording) and the #421 stop → `file-list-gap`; (2) `https://github.com/o/r/pull/1 READY` → `done-ready`; (3) a planted `STOPPED X (PR #1, retitled [blocked:claude]): SECRET-123 /home/x/patient.pdf Jane` → a literal in the enum, and the output contains none of the planted strings; (4) `validOutcomes` keeps `{id: 'TOAST-SHELL', kind: 'review', stop_class: 'resume-identity'}`, drops `{stop_class: 'identity check failed'}`, drops `{id: 'toast shell'}`, drops `{pr_state: 'claim'}`; (5) a non-array → `[]` with a note. RED on `main`: both `sed`s print nothing.
2. **GREEN.** The two functions, the `:182` arg, the schema field, the one Mine step, `outcome_clusters` in `summary` and the early returns.
3. **Dry run.** `rsi-loop` with `{dry_run: true, run_id: '<date>-outcomes-dry', since: '2026-10-30'}`; paste `outcome_clusters` (expected to include `pr-title/claim-stale` or `build-item/resume-identity` for TOAST-SHELL #410 and `file-list-gap` for RAPIDOCR-BUNDLE #421, unless those PRs changed since); `grep -ciE 'token|secret|password|api[_-]?key|bearer'` on the dry-run result prints 0 except the `tokens_per_item` key (rsi-runs README step 4).

**Acceptance:** fixture `outcomes ok (N)` pasted with its RED; dry-run result pasted; ALLOW, DENY, `gateDiff`, `gateNumstat`, `mergeReflections` and the target enum show no diff (`git diff origin/main -- .claude/workflows/rsi-loop.js` touches only `MINE_SCHEMA`, the Mine prompt, the new function, `summary` and the three early returns); `claude plugin test` unchanged. Est 3 h.

**Files:** `.claude/workflows/rsi-loop.js` (`MINE_SCHEMA` `:131-154`; Mine prompt `:217-224`; new `validOutcomes` after `:128`; `summary` `:356-362`; returns `:227`, `:232`, `:278`, `:373-380`), `.claude/workflows/build-program.js` (new `outcomeClass`; `:182` arg), `docs/agentic/rsi-runs/README.md` (one line: `summary.json` carries `outcome_clusters`, fixed classes only).

**depends_on:** —. **Never beside:** RSI-OWNER-NOTES (same `rsi-loop.js`; this row goes first); any other `.claude/workflows/rsi-loop.js` or `build-program.js` PR; a running `build-program` or `rsi-loop` workflow on the box while the PR is tested (the dry run reads the live logs). **Owner gates:** RSI-HARNESS-GO (open); owner merges (RSI-4). **Stops:** a needed field that is free text; any write of a title, slug or stop reason; any change to the gate functions.

---

## RSI-OWNER-NOTES — Reflect may emit owner notes for targets outside ALLOW

**Source:** owner row RSI-HARNESS-PLAN, item D. Every rsi-loop run since 2026-10-26 ended "nothing worth proposing" (`docs/agentic/rsi-runs/README.md` Runs table), partly because the smallest fix for a cluster sat outside ALLOW (a skill, a workflow prompt, CLAUDE.md), where the loop is told to set `worth_proposing=false` (`rsi-loop.js:244`). Kind: **HARNESS, RSI** (workflow script; no slot).

**This relaxes only what the loop may *suggest*.** Owner notes are text in `summary.json` and the run archive for the owner and L0 to read. They are never a PR, never a commit, never an edit and never passed to Propose, Gate or Publish's PR step. ALLOW, DENY and every gate stay exactly as they are for PRs.

**Facts (re-read on `d6bc6643`).**
1. `REFLECT_SCHEMA` (`:155-166`) holds only `reflections`, each with `target_file` limited to the three ALLOW paths (`:161`). `mergeReflections` (`:87-120`) and `toPropose` (`:275`) feed Propose from `reflections` only.
2. The common outcome returns before Publish: `:278` ("nothing worth proposing") returns `reflections` and `codex_reflections` in the workflow result and writes no `summary-<run_id>.json`; L0 archives that result as `summary.json` (rsi-runs README `:31`, 2026-10-31 row). Publish writes `summary` (`:356-362`) only when there are candidates (`:365`).
3. Agent free text that reaches the archive is already filtered once: the Codex finding is cut to printable ASCII and 160 characters (`:337-338`).

**Design.**
- `REFLECT_SCHEMA` gains `owner_notes: [{cluster, target_kind, target, note}]`, `target_kind` enum `skill | workflow | claude-md | agent-md | runbook`. The Reflect prompt (`:243-246`) gains one sentence: when the smallest fix is outside the three allowed files, you may add at most one owner note per cluster naming the file and the change; it is advice for the owner, never implemented by this run.
- New self-contained `function ownerNotes(raw, allow, deny, max)` keeps a note only if: `target_kind` is in the enum; `target` matches that kind's pattern (`skill`: `^(\.claude/skills|skills)/[a-z0-9-]+/SKILL\.md$`; `workflow`: `^\.claude/workflows/[a-z0-9-]+\.js$`; `claude-md`: `^(CLAUDE|\.\./CLAUDE)\.md$` → stored as `CLAUDE.md`; `agent-md`: `^AGENT\.md$`; `runbook`: `^docs/plans/2026-10-15-build-program/RUNBOOK\.md$`); `target` is not in ALLOW (those go through the normal proposal path); `target` matches no DENY pattern (`:39-54`; see OQ-RSI-NOTES-DENY); `cluster` is one of this run's tool or outcome cluster keys. The kept `note` is printable ASCII, newlines removed, cut to 300 characters; at most `max` = 5 notes per run. Everything else is dropped with a count note. Only Claude's Reflect may emit notes; Codex proposer output is unchanged (`CODEX_PROPOSE_PROMPT`, `:240`).
- `owner_notes` is added to `summary` (`:356-362`, so Publish writes it when it runs) and to the `:278` return (so the archived workflow result carries it). The Publish PR body (`:367`) is not changed, so a note never appears in an RSI PR.
- `docs/agentic/rsi-runs/README.md`: `summary.json` may carry `owner_notes`; L0 reads them after each run and turns any it agrees with into a queue bullet. The capstone section ([§2 Track 1](../capstone-report/rsi-in-development-and-application.md#2-track-1-development-harness)) gets one sentence when the first note is archived, by L0, not by this row.

**Tasks (test-first).**
1. **RED (fixture).** `sed -n '/^function ownerNotes/,/^}/p'` into a scratch file; a node script asserts: (1) `{target_kind: 'skill', target: '.claude/skills/build-item/SKILL.md', cluster: 'Bash/no-such-file', note: 'x'}` kept; (2) target `.claude/mods/asclexis-rsi/hooks/rules.ts` dropped (ALLOW); (3) targets `scripts/pyslot.sh`, `src/backend/modules/redaction.py`, `.github/workflows/ci.yml` dropped (DENY); (4) `target_kind: 'product'` dropped; (5) a `workflow` kind with target `.claude/workflows/../x.js` dropped; (6) a 1000-character note with a newline and a non-ASCII character → one line, ASCII, 300 characters; (7) 7 valid notes → 5; (8) unknown cluster dropped; (9) non-array → `[]`. RED on `main`: the `sed` prints nothing.
2. **Isolation check (grep, pasted).** `grep -n "owner_notes" .claude/workflows/rsi-loop.js` lists only the schema, `ownerNotes`, the Reflect sentence, `summary` and the `:278` return: no line in the Propose prompt (`:295-304`), the Gate (`:308-346`) or the PR step of Publish (`:367`).
3. **GREEN**, then a dry run (`dry_run: true`): paste `owner_notes` from the result (may be empty) and the secrets grep as in RSI-MINE-OUTCOMES.

**Acceptance:** fixture `notes ok (9)` with its RED; isolation grep pasted; dry-run result pasted; `git diff origin/main` on `rsi-loop.js` shows ALLOW, DENY, `gateDiff`, `gateNumstat`, `mergeReflections`, `target_file` enum, `CODEX_*` prompts and the Publish PR text unchanged. Est 2 h.

**Files:** `.claude/workflows/rsi-loop.js` (`REFLECT_SCHEMA` `:155-166`; Reflect prompt `:243-246`; new `ownerNotes`; `summary` `:356-362`; return `:278`), `docs/agentic/rsi-runs/README.md` (one line on `owner_notes`).

**depends_on:** RSI-MINE-OUTCOMES merged (shared file; and notes on outcome clusters need them). It can be built without C only by an L0 queue edit that drops the outcome-cluster keys from rule (8). **Never beside:** RSI-MINE-OUTCOMES; any other `rsi-loop.js` PR. **Owner gates:** RSI-HARNESS-GO (open); OQ-RSI-NOTES-DENY (drafted; the recommended answer is the design above); owner merges (RSI-4). **Stops:** any path by which a note could reach a worktree, a commit or a PR.

---

## Drafted owner questions (not asked)

- **RSI-HARNESS-GO** (one per row: A, B, C, D). "Build row <id> as planned in `docs/plans/2026-10-31-rsi-harness-plan.md`?" Options: (a) yes, as planned (Recommended); (b) not now. No row is claimed before its yes is recorded on `origin/main`.
- **OQ-RSI-NOTES-DENY** (Row D). "Should an owner note whose target is a DENY path (tests, `scripts/`, `.github/`, thresholds, ask-first files) be dropped?" Options: (a) drop it, so the loop never suggests edits there (Recommended: conservative, matches the PR gate); (b) keep it as a note, marked `deny:<reason>`, since a note edits nothing.
- **OQ-RSI-SESSIONLOG** (follow-up to Row A, optional). "`session_log.py` mirrors `classifyError` for Edit/Write/Bash. Add `edit-not-read` there too, as its own row (pytest, `test_session_log_hook.py`)?" Options: (a) yes, own row after Row A (Recommended); (b) no, the mod's log is enough.
- **OQ-RSI-FIXTURE** (Rows C and D, optional). "Commit the node fixture for the `rsi-loop.js` / `build-program.js` pure functions, run in CI, instead of the scratch `sed` + node pattern?" Options: (a) keep the scratch pattern used since §2.17 (Recommended: no new CI job); (b) commit it as `.claude/workflows/tests/*.mjs` with a CI step (a new row).
