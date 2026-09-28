#!/usr/bin/env python3
"""Fail-closed validator for an Fn07 D00 installer/BMS generation.

The validator is intentionally read-only.  It rejects loose binaries and old
packages whose source receipt cannot prove that both sides were built from the
current Service metadata projection inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REQUIRED_SOURCES = (
    "src/adapter/framework/package-manager/jni/apk_manifest_parser.cpp",
    "src/adapter/framework/package-manager/jni/apk_manifest_parser.h",
    "src/adapter/framework/package-manager/jni/oh_adapter_install_apk_c_entry.cpp",
    "src/adapter/ohos_patches/fn07/service_metadata_projection.patch",
    "src/adapter/restore_after_sync.sh",
)
REQUIRED_ARTIFACTS = {
    "libapk_installer.so": "/system/lib64/libapk_installer.so",
    "libbms.z.so": "/system/lib64/libbms.z.so",
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def regular(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} must be a regular non-symlink file: {path}")


def load_receipt(path: Path) -> dict[str, str]:
    regular(path, "source receipt")
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != "bridge.fn07.d00.source-receipt.v1":
        raise ValueError("source receipt schema mismatch")
    entries = document.get("sources")
    if not isinstance(entries, list):
        raise ValueError("source receipt sources must be a list")
    result: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("source receipt entry must be an object")
        relative = entry.get("path")
        sha256 = entry.get("sha256")
        if (
            not isinstance(relative, str)
            or relative.startswith("/")
            or ".." in Path(relative).parts
            or not isinstance(sha256, str)
            or len(sha256) != 64
        ):
            raise ValueError(f"invalid source receipt entry: {entry!r}")
        if relative in result:
            raise ValueError(f"duplicate source receipt path: {relative}")
        result[relative] = sha256
    return result


def elf_identity(path: Path) -> str:
    completed = subprocess.run(
        ["file", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    identity = completed.stdout.strip()
    if "ELF 64-bit" not in identity or "ARM aarch64" not in identity:
        raise ValueError(f"artifact is not AArch64 ELF64: {identity}")
    return identity


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("generation_root", type=Path)
    args = parser.parse_args()

    generation = args.generation_root.resolve()
    if not generation.is_dir() or generation.is_symlink():
        raise ValueError(f"generation root must be a real directory: {generation}")
    if ROOT not in generation.parents:
        raise ValueError(f"generation escaped /opt/Bridge project: {generation}")

    receipt_path = generation / "meta" / "fn07-source-receipt.json"
    receipt = load_receipt(receipt_path)
    source_results = []
    for relative in REQUIRED_SOURCES:
        source = ROOT / relative
        regular(source, "live source")
        actual = digest(source)
        recorded = receipt.get(relative)
        if recorded != actual:
            raise ValueError(
                f"source receipt mismatch for {relative}: "
                f"recorded={recorded!r} live={actual}"
            )
        source_results.append({"path": relative, "sha256": actual})

    artifacts = []
    for name, destination in REQUIRED_ARTIFACTS.items():
        artifact = generation / "artifacts" / name
        regular(artifact, "artifact")
        artifacts.append(
            {
                "name": name,
                "source": str(artifact.relative_to(ROOT)),
                "destination": destination,
                "sha256": digest(artifact),
                "identity": elf_identity(artifact),
            }
        )

    generation_meta = generation / "meta" / "generation.json"
    regular(generation_meta, "generation metadata")
    metadata = json.loads(generation_meta.read_text(encoding="utf-8"))
    generation_id = metadata.get("generation_id")
    if not isinstance(generation_id, str) or not generation_id.startswith(
        "fn07-d00-"
    ):
        raise ValueError("generation_id must start with fn07-d00-")
    if metadata.get("status") != "build_pass":
        raise ValueError("generation metadata status must be build_pass")
    if metadata.get("paired_build") is not True:
        raise ValueError("generation metadata must declare paired_build=true")

    output = {
        "artifacts": artifacts,
        "generation_id": generation_id,
        "generation_root": str(generation.relative_to(ROOT)),
        "schema": "bridge.fn07.d00.preflight-result.v1",
        "sources": source_results,
        "status": "PASS",
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"FN07_D00_GENERATION_REJECTED: {error}", file=sys.stderr)
        raise SystemExit(1)
