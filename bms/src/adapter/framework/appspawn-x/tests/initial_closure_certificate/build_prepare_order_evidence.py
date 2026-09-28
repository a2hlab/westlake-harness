#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
import struct
import sys
from typing import Any


HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import initial_closure_gate as gate  # noqa: E402


SCHEMA = gate.SCHEMA_PHASE
METHOD = "verified_binary_callgraph_v1"
CHILD_MAIN = "_ZN9appspawnx9ChildMain3runERKNS_8SpawnMsgEPNS_16AppSpawnXRuntimeE"
APPLY_SELINUX = "_ZN9appspawnx9ChildMain12applySELinuxERKNS_8SpawnMsgE"


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def symbol_table(elf: gate.Elf64) -> dict[str, tuple[int, int]]:
    result: dict[str, tuple[int, int]] = {}
    for section in elf.section_headers:
        if section.sh_type not in (gate.SHT_SYMTAB, gate.SHT_DYNSYM):
            continue
        if section.sh_link >= len(elf.section_headers):
            raise gate.GateFailure("SYMTAB_LINK", "symbol table has invalid string table link", path=str(elf.path))
        strings = elf.section_headers[section.sh_link]
        elf._range(strings.sh_offset, strings.sh_size, "symbol_strings")
        entry_size = section.sh_entsize or 24
        if entry_size < 24 or section.sh_size % entry_size:
            raise gate.GateFailure("SYMTAB_SIZE", "symbol table has invalid entry size", path=str(elf.path))
        elf._range(section.sh_offset, section.sh_size, "symbols")
        for offset in range(section.sh_offset, section.sh_offset + section.sh_size, entry_size):
            name_index, info, _other, shndx, value, size = struct.unpack_from("<IBBHQQ", elf.data, offset)
            if shndx == gate.SHN_UNDEF or name_index >= strings.sh_size:
                continue
            if (info & 0x0F) != 2 or not value:
                continue
            start = strings.sh_offset + name_index
            end = elf.data.find(b"\0", start, strings.sh_offset + strings.sh_size)
            if end < 0:
                raise gate.GateFailure("SYMBOL_STRING_NUL", "symbol name is not terminated", path=str(elf.path))
            if end == start:
                continue
            name = elf.data[start:end].decode("utf-8", errors="replace")
            current = result.get(name)
            candidate = (value, size)
            if current is None or candidate[1] > current[1]:
                result[name] = candidate
    return result


def sign_extend(value: int, bits: int) -> int:
    sign = 1 << (bits - 1)
    return (value ^ sign) - sign


def decode_bl_target(word: int, address: int) -> int | None:
    if (word & 0xFC000000) != 0x94000000:
        return None
    imm26 = sign_extend(word & 0x03FFFFFF, 26)
    return address + (imm26 << 2)


def function_bytes(elf: gate.Elf64, address: int, size: int) -> bytes:
    if size <= 0:
        raise gate.GateFailure("FUNCTION_SIZE", "function size must be positive", path=str(elf.path), address=address, size=size)
    offset = elf._vaddr_to_offset(address, size)
    elf._range(offset, size, "function_bytes")
    return elf.data[offset:offset + size]


def exact_calls(sidecar: gate.Elf64, child_address: int, child_size: int) -> list[dict[str, int]]:
    code = function_bytes(sidecar, child_address, child_size)
    result: list[dict[str, int]] = []
    for step in range(0, len(code), 4):
        word = struct.unpack_from("<I", code, step)[0]
        address = child_address + step
        target = decode_bl_target(word, address)
        if target is None:
            continue
        result.append({"address": address, "target": target, "encoding": word})
    return result


