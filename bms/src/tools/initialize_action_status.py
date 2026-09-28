#!/usr/bin/env python3
"""Create the per-Action code-status source without overwriting existing state."""

from __future__ import annotations

from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = PROJECT_ROOT / "spec" / "atoms"
STATUS_ROOT = PROJECT_ROOT / "src" / "atoms"


def main() -> int:
    atom_paths = sorted(SPEC_ROOT.glob("Fn*/A*/atom.yaml"))
    if len(atom_paths) != 143:
        raise SystemExit(f"expected 143 Actions, found {len(atom_paths)}")

    created = 0
    for atom_path in atom_paths:
        atom = yaml.safe_load(atom_path.read_text(encoding="utf-8"))
        action_id = atom["atom_id"]
        fn_id, action_suffix = action_id.split(".")
        status_path = STATUS_ROOT / fn_id / action_suffix / "STATUS.yaml"
        if status_path.exists():
            continue
        status_path.parent.mkdir(parents=True, exist_ok=True)
        status_path.write_text(
            "\n".join(
                [
                    "schema_version: '1.0'",
                    f"action_id: {action_id}",
                    "code:",
                    "  status: SOURCE_UNMAPPED",
                    "  goals: []",
                    "  summary: 尚未建立本 Action 到实现源码的可复核映射。",
                    "  code_refs: []",
                    "  evidence_refs: []",
                    "  observed_at: null",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        created += 1

    print(f"Action status initialized: created={created}, total={len(atom_paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
