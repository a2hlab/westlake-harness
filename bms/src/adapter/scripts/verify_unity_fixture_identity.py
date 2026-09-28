#!/usr/bin/env python3
"""Bind a Unity fixture TSV to one generation-private identity receipt."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path, PurePosixPath


SCHEMA = "westlake.unity.generation_private_identity.v1"
REQUIRED_ROLES = {
    "main", "unity", "il2cpp", "app_native_loader", "native_loader",
    "native_helper", "musl_loader", "dlns_provider",
}


class Reject(RuntimeError):
    pass


def regular(path: Path, label: str) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise Reject(f"{label} missing: {path}: {exc}") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise Reject(f"{label} must be a regular non-symlink file: {path}")


def directory(path: Path, label: str) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise Reject(f"{label} missing: {path}: {exc}") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
        raise Reject(f"{label} must be a non-symlink directory: {path}")


def below(root: Path, relative: object, label: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise Reject(f"unsafe {label} relative path")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or any(part in ("", ".", "..") for part in pure.parts):
        raise Reject(f"unsafe {label} relative path")
    current = root
    for part in pure.parts:
        current /= part
        if current.is_symlink():
            raise Reject(f"{label} path contains symlink")
    regular(current, label)
    try:
        current.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise Reject(f"{label} escapes private root") from exc
    return current.absolute()


def load_json(path: Path, label: str) -> dict:
    regular(path, label)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Reject(f"invalid {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise Reject(f"{label} root must be an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity-receipt", required=True, type=Path)
    parser.add_argument("--fixture-manifest", required=True, type=Path)
    args = parser.parse_args()

    receipt_path = args.identity_receipt.absolute()
    receipt = load_json(receipt_path, "identity receipt")
    if receipt.get("schema") != SCHEMA or receipt.get("status") != "identity_pass":
        raise Reject("identity receipt schema/status mismatch")
    if receipt.get("device_verified") is not False or receipt.get("engine_started") is not False:
        raise Reject("identity receipt contains an invalid promoted state")
    roots = receipt.get("roots")
    if not isinstance(roots, dict):
        raise Reject("identity receipt roots missing")
    generation_root = Path(roots.get("generation", "")).absolute()
    cardwords_root = Path(roots.get("cardwords", "")).absolute()
    directory(generation_root, "generation root")
    directory(cardwords_root, "CardWords root")
    if receipt_path != generation_root / "meta/unity-identity.json":
        raise Reject("identity receipt must be GENERATION_ROOT/meta/unity-identity.json")

    allowed: set[tuple[str, str, str]] = set()
    artifacts = receipt.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise Reject("identity receipt artifacts missing")
    for item in artifacts:
        if not isinstance(item, dict):
            raise Reject("malformed identity artifact")
        root_name = item.get("root")
        if root_name == "generation":
            path = below(generation_root / "payload", item.get("path"), "generation artifact")
        elif root_name == "cardwords":
            path = below(cardwords_root, item.get("path"), "CardWords artifact")
        else:
            raise Reject("identity artifact has unknown root")
        allowed.add((str(path), item.get("sha256"), item.get("build_id")))

    regular(args.fixture_manifest, "fixture manifest")
    seen: dict[str, str] = {}
    used_paths: dict[str, str] = {}
    for raw in args.fixture_manifest.read_text(encoding="utf-8").splitlines():
        if not raw or raw.startswith("#"):
            continue
        fields = raw.split("\t")
        if len(fields) != 4:
            raise Reject("fixture manifest row must have four TSV fields")
        role, path, sha256, build_id = fields
        if role not in REQUIRED_ROLES or role in seen:
            raise Reject(f"fixture manifest role invalid or duplicate: {role}")
        absolute = str(Path(path).absolute())
        if (absolute, sha256, build_id) not in allowed:
            raise Reject(f"GENERATION_PATH_OUTSIDE_PRIVATE_ROOT role={role}")
        previous = used_paths.get(absolute)
        duplicate_loader_roles = {previous, role} == {"musl_loader", "dlns_provider"}
        if previous is not None and not duplicate_loader_roles:
            raise Reject(f"one identity artifact fills multiple roles: {previous},{role}")
        used_paths[absolute] = role
        seen[role] = absolute
    if set(seen) != REQUIRED_ROLES:
        raise Reject(f"fixture manifest roles incomplete: {sorted(REQUIRED_ROLES - set(seen))}")
    print(
        "UNITY_FIXTURE_IDENTITY_PASS "
        f"generation={receipt.get('generation_id')} roles={len(seen)}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Reject as exc:
        print(f"UNITY_FIXTURE_IDENTITY_REJECT {exc}", file=sys.stderr)
        raise SystemExit(1)
