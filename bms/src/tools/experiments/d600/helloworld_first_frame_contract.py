#!/usr/bin/env python3
"""Fail-closed contracts for the D600 HelloWorld first-frame developer run.

This module is deliberately host-only and uses only the Python standard
library.  It validates immutable identities and digest references; it never
connects to a device and never promotes a developer observation to an
independent Action or Journey verdict.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
HELLOWORLD_APK_SHA256 = "2d122a7973ffd68c799700aaaaaa0593e5deec30bac83e22a9dc1bf9f64319fd"
HELLOWORLD_PACKAGE = "com.example.helloworld"
HELLOWORLD_ACTIVITY = "com.example.helloworld.MainActivity"
DEVELOPER_CLAIM_BOUNDARY = "DEVELOPER_DEVICE_OBSERVATION_ONLY"
FORMAL_VERDICT = "NOT_ISSUED"

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
TERMINAL_STATES = frozenset(
    {
        "DEVELOPER_OBSERVED_FIRST_FRAME",
        "BLOCK_PRECONDITION",
        "FAIL_LAUNCH",
        "FAIL_NO_PROCESS",
        "FAIL_PROCESS_CRASH",
        "FAIL_LIFECYCLE",
        "FAIL_PRESENT",
        "FAIL_WRONG_CONTENT",
        "FAIL_UNSTABLE_FRAME",
        "INVALIDATED_IDENTITY",
    }
)


class ContractError(ValueError):
    """Raised when an input cannot be safely bound to this P0 run."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_json_object(path: Path, label: str = "document") -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ContractError(f"{label}: cannot load JSON: {error}") from error
    return dict(_mapping(value, label))


def resolve_project_path(
    value: str | Path,
    *,
    project_root: Path = PROJECT_ROOT,
    must_exist: bool = False,
) -> Path:
    root = project_root.resolve()
    raw = Path(value)
    path = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ContractError(f"path must remain inside project root: {value}") from error
    if must_exist and not path.exists():
        raise ContractError(f"path does not exist: {path}")
    return path


def make_digest_ref(path: Path, *, project_root: Path = PROJECT_ROOT) -> dict[str, str]:
    resolved = resolve_project_path(path, project_root=project_root, must_exist=True)
    if not resolved.is_file():
        raise ContractError(f"digest reference is not a regular file: {resolved}")
    return {
        "path": resolved.relative_to(project_root.resolve()).as_posix(),
        "sha256": sha256_file(resolved),
    }


def load_digest_ref(
    reference: object, *, project_root: Path = PROJECT_ROOT
) -> Path:
    value = _mapping(reference, "digest_ref")
    _exact_fields(value, {"path", "sha256"}, "digest_ref")
    path_value = _nonempty_string(value.get("path"), "digest_ref.path")
    expected = _sha256(value.get("sha256"), "digest_ref.sha256")
    path = resolve_project_path(path_value, project_root=project_root, must_exist=True)
    if not path.is_file():
        raise ContractError(f"digest_ref.path is not a regular file: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise ContractError(
            f"digest_ref digest mismatch: expected {expected}, observed {actual}, path={path}"
        )
    return path


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{label}: required object")
    return value


def _sequence(value: object, label: str, *, nonempty: bool = False) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ContractError(f"{label}: required array")
    if nonempty and not value:
        raise ContractError(f"{label}: required non-empty array")
    return value


def _required_fields(value: Mapping[str, Any], required: set[str], label: str) -> None:
    missing = sorted(required - set(value))
    if missing:
        raise ContractError(f"{label}: missing fields {missing}")


def _exact_fields(value: Mapping[str, Any], allowed: set[str], label: str) -> None:
    extra = sorted(set(value) - allowed)
    if extra:
        raise ContractError(f"{label}: unexpected fields {extra}")


def _object_shape(
    value: object,
    *,
    required: set[str],
    allowed: set[str] | None = None,
    label: str,
) -> Mapping[str, Any]:
    result = _mapping(value, label)
    _required_fields(result, required, label)
    _exact_fields(result, allowed or required, label)
    return result


def _nonempty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{label}: required non-empty string")
    return value.strip()


def _id(value: object, label: str) -> str:
    result = _nonempty_string(value, label)
    if ID_RE.fullmatch(result) is None:
        raise ContractError(f"{label}: invalid stable identifier")
    return result


