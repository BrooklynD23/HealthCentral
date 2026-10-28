// Single source of the replay set (JSON-shaped; the test environment cannot import .json).
// Shape: {id, rule, tool, input, error_text?, failed?, expect: 'deny'|'hint'|'pass'}.
export default [
  {"id": "pkill-self-pos-1", "rule": "pkill-self", "tool": "Bash", "input": {"command": "pkill -f \"vite --port 5173\""}, "expect": "deny"},
  {"id": "pkill-self-pos-2", "rule": "pkill-self", "tool": "Bash", "input": {"command": "pkill -9 -f uvicorn"}, "expect": "deny"},
  {"id": "pkill-self-pos-3", "rule": "pkill-self", "tool": "Bash", "input": {"command": "pkill --full uvicorn"}, "expect": "deny"},
  {"id": "pkill-self-neg-1", "rule": "pkill-self", "tool": "Bash", "input": {"command": "lsof -ti:5173 -sTCP:LISTEN | xargs kill"}, "expect": "pass"},
  {"id": "pkill-self-neg-2", "rule": "pkill-self", "tool": "Bash", "input": {"command": "pkill node"}, "expect": "pass"},
  {"id": "playwright-exec-path-pos", "rule": "playwright-exec-path", "tool": "Bash", "input": {"command": "npx playwright test"}, "error_text": "Error: browserType.launch: Executable doesn't exist at /home/u/.cache/ms-playwright/chromium-1187/chrome-linux/chrome", "expect": "hint"},
  {"id": "playwright-exec-path-neg", "rule": "playwright-exec-path", "tool": "Bash", "input": {"command": "npx playwright test"}, "error_text": "Error: expect(locator).toBeVisible() failed", "expect": "pass"},
  {"id": "gh-pr-edit-projects-classic-pos", "rule": "gh-pr-edit-projects-classic", "tool": "Bash", "input": {"command": "gh pr edit 12 --title x"}, "error_text": "GraphQL: Projects (classic) is being deprecated (repository.pullRequest.projectCards)", "expect": "hint"},
  {"id": "gh-pr-edit-projects-classic-neg", "rule": "gh-pr-edit-projects-classic", "tool": "Bash", "input": {"command": "gh pr edit 12 --title x"}, "error_text": "GraphQL: Could not resolve to a PullRequest", "expect": "pass"},
  {"id": "venv-husk-pos", "rule": "venv-husk", "tool": "Bash", "input": {"command": "src/backend/.venv/bin/pytest -q tests/"}, "failed": false, "error_text": "", "expect": "hint"},
  {"id": "venv-husk-neg-summary", "rule": "venv-husk", "tool": "Bash", "input": {"command": "src/backend/.venv/bin/pytest -q tests/"}, "failed": false, "error_text": "12 passed in 1.2s", "expect": "pass"},
  {"id": "venv-husk-neg-good-venv", "rule": "venv-husk", "tool": "Bash", "input": {"command": "~/venvs/asclexis-311/bin/pytest -q"}, "failed": false, "error_text": "", "expect": "pass"},
  {"id": "llama-cpp-no-compiler-pos", "rule": "llama-cpp-no-compiler", "tool": "Bash", "input": {"command": "pip install llama-cpp-python"}, "error_text": "CMake Error: No CMAKE_C_COMPILER could be found.", "expect": "hint"},
  {"id": "llama-cpp-no-compiler-neg", "rule": "llama-cpp-no-compiler", "tool": "Bash", "input": {"command": "pip install llama-cpp-python"}, "error_text": "ERROR: No matching distribution found", "expect": "pass"},
  {"id": "embedding-bundle-missing-pos", "rule": "embedding-bundle-missing", "tool": "Bash", "input": {"command": "pytest -q tests/"}, "error_text": "FAILED tests/test_rag_pipeline.py::test_api_rag_index_002b - AssertionError", "expect": "hint"},
  {"id": "embedding-bundle-missing-neg", "rule": "embedding-bundle-missing", "tool": "Bash", "input": {"command": "pytest -q tests/"}, "error_text": "FAILED tests/test_auth.py::test_hc_auth_001 - AssertionError", "expect": "pass"},
  {"id": "no-such-file-path-pos-1", "rule": "no-such-file-path", "tool": "Bash", "input": {"command": "cat docs/missing.md"}, "error_text": "Exit code 1\ncat: docs/missing.md: No such file or directory", "expect": "hint"},
  {"id": "no-such-file-path-pos-2", "rule": "no-such-file-path", "tool": "Bash", "input": {"command": "cd /mnt/e/Programming/Github Repo/HealthCentral && git status"}, "error_text": "bash: cd: /mnt/e/Programming/Github: No such file or directory", "expect": "hint"},
  {"id": "no-such-file-path-neg-1", "rule": "no-such-file-path", "tool": "Bash", "input": {"command": "grep -rn 'No such file' docs/"}, "failed": false, "error_text": "docs/agentic/recurring-failures.md:7: No such file or directory", "expect": "pass"},
  {"id": "no-such-file-path-neg-2", "rule": "no-such-file-path", "tool": "Bash", "input": {"command": "pytest -q tests/test_x.py"}, "error_text": "FAILED tests/test_x.py::test_y - AssertionError: 1 != 2", "expect": "pass"},
]
