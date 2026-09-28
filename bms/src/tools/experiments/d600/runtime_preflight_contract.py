#!/usr/bin/env python3
"""Validate a device-bound D600 appspawn-x runtime preflight receipt."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
POSITIVE_PID_RE = re.compile(r"^[1-9][0-9]*$")

REQUIRED_ARTIFACTS = {
    "libart.so": "/system/android/lib64/libart.so",
    "boot.art": "/system/android/framework/arm64/boot.art",
    "appspawn-x": "/system/bin/appspawn-x",
    "libappms.z.so": "/system/lib64/libappms.z.so",
    "libbms.z.so": "/system/lib64/libbms.z.so",
    "libapk_installer.so": "/system/lib64/libapk_installer.so",
}


def _mapping(value: object, field: str, errors: list[str]) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping):
        errors.append(f"{field}: required object")
        return None
    return value


def _nonempty_string(value: object, field: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field}: required non-empty string")
        return None
    return value.strip()


def _sha256(value: object, field: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        errors.append(f"{field}: required 64-character hexadecimal SHA-256")
        return None
    normalized = value.lower()
    if normalized == "0" * 64:
        errors.append(f"{field}: all-zero SHA-256 placeholder is invalid")
        return None
    return normalized


def _positive_pid(value: object, field: str, errors: list[str]) -> int | None:
    if isinstance(value, bool):
        errors.append(f"{field}: required positive decimal PID")
        return None
    if isinstance(value, int):
        if value > 0:
            return value
        errors.append(f"{field}: required positive decimal PID")
        return None
    if isinstance(value, str) and POSITIVE_PID_RE.fullmatch(value.strip()):
        return int(value.strip())
    errors.append(f"{field}: required positive decimal PID")
    return None


def _positive_number(value: object, field: str, errors: list[str]) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        errors.append(f"{field}: required number greater than zero")


def validate_receipt(receipt: object) -> list[str]:
    """Return all contract violations; an empty list means PASS."""

    errors: list[str] = []
    root = _mapping(receipt, "receipt", errors)
    if root is None:
        return errors

    schema_version = root.get("schema_version")
    if isinstance(schema_version, bool) or schema_version != SCHEMA_VERSION:
        errors.append(f"schema_version: required integer {SCHEMA_VERSION}")
    _nonempty_string(root.get("device_serial"), "device_serial", errors)
    _nonempty_string(root.get("boot_id"), "boot_id", errors)

    artifacts = _mapping(root.get("artifacts"), "artifacts", errors)
    if artifacts is not None:
        for name, expected_path in REQUIRED_ARTIFACTS.items():
            field = f"artifacts.{name}"
            artifact = _mapping(artifacts.get(name), field, errors)
            if artifact is None:
                continue
            if artifact.get("path") != expected_path:
                errors.append(f"{field}.path: required {expected_path}")
            expected = _sha256(
                artifact.get("expected_sha256"), f"{field}.expected_sha256", errors
            )
            device = _sha256(
                artifact.get("device_sha256"), f"{field}.device_sha256", errors
            )
            if expected is not None and device is not None and expected != device:
                errors.append(f"{field}: expected_sha256 does not match device_sha256")

    appspawn = _mapping(root.get("appspawn_x"), "appspawn_x", errors)
    parent_pid = None
    if appspawn is not None:
        parent_pid = _positive_pid(appspawn.get("pid"), "appspawn_x.pid", errors)
        if appspawn.get("socket_exists") is not True:
            errors.append("appspawn_x.socket_exists: required true")

        sample = _mapping(appspawn.get("sample_window"), "appspawn_x.sample_window", errors)
        if sample is not None:
            _positive_number(
                sample.get("duration_seconds"),
                "appspawn_x.sample_window.duration_seconds",
                errors,
            )
            exit_count = sample.get("exit_127_count")
            if isinstance(exit_count, bool) or not isinstance(exit_count, int):
                errors.append(
                    "appspawn_x.sample_window.exit_127_count: required non-negative integer"
                )
            elif exit_count < 0:
                errors.append(
                    "appspawn_x.sample_window.exit_127_count: required non-negative integer"
                )
            elif exit_count != 0:
                errors.append(
                    "appspawn_x.sample_window.exit_127_count: required 0 for a stable preflight"
                )

    spawn = _mapping(root.get("spawn_response"), "spawn_response", errors)
    if spawn is not None:
        result = spawn.get("result")
        if not isinstance(result, str) or result.lower() != "0x0":
            errors.append("spawn_response.result: required 0x0")
        child_pid = _positive_pid(
            spawn.get("child_pid"), "spawn_response.child_pid", errors
        )
        if parent_pid is not None and child_pid == parent_pid:
            errors.append("spawn_response.child_pid: must differ from appspawn_x.pid")

    return errors


def load_receipt(path: Path) -> object:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def _validate_path(path: Path) -> tuple[str, list[str]]:
    try:
        receipt = load_receipt(path)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return "unknown", [f"receipt_file: {error}"]

    device = "unknown"
    if isinstance(receipt, Mapping):
        value = receipt.get("device_serial")
        if isinstance(value, str) and value.strip():
            device = value.strip()
    return device, validate_receipt(receipt)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipts", nargs="+", type=Path, help="JSON receipt files")
    args = parser.parse_args(argv)

    failed = False
    for path in args.receipts:
        device, errors = _validate_path(path)
        if errors:
            failed = True
            print(f"FAIL runtime preflight device={device} receipt={path}")
            for error in errors:
                print(f"- {error}")
            continue
        print(
            "PASS runtime preflight "
            f"device={device} receipt={path} artifacts={len(REQUIRED_ARTIFACTS)}"
        )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
