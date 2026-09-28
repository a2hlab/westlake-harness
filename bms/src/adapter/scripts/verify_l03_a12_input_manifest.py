#!/usr/bin/env python3
"""Verify SHA-256 manifests cover the exact L03.A12 build inputs.

Unlike ``sha256sum -c``, this gate binds the manifest to the paths the build
will actually consume. Required files must be listed, and every regular file
under each required tree must be listed. Safe directory symlinks are
identity-bound and may resolve only below the declared roots; special files and
escaping links fail closed. Repository metadata named ``.git`` is excluded
because the reviewed build never consumes it.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import stat
from pathlib import Path


LINE = re.compile(r"^([0-9a-f]{64}) ([ *])(.+)$")
# Keep the verifier's tree definition byte-for-byte aligned with the writer.
# Python bytecode caches are generated test/runtime state, not source input.
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


def lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def require_readable_file(path: Path, label: str) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise ValueError(f"{label} is missing: {path}: {exc}") from exc
    if stat.S_ISLNK(mode):
        if not path.is_file():
            raise ValueError(f"{label} symlink does not resolve to a file: {path}")
    elif not stat.S_ISREG(mode):
        raise ValueError(f"{label} is not a regular file: {path}")


def require_manifest_entry(path: Path) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise ValueError(f"manifest entry is missing: {path}: {exc}") from exc
    if stat.S_ISREG(mode):
        return
    if stat.S_ISLNK(mode):
        try:
            resolved = path.resolve(strict=True)
        except OSError as exc:
            raise ValueError(f"manifest symlink is broken: {path}: {exc}") from exc
        if resolved.is_file() or resolved.is_dir():
            return
    raise ValueError(f"manifest entry is not a regular file or symlink: {path}")


def load_manifest(path: Path) -> dict[Path, str]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"manifest must be a regular non-symlink file: {path}")
    directory = path.resolve().parent
    records: dict[Path, str] = {}
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        match = LINE.fullmatch(line)
        if match is None:
            raise ValueError(f"malformed manifest line {line_number}")
        raw = Path(match.group(3))
        candidate = raw if raw.is_absolute() else directory / raw
        absolute = lexical_absolute(candidate)
        if absolute in records:
            raise ValueError(f"duplicate manifest path: {absolute}")
        require_manifest_entry(absolute)
        actual = entry_sha256(absolute)
        expected = match.group(1)
        if actual != expected:
            raise ValueError(
                f"manifest digest mismatch: {absolute} "
                f"expected={expected} actual={actual}"
            )
        records[absolute] = expected
    if not records:
        raise ValueError("manifest is empty")
    return records


def is_below_any(path: Path, roots: tuple[Path, ...]) -> bool:
    physical = os.fspath(path.resolve(strict=True))
    for root in roots:
        try:
            if os.path.commonpath((os.fspath(root), physical)) == os.fspath(root):
                return True
        except ValueError:
            continue
    return False


def tree_files(root: Path, allowed_roots: tuple[Path, ...]) -> set[Path]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"required tree must be a non-symlink directory: {root}")
    result: set[Path] = set()
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
                    raise ValueError(f"required tree has broken directory symlink: {path}: {exc}") from exc
                if not resolved.is_dir() or not is_below_any(resolved, allowed_roots):
                    raise ValueError(f"required tree directory symlink escapes manifest roots: {path}")
                result.add(lexical_absolute(path))
                continue
            retained_directories.append(name)
        dirnames[:] = retained_directories
        for name in filenames:
            if name in IGNORED_DIRECTORY_NAMES:
                continue
            path = lexical_absolute(directory_path / name)
            require_readable_file(path, "required tree entry")
            result.add(path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("--required-file", action="append", default=[])
    parser.add_argument("--required-tree", action="append", default=[])
    args = parser.parse_args()

    manifest = lexical_absolute(Path(args.manifest))
    records = load_manifest(manifest)

    required_files = {lexical_absolute(Path(raw)) for raw in args.required_file}
    required_roots = tuple(lexical_absolute(Path(raw)) for raw in args.required_tree)
    for root in required_roots:
        if root.is_symlink() or not root.is_dir():
            raise ValueError(f"required tree must be a non-symlink directory: {root}")
    physical_roots = tuple(root.resolve(strict=True) for root in required_roots)
    required_tree_files: set[Path] = set()
    for root in required_roots:
        required_tree_files.update(tree_files(root, physical_roots))

    for path in sorted(required_files):
        require_readable_file(path, "required file")
    required = required_files | required_tree_files
    missing = sorted(required - records.keys())
    if missing:
        preview = ", ".join(str(path) for path in missing[:8])
        suffix = "" if len(missing) <= 8 else f" ... (+{len(missing) - 8})"
        raise ValueError(f"input manifest omits required paths: {preview}{suffix}")

    print(
        "INPUT_MANIFEST_PASS "
        f"entries={len(records)} required_files={len(required_files)} "
        f"tree_files={len(required_tree_files)} trees={len(args.required_tree)}"
    )


if __name__ == "__main__":
    main()
