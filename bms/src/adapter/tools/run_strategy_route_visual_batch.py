#!/usr/bin/env python3
"""Run the Gemini strategy-route visual generator over a bounded atom set."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import subprocess
import sys


ROOT = Path("/opt/21.Game/02.unity.cardwords/adapter/research/atoms")
GENERATOR = Path("/opt/21.Game/02.unity.cardwords/adapter/tools/generate_strategy_route_3d.py")


def floor_number(path: Path) -> int:
    return int(path.parent.name.removeprefix("L"))


def eligible(path: Path, args: argparse.Namespace) -> bool:
    floor = floor_number(path)
    if floor < args.floor_from or floor > args.floor_to:
        return False
    if not (path / "strategy.md").exists() or not (path / "routemap.md").exists():
        return False
    if args.only_existing_html and not any((path / name).exists() for name in ("strategy-review.html", "strategy_review.html")):
        return False
    if args.exclude and f"{path.parent.name}.{path.name}" in args.exclude:
        return False
    return True


def run_one(path: Path, force: bool) -> tuple[str, int, str]:
    cmd = [sys.executable, str(GENERATOR), str(path)]
    if force:
        cmd.append("--force")
    result = subprocess.run(cmd, text=True, capture_output=True)
    output = (result.stdout + result.stderr).strip()
    return f"{path.parent.name}.{path.name}", result.returncode, output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--floor-from", type=int, default=1)
    parser.add_argument("--floor-to", type=int, default=14)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--only-existing-html", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--exclude", action="append", default=[])
    args = parser.parse_args()
    atoms = [path for path in sorted(ROOT.glob("L*/A*")) if path.is_dir() and eligible(path, args)]
    if args.limit:
        atoms = atoms[: args.limit]
    print(f"selected={len(atoms)} floors=L{args.floor_from:02d}-L{args.floor_to:02d} jobs={args.jobs}")
    if args.dry_run:
        for path in atoms:
            print(f"{path.parent.name}.{path.name} {path}")
        return 0
    failures = 0
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = {pool.submit(run_one, path, args.force): path for path in atoms}
        for future in as_completed(futures):
            atom_id, rc, output = future.result()
            print(f"[{atom_id}] rc={rc} {output}", flush=True)
            failures += int(rc != 0)
    print(f"complete={len(atoms) - failures} failed={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
