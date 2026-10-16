export const meta = {
  name: 'build-item',
  description: 'Run one build-program queue item: explore, Task 0 + claim, implement test-first, haiku test run, review (max 3), verify + PR',
  whenToUse: 'L0 runs one queue item from docs/plans/2026-10-15-build-program/queue.md; args {id: "E-1"}. At most 2 at once.',
  phases: [
    { title: 'Explore', detail: 'haiku reads the queue row, lane doc, plan', model: 'haiku' },
    { title: 'Plan check', detail: 'opus runs Task 0 and claims the item on GitHub', model: 'opus' },
    { title: 'Implement', detail: 'sonnet implements test-first in the claimed worktree', model: 'sonnet' },
    { title: 'Test', detail: 'haiku runs the test suites and acceptance commands, never edits', model: 'haiku' },
    { title: 'Review', detail: 'opus review, at most 3 rounds', model: 'opus' },
    { title: 'Verify', detail: 'opus measured acceptance, PR body, release slot', model: 'opus' },
  ],
}

// Runbook: docs/plans/2026-10-15-build-program/RUNBOOK.md. This script only sequences it.
const STYLE = 'Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)'
const RUNBOOK = 'docs/plans/2026-10-15-build-program/RUNBOOK.md'
const QUEUE = 'docs/plans/2026-10-15-build-program/queue.md'
const MAX_ROUNDS = 3

const ID = args && typeof args.id === 'string' ? args.id.trim() : ''
// The id ends up in shell commands and branch names: accept queue-ID shape only.
if (!/^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$/.test(ID)) {
  throw new Error(`args.id must be a queue ID like "E-1" or "RAG-RUNTIME-500"; got ${JSON.stringify(args)}`)
}

const EXPLORE_SCHEMA = {
  type: 'object',
  properties: {
    found: { type: 'boolean' },
    repo_root: { type: 'string' },
    kind: { type: 'string' },
    runtime: { type: 'string' },
    depends_on: { type: 'string' },
    gates: { type: 'string' },
    ask_first: { type: 'string' },
    files: { type: 'array', items: { type: 'string' } },
    spec_paths: { type: 'array', items: { type: 'string' } },
    acceptance_commands: { type: 'array', items: { type: 'string' } },
    contracts: { type: 'array', items: { type: 'string' } },
    architectural: { type: 'boolean' },
    security_sensitive: { type: 'boolean' },
    notes: { type: 'string' },
  },
  required: ['found', 'repo_root', 'kind', 'runtime', 'files', 'spec_paths', 'acceptance_commands', 'architectural', 'security_sensitive'],
}

const PLANCHECK_SCHEMA = {
  type: 'object',
  properties: {
    go: { type: 'boolean' },
    stop_reasons: { type: 'array', items: { type: 'string' } },
    worktree: { type: 'string' },
    branch: { type: 'string' },
    pr_number: { type: 'integer' },
    start_count: { type: 'string' },
    skipped_tasks: { type: 'array', items: { type: 'string' } },
    gates_quoted: { type: 'array', items: { type: 'string' } },
    brief: { type: 'string' },
  },
  required: ['go', 'stop_reasons', 'gates_quoted', 'skipped_tasks'],
}

const IMPL_SCHEMA = {
  type: 'object',
  properties: {
    status: { type: 'string', enum: ['done', 'stopped'] },
    stop_reason: { type: 'string' },
    commits: { type: 'array', items: { type: 'string' } },
    files_changed: { type: 'array', items: { type: 'string' } },
    red_green_output: { type: 'string' },
    report: { type: 'string' },
  },
  required: ['status', 'files_changed', 'commits', 'red_green_output', 'report'],
}

const TEST_SCHEMA = {
  type: 'object',
  properties: {
    all_passed: { type: 'boolean' },
    collected_line: { type: 'string' },
    runs: { type: 'array', items: { type: 'object', properties: {
      command: { type: 'string' }, exit_code: { type: 'integer' }, output_tail: { type: 'string' },
    }, required: ['command', 'exit_code', 'output_tail'] } },
    failures: { type: 'array', items: { type: 'string' } },
  },
  required: ['all_passed', 'runs', 'failures'],
}