def slot5_sites(tp_report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in tp_report.get("object_scans", []):
        for access in item.get("accesses", []):
            if not access.get("overlaps_slot5"):
                continue
            rows.append({
                "elf_sha256": item["sha256"],
                "mrs_address": access["mrs_address"],
                "access_address": access["address"],
                "offset": access["offset"],
                "width": access["width"],
            })
    rows.sort(key=lambda row: (row["elf_sha256"], row["mrs_address"], row["access_address"], row["offset"], row["width"]))
    return rows


def build_evidence(config_path: pathlib.Path, tp_report_path: pathlib.Path) -> dict[str, Any]:
    config = load_json(config_path)
    if config.get("schema") != gate.SCHEMA_CONFIG:
        raise gate.GateFailure("CONFIG_SCHEMA", "unexpected gate config schema", path=str(config_path))
    tp_report = load_json(tp_report_path)
    if tp_report.get("schema") != "westlake-initial-closure-tp-scan-v1":
        raise gate.GateFailure("TP_REPORT_SCHEMA", "unexpected TP report schema", path=str(tp_report_path))

    snapshot_root = (gate.PROJECT_ROOT / config["snapshot_root"]).resolve()
    main = gate.Elf64(snapshot_root / config["main"])
    sidecar = gate.Elf64(snapshot_root / config["main_sidecar"])
    symbols = symbol_table(sidecar)

    prepare_symbol = next(
        (name for name in config.get("expected_prepare_symbols", []) if isinstance(name, str) and name in symbols),
        None,
    )
    if prepare_symbol is None:
        raise gate.GateFailure(
            "TLS_PREPARE_SYMBOL_ABSENT",
            "no expected prepare symbol is defined in the exact main sidecar",
            expected_symbols=config.get("expected_prepare_symbols", []),
        )
    if CHILD_MAIN not in symbols or APPLY_SELINUX not in symbols:
        raise gate.GateFailure(
            "PHASE_EVIDENCE_REQUIRED_SYMBOL",
            "required ChildMain phase symbols are absent from the exact main sidecar",
        )

    child_address, child_size = symbols[CHILD_MAIN]
    apply_selinux_address, _ = symbols[APPLY_SELINUX]
    prepare_address, _ = symbols[prepare_symbol]
    calls = exact_calls(sidecar, child_address, child_size)
    selinux_calls = [row for row in calls if row["target"] == apply_selinux_address]
    prepare_calls = [row for row in calls if row["target"] == prepare_address]
    if not selinux_calls or not prepare_calls:
        raise gate.GateFailure(
            "PHASE_EVIDENCE_CALLS",
            "exact ChildMain binary does not call both applySELinux and native prepare",
            child_main=hex(child_address),
            apply_selinux=hex(apply_selinux_address),
            prepare=hex(prepare_address),
        )
    first_selinux = min(selinux_calls, key=lambda row: row["address"])
    first_prepare = min(prepare_calls, key=lambda row: row["address"])
    if first_selinux["address"] >= first_prepare["address"]:
        raise gate.GateFailure(
            "PHASE_EVIDENCE_ORDER",
            "native prepare is not ordered after stock applySELinux in exact ChildMain",
            apply_selinux_call=hex(first_selinux["address"]),
            prepare_call=hex(first_prepare["address"]),
        )

    sites = slot5_sites(tp_report)
    if sites:
        raise gate.GateFailure(
            "PHASE_EVIDENCE_NONEMPTY_SLOT5_SITE_SET",
            "this generator only certifies the exact empty slot5 site set; a non-empty set needs per-site placement proof",
            slot5_site_count=len(sites),
        )

    return {
        "schema": SCHEMA,
        "method": METHOD,
        "complete": True,
        "main_sha256": main.sha256,
        "prepare_symbol": prepare_symbol,
        "slot5_sites": [],
        "pre_prepare_slot5_access_count": 0,
        "post_prepare_slot5_access_count": 0,
        "subject": {
            "main": main.identity_dict(snapshot_root),
            "sidecar": sidecar.identity_dict(snapshot_root),
        },
        "exact_call_order": {
            "child_main_symbol": CHILD_MAIN,
            "child_main_address": child_address,
            "child_main_size": child_size,
            "apply_selinux_symbol": APPLY_SELINUX,
            "apply_selinux_address": apply_selinux_address,
            "prepare_address": prepare_address,
            "first_apply_selinux_call": first_selinux["address"],
            "first_prepare_call": first_prepare["address"],
        },
        "proof_limits": {
            "slot5_site_set": "exact-empty-set-only",
            "why_admissible": "exact main sha, exact sidecar, exact call order, and exact scanner site set are all bound",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=pathlib.Path)
    parser.add_argument("--tp-report", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    evidence = build_evidence(args.config.resolve(), args.tp_report.resolve())
    gate.write_atomic(args.output.resolve(), gate.stable_json_bytes(evidence))
    print(
        "PASS prepare_order_proven=true pre_prepare_slot5=0 "
        f"main_sha256={evidence['main_sha256']} slot5_sites={len(evidence['slot5_sites'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