def _sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise ContractError(f"{label}: required 64 lowercase hexadecimal SHA-256")
    if value == "0" * 64:
        raise ContractError(f"{label}: all-zero SHA-256 placeholder is invalid")
    return value


def _sha_or_absent(value: object, label: str) -> str:
    if value == "ABSENT":
        return "ABSENT"
    return _sha256(value, label)


def _boolean(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise ContractError(f"{label}: required boolean")
    return value


def _integer(value: object, label: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"{label}: required integer")
    if minimum is not None and value < minimum:
        raise ContractError(f"{label}: required integer >= {minimum}")
    return value


def _nullable_integer(
    value: object, label: str, *, minimum: int | None = None
) -> int | None:
    if value is None:
        return None
    return _integer(value, label, minimum=minimum)


def _number(value: object, label: str, *, minimum: float = 0.0) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < minimum
    ):
        raise ContractError(f"{label}: required finite number >= {minimum}")
    return float(value)


def _nullable_number(value: object, label: str) -> float | None:
    if value is None:
        return None
    return _number(value, label)


def _uuid(value: object, label: str) -> str:
    result = _nonempty_string(value, label)
    try:
        uuid.UUID(result)
    except ValueError as error:
        raise ContractError(f"{label}: required UUID") from error
    return result


def _date_time(value: object, label: str) -> str:
    result = _nonempty_string(value, label)
    try:
        datetime.fromisoformat(result.replace("Z", "+00:00"))
    except ValueError as error:
        raise ContractError(f"{label}: required ISO-8601 date-time") from error
    return result


def load_frozen_apk(
    receipt_path: Path,
    *,
    project_root: Path = PROJECT_ROOT,
    expected_sha256: str = HELLOWORLD_APK_SHA256,
) -> dict[str, Any]:
    receipt = load_json_object(receipt_path, "frozen_apk")
    required = {
        "schema_version",
        "resolved_path",
        "size_bytes",
        "sha256",
        "package_name",
        "activity_name",
        "unmodified",
    }
    _required_fields(receipt, required, "frozen_apk")
    optional = {
        "staged_sha256",
        "installed_sha256",
        "resolved_path_kind",
        "git_tracking",
        "verification",
    }
    _exact_fields(receipt, required | optional, "frozen_apk")
    if receipt["schema_version"] not in (1, "bridge.p0.frozen-apk.v1") or isinstance(
        receipt["schema_version"], bool
    ):
        raise ContractError(
            "frozen_apk.schema_version: required 1 or bridge.p0.frozen-apk.v1"
        )
    digest = _sha256(receipt["sha256"], "frozen_apk.sha256")
    expected = _sha256(expected_sha256, "expected_sha256")
    if digest != expected:
        raise ContractError(f"frozen_apk.sha256: expected {expected}, got {digest}")
    if receipt["package_name"] != HELLOWORLD_PACKAGE:
        raise ContractError(f"frozen_apk.package_name: required {HELLOWORLD_PACKAGE}")
    if receipt["activity_name"] != HELLOWORLD_ACTIVITY:
        raise ContractError(f"frozen_apk.activity_name: required {HELLOWORLD_ACTIVITY}")
    if receipt["unmodified"] is not True:
        raise ContractError("frozen_apk.unmodified: required true")
    if receipt.get("resolved_path_kind", "project_relative") != "project_relative":
        raise ContractError("frozen_apk.resolved_path_kind: required project_relative")

    if "git_tracking" in receipt:
        tracking = _object_shape(
            receipt["git_tracking"],
            required={"tracked", "mode", "blob_oid_sha1", "baseline_head"},
            label="frozen_apk.git_tracking",
        )
        if tracking["tracked"] is not True or tracking["mode"] != "100644":
            raise ContractError("frozen_apk.git_tracking: required tracked regular file")
        if not isinstance(tracking["blob_oid_sha1"], str) or SHA1_RE.fullmatch(
            tracking["blob_oid_sha1"]
        ) is None:
            raise ContractError("frozen_apk.git_tracking.blob_oid_sha1: required SHA-1")
        if not isinstance(tracking["baseline_head"], str) or SHA1_RE.fullmatch(
            tracking["baseline_head"]
        ) is None:
            raise ContractError("frozen_apk.git_tracking.baseline_head: required Git SHA-1")

    if "verification" in receipt:
        verification = _object_shape(
            receipt["verification"],
            required={
                "path_selection",
                "size_match",
                "sha256_match",
                "rejected_fallback",
            },
            label="frozen_apk.verification",
        )
        if verification["path_selection"] != "explicit_tracked_evidence_only":
            raise ContractError("frozen_apk.verification.path_selection: wrong policy")
        if verification["size_match"] is not True or verification["sha256_match"] is not True:
            raise ContractError("frozen_apk.verification: size and sha256 must match")
        if verification["rejected_fallback"] != "src/adapter/out/app/HelloWorld.apk":
            raise ContractError("frozen_apk.verification.rejected_fallback: wrong path")
    size = _integer(receipt["size_bytes"], "frozen_apk.size_bytes", minimum=1)
    path = resolve_project_path(
        _nonempty_string(receipt["resolved_path"], "frozen_apk.resolved_path"),
        project_root=project_root,
        must_exist=True,
    )
    if not path.is_file() or path.suffix.lower() != ".apk":
        raise ContractError(f"frozen_apk.resolved_path: required APK file: {path}")
    if path.stat().st_size != size:
        raise ContractError(
            f"frozen_apk.size_bytes: receipt {size} != file {path.stat().st_size}"
        )
    actual = sha256_file(path)
    if actual != digest:
        raise ContractError(f"frozen_apk.sha256: receipt {digest} != file {actual}")
    for optional in ("staged_sha256", "installed_sha256"):
        if optional in receipt and _sha256(receipt[optional], f"frozen_apk.{optional}") != digest:
            raise ContractError(f"frozen_apk.{optional}: must equal frozen APK sha256")
    result = dict(receipt)
    result["resolved_path"] = str(path)
    return result


