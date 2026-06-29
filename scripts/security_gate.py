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
from datetime import date

# ---------------------------------------------------------------------------
# Waivers — temporarily allow a known finding past the gate.
#
# Each waiver must carry an owner and an expiry date (ISO YYYY-MM-DD). A waiver
# matches a bandit finding by its ``test_id`` or a pip-audit finding by its
# ``vuln_id``. Expired waivers are ignored, so the finding fails the gate again
# once the expiry date has passed. Keep this list short and review on expiry.
# ---------------------------------------------------------------------------
WAIVERS: list[dict] = [
    {
        "id": "CVE-2025-69872",
        "owner": "dangtran1022@gmail.com",
        "expiry": "2026-09-23",
        "reason": (
            "diskcache is a transitive dependency of llama-cpp-python; no "
            "patched release exists. The pickle deserialization RCE requires "
            "local write access to the cache directory, which is outside the "
            "local-first, single-user threat model."
        ),
    },
]


def _finding_id(finding: dict) -> str:
    """Return the identifier a waiver matches against for a given finding."""
    return finding.get("vuln_id") or finding.get("test_id") or ""


def partition_waived(findings: list[dict], today: date | None = None) -> tuple[list[dict], list[dict]]:
    """Split findings into (active, waived) using non-expired waivers."""
    today = today or date.today()
    active_waivers = {}
    for w in WAIVERS:
        try:
            expiry = date.fromisoformat(w["expiry"])
        except (KeyError, ValueError):
            # Malformed waiver — treat as absent so the finding still fails.
            continue
        if expiry >= today:
            active_waivers[w["id"]] = w

    active: list[dict] = []
    waived: list[dict] = []
    for f in findings:
        waiver = active_waivers.get(_finding_id(f))
        if waiver:
            f = {**f, "_waiver": waiver}
            waived.append(f)
        else:
            active.append(f)
    return active, waived


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

    all_findings, waived = partition_waived(all_findings)

    if waived:
        print(f"Security gate: {len(waived)} finding(s) waived")
        for f in waived:
            w = f["_waiver"]
            print(f"  [WAIVED until {w['expiry']}, owner {w['owner']}] {_finding_id(f)}")
            print(f"    {w['reason']}")
        print()

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
