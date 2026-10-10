#!/usr/bin/env python3
"""Read-only, exact-artifact JNI/TU comparison; no build or board access."""
import argparse
import collections
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACES = Path(os.environ.get("WORKSPACES", HERE.parents[2]))
EXPECTED = {
    "u13": "18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae",
    "boat": "adc125f4dfb800c25d80e7d73216c8885fd64a31c6b91f064494166c63a59130",
}
CLASSES = {
    "android_database_SQLiteConnection.cpp": "android/database/sqlite/SQLiteConnection",
    "android_database_SQLiteGlobal.cpp": "android/database/sqlite/SQLiteGlobal",
    "android_database_SQLiteDebug.cpp": "android/database/sqlite/SQLiteDebug",
    "android_database_CursorWindow.cpp": "android/database/CursorWindow",
    "android_view_VelocityTracker.cpp": "android/view/VelocityTracker",
    "android_media_AudioSystemCapabilities.cpp": "android/media/AudioSystem",
    "common_event_registration.cpp": "adapter/activity/ActivityManagerAdapter",
    "android_graphics_compat_shim.cpp": "android/graphics/BLASTBufferQueue",
    "oh_egl_impl.cpp": "com/google/android/gles_jni/EGLImpl",
    "com_google_android_gles_jni_GLImpl.cpp": "com/google/android/gles_jni/GLImpl",
    "emboss-registration.cpp": "android/graphics/EmbossMaskFilter",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def portable(path):
    text = str(path.resolve())
    prefix = str(WORKSPACES.resolve()) + "/"
    return "$WORKSPACES/" + text[len(prefix):] if text.startswith(prefix) else text


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def dispatch(elf):
    rows = []
    for symbol in elf.symbols:
        if symbol["type"] != 1 or "kRegJNI" not in symbol["name"]:
            continue
        for address in range(symbol["value"], symbol["value"] + symbol["size"], 16):
            name = elf.cstr(elf.pointers.get(address, 0))
            target = elf.pointers.get(address + 8)
            if target is not None and name.startswith("register_"):
                rows.append({"table": symbol["name"], "address": hex(address),
                             "registrar": name, "target": hex(target),
                             "target_symbols": elf.sym_at.get(target, []),
                             "body_prefix": elf.at(target, 8).hex()})
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--u13", type=Path, default=WORKSPACES / "westlake-inputs/generations/t2c-runtime-reproduction-20261010/r1/runtime-out/liboh_android_runtime.so")
    parser.add_argument("--boat", type=Path, default=WORKSPACES / "westlake-harness-tools-inventory/benchmark/2026-10-10-5cd-demo-regression/boat-full128/signed-artifacts/liboh_android_runtime.so")
    parser.add_argument("--libandroid-base", type=Path, default=WORKSPACES / "westlake-inputs/generations/u13-stageA-91272eaf-20261003/armed-bundle/native/payload/android/lib64/libandroid.so")
    parser.add_argument("--assembled-libandroid", type=Path, default=WORKSPACES.parent / "00.Workspace-games-ad1ab0a7/.bridge-payload/zigzag-candidates/strict-boat-assembled-20260924T074522Z-25403/files/libandroid.so")
    args = parser.parse_args()
    paths = {"u13": args.u13, "boat": args.boat}
    for tag, path in paths.items():
        if digest(path) != EXPECTED[tag]:
            raise ValueError("wrong artifact: " + tag)
    master = WORKSPACES / "westlake-harness"
    scanner_path = master / "benchmark/2026-09-29-static-wall-prediction/scan_jni.py"
    comparison_path = WORKSPACES / "westlake-harness-tools-inventory/benchmark/2026-10-10-5cd-demo-regression/boat-full128/compare_runtime_jni.py"
    scanner = load_module("jni_scan", scanner_path)
    comparison = load_module("jni_compare", comparison_path)
    elfs, tables, scoped, global_delta, registrars = comparison.compare(scanner, paths)
    if digest(args.libandroid_base) != "9ccf64f8d1f6e1748665057273eaa4c2770098934d39afa160f2c6b4c18b06db":
        raise ValueError("wrong libandroid baseline")
    if digest(args.assembled_libandroid) != EXPECTED["boat"]:
        raise ValueError("wrong assembled libandroid")
    baseline = scanner.ELF(args.libandroid_base)
    changes = []
    for offset, (before, after) in enumerate(zip(baseline.data, elfs["boat"].data)):
        if before == after:
            continue
        section = next(section for section in baseline.sections if section["type"] != 8 and section["offset"] <= offset < section["offset"] + section["size"])
        address = section["addr"] + offset - section["offset"]
        owners = [symbol["name"] for symbol in baseline.symbols if symbol["type"] == 2 and symbol["value"] <= address < symbol["value"] + symbol["size"]]
        changes.append({"file_offset": hex(offset), "virtual_address": hex(address),
                        "before": before, "after": after, "executable": bool(section["flags"] & 4), "functions": owners})
    write_json("libandroid-origin.json", {
        "base": {"path": portable(args.libandroid_base), "sha256": digest(args.libandroid_base), "bytes": len(baseline.data)},
        "assembled": {"path": "$WORKSPACES/../" + str(args.assembled_libandroid.resolve().relative_to(WORKSPACES.parent)), "sha256": digest(args.assembled_libandroid)},
        "alias_identical": args.assembled_libandroid.read_bytes() == elfs["boat"].data,
        "same_size": len(baseline.data) == len(elfs["boat"].data),
        "changed_bytes": len(changes), "changed_executable_bytes": sum(row["executable"] for row in changes),
        "changes": changes,
        "exports_identical": baseline.exports == elfs["boat"].exports,
        "jni_tables_identical": baseline.tables() == elfs["boat"].tables(),
        "dispatch_identical": dispatch(baseline) == dispatch(elfs["boat"]),
    })
    write_json("exports.json", {
        "u13_count": len(elfs["u13"].exports), "boat_count": len(elfs["boat"].exports),
        "u13_only": sorted(set(elfs["u13"].exports) - set(elfs["boat"].exports)),
        "boat_only": sorted(set(elfs["boat"].exports) - set(elfs["u13"].exports)),
        "common": sorted(set(elfs["boat"].exports) & set(elfs["u13"].exports)),
    })
    tus = {tag: sorted({symbol["name"] for symbol in elf.symbols if symbol["type"] == 4})
           for tag, elf in elfs.items()}
    write_json("translation-units.json", {
        "basis": "ELF STT_FILE; not a complete build manifest", "files": tus,
        "u13_only": sorted(set(tus["u13"]) - set(tus["boat"])),
        "boat_only": sorted(set(tus["boat"]) - set(tus["u13"])),
    })
    write_json("registration-dispatch.json", {
        tag: {"JNI_OnLoad_exported": "JNI_OnLoad" in elf.exports,
              "startReg_symbols": [symbol for symbol in elf.symbols if "startReg" in symbol["name"]],
              "dispatch": dispatch(elf)} for tag, elf in elfs.items()
    })
    write_json("registrar-delta.json", registrars)
    for tag, rows in tables.items():
        write_json(tag + "-tables.json", rows)
    write_json("missing-methods.json", [dict(row, class_name=CLASSES.get(row["elf_source_file"], "unknown")) for row in scoped])
    with (HERE / "missing-methods.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["class", "method", "signature", "translation_unit", "table_symbol", "u13_table_address", "u13_function_address"])
        for row in scoped:
            writer.writerow([CLASSES.get(row["elf_source_file"], "unknown"), row["method"], row["signature"], row["elf_source_file"], row["elf_table_symbol"], row["table_address"], row["function_address"]])
    input_inventory = WORKSPACES / "westlake-inputs/generations/t2c-runtime-reproduction-20261010/input-inventory.json"
    inventory = json.loads(input_inventory.read_text())["files"]
    sources = [row for row in inventory if Path(row["path"]).name in set(tus["u13"]) and Path(row["path"]).suffix in (".cpp", ".c")]
    write_json("u13-source-witnesses.json", sources)
    result = {
        "artifacts": {tag: {"path": portable(path), "sha256": digest(path), "bytes": path.stat().st_size} for tag, path in paths.items()},
        "scanner": {"path": portable(scanner_path), "sha256": digest(scanner_path)},
        "comparison": {"path": portable(comparison_path), "sha256": digest(comparison_path)},
        "table_counts": {tag: len(rows) for tag, rows in tables.items()},
        "scoped_absent_rows": len(scoped),
        "scoped_by_translation_unit": dict(collections.Counter(row["elf_source_file"] for row in scoped)),
        "globally_absent_unique_pairs": len({(row["method"], row["signature"]) for row in global_delta}),
        "sqlite_noop_registrars": len([row for row in registrars if row.get("boat_is_return_zero_stub")]),
        "origin": {"libandroid_base_sha256": digest(args.libandroid_base),
                   "assembled_alias_sha256": digest(args.assembled_libandroid),
                   "alias_identical": args.assembled_libandroid.read_bytes() == elfs["boat"].data,
                   "patch_bytes": len(changes), "executable_patch_bytes": sum(row["executable"] for row in changes)},
        "wrong_path_verdict": "libandroid-derived blob replaces the full runtime JNI contract",
        "board_access": False, "rebuild": False,
    }
    write_json("results.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
