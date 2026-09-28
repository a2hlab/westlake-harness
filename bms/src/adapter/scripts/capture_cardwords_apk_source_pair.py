#!/usr/bin/env python3
"""Capture the fixed CardWords origin/project APK byte-equivalence receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from pathlib import Path


SCHEMA = "westlake.unity_apk_source_pair.v1"
CONTRACT = "westlake.unity_apk_binary_only.v1"
ORIGIN = Path("/opt/21.Game/artifacts/selfcontained_cardwords.apk")
PROJECT = Path("/opt/21.Game/02.unity.cardwords/adapter/frozen/product_inputs/cardwords-current/canonical/selfcontained_cardwords.apk")
EXPECTED_SIZE = 66377217
EXPECTED_SHA256 = "435f0ebbf99b5f5ae76aecb411da7684052a92ef0b6aee18d50afa6a98210626"
SHA_RE = re.compile(r"[0-9a-f]{64}")


class Reject(RuntimeError):
    pass


def regular(path: Path, label: str) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise Reject(f"{label} missing: {path}: {exc}") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise Reject(f"{label} must be a regular non-symlink file: {path}")


def digest(path: Path) -> tuple[int, str]:
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(block)
            h.update(block)
    return size, h.hexdigest()


def same_bytes(left: Path, right: Path) -> bool:
    with left.open("rb") as a, right.open("rb") as b:
        while True:
            aa = a.read(1024 * 1024)
            bb = b.read(1024 * 1024)
            if aa != bb:
                return False
            if not aa:
                return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin-apk", required=True, type=Path)
    parser.add_argument("--project-apk", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    origin = args.origin_apk.absolute()
    project = args.project_apk.absolute()
    output = args.output.absolute()
    if origin != ORIGIN or project != PROJECT:
        raise Reject("APK path is not the fixed origin/project pair")
    if output.exists() or output.is_symlink():
        raise Reject(f"refusing output reuse: {output}")
    regular(origin, "origin APK")
    regular(project, "GroundTruth project APK")
    origin_size, origin_sha = digest(origin)
    project_size, project_sha = digest(project)
    if (origin_size, project_size) != (EXPECTED_SIZE, EXPECTED_SIZE):
        raise Reject("APK size mismatch")
    if not SHA_RE.fullmatch(origin_sha) or origin_sha != EXPECTED_SHA256:
        raise Reject("origin APK SHA256 mismatch")
    if project_sha != EXPECTED_SHA256:
        raise Reject("GroundTruth project APK SHA256 mismatch")
    if not same_bytes(origin, project):
        raise Reject("origin and GroundTruth project APK bytes differ")

    receipt = {
        "schema": SCHEMA,
        "contract_id": CONTRACT,
        "status": "source_pair_pass",
        "origin": {"path": str(origin), "size": origin_size, "sha256": origin_sha},
        "project": {"path": str(project), "size": project_size, "sha256": project_sha},
        "cmp_equal": True,
        "command_argv": [str(Path(__file__).absolute()), *os.sys.argv[1:]],
        "exit_code": 0,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp.{os.getpid()}")
    temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, output)
    print(f"UNITY_APK_SOURCE_PAIR_PASS sha256={origin_sha} size={origin_size}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Reject as exc:
        print(f"UNITY_APK_SOURCE_PAIR_REJECT {exc}", file=os.sys.stderr)
        raise SystemExit(1)
