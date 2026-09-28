#!/usr/bin/env python3
"""Merge one conservative unit-verification readiness audit into Action status.

This tool writes only the top-level ``unit_verification`` section of each
``src/atoms/Fnxx/Ayy/STATUS.yaml`` file named by the audit.  It deliberately
cannot issue a formal Action verdict: formal verdicts belong to immutable,
validator-clean ``var/evidence/atoms/.../runs/.../manifest.json`` runs.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

import yaml


READINESS_VERDICTS = {"READY", "BLOCK", "SPEC_GAP"}


def load_mapping(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: YAML root must be a mapping")
    return data


def normalize_actions(raw_actions: Any) -> dict[str, dict[str, Any]]:
    """Accept keyed audits and generator-friendly lists without changing semantics."""
    if isinstance(raw_actions, dict) and raw_actions:
        actions = raw_actions
    elif isinstance(raw_actions, list) and raw_actions:
        actions = {}
        for index, raw_entry in enumerate(raw_actions):
            if not isinstance(raw_entry, dict):
                raise ValueError(f"actions[{index}] must be a mapping")
            action_id = raw_entry.get("action_id")
            if not isinstance(action_id, str) or "." not in action_id:
                raise ValueError(f"actions[{index}] has invalid action_id")
            if action_id in actions:
                raise ValueError(f"duplicate Action ID: {action_id}")
            entry = dict(raw_entry)
            entry.pop("action_id")
            actions[action_id] = entry
    else:
        raise ValueError("actions must be a non-empty mapping or list")
    return actions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if STATUS.yaml does not already match; do not write.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    audit_path = Path(args.audit)
    if not audit_path.is_absolute():
        audit_path = root / audit_path
    audit_path = audit_path.resolve()
    audit = load_mapping(audit_path)

    if audit.get("schema_version") != "1.0":
        raise ValueError("audit schema_version must be '1.0'")
    audit_id = str(audit.get("audit_id", "")).strip()
    audited_at = str(audit.get("audited_at", "")).strip()
    actions = normalize_actions(audit.get("actions"))
    if not audit_id or not audited_at:
        raise ValueError("audit_id and audited_at are required")
    try:
        audit_ref = str(audit_path.relative_to(root))
    except ValueError as error:
        raise ValueError("audit must live under --root") from error

    changed = 0
    for action_id, entry in sorted(actions.items()):
        if not isinstance(action_id, str) or "." not in action_id:
            raise ValueError(f"invalid Action ID: {action_id!r}")
        if not isinstance(entry, dict):
            raise ValueError(f"{action_id}: audit entry must be a mapping")
        readiness_verdict = entry.get("readiness_verdict")
        if readiness_verdict not in READINESS_VERDICTS:
            raise ValueError(
                f"{action_id}: readiness_verdict must be one of "
                f"{sorted(READINESS_VERDICTS)}"
            )
        if entry.get("formal_action_verdict") != "NOT_ISSUED":
            raise ValueError(
                f"{action_id}: this readiness tool cannot issue a formal verdict"
            )

        fn_id, action_suffix = action_id.split(".", 1)
        status_path = (
            root / "src" / "atoms" / fn_id / action_suffix / "STATUS.yaml"
        )
        status = load_mapping(status_path)
        if status.get("action_id") != action_id:
            raise ValueError(f"{status_path}: Action identity mismatch")

        unit_verification = {
            "schema_version": "1.0",
            "audit_id": audit_id,
            "audit_ref": audit_ref,
            "audited_at": audited_at,
            **entry,
        }
        if status.get("unit_verification") == unit_verification:
            continue
        changed += 1
        if not args.check:
            status["unit_verification"] = unit_verification
            status_path.write_text(
                yaml.safe_dump(status, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

    if args.check and changed:
        print(f"FAIL: {changed} Action status file(s) differ from audit")
        return 1
    verb = "checked" if args.check else "updated"
    print(f"PASS: {verb} {len(actions)} Action status file(s); changed={changed}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