CHANGE_SET_REQUIRED = {
    "change_set_id",
    "hypothesis",
    "atomic_reason",
    "members",
    "earliest_transition",
    "expected_observation",
    "falsifier",
    "unchanged_invariants",
    "pnf_cases",
    "rollback",
    "status",
}


def validate_change_set(document: object) -> dict[str, Any]:
    value = _mapping(document, "change_set")
    _required_fields(value, CHANGE_SET_REQUIRED, "change_set")
    _exact_fields(value, CHANGE_SET_REQUIRED | {"reused_receipts"}, "change_set")
    _id(value["change_set_id"], "change_set.change_set_id")
    for field in (
        "hypothesis",
        "atomic_reason",
        "earliest_transition",
        "expected_observation",
        "falsifier",
    ):
        _nonempty_string(value[field], f"change_set.{field}")

    members = _sequence(value["members"], "change_set.members", nonempty=True)
    member_paths: set[str] = set()
    member_fields = {
        "path",
        "component",
        "before_sha256",
        "after_sha256",
        "mechanism",
        "expected_effect",
    }
    for index, raw in enumerate(members):
        label = f"change_set.members[{index}]"
        member = _object_shape(raw, required=member_fields, label=label)
        path = _nonempty_string(member["path"], f"{label}.path")
        if path in member_paths:
            raise ContractError(f"change_set.members: duplicate member path {path}")
        member_paths.add(path)
        _nonempty_string(member["component"], f"{label}.component")
        before = _sha_or_absent(member["before_sha256"], f"{label}.before_sha256")
        after = _sha_or_absent(member["after_sha256"], f"{label}.after_sha256")
        if before == after:
            raise ContractError(f"{label}: before/after must change identity")
        _nonempty_string(member["mechanism"], f"{label}.mechanism")
        _nonempty_string(member["expected_effect"], f"{label}.expected_effect")

    invariants = _sequence(value["unchanged_invariants"], "change_set.unchanged_invariants")
    for index, invariant in enumerate(invariants):
        _nonempty_string(invariant, f"change_set.unchanged_invariants[{index}]")

    pnf_fields = {"positive", "negative", "failure"}
    pnf = _object_shape(value["pnf_cases"], required=pnf_fields, label="change_set.pnf_cases")
    for field in pnf_fields:
        _nonempty_string(pnf[field], f"change_set.pnf_cases.{field}")

    rollback_fields = {"restore_all_members", "procedure_ref", "post_rollback_oracle"}
    rollback = _object_shape(
        value["rollback"], required=rollback_fields, label="change_set.rollback"
    )
    if rollback["restore_all_members"] is not True:
        raise ContractError("change_set.rollback.restore_all_members: required true")
    _nonempty_string(rollback["procedure_ref"], "change_set.rollback.procedure_ref")
    _nonempty_string(
        rollback["post_rollback_oracle"], "change_set.rollback.post_rollback_oracle"
    )

    if value["status"] not in {
        "DRAFT",
        "BUILT",
        "DEPLOYED",
        "TESTED",
        "FALSIFIED",
        "ACCEPTED",
        "ROLLED_BACK",
    }:
        raise ContractError("change_set.status: invalid state")

    if "reused_receipts" in value:
        receipts = _sequence(value["reused_receipts"], "change_set.reused_receipts")
        receipt_fields = {"path", "sha256", "reuse_reason"}
        for index, raw in enumerate(receipts):
            label = f"change_set.reused_receipts[{index}]"
            receipt = _object_shape(raw, required=receipt_fields, label=label)
            _nonempty_string(receipt["path"], f"{label}.path")
            _sha256(receipt["sha256"], f"{label}.sha256")
            _nonempty_string(receipt["reuse_reason"], f"{label}.reuse_reason")
    return dict(value)


