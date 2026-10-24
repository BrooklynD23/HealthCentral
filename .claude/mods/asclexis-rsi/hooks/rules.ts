// Data-only guard/hint table (RSI contract). `rsi-loop` proposals may edit ONLY this file,
// replay/cases.ts and docs/agentic/recurring-failures.md.
// Fields: id, tool, when (before|after), match (regex source; before: over the command,
// after: over the error/output text), action (deny|hint), message, source, errorClass.
// Optional after-only refinements: `command` (regex the command must also match),
// `onSuccess` (also fire when the call did not fail), `absent` (regex that must NOT occur in output).
export type Rule = {
  id: string
  tool: string
  when: 'before' | 'after'
  match: string
  action: 'deny' | 'hint'
  message: string
  source: string
  errorClass: string
  command?: string
  onSuccess?: boolean
  absent?: string
}

export const RULES: readonly Rule[] = [
  {
    id: 'pkill-self',
    tool: 'Bash',
    when: 'before',
    match: String.raw`\bpkill\s+(?:-[A-Za-z0-9]+\s+)*(?:-[A-Za-z]*f[A-Za-z]*|--full)\b`,
    action: 'deny',
    message:
      '`pkill -f` can match this shell itself and kill it (exit 144). Stop by port instead: `lsof -ti:PORT -sTCP:LISTEN | xargs kill`.',
    source: 'handoff 2026-10-17 s4: pkill -f killed the agent shell (exit 144)',
    errorClass: 'exit-144-self-kill',
  },
  {
    id: 'playwright-exec-path',
    tool: 'Bash',
    when: 'after',
    match: String.raw`Executable doesn't exist at \S*ms-playwright`,
    action: 'hint',
    message:
      'Playwright bundled browser revision differs. Launch with executablePath=~/.cache/ms-playwright/chromium-1200/chrome-linux64/chrome.',
    source: 'handoff 2026-10-17 s4: Playwright browser path mismatch',
    errorClass: 'playwright-exec-missing',
  },
  {
    id: 'gh-pr-edit-projects-classic',
    tool: 'Bash',
    when: 'after',
    match: String.raw`Projects \(classic\)|projectCards`,
    command: String.raw`\bgh\s+pr\s+edit\b`,
    action: 'hint',
    message:
      '`gh pr edit` fails on Projects (classic). Use: gh api -X PATCH repos/{owner}/{repo}/pulls/N -f title=... -f body=...',
    source: 'handoff 2026-10-17 s2.2: gh pr edit failing on Projects classic',
    errorClass: 'gh-projects-classic',
  },
  {
    id: 'venv-husk',
    tool: 'Bash',
    when: 'after',
    match: String.raw`^`,
    command: String.raw`\.?venv/bin/(?:pytest|python3?\s+-m\s+pytest)\b`,
    onSuccess: true,
    absent: String.raw`\d+ (?:passed|failed|skipped|errors?)|no tests ran|collected \d+`,
    action: 'hint',
    message:
      'Exit 0 with no pytest summary: a checked-in venv bin file is a husk that silently no-ops. Use ~/venvs/asclexis-311/bin/pytest.',
    source: 'memory wsl-pytest-venv-husk-gotcha: checked-in venv bin files exit 0 without running',
    errorClass: 'venv-husk',
  },
  {
    id: 'llama-cpp-no-compiler',
    tool: 'Bash',
    when: 'after',
    match: String.raw`No CMAKE_C_COMPILER|CMAKE_CXX_COMPILER (?:not set|could not be found)|gcc: command not found`,
    action: 'hint',
    message: 'llama-cpp-python needs a C compiler. Install one first: sudo apt-get install -y build-essential cmake.',
    source: 'handoff 2026-10-17 s2.2: llama-cpp-python with no C compiler',
    errorClass: 'no-c-compiler',
  },
  {
    id: 'embedding-bundle-missing',
    tool: 'Bash',
    when: 'after',
    match: String.raw`test_hc_emb_002_fetched_model_loads_offline|test_api_rag_index_002[bc]?|test_search_vectors_async_calculates_similarity`,
    action: 'hint',
    message:
      'These failures are environmental. Fetch the model with python scripts/download_models.py embedding. Do not lower the 0.7 threshold. Judge on the collected count (recurring-failures #4).',
    source: 'pr-review leads 223,218',
    errorClass: 'embedding-bundle-missing',
  },
  {
    id: 'no-such-file-path',
    tool: 'Bash',
    when: 'after',
    match: String.raw`No such file or directory`,
    action: 'hint',
    message:
      'A path was not found ("No such file or directory"). Resolve and verify the path (ls its parent directory) before retrying the command unchanged.',
    source: 'rsi-2026-10-24-gpubox-1: Bash/no-such-file cluster, 35 failed calls since 2026-10-21, no path recorded',
    errorClass: 'no-such-file',
  },
]
