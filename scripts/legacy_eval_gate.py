#!/usr/bin/env python3
"""
Legacy RAG eval gate: fail CI if the legacy (non-agent) POST /assistant/chat
path serves an answer that failed validation (W-4; owner decision G-B5,
docs/capstone-report/owner-decisions-2026-09-27.md).

Usage (from the repo root):
    python3 scripts/legacy_eval_gate.py

Scores src/backend/tests/legacy_eval/golden/*.json through the real route over
HTTP; only retrieval and generation are faked (see tests/legacy_eval/harness.py).

Exit codes:
    0: PASS
    1: FAIL (an invalid or uncited legacy answer reached the patient, or a
       grounded answer was abstained)
    2: the gate itself could not run (import/setup/malformed case)

Bars (never lowered; contract C-SAFE-4):
    served_invalid == 0, uncited_served == 0, leaked == 0, persisted_mismatch == 0,
    abstention == 1.0, escalation == 1.0, answer_rate == 1.0.
(escalation and leaked are added by the 2026-10-11 amendment; none is lowered.)
The 0.6 faithfulness threshold lives in modules/rag.py and is not read or set here.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "src" / "backend"


def _setup_backend_path() -> None:
    backend_str = str(BACKEND_DIR)
    if backend_str not in sys.path:
        sys.path.insert(0, backend_str)
    os.environ.setdefault("TEST_MODE", "1")


def main() -> int:
    _setup_backend_path()
    try:
        from tests.legacy_eval.harness import load_cases, score_cases
    except Exception as exc:
        print(f"Legacy eval gate: ERROR, could not import harness: {exc}")
        return 2
    try:
        report = score_cases(load_cases())
    except Exception as exc:
        print(f"Legacy eval gate: ERROR, scoring raised: {exc}")
        return 2

    print(report.render())
    print()
    if report.passed:
        print("Legacy eval gate: PASS")
        return 0
    print("Legacy eval gate: FAIL, " + "; ".join(report.failure_reasons()))
    return 1


if __name__ == "__main__":
    sys.exit(main())
