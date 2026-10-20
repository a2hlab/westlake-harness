#!/usr/bin/env python3
"""Replay a private raw index from its published root alias, without overrides."""
import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath


def check(index):
    raw = index.read_bytes()
    data = json.loads(raw)
    alias = data["private_root"]
    if not isinstance(alias, str) or not alias.startswith("$HOME/"):
        raise ValueError("private_root must use the explicit $HOME/ alias")
    relative = PurePosixPath(alias[6:])
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError("unsafe private_root")
    root = Path.home().joinpath(*relative.parts).resolve(strict=True)
    rows = data["files"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("files must be nonempty")
    seen, failures = set(), []
    for row in rows:
        name = row["path"]
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or not path.parts or name in seen:
            raise ValueError("unsafe or duplicate member path")
        seen.add(name)
        if not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
            raise ValueError("invalid SHA256")
        if type(row["bytes"]) is not int or row["bytes"] < 0:
            raise ValueError("invalid size")
        try:
            target = root.joinpath(*path.parts).resolve(strict=True)
            target.relative_to(root)
            actual = target.read_bytes()
            digest = hashlib.sha256(actual).hexdigest()
            if len(actual) != row["bytes"] or digest != row["sha256"]:
                failures.append({"path": name, "reason": "SHA_OR_SIZE_MISMATCH"})
        except (OSError, ValueError):
            failures.append({"path": name, "reason": "UNREADABLE_OR_OUTSIDE_ROOT"})
    return {
        "status": "PASS" if not failures else "FAIL",
        "index_sha256": hashlib.sha256(raw).hexdigest(),
        "private_root": alias,
        "checked": len(rows),
        "failures": failures,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    args = parser.parse_args()
    try:
        result = check(args.index)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {"status": "FAIL", "reason": type(exc).__name__}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
