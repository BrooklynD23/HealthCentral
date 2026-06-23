"""Shared fixtures for the agent eval suite.

Golden cases are checked-in JSON (docs/agile/EXPLORATION_SUMMARY.md, decided),
loaded from ``tests/agent/golden/``. Each case is a triple: question + synthetic
vault state + expected behavior (skills/healthcentral-evals).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

GOLDEN_DIR = Path(__file__).parent / "golden"


def load_golden_cases() -> list[dict]:
    """Load every golden case JSON file under tests/agent/golden/."""
    cases: list[dict] = []
    for path in sorted(GOLDEN_DIR.glob("*.json")):
        cases.append(json.loads(path.read_text()))
    return cases


@pytest.fixture
def golden_cases() -> list[dict]:
    return load_golden_cases()
