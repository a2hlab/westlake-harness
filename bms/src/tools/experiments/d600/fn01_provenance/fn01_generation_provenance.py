#!/usr/bin/env python3
"""Fn01 host/target/deployment generation provenance producer and gate.

This tool deliberately proves byte identity only.  A successful provenance
gate never means that an Action's Android-visible behavior passed on a device.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


CONFIG_SCHEMA = "bridge.fn01.generation-config.v1"
BUILD_SCHEMA = "bridge.fn01.generation-build-receipt.v1"
DEVICE_SCHEMA = "bridge.fn01.device-generation-receipt.v1"
GATE_SCHEMA = "bridge.fn01.generation-gate-report.v1"
IDENTITY_SCHEMA = "bridge.fn01.generation-identity.v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
BOOT_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
ROLE_RE = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
ACTION_RE = re.compile(r"^Fn[0-9]{2}\.A[0-9]{2}$")


class ProvenanceError(RuntimeError):
    """Fail-closed provenance rejection."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProvenanceError(f"cannot read JSON {path}: {exc}") from exc


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json_bytes(value))


def require_dict(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProvenanceError(f"{where} must be an object")
    return value


def require_list(value: Any, where: str) -> list[Any]:
    if not isinstance(value, list):
        raise ProvenanceError(f"{where} must be an array")
    return value


def require_str(value: Any, where: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str) or (nonempty and not value.strip()):
        raise ProvenanceError(f"{where} must be a non-empty string")
    return value


def require_bool(value: Any, where: str) -> bool:
    if not isinstance(value, bool):
        raise ProvenanceError(f"{where} must be a boolean")
    return value


def require_exact_keys(
    value: Mapping[str, Any],
    where: str,
    required: set[str],
    optional: set[str] | None = None,
) -> None:
    optional = optional or set()
    missing = required - set(value)
    extra = set(value) - required - optional
    if missing:
        raise ProvenanceError(f"{where} missing keys: {sorted(missing)}")
    if extra:
        raise ProvenanceError(f"{where} has unsupported keys: {sorted(extra)}")


def resolve_under(root: Path, raw: str, where: str, *, must_exist: bool = True) -> Path:
    text = require_str(raw, where)
    candidate = Path(text)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve(strict=False)
    root_resolved = root.resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise ProvenanceError(f"{where} escapes repository root: {raw}")
    if must_exist and not resolved.exists():
        raise ProvenanceError(f"{where} does not exist: {raw}")
    return resolved


def repo_relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def file_entry(root: Path, path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise ProvenanceError(f"symlink is not admitted to source closure: {path}")
    if not path.is_file():
        raise ProvenanceError(f"not a regular file: {path}")
    return {
        "path": repo_relative(root, path),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def expand_source_manifest(
    root: Path,
    source_paths: Sequence[Any],
    source_exclude_paths: Sequence[Any] | None = None,
) -> dict[str, Any]:
    if not source_paths:
        raise ProvenanceError("source_paths must not be empty")
    excluded: list[Path] = []
    for index, raw in enumerate(source_exclude_paths or []):
        excluded.append(
            resolve_under(
                root,
                require_str(raw, f"source_exclude_paths[{index}]"),
                f"source_exclude_paths[{index}]",
            )
        )

    def is_excluded(candidate: Path) -> bool:
        resolved = candidate.resolve()
        return any(
            resolved == exclude or exclude in resolved.parents for exclude in excluded
        )

    selected: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(source_paths):
        path = resolve_under(root, require_str(raw, f"source_paths[{index}]"), f"source_paths[{index}]")
        if path.is_symlink():
            raise ProvenanceError(f"source path is a symlink: {raw}")
        paths: Iterable[Path]
        if path.is_file():
            paths = (path,)
        elif path.is_dir():
            paths = (
                candidate
                for candidate in sorted(path.rglob("*"))
                if (candidate.is_file() or candidate.is_symlink())
                and not is_excluded(candidate)
            )
        else:
            raise ProvenanceError(f"unsupported source path: {raw}")
        for candidate in paths:
            entry = file_entry(root, candidate)
            selected[entry["path"]] = entry
    entries = [selected[key] for key in sorted(selected)]
    if not entries:
        raise ProvenanceError("expanded source manifest is empty")
    return {
        "entries": entries,
        "manifest_sha256": sha256_bytes(json_bytes(entries)),
    }


def validate_command(raw: Any, where: str) -> list[str]:
    command = require_list(raw, where)
    if not command:
        raise ProvenanceError(f"{where} must not be empty")
    return [require_str(item, f"{where}[{index}]") for index, item in enumerate(command)]


def validate_env(raw: Any, where: str) -> dict[str, str]:
    value = require_dict(raw, where)
    result: dict[str, str] = {}
    for key, item in value.items():
        name = require_str(key, f"{where}.key")
        if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", name):
            raise ProvenanceError(f"{where} invalid environment name: {name}")
        result[name] = require_str(item, f"{where}.{name}", nonempty=False)
    return result


def validate_config(config: Any, root: Path) -> dict[str, Any]:
    value = require_dict(config, "config")
    require_exact_keys(
        value,
        "config",
        {
            "schema_version",
            "action_id",
            "target",
            "source_paths",
            "builder_identity_probes",
            "stages",
            "artifacts",
        },
        {"source_exclude_paths"},
    )
    if value["schema_version"] != CONFIG_SCHEMA:
        raise ProvenanceError(f"unsupported config schema: {value['schema_version']}")
    action_id = require_str(value["action_id"], "config.action_id")
    if not ACTION_RE.fullmatch(action_id):
        raise ProvenanceError(f"invalid Action ID: {action_id}")

    target = require_dict(value["target"], "config.target")
    require_exact_keys(target, "config.target", {"os", "version", "arch"})
    for key in ("os", "version", "arch"):
        require_str(target[key], f"config.target.{key}")

    source_paths = require_list(value["source_paths"], "config.source_paths")
    for index, raw in enumerate(source_paths):
        resolve_under(root, require_str(raw, f"config.source_paths[{index}]"), f"config.source_paths[{index}]")
    source_excludes = require_list(
        value.get("source_exclude_paths", []), "config.source_exclude_paths"
    )
    for index, raw in enumerate(source_excludes):
        resolve_under(
            root,
            require_str(raw, f"config.source_exclude_paths[{index}]"),
            f"config.source_exclude_paths[{index}]",
        )

    probes = require_list(
        value["builder_identity_probes"], "config.builder_identity_probes"
    )
    probe_names: set[str] = set()
    for index, raw in enumerate(probes):
        probe = require_dict(raw, f"config.builder_identity_probes[{index}]")
        require_exact_keys(
            probe,
            f"config.builder_identity_probes[{index}]",
            {"name", "command"},
            {"cwd", "env"},
        )
        name = require_str(probe["name"], f"config.builder_identity_probes[{index}].name")
        if not ROLE_RE.fullmatch(name) or name in probe_names:
            raise ProvenanceError(f"invalid or duplicate builder probe name: {name}")
        probe_names.add(name)
        validate_command(probe["command"], f"config.builder_identity_probes[{index}].command")
        if "cwd" in probe:
            resolve_under(root, probe["cwd"], f"config.builder_identity_probes[{index}].cwd")
        if "env" in probe:
            validate_env(probe["env"], f"config.builder_identity_probes[{index}].env")
    if not probes:
        raise ProvenanceError("at least one builder identity probe is required")

    stages = require_list(value["stages"], "config.stages")
    stage_names: set[str] = set()
    scopes: set[str] = set()
    for index, raw in enumerate(stages):
        stage = require_dict(raw, f"config.stages[{index}]")
        require_exact_keys(
            stage,
            f"config.stages[{index}]",
            {"name", "scope", "command"},
            {"cwd", "env"},
        )
        name = require_str(stage["name"], f"config.stages[{index}].name")
        if not ROLE_RE.fullmatch(name) or name in stage_names:
            raise ProvenanceError(f"invalid or duplicate stage name: {name}")
        stage_names.add(name)
        scope = require_str(stage["scope"], f"config.stages[{index}].scope")
        if scope not in {"host", "target"}:
            raise ProvenanceError(f"unsupported stage scope: {scope}")
        scopes.add(scope)
        validate_command(stage["command"], f"config.stages[{index}].command")
        if "cwd" in stage:
            resolve_under(root, stage["cwd"], f"config.stages[{index}].cwd")
        if "env" in stage:
            validate_env(stage["env"], f"config.stages[{index}].env")
    if scopes != {"host", "target"}:
        raise ProvenanceError("config must contain at least one host and one target stage")

    artifacts = require_list(value["artifacts"], "config.artifacts")
    roles: set[str] = set()
    for index, raw in enumerate(artifacts):
        artifact = require_dict(raw, f"config.artifacts[{index}]")
        require_exact_keys(
            artifact,
            f"config.artifacts[{index}]",
            {"role", "kind", "local_path", "device_path", "producer_stage"},
        )
        role = require_str(artifact["role"], f"config.artifacts[{index}].role")
        if not ROLE_RE.fullmatch(role) or role in roles:
            raise ProvenanceError(f"invalid or duplicate artifact role: {role}")
        roles.add(role)
        kind = require_str(artifact["kind"], f"config.artifacts[{index}].kind")
        if kind not in {"elf", "jar", "art", "file"}:
            raise ProvenanceError(f"unsupported artifact kind for {role}: {kind}")
        resolve_under(
            root,
            require_str(artifact["local_path"], f"config.artifacts[{index}].local_path"),
            f"config.artifacts[{index}].local_path",
            must_exist=False,
        )
        device_path = require_str(
            artifact["device_path"], f"config.artifacts[{index}].device_path"
        )
        if not device_path.startswith("/") or ".." in Path(device_path).parts:
            raise ProvenanceError(f"invalid device path for {role}: {device_path}")
        producer = require_str(
            artifact["producer_stage"], f"config.artifacts[{index}].producer_stage"
        )
        if producer not in stage_names:
            raise ProvenanceError(
                f"artifact {role} references unknown producer stage: {producer}"
            )
    if not artifacts:
        raise ProvenanceError("at least one target artifact is required")
    return value


def run_command(
    command: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str] | None = None,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    try:
        return subprocess.run(
            list(command),
            cwd=cwd,
            env=merged,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProvenanceError(f"command could not run: {shlex.join(command)}: {exc}") from exc


def command_record(
    command: Sequence[str],
    result: subprocess.CompletedProcess[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    log_path: Path | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    output = result.stdout or ""
    record: dict[str, Any] = {
        "command": list(command),
        "cwd": repo_relative(root, cwd) if root else str(cwd),
        "env": dict(sorted(env.items())),
        "rc": result.returncode,
        "stdout_sha256": sha256_bytes(output.encode("utf-8")),
        "stdout_bytes": len(output.encode("utf-8")),
    }
    if log_path is not None:
        record["log_path"] = repo_relative(root, log_path) if root else str(log_path)
        record["log_sha256"] = sha256_file(log_path)
    return record


def local_builder_identity(root: Path) -> dict[str, Any]:
    python_path = Path(sys.executable).resolve()
    return {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": {
            "path": str(python_path),
            "version": platform.python_version(),
            "sha256": sha256_file(python_path),
        },
        "repository_root": str(root.resolve()),
    }


def artifact_identity(root: Path, raw: Mapping[str, Any]) -> dict[str, Any]:
    role = str(raw["role"])
    path = resolve_under(root, str(raw["local_path"]), f"artifact {role}.local_path")
    if path.is_symlink() or not path.is_file():
        raise ProvenanceError(f"artifact {role} is not an admitted regular file: {path}")
    identity: dict[str, Any] = {
        "role": role,
        "kind": raw["kind"],
        "local_path": repo_relative(root, path),
        "device_path": raw["device_path"],
        "producer_stage": raw["producer_stage"],
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }
    if raw["kind"] == "elf":
        file_tool = shutil.which("file")
        if not file_tool:
            raise ProvenanceError("file tool is required for ELF artifact identity")
        result = run_command([file_tool, str(path)], cwd=root)
        if result.returncode != 0 or "ELF 64-bit" not in result.stdout:
            raise ProvenanceError(f"artifact {role} is not an ELF64 file: {result.stdout}")
        identity["file_identity"] = result.stdout.strip()
        readelf = shutil.which("readelf")
        if readelf:
            note = run_command([readelf, "-n", str(path)], cwd=root)
            if note.returncode == 0:
                match = re.search(r"Build ID:\s*([0-9a-fA-F]+)", note.stdout)
                identity["elf_build_id"] = match.group(1).lower() if match else None
    return identity


def seal_artifact(
    root: Path, run_dir: Path, raw: Mapping[str, Any]
) -> dict[str, Any]:
    role = str(raw["role"])
    origin = resolve_under(root, str(raw["local_path"]), f"artifact {role}.local_path")
    destination = run_dir / "artifacts" / role / origin.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(origin, destination)
    if sha256_file(origin) != sha256_file(destination):
        raise ProvenanceError(f"artifact copy hash mismatch: {role}")
    sealed_raw = dict(raw)
    sealed_raw["local_path"] = repo_relative(root, destination)
    identity = artifact_identity(root, sealed_raw)
    identity["origin_path"] = repo_relative(root, origin)
    identity["sealed"] = True
    return identity


def write_hash_manifest(root: Path, run_dir: Path, output: Path) -> None:
    admitted: list[Path] = []
    for directory in ("inputs", "builder", "logs", "artifacts"):
        candidate = run_dir / directory
        if candidate.is_dir():
            admitted.extend(path for path in candidate.rglob("*") if path.is_file())
    build_receipt = run_dir / "build-receipt.json"
    if build_receipt.is_file():
        admitted.append(build_receipt)
    lines = [
        f"{sha256_file(path)}  {repo_relative(run_dir, path)}"
        for path in sorted(set(admitted))
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_hash_manifest(run_dir: Path, manifest_path: Path) -> None:
    seen: set[str] = set()
    for line_number, line in enumerate(
        manifest_path.read_text(encoding="utf-8").splitlines(), 1
    ):
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
        if not match:
            raise ProvenanceError(
                f"invalid closure manifest line {line_number}: {line!r}"
            )
        expected, relative = match.groups()
        if relative in seen:
            raise ProvenanceError(f"duplicate closure manifest path: {relative}")
        seen.add(relative)
        path = resolve_under(
            run_dir, relative, f"closure manifest line {line_number}"
        )
        if path.is_symlink() or not path.is_file():
            raise ProvenanceError(f"closure member is not a regular file: {relative}")
        actual = sha256_file(path)
        if actual != expected:
            raise ProvenanceError(
                f"closure member hash mismatch {relative}: {expected} != {actual}"
            )
    if not seen:
        raise ProvenanceError("closure manifest is empty")


def write_generation_identity(
    root: Path, run_dir: Path, receipt: Mapping[str, Any]
) -> dict[str, Any]:
    build_path = run_dir / "build-receipt.json"
    closure_path = run_dir / "closure-manifest.sha256"
    identity = {
        "schema_version": IDENTITY_SCHEMA,
        "action_id": receipt["action_id"],
        "generation_id": receipt["generation_id"],
        "generation_digest": receipt["generation_digest"],
        "source_manifest_sha256": receipt["source_manifest"]["manifest_sha256"],
        "build_receipt": {
            "path": repo_relative(root, build_path),
            "sha256": sha256_file(build_path),
            "body_sha256": receipt["receipt_body_sha256"],
        },
        "closure_manifest": {
            "path": repo_relative(root, closure_path),
            "sha256": sha256_file(closure_path),
        },
        "artifacts": [
            {
                "role": item["role"],
                "device_path": item["device_path"],
                "sealed_path": item["local_path"],
                "sha256": item["sha256"],
                "bytes": item["bytes"],
            }
            for item in receipt["artifacts"]
        ],
        "status": {
            "build_pass": True,
            "target_deployment_generation_bound": False,
            "device_verified": False,
            "formal_verdict": "NOT_ISSUED",
        },
        "semantics": {
            "expected_artifact_hashes_must_be_imported_from_this_identity": True,
            "caller_reported_expected_hashes_are_not_authoritative": True,
        },
    }
    add_body_digest(identity)
    identity_path = run_dir / "generation-identity.json"
    write_json(identity_path, identity)
    (run_dir / "generation-identity.sha256").write_text(
        f"{sha256_file(identity_path)}  generation-identity.json\n", encoding="utf-8"
    )
    return identity


def verify_generation_closure(
    build_receipt_path: Path, build: Mapping[str, Any]
) -> dict[str, Any]:
    run_dir = build_receipt_path.resolve().parent
    closure_path = run_dir / "closure-manifest.sha256"
    identity_path = run_dir / "generation-identity.json"
    identity_sha_path = run_dir / "generation-identity.sha256"
    for path in (closure_path, identity_path, identity_sha_path):
        if not path.is_file():
            raise ProvenanceError(f"missing generation closure member: {path}")
    verify_hash_manifest(run_dir, closure_path)
    identity = require_dict(load_json(identity_path), "generation_identity")
    if identity.get("schema_version") != IDENTITY_SCHEMA:
        raise ProvenanceError("unsupported generation identity schema")
    verify_body_digest(identity, "generation_identity")
    if identity.get("action_id") != build.get("action_id"):
        raise ProvenanceError("generation identity Action ID mismatch")
    if identity.get("generation_id") != build.get("generation_id"):
        raise ProvenanceError("generation identity generation ID mismatch")
    if identity.get("source_manifest_sha256") != build["source_manifest"]["manifest_sha256"]:
        raise ProvenanceError("generation identity source manifest mismatch")
    build_ref = require_dict(identity.get("build_receipt"), "identity.build_receipt")
    if build_ref.get("sha256") != sha256_file(build_receipt_path):
        raise ProvenanceError("generation identity build receipt SHA mismatch")
    closure_ref = require_dict(identity.get("closure_manifest"), "identity.closure_manifest")
    if closure_ref.get("sha256") != sha256_file(closure_path):
        raise ProvenanceError("generation identity closure manifest SHA mismatch")
    expected_identity_line = (
        f"{sha256_file(identity_path)}  generation-identity.json"
    )
    if identity_sha_path.read_text(encoding="utf-8").strip() != expected_identity_line:
        raise ProvenanceError("generation identity SHA sidecar mismatch")
    identity_artifacts = {
        item["role"]: item
        for item in require_list(identity.get("artifacts"), "identity.artifacts")
    }
    for artifact in build["artifacts"]:
        item = identity_artifacts.get(artifact["role"])
        if (
            not isinstance(item, dict)
            or item.get("sha256") != artifact["sha256"]
            or item.get("bytes") != artifact["bytes"]
            or item.get("sealed_path") != artifact["local_path"]
            or item.get("device_path") != artifact["device_path"]
        ):
            raise ProvenanceError(
                f"generation identity artifact mismatch: {artifact['role']}"
            )
    return identity


def add_body_digest(value: dict[str, Any]) -> dict[str, Any]:
    if "receipt_body_sha256" in value:
        raise ProvenanceError("receipt already contains receipt_body_sha256")
    value["receipt_body_sha256"] = sha256_bytes(json_bytes(value))
    return value


def verify_body_digest(value: Mapping[str, Any], where: str) -> None:
    expected = value.get("receipt_body_sha256")
    if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
        raise ProvenanceError(f"{where}.receipt_body_sha256 is invalid")
    body = dict(value)
    del body["receipt_body_sha256"]
    actual = sha256_bytes(json_bytes(body))
    if actual != expected:
        raise ProvenanceError(
            f"{where} body digest mismatch: expected {expected}, actual {actual}"
        )


def produce_build_receipt(
    root: Path, config_path: Path, run_dir: Path
) -> dict[str, Any]:
    root = root.resolve()
    config_path = config_path.resolve()
    run_dir = run_dir.resolve()
    if root != run_dir and root not in run_dir.parents:
        raise ProvenanceError("run directory must be inside repository root")
    config = validate_config(load_json(config_path), root)
    run_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir = run_dir / "inputs"
    builder_dir = run_dir / "builder"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    builder_dir.mkdir(parents=True, exist_ok=True)

    source_before = expand_source_manifest(
        root, config["source_paths"], config.get("source_exclude_paths", [])
    )
    config_sha = sha256_file(config_path)
    generation_digest = sha256_bytes(
        json_bytes(
            {
                "action_id": config["action_id"],
                "config_sha256": config_sha,
                "source_manifest_sha256": source_before["manifest_sha256"],
                "target": config["target"],
            }
        )
    )
    generation_id = f"{config['action_id']}-{generation_digest[:20]}"
    source_manifest_path = inputs_dir / "source-manifest.json"
    write_json(source_manifest_path, source_before)
    config_snapshot_path = inputs_dir / "generation-config.json"
    shutil.copy2(config_path, config_snapshot_path)
    if sha256_file(config_snapshot_path) != config_sha:
        raise ProvenanceError("generation config snapshot hash mismatch")

    probes: list[dict[str, Any]] = []
    for index, raw in enumerate(config["builder_identity_probes"]):
        cwd = resolve_under(
            root, raw.get("cwd", "."), f"builder probe {raw['name']}.cwd"
        )
        env = validate_env(raw.get("env", {}), f"builder probe {raw['name']}.env")
        command = validate_command(raw["command"], f"builder probe {raw['name']}.command")
        result = run_command(command, cwd=cwd, env=env)
        log_path = logs_dir / f"probe-{index:02d}-{raw['name']}.log"
        log_path.write_text(result.stdout or "", encoding="utf-8")
        record = command_record(
            command, result, cwd=cwd, env=env, log_path=log_path, root=root
        )
        record["name"] = raw["name"]
        probes.append(record)
        if result.returncode != 0 or not (result.stdout or "").strip():
            raise ProvenanceError(
                f"builder identity probe {raw['name']} failed or returned empty output"
            )

    stages: list[dict[str, Any]] = []
    for index, raw in enumerate(config["stages"]):
        cwd = resolve_under(root, raw.get("cwd", "."), f"stage {raw['name']}.cwd")
        env = validate_env(raw.get("env", {}), f"stage {raw['name']}.env")
        command = validate_command(raw["command"], f"stage {raw['name']}.command")
        result = run_command(command, cwd=cwd, env=env)
        log_path = logs_dir / f"stage-{index:02d}-{raw['name']}.log"
        log_path.write_text(result.stdout or "", encoding="utf-8")
        record = command_record(
            command, result, cwd=cwd, env=env, log_path=log_path, root=root
        )
        record.update({"name": raw["name"], "scope": raw["scope"]})
        stages.append(record)
        if result.returncode != 0:
            failure = {
                "schema_version": "bridge.fn01.generation-build-failure.v1",
                "action_id": config["action_id"],
                "generation_id": generation_id,
                "failed_stage": record,
                "formal_verdict": "NOT_ISSUED",
                "device_verified": False,
            }
            write_json(run_dir / "build-failure.json", failure)
            raise ProvenanceError(
                f"build stage {raw['name']} failed with rc={result.returncode}"
            )

    source_after = expand_source_manifest(
        root, config["source_paths"], config.get("source_exclude_paths", [])
    )
    if source_before != source_after:
        raise ProvenanceError("source closure changed while generation stages were running")

    builder_identity = {
        "local_identity": local_builder_identity(root),
        "identity_probes": probes,
    }
    builder_identity_path = builder_dir / "builder-identity.json"
    write_json(builder_identity_path, builder_identity)
    artifacts = [seal_artifact(root, run_dir, raw) for raw in config["artifacts"]]
    receipt = {
        "schema_version": BUILD_SCHEMA,
        "action_id": config["action_id"],
        "generation_id": generation_id,
        "generation_digest": generation_digest,
        "captured_at": utc_now(),
        "target": config["target"],
        "status": {
            "build_pass": True,
            "host_scope_build_pass": any(
                stage["scope"] == "host" and stage["rc"] == 0 for stage in stages
            ),
            "target_scope_build_pass": any(
                stage["scope"] == "target" and stage["rc"] == 0 for stage in stages
            ),
            "target_deployment_generation_bound": False,
            "device_verified": False,
            "formal_verdict": "NOT_ISSUED",
        },
        "config": {
            "origin_path": repo_relative(root, config_path),
            "sealed_path": repo_relative(root, config_snapshot_path),
            "sha256": sha256_file(config_snapshot_path),
        },
        "source_manifest": source_before,
        "source_manifest_ref": {
            "path": repo_relative(root, source_manifest_path),
            "sha256": sha256_file(source_manifest_path),
        },
        "builder": builder_identity,
        "builder_identity_ref": {
            "path": repo_relative(root, builder_identity_path),
            "sha256": sha256_file(builder_identity_path),
        },
        "stages": stages,
        "artifacts": artifacts,
        "semantics": {
            "build_pass_is_not_device_verified": True,
            "deployment_byte_match_is_not_action_behavior_verification": True,
        },
    }
    add_body_digest(receipt)
    build_receipt_path = run_dir / "build-receipt.json"
    write_json(build_receipt_path, receipt)
    closure_path = run_dir / "closure-manifest.sha256"
    write_hash_manifest(root, run_dir, closure_path)
    verify_hash_manifest(run_dir, closure_path)
    write_generation_identity(root, run_dir, receipt)
    verify_generation_closure(build_receipt_path, receipt)
    return receipt


def hdc_run(hdc: Path, serial: str, arguments: Sequence[str]) -> str:
    command = [str(hdc), "-t", serial, *arguments]
    result = run_command(command, cwd=Path.cwd(), timeout=30)
    if result.returncode != 0:
        raise ProvenanceError(
            f"hdc command failed rc={result.returncode}: {shlex.join(command)}\n"
            f"{result.stdout}"
        )
    return (result.stdout or "").strip()


def parse_device_sha(output: str, expected_path: str) -> str:
    match = re.search(r"(?m)^([0-9a-f]{64})\s+(.+?)\s*$", output)
    if not match:
        raise ProvenanceError(f"cannot parse device sha256sum output: {output!r}")
    if match.group(2) != expected_path:
        raise ProvenanceError(
            f"device sha256 path mismatch: expected {expected_path}, got {match.group(2)}"
        )
    return match.group(1)


def parse_nonnegative_int(output: str, where: str) -> int:
    text = output.strip()
    if not re.fullmatch(r"[0-9]+", text):
        raise ProvenanceError(f"{where} is not a non-negative integer: {output!r}")
    return int(text)


def validate_build_receipt(value: Any) -> dict[str, Any]:
    receipt = require_dict(value, "build_receipt")
    if receipt.get("schema_version") != BUILD_SCHEMA:
        raise ProvenanceError("unsupported build receipt schema")
    verify_body_digest(receipt, "build_receipt")
    if not ACTION_RE.fullmatch(require_str(receipt.get("action_id"), "build_receipt.action_id")):
        raise ProvenanceError("invalid build receipt Action ID")
    status = require_dict(receipt.get("status"), "build_receipt.status")
    for field in (
        "build_pass",
        "host_scope_build_pass",
        "target_scope_build_pass",
        "target_deployment_generation_bound",
        "device_verified",
    ):
        require_bool(status.get(field), f"build_receipt.status.{field}")
    if (
        not status["build_pass"]
        or not status["host_scope_build_pass"]
        or not status["target_scope_build_pass"]
        or status["target_deployment_generation_bound"]
        or status["device_verified"]
        or status.get("formal_verdict") != "NOT_ISSUED"
    ):
        raise ProvenanceError("build receipt has invalid status semantics")
    artifacts = require_list(receipt.get("artifacts"), "build_receipt.artifacts")
    if not artifacts:
        raise ProvenanceError("build receipt artifact list is empty")
    roles: set[str] = set()
    for index, raw in enumerate(artifacts):
        artifact = require_dict(raw, f"build_receipt.artifacts[{index}]")
        role = require_str(artifact.get("role"), f"build_receipt.artifacts[{index}].role")
        if role in roles:
            raise ProvenanceError(f"duplicate build artifact role: {role}")
        roles.add(role)
        if not SHA256_RE.fullmatch(
            require_str(artifact.get("sha256"), f"build_receipt.artifacts[{index}].sha256")
        ):
            raise ProvenanceError(f"invalid artifact SHA256: {role}")
        if not isinstance(artifact.get("bytes"), int) or artifact["bytes"] < 0:
            raise ProvenanceError(f"invalid artifact byte size: {role}")
        require_str(
            artifact.get("device_path"),
            f"build_receipt.artifacts[{index}].device_path",
        )
    return receipt


def capture_device_receipt(
    build_receipt_path: Path,
    serial: str,
    hdc_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    build_receipt_path = build_receipt_path.resolve()
    build = validate_build_receipt(load_json(build_receipt_path))
    identity = verify_generation_closure(build_receipt_path, build)
    identity_path = build_receipt_path.parent / "generation-identity.json"
    closure_path = build_receipt_path.parent / "closure-manifest.sha256"
    hdc_path = hdc_path.resolve()
    if not hdc_path.is_file():
        raise ProvenanceError(f"hdc executable does not exist: {hdc_path}")
    list_result = run_command([str(hdc_path), "list", "targets"], cwd=Path.cwd(), timeout=30)
    if list_result.returncode != 0:
        raise ProvenanceError(f"hdc list targets failed: {list_result.stdout}")
    targets = {line.strip() for line in list_result.stdout.splitlines() if line.strip()}
    if serial not in targets:
        raise ProvenanceError(f"requested device serial is not online: {serial}")

    boot_before = hdc_run(
        hdc_path, serial, ["shell", "cat /proc/sys/kernel/random/boot_id"]
    )
    if not BOOT_ID_RE.fullmatch(boot_before):
        raise ProvenanceError(f"invalid device boot_id: {boot_before!r}")
    os_version = hdc_run(
        hdc_path,
        serial,
        [
            "shell",
            "param get const.product.software.version 2>/dev/null || "
            "param get const.ohos.fullname",
        ],
    )
    security_mode = hdc_run(
        hdc_path,
        serial,
        ["shell", "getenforce 2>/dev/null || cat /sys/fs/selinux/enforce"],
    )

    deployed: list[dict[str, Any]] = []
    for raw in build["artifacts"]:
        path = raw["device_path"]
        size_output = hdc_run(hdc_path, serial, ["shell", f"stat -c %s {shlex.quote(path)}"])
        hash_output = hdc_run(
            hdc_path, serial, ["shell", f"sha256sum {shlex.quote(path)}"]
        )
        deployed.append(
            {
                "role": raw["role"],
                "device_path": path,
                "sha256": parse_device_sha(hash_output, path),
                "bytes": parse_nonnegative_int(
                    size_output, f"device artifact {raw['role']} size"
                ),
            }
        )
    boot_after = hdc_run(
        hdc_path, serial, ["shell", "cat /proc/sys/kernel/random/boot_id"]
    )
    if boot_before != boot_after:
        raise ProvenanceError(
            f"device rebooted during provenance capture: {boot_before} -> {boot_after}"
        )

    hdc_version_result = run_command([str(hdc_path), "-v"], cwd=Path.cwd(), timeout=30)
    hdc_version = (hdc_version_result.stdout or "").strip()
    receipt = {
        "schema_version": DEVICE_SCHEMA,
        "action_id": build["action_id"],
        "generation_id": build["generation_id"],
        "captured_at": utc_now(),
        "build_receipt": {
            "path": str(build_receipt_path),
            "sha256": sha256_file(build_receipt_path),
            "body_sha256": build["receipt_body_sha256"],
        },
        "generation_identity": {
            "path": str(identity_path),
            "sha256": sha256_file(identity_path),
            "body_sha256": identity["receipt_body_sha256"],
        },
        "closure_manifest": {
            "path": str(closure_path),
            "sha256": sha256_file(closure_path),
        },
        "collector": {
            "hdc_path": str(hdc_path),
            "hdc_sha256": sha256_file(hdc_path),
            "hdc_version": hdc_version,
        },
        "device": {
            "serial": serial,
            "boot_id_before": boot_before,
            "boot_id_after": boot_after,
            "os_version": os_version,
            "security_mode": security_mode,
        },
        "deployed_artifacts": deployed,
        "status": {
            "read_only_capture_complete": True,
            "target_deployment_generation_bound": False,
            "device_verified": False,
            "formal_verdict": "NOT_ISSUED",
        },
        "semantics": {
            "capture_performed_no_deployment": True,
            "deployment_byte_match_is_not_action_behavior_verification": True,
        },
    }
    add_body_digest(receipt)
    write_json(output_path, receipt)
    return receipt


def validate_device_receipt(value: Any) -> dict[str, Any]:
    receipt = require_dict(value, "device_receipt")
    if receipt.get("schema_version") != DEVICE_SCHEMA:
        raise ProvenanceError("unsupported device receipt schema")
    verify_body_digest(receipt, "device_receipt")
    status = require_dict(receipt.get("status"), "device_receipt.status")
    if (
        status.get("read_only_capture_complete") is not True
        or status.get("target_deployment_generation_bound") is not False
        or status.get("device_verified") is not False
        or status.get("formal_verdict") != "NOT_ISSUED"
    ):
        raise ProvenanceError("device receipt has invalid status semantics")
    device = require_dict(receipt.get("device"), "device_receipt.device")
    before = require_str(device.get("boot_id_before"), "device_receipt.device.boot_id_before")
    after = require_str(device.get("boot_id_after"), "device_receipt.device.boot_id_after")
    if not BOOT_ID_RE.fullmatch(before) or before != after:
        raise ProvenanceError("device receipt boot identity is invalid or unstable")
    return receipt


def verify_local_build_state(root: Path, build: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    source_manifest = require_dict(build.get("source_manifest"), "build.source_manifest")
    expected_entries = require_list(source_manifest.get("entries"), "build.source_manifest.entries")
    current_entries: list[dict[str, Any]] = []
    for index, raw in enumerate(expected_entries):
        entry = require_dict(raw, f"build.source_manifest.entries[{index}]")
        try:
            path = resolve_under(
                root,
                require_str(entry.get("path"), f"build.source_manifest.entries[{index}].path"),
                f"build.source_manifest.entries[{index}].path",
            )
            current_entries.append(file_entry(root, path))
        except ProvenanceError as exc:
            failures.append(str(exc))
    current_entries.sort(key=lambda item: item["path"])
    if current_entries != expected_entries:
        failures.append("current source closure differs from build receipt")

    for raw in build["artifacts"]:
        try:
            path = resolve_under(
                root,
                require_str(raw.get("local_path"), f"artifact {raw.get('role')}.local_path"),
                f"artifact {raw.get('role')}.local_path",
            )
            actual = file_entry(root, path)
            if actual["sha256"] != raw["sha256"] or actual["bytes"] != raw["bytes"]:
                failures.append(f"current local artifact differs: {raw['role']}")
        except ProvenanceError as exc:
            failures.append(str(exc))
    return failures


def gate_report(
    root: Path,
    build_receipt_path: Path,
    device_receipt_path: Path,
    expected_serial: str | None = None,
) -> dict[str, Any]:
    build_receipt_path = build_receipt_path.resolve()
    device_receipt_path = device_receipt_path.resolve()
    build = validate_build_receipt(load_json(build_receipt_path))
    identity = verify_generation_closure(build_receipt_path, build)
    device = validate_device_receipt(load_json(device_receipt_path))
    failures: list[dict[str, str]] = []

    def fail(code: str, detail: str) -> None:
        failures.append({"code": code, "detail": detail})

    if device.get("action_id") != build.get("action_id"):
        fail("ACTION_ID_MISMATCH", "build and device receipt Action IDs differ")
    if device.get("generation_id") != build.get("generation_id"):
        fail("GENERATION_ID_MISMATCH", "build and device generation IDs differ")
    device_build_ref = require_dict(device.get("build_receipt"), "device.build_receipt")
    actual_build_sha = sha256_file(build_receipt_path)
    if device_build_ref.get("sha256") != actual_build_sha:
        fail("BUILD_RECEIPT_SHA_MISMATCH", "device receipt is bound to another build receipt")
    if device_build_ref.get("body_sha256") != build.get("receipt_body_sha256"):
        fail("BUILD_BODY_SHA_MISMATCH", "device receipt build body digest differs")
    identity_ref = require_dict(
        device.get("generation_identity"), "device.generation_identity"
    )
    identity_path = build_receipt_path.parent / "generation-identity.json"
    if identity_ref.get("sha256") != sha256_file(identity_path):
        fail(
            "GENERATION_IDENTITY_SHA_MISMATCH",
            "device receipt is bound to another generation identity",
        )
    if identity_ref.get("body_sha256") != identity.get("receipt_body_sha256"):
        fail(
            "GENERATION_IDENTITY_BODY_MISMATCH",
            "device receipt generation identity body differs",
        )
    closure_ref = require_dict(
        device.get("closure_manifest"), "device.closure_manifest"
    )
    closure_path = build_receipt_path.parent / "closure-manifest.sha256"
    if closure_ref.get("sha256") != sha256_file(closure_path):
        fail(
            "CLOSURE_MANIFEST_SHA_MISMATCH",
            "device receipt is bound to another closure manifest",
        )
    serial = require_str(
        require_dict(device.get("device"), "device.device").get("serial"),
        "device.device.serial",
    )
    if expected_serial and serial != expected_serial:
        fail("SERIAL_MISMATCH", f"expected {expected_serial}, captured {serial}")

    build_by_role = {item["role"]: item for item in build["artifacts"]}
    deployed_list = require_list(
        device.get("deployed_artifacts"), "device.deployed_artifacts"
    )
    deployed_by_role: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(deployed_list):
        item = require_dict(raw, f"device.deployed_artifacts[{index}]")
        role = require_str(item.get("role"), f"device.deployed_artifacts[{index}].role")
        if role in deployed_by_role:
            fail("DUPLICATE_DEPLOYED_ROLE", role)
        deployed_by_role[role] = item
    for role, built in build_by_role.items():
        deployed = deployed_by_role.get(role)
        if deployed is None:
            fail("MISSING_DEPLOYED_ROLE", role)
            continue
        if deployed.get("device_path") != built.get("device_path"):
            fail("DEVICE_PATH_MISMATCH", role)
        if deployed.get("sha256") != built.get("sha256"):
            fail(
                "DEPLOYED_SHA_MISMATCH",
                f"{role}: build={built.get('sha256')} device={deployed.get('sha256')}",
            )
        if deployed.get("bytes") != built.get("bytes"):
            fail(
                "DEPLOYED_SIZE_MISMATCH",
                f"{role}: build={built.get('bytes')} device={deployed.get('bytes')}",
            )
    for role in sorted(set(deployed_by_role) - set(build_by_role)):
        fail("UNEXPECTED_DEPLOYED_ROLE", role)

    for detail in verify_local_build_state(root.resolve(), build):
        fail("CURRENT_LOCAL_STATE_MISMATCH", detail)

    matched = not failures
    report = {
        "schema_version": GATE_SCHEMA,
        "action_id": build["action_id"],
        "generation_id": build["generation_id"],
        "checked_at": utc_now(),
        "build_receipt": {
            "path": str(build_receipt_path),
            "sha256": actual_build_sha,
        },
        "device_receipt": {
            "path": str(device_receipt_path),
            "sha256": sha256_file(device_receipt_path),
        },
        "device_serial": serial,
        "gate_status": "PASS" if matched else "FAIL",
        "status": {
            "build_pass": True,
            "host_scope_build_pass": True,
            "target_scope_build_pass": True,
            "target_deployment_generation_bound": matched,
            "device_verified": False,
            "formal_verdict": "NOT_ISSUED",
        },
        "failures": failures,
        "semantics": {
            "pass_means_exact_deployed_bytes_for_same_generation": True,
            "pass_does_not_mean_action_behavior_device_verified": True,
            "independent_action_verifier_still_required": True,
        },
    }
    add_body_digest(report)
    return report


def command_build(args: argparse.Namespace) -> int:
    receipt = produce_build_receipt(args.root, args.config, args.run_dir)
    output = args.run_dir.resolve() / "build-receipt.json"
    print(f"BUILD_RECEIPT={output}")
    print(f"GENERATION_ID={receipt['generation_id']}")
    print("STATUS=build_pass")
    print("DEVICE_VERIFIED=false")
    print("FORMAL_VERDICT=NOT_ISSUED")
    return 0


def command_capture_device(args: argparse.Namespace) -> int:
    receipt = capture_device_receipt(
        args.build_receipt, args.serial, args.hdc, args.output
    )
    print(f"DEVICE_RECEIPT={args.output.resolve()}")
    print(f"DEVICE_SERIAL={receipt['device']['serial']}")
    print(f"BOOT_ID={receipt['device']['boot_id_before']}")
    print("MUTATION=none")
    print("DEVICE_VERIFIED=false")
    print("FORMAL_VERDICT=NOT_ISSUED")
    return 0


def command_verify(args: argparse.Namespace) -> int:
    report = gate_report(
        args.root,
        args.build_receipt,
        args.device_receipt,
        args.expected_serial,
    )
    write_json(args.output, report)
    print(f"GATE_REPORT={args.output.resolve()}")
    print(f"GATE_STATUS={report['gate_status']}")
    print(
        "TARGET_DEPLOYMENT_GENERATION_BOUND="
        f"{str(report['status']['target_deployment_generation_bound']).lower()}"
    )
    print("DEVICE_VERIFIED=false")
    print("FORMAL_VERDICT=NOT_ISSUED")
    for failure in report["failures"]:
        print(f"FAILURE={failure['code']}:{failure['detail']}")
    return 0 if report["gate_status"] == "PASS" else 1


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--root", type=Path, default=Path("/opt/Bridge"), help="repository root"
    )
    subparsers = result.add_subparsers(dest="subcommand", required=True)

    build = subparsers.add_parser("build", help="run host+target stages and seal receipt")
    build.add_argument("--config", type=Path, required=True)
    build.add_argument("--run-dir", type=Path, required=True)
    build.set_defaults(handler=command_build)

    capture = subparsers.add_parser(
        "capture-device", help="read serial/boot/deployed hashes without mutation"
    )
    capture.add_argument("--build-receipt", type=Path, required=True)
    capture.add_argument("--serial", required=True)
    capture.add_argument("--hdc", type=Path, required=True)
    capture.add_argument("--output", type=Path, required=True)
    capture.set_defaults(handler=command_capture_device)

    verify = subparsers.add_parser(
        "verify", help="fail closed unless deployed bytes match one build generation"
    )
    verify.add_argument("--build-receipt", type=Path, required=True)
    verify.add_argument("--device-receipt", type=Path, required=True)
    verify.add_argument("--expected-serial")
    verify.add_argument("--output", type=Path, required=True)
    verify.set_defaults(handler=command_verify)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return int(args.handler(args))
    except ProvenanceError as exc:
        print(f"PROVENANCE_REJECTED: {exc}", file=sys.stderr)
        print("DEVICE_VERIFIED=false", file=sys.stderr)
        print("FORMAL_VERDICT=NOT_ISSUED", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