def load_change_set(path: Path) -> dict[str, Any]:
    return validate_change_set(load_json_object(path, "change_set"))


def validate_generation(document: object) -> dict[str, Any]:
    value = _mapping(document, "generation")
    required = {
        "generation_id",
        "source_manifest_sha256",
        "builder_identity_ref",
        "primary_manifest_ref",
        "repro_manifest_ref",
        "artifact_pairs",
        "reproducibility",
        "selected_deploy_set_ref",
        "claim_boundary",
    }
    _required_fields(value, required, "generation")
    _sha256(value["generation_id"], "generation.generation_id")
    _sha256(value["source_manifest_sha256"], "generation.source_manifest_sha256")
    for field in (
        "builder_identity_ref",
        "primary_manifest_ref",
        "repro_manifest_ref",
        "selected_deploy_set_ref",
    ):
        _nonempty_string(value[field], f"generation.{field}")
    if value["reproducibility"] not in {"MATCH", "MISMATCH", "REUSED"}:
        raise ContractError("generation.reproducibility: invalid state")
    if value["claim_boundary"] != "BUILD_AND_ARTIFACT_ONLY":
        raise ContractError("generation.claim_boundary: required BUILD_AND_ARTIFACT_ONLY")
    pairs = _sequence(value["artifact_pairs"], "generation.artifact_pairs", nonempty=True)
    for index, raw in enumerate(pairs):
        pair = _mapping(raw, f"generation.artifact_pairs[{index}]")
        for field in ("role", "primary_sha256", "repro_sha256"):
            if field not in pair:
                raise ContractError(f"generation.artifact_pairs[{index}]: missing {field}")
        _nonempty_string(pair["role"], f"generation.artifact_pairs[{index}].role")
        primary = _sha256(pair["primary_sha256"], f"generation.artifact_pairs[{index}].primary_sha256")
        repro = _sha256(pair["repro_sha256"], f"generation.artifact_pairs[{index}].repro_sha256")
        if value["reproducibility"] == "MATCH" and primary != repro:
            raise ContractError(f"generation.artifact_pairs[{index}]: primary/repro mismatch")
    return dict(value)


def load_generation(path: Path) -> dict[str, Any]:
    return validate_generation(load_json_object(path, "generation"))


def validate_device_identity(document: object) -> dict[str, Any]:
    value = _mapping(document, "device_identity")
    required = {
        "serial",
        "boot_id",
        "generation_id",
        "apk_sha256",
        "device_readback_sha256",
    }
    _required_fields(value, required, "device_identity")
    _nonempty_string(value["serial"], "device_identity.serial")
    _uuid(value["boot_id"], "device_identity.boot_id")
    _sha256(value["generation_id"], "device_identity.generation_id")
    _sha256(value["apk_sha256"], "device_identity.apk_sha256")
    _sha256(value["device_readback_sha256"], "device_identity.device_readback_sha256")
    if value["apk_sha256"] != HELLOWORLD_APK_SHA256:
        raise ContractError("device_identity.apk_sha256: wrong HelloWorld APK")
    appspawn = value.get("appspawn_parent")
    if appspawn is not None:
        parent = _mapping(appspawn, "device_identity.appspawn_parent")
        for field in ("pid", "ppid", "start_ticks", "exe"):
            if field not in parent:
                raise ContractError(f"device_identity.appspawn_parent: missing {field}")
        _integer(parent["pid"], "device_identity.appspawn_parent.pid", minimum=1)
        _integer(parent["ppid"], "device_identity.appspawn_parent.ppid", minimum=0)
        _integer(parent["start_ticks"], "device_identity.appspawn_parent.start_ticks", minimum=0)
        _nonempty_string(parent["exe"], "device_identity.appspawn_parent.exe")
    artifacts = value.get("artifacts", {})
    if not isinstance(artifacts, Mapping):
        raise ContractError("device_identity.artifacts: required object")
    for name, raw in artifacts.items():
        artifact = _object_shape(
            raw, required={"path", "sha256"}, label=f"device_identity.artifacts.{name}"
        )
        _nonempty_string(artifact["path"], f"device_identity.artifacts.{name}.path")
        _sha256(artifact["sha256"], f"device_identity.artifacts.{name}.sha256")
    return dict(value)


