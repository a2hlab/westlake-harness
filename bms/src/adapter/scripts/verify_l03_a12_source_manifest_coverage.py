#!/usr/bin/env python3
"""Require exact source-manifest coverage for generation-owned inputs."""

import argparse
import hashlib
import re
from pathlib import Path


LINE = re.compile(r"^([0-9a-f]{64}) ([ *])(.+)$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("required", nargs="+")
    args = parser.parse_args()

    manifest = Path(args.manifest)
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError(f"manifest must be a regular non-symlink: {manifest}")
    manifest_dir = manifest.resolve().parent

    records = {}
    for line_number, line in enumerate(
        manifest.read_text(encoding="utf-8").splitlines(), start=1
    ):
        match = LINE.fullmatch(line)
        if match is None:
            raise ValueError(f"malformed sha256 manifest line {line_number}")
        raw_path = Path(match.group(3))
        path = raw_path if raw_path.is_absolute() else manifest_dir / raw_path
        resolved = path.resolve(strict=True)
        if resolved in records:
            raise ValueError(f"duplicate manifest path: {resolved}")
        records[resolved] = match.group(1)

    for raw_required in args.required:
        required = Path(raw_required)
        if required.is_symlink() or not required.is_file():
            raise ValueError(f"required source is missing or a symlink: {required}")
        resolved = required.resolve(strict=True)
        recorded = records.get(resolved)
        if recorded is None:
            raise ValueError(f"source manifest omits required input: {resolved}")
        actual = sha256(resolved)
        if actual != recorded:
            raise ValueError(
                f"source manifest digest mismatch: {resolved} "
                f"expected={recorded} actual={actual}"
            )

    print(f"SOURCE_COVERAGE_PASS files={len(args.required)}")


if __name__ == "__main__":
    main()