const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['PASS', 'REVISE'] },
    findings: { type: 'array', items: { type: 'string' } },
  },
  required: ['verdict', 'findings'],
}

// ---------------------------------------------------------------------------
phase('Explore')
const spec = await agent(
  `Read-only. Find build-program queue item ${ID}.
1. Run \`git rev-parse --show-toplevel\` from your cwd; that is repo_root. Run \`git -C <repo_root> fetch origin\`.
2. Read its row in <repo_root>/${QUEUE} (read the file at origin/main if the working tree lacks it: \`git show origin/main:${QUEUE}\`). found=false if no row has id ${ID}.
3. From the row, copy kind, runtime, depends_on, owner gates, ask-first, and the full file list (expand be/ = src/backend/, fe/ = src/frontend/src/).
4. Read the lane-doc section for ${ID} (docs/plans/2026-10-15-build-program/lane-*.md) and the plan file it names. spec_paths = those paths with section anchors or line ranges.
5. acceptance_commands = the plan's measured acceptance commands, verbatim.
6. contracts = the I-n rows in contracts.md §a where ${ID} is provider or consumer.
7. architectural = true if docs/agentic/orchestration.md §5 lists the item's phase or the row says "+ Codex". security_sensitive = true if the files touch redaction, auth, encryption, export, logging or the external runner.
Do not edit anything.
${STYLE}`,
  { label: `explore ${ID}`, phase: 'Explore', model: 'haiku', effort: 'low', schema: EXPLORE_SCHEMA },
)
if (!spec || !spec.found) {
  return `STOPPED ${ID}: not found in ${QUEUE}`
}

const runtime = (spec.runtime || '').toLowerCase()
const kind = (spec.kind || '').toUpperCase()
if (runtime.includes('model machine') || kind.startsWith('OWNER')) {
  return `STOPPED ${ID}: ${spec.kind} / ${spec.runtime} is owner or model-machine work (${RUNBOOK} §9 rule 8)`
}
if (!(runtime.startsWith('claude') || runtime.startsWith('any'))) {
  return `STOPPED ${ID}: runtime is "${spec.runtime}"; Claude Code takes only claude/any rows unless L0 edits the queue row (${RUNBOOK} §1 rule 1)`
}
const noSlot = kind.startsWith('DOCS') || kind.includes('NO SLOT')
const specText = JSON.stringify(spec, null, 2)

