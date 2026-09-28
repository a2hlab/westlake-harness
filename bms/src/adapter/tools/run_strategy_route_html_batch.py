#!/usr/bin/env python3
"""Build missing strategy pages or inject visuals into existing pages without replacing decisions."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


ROOT = Path("/opt/21.Game/02.unity.cardwords/adapter/research/atoms")
BUILD = Path("/opt/21.Game/02.unity.cardwords/adapter/tools/build_strategy_review_html.py")
INJECT = Path("/opt/21.Game/02.unity.cardwords/adapter/tools/inject_strategy_route_visual.py")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--floor-from", type=int, default=1)
    parser.add_argument("--floor-to", type=int, default=14)
    parser.add_argument("--exclude", action="append", default=[])
    args = parser.parse_args()
    failures = []
    completed = 0
    for atom in sorted(ROOT.glob("L*/A*")):
        if not atom.is_dir() or not args.floor_from <= int(atom.parent.name[1:]) <= args.floor_to:
            continue
        atom_id = f"{atom.parent.name}.{atom.name}"
        if atom_id in args.exclude or not (atom / "strategy.md").exists() or not (atom / "routemap.md").exists():
            continue
        if not (atom / "strategy-route-3d.jpg").exists() and not (atom / "strategy-route-3d.png").exists():
            failures.append((atom_id, "missing image"))
            continue
        existing = (atom / "strategy-review.html").exists() or (atom / "strategy_review.html").exists()
        cmd = [sys.executable, str(INJECT if existing else BUILD), str(atom)]
        result = subprocess.run(cmd, text=True, capture_output=True)
        if result.returncode:
            failures.append((atom_id, (result.stdout + result.stderr).strip()))
        else:
            completed += 1
            print(result.stdout.strip())
    print(f"complete={completed} failed={len(failures)}")
    for atom_id, reason in failures:
        print(f"FAIL {atom_id} {reason}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
