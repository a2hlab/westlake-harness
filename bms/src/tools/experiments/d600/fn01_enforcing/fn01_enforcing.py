#!/usr/bin/env python3
"""Fn01 A01-A04 developer-side D600 Enforcing evidence collector.

This tool never issues an Action verdict.  It only decides whether a captured
environment/request evidence bundle is internally valid enough to hand to an
independent verifier.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "1.0"
TOOL_VERSION = "fn01-enforcing-evidence-v2"
CARD1_BUILD_SCHEMA = "bridge.fn01.generation-build-receipt.v1"
CARD1_DEVICE_SCHEMA = "bridge.fn01.device-generation-receipt.v1"
CARD1_GATE_SCHEMA = "bridge.fn01.generation-gate-report.v1"
CARD1_ADAPTER_SCHEMA = "bridge.fn01.enforcing-card1-adapter.v1"
DEFAULT_HDC = (
    "/Applications/DevEco-Studio.app/Contents/sdk/default/"
    "openharmony/toolchains/hdc"
)
DEFAULT_ROOT = Path(__file__).resolve().parents[4]
FORBIDDEN_SERIAL_PREFIXES = ("5eab",)
DEFAULT_PROCESSES = ("appspawn-x", "foundation")
DEFAULT_LABEL_PATHS = (
    "/system/bin/appspawn-x",
    "/system/lib64/libbms.z.so",
    "/system/lib64/libinstalls.z.so",
    "/system/lib64/libapk_installer.so",
    "/system/android/lib64/liboh_adapter_bridge.so",
)
ACTION_IDS = {f"Fn01.A{index:02d}" for index in range(1, 5)}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
BOOT_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}$"
)
SELINUX_CONTEXT_RE = re.compile(r"^u:[^:\s]+:[^:\s]+:s\d+(?::[^\s]+)?$")
PROCESS_NAME_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
DENIAL_RE = re.compile(
    r"(?:avc:\s*denied|type=1400\b|audit\([^)]*\).*denied)",
    re.IGNORECASE,
)


class EvidenceError(RuntimeError):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def require_object(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError(f"{where} must be a JSON object")
    return value


def require_array(value: Any, where: str) -> list[Any]:
    if not isinstance(value, list):
        raise EvidenceError(f"{where} must be a JSON array")
    return value


def require_string(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise EvidenceError(f"{where} must be a non-empty string")
    return value


def require_bool(value: Any, where: str) -> bool:
    if not isinstance(value, bool):
        raise EvidenceError(f"{where} must be a boolean")
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
        raise EvidenceError(f"{where} missing fields: {sorted(missing)}")
    if extra:
        raise EvidenceError(f"{where} has unsupported fields: {sorted(extra)}")


def verify_card1_body_digest(value: Mapping[str, Any], where: str) -> None:
    expected = value.get("receipt_body_sha256")
    if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
        raise EvidenceError(f"{where}.receipt_body_sha256 is invalid")
    body = dict(value)
    del body["receipt_body_sha256"]
    actual = sha256_bytes(canonical_json_bytes(body))
    if actual != expected:
        raise EvidenceError(
            f"{where} body digest mismatch: expected={expected} actual={actual}"
        )


def _reject_symlink_chain(root: Path, path: Path, where: str) -> None:
    root = root.resolve(strict=True)
    current = path
    chain: list[Path] = []
    while current != root:
        chain.append(current)
        if root not in current.parents:
            raise EvidenceError(f"{where} escapes bundle root: {path}")
        current = current.parent
    for candidate in reversed(chain):
        try:
            mode = candidate.lstat().st_mode
        except FileNotFoundError as exc:
            raise EvidenceError(f"{where} is missing: {candidate}") from exc
        if stat.S_ISLNK(mode):
            raise EvidenceError(f"{where} contains symlink: {candidate}")


def resolve_bundle_file(root: Path, member: str, where: str) -> Path:
    root = root.resolve(strict=True)
    member_path = Path(require_string(member, where))
    if (
        member_path.is_absolute()
        or any(part in {"", ".", ".."} for part in member_path.parts)
    ):
        raise EvidenceError(f"{where} must be an ordinary relative path: {member!r}")
    candidate = root / member_path
    _reject_symlink_chain(root, candidate, where)
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise EvidenceError(f"{where} escapes bundle root: {member!r}") from exc
    if not stat.S_ISREG(resolved.stat().st_mode):
        raise EvidenceError(f"{where} is not a regular file: {member!r}")
    return resolved


def relative_regular_file(root: Path, path: Path, where: str) -> str:
    root = root.resolve(strict=True)
    if path.is_symlink():
        raise EvidenceError(f"{where} must not be a symlink: {path}")
    resolved = path.resolve(strict=True)
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise EvidenceError(f"{where} is outside manifest root: {path}") from exc
    _reject_symlink_chain(root, resolved, where)
    if not stat.S_ISREG(resolved.stat().st_mode):
        raise EvidenceError(f"{where} is not a regular file: {path}")
    return relative.as_posix()


def read_closed_manifest(
    manifest_path: Path,
    *,
    excluded: set[str] | None = None,
) -> tuple[Path, dict[str, str]]:
    excluded = excluded or set()
    if manifest_path.is_symlink():
        raise EvidenceError(f"manifest must not be a symlink: {manifest_path}")
    manifest = manifest_path.resolve(strict=True)
    if not stat.S_ISREG(manifest.stat().st_mode):
        raise EvidenceError(f"manifest is not a regular file: {manifest}")
    root = manifest.parent.resolve(strict=True)
    listed: dict[str, str] = {}
    for line_number, line in enumerate(
        manifest.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if "  " not in line:
            raise EvidenceError(f"manifest invalid line {line_number}")
        expected, relative = line.split("  ", 1)
        if not SHA256_RE.fullmatch(expected):
            raise EvidenceError(f"manifest invalid SHA256 on line {line_number}")
        if relative in listed:
            raise EvidenceError(f"manifest duplicate path: {relative}")
        path = resolve_bundle_file(root, relative, f"manifest line {line_number}")
        if relative in excluded:
            raise EvidenceError(f"manifest must not list excluded path: {relative}")
        actual = sha256_file(path)
        if actual != expected:
            raise EvidenceError(
                f"manifest hash mismatch: {relative}: expected={expected} actual={actual}"
            )
        listed[relative] = expected

    actual: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise EvidenceError(f"bundle contains symlink: {path}")
        if path.is_file() and path != manifest:
            relative = path.relative_to(root).as_posix()
            if relative not in excluded:
                actual.add(relative)
    if set(listed) != actual:
        missing = sorted(actual - set(listed))
        outside = sorted(set(listed) - actual)
        raise EvidenceError(
            f"manifest closure mismatch: unlisted={missing} non_payload={outside}"
        )
    return root, listed


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def write_json(path: Path, value: Any) -> None:
    data = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()
    write_bytes(path, data)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise EvidenceError(f"JSON object required: {path}")
    return value


def ensure_safe_serial(serial: str) -> None:
    normalized = serial.strip().lower()
    if not normalized:
        raise EvidenceError("empty serial")
    if any(normalized.startswith(prefix) for prefix in FORBIDDEN_SERIAL_PREFIXES):
        raise EvidenceError(f"serial {serial} is explicitly excluded from this tool")


def ensure_safe_process_names(process_names: Iterable[str]) -> list[str]:
    result = list(dict.fromkeys(process_names))
    for process_name in result:
        if not isinstance(process_name, str) or not PROCESS_NAME_RE.fullmatch(process_name):
            raise EvidenceError(f"invalid exact process name: {process_name!r}")
    return result


def run_process(argv: list[str], timeout: int = 30) -> bytes:
    completed = subprocess.run(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=timeout,
    )
    if completed.returncode != 0:
        rendered = " ".join(shlex.quote(item) for item in argv)
        output = completed.stdout.decode("utf-8", errors="replace")
        raise EvidenceError(f"command failed rc={completed.returncode}: {rendered}\n{output}")
    return completed.stdout


def ensure_target_online(hdc: str, serial: str) -> bytes:
    ensure_safe_serial(serial)
    output = run_process([hdc, "list", "targets"])
    targets = {line.strip() for line in output.decode(errors="replace").splitlines()}
    if serial not in targets:
        raise EvidenceError(f"target not online: {serial}")
    return output


def hdc_shell(hdc: str, serial: str, command: str, timeout: int = 30) -> bytes:
    ensure_safe_serial(serial)
    return run_process([hdc, "-t", serial, "shell", command], timeout=timeout)


def decode(data: bytes) -> str:
    return data.decode("utf-8", errors="replace").strip()


def first_nonempty_line(data: bytes) -> str:
    for line in decode(data).splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def parse_uptime(data: bytes) -> float:
    try:
        return float(first_nonempty_line(data).split()[0])
    except (ValueError, IndexError) as exc:
        raise EvidenceError(f"invalid /proc/uptime: {decode(data)!r}") from exc


def parse_ps(data: bytes) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for line in decode(data).splitlines():
        fields = line.strip().split(None, 4)
        if len(fields) < 4 or fields[0] == "PID":
            continue
        try:
            pid, uid, gid = map(int, fields[:3])
        except ValueError:
            continue
        result.append(
            {
                "pid": pid,
                "uid": uid,
                "gid": gid,
                "name": fields[3],
                "args": fields[4] if len(fields) == 5 else "",
            }
        )
    return result


def parse_remote_hash(data: bytes, remote_path: str) -> str:
    fields = first_nonempty_line(data).split()
    if not fields or not SHA256_RE.fullmatch(fields[0]):
        raise EvidenceError(f"cannot parse sha256sum for {remote_path}: {decode(data)!r}")
    return fields[0]


def parse_file_label(data: bytes, remote_path: str) -> str:
    for token in decode(data).split():
        if token.startswith("u:") and SELINUX_CONTEXT_RE.fullmatch(token):
            return token
    raise EvidenceError(f"cannot parse SELinux label for {remote_path}: {decode(data)!r}")


def parse_status_identity(data: bytes) -> dict[str, int]:
    values: dict[str, int] = {}
    for line in decode(data).splitlines():
        if line.startswith("Pid:"):
            values["pid"] = int(line.split()[1])
        elif line.startswith("PPid:"):
            values["ppid"] = int(line.split()[1])
        elif line.startswith("Uid:"):
            values["uid"] = int(line.split()[1])
        elif line.startswith("Gid:"):
            values["gid"] = int(line.split()[1])
    return values


def capture_snapshot(
    *,
    hdc: str,
    serial: str,
    label_paths: Iterable[str],
    process_names: Iterable[str],
    raw_dir: Path,
    phase: str,
) -> dict[str, Any]:
    targets = ensure_target_online(hdc, serial)
    enforcing_raw = hdc_shell(hdc, serial, "getenforce")
    boot_raw = hdc_shell(hdc, serial, "cat /proc/sys/kernel/random/boot_id")
    uptime_raw = hdc_shell(hdc, serial, "cat /proc/uptime")
    version_raw = hdc_shell(hdc, serial, "param get const.product.software.version")
    uname_raw = hdc_shell(hdc, serial, "uname -a")
    ps_raw = hdc_shell(hdc, serial, "ps -A -o PID,UID,GID,NAME,ARGS")
    hilog_raw = hdc_shell(hdc, serial, "hilog -x", timeout=60)

    raw_values = {
        "targets.txt": targets,
        "getenforce.txt": enforcing_raw,
        "boot-id.txt": boot_raw,
        "uptime.txt": uptime_raw,
        "software-version.txt": version_raw,
        "uname.txt": uname_raw,
        "ps.txt": ps_raw,
        "hilog.txt": hilog_raw,
    }
    raw_hashes: dict[str, str] = {}
    for name, data in raw_values.items():
        relative = f"raw/{phase}-{name}"
        write_bytes(raw_dir.parent / relative, data)
        raw_hashes[relative] = sha256_bytes(data)

    files: dict[str, Any] = {}
    for index, remote_path in enumerate(dict.fromkeys(label_paths)):
        quoted = shlex.quote(remote_path)
        hash_raw = hdc_shell(hdc, serial, f"sha256sum -- {quoted}")
        label_raw = hdc_shell(hdc, serial, f"ls -ldZ -- {quoted}")
        hash_relative = f"raw/{phase}-file-{index:02d}.sha256"
        label_relative = f"raw/{phase}-file-{index:02d}.label"
        write_bytes(raw_dir.parent / hash_relative, hash_raw)
        write_bytes(raw_dir.parent / label_relative, label_raw)
        raw_hashes[hash_relative] = sha256_bytes(hash_raw)
        raw_hashes[label_relative] = sha256_bytes(label_raw)
        files[remote_path] = {
            "sha256": parse_remote_hash(hash_raw, remote_path),
            "selinux_label": parse_file_label(label_raw, remote_path),
            "raw_hash": hash_relative,
            "raw_label": label_relative,
        }

    ps_rows = parse_ps(ps_raw)
    processes: dict[str, list[dict[str, Any]]] = {}
    for process_name in dict.fromkeys(process_names):
        matches: list[dict[str, Any]] = []
        for row in ps_rows:
            if row["name"] != process_name:
                continue
            pid = row["pid"]
            context_raw = hdc_shell(hdc, serial, f"cat /proc/{pid}/attr/current")
            exe_raw = hdc_shell(hdc, serial, f"readlink /proc/{pid}/exe")
            status_raw = hdc_shell(
                hdc,
                serial,
                f"grep -E '^(Name|Pid|PPid|Uid|Gid):' /proc/{pid}/status",
            )
            cmdline_raw = hdc_shell(hdc, serial, f"cat /proc/{pid}/cmdline")
            prefix = f"raw/{phase}-process-{process_name}-{pid}"
            for suffix, data in (
                ("context.txt", context_raw),
                ("exe.txt", exe_raw),
                ("status.txt", status_raw),
                ("cmdline.bin", cmdline_raw),
            ):
                relative = f"{prefix}-{suffix}"
                write_bytes(raw_dir.parent / relative, data)
                raw_hashes[relative] = sha256_bytes(data)
            status_identity = parse_status_identity(status_raw)
            matches.append(
                {
                    **row,
                    **status_identity,
                    "selinux_context": first_nonempty_line(context_raw),
                    "exe": first_nonempty_line(exe_raw),
                    "cmdline_sha256": sha256_bytes(cmdline_raw),
                }
            )
        processes[process_name] = matches

    return {
        "captured_at": utc_now(),
        "serial": serial,
        "enforcing": first_nonempty_line(enforcing_raw),
        "boot_id": first_nonempty_line(boot_raw).lower(),
        "uptime_seconds": parse_uptime(uptime_raw),
        "software_version": first_nonempty_line(version_raw),
        "uname": first_nonempty_line(uname_raw),
        "files": files,
        "processes": processes,
        "hilog_relative_path": f"raw/{phase}-hilog.txt",
        "hilog_sha256": sha256_bytes(hilog_raw),
        "raw_sha256": raw_hashes,
    }


def validate_snapshot(
    snapshot: dict[str, Any],
    expected_hashes: dict[str, str],
    process_names: Iterable[str],
) -> list[str]:
    reasons: list[str] = []
    if snapshot.get("enforcing") != "Enforcing":
        reasons.append(f"SELINUX_NOT_ENFORCING:{snapshot.get('enforcing')!r}")
    boot_id = str(snapshot.get("boot_id", ""))
    if not BOOT_ID_RE.fullmatch(boot_id):
        reasons.append(f"INVALID_BOOT_ID:{boot_id!r}")
    if not expected_hashes:
        reasons.append("NO_EXPECTED_ARTIFACT_HASH")
    files = snapshot.get("files", {})
    for remote_path, expected_hash in expected_hashes.items():
        actual = files.get(remote_path, {}).get("sha256")
        if actual != expected_hash:
            reasons.append(
                f"ARTIFACT_HASH_MISMATCH:{remote_path}:expected={expected_hash}:actual={actual}"
            )
    for remote_path, fact in files.items():
        label = fact.get("selinux_label", "")
        if not SELINUX_CONTEXT_RE.fullmatch(label):
            reasons.append(f"INVALID_FILE_LABEL:{remote_path}:{label!r}")
    processes = snapshot.get("processes", {})
    for process_name in process_names:
        matches = processes.get(process_name, [])
        if not matches:
            reasons.append(f"PROCESS_NOT_FOUND:{process_name}")
            continue
        for match in matches:
            context = match.get("selinux_context", "")
            if not SELINUX_CONTEXT_RE.fullmatch(context):
                reasons.append(
                    f"INVALID_PROCESS_CONTEXT:{process_name}:{match.get('pid')}:{context!r}"
                )
    return reasons


def _validate_card1_build_receipt(value: Any) -> dict[str, Any]:
    receipt = require_object(value, "card1.build_receipt")
    require_exact_keys(
        receipt,
        "card1.build_receipt",
        {
            "schema_version",
            "action_id",
            "generation_id",
            "generation_digest",
            "captured_at",
            "target",
            "status",
            "config",
            "source_manifest",
            "builder",
            "stages",
            "artifacts",
            "semantics",
            "receipt_body_sha256",
        },
    )
    if receipt["schema_version"] != CARD1_BUILD_SCHEMA:
        raise EvidenceError(
            f"unsupported card1 build schema: {receipt['schema_version']!r}"
        )
    verify_card1_body_digest(receipt, "card1.build_receipt")
    action_id = require_string(receipt["action_id"], "card1.build_receipt.action_id")
    if action_id not in ACTION_IDS:
        raise EvidenceError(f"card1 build receipt Action is outside Fn01 A01-A04: {action_id}")
    require_string(receipt["generation_id"], "card1.build_receipt.generation_id")
    generation_digest = require_string(
        receipt["generation_digest"], "card1.build_receipt.generation_digest"
    )
    if not SHA256_RE.fullmatch(generation_digest):
        raise EvidenceError("card1 build receipt generation_digest is invalid")

    status = require_object(receipt["status"], "card1.build_receipt.status")
    require_exact_keys(
        status,
        "card1.build_receipt.status",
        {
            "build_pass",
            "host_scope_build_pass",
            "target_scope_build_pass",
            "target_deployment_generation_bound",
            "device_verified",
            "formal_verdict",
        },
    )
    for field in (
        "build_pass",
        "host_scope_build_pass",
        "target_scope_build_pass",
        "target_deployment_generation_bound",
        "device_verified",
    ):
        require_bool(status[field], f"card1.build_receipt.status.{field}")
    if (
        not status["build_pass"]
        or not status["host_scope_build_pass"]
        or not status["target_scope_build_pass"]
        or status["target_deployment_generation_bound"]
        or status["device_verified"]
        or status["formal_verdict"] != "NOT_ISSUED"
    ):
        raise EvidenceError("card1 build receipt status is not an admitted build handoff")

    semantics = require_object(
        receipt["semantics"], "card1.build_receipt.semantics"
    )
    require_exact_keys(
        semantics,
        "card1.build_receipt.semantics",
        {
            "build_pass_is_not_device_verified",
            "deployment_byte_match_is_not_action_behavior_verification",
        },
    )
    if (
        semantics["build_pass_is_not_device_verified"] is not True
        or semantics[
            "deployment_byte_match_is_not_action_behavior_verification"
        ]
        is not True
    ):
        raise EvidenceError("card1 build receipt semantics are unsafe")

    artifacts = require_array(receipt["artifacts"], "card1.build_receipt.artifacts")
    if not artifacts:
        raise EvidenceError("card1 build receipt contains no artifacts")
    roles: set[str] = set()
    paths: set[str] = set()
    for index, raw in enumerate(artifacts):
        artifact = require_object(raw, f"card1.build_receipt.artifacts[{index}]")
        require_exact_keys(
            artifact,
            f"card1.build_receipt.artifacts[{index}]",
            {
                "role",
                "kind",
                "local_path",
                "device_path",
                "producer_stage",
                "sha256",
                "bytes",
            },
            {"file_identity", "elf_build_id"},
        )
        role = require_string(
            artifact["role"], f"card1.build_receipt.artifacts[{index}].role"
        )
        if role in roles:
            raise EvidenceError(f"duplicate card1 build artifact role: {role}")
        roles.add(role)
        device_path = require_string(
            artifact["device_path"],
            f"card1.build_receipt.artifacts[{index}].device_path",
        )
        if (
            not device_path.startswith("/")
            or any(part in {".", ".."} for part in Path(device_path).parts)
            or device_path in paths
        ):
            raise EvidenceError(f"invalid or duplicate card1 device path: {device_path}")
        paths.add(device_path)
        digest = require_string(
            artifact["sha256"],
            f"card1.build_receipt.artifacts[{index}].sha256",
        )
        if not SHA256_RE.fullmatch(digest):
            raise EvidenceError(f"invalid card1 artifact SHA256: {role}")
        if (
            not isinstance(artifact["bytes"], int)
            or isinstance(artifact["bytes"], bool)
            or artifact["bytes"] < 0
        ):
            raise EvidenceError(f"invalid card1 artifact size: {role}")
    return receipt


def _validate_card1_device_receipt(value: Any) -> dict[str, Any]:
    receipt = require_object(value, "card1.device_receipt")
    require_exact_keys(
        receipt,
        "card1.device_receipt",
        {
            "schema_version",
            "action_id",
            "generation_id",
            "captured_at",
            "build_receipt",
            "collector",
            "device",
            "deployed_artifacts",
            "status",
            "semantics",
            "receipt_body_sha256",
        },
    )
    if receipt["schema_version"] != CARD1_DEVICE_SCHEMA:
        raise EvidenceError(
            f"unsupported card1 device schema: {receipt['schema_version']!r}"
        )
    verify_card1_body_digest(receipt, "card1.device_receipt")
    require_string(receipt["action_id"], "card1.device_receipt.action_id")
    require_string(receipt["generation_id"], "card1.device_receipt.generation_id")

    build_ref = require_object(
        receipt["build_receipt"], "card1.device_receipt.build_receipt"
    )
    require_exact_keys(
        build_ref,
        "card1.device_receipt.build_receipt",
        {"path", "sha256", "body_sha256"},
    )
    require_string(build_ref["path"], "card1.device_receipt.build_receipt.path")
    for field in ("sha256", "body_sha256"):
        if not SHA256_RE.fullmatch(
            require_string(
                build_ref[field], f"card1.device_receipt.build_receipt.{field}"
            )
        ):
            raise EvidenceError(f"invalid card1 device build reference {field}")

    collector = require_object(
        receipt["collector"], "card1.device_receipt.collector"
    )
    require_exact_keys(
        collector,
        "card1.device_receipt.collector",
        {"hdc_path", "hdc_sha256", "hdc_version"},
    )
    require_string(collector["hdc_path"], "card1.device_receipt.collector.hdc_path")
    if not SHA256_RE.fullmatch(
        require_string(
            collector["hdc_sha256"], "card1.device_receipt.collector.hdc_sha256"
        )
    ):
        raise EvidenceError("invalid card1 collector hdc_sha256")
    require_string(
        collector["hdc_version"], "card1.device_receipt.collector.hdc_version"
    )

    device = require_object(receipt["device"], "card1.device_receipt.device")
    require_exact_keys(
        device,
        "card1.device_receipt.device",
        {
            "serial",
            "boot_id_before",
            "boot_id_after",
            "os_version",
            "security_mode",
        },
    )
    ensure_safe_serial(
        require_string(device["serial"], "card1.device_receipt.device.serial")
    )
    boot_before = require_string(
        device["boot_id_before"], "card1.device_receipt.device.boot_id_before"
    ).lower()
    boot_after = require_string(
        device["boot_id_after"], "card1.device_receipt.device.boot_id_after"
    ).lower()
    if not BOOT_ID_RE.fullmatch(boot_before) or boot_before != boot_after:
        raise EvidenceError("card1 device receipt boot identity is invalid or unstable")
    require_string(device["os_version"], "card1.device_receipt.device.os_version")
    require_string(
        device["security_mode"], "card1.device_receipt.device.security_mode"
    )

    status = require_object(receipt["status"], "card1.device_receipt.status")
    require_exact_keys(
        status,
        "card1.device_receipt.status",
        {
            "read_only_capture_complete",
            "target_deployment_generation_bound",
            "device_verified",
            "formal_verdict",
        },
    )
    for field in (
        "read_only_capture_complete",
        "target_deployment_generation_bound",
        "device_verified",
    ):
        require_bool(status[field], f"card1.device_receipt.status.{field}")
    if (
        not status["read_only_capture_complete"]
        or status["target_deployment_generation_bound"]
        or status["device_verified"]
        or status["formal_verdict"] != "NOT_ISSUED"
    ):
        raise EvidenceError("card1 device receipt status is not an admitted capture")

    semantics = require_object(
        receipt["semantics"], "card1.device_receipt.semantics"
    )
    require_exact_keys(
        semantics,
        "card1.device_receipt.semantics",
        {
            "capture_performed_no_deployment",
            "deployment_byte_match_is_not_action_behavior_verification",
        },
    )
    if (
        semantics["capture_performed_no_deployment"] is not True
        or semantics[
            "deployment_byte_match_is_not_action_behavior_verification"
        ]
        is not True
    ):
        raise EvidenceError("card1 device receipt semantics are unsafe")

    deployed = require_array(
        receipt["deployed_artifacts"], "card1.device_receipt.deployed_artifacts"
    )
    if not deployed:
        raise EvidenceError("card1 device receipt contains no deployed artifacts")
    roles: set[str] = set()
    for index, raw in enumerate(deployed):
        artifact = require_object(
            raw, f"card1.device_receipt.deployed_artifacts[{index}]"
        )
        require_exact_keys(
            artifact,
            f"card1.device_receipt.deployed_artifacts[{index}]",
            {"role", "device_path", "sha256", "bytes"},
        )
        role = require_string(
            artifact["role"],
            f"card1.device_receipt.deployed_artifacts[{index}].role",
        )
        if role in roles:
            raise EvidenceError(f"duplicate card1 deployed artifact role: {role}")
        roles.add(role)
        require_string(
            artifact["device_path"],
            f"card1.device_receipt.deployed_artifacts[{index}].device_path",
        )
        if not SHA256_RE.fullmatch(
            require_string(
                artifact["sha256"],
                f"card1.device_receipt.deployed_artifacts[{index}].sha256",
            )
        ):
            raise EvidenceError(f"invalid card1 deployed artifact SHA256: {role}")
        if (
            not isinstance(artifact["bytes"], int)
            or isinstance(artifact["bytes"], bool)
            or artifact["bytes"] < 0
        ):
            raise EvidenceError(f"invalid card1 deployed artifact size: {role}")
    return receipt


def _validate_card1_gate_report(value: Any) -> dict[str, Any]:
    receipt = require_object(value, "card1.gate_report")
    require_exact_keys(
        receipt,
        "card1.gate_report",
        {
            "schema_version",
            "action_id",
            "generation_id",
            "checked_at",
            "build_receipt",
            "device_receipt",
            "device_serial",
            "gate_status",
            "status",
            "failures",
            "semantics",
            "receipt_body_sha256",
        },
    )
    if receipt["schema_version"] != CARD1_GATE_SCHEMA:
        raise EvidenceError(
            f"unsupported card1 gate schema: {receipt['schema_version']!r}"
        )
    verify_card1_body_digest(receipt, "card1.gate_report")
    require_string(receipt["action_id"], "card1.gate_report.action_id")
    require_string(receipt["generation_id"], "card1.gate_report.generation_id")
    ensure_safe_serial(
        require_string(receipt["device_serial"], "card1.gate_report.device_serial")
    )
    if receipt["gate_status"] != "PASS":
        raise EvidenceError(f"card1 gate is not PASS: {receipt['gate_status']!r}")
    failures = require_array(receipt["failures"], "card1.gate_report.failures")
    if failures:
        raise EvidenceError("card1 PASS gate contains failures")

    for name in ("build_receipt", "device_receipt"):
        reference = require_object(
            receipt[name], f"card1.gate_report.{name}"
        )
        require_exact_keys(
            reference, f"card1.gate_report.{name}", {"path", "sha256"}
        )
        require_string(reference["path"], f"card1.gate_report.{name}.path")
        if not SHA256_RE.fullmatch(
            require_string(
                reference["sha256"], f"card1.gate_report.{name}.sha256"
            )
        ):
            raise EvidenceError(f"invalid card1 gate {name} SHA256")

    status = require_object(receipt["status"], "card1.gate_report.status")
    require_exact_keys(
        status,
        "card1.gate_report.status",
        {
            "build_pass",
            "host_scope_build_pass",
            "target_scope_build_pass",
            "target_deployment_generation_bound",
            "device_verified",
            "formal_verdict",
        },
    )
    for field in (
        "build_pass",
        "host_scope_build_pass",
        "target_scope_build_pass",
        "target_deployment_generation_bound",
        "device_verified",
    ):
        require_bool(status[field], f"card1.gate_report.status.{field}")
    if (
        not status["build_pass"]
        or not status["host_scope_build_pass"]
        or not status["target_scope_build_pass"]
        or not status["target_deployment_generation_bound"]
        or status["device_verified"]
        or status["formal_verdict"] != "NOT_ISSUED"
    ):
        raise EvidenceError("card1 gate status does not prove deployment generation")

    semantics = require_object(
        receipt["semantics"], "card1.gate_report.semantics"
    )
    require_exact_keys(
        semantics,
        "card1.gate_report.semantics",
        {
            "pass_means_exact_deployed_bytes_for_same_generation",
            "pass_does_not_mean_action_behavior_device_verified",
            "independent_action_verifier_still_required",
        },
    )
    if any(value is not True for value in semantics.values()):
        raise EvidenceError("card1 gate semantics are unsafe")
    return receipt


def _find_unique_manifest_payload(
    root: Path,
    listed: Mapping[str, str],
    digest: str,
    where: str,
) -> tuple[str, Path]:
    matches = [relative for relative, value in listed.items() if value == digest]
    if len(matches) != 1:
        raise EvidenceError(
            f"{where} must resolve to exactly one manifest payload, found={matches}"
        )
    relative = matches[0]
    return relative, resolve_bundle_file(root, relative, where)


def load_card1_provenance_bundle(
    manifest_path: Path,
    gate_report_path: Path,
    *,
    expected_action_id: str,
    expected_serial: str,
) -> tuple[dict[str, Any], dict[str, str], Path, dict[str, str]]:
    root, listed = read_closed_manifest(manifest_path)
    gate_relative = relative_regular_file(
        root, gate_report_path, "card1 gate report"
    )
    if gate_relative not in listed:
        raise EvidenceError("card1 gate report is not listed by its manifest")
    gate_path = resolve_bundle_file(root, gate_relative, "card1 gate report")
    if sha256_file(gate_path) != listed[gate_relative]:
        raise EvidenceError("card1 gate report manifest hash mismatch")
    gate = _validate_card1_gate_report(load_json(gate_path))

    build_relative, build_path = _find_unique_manifest_payload(
        root,
        listed,
        gate["build_receipt"]["sha256"],
        "card1 build receipt",
    )
    device_relative, device_path = _find_unique_manifest_payload(
        root,
        listed,
        gate["device_receipt"]["sha256"],
        "card1 device receipt",
    )
    build = _validate_card1_build_receipt(load_json(build_path))
    device = _validate_card1_device_receipt(load_json(device_path))

    if gate["action_id"] != expected_action_id:
        raise EvidenceError(
            "card1 gate Action does not match Enforcing Action; "
            "cross-Action coverage is not present in card1 v1"
        )
    if gate["device_serial"] != expected_serial:
        raise EvidenceError(
            f"card1 gate serial mismatch: expected={expected_serial} "
            f"actual={gate['device_serial']}"
        )
    if (
        build["action_id"] != gate["action_id"]
        or device["action_id"] != gate["action_id"]
        or build["generation_id"] != gate["generation_id"]
        or device["generation_id"] != gate["generation_id"]
    ):
        raise EvidenceError("card1 receipt Action/generation chain is inconsistent")
    if device["device"]["serial"] != expected_serial:
        raise EvidenceError("card1 device receipt serial differs from gate serial")
    if (
        device["build_receipt"]["sha256"] != sha256_file(build_path)
        or device["build_receipt"]["body_sha256"]
        != build["receipt_body_sha256"]
    ):
        raise EvidenceError("card1 device receipt is not bound to the manifest build receipt")

    built_by_role = {item["role"]: item for item in build["artifacts"]}
    deployed_by_role = {item["role"]: item for item in device["deployed_artifacts"]}
    if set(built_by_role) != set(deployed_by_role):
        raise EvidenceError("card1 built/deployed artifact roles are not identical")
    expected_hashes: dict[str, str] = {}
    for role, built in built_by_role.items():
        deployed = deployed_by_role[role]
        if (
            deployed["device_path"] != built["device_path"]
            or deployed["sha256"] != built["sha256"]
            or deployed["bytes"] != built["bytes"]
        ):
            raise EvidenceError(f"card1 built/deployed artifact mismatch: {role}")
        expected_hashes[built["device_path"]] = built["sha256"]
    if not expected_hashes:
        raise EvidenceError("card1 provenance imports no expected artifact hashes")

    metadata = {
        "adapter_schema": CARD1_ADAPTER_SCHEMA,
        "manifest_sha256": sha256_file(manifest_path.resolve(strict=True)),
        "gate_report_path": gate_relative,
        "gate_report_sha256": sha256_file(gate_path),
        "build_receipt_path": build_relative,
        "build_receipt_sha256": sha256_file(build_path),
        "device_receipt_path": device_relative,
        "device_receipt_sha256": sha256_file(device_path),
        "action_id": gate["action_id"],
        "generation_id": gate["generation_id"],
        "device_serial": expected_serial,
        "device_boot_id": device["device"]["boot_id_before"].lower(),
        "expected_hashes": expected_hashes,
        "formal_verdict": "NOT_ISSUED",
        "device_verified": False,
    }
    return metadata, expected_hashes, root, listed


def freeze_card1_provenance_bundle(
    run_dir: Path,
    manifest_path: Path,
    gate_report_path: Path,
    *,
    expected_action_id: str,
    expected_serial: str,
) -> tuple[dict[str, Any], dict[str, str]]:
    metadata, expected_hashes, source_root, listed = load_card1_provenance_bundle(
        manifest_path,
        gate_report_path,
        expected_action_id=expected_action_id,
        expected_serial=expected_serial,
    )
    destination = run_dir / "inputs/provenance"
    destination.mkdir(parents=True, exist_ok=False)
    for relative in sorted(listed):
        source = resolve_bundle_file(
            source_root, relative, f"card1 provenance payload {relative}"
        )
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    shutil.copyfile(manifest_path.resolve(strict=True), destination / "MANIFEST.sha256")
    frozen_gate = destination / metadata["gate_report_path"]
    frozen_metadata, frozen_hashes, _, _ = load_card1_provenance_bundle(
        destination / "MANIFEST.sha256",
        frozen_gate,
        expected_action_id=expected_action_id,
        expected_serial=expected_serial,
    )
    frozen_metadata["bundle_path"] = "inputs/provenance"
    if frozen_metadata != {**metadata, "bundle_path": "inputs/provenance"}:
        raise EvidenceError("frozen card1 provenance metadata changed while copying")
    if frozen_hashes != expected_hashes:
        raise EvidenceError("frozen card1 expected hashes changed while copying")
    return frozen_metadata, frozen_hashes


def validate_frozen_card1_provenance(
    run_dir: Path, session: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, str]]:
    recorded = require_object(session.get("provenance"), "session.provenance")
    bundle_relative = recorded.get("bundle_path")
    if bundle_relative != "inputs/provenance":
        raise EvidenceError("session provenance bundle path is unsupported")
    bundle = run_dir / "inputs/provenance"
    gate_relative = require_string(
        recorded.get("gate_report_path"), "session.provenance.gate_report_path"
    )
    metadata, expected_hashes, _, _ = load_card1_provenance_bundle(
        bundle / "MANIFEST.sha256",
        bundle / gate_relative,
        expected_action_id=require_string(session.get("action_id"), "session.action_id"),
        expected_serial=require_string(
            session.get("original_serial"), "session.original_serial"
        ),
    )
    metadata["bundle_path"] = "inputs/provenance"
    if metadata != recorded:
        raise EvidenceError("frozen card1 provenance metadata differs from session")
    return metadata, expected_hashes


def capture_contract_inputs(
    root: Path, run_dir: Path, action_id: str
) -> dict[str, dict[str, str]]:
    action_leaf = action_id.split(".", 1)[1]
    sources = {
        "definition": root / f"docs/spec/atoms/Fn01/{action_leaf}/atom.yaml",
        "verification": root / f"docs/spec/atoms/Fn01/{action_leaf}/verification.md",
        "implementation": root / f"src/atoms/Fn01/{action_leaf}/IMPLEMENTATION.yaml",
    }
    result: dict[str, dict[str, str]] = {}
    for role, source in sources.items():
        if not source.is_file():
            raise EvidenceError(f"required {role} input missing: {source}")
        data = source.read_bytes()
        suffix = source.suffix or ".bin"
        stored = run_dir / f"inputs/{role}{suffix}"
        write_bytes(stored, data)
        result[role] = {
            "source_path": str(source.resolve()),
            "stored_path": str(stored.relative_to(run_dir)),
            "sha256": sha256_bytes(data),
        }
    return result


def compute_hilog_delta(before: bytes, after: bytes) -> tuple[bytes, bool]:
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    if not before_lines:
        return after, True
    if len(after_lines) >= len(before_lines) and after_lines[: len(before_lines)] == before_lines:
        return b"".join(after_lines[len(before_lines) :]), True
    if not after_lines:
        return b"", False
    candidate_starts = [
        index for index, line in enumerate(before_lines) if line == after_lines[0]
    ]
    best_overlap = 0
    for start in candidate_starts:
        overlap = min(len(before_lines) - start, len(after_lines))
        if before_lines[start : start + overlap] == after_lines[:overlap]:
            best_overlap = max(best_overlap, overlap)
    minimum_overlap = min(20, len(before_lines))
    if best_overlap < minimum_overlap:
        return b"", False
    return b"".join(after_lines[best_overlap:]), True


def verify_raw_hashes(run_dir: Path, snapshot: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    for relative, expected in snapshot.get("raw_sha256", {}).items():
        try:
            path = resolve_bundle_file(run_dir, relative, f"raw file {relative}")
        except (EvidenceError, OSError) as exc:
            reasons.append(f"RAW_FILE_INVALID:{relative}:{exc}")
            continue
        actual = sha256_file(path)
        if actual != expected:
            reasons.append(f"RAW_HASH_MISMATCH:{relative}:expected={expected}:actual={actual}")
    return reasons


def verify_manifest(run_dir: Path) -> list[str]:
    try:
        read_closed_manifest(
            run_dir / "MANIFEST.sha256",
            excluded={"validation.replay.json"},
        )
        return []
    except (EvidenceError, OSError, UnicodeError) as exc:
        return [f"BUNDLE_MANIFEST_INVALID:{exc}"]


def verify_normalized_receipt_integrity(
    run_dir: Path, receipt: dict[str, Any]
) -> list[str]:
    reasons: list[str] = []
    stored_relative = receipt.get("stored_receipt")
    source_digest = receipt.get("source_receipt_sha256")
    if not isinstance(stored_relative, str) or not SHA256_RE.fullmatch(
        str(source_digest)
    ):
        return ["RECEIPT_SOURCE_IDENTITY_MISSING"]
    try:
        stored_path = resolve_bundle_file(
            run_dir, stored_relative, "normalized receipt source"
        )
    except (EvidenceError, OSError) as exc:
        return [f"RECEIPT_SOURCE_INVALID:{exc}"]
    if sha256_file(stored_path) != source_digest:
        reasons.append("RECEIPT_SOURCE_HASH_MISMATCH")
        return reasons
    source = load_json(stored_path)
    for key, value in source.items():
        if receipt.get(key) != value:
            reasons.append(f"NORMALIZED_RECEIPT_DIVERGED:{key}")
    return reasons


def resolve_receipt_member(receipt_path: Path, member: str) -> Path:
    if receipt_path.is_symlink():
        raise EvidenceError(f"receipt must not be a symlink: {receipt_path}")
    receipt = receipt_path.resolve(strict=True)
    if not stat.S_ISREG(receipt.stat().st_mode):
        raise EvidenceError(f"receipt must be a regular file: {receipt_path}")
    return resolve_bundle_file(receipt.parent, member, "receipt member")


def normalize_receipt(
    *,
    run_dir: Path,
    source_receipt_path: Path,
    session: dict[str, Any],
) -> dict[str, Any]:
    if source_receipt_path.is_symlink():
        raise EvidenceError(f"request receipt must not be a symlink: {source_receipt_path}")
    source_receipt_path = source_receipt_path.resolve(strict=True)
    if not stat.S_ISREG(source_receipt_path.stat().st_mode):
        raise EvidenceError("request receipt must be a regular file")
    receipt = load_json(source_receipt_path)
    request_member = receipt.get("request_file")
    response_member = receipt.get("response_file")
    if not isinstance(request_member, str) or not isinstance(response_member, str):
        raise EvidenceError("receipt requires request_file and response_file")
    request_path = resolve_receipt_member(source_receipt_path, request_member)
    response_path = resolve_receipt_member(source_receipt_path, response_member)
    if not request_path.is_file() or not response_path.is_file():
        raise EvidenceError("receipt request_file/response_file must exist")
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    stored_receipt = raw_dir / "request-receipt.source.json"
    stored_request = raw_dir / "request.bin"
    stored_response = raw_dir / "response.bin"
    shutil.copyfile(source_receipt_path, stored_receipt)
    shutil.copyfile(request_path, stored_request)
    shutil.copyfile(response_path, stored_response)
    normalized = dict(receipt)
    normalized.update(
        {
            "source_receipt_sha256": sha256_file(stored_receipt),
            "stored_receipt": "raw/request-receipt.source.json",
            "stored_request": "raw/request.bin",
            "stored_response": "raw/response.bin",
            "request_file_sha256_actual": sha256_file(stored_request),
            "response_file_sha256_actual": sha256_file(stored_response),
            "normalized_at": utc_now(),
            "session_id": session["session_id"],
        }
    )
    write_json(run_dir / "normalized-receipt.json", normalized)
    return normalized


def validate_receipt_and_end(
    *,
    run_dir: Path,
    session: dict[str, Any],
    end_snapshot: dict[str, Any],
    receipt: dict[str, Any],
) -> tuple[list[str], dict[str, Any]]:
    reasons: list[str] = []
    start = session["device_start"]
    expected_hashes = session["expected_hashes"]
    process_names = session["process_names"]
    reasons.extend(validate_snapshot(end_snapshot, expected_hashes, process_names))
    reasons.extend(verify_raw_hashes(run_dir, start))
    reasons.extend(verify_raw_hashes(run_dir, end_snapshot))

    if end_snapshot.get("serial") != session.get("serial"):
        reasons.append("SERIAL_CHANGED")
    if end_snapshot.get("boot_id") != start.get("boot_id"):
        reasons.append("BOOT_ID_CHANGED")

    for process_name in process_names:
        before = {
            (
                item.get("pid"),
                item.get("uid"),
                item.get("gid"),
                item.get("name"),
                item.get("selinux_context"),
                item.get("exe"),
                item.get("cmdline_sha256"),
            )
            for item in start.get("processes", {}).get(process_name, [])
        }
        after = {
            (
                item.get("pid"),
                item.get("uid"),
                item.get("gid"),
                item.get("name"),
                item.get("selinux_context"),
                item.get("exe"),
                item.get("cmdline_sha256"),
            )
            for item in end_snapshot.get("processes", {}).get(process_name, [])
        }
        if before != after:
            reasons.append(f"PROCESS_IDENTITY_CHANGED:{process_name}")

    required_receipt_fields = (
        "schema_version",
        "action_id",
        "request_id",
        "serial",
        "boot_id",
        "started_uptime_seconds",
        "finished_uptime_seconds",
        "artifact_hashes",
        "contract_sha256",
        "request_sha256",
        "response_sha256",
        "request_process",
    )
    for field in required_receipt_fields:
        if field not in receipt:
            reasons.append(f"RECEIPT_FIELD_MISSING:{field}")

    if receipt.get("schema_version") != SCHEMA_VERSION:
        reasons.append("RECEIPT_SCHEMA_UNSUPPORTED")
    if receipt.get("action_id") != session.get("action_id"):
        reasons.append("RECEIPT_ACTION_MISMATCH")
    if receipt.get("serial") != session.get("serial"):
        reasons.append("RECEIPT_SERIAL_MISMATCH")
    if str(receipt.get("boot_id", "")).lower() != start.get("boot_id"):
        reasons.append("RECEIPT_BOOT_MISMATCH")

    request_id = receipt.get("request_id")
    if not isinstance(request_id, str) or not request_id.strip():
        reasons.append("RECEIPT_REQUEST_ID_INVALID")

    try:
        receipt_start = float(receipt["started_uptime_seconds"])
        receipt_end = float(receipt["finished_uptime_seconds"])
        if receipt_start < float(start["uptime_seconds"]) - 0.5:
            reasons.append("RECEIPT_STALE_BEFORE_CAPTURE")
        if receipt_end < receipt_start:
            reasons.append("RECEIPT_TIME_REVERSED")
        if receipt_end > float(end_snapshot["uptime_seconds"]) + 0.5:
            reasons.append("RECEIPT_AFTER_CAPTURE")
    except (KeyError, TypeError, ValueError):
        reasons.append("RECEIPT_UPTIME_INVALID")

    receipt_hashes = receipt.get("artifact_hashes")
    if not isinstance(receipt_hashes, dict):
        reasons.append("RECEIPT_ARTIFACT_HASHES_INVALID")
    else:
        for remote_path, expected_hash in expected_hashes.items():
            if receipt_hashes.get(remote_path) != expected_hash:
                reasons.append(f"RECEIPT_ARTIFACT_MISMATCH:{remote_path}")

    expected_contract_hashes = {
        role: fact["sha256"] for role, fact in session.get("contract_inputs", {}).items()
    }
    if receipt.get("contract_sha256") != expected_contract_hashes:
        reasons.append("RECEIPT_CONTRACT_HASH_MISMATCH")

    try:
        stored_request = resolve_bundle_file(
            run_dir,
            str(receipt.get("stored_request", "")),
            "stored request",
        )
        stored_response = resolve_bundle_file(
            run_dir,
            str(receipt.get("stored_response", "")),
            "stored response",
        )
    except (EvidenceError, OSError) as exc:
        reasons.append(f"STORED_REQUEST_RESPONSE_INVALID:{exc}")
    else:
        request_hash = sha256_file(stored_request)
        response_hash = sha256_file(stored_response)
        if receipt.get("request_sha256") != request_hash:
            reasons.append("REQUEST_HASH_MISMATCH")
        if receipt.get("response_sha256") != response_hash:
            reasons.append("RESPONSE_HASH_MISMATCH")
        if isinstance(request_id, str):
            request_bytes = stored_request.read_bytes()
            response_bytes = stored_response.read_bytes()
            encoded_request_id = request_id.encode()
            if encoded_request_id not in request_bytes:
                reasons.append("REQUEST_ID_NOT_IN_REQUEST")
            if encoded_request_id not in response_bytes:
                reasons.append("REQUEST_ID_NOT_IN_RESPONSE")

    request_process = receipt.get("request_process")
    if not isinstance(request_process, dict):
        reasons.append("REQUEST_PROCESS_INVALID")
    else:
        required_process_fields = ("pid", "uid", "gid", "name", "selinux_context")
        if any(field not in request_process for field in required_process_fields):
            reasons.append("REQUEST_PROCESS_INCOMPLETE")
        else:
            request_name = request_process.get("name")
            if request_name not in process_names:
                reasons.append("REQUEST_PROCESS_NOT_IN_BEGIN_WHITELIST")
            else:
                begin_rows = start.get("processes", {}).get(request_name, [])
                end_rows = end_snapshot.get("processes", {}).get(request_name, [])
                begin_matching = [
                    item
                    for item in begin_rows
                    if all(
                        item.get(field) == request_process.get(field)
                        for field in required_process_fields
                    )
                ]
                end_matching = [
                    item
                    for item in end_rows
                    if all(
                        item.get(field) == request_process.get(field)
                        for field in required_process_fields
                    )
                ]
                if len(begin_matching) != 1:
                    reasons.append("REQUEST_PROCESS_NOT_UNIQUE_IN_BEGIN_SNAPSHOT")
                if len(end_matching) != 1:
                    reasons.append("REQUEST_PROCESS_NOT_UNIQUE_IN_END_SNAPSHOT")
                if len(begin_matching) == 1 and len(end_matching) == 1:
                    identity_fields = (
                        "pid",
                        "uid",
                        "gid",
                        "name",
                        "selinux_context",
                        "exe",
                        "cmdline_sha256",
                    )
                    before_identity = tuple(
                        begin_matching[0].get(field) for field in identity_fields
                    )
                    after_identity = tuple(
                        end_matching[0].get(field) for field in identity_fields
                    )
                    if before_identity != after_identity:
                        reasons.append("REQUEST_PROCESS_IDENTITY_CHANGED")

    try:
        before_hilog_path = resolve_bundle_file(
            run_dir, start["hilog_relative_path"], "begin hilog"
        )
        after_hilog_path = resolve_bundle_file(
            run_dir, end_snapshot["hilog_relative_path"], "end hilog"
        )
        before_hilog = before_hilog_path.read_bytes()
        after_hilog = after_hilog_path.read_bytes()
    except (KeyError, EvidenceError, OSError) as exc:
        reasons.append(f"HILOG_PATH_INVALID:{exc}")
        before_hilog = b""
        after_hilog = b""
    delta, log_window_valid = compute_hilog_delta(before_hilog, after_hilog)
    write_bytes(run_dir / "raw/hilog-window.delta", delta)
    if not log_window_valid:
        reasons.append("HILOG_WINDOW_STALE_OR_ROTATED")
    denial_lines = [
        line for line in delta.decode("utf-8", errors="replace").splitlines() if DENIAL_RE.search(line)
    ]
    write_bytes(
        run_dir / "raw/selinux-denials.delta",
        (("\n".join(denial_lines) + "\n") if denial_lines else "").encode(),
    )
    request_id_token = request_id if isinstance(request_id, str) else ""
    bound_names = set(process_names)
    bound_contexts: set[str] = set()
    bound_pids: set[int] = set()
    for snapshot in (start, end_snapshot):
        for process_name in process_names:
            for item in snapshot.get("processes", {}).get(process_name, []):
                context = item.get("selinux_context")
                if isinstance(context, str) and context:
                    bound_contexts.add(context)
                pid = item.get("pid")
                if isinstance(pid, int) and not isinstance(pid, bool):
                    bound_pids.add(pid)
    if isinstance(request_process, dict):
        name = request_process.get("name")
        if isinstance(name, str) and name:
            bound_names.add(name)
        context = request_process.get("selinux_context")
        if isinstance(context, str) and context:
            bound_contexts.add(context)
        pid = request_process.get("pid")
        if isinstance(pid, int) and not isinstance(pid, bool):
            bound_pids.add(pid)

    def denial_is_relevant(line: str) -> bool:
        if request_id_token and request_id_token in line:
            return True
        for pid in bound_pids:
            if re.search(rf"(?:^|[\s,(])pid[=:]\s*{pid}(?:\D|$)", line):
                return True
        for name in bound_names:
            escaped = re.escape(name)
            if re.search(
                rf"(?:comm|name|process)[=:]\s*[\"']?{escaped}(?:[\"'\s,)]|$)",
                line,
                re.IGNORECASE,
            ):
                return True
        return any(context in line for context in bound_contexts)

    relevant_denials = [line for line in denial_lines if denial_is_relevant(line)]
    unattributed_denials = [
        line for line in denial_lines if not denial_is_relevant(line)
    ]
    if relevant_denials:
        reasons.append("REQUEST_RELEVANT_SELINUX_DENIAL")
    if unattributed_denials:
        reasons.append("UNATTRIBUTED_SELINUX_DENIAL_IN_REQUEST_WINDOW")

    details = {
        "hilog_window_valid": log_window_valid,
        "hilog_delta_sha256": sha256_bytes(delta),
        "selinux_denial_count": len(denial_lines),
        "request_relevant_selinux_denial_count": len(relevant_denials),
        "request_relevant_selinux_denials": relevant_denials,
        "unattributed_selinux_denial_count": len(unattributed_denials),
        "unattributed_selinux_denials": unattributed_denials,
    }
    return reasons, details


def write_validation(
    run_dir: Path,
    *,
    phase: str,
    reasons: list[str],
    details: dict[str, Any] | None = None,
    output_name: str = "validation.json",
) -> dict[str, Any]:
    result = {
        "schema_version": SCHEMA_VERSION,
        "tool_version": TOOL_VERSION,
        "phase": phase,
        "evidence_status": "DEVELOPER_EVIDENCE_VALID" if not reasons else "EVIDENCE_REJECTED",
        "formal_verdict": "NOT_ISSUED",
        "reasons": sorted(set(reasons)),
        "details": details or {},
        "validated_at": utc_now(),
    }
    write_json(run_dir / output_name, result)
    return result


def write_manifest(run_dir: Path) -> None:
    run_dir = run_dir.resolve(strict=True)
    root_manifest = run_dir / "MANIFEST.sha256"
    replay_validation = run_dir / "validation.replay.json"
    lines: list[str] = []
    for path in sorted(run_dir.rglob("*")):
        if path.is_symlink():
            raise EvidenceError(f"refusing to seal symlink in bundle: {path}")
        if not path.is_file() or path in {root_manifest, replay_validation}:
            continue
        lines.append(f"{sha256_file(path)}  {path.relative_to(run_dir)}")
    write_bytes(run_dir / "MANIFEST.sha256", ("\n".join(lines) + "\n").encode())


def validate_begin_bundle_before_hdc(run_dir: Path) -> dict[str, Any]:
    manifest_reasons = verify_manifest(run_dir)
    if manifest_reasons:
        raise EvidenceError(
            "begin bundle failed pre-HDC manifest validation: "
            + "; ".join(manifest_reasons)
        )
    session_path = resolve_bundle_file(run_dir, "session.json", "session")
    validation_path = resolve_bundle_file(
        run_dir, "validation.json", "begin validation"
    )
    session = load_json(session_path)
    validation = load_json(validation_path)
    if (
        validation.get("phase") != "begin"
        or validation.get("evidence_status") != "DEVELOPER_EVIDENCE_VALID"
        or validation.get("formal_verdict") != "NOT_ISSUED"
        or validation.get("reasons") != []
    ):
        raise EvidenceError("begin validation is not admitted for finalize")

    action_id = require_string(session.get("action_id"), "session.action_id")
    if action_id not in ACTION_IDS:
        raise EvidenceError("session Action is not supported")
    serial = require_string(session.get("serial"), "session.serial")
    original_serial = require_string(
        session.get("original_serial"), "session.original_serial"
    )
    allowed_serials = require_array(
        session.get("allowed_serials"), "session.allowed_serials"
    )
    if allowed_serials != [original_serial] or serial != original_serial:
        raise EvidenceError("session serial is not locked to the one provenance device")
    ensure_safe_serial(original_serial)
    start = require_object(session.get("device_start"), "session.device_start")
    if start.get("serial") != original_serial:
        raise EvidenceError("begin snapshot serial differs from original serial")
    metadata, expected_hashes = validate_frozen_card1_provenance(run_dir, session)
    if session.get("expected_hashes") != expected_hashes:
        raise EvidenceError("session expected hashes differ from card1 provenance")
    if start.get("boot_id") != metadata["device_boot_id"]:
        raise EvidenceError("begin snapshot boot differs from card1 provenance boot")
    raw_reasons = verify_raw_hashes(run_dir, start)
    if raw_reasons:
        raise EvidenceError("begin raw inputs failed pre-HDC validation: " + "; ".join(raw_reasons))
    return session


def command_begin(args: argparse.Namespace) -> int:
    if args.action_id not in ACTION_IDS:
        raise EvidenceError(f"action-id must be one of {sorted(ACTION_IDS)}")
    ensure_safe_serial(args.serial)
    run_dir = Path(args.out_dir).resolve()
    if run_dir.exists() and any(run_dir.iterdir()):
        raise EvidenceError(f"out-dir must be absent or empty: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    provenance, expected_hashes = freeze_card1_provenance_bundle(
        run_dir,
        Path(args.provenance_manifest),
        Path(args.provenance_receipt),
        expected_action_id=args.action_id,
        expected_serial=args.serial,
    )
    contract_inputs = capture_contract_inputs(Path(args.root).resolve(), run_dir, args.action_id)
    label_paths = list(dict.fromkeys([*DEFAULT_LABEL_PATHS, *args.file_label_path, *expected_hashes]))
    process_names = ensure_safe_process_names(args.process or DEFAULT_PROCESSES)
    snapshot = capture_snapshot(
        hdc=args.hdc,
        serial=args.serial,
        label_paths=label_paths,
        process_names=process_names,
        raw_dir=run_dir / "raw",
        phase="begin",
    )
    session = {
        "schema_version": SCHEMA_VERSION,
        "tool_version": TOOL_VERSION,
        "session_id": f"{args.action_id}-{args.serial}-{snapshot['boot_id']}-{int(snapshot['uptime_seconds'])}",
        "action_id": args.action_id,
        "serial": args.serial,
        "original_serial": args.serial,
        "allowed_serials": [args.serial],
        "created_at": utc_now(),
        "expected_hashes": expected_hashes,
        "provenance": provenance,
        "contract_inputs": contract_inputs,
        "label_paths": label_paths,
        "process_names": process_names,
        "device_start": snapshot,
        "formal_verdict": "NOT_ISSUED",
    }
    write_json(run_dir / "session.json", session)
    reasons = validate_snapshot(snapshot, expected_hashes, process_names)
    if snapshot.get("serial") != provenance["device_serial"]:
        reasons.append("PROVENANCE_SERIAL_MISMATCH")
    if snapshot.get("boot_id") != provenance["device_boot_id"]:
        reasons.append("PROVENANCE_BOOT_MISMATCH")
    reasons.extend(verify_raw_hashes(run_dir, snapshot))
    result = write_validation(run_dir, phase="begin", reasons=reasons)
    write_manifest(run_dir)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if not reasons else 2


def command_finalize(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).resolve()
    session = validate_begin_bundle_before_hdc(run_dir)
    receipt_path = Path(args.request_receipt).resolve()
    process_names = ensure_safe_process_names(session["process_names"])
    end_snapshot = capture_snapshot(
        hdc=args.hdc,
        serial=session["original_serial"],
        label_paths=session["label_paths"],
        process_names=process_names,
        raw_dir=run_dir / "raw",
        phase="end",
    )
    session["device_end"] = end_snapshot
    session["end_process_names"] = process_names
    write_json(run_dir / "session.json", session)
    receipt = normalize_receipt(
        run_dir=run_dir,
        source_receipt_path=receipt_path,
        session=session,
    )
    reasons, details = validate_receipt_and_end(
        run_dir=run_dir,
        session=session,
        end_snapshot=end_snapshot,
        receipt=receipt,
    )
    begin_reasons = validate_snapshot(
        session["device_start"], session["expected_hashes"], session["process_names"]
    )
    reasons.extend(begin_reasons)
    try:
        _, frozen_hashes = validate_frozen_card1_provenance(run_dir, session)
        if frozen_hashes != session["expected_hashes"]:
            reasons.append("FROZEN_PROVENANCE_HASHES_CHANGED")
    except EvidenceError as exc:
        reasons.append(f"FROZEN_PROVENANCE_INVALID:{exc}")
    result = write_validation(run_dir, phase="finalize", reasons=reasons, details=details)
    write_manifest(run_dir)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if not reasons else 2


def command_validate(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).resolve()
    manifest_reasons = verify_manifest(run_dir)
    if manifest_reasons:
        result = write_validation(
            run_dir,
            phase="offline-replay",
            reasons=manifest_reasons,
            details={},
            output_name="validation.replay.json",
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 2
    session = load_json(resolve_bundle_file(run_dir, "session.json", "session"))
    receipt = load_json(
        resolve_bundle_file(
            run_dir, "normalized-receipt.json", "normalized receipt"
        )
    )
    if "device_end" not in session:
        reasons = ["END_SNAPSHOT_MISSING"]
        details: dict[str, Any] = {}
    else:
        reasons, details = validate_receipt_and_end(
            run_dir=run_dir,
            session=session,
            end_snapshot=session["device_end"],
            receipt=receipt,
        )
        reasons.extend(
            validate_snapshot(
                session["device_start"],
                session["expected_hashes"],
                session["process_names"],
            )
        )
    try:
        _, frozen_hashes = validate_frozen_card1_provenance(run_dir, session)
        if frozen_hashes != session.get("expected_hashes"):
            reasons.append("FROZEN_PROVENANCE_HASHES_CHANGED")
    except EvidenceError as exc:
        reasons.append(f"FROZEN_PROVENANCE_INVALID:{exc}")
    reasons.extend(verify_normalized_receipt_integrity(run_dir, receipt))
    result = write_validation(
        run_dir,
        phase="offline-replay",
        reasons=reasons,
        details=details,
        output_name="validation.replay.json",
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if not reasons else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    begin = subparsers.add_parser("begin", help="capture and gate the pre-request device state")
    begin.add_argument("--action-id", required=True, choices=sorted(ACTION_IDS))
    begin.add_argument("--serial", required=True)
    begin.add_argument("--out-dir", required=True)
    begin.add_argument("--hdc", default=DEFAULT_HDC)
    begin.add_argument(
        "--root",
        default=str(DEFAULT_ROOT),
        help="Bridge repository root used to freeze atom/verification/implementation inputs",
    )
    begin.add_argument(
        "--provenance-receipt",
        required=True,
        metavar="CARD1_GATE_REPORT_JSON",
        help=(
            "card1 generation-gate-report.v1 inside the closed provenance bundle; "
            "expected artifact hashes are imported only from this receipt chain"
        ),
    )
    begin.add_argument(
        "--provenance-manifest",
        required=True,
        metavar="MANIFEST_SHA256",
        help=(
            "closed SHA-256 manifest for the card1 gate/build/device receipt bundle"
        ),
    )
    begin.add_argument(
        "--file-label-path",
        action="append",
        default=[],
        metavar="REMOTE_PATH",
        help="additional path whose hash and SELinux label must be captured",
    )
    begin.add_argument(
        "--process",
        action="append",
        metavar="EXACT_NAME",
        help="exact process name to bind; defaults to appspawn-x and foundation",
    )
    begin.set_defaults(func=command_begin)

    finalize = subparsers.add_parser(
        "finalize", help="capture post-request state and validate a request receipt"
    )
    finalize.add_argument("--run-dir", required=True)
    finalize.add_argument("--request-receipt", required=True)
    finalize.add_argument("--hdc", default=DEFAULT_HDC)
    finalize.set_defaults(func=command_finalize)

    validate = subparsers.add_parser(
        "validate", help="replay validation from the self-contained captured bundle"
    )
    validate.add_argument("--run-dir", required=True)
    validate.set_defaults(func=command_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (EvidenceError, OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
