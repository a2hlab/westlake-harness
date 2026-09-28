#!/usr/bin/env python3
"""Write a deterministic absolute-path manifest for build input trees.

Regular files are hashed by content. File symlinks bind both link text and
resolved bytes. Directory symlinks bind link text and must resolve below one
of the declared roots, whose canonical files are covered separately. Repository
metadata named ``.git`` is excluded because the reviewed build never consumes it.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import stat
from pathlib import Path


# Build-system metadata and interpreter caches are not product inputs.  The
# latter may be created by a verifier between the before/after brackets and
# must never make an otherwise unchanged source tree nondeterministic.
IGNORED_DIRECTORY_NAMES = {".git", "__pycache__"}
FILE_SYMLINK_DOMAIN = b"westlake.file_symlink.v1\0"
DIRECTORY_SYMLINK_DOMAIN = b"westlake.directory_symlink.v1\0"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def entry_sha256(path: Path) -> str:
    mode = path.lstat().st_mode
    if stat.S_ISREG(mode):
        return sha256(path)
    if not stat.S_ISLNK(mode):
        raise ValueError(f"manifest entry is not a regular file or symlink: {path}")
    raw_target = os.readlink(path)
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"manifest symlink is broken: {path}: {exc}") from exc
    digest = hashlib.sha256()
    if resolved.is_file():
        digest.update(FILE_SYMLINK_DOMAIN)
        digest.update(os.fsencode(raw_target))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256(resolved)))
    elif resolved.is_dir():
        digest.update(DIRECTORY_SYMLINK_DOMAIN)
        digest.update(os.fsencode(raw_target))
    else:
        raise ValueError(f"manifest symlink resolves to a special file: {path}")
    return digest.hexdigest()


def regular_or_file_symlink(path: Path, label: str) -> None:
    mode = path.lstat().st_mode
    if stat.S_ISREG(mode):
        return
    if stat.S_ISLNK(mode) and path.is_file():
        return
    raise ValueError(f"{label} is not a regular file or file symlink: {path}")


def is_below_any(path: Path, roots: tuple[Path, ...]) -> bool:
    physical = os.fspath(path.resolve(strict=True))
    for root in roots:
        try:
            if os.path.commonpath((os.fspath(root), physical)) == os.fspath(root):
                return True
        except ValueError:
            continue
    return False


def collect(root: Path, allowed_roots: tuple[Path, ...]) -> list[Path]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"root must be a non-symlink directory: {root}")
    files: list[Path] = []
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        retained_directories: list[str] = []
        for name in dirnames:
            if name in IGNORED_DIRECTORY_NAMES:
                continue
            path = directory_path / name
            if path.is_symlink():
                try:
                    resolved = path.resolve(strict=True)
                except OSError as exc:
                    raise ValueError(f"directory symlink is broken: {path}: {exc}") from exc
                if not resolved.is_dir() or not is_below_any(resolved, allowed_roots):
                    raise ValueError(f"directory symlink escapes manifest roots: {path}")
                files.append(path.absolute())
                continue
            retained_directories.append(name)
        dirnames[:] = retained_directories
        for name in filenames:
            if name in IGNORED_DIRECTORY_NAMES:
                continue
            path = directory_path / name
            regular_or_file_symlink(path, "tree entry")
            files.append(path.absolute())
    return files


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--file", action="append", default=[])
    parser.add_argument("root", nargs="+")
    args = parser.parse_args()

    output = Path(args.output).absolute()
    if output.exists() or output.is_symlink():
        raise ValueError(f"output already exists: {output}")
    roots = tuple(Path(raw).absolute() for raw in args.root)
    for root in roots:
        if root.is_symlink() or not root.is_dir():
            raise ValueError(f"root must be a non-symlink directory: {root}")
    physical_roots = tuple(root.resolve(strict=True) for root in roots)
    files: set[Path] = set()
    for root in roots:
        files.update(collect(root, physical_roots))
    for raw in args.file:
        path = Path(raw).absolute()
        regular_or_file_symlink(path, "explicit file")
        files.add(path)
    if not files:
        raise ValueError("no files found")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        for path in sorted(files, key=os.fspath):
            stream.write(f"{entry_sha256(path)}  {path}\n")


if __name__ == "__main__":
    main()
