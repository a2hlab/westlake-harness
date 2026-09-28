#!/usr/bin/env python3
"""Require two directory trees to contain the same regular-file bytes."""

from __future__ import annotations

import argparse
import hashlib
import os
import stat
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(root: Path, label: str) -> dict[str, str]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"{label} must be a non-symlink directory: {root}")
    result: dict[str, str] = {}
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        for name in dirnames:
            path = directory_path / name
            if path.is_symlink():
                raise ValueError(f"{label} contains directory symlink: {path}")
        for name in filenames:
            path = directory_path / name
            mode = path.lstat().st_mode
            if not stat.S_ISREG(mode):
                raise ValueError(f"{label} contains non-regular file: {path}")
            relative = path.relative_to(root).as_posix()
            result[relative] = sha256(path)
    if not result:
        raise ValueError(f"{label} is empty: {root}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("left")
    parser.add_argument("right")
    args = parser.parse_args()

    left = inventory(Path(args.left).absolute(), "left tree")
    right = inventory(Path(args.right).absolute(), "right tree")
    if left.keys() != right.keys():
        raise ValueError(
            "tree path mismatch: "
            f"left_only={sorted(left.keys() - right.keys())[:8]} "
            f"right_only={sorted(right.keys() - left.keys())[:8]}"
        )
    changed = [path for path in sorted(left) if left[path] != right[path]]
    if changed:
        raise ValueError(f"tree digest mismatch: {changed[:8]}")
    print(f"TREE_IDENTITY_PASS files={len(left)}")


if __name__ == "__main__":
    main()
