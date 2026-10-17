// Verbatim copy of cases.json (the test environment cannot import JSON). Regenerate:
//   (echo '// ...'; echo "export default $(cat replay/cases.json)") — see README.
export default [
  { "id": "pkill-self-pos-1", "rule": "pkill-self", "tool": "Bash", "input": { "command": "pkill -f \"vite --port 5173\"" }, "expect": "deny" },
  { "id": "pkill-self-pos-2", "rule": "pkill-self", "tool": "Bash", "input": { "command": "pkill -9 -f uvicorn" }, "expect": "deny" },
  { "id": "pkill-self-neg-1", "rule": "pkill-self", "tool": "Bash", "input": { "command": "lsof -ti:5173 -sTCP:LISTEN | xargs kill" }, "expect": "pass" },
  { "id": "pkill-self-neg-2", "rule": "pkill-self", "tool": "Bash", "input": { "command": "pkill node" }, "expect": "pass" },
  { "id": "playwright-exec-path-pos", "rule": "playwright-exec-path", "tool": "Bash", "input": { "command": "npx playwright test" }, "error_text": "Error: browserType.launch: Executable doesn't exist at /home/u/.cache/ms-playwright/chromium-1187/chrome-linux/chrome", "expect": "hint" },
  { "id": "playwright-exec-path-neg", "rule": "playwright-exec-path", "tool": "Bash", "input": { "command": "npx playwright test" }, "error_text": "Error: expect(locator).toBeVisible() failed", "expect": "pass" },
  { "id": "gh-pr-edit-projects-classic-pos", "rule": "gh-pr-edit-projects-classic", "tool": "Bash", "input": { "command": "gh pr edit 12 --title x" }, "error_text": "GraphQL: Projects (classic) is being deprecated (repository.pullRequest.projectCards)", "expect": "hint" },
  { "id": "gh-pr-edit-projects-classic-neg", "rule": "gh-pr-edit-projects-classic", "tool": "Bash", "input": { "command": "gh pr edit 12 --title x" }, "error_text": "GraphQL: Could not resolve to a PullRequest", "expect": "pass" },
  { "id": "venv-husk-pos", "rule": "venv-husk", "tool": "Bash", "input": { "command": "src/backend/.venv/bin/pytest -q tests/" }, "failed": false, "error_text": "", "expect": "hint" },
  { "id": "venv-husk-neg-summary", "rule": "venv-husk", "tool": "Bash", "input": { "command": "src/backend/.venv/bin/pytest -q tests/" }, "failed": false, "error_text": "12 passed in 1.2s", "expect": "pass" },
  { "id": "venv-husk-neg-good-venv", "rule": "venv-husk", "tool": "Bash", "input": { "command": "~/venvs/asclexis-311/bin/pytest -q" }, "failed": false, "error_text": "", "expect": "pass" },
  { "id": "llama-cpp-no-compiler-pos", "rule": "llama-cpp-no-compiler", "tool": "Bash", "input": { "command": "pip install llama-cpp-python" }, "error_text": "CMake Error: No CMAKE_C_COMPILER could be found.", "expect": "hint" },
  { "id": "llama-cpp-no-compiler-neg", "rule": "llama-cpp-no-compiler", "tool": "Bash", "input": { "command": "pip install llama-cpp-python" }, "error_text": "ERROR: No matching distribution found", "expect": "pass" }
]
