#!/usr/bin/env python3
"""python3 -m westlake_gap.close_routing <map> <new map>  -- a corpus map whose launch args carry the routing
closure (gapmap.close_routing) without rebuilding any map: every file is hard-linked from <map>, and each
gap-map.json the closure changes is written anew (never through the link), with the added names in its notes
("routing_closure"). Prints how many maps it read and how many changed. GAP-MAP.md is not rewritten."""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

from .gapmap import close_routing


def close_map(src: Path, dst: Path) -> tuple[int, int]:
    if dst.exists():
        raise SystemExit(f"{dst} exists")
    read = changed = 0
    for app in sorted(path for path in src.iterdir() if path.is_dir()):
        out = dst / app.name
        out.mkdir(parents=True)
        for item in app.iterdir():
            if item.is_dir():
                shutil.copytree(item, out / item.name, copy_function=os.link)
            else:
                os.link(item, out / item.name)
        gap, scan = out / "gap-map.json", app / "scan.json"
        if not gap.exists() or not scan.exists():
            continue
        read += 1
        data = json.loads(gap.read_text())
        args, added = close_routing(data.get("launch_args") or [], json.loads(scan.read_text()))
        if not added:
            continue
        data["launch_args"] = args
        data.setdefault("notes", {})["routing_closure"] = added
        gap.unlink()
        gap.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        changed += 1
    return read, changed


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 64
    read, changed = close_map(Path(args[0]), Path(args[1]))
    print(f"{read} maps, {changed} with libraries added to the routing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