def load_device_identity(path: Path) -> dict[str, Any]:
    return validate_device_identity(load_json_object(path, "device_identity"))


CANDIDATE_REQUIRED = {
    "candidate_id",
    "run_id",
    "apk",
    "device",
    "generation",
    "launch",
    "process",
    "observations",
    "pnf",
    "first_bad",
    "terminal_state",
    "evidence_manifest_sha256",
}


def validate_candidate(document: object) -> dict[str, Any]:
    value = _mapping(document, "candidate")
    _required_fields(value, CANDIDATE_REQUIRED, "candidate")
    _exact_fields(value, CANDIDATE_REQUIRED | {"change_set_ref"}, "candidate")
    _id(value["candidate_id"], "candidate.candidate_id")
    _id(value["run_id"], "candidate.run_id")

    apk_fields = {"sha256", "package_name", "activity_name", "unmodified"}
    apk = _object_shape(value["apk"], required=apk_fields, label="candidate.apk")
    if apk["sha256"] != HELLOWORLD_APK_SHA256:
        raise ContractError("candidate.apk.sha256: wrong frozen APK")
    if apk["package_name"] != HELLOWORLD_PACKAGE:
        raise ContractError("candidate.apk.package_name: wrong package")
    if apk["activity_name"] != HELLOWORLD_ACTIVITY:
        raise ContractError("candidate.apk.activity_name: wrong activity")
    if apk["unmodified"] is not True:
        raise ContractError("candidate.apk.unmodified: required true")

    device_fields = {"serial", "boot_id", "oh_version", "selinux", "lease_ref"}
    device = _object_shape(value["device"], required=device_fields, label="candidate.device")
    _nonempty_string(device["serial"], "candidate.device.serial")
    _uuid(device["boot_id"], "candidate.device.boot_id")
    _nonempty_string(device["oh_version"], "candidate.device.oh_version")
    if device["selinux"] not in {"Enforcing", "Permissive"}:
        raise ContractError("candidate.device.selinux: invalid state")
    _nonempty_string(device["lease_ref"], "candidate.device.lease_ref")

    generation_fields = {"generation_id", "device_readback_receipt", "identity_valid"}
    generation = _object_shape(
        value["generation"], required=generation_fields, label="candidate.generation"
    )
    _sha256(generation["generation_id"], "candidate.generation.generation_id")
    _nonempty_string(
        generation["device_readback_receipt"],
        "candidate.generation.device_readback_receipt",
    )
    if generation["identity_valid"] is not True:
        raise ContractError("candidate.generation.identity_valid: required true")
    if "change_set_ref" in value:
        _nonempty_string(value["change_set_ref"], "candidate.change_set_ref")

    launch_fields = {
        "cold_precondition",
        "started_at_utc",
        "started_at_monotonic",
        "request_id",
    }
    launch = _object_shape(value["launch"], required=launch_fields, label="candidate.launch")
    if launch["cold_precondition"] is not True:
        raise ContractError("candidate.launch.cold_precondition: required true")
    _date_time(launch["started_at_utc"], "candidate.launch.started_at_utc")
    _number(launch["started_at_monotonic"], "candidate.launch.started_at_monotonic")
    if launch["request_id"] is not None:
        _nonempty_string(launch["request_id"], "candidate.launch.request_id")

    process_fields = {"pid", "start_ticks", "parent_pid", "package_bound", "alive_at_hold_end"}
    process = _object_shape(value["process"], required=process_fields, label="candidate.process")
    pid = _nullable_integer(process["pid"], "candidate.process.pid", minimum=1)
    start_ticks = _nullable_integer(
        process["start_ticks"], "candidate.process.start_ticks", minimum=0
    )
    parent_pid = _nullable_integer(
        process["parent_pid"], "candidate.process.parent_pid", minimum=1
    )
    package_bound = _boolean(process["package_bound"], "candidate.process.package_bound")
    alive = _boolean(process["alive_at_hold_end"], "candidate.process.alive_at_hold_end")
    if any(item is None for item in (pid, start_ticks, parent_pid)) and any(
        item is not None for item in (pid, start_ticks, parent_pid)
    ):
        raise ContractError("candidate.process: pid/start_ticks/parent_pid must be jointly present")

    observation_fields = {
        "on_resume",
        "app_window_visible",
        "present_observed",
        "hello_world_visible",
        "first_frame_seconds",
        "hold_seconds",
        "screens",
    }
    observations = _object_shape(
        value["observations"], required=observation_fields, label="candidate.observations"
    )
    for field in ("on_resume", "app_window_visible", "present_observed", "hello_world_visible"):
        _boolean(observations[field], f"candidate.observations.{field}")
    first_frame = _nullable_number(
        observations["first_frame_seconds"], "candidate.observations.first_frame_seconds"
    )
    hold = _number(observations["hold_seconds"], "candidate.observations.hold_seconds")
    screens = _sequence(observations["screens"], "candidate.observations.screens")
    roles: list[str] = []
    screen_fields = {"role", "path", "sha256", "captured_at_utc"}
    for index, raw in enumerate(screens):
        label = f"candidate.observations.screens[{index}]"
        screen = _object_shape(raw, required=screen_fields, label=label)
        if screen["role"] not in {"PRECONDITION", "FIRST_FRAME", "HOLD_END", "CRASH"}:
            raise ContractError(f"{label}.role: invalid role")
        roles.append(screen["role"])
        _nonempty_string(screen["path"], f"{label}.path")
        _sha256(screen["sha256"], f"{label}.sha256")
        _date_time(screen["captured_at_utc"], f"{label}.captured_at_utc")

    pnf_fields = {"positive", "negative", "failure"}
    pnf = _object_shape(value["pnf"], required=pnf_fields, label="candidate.pnf")
    for field in pnf_fields:
        if pnf[field] not in {"PASS", "FAIL", "NOT_RUN"}:
            raise ContractError(f"candidate.pnf.{field}: invalid state")

    _nonempty_string(value["first_bad"], "candidate.first_bad")
    terminal = value["terminal_state"]
    if terminal not in TERMINAL_STATES:
        raise ContractError("candidate.terminal_state: invalid typed terminal state")
    _sha256(value["evidence_manifest_sha256"], "candidate.evidence_manifest_sha256")

    if terminal == "DEVELOPER_OBSERVED_FIRST_FRAME":
        if None in (pid, start_ticks, parent_pid) or not package_bound or not alive:
            raise ContractError("candidate.process: success requires one live pid+start_ticks identity")
        if not all(
            observations[field]
            for field in ("on_resume", "app_window_visible", "present_observed", "hello_world_visible")
        ):
            raise ContractError("candidate.observations: success requires lifecycle/window/present/content")
        if first_frame is None or first_frame > 15.0:
            raise ContractError("candidate.observations.first_frame_seconds: success deadline is 15s")
        if hold < 5.0:
            raise ContractError("candidate.observations.hold_seconds: success requires at least 5s")
        if roles.count("FIRST_FRAME") != 1 or roles.count("HOLD_END") != 1:
            raise ContractError("candidate.observations.screens: success requires one FIRST_FRAME and HOLD_END")
    return dict(value)


