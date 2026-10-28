"""Claude Code hook: append one JSONL telemetry row per tool call / session end.

Observe leg of the dev-process self-improvement loop
(docs/plans/2026-10-10-rsi-loop-applicability-report.md §5 #1).

Records metadata only: never file contents, command text, or tool output,
which can hold PHI or secrets. Failure rows carry `error_class`, a fixed
category (mirrors classifyError in the asclexis-rsi mod), never the error text. Writes to .claude/logs/ (git-ignored) so the
hook never dirties the tracked tree. Always exits 0: telemetry must not block.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = REPO_ROOT / ".claude" / "logs" / "session-log.jsonl"

_EXIT_RE = re.compile(r"^Exit code (\d+)")
_PASSED_RE = re.compile(r"(\d+) passed")
_FAILED_RE = re.compile(r"(\d+) failed")

_ERROR_CLASSES = (
    "exit-144-self-kill", "timeout", "edit-no-match", "permission-denied", "module-not-found",
    "command-not-found", "no-such-file", "tests-failed", "git-fatal", "syntax-error",
    "exit-", "other",
)


def _classify(text: str) -> str:
    """Fixed category for a failure; mirrors classifyError in the asclexis-rsi mod. Never returns input text."""
    a = re.ASCII
    if re.search(r"Exit code 144\b", text, a):
        return "exit-144-self-kill"
    if re.search(r"timed out|timeout", text, re.IGNORECASE):
        return "timeout"
    if re.search(r"did not match|not found in file|String to replace not found", text, re.IGNORECASE):
        return "edit-no-match"
    if re.search(r"permission denied|EACCES", text, re.IGNORECASE):
        return "permission-denied"
    if re.search(r"ModuleNotFoundError|No module named", text):
        return "module-not-found"
    if re.search(r"command not found|Exit code 127\b", text, a):
        return "command-not-found"
    if re.search(r"No such file or directory|ENOENT", text):
        return "no-such-file"
    if re.search(r"\b\d+ failed\b", text, a):
        return "tests-failed"
    if re.search(r"^fatal: ", text, re.MULTILINE):
        return "git-fatal"
    if re.search(r"SyntaxError|syntax error", text, re.IGNORECASE):
        return "syntax-error"
    match = re.search(r"^Exit code (\d{1,3})\b", text, re.MULTILINE | a)
    if match and 1 <= int(match.group(1)) <= 255:
        return f"exit-{int(match.group(1))}"
    return "other"


def _rel_path(raw: str | None, repo_root: Path) -> str | None:
    if not raw:
        return None
    try:
        return Path(raw).resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return "<outside-repo>"


def _test_counts(text: str) -> dict[str, int] | None:
    passed, failed = _PASSED_RE.search(text), _FAILED_RE.search(text)
    if not (passed or failed):
        return None
    return {"passed": int(passed.group(1)) if passed else 0, "failed": int(failed.group(1)) if failed else 0}


def build_record(payload: dict, repo_root: Path) -> dict:
    event = payload.get("hook_event_name")
    record = {"ts": datetime.now(UTC).isoformat(), "event": event, "session_id": payload.get("session_id")}
    if event == "SessionEnd":
        record["reason"] = payload.get("reason")
        return record

    tool_input = payload.get("tool_input") or {}
    record.update(
        tool_name=payload.get("tool_name"),
        file_path=_rel_path(tool_input.get("file_path") or tool_input.get("notebook_path"), repo_root),
        ok=event != "PostToolUseFailure",
        duration_ms=payload.get("duration_ms"),
    )
    record["error_class"] = None if record["ok"] else _classify(payload.get("error") or "")
    if record["tool_name"] == "Bash":
        if record["ok"]:
            response = payload.get("tool_response") or {}
            output = f"{response.get('stdout', '')}\n{response.get('stderr', '')}"
            record["exit_code"] = 0
        else:
            output = payload.get("error") or ""
            match = _EXIT_RE.match(output)
            record["exit_code"] = int(match.group(1)) if match else None
        record["tests"] = _test_counts(output)
    return record


def main(stdin_text: str, log_path: Path = LOG_PATH, repo_root: Path = REPO_ROOT) -> int:
    try:
        payload = json.loads(stdin_text)
        record = build_record(payload, repo_root)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except Exception:  # noqa: BLE001 - telemetry must never block a session
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.stdin.read()))
