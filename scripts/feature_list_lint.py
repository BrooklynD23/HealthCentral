#!/usr/bin/env python3
"""
Structural linter for feature_list.json — the agentic harness's task inventory
(docs/agentic/harness.md instructs every agent session to read it on start).

Until now nothing validated this file, so it silently fell thirteen milestones
behind the shipped product. These checks are deliberately structural only: they
cannot tell whether a `completed` entry is honestly complete, but they do stop
malformed, duplicated or unverifiable entries from landing.

Rules:
  FL-001  Top level is an object with a `features` list.
  FL-002  Every entry has all required keys.
  FL-003  `id` is unique and matches HC-M<digits>[letter].
  FL-004  `status` is one of pending | in_progress | completed.
  FL-005  `priority` is an integer 1-5.
  FL-006  `description` and `user_value` are non-empty strings.
  FL-007  `verification_steps` is a non-empty list of non-empty strings.

Usage:
  python3 scripts/feature_list_lint.py
Exits 1 and prints one line per violation on failure.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FEATURE_LIST = REPO_ROOT / "feature_list.json"

REQUIRED_KEYS = (
    "id",
    "category",
    "description",
    "user_value",
    "verification_steps",
    "priority",
    "status",
)
VALID_STATUSES = {"pending", "in_progress", "completed"}
ID_PATTERN = re.compile(r"^HC-M\d+[a-z]?$")


def _non_empty_str(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def lint(path: Path) -> list[str]:
    errors: list[str] = []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"{path.name}: file not found (FL-001)"]
    except json.JSONDecodeError as exc:
        return [f"{path.name}: invalid JSON at line {exc.lineno} — {exc.msg} (FL-001)"]

    if not isinstance(data, dict) or not isinstance(data.get("features"), list):
        return [f"{path.name}: top level must be an object with a 'features' list (FL-001)"]

    seen_ids: set[str] = set()

    for index, entry in enumerate(data["features"]):
        # Prefer the entry's own id in messages; fall back to position.
        label = entry.get("id") if isinstance(entry, dict) else None
        label = label if _non_empty_str(label) else f"features[{index}]"

        if not isinstance(entry, dict):
            errors.append(f"{label}: entry is not an object (FL-002)")
            continue

        for key in REQUIRED_KEYS:
            if key not in entry:
                errors.append(f"{label}: missing required key '{key}' (FL-002)")

        entry_id = entry.get("id")
        if _non_empty_str(entry_id):
            if not ID_PATTERN.match(entry_id):
                errors.append(f"{label}: id '{entry_id}' does not match HC-M<digits>[letter] (FL-003)")
            if entry_id in seen_ids:
                errors.append(f"{label}: duplicate id '{entry_id}' (FL-003)")
            seen_ids.add(entry_id)
        elif "id" in entry:
            errors.append(f"{label}: id must be a non-empty string (FL-003)")

        status = entry.get("status")
        if "status" in entry and status not in VALID_STATUSES:
            errors.append(
                f"{label}: status '{status}' not in {sorted(VALID_STATUSES)} (FL-004)"
            )

        priority = entry.get("priority")
        # bool is an int subclass — reject it explicitly so `true` can't pass as 1.
        if "priority" in entry and (
            isinstance(priority, bool) or not isinstance(priority, int) or not 1 <= priority <= 5
        ):
            errors.append(f"{label}: priority '{priority}' must be an integer 1-5 (FL-005)")

        for key in ("description", "user_value"):
            if key in entry and not _non_empty_str(entry[key]):
                errors.append(f"{label}: '{key}' must be a non-empty string (FL-006)")

        steps = entry.get("verification_steps")
        if "verification_steps" in entry:
            if not isinstance(steps, list) or not steps:
                errors.append(
                    f"{label}: verification_steps must be a non-empty list (FL-007)"
                )
            elif not all(_non_empty_str(step) for step in steps):
                errors.append(
                    f"{label}: every verification step must be a non-empty string (FL-007)"
                )

    return errors


def main() -> int:
    errors = lint(FEATURE_LIST)
    if errors:
        for error in errors:
            print(f"FAIL {error}")
        print(f"\n{len(errors)} violation(s) in {FEATURE_LIST.name}")
        return 1

    count = len(json.loads(FEATURE_LIST.read_text(encoding="utf-8"))["features"])
    print(f"OK feature_list.json: {count} entries, no violations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