def load_candidate(path: Path) -> dict[str, Any]:
    return validate_candidate(load_json_object(path, "candidate"))


REUSE_FIELDS: dict[str, tuple[str, ...]] = {
    "apk": ("apk_sha256",),
    "build": (
        "apk_sha256",
        "source_manifest_sha256",
        "builder_identity_sha256",
        "toolchain_sha256",
        "generation_id",
    ),
    "device": (
        "apk_sha256",
        "generation_id",
        "serial",
        "boot_id",
        "device_readback_sha256",
    ),
    "candidate": (
        "apk_sha256",
        "source_manifest_sha256",
        "builder_identity_sha256",
        "toolchain_sha256",
        "generation_id",
        "serial",
        "boot_id",
        "device_readback_sha256",
        "log_timeline_sha256",
        "screenshot_timeline_sha256",
    ),
}


def receipt_reuse_errors(
    receipt_kind: str,
    cached_bindings: Mapping[str, object],
    current_bindings: Mapping[str, object],
) -> list[str]:
    fields = REUSE_FIELDS.get(receipt_kind)
    if fields is None:
        return [f"receipt_kind: unsupported kind {receipt_kind!r}"]
    errors: list[str] = []
    for field in fields:
        if field not in cached_bindings:
            errors.append(f"{field}: absent from cached receipt bindings")
            continue
        if field not in current_bindings:
            errors.append(f"{field}: absent from current bindings")
            continue
        if cached_bindings[field] != current_bindings[field]:
            errors.append(
                f"{field}: reuse invalidated ({cached_bindings[field]!r} != {current_bindings[field]!r})"
            )
    return errors


