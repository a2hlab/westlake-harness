#!/usr/bin/env python3
"""Verify Bridge-local Unity imports without consulting their legacy source."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import struct
import sys
import zipfile

import yaml


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def _length8(data: bytes, offset: int) -> tuple[int, int]:
    first = data[offset]
    if first & 0x80:
        return ((first & 0x7F) << 8) | data[offset + 1], offset + 2
    return first, offset + 1


def _length16(data: bytes, offset: int) -> tuple[int, int]:
    first = _u16(data, offset)
    if first & 0x8000:
        return ((first & 0x7FFF) << 16) | _u16(data, offset + 2), offset + 4
    return first, offset + 2


def manifest_package(apk: Path) -> str:
    """Read the package attribute from Android's binary manifest XML."""
    with zipfile.ZipFile(apk) as archive:
        data = archive.read("AndroidManifest.xml")
    if _u16(data, 0) != 0x0003:
        raise ValueError("AndroidManifest.xml is not binary XML")

    strings: list[str] = []
    offset = _u16(data, 2)
    while offset + 8 <= len(data):
        chunk_type = _u16(data, offset)
        header_size = _u16(data, offset + 2)
        chunk_size = _u32(data, offset + 4)
        if chunk_size < header_size or offset + chunk_size > len(data):
            raise ValueError("invalid binary XML chunk")
        if chunk_type == 0x0001:
            count = _u32(data, offset + 8)
            flags = _u32(data, offset + 16)
            strings_start = _u32(data, offset + 20)
            offsets_start = offset + header_size
            pool_start = offset + strings_start
            utf8 = bool(flags & 0x00000100)
            strings = []
            for index in range(count):
                cursor = pool_start + _u32(data, offsets_start + index * 4)
                if utf8:
                    _, cursor = _length8(data, cursor)
                    byte_length, cursor = _length8(data, cursor)
                    value = data[cursor : cursor + byte_length].decode("utf-8")
                else:
                    unit_length, cursor = _length16(data, cursor)
                    value = data[cursor : cursor + unit_length * 2].decode(
                        "utf-16le"
                    )
                strings.append(value)
        elif chunk_type == 0x0102 and strings:
            name_index = _u32(data, offset + 20)
            if name_index < len(strings) and strings[name_index] == "manifest":
                attribute_start = _u16(data, offset + 24)
                attribute_size = _u16(data, offset + 26)
                attribute_count = _u16(data, offset + 28)
                cursor = offset + 16 + attribute_start
                for _ in range(attribute_count):
                    attr_name = _u32(data, cursor + 4)
                    raw_value = _u32(data, cursor + 8)
                    data_type = data[cursor + 15]
                    typed_value = _u32(data, cursor + 16)
                    if attr_name < len(strings) and strings[attr_name] == "package":
                        value_index = (
                            raw_value
                            if raw_value != 0xFFFFFFFF
                            else typed_value if data_type == 0x03 else 0xFFFFFFFF
                        )
                        if value_index < len(strings):
                            return strings[value_index]
                    cursor += attribute_size
        offset += chunk_size
    raise ValueError("manifest package attribute not found")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="/opt/Bridge")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    spec_path = root / "spec" / "unity-goal-ladder.yaml"
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    import_root = Path(spec["import_policy"]["canonical_root"]).resolve()

    failures: list[str] = []
    checked = 0
    for goal in spec["goals"]:
        if goal.get("import_state") != "COMPLETE_LOCAL_COPY":
            continue
        project_dir = Path(goal["project_dir"]).resolve()
        if import_root not in project_dir.parents:
            failures.append(f"{goal['id']}: project_dir escapes import root")
        if not project_dir.is_dir():
            failures.append(f"{goal['id']}: missing project_dir {project_dir}")
        for artifact in goal.get("artifacts", []):
            checked += 1
            apk = (import_root / artifact["path"]).resolve()
            if import_root not in apk.parents:
                failures.append(f"{artifact['id']}: path escapes import root")
                continue
            if not apk.is_file():
                failures.append(f"{artifact['id']}: missing {apk}")
                continue
            size = apk.stat().st_size
            if size != artifact["size_bytes"]:
                failures.append(
                    f"{artifact['id']}: size {size} != {artifact['size_bytes']}"
                )
            actual_sha = sha256(apk)
            if actual_sha != artifact["sha256"]:
                failures.append(
                    f"{artifact['id']}: sha256 {actual_sha} != {artifact['sha256']}"
                )
            try:
                with zipfile.ZipFile(apk) as archive:
                    entries = set(archive.namelist())
            except zipfile.BadZipFile:
                failures.append(f"{artifact['id']}: invalid ZIP/APK")
                continue
            try:
                actual_package = manifest_package(apk)
            except (KeyError, UnicodeDecodeError, ValueError) as exc:
                failures.append(f"{artifact['id']}: cannot parse package: {exc}")
                continue
            expected_package = artifact.get("package_name")
            if expected_package == "ARTIFACT_PARSE_PENDING":
                print(f"INFO: {artifact['id']} package_name={actual_package}")
            elif actual_package != expected_package:
                failures.append(
                    f"{artifact['id']}: package {actual_package} != "
                    f"{expected_package}"
                )
            for entry in artifact.get("required_zip_entries", []):
                if entry not in entries:
                    failures.append(f"{artifact['id']}: missing ZIP entry {entry}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print(f"PASS: verified {checked} Bridge-local Unity APK artifacts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