// ---------------------------------------------------------------------------
phase('Plan check')
const plan = await agent(
  `You are L1 (Opus) for build-program item ${ID}. Follow ${RUNBOOK} exactly; repo_root = ${spec.repo_root}.
Item spec (from a Haiku explorer; verify it, it is a lead not a finding):
${specText}

1. Read the spec paths yourself and check the explorer's file list and gates against the queue row.
2. Claim the item per RUNBOOK §3 with RT=claude${noSlot ? ' and NOSLOT=":noslot"' : ''}. Pick TYPE and a short SLUG. Run the lock check and the slot check first. If either fails, do not claim: go=false.
3. Run RUNBOOK §4 Task 0 checks 1-7 in the new worktree. Quote each owner-decisions line you rely on, verbatim. Never infer an approval. A gate that is only "merge only" does not stop work; tasks the row marks blocked go to skipped_tasks.
4. If a check fails: post the command and output as a comment on your draft PR, keep it draft, go=false.
5. brief = an L2 implementer brief: worktree, branch, plan path + task list to execute (minus skipped tasks), exact file list, ask-first files with the signed gate naming each allowed edit (or "none — do not edit"), contracts to honour, RED-first rule, commit plan.
Do not edit product code yourself.
${STYLE}`,
  { label: `task0+claim ${ID}`, phase: 'Plan check', model: 'opus', effort: 'high', schema: PLANCHECK_SCHEMA },
)
if (!plan || !plan.go) {
  const why = `Task 0: ${(plan && plan.stop_reasons || ['plan-check agent returned nothing']).join('; ')}`
  if (plan && plan.pr_number) {
    await agent(
      `Build-program item ${ID} failed Task 0 after claiming draft PR #${plan.pr_number}. Change nothing else: gh pr edit ${plan.pr_number} --title "[blocked:claude] ${ID} <keep the current slug>" (keep it draft). ${STYLE}`,
      { label: `block ${ID}`, phase: 'Plan check', model: 'opus', effort: 'low' },
    )
  }
  return `STOPPED ${ID} at ${why}${plan && plan.pr_number ? ` (PR #${plan.pr_number}, retitled [blocked:claude])` : ''}`
}
log(`${ID}: claimed PR #${plan.pr_number} on ${plan.branch}`)

const where = `worktree ${plan.worktree}, branch ${plan.branch}, draft PR #${plan.pr_number}`

// Any stop after the claim retitles the PR to [blocked:claude] so it stops holding a code slot (RUNBOOK §3 Release, §8).
const block = async (why) => {
  await agent(
    `Build-program item ${ID} stopped: ${where}. Change nothing else.
1. gh pr edit ${plan.pr_number} --title "[blocked:claude] ${ID} <keep the current slug>" (keep it draft).
2. gh pr comment ${plan.pr_number} --body-file <tmpfile under /tmp/claude-1000> with heading "blocked: tell L0" and this reason verbatim:
${why}
${STYLE}`,
    { label: `block ${ID}`, phase: 'Review', model: 'opus', effort: 'low' },
  )
  return `STOPPED ${ID} (PR #${plan.pr_number}, retitled [blocked:claude]): ${why}`
}

// ---------------------------------------------------------------------------
const implement = (findings, round) => agent(
  `You are the L2 implementer (Sonnet) for build-program item ${ID}: ${where}. Work only in that worktree.
Brief from L1:
${plan.brief}

${findings
    ? `Review round ${round}/${MAX_ROUNDS} returned REVISE. Findings:\n${findings.join('\n')}\nVerify each against the code before changing anything (receiving-code-review). Fix BLOCKER and MAJOR; push back with evidence on a finding that is wrong.`
    : 'Execute the brief test-first: write each new test, run it and capture RED output, then implement to GREEN.'}
Rules: edit only the brief's files; stage explicit paths (never git add -A); commit as the plan lists; never edit an ask-first file unless the brief names its signed gate; never weaken a test, threshold or validation. You write the tests; you run ONLY the focused test files you touch (for RED/GREEN), always as ""$(git rev-parse --show-toplevel)/scripts/pyslot.sh" env HF_HUB_OFFLINE=1 <venv python> -m pytest <file>". A Haiku runner runs the full suite and acceptance; do not run it yourself. Push to ${plan.branch} when done. If something blocks you, status=stopped with the reason; do not work around it.
${STYLE}`,
  { label: `implement ${ID}${round ? ` r${round}` : ''}`, phase: 'Implement', model: 'sonnet', schema: IMPL_SCHEMA },
)

// Haiku runs tests only: it never writes or edits tests or code.
const runTests = (round) => agent(
  `Test runner for build-program item ${ID}, round ${round}: ${where}. Read-only: never edit, create, commit or push any file.
Run from ${plan.worktree}, every pytest through scripts/pyslot.sh (3 machine-wide pytest slots):
1. Focused: the test files in this list, if any: ${JSON.stringify((impl && impl.files_changed || []).filter((f) => /tests?\//.test(f)))}.
   "$(git rev-parse --show-toplevel)/scripts/pyslot.sh" env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest <files> -p no:cacheprovider -q   (cwd src/backend)
2. Collection: same prefix with tests/ --collect-only -q; copy the final line into collected_line.
3. Full backend suite: same prefix with tests/ -q.
4. These plan acceptance commands, skipping any that build, install or edit (npm build, pip install, writes): ${spec.acceptance_commands.join(' ;; ') || 'none listed'}.
5. python3 scripts/docs_lint.py (cwd worktree root).
Frontend vitest stalls under WSL on /mnt/c: record it as skipped with that reason, never retry.
\`test_api_rag_index_002b\` failing without an embedding model is environmental: list it in failures prefixed "ENV:" and do not count it against all_passed.
Return each command, its exit code and the last 30 lines of output verbatim. failures = one line per failing test id or command.
${STYLE}`,
  { label: `test ${ID} r${round}`, phase: 'Test', model: 'haiku', effort: 'low', schema: TEST_SCHEMA },
)

phase('Implement')
let impl = await implement(null, 0)
if (!impl || impl.status !== 'done') {
  return await block(`implement: ${impl ? impl.stop_reason || impl.report : 'implementer returned nothing'}`)
}
phase('Test')
let tests = await runTests(0)
for (let fix = 1; tests && !tests.all_passed && fix <= MAX_ROUNDS; fix++) {
  log(`${ID}: tests failing (${tests.failures.length}); back to implementer, fix ${fix}/${MAX_ROUNDS}`)
  impl = await implement(tests.failures.map((f) => `[BLOCKER] test failure — ${f}`), fix)
  if (!impl || impl.status !== 'done') return await block(`fixing tests: ${impl ? impl.stop_reason || impl.report : 'implementer returned nothing'}`)
  tests = await runTests(fix)
}
if (!tests || !tests.all_passed) {
  return await block(`tests still failing after ${MAX_ROUNDS} fixes:\n${tests ? tests.failures.join('\n') : 'test runner returned nothing'}`)
}
const testEvidence = () => tests.runs.map((r) => `$ ${r.command}\n(exit ${r.exit_code})\n${r.output_tail}`).join('\n\n')

// ---------------------------------------------------------------------------
const reviewPrompt = (round, lens) => `Review build-program item ${ID}, round ${round}/${MAX_ROUNDS}: ${where}. Read-only: never edit, commit or push.
Lens: ${lens}.
Spec: ${spec.spec_paths.join(', ')}; queue row in ${QUEUE}; contracts ${(spec.contracts || []).join(', ') || 'none'}.
Allowed files: ${spec.files.join(', ')}.
Implementer report:
${impl.report}
Test run (Haiku, verbatim):
${testEvidence()}
Diff: git -C ${plan.worktree} diff origin/main...HEAD.
Check in order: (1) spec compliance and file list, (2) quality, (3) every mode in docs/agentic/recurring-failures.md: route tests via route_client, say what each new test would fail to notice. Flag any ask-first edit without a signed gate naming it, and any weakened test or threshold.
Return verdict PASS or REVISE and findings as "[BLOCKER|MAJOR|MINOR] file:line — issue — fix". Then post them as a PR comment headed "review round ${round}/${MAX_ROUNDS} (claude, opus ${lens})" with: gh pr comment ${plan.pr_number} --body-file <tmpfile under /tmp/claude-1000>.
${STYLE}`

phase('Review')
let passed = false
let lastFindings = []
for (let round = 1; round <= MAX_ROUNDS; round++) {
  const lenses = [{ lens: 'spec + quality + recurring failures', agentType: 'code-reviewer' }]
  if (spec.security_sensitive) lenses.push({ lens: 'security: PHI leaks, redaction, auth, audit logging', agentType: 'security-reviewer' })
  const reviews = (await parallel(lenses.map((l) => () => agent(reviewPrompt(round, l.lens), {
    label: `review ${ID} r${round} ${l.agentType}`, phase: 'Review', model: 'opus', effort: 'high', agentType: l.agentType, schema: REVIEW_SCHEMA,
  })))).filter(Boolean)
  if (reviews.length !== lenses.length) {
    return await block(`review round ${round}: a reviewer returned nothing; re-run review, do not treat as PASS`)
  }
  lastFindings = reviews.flatMap((r) => r.findings)
  if (reviews.every((r) => r.verdict === 'PASS')) { passed = true; break }
  log(`${ID}: round ${round} REVISE, ${lastFindings.length} findings`)
  if (round === MAX_ROUNDS) break
  impl = await implement(lastFindings, round)
  if (!impl || impl.status !== 'done') {
    return await block(`fixing round ${round}: ${impl ? impl.stop_reason || impl.report : 'implementer returned nothing'}`)
  }
  tests = await runTests(round)
  if (!tests || !tests.all_passed) {
    return await block(`tests failing after review fix ${round}:\n${tests ? tests.failures.join('\n') : 'test runner returned nothing'}`)
  }
}

if (!passed) {
  await agent(
    `Escalate build-program item ${ID} per ${RUNBOOK} §8: ${where}.
1. gh pr edit ${plan.pr_number} --title "[escalated:claude] ${ID} <keep the current slug>" (keep it draft).
2. gh pr comment ${plan.pr_number} with heading "escalation: owner", listing these open findings verbatim:
${lastFindings.join('\n')}
Change nothing else.
${STYLE}`,
    { label: `escalate ${ID}`, phase: 'Review', model: 'opus', effort: 'low' },
  )
  return `ESCALATED ${ID} after ${MAX_ROUNDS} REVISE rounds (PR #${plan.pr_number}). Open findings:\n${lastFindings.join('\n')}`
}

// ---------------------------------------------------------------------------
phase('Verify')
return await agent(
  `You are L1 (Opus) closing build-program item ${ID}: ${where}. Follow ${RUNBOOK} §6 and §7 exactly.
1. Merge origin/main into the worktree only if the PR has a real code conflict or code dependency (contracts.md §d step 4). Never edit docs/INDEX.md, docs/_link_graph.json, the count slots or the docs/reviews/README.md table; on any conflict in your own files stop and report.
2. The Haiku runner's final test output is below; judge it (a report is a lead, not a finding: re-run any single command whose output looks wrong, under the flock). Run the §6 steps that are not test runs (greps, scope checks, docs lint) yourself and keep every command with its output.\nHaiku test output:\n${testEvidence()}\n   Paste the measured collected line and its delta into the PR body; never write the count slots (SLOT-RULE-2). If anything fails, stop: keep draft, comment the output on the PR, retitle it "[blocked:claude] ${ID} <keep the current slug>" (${RUNBOOK} §8), and return FAILED.
3. ${spec.architectural ? `Architectural item: run the Codex adversarial review (§10.2 codex-companion adversarial-review) from the worktree. A BLOCKER means: keep draft, comment it, retitle it "[blocked:claude] ${ID} <keep the current slug>", return BLOCKED.` : 'Not architectural: no Codex review.'}
4. Push. Write the PR body with every §6 table section (gates quoted: ${(plan.gates_quoted || []).join(' | ') || 'none'}; skipped tasks: ${(plan.skipped_tasks || []).join(', ') || 'none'}; start count: ${plan.start_count || 'see Task 0'}; implementer claude sonnet; reviewer claude opus, final verdict PASS). Use gh pr edit ${plan.pr_number} --body-file.
5. Retitle to "<type>(<scope>): <summary> (${ID})" to release the slot. Run gh pr ready ${plan.pr_number} only if no merge-only gate is unanswered and the item is not a parked draft (contracts.md §b rule 2). Re-read the row's owner gates against owner-decisions yourself first; an empty gates list from Task 0 is not evidence that none apply.
6. Stop. Never merge, never push to main.
Return: first line PR URL + READY | DRAFT (why) | FAILED | BLOCKED; then the final count line and the full test command output tail.
${STYLE}`,
  { label: `verify+PR ${ID}`, phase: 'Verify', model: 'opus', effort: 'high' },
)