def validate_developer_verdict(
    document: object, candidate: Mapping[str, object]
) -> dict[str, Any]:
    value = _mapping(document, "developer_verdict")
    fields = {
        "candidate_ref",
        "evidence_manifest_sha256",
        "verdict",
        "first_bad",
        "issued_by",
        "claim_boundary",
        "formal_journey_verdict",
    }
    _required_fields(value, fields, "developer_verdict")
    _exact_fields(value, fields, "developer_verdict")
    _nonempty_string(value["candidate_ref"], "developer_verdict.candidate_ref")
    manifest = _sha256(
        value["evidence_manifest_sha256"],
        "developer_verdict.evidence_manifest_sha256",
    )
    _nonempty_string(value["first_bad"], "developer_verdict.first_bad")
    _nonempty_string(value["issued_by"], "developer_verdict.issued_by")
    if value["claim_boundary"] != DEVELOPER_CLAIM_BOUNDARY:
        raise ContractError(
            f"developer_verdict.claim_boundary: required {DEVELOPER_CLAIM_BOUNDARY}"
        )
    if value["formal_journey_verdict"] != FORMAL_VERDICT:
        raise ContractError(
            f"developer_verdict.formal_journey_verdict: required {FORMAL_VERDICT}"
        )
    verdict = _nonempty_string(value["verdict"], "developer_verdict.verdict")
    if not (
        verdict == "DEVELOPER_OBSERVED_FIRST_FRAME"
        or verdict == "SPEC_GAP"
        or verdict.startswith("FAIL_")
        or verdict.startswith("BLOCK_")
    ):
        raise ContractError("developer_verdict.verdict: independent/general PASS is forbidden")
    candidate_manifest = candidate.get("evidence_manifest_sha256")
    if manifest != candidate_manifest:
        raise ContractError("developer_verdict.evidence_manifest_sha256: candidate mismatch")
    candidate_terminal = candidate.get("terminal_state")
    if verdict == "DEVELOPER_OBSERVED_FIRST_FRAME" and candidate_terminal != verdict:
        raise ContractError("developer_verdict.verdict: candidate did not reach developer first frame")
    if verdict.startswith(("FAIL_", "BLOCK_")) and candidate_terminal != verdict:
        raise ContractError("developer_verdict.verdict: candidate terminal state mismatch")
    return dict(value)


def load_developer_verdict(
    path: Path, candidate: Mapping[str, object]
) -> dict[str, Any]:
    return validate_developer_verdict(load_json_object(path, "developer_verdict"), candidate)


__all__ = [
    "ContractError",
    "DEVELOPER_CLAIM_BOUNDARY",
    "FORMAL_VERDICT",
    "HELLOWORLD_ACTIVITY",
    "HELLOWORLD_APK_SHA256",
    "HELLOWORLD_PACKAGE",
    "PROJECT_ROOT",
    "TERMINAL_STATES",
    "canonical_json_sha256",
    "load_candidate",
    "load_change_set",
    "load_developer_verdict",
    "load_device_identity",
    "load_digest_ref",
    "load_frozen_apk",
    "load_generation",
    "load_json_object",
    "make_digest_ref",
    "receipt_reuse_errors",
    "resolve_project_path",
    "sha256_file",
    "validate_candidate",
    "validate_change_set",
    "validate_developer_verdict",
    "validate_device_identity",
    "validate_generation",
]
