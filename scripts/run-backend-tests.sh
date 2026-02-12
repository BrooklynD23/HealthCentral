#!/usr/bin/env bash
# Backend test runner for HealthCentral.
#
# Usage:
#   bash scripts/run-backend-tests.sh              # run all tests
#   bash scripts/run-backend-tests.sh tests/test_bootstrap_check.py -q
#
# This script:
#   1. Sets PYTHONPATH so imports resolve from src/backend.
#   2. Sets TEST_MODE=1 (conftest.py also sets this, but belt-and-suspenders).
#   3. Invokes pytest with any extra arguments passed to this script.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/src/backend"

export PYTHONPATH="$BACKEND_DIR${PYTHONPATH:+:$PYTHONPATH}"
export TEST_MODE=1

cd "$BACKEND_DIR"

echo "Running backend tests from $BACKEND_DIR"
echo "PYTHONPATH=$PYTHONPATH"
echo "---"

python3 -m pytest "$@"
