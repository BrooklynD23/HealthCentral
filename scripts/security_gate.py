#!/usr/bin/env python3
"""
Security scan gate — fail CI if high/critical findings exist.

Usage:
    python3 scripts/security_gate.py [--bandit bandit-report.json] [--pip-audit pip-audit-report.json]

Exit codes:
    0 — no high/critical findings
    1 — high/critical findings detected
    2 — report parsing error
"""

import argparse
import json
import sys


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
                "description": v.get("description", "")[:200],
            })
    return findings


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

    if not all_findings:
        print("Security gate: PASS (no high/critical findings)")
        return 0

    print(f"Security gate: FAIL ({len(all_findings)} high/critical finding(s))")
    print()
    for f in all_findings:
        if f["tool"] == "bandit":
            print(f"  [{f['tool']}] {f['severity']}/{f['confidence']}: {f['issue']}")
            print(f"    {f['file']}:{f['line']} ({f['test_id']})")
        else:
            print(f"  [{f['tool']}] {f['severity']}: {f['package']}=={f['version']}")
            print(f"    {f['vuln_id']}: {f['description']}")
        print()

    return 1


if __name__ == "__main__":
    sys.exit(main())
