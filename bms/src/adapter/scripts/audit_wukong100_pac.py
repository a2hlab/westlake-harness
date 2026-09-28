#!/usr/bin/env python3
"""Parse a UIS7885 PAC and prove its System entry is the audited system image."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import BinaryIO


HEADER_SIZE = 2124
ENTRY_SIZE = 2580
FILE_COUNT_OFFSET = 1076
FILE_TABLE_OFFSET_OFFSET = 1080


def sha256_stream(stream: BinaryIO, size: int | None = None) -> str:
    digest = hashlib.sha256()
    remaining = size
    while remaining is None or remaining:
        request = 1024 * 1024 if remaining is None else min(1024 * 1024, remaining)
        chunk = stream.read(request)
        if not chunk:
            if remaining is not None and remaining:
                raise ValueError(f"truncated stream: remaining={remaining}")
            break
        digest.update(chunk)
        if remaining is not None:
            remaining -= len(chunk)
    return digest.hexdigest()


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return sha256_stream(stream)


def utf16_field(value: bytes) -> str:
    try:
        text = value.decode("utf-16le")
    except UnicodeDecodeError as exc:
        raise ValueError("invalid PAC UTF-16 field") from exc
    return text.split("\x00", 1)[0]


def parse_entry(raw: bytes, index: int) -> dict[str, int | str]:
    if len(raw) != ENTRY_SIZE:
        raise ValueError(f"short PAC entry header: index={index} size={len(raw)}")
    size = struct.unpack_from("<I", raw, 0)[0]
    if size != ENTRY_SIZE:
        raise ValueError(f"bad PAC entry struct size: index={index} size={size}")
    file_id = utf16_field(raw[4:516])
    file_name = utf16_field(raw[516:1028])
    hi_file_size, hi_offset, lo_file_size = struct.unpack_from("<III", raw, 1532)
    file_flag, check_flag, lo_offset = struct.unpack_from("<III", raw, 1544)
    file_size = (hi_file_size << 32) | lo_file_size
    data_offset = (hi_offset << 32) | lo_offset
    return {
        "index": index,
        "file_id": file_id,
        "file_name": file_name,
        "file_size": file_size,
        "data_offset": data_offset,
        "file_flag": file_flag,
        "check_flag": check_flag,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pac", type=Path, required=True)
    parser.add_argument("--system-image", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise ValueError(f"refusing to replace PAC audit: {args.output}")

    pac_size = args.pac.stat().st_size
    system_size = args.system_image.stat().st_size
    system_sha = sha256_file(args.system_image)
    with args.pac.open("rb") as stream:
        header = stream.read(HEADER_SIZE)
        if len(header) != HEADER_SIZE:
            raise ValueError("PAC header is truncated")
        file_count = struct.unpack_from("<I", header, FILE_COUNT_OFFSET)[0]
        table_offset = struct.unpack_from("<I", header, FILE_TABLE_OFFSET_OFFSET)[0]
        if table_offset != HEADER_SIZE or not 1 <= file_count <= 256:
            raise ValueError(
                f"invalid PAC table metadata: count={file_count} offset={table_offset}"
            )
        entries = [
            parse_entry(stream.read(ENTRY_SIZE), index) for index in range(file_count)
        ]
        candidates = [
            entry
            for entry in entries
            if str(entry["file_name"]).lower() == "system.img"
            or str(entry["file_id"]).lower() == "system"
        ]
        if len(candidates) != 1:
            raise ValueError(f"PAC must contain one System entry, found {len(candidates)}")
        system_entry = candidates[0]
        offset = int(system_entry["data_offset"])
        size = int(system_entry["file_size"])
        if offset < HEADER_SIZE + file_count * ENTRY_SIZE or offset + size > pac_size:
            raise ValueError(
                f"System entry bounds invalid: offset={offset} size={size} pac={pac_size}"
            )
        stream.seek(offset)
        embedded_sha = sha256_stream(stream, size)

    exact = size == system_size and embedded_sha == system_sha
    document = {
        "schema": "westlake.wukong100.pac_system_readback.v1",
        "scope": "HOST_ARTIFACT_VERIFIED / NOT_FLASH_OR_DEVICE_VERIFIED",
        "pac_path": str(args.pac.absolute()),
        "pac_sha256": sha256_file(args.pac),
        "pac_size": pac_size,
        "file_count": file_count,
        "file_table_offset": table_offset,
        "system_image_path": str(args.system_image.absolute()),
        "system_image_sha256": system_sha,
        "system_image_size": system_size,
        "system_entry": system_entry,
        "embedded_system_sha256": embedded_sha,
        "embedded_system_exact": exact,
        "entries": entries,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not exact:
        print(
            f"PAC_AUDIT_FAIL pac={args.pac} expected={system_sha}/{system_size} "
            f"actual={embedded_sha}/{size}"
        )
        return 1
    print(
        f"PAC_AUDIT_PASS pac_sha256={document['pac_sha256']} "
        f"system_sha256={system_sha} entry_index={system_entry['index']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
