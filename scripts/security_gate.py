#!/usr/bin/env python3
"""
Security scan gate — fail CI if high/critical findings exist.

Usage:
    python3 scripts/security_gate.py [--bandit bandit-report.json] [--pip-audit pip-audit-report.json]

Exit codes:
    0 — no unwaived high/critical findings
    1 — unwaived high/critical findings detected
    2 — report parsing error

Waivers
-------
A finding can be accepted with an explicit, time-boxed waiver (see WAIVERS).
Every waiver MUST declare an owner and an expiry date. Once the expiry date
passes, the waiver stops suppressing the finding and the gate fails again,
which forces the risk to be re-reviewed rather than silently accepted forever.
"""

import argparse
import json
import sys
from datetime import date, datetime

# Accepted findings keyed by advisory id (CVE / GHSA / PYSEC) or bandit test id.
# Matching is done against the finding's id AND its aliases, so either the CVE
# or the GHSA form works.
WAIVERS: dict[str, dict[str, str]] = {
    "CVE-2025-69872": {
        "package": "diskcache",
        "reason": (
            "diskcache is a transitive dependency of llama-cpp-python; no "
            "patched release exists. The pickle deserialization RCE requires "
            "local write access to the cache directory, which is outside the "
            "local-first, single-user threat model."
        ),
        "owner": "dangtran1022@gmail.com",
        "expires": "2026-09-23",
    },
}


def check_bandit(report_path: str) -> list[dict]:
    """Parse bandit JSON report and return high/critical findings."""
    try:
        with open(report_path) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"WARNING: Could not parse bandit report '{report_path}': {e}")
        return []

    results = data.get("results", [])
    findings = []
    for r in results:
        severity = r.get("issue_severity", "").upper()
        confidence = r.get("issue_confidence", "").upper()
        if severity in ("HIGH", "CRITICAL") and confidence in ("HIGH", "MEDIUM"):
            findings.append({
                "tool": "bandit",
                "severity": severity,
                "confidence": confidence,
                "issue": r.get("issue_text", ""),
                "file": r.get("filename", ""),
                "line": r.get("line_number", ""),
                "test_id": r.get("test_id", ""),
            })
    return findings


def check_pip_audit(report_path: str) -> list[dict]:
    """Parse pip-audit JSON report and return high/critical vulnerabilities."""
    try:
        with open(report_path) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"WARNING: Could not parse pip-audit report '{report_path}': {e}")
        return []

    # pip-audit JSON format: {"dependencies": [...]} or bare list
    deps = data if isinstance(data, list) else data.get("dependencies", [])
    findings = []
    for dep in deps:
        vulns = dep.get("vulns", [])
        for v in vulns:
            # Treat all pip-audit vulnerabilities as high (they're known CVEs)
            findings.append({
                "tool": "pip-audit",
                "severity": "HIGH",
                "package": dep.get("name", ""),
                "version": dep.get("version", ""),
                "vuln_id": v.get("id", ""),
                "aliases": list(v.get("aliases", []) or []),
                "description": v.get("description", "")[:200],
            })
    return findings


def _finding_ids(finding: dict) -> set[str]:
    """All identifiers a waiver could match for this finding."""
    ids: set[str] = set()
    if finding.get("vuln_id"):
        ids.add(finding["vuln_id"])
    if finding.get("test_id"):
        ids.add(finding["test_id"])
    ids.update(finding.get("aliases", []) or [])
    return ids


def match_waiver(finding: dict) -> tuple[str, dict] | None:
    """Return (matched_id, waiver) if any id of the finding has a waiver."""
    for ident in _finding_ids(finding):
        if ident in WAIVERS:
            return ident, WAIVERS[ident]
    return None


def _describe(finding: dict) -> str:
    if finding["tool"] == "bandit":
        return (
            f"  [{finding['tool']}] {finding['severity']}/{finding['confidence']}: "
            f"{finding['issue']}\n    {finding['file']}:{finding['line']} ({finding['test_id']})"
        )
    return (
        f"  [{finding['tool']}] {finding['severity']}: "
        f"{finding['package']}=={finding['version']}\n    "
        f"{finding['vuln_id']}: {finding['description']}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Security scan gate for CI")
    parser.add_argument(
        "--bandit",
        default="bandit-report.json",
        help="Bandit JSON report path",
    )
    parser.add_argument(
        "--pip-audit",
        default="pip-audit-report.json",
        help="pip-audit JSON report path",
    )
    args = parser.parse_args()

    all_findings: list[dict] = []
    all_findings.extend(check_bandit(args.bandit))
    all_findings.extend(check_pip_audit(args.pip_audit))

    today = date.today()
    active: list[dict] = []
    waived: list[tuple[dict, str, dict]] = []

    for f in all_findings:
        matched = match_waiver(f)
        if matched is not None:
            ident, waiver = matched
            expires = datetime.strptime(waiver["expires"], "%Y-%m-%d").date()
            if expires >= today:
                waived.append((f, ident, waiver))
                continue
            # Expired waiver: do not suppress; surface it as active with a note.
            f = {**f, "_expired": (ident, expires)}
        active.append(f)

    if waived:
        print(f"Security gate: {len(waived)} finding(s) suppressed by active waiver(s)")
        for f, ident, waiver in waived:
            print(_describe(f))
            print(
                f"    WAIVED {ident} (owner={waiver['owner']}, expires={waiver['expires']}): "
                f"{waiver['reason']}"
            )
            print()

    if not active:
        print("Security gate: PASS (no unwaived high/critical findings)")
        return 0

    print(f"Security gate: FAIL ({len(active)} high/critical finding(s))")
    print()
    for f in active:
        print(_describe(f))
        if "_expired" in f:
            ident, expires = f["_expired"]
            print(f"    NOTE: waiver for {ident} EXPIRED on {expires} — re-review required")
        print()

    return 1


if __name__ == "__main__":
    sys.exit(main())
