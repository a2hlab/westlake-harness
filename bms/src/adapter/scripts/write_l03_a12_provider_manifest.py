#!/usr/bin/env python3
"""Write one self-contained L03.A12 ARM64 deploy-closure manifest.

The writer is deliberately strict: a generation is not eligible for the
provider/deploy gates unless its payload, immutable image base, deployment
plan, build log, and every provenance digest form one immutable v3 record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath
from typing import Any


SCHEMA = "westlake.l03_a12.provider_closure.v3"
DEPLOY_SCHEMA = "westlake.l03_a12.deploy_plan.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")
GENERATION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
ROLE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
MODE = re.compile(r"0[0-7]{3}")
ROLE_PATHS = {
    "backend": "adapter/libapp_native_loader.so",
    "bridge": "adapter/liboh_adapter_bridge.so",
    "native_loader": "aosp/libnativeloader.so",
    "runtime": "adapter/liboh_android_runtime.so",
    "profile": "aosp/libprofile.so",
    "unwindstack": "aosp/libunwindstack.so",
    "art": "aosp/libart.so",
    "appspawn": "bin/appspawn-x",
    "oh_service": "oh-service/libabilityms.z.so",
}
PROVENANCE_PATHS = {
    "source_manifest": "inputs/source.sha256",
    "toolchain_manifest": "inputs/toolchain.sha256",
    "sysroot_manifest": "inputs/sysroot.sha256",
    "external_source_manifest": "inputs/external-source.sha256",
    "immutable_base_manifest": "inputs/immutable-base.sha256",
    "generated_input_manifest": "generated-inputs.sha256",
    "deploy_plan": "inputs/deploy-plan.json",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def immutable_base_role(relative: str) -> str:
    """Encode an exact immutable-base path as a punctuation-safe role."""
    encoded = hashlib.sha256(relative.encode("utf-8")).hexdigest()
    return f"base:sha256:{encoded}"


def regular_file(path: Path, label: str) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise ValueError(f"{label} is missing: {path}: {exc}") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise ValueError(f"{label} must be a regular non-symlink file: {path}")


def regular_directory(path: Path, label: str) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise ValueError(f"{label} is missing: {path}: {exc}") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
        raise ValueError(f"{label} must be a non-symlink directory: {path}")


def digest(value: str, label: str) -> str:
    if SHA256.fullmatch(value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256")
    return value


def safe_relative(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    if any(character in value for character in ("\t", "\n", "\r")):
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and all(
        part not in ("", ".", "..") for part in path.parts
    )


def safe_absolute(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("/") or "\\" in value:
        return False
    if any(character in value for character in ("\t", "\n", "\r")):
        return False
    return ".." not in PurePosixPath(value).parts


def relative_below(path: Path, root: Path, label: str) -> str:
    relative = os.path.relpath(path, root).replace(os.sep, "/")
    if not safe_relative(relative):
        raise ValueError(f"{label} must be below manifest directory: {path}")
    return relative


def exact_regular_files(root: Path, label: str) -> list[str]:
    regular_directory(root, label)
    files: list[str] = []
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        for name in list(dirnames):
            path = directory_path / name
            if path.is_symlink():
                raise ValueError(f"{label} directory symlink is forbidden: {path}")
        for name in filenames:
            path = directory_path / name
            regular_file(path, f"{label} entry")
            files.append(path.relative_to(root).as_posix())
    return sorted(files)


def load_json(path: Path, label: str) -> Any:
    regular_file(path, label)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not valid UTF-8 JSON: {path}: {exc}") from exc


def validate_deployment(
    value: Any,
    generation_id: str,
    image_fingerprint: str,
    expected_interpreter: str,
    payload_paths: set[str],
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("deploy plan root must be an object")
    expected_fields = {
        "schema": DEPLOY_SCHEMA,
        "generation_id": generation_id,
        "image_fingerprint": image_fingerprint,
        "filesystem_type": "ext4",
        "expected_interpreter": expected_interpreter,
    }
    for field, expected in expected_fields.items():
        if value.get(field) != expected:
            raise ValueError(
                f"deploy plan {field} mismatch: expected={expected!r} "
                f"actual={value.get(field)!r}"
            )
    entries = value.get("entries")
    if not isinstance(entries, list):
        raise ValueError("deploy plan entries must be a list")
    sources: set[str] = set()
    destinations: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"deploy plan entry {index} must be an object")
        source = entry.get("source")
        destination = entry.get("destination")
        if not safe_relative(source):
            raise ValueError(f"deploy plan entry {index} has unsafe source: {source!r}")
        assert isinstance(source, str)
        if source in sources:
            raise ValueError(f"deploy plan source is duplicated: {source}")
        sources.add(source)
        if not safe_absolute(destination):
            raise ValueError(
                f"deploy plan entry {index} has unsafe destination: {destination!r}"
            )
        assert isinstance(destination, str)
        if destination in destinations:
            raise ValueError(f"deploy plan destination is duplicated: {destination}")
        destinations.add(destination)
        mode = entry.get("mode")
        if not isinstance(mode, str) or MODE.fullmatch(mode) is None:
            raise ValueError(f"deploy plan entry {index} has invalid mode: {mode!r}")
        for field in ("owner", "group", "selinux_label", "namespace_owner"):
            item = entry.get(field)
            if not isinstance(item, str) or not item.strip():
                raise ValueError(
                    f"deploy plan entry {index} has invalid {field}: {item!r}"
                )
    if sources != payload_paths:
        raise ValueError(
            "deploy plan payload coverage is not exact: "
            f"missing={sorted(payload_paths - sources)} "
            f"extra={sorted(sources - payload_paths)}"
        )
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation-id", required=True)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--immutable-base-root", required=True)
    parser.add_argument("--image-fingerprint", required=True)
    parser.add_argument("--expected-interpreter", required=True)
    parser.add_argument("--deploy-plan", required=True)
    parser.add_argument("--build-log", required=True)
    parser.add_argument("--source-before", required=True)
    parser.add_argument("--source-after", required=True)
    parser.add_argument("--toolchain-manifest", required=True)
    parser.add_argument("--sysroot-manifest", required=True)
    parser.add_argument("--external-source-manifest", required=True)
    parser.add_argument("--immutable-base-manifest", required=True)
    parser.add_argument("--generated-input-manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    if GENERATION_ID.fullmatch(args.generation_id) is None:
        raise ValueError("invalid generation id")
    if not isinstance(args.image_fingerprint, str) or not args.image_fingerprint.strip():
        raise ValueError("image fingerprint must be non-empty")
    if any(character in args.image_fingerprint for character in ("\n", "\r", "\t")):
        raise ValueError("image fingerprint contains control whitespace")
    if not safe_absolute(args.expected_interpreter):
        raise ValueError("expected interpreter must be a safe absolute path")

    artifact_root = Path(args.artifact_root).absolute()
    immutable_base_root = Path(args.immutable_base_root).absolute()
    build_log = Path(args.build_log).absolute()
    deploy_plan = Path(args.deploy_plan).absolute()
    output = Path(args.output).absolute()
    output.parent.mkdir(parents=True, exist_ok=True)
    regular_directory(output.parent, "manifest directory")
    if output.exists() or output.is_symlink():
        raise ValueError(f"output already exists: {output}")
    manifest_dir = output.parent

    source_before = digest(args.source_before, "source-before")
    source_after = digest(args.source_after, "source-after")
    if source_before != source_after:
        raise ValueError("source manifest changed during generation")
    toolchain_digest = digest(args.toolchain_manifest, "toolchain-manifest")
    sysroot_digest = digest(args.sysroot_manifest, "sysroot-manifest")
    external_source_digest = digest(
        args.external_source_manifest, "external-source-manifest"
    )
    immutable_base_digest = digest(
        args.immutable_base_manifest, "immutable-base-manifest"
    )
    generated_input_digest = digest(
        args.generated_input_manifest, "generated-input-manifest"
    )
    provenance_expected = {
        "source_manifest": source_after,
        "toolchain_manifest": toolchain_digest,
        "sysroot_manifest": sysroot_digest,
        "external_source_manifest": external_source_digest,
        "immutable_base_manifest": immutable_base_digest,
        "generated_input_manifest": generated_input_digest,
    }
    provenance_files: dict[str, dict[str, str]] = {}
    for name, relative in PROVENANCE_PATHS.items():
        path = manifest_dir.joinpath(*PurePosixPath(relative).parts)
        regular_file(path, f"provenance file {name}")
        actual = sha256(path)
        expected = actual if name == "deploy_plan" else provenance_expected[name]
        if actual != expected:
            raise ValueError(
                f"provenance file digest mismatch: name={name} "
                f"expected={expected} actual={actual}"
            )
        provenance_files[name] = {
            "path": relative,
            "sha256": actual,
        }

    deploy_plan_relative = relative_below(deploy_plan, manifest_dir, "deploy plan")
    if deploy_plan_relative != PROVENANCE_PATHS["deploy_plan"]:
        raise ValueError(
            "deploy plan must use the self-contained generation path: "
            f"{PROVENANCE_PATHS['deploy_plan']}"
        )

    payload_actual = set(exact_regular_files(artifact_root, "payload root"))
    forbidden_payload = {"aosp/libart_runtime_stubs.so"}
    if payload_actual & forbidden_payload:
        raise ValueError(
            "payload contains forbidden broad runtime stubs: "
            f"paths={sorted(payload_actual & forbidden_payload)}"
        )
    payload_required = set(ROLE_PATHS.values())
    if not payload_required.issubset(payload_actual):
        raise ValueError(
            "payload omits required artifacts: "
            f"missing={sorted(payload_required - payload_actual)}"
        )

    artifacts = []
    roles: set[str] = set()
    for role, relative in ROLE_PATHS.items():
        path = artifact_root / relative
        regular_file(path, role)
        artifacts.append({"role": role, "path": relative, "sha256": sha256(path)})
        roles.add(role)
    for relative in sorted(payload_actual - payload_required):
        parts = PurePosixPath(relative).parts
        if (
            len(parts) != 2
            or parts[0] not in {"aosp", "adapter", "oh-service"}
            or not parts[1].startswith("lib")
            or not (parts[1].endswith(".so") or parts[1].endswith(".z.so"))
        ):
            raise ValueError(f"unsupported extra payload artifact: {relative}")
        role = f"companion:{parts[0]}:{parts[1]}"
        if ROLE.fullmatch(role) is None or role in roles:
            raise ValueError(f"extra payload cannot form a unique role: {relative}")
        path = artifact_root / relative
        regular_file(path, role)
        artifacts.append({"role": role, "path": relative, "sha256": sha256(path)})
        roles.add(role)

    base_relative = relative_below(
        immutable_base_root, manifest_dir, "immutable base root"
    )
    base_files = exact_regular_files(immutable_base_root, "immutable base root")
    if not base_files:
        raise ValueError("immutable base root is empty")
    interpreter_relative = args.expected_interpreter.lstrip("/")
    if interpreter_relative not in base_files:
        raise ValueError(
            "immutable base does not contain the expected interpreter: "
            f"{interpreter_relative}"
        )
    base_artifacts = []
    for relative in base_files:
        role = (
            "loader"
            if relative == interpreter_relative
            else immutable_base_role(relative)
        )
        if ROLE.fullmatch(role) is None:
            raise ValueError(f"immutable base path cannot form a valid role: {relative}")
        path = immutable_base_root / relative
        base_artifacts.append(
            {
                "role": role,
                "path": relative,
                "deploy_path": f"/{relative}",
                "sha256": sha256(path),
            }
        )

    deployment = validate_deployment(
        load_json(deploy_plan, "deploy plan"),
        args.generation_id,
        args.image_fingerprint,
        args.expected_interpreter,
        payload_actual,
    )
    regular_file(build_log, "build log")
    build_log_relative = relative_below(build_log, manifest_dir, "build log")

    manifest = {
        "schema": SCHEMA,
        "generation_id": args.generation_id,
        "architecture": "aarch64",
        "payload_complete": True,
        "closure": {
            "provider_subgraph_scope": "payload",
            "deploy_closure_scope": "payload+immutable_base",
            "expected_interpreter": args.expected_interpreter,
        },
        "immutable_base": {
            "root": base_relative,
            "image_fingerprint": args.image_fingerprint,
            "artifacts": base_artifacts,
        },
        "deployment": deployment,
        "provenance_files": provenance_files,
        "inputs": {
            "source_before_sha256": source_before,
            "source_after_sha256": source_after,
            "toolchain_manifest_sha256": toolchain_digest,
            "sysroot_manifest_sha256": sysroot_digest,
            "external_source_manifest_sha256": external_source_digest,
            "immutable_base_manifest_sha256": immutable_base_digest,
            "generated_input_manifest_sha256": generated_input_digest,
            "deploy_plan_sha256": sha256(deploy_plan),
        },
        "build": {
            "strict_link": True,
            "relaxed_link": False,
            "log": build_log_relative,
            "sha256": sha256(build_log),
        },
        "artifacts": artifacts,
    }
    with output.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main()
