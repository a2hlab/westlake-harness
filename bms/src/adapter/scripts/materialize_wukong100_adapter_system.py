#!/usr/bin/env python3
"""Overlay one canonical validated adapter image plan into isolated staging."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any


SCHEMA = "westlake.wukong100.adapter_image_plan.v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("image plan must be a JSON object")
    return value


def regular_source(root: Path, relative: str) -> Path:
    if relative.startswith("/") or ".." in Path(relative).parts:
        raise ValueError(f"unsafe source path: {relative}")
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"source must be a regular non-symlink: {path}")
    path.resolve().relative_to(root.resolve())
    return path


def safe_destination(staging: Path, destination: str) -> Path:
    if not destination.startswith("/system/") or ".." in Path(destination).parts:
        raise ValueError(f"unsafe destination: {destination}")
    relative = destination.removeprefix("/system/")
    path = staging / relative
    staging_resolved = staging.resolve()
    current = staging
    for component in Path(relative).parts[:-1]:
        current = current / component
        if current.is_symlink():
            raise ValueError(f"destination parent is a symlink: {current}")
        if current.exists() and not current.is_dir():
            raise ValueError(f"destination parent is not a directory: {current}")
        if current.exists():
            current.resolve().relative_to(staging_resolved)
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--generation-root", type=Path, required=True)
    parser.add_argument("--adapter-root", type=Path, required=True)
    parser.add_argument("--derived-root", type=Path, required=True)
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    plan = load_json(args.plan)
    if plan.get("schema") != SCHEMA:
        raise ValueError(f"unsupported image plan schema: {plan.get('schema')}")
    staging = args.staging_root.resolve()
    if not staging.is_dir() or staging.is_symlink():
        raise ValueError(f"staging root must already be an isolated directory: {staging}")
    receipt = args.receipt.absolute()
    if receipt.exists() or receipt.is_symlink():
        raise ValueError(f"refusing to replace receipt: {receipt}")
    roots = {
        "generation": args.generation_root.resolve() / "payload",
        "adapter": args.adapter_root.resolve(),
        "derived": args.derived_root.resolve(),
    }

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in plan.get("entries", []):
        scope = entry.get("source_scope")
        source = entry.get("source")
        destination = entry.get("destination")
        if scope not in roots or not isinstance(source, str) or not isinstance(destination, str):
            raise ValueError(f"invalid image-plan entry: {entry}")
        if destination in seen:
            raise ValueError(f"duplicate destination: {destination}")
        seen.add(destination)
        source_path = regular_source(roots[scope], source)
        source_sha = sha256_file(source_path)
        if source_sha != entry.get("sha256") or source_path.stat().st_size != entry.get("size"):
            raise ValueError(f"source identity drift: {scope}:{source}")
        destination_path = safe_destination(staging, destination)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        if destination_path.is_symlink() or (
            destination_path.exists() and not destination_path.is_file()
        ):
            raise ValueError(f"unsafe existing destination: {destination_path}")
        shutil.copyfile(source_path, destination_path)
        os.chmod(destination_path, int(entry["mode"], 8))
        destination_sha = sha256_file(destination_path)
        if destination_sha != source_sha:
            raise ValueError(f"post-copy SHA mismatch: {destination}")
        rows.append(
            {
                "destination": destination,
                "source_scope": scope,
                "source": source,
                "sha256": destination_sha,
                "size": destination_path.stat().st_size,
                "mode": entry["mode"],
            }
        )
    if len(rows) != plan.get("entry_count"):
        raise ValueError(
            f"entry count mismatch plan={plan.get('entry_count')} materialized={len(rows)}"
        )
    document = {
        "schema": "westlake.wukong100.adapter_system_materialization.v1",
        "scope": "ISOLATED_STAGING / NOT_IMAGE_OR_DEVICE_VERIFIED",
        "generation_id": plan["generation_id"],
        "image_plan_path": str(args.plan.absolute()),
        "image_plan_sha256": sha256_file(args.plan),
        "staging_root": str(staging),
        "entry_count": len(rows),
        "entries": rows,
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"MATERIALIZATION_PASS generation={plan['generation_id']} entries={len(rows)} "
        f"receipt={receipt} sha256={sha256_file(receipt)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
