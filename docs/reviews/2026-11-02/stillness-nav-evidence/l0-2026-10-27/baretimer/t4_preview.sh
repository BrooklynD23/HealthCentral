#!/usr/bin/env bash
# Preview T4 (HC-UISH-009 desktop + phone + popover M0, HC-UIG-006) x3 on the branch's own spec and config, read-only.
M=/tmp/claude-1000/-mnt-e-Programming-Github-Repo-HealthCentral/b8becc8c-4942-444f-9c3c-2a03f3900e75/scratchpad/baretimer
cd "/mnt/e/Programming/Github Repo/hc-ui-shell/src/frontend" || exit 2
echo "=== preview T4 $(date +%T)"; uptime; echo pgrep:; pgrep -fa "playwright|vitest|pytest" | grep -v -e pgrep -e t4_preview
HC_E2E_BASE_URL=http://127.0.0.1:4190 HC_E2E_BACKEND_PYTHON=$HOME/venvs/asclexis-311/bin/python \
  /tmp/claude-1000/hold_slots.sh npx playwright test e2e/ui-shell.spec.ts e2e/ui-gates.spec.ts --project=chromium \
  -g "HC-UISH-009|HC-UIG-006" --repeat-each=3 --reporter=line --output $M/pw-out-preview
echo "exit=$?"
