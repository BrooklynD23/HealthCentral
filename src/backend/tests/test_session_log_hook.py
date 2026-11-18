"""Regression coverage for the Claude Code session-log hook (.claude/hooks/session_log.py)."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / ".claude" / "hooks" / "session_log.py"
SPEC = importlib.util.spec_from_file_location("session_log_hook", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
session_log = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = session_log
SPEC.loader.exec_module(session_log)


def _run(tmp_path: Path, payload: object) -> list[dict]:
    log_path = tmp_path / "logs" / "session-log.jsonl"
    stdin = payload if isinstance(payload, str) else json.dumps(payload)
    assert session_log.main(stdin, log_path=log_path, repo_root=tmp_path) == 0
    if not log_path.exists():
        return []
    return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]


def test_edit_records_repo_relative_path_and_never_content(tmp_path: Path) -> None:
    rows = _run(tmp_path, {
        "session_id": "s1",
        "hook_event_name": "PostToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": str(tmp_path / "src" / "a.py"), "content": "PATIENT SECRET"},
        "tool_response": {"filePath": str(tmp_path / "src" / "a.py"), "type": "create"},
        "duration_ms": 12,
    })

    assert len(rows) == 1
    row = rows[0]
    assert row["session_id"] == "s1"
    assert row["tool_name"] == "Write"
    assert row["file_path"] == "src/a.py"
    assert row["ok"] is True
    assert "PATIENT SECRET" not in json.dumps(row)


def test_path_outside_repo_is_not_recorded(tmp_path: Path) -> None:
    rows = _run(tmp_path, {
        "session_id": "s1",
        "hook_event_name": "PostToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "/home/someone/private/notes.txt"},
    })

    assert rows[0]["file_path"] == "<outside-repo>"


def test_bash_success_records_test_counts_but_not_the_command(tmp_path: Path) -> None:
    rows = _run(tmp_path, {
        "session_id": "s2",
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "TOKEN=abc123 python -m pytest tests/"},
        "tool_response": {"stdout": "...\n1379 passed, 2 skipped in 80.1s\n", "stderr": ""},
    })

    row = rows[0]
    assert row["exit_code"] == 0
    assert row["tests"] == {"passed": 1379, "failed": 0}
    assert "abc123" not in json.dumps(row)
    assert "pytest" not in json.dumps(row)


def test_bash_failure_records_exit_code_and_red_counts(tmp_path: Path) -> None:
    rows = _run(tmp_path, {
        "session_id": "s3",
        "hook_event_name": "PostToolUseFailure",
        "tool_name": "Bash",
        "tool_input": {"command": "npx vitest run"},
        "error": "Exit code 1\n Tests  3 failed | 10 passed (13)",
    })

    row = rows[0]
    assert row["ok"] is False
    assert row["exit_code"] == 1
    assert row["tests"] == {"passed": 10, "failed": 3}


def test_session_end_is_recorded(tmp_path: Path) -> None:
    rows = _run(tmp_path, {"session_id": "s4", "hook_event_name": "SessionEnd", "reason": "logout"})

    assert rows[0]["event"] == "SessionEnd"
    assert rows[0]["reason"] == "logout"


def test_malformed_input_never_blocks_and_writes_nothing(tmp_path: Path) -> None:
    assert _run(tmp_path, "not json{") == []


def test_committed_settings_wire_the_hook_to_a_script_that_exists() -> None:
    """A hook whose command points at a missing file is a phantom gate."""
    settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    commands = [
        hook["command"]
        for groups in settings["hooks"].values()
        for group in groups
        for hook in group["hooks"]
    ]

    assert {"PostToolUse", "PostToolUseFailure", "SessionEnd"} <= set(settings["hooks"])
    assert commands and all(".claude/hooks/session_log.py" in c for c in commands)
    assert SCRIPT_PATH.is_file()


def _failure(tool: str, error: str, tmp_path: Path) -> dict:
    tool_input = {"file_path": str(tmp_path / "a.py")} if tool == "Edit" else {"command": "x"}
    return {
        "session_id": "s5",
        "hook_event_name": "PostToolUseFailure",
        "tool_name": tool,
        "tool_input": tool_input,
        "error": error,
    }


def test_hc_slog_001_failure_row_gets_fixed_class_never_the_error_text(tmp_path: Path) -> None:
    rows = _run(tmp_path, _failure("Bash", "Exit code 1\nModuleNotFoundError: No module named 'secretpkg'", tmp_path))

    assert rows[0]["error_class"] == "module-not-found"
    assert "secretpkg" not in json.dumps(rows[0])


@pytest.mark.parametrize(
    ("tool", "error", "expected"),
    [
        ("Bash", "Exit code 2\nboom", "exit-2"),
        ("Bash", "Exit code 144", "exit-144-self-kill"),
        ("Bash", "no exit line", "other"),
        ("Edit", "String to replace not found", "edit-no-match"),
    ],
)
def test_hc_slog_002_classes(tmp_path: Path, tool: str, error: str, expected: str) -> None:
    rows = _run(tmp_path, _failure(tool, error, tmp_path))

    assert rows[0]["error_class"] == expected


def test_hc_slog_003_success_is_null_and_session_end_has_no_key(tmp_path: Path) -> None:
    ok_rows = _run(tmp_path, {
        "session_id": "s6",
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "ls"},
        "tool_response": {"stdout": "", "stderr": ""},
    })
    end_rows = _run(tmp_path, {"session_id": "s6", "hook_event_name": "SessionEnd", "reason": "logout"})

    assert "error_class" in ok_rows[0] and ok_rows[0]["error_class"] is None
    assert "error_class" not in end_rows[-1]


def test_hc_slog_004_classes_match_the_mod_classifier() -> None:
    """Python and TS classifiers must emit the same fixed vocabulary."""
    source = (REPO_ROOT / ".claude" / "mods" / "asclexis-rsi" / "hooks" / "logic.ts").read_text(encoding="utf-8")
    body = source.split("export function classifyError", 1)[1].split("\n}", 1)[0]
    literals = set(re.findall(r"return '([a-z0-9-]+)'", body))

    assert "`exit-${n}`" in body
    assert set(session_log._ERROR_CLASSES) == literals | {"exit-"}
