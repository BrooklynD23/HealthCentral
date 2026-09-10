"""HC-SECGATE-001..007 — the security gate must fail closed.

`scripts/security_gate.py` documents exit code 2 for "report parsing error"
(module docstring, ~line 9) but before this test existed, a missing or
truncated bandit/pip-audit report was swallowed by `check_bandit` /
`check_pip_audit` (they caught `FileNotFoundError` / `json.JSONDecodeError`,
printed a WARNING, and returned `[]`) and the gate read that as "zero
findings" — exit 0, a green security gate, for a scan that never happened.

These tests pin the fail-closed behavior: absent evidence must never read as
absence of findings.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "security_gate.py"
SPEC = importlib.util.spec_from_file_location("security_gate_root", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
security_gate = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = security_gate
SPEC.loader.exec_module(security_gate)

main = security_gate.main

CLEAN_BANDIT = {"results": []}
CLEAN_PIP_AUDIT = {"dependencies": []}

HIGH_BANDIT = {
    "results": [
        {
            "issue_severity": "HIGH",
            "issue_confidence": "HIGH",
            "issue_text": "Use of insecure function",
            "filename": "src/backend/modules/example.py",
            "line_number": 42,
            "test_id": "B999",
        }
    ]
}


def _write(path: Path, data: dict) -> str:
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


# HC-SECGATE-001 — a missing bandit report must exit 2, not read as clean
def test_missing_bandit_report_exits_2(tmp_path: Path, capsys) -> None:
    pip_audit_path = _write(tmp_path / "pip-audit-report.json", CLEAN_PIP_AUDIT)
    missing_bandit_path = str(tmp_path / "does-not-exist-bandit.json")

    exit_code = main(["--bandit", missing_bandit_path, "--pip-audit", pip_audit_path])

    assert exit_code == 2
    assert "ERROR" in capsys.readouterr().out


# HC-SECGATE-002 — a missing pip-audit report must exit 2, not read as clean
def test_missing_pip_audit_report_exits_2(tmp_path: Path, capsys) -> None:
    bandit_path = _write(tmp_path / "bandit-report.json", CLEAN_BANDIT)
    missing_pip_audit_path = str(tmp_path / "does-not-exist-pip-audit.json")

    exit_code = main(["--bandit", bandit_path, "--pip-audit", missing_pip_audit_path])

    assert exit_code == 2
    assert "ERROR" in capsys.readouterr().out


# HC-SECGATE-003 — truncated/malformed JSON must exit 2, not read as clean
def test_malformed_bandit_json_exits_2(tmp_path: Path, capsys) -> None:
    bandit_path = tmp_path / "bandit-report.json"
    bandit_path.write_text('{"results": [', encoding="utf-8")  # truncated
    pip_audit_path = _write(tmp_path / "pip-audit-report.json", CLEAN_PIP_AUDIT)

    exit_code = main(["--bandit", str(bandit_path), "--pip-audit", pip_audit_path])

    assert exit_code == 2
    assert "ERROR" in capsys.readouterr().out


# HC-SECGATE-004 — a valid report with an unwaived high-severity finding fails the build
def test_unwaived_high_severity_finding_exits_1(tmp_path: Path, capsys) -> None:
    bandit_path = _write(tmp_path / "bandit-report.json", HIGH_BANDIT)
    pip_audit_path = _write(tmp_path / "pip-audit-report.json", CLEAN_PIP_AUDIT)

    exit_code = main(["--bandit", bandit_path, "--pip-audit", pip_audit_path])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "FAIL" in out


# HC-SECGATE-005 — a valid, clean report pair passes
def test_clean_reports_exit_0(tmp_path: Path, capsys) -> None:
    bandit_path = _write(tmp_path / "bandit-report.json", CLEAN_BANDIT)
    pip_audit_path = _write(tmp_path / "pip-audit-report.json", CLEAN_PIP_AUDIT)

    exit_code = main(["--bandit", bandit_path, "--pip-audit", pip_audit_path])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "PASS" in out


# HC-SECGATE-006 — an expired waiver must surface its finding again, not stay suppressed
def test_expired_waiver_still_fails(tmp_path: Path, capsys) -> None:
    expired_pip_audit = {
        "dependencies": [
            {
                "name": "diskcache",
                "version": "5.0.0",
                "vulns": [
                    {
                        "id": "CVE-2025-69872",
                        "aliases": [],
                        "description": "pickle deserialization RCE",
                    }
                ],
            }
        ]
    }
    bandit_path = _write(tmp_path / "bandit-report.json", CLEAN_BANDIT)
    pip_audit_path = _write(tmp_path / "pip-audit-report.json", expired_pip_audit)

    # The real WAIVERS entry for CVE-2025-69872 expires 2026-12-30 and is
    # still active "today" in this repo's clock; this test only confirms the
    # mechanism (not the live waiver's date), so drive it through the
    # module's own expiry comparison by monkeypatching `date.today`.
    import datetime as _datetime

    class _FixedDate(_datetime.date):
        @classmethod
        def today(cls):
            return _datetime.date(2027, 1, 1)

    original_date = security_gate.date
    security_gate.date = _FixedDate
    try:
        exit_code = main(["--bandit", bandit_path, "--pip-audit", pip_audit_path])
    finally:
        security_gate.date = original_date

    out = capsys.readouterr().out
    assert exit_code == 1
    assert "EXPIRED" in out


def test_hc_secgate_007_cli_boundary_exits_2_on_missing_report(tmp_path):
    """HC-SECGATE-007 — exit 2 survives the CLI boundary CI actually uses.

    The tests above call `main()` in-process, which cannot see a regression in
    the `sys.exit(main())` wiring or in argparse itself. CI invokes the script
    as `python3 scripts/security_gate.py --bandit ... --pip-audit ...`, so pin
    that form too: a missing report must make the *process* exit 2.
    """
    import subprocess

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--bandit",
            str(tmp_path / "absent-bandit.json"),
            "--pip-audit",
            str(tmp_path / "absent-pip-audit.json"),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2, result.stdout + result.stderr
    assert "ERROR" in result.stdout
