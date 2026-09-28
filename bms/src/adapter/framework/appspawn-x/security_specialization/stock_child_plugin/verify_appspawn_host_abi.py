#!/usr/bin/env python3
"""Fail closed unless the rebuilt host matches the target appspawn ABI cohort."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


TARGET_HEADER_SHA256 = (
    "b3619c81b3e91af8c079eb17a922ef8a573938259745e54726122ffa174143b6"
)
CURRENT_HEADER_SHA256 = (
    "5455b2c27d2a0c63733b10fddf13e3cb7b724da766f498a5c737418f3127c7de"
)
TARGET_COMMON_BUILD_ID = "7240f7b76df8567014a7371661866cbf"
TARGET_SIZE = 0x100
TARGET_MEMBERS = {
    "content": 0x00,
    "server": 0x68,
    "sigHandler": 0x70,
    "servicePid": 0x78,
    "appQueue": 0x80,
    "diedAppCount": 0x90,
    "flags": 0x94,
    "diedQueue": 0x98,
    "appSpawnQueue": 0xA8,
    "perLoadStart": 0xB8,
    "perLoadEnd": 0xC8,
    "extData": 0xD8,
    "spawnTime": 0xE8,
    "dataGroupCtxQueue": 0xF0,
}
DIRECT_CONSUMERS = (
    "appspawn_modulemgr",
    "appspawn_appmgr",
    "appspawn_kickdog",
    "appspawn_msgmgr",
    "appspawn_service",
)
MANAGER_PATTERN = re.compile(
    r"typedef struct TagAppSpawnMgr \{.*?\n\} AppSpawnMgr;", re.DOTALL
)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def run(*command: str) -> str:
    return subprocess.run(
        command, check=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True,
    ).stdout


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def parse_layouts(text: str) -> list[dict[str, object]]:
    starts = [match.start() for match in re.finditer(
        r"(?m)^0x[0-9a-f]+: DW_TAG_structure_type\n"
        r"\s+DW_AT_name\s+\(\"TagAppSpawnMgr\"\)", text
    )]
    layouts: list[dict[str, object]] = []
    for start in starts:
        end_match = re.search(r"(?m)^0x[0-9a-f]+:\s+NULL\s*$", text[start:])
        require(end_match is not None, "unterminated TagAppSpawnMgr DWARF")
        block = text[start:start + end_match.end()]
        size_match = re.search(r"DW_AT_byte_size\s+\((0x[0-9a-f]+)\)", block)
        decl_match = re.search(r"DW_AT_decl_file\s+\(\"([^\"]+)\"\)", block)
        require(size_match is not None and decl_match is not None,
                "incomplete TagAppSpawnMgr DWARF definition")
        members: dict[str, int] = {}
        for member in re.finditer(
            r"DW_TAG_member\n"
            r"\s+DW_AT_name\s+\(\"([^\"]+)\"\)"
            r"(?:(?!DW_TAG_member|\n0x).)*?"
            r"DW_AT_data_member_location\s+\((0x[0-9a-f]+)\)",
            block, re.DOTALL,
        ):
            members[member.group(1)] = int(member.group(2), 16)
        layouts.append({
            "size": int(size_match.group(1), 16),
            "decl_file": decl_match.group(1),
            "members": members,
        })
    return layouts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True, type=Path)
    parser.add_argument("--current-header", required=True, type=Path)
    parser.add_argument("--target-header", required=True, type=Path)
    parser.add_argument("--overlay-header", required=True, type=Path)
    parser.add_argument("--dependency-dir", required=True, type=Path)
    parser.add_argument("--stock-common", required=True, type=Path)
    parser.add_argument("--dwarfdump", required=True, type=Path)
    parser.add_argument("--readelf", required=True, type=Path)
    parser.add_argument("--objdump", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    for path in (args.host, args.current_header, args.target_header,
                 args.overlay_header, args.stock_common,
                 args.dwarfdump, args.readelf, args.objdump):
        require(path.is_file(), f"missing ABI input: {path}")

    current_sha = digest(args.current_header)
    require(current_sha == CURRENT_HEADER_SHA256,
            f"current security-v7 manager header identity drift: {current_sha}")
    header_sha = digest(args.target_header)
    require(header_sha == TARGET_HEADER_SHA256,
            f"target appspawn_manager.h identity drift: {header_sha}")

    current_text = args.current_header.read_text()
    target_text = args.target_header.read_text()
    overlay_text = args.overlay_header.read_text()
    current_managers = MANAGER_PATTERN.findall(current_text)
    target_managers = MANAGER_PATTERN.findall(target_text)
    require(len(current_managers) == 1 and len(target_managers) == 1,
            "manager declaration extraction drift")
    expected_overlay = current_text.replace(
        current_managers[0], target_managers[0]
    )
    require(overlay_text == expected_overlay,
            "ABI overlay changed content outside TagAppSpawnMgr")
    require("uint64_t checkPointId;" in overlay_text,
            "current AppSpawningCtx checkpoint declaration lost")

    dependency_sha256 = {}
    overlay_resolved = str(args.overlay_header.resolve())
    for consumer in DIRECT_CONSUMERS:
        dependency = args.dependency_dir / f"{consumer}.d"
        require(dependency.is_file(), f"missing direct-consumer dependency: {dependency}")
        dependency_text = dependency.read_text().replace("\\\n", " ")
        require(str(args.overlay_header) in dependency_text or
                overlay_resolved in dependency_text,
                f"{consumer} did not bind manager ABI overlay")
        normalized_dependency = dependency_text.replace(
            str(args.dependency_dir), "<DEPDIR>"
        )
        dependency_sha256[consumer] = hashlib.sha256(
            normalized_dependency.encode()
        ).hexdigest()

    dwarf = run(str(args.dwarfdump), "--name=TagAppSpawnMgr",
                "--show-children", str(args.host))
    layouts = parse_layouts(dwarf)
    require(layouts, "rebuilt host has no TagAppSpawnMgr DWARF")
    cohort_layouts = [
        layout for layout in layouts
        if "out/abi-cohort/OpenHarmony-6.1.0.31/standard/"
        "appspawn_manager.h" in str(layout["decl_file"])
    ]
    opaque_layouts = [layout for layout in layouts if layout not in cohort_layouts]
    require(len(cohort_layouts) == len(DIRECT_CONSUMERS),
            "direct-consumer cohort definition count mismatch: "
            f"{len(cohort_layouts)}")
    for index, layout in enumerate(cohort_layouts):
        require(layout["size"] == TARGET_SIZE,
                f"host layout {index} size mismatch: {layout['size']:#x}")
        require(layout["members"] == TARGET_MEMBERS,
                f"host layout {index} member mismatch: {layout['members']}")
        require(layout["members"].get("extData") == 0xD8 and
                layout["members"].get("extData") != 0xE0,
                f"host layout {index} retained rejected extData offset")

    common_notes = run(str(args.readelf), "-nW", str(args.stock_common))
    build_ids = re.findall(r"Build ID:\s*([0-9a-f]+)", common_notes)
    require(build_ids == [TARGET_COMMON_BUILD_ID],
            f"stock common DSO Build-ID drift: {build_ids}")
    common_disassembly = run(
        str(args.objdump), "-d", "--start-address=0xf15c",
        "--stop-address=0xf1a4", str(args.stock_common),
    )
    require(re.search(r"add\s+x0, x0, #(216|0xd8)", common_disassembly),
            "stock common DSO no longer materializes extData at +0xd8")
    require("OH_ListFind" in common_disassembly,
            "stock common DSO pre-fork lookup no longer calls OH_ListFind")

    manager_disassembly = run(
        str(args.objdump), "-d",
        "--disassemble-symbols=CreateAppSpawnMgr,DeleteAppSpawnMgr",
        str(args.host),
    )
    require(re.search(r"mov\s+w1, #(256|264|0x100|0x108)",
                      manager_disassembly),
            "host manager allocation size is not 0x100/0x108")
    require(re.search(r"add\s+x0, x(?:0|19), #(216|0xd8)",
                      manager_disassembly),
            "host Create/Delete does not materialize extData at +0xd8")
    require(re.search(r"add\s+x0, x(?:0|19), #(240|0xf0)",
                      manager_disassembly),
            "host Create/Delete does not materialize dataGroupCtxQueue at +0xf0")
    require(not re.search(r"add\s+x0, x(?:0|19), #(224|0xe0)",
                          manager_disassembly),
            "host retains rejected extData +0xe0 manager operation")

    report = {
        "schema": "westlake.appspawn-host-abi-cohort.v1",
        "status": "PASS",
        "candidate": "P0-A06-ABI-D8-001",
        "variable": "APPSPAWN_X_HOST_SOURCE_ABI_COHORT=OpenHarmony-6.1.0.31",
        "target_header_sha256": header_sha,
        "current_header_sha256": current_sha,
        "overlay_header_sha256": digest(args.overlay_header),
        "overlay_scope": "TagAppSpawnMgr_declaration_only",
        "direct_consumer_dependency_sha256": dependency_sha256,
        "host_sha256": digest(args.host),
        "host_layout_definition_count": len(layouts),
        "direct_consumer_layout_definition_count": len(cohort_layouts),
        "opaque_non_consumer_layouts": opaque_layouts,
        "host_struct_size": TARGET_SIZE,
        "host_member_offsets": TARGET_MEMBERS,
        "rejected_extdata_offset": 0xE0,
        "stock_common_sha256": digest(args.stock_common),
        "stock_common_build_id": TARGET_COMMON_BUILD_ID,
        "stock_common_extdata_offset": 0xD8,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
