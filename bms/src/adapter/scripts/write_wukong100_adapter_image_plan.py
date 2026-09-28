#!/usr/bin/env python3
"""Create the canonical fail-closed wukong100 adapter image overlay plan.

The native generation producer deliberately stops at an immutable payload.
This writer is the missing consumer edge between that payload and the product
system image.  It never edits an OpenHarmony output tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


SCHEMA = "westlake.wukong100.adapter_image_plan.v1"
GENERATION_SCHEMA = "westlake.l03_a12.provider_closure.v3"
DEPLOY_SCHEMA = "westlake.l03_a12.deploy_plan.v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
BUILD_ID_RE = re.compile(r"Build ID:\s*([0-9a-fA-F]+)")
REQUIRED_GENERATION_DESTINATIONS = {
    "/system/bin/appspawn-x",
    "/system/android/lib64/libbionic_compat.so",
    "/system/android/lib64/liboh_adapter_bridge.so",
    "/system/android/lib64/liboh_android_runtime.so",
    "/system/android/lib64/libwestlake_thread_guard_registry.so",
}
CONFIG_ENTRIES = (
    (
        "appspawn_init_config",
        "framework/appspawn-x/config/appspawn_x.cfg",
        "/system/etc/init/appspawn_x.cfg",
    ),
    (
        "appspawn_sandbox_config",
        "framework/appspawn-x/config/appspawn_x_sandbox.json",
        "/system/etc/appspawn_x_sandbox.json",
    ),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def regular_file(root: Path, relative: str) -> Path:
    if relative.startswith("/") or ".." in Path(relative).parts:
        raise ValueError(f"unsafe relative source: {relative}")
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"source must be a regular non-symlink: {path}")
    resolved = path.resolve()
    resolved.relative_to(root.resolve())
    return path


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"top-level JSON object required: {path}")
    return value


def elf_build_id(path: Path, readelf: Path) -> str | None:
    if path.read_bytes()[:4] != b"\x7fELF":
        return None
    process = subprocess.run(
        [str(readelf), "--notes", "--wide", str(path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0:
        raise ValueError(f"readelf failed for {path}: {process.stderr.strip()}")
    match = BUILD_ID_RE.search(process.stdout)
    if not match:
        raise ValueError(f"ELF lacks a Build-ID: {path}")
    return match.group(1).lower()


def validate_destination(destination: str) -> None:
    if (
        not destination.startswith("/system/")
        or "//" in destination
        or ".." in Path(destination).parts
    ):
        raise ValueError(f"unsafe image destination: {destination}")


def append_systemscence_path(source: str) -> str:
    """Add only the AArch64 adapter directory to systemscence search paths."""

    section = None
    keys_seen: set[str] = set()
    output: list[str] = []
    for raw_line in source.splitlines(keepends=True):
        stripped = raw_line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1]
        if section == "systemscence" and "=" in raw_line:
            prefix, value = raw_line.split("=", 1)
            key = prefix.strip()
            if key in {
                "namespace.default.lib.paths",
                "namespace.default.asan.lib.paths",
            }:
                newline = "\n" if value.endswith("\n") else ""
                paths = value.rstrip("\n").strip().split(":")
                if "/system/android/lib64" not in paths:
                    paths.append("/system/android/lib64")
                raw_line = f"{prefix}= {':'.join(paths)}{newline}"
                keys_seen.add(key)
        output.append(raw_line)
    expected = {
        "namespace.default.lib.paths",
        "namespace.default.asan.lib.paths",
    }
    if keys_seen != expected:
        raise ValueError(
            f"systemscence namespace keys incomplete: expected={sorted(expected)} "
            f"actual={sorted(keys_seen)}"
        )
    result = "".join(output)
    if result.count("/system/android/lib64") != 2:
        raise ValueError("adapter namespace path must occur exactly twice")
    return result


def make_entry(
    *,
    role: str,
    source_scope: str,
    source: str,
    destination: str,
    source_path: Path,
    readelf: Path,
    mode: str,
    selinux_label: str,
) -> dict[str, Any]:
    validate_destination(destination)
    build_id = elf_build_id(source_path, readelf)
    if destination.endswith(".so") or destination == "/system/bin/appspawn-x":
        if build_id is None:
            raise ValueError(f"native image entry is not an ELF with Build-ID: {source}")
    return {
        "role": role,
        "source_scope": source_scope,
        "source": source,
        "destination": destination,
        "sha256": sha256_file(source_path),
        "size": source_path.stat().st_size,
        "build_id": build_id,
        "mode": mode,
        "uid": 0,
        "gid": 0,
        "selinux_label": selinux_label,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation-root", type=Path, required=True)
    parser.add_argument("--adapter-root", type=Path, required=True)
    parser.add_argument("--base-system-root", type=Path, required=True)
    parser.add_argument("--derived-root", type=Path, required=True)
    parser.add_argument("--readelf", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--dirty-manifest-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    generation_root = args.generation_root.resolve()
    adapter_root = args.adapter_root.resolve()
    base_system_root = args.base_system_root.resolve()
    derived_root = args.derived_root.resolve()
    output = args.output.absolute()
    if output.exists() or output.is_symlink():
        raise ValueError(f"refusing to replace image plan: {output}")
    if derived_root.exists() or derived_root.is_symlink():
        raise ValueError(f"refusing to reuse derived root: {derived_root}")
    if not SHA256_RE.fullmatch(args.dirty_manifest_sha256):
        raise ValueError("dirty manifest SHA-256 must be lowercase hex")
    if not args.readelf.is_file() or not os.access(args.readelf, os.X_OK):
        raise ValueError(f"readelf is not executable: {args.readelf}")
    incomplete = generation_root / "meta/INCOMPLETE"
    if incomplete.exists() or incomplete.is_symlink():
        raise ValueError(f"generation is incomplete: {incomplete}")

    generation_path = regular_file(generation_root, "meta/generation.json")
    deploy_path = regular_file(generation_root, "meta/inputs/deploy-plan.json")
    generation = load_json(generation_path)
    deploy = load_json(deploy_path)
    if generation.get("schema") != GENERATION_SCHEMA:
        raise ValueError(f"unsupported generation schema: {generation.get('schema')}")
    if deploy.get("schema") != DEPLOY_SCHEMA:
        raise ValueError(f"unsupported deploy schema: {deploy.get('schema')}")
    generation_id = generation.get("generation_id")
    if not isinstance(generation_id, str) or deploy.get("generation_id") != generation_id:
        raise ValueError("generation/deploy-plan identity mismatch")
    if generation.get("payload_complete") is not True:
        raise ValueError("generation payload_complete is not true")
    build = generation.get("build", {})
    if build.get("strict_link") is not True or build.get("relaxed_link") is not False:
        raise ValueError("generation did not pass strict-link admission")

    artifacts = generation.get("artifacts")
    deploy_entries = deploy.get("entries")
    if not isinstance(artifacts, list) or not isinstance(deploy_entries, list):
        raise ValueError("generation artifacts/deploy entries must be arrays")
    artifact_sha: dict[str, str] = {}
    for item in artifacts:
        if not isinstance(item, dict):
            raise ValueError("generation artifact must be an object")
        path = item.get("path")
        digest = item.get("sha256")
        if (
            not isinstance(path, str)
            or path in artifact_sha
            or not isinstance(digest, str)
            or not SHA256_RE.fullmatch(digest)
        ):
            raise ValueError(f"invalid or duplicate generation artifact: {item}")
        artifact_sha[path] = digest

    entries: list[dict[str, Any]] = []
    destinations: set[str] = set()
    sources: set[str] = set()
    for item in deploy_entries:
        if not isinstance(item, dict):
            raise ValueError("deploy entry must be an object")
        source = item.get("source")
        destination = item.get("destination")
        if not isinstance(source, str) or not isinstance(destination, str):
            raise ValueError(f"deploy entry lacks source/destination: {item}")
        if source in sources or destination in destinations:
            raise ValueError(f"duplicate deploy source/destination: {source} {destination}")
        sources.add(source)
        destinations.add(destination)
        source_path = regular_file(generation_root / "payload", source)
        actual_sha = sha256_file(source_path)
        if artifact_sha.get(source) != actual_sha:
            raise ValueError(
                f"generation artifact SHA mismatch: {source} "
                f"manifest={artifact_sha.get(source)} actual={actual_sha}"
            )
        label = (
            "u:object_r:appspawn_exec:s0"
            if destination == "/system/bin/appspawn-x"
            else "u:object_r:system_lib_file:s0"
        )
        entries.append(
            make_entry(
                role=f"generation:{source}",
                source_scope="generation",
                source=source,
                destination=destination,
                source_path=source_path,
                readelf=args.readelf,
                mode=item.get("mode", "0755"),
                selinux_label=label,
            )
        )
    if set(artifact_sha) != sources:
        raise ValueError(
            "deploy plan must consume every generation artifact exactly once: "
            f"artifacts={len(artifact_sha)} sources={len(sources)}"
        )
    missing_destinations = REQUIRED_GENERATION_DESTINATIONS - destinations
    if missing_destinations:
        raise ValueError(
            f"generation lacks required product destinations: {sorted(missing_destinations)}"
        )

    for role, source, destination in CONFIG_ENTRIES:
        source_path = regular_file(adapter_root, source)
        try:
            json.loads(source_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON config {source}: {exc}") from exc
        if destination in destinations:
            raise ValueError(f"duplicate config destination: {destination}")
        destinations.add(destination)
        entries.append(
            make_entry(
                role=role,
                source_scope="adapter",
                source=source,
                destination=destination,
                source_path=source_path,
                readelf=args.readelf,
                mode="0644",
                selinux_label="u:object_r:system_file:s0",
            )
        )

    namespace_source = regular_file(
        base_system_root, "etc/ld-musl-namespace-aarch64.ini"
    )
    namespace_bytes = append_systemscence_path(
        namespace_source.read_text(encoding="utf-8")
    ).encode("utf-8")
    derived_root.mkdir(parents=True)
    namespace_derived = derived_root / "ld-musl-namespace-aarch64.ini"
    namespace_derived.write_bytes(namespace_bytes)
    entries.append(
        make_entry(
            role="systemscence_namespace",
            source_scope="derived",
            source=namespace_derived.name,
            destination="/system/etc/ld-musl-namespace-aarch64.ini",
            source_path=namespace_derived,
            readelf=args.readelf,
            mode="0644",
            selinux_label="u:object_r:system_file:s0",
        )
    )

    entries.sort(key=lambda item: item["destination"])
    document = {
        "schema": SCHEMA,
        "product": "wukong100",
        "architecture": "aarch64",
        "scope": "ADAPTER_IMAGE_CLOSURE / NOT_DEVICE_VERIFIED",
        "generation_id": generation_id,
        "source_identity": {
            "canonical_adapter": "/opt/21.Game/02.unity.cardwords/adapter",
            "executor_adapter_mirror": str(adapter_root),
            "revision": args.source_revision,
            "dirty_manifest_sha256": args.dirty_manifest_sha256,
        },
        "generation_identity": {
            "root": str(generation_root),
            "generation_json_sha256": sha256_file(generation_path),
            "deploy_plan_sha256": sha256_file(deploy_path),
        },
        "base_identity": {
            "system_root": str(base_system_root),
            "namespace_source_sha256": sha256_file(namespace_source),
        },
        "required_roles": [
            "native_generation_payload",
            "appspawn_init_config",
            "appspawn_sandbox_config",
            "systemscence_namespace",
        ],
        "entry_count": len(entries),
        "entries": entries,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"IMAGE_PLAN_PASS generation={generation_id} entries={len(entries)} "
        f"output={output} sha256={sha256_file(output)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
