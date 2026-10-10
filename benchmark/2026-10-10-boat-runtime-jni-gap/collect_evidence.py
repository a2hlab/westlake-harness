#!/usr/bin/env python3
"""Collect bounded source/disassembly evidence from local files only."""
import json
import subprocess
from pathlib import Path

import audit

HERE = audit.HERE
WS = audit.WORKSPACES
ORCA = WS.parent
OBJDUMP = Path("/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin/llvm-objdump")


def portable(text):
    return text.replace(str(WS) + "/", "$WORKSPACES/").replace(str(ORCA) + "/", "$WORKSPACES/../")


def main():
    evidence = HERE / "evidence"
    evidence.mkdir(exist_ok=True)
    result = json.loads((HERE / "results.json").read_text())
    index = []
    for tag, record in result["artifacts"].items():
        binary = Path(record["path"].replace("$WORKSPACES", str(WS)))
        dispatch = json.loads((HERE / "registration-dispatch.json").read_text())[tag]
        symbol = next(row for row in dispatch["startReg_symbols"] if row["type"] == 2)
        regions = [("startReg", symbol["value"], symbol["value"] + symbol["size"])]
        registrars = json.loads((HERE / "registrar-delta.json").read_text())
        for row in registrars:
            if row.get("boat_is_return_zero_stub"):
                symbol = row[tag]
                regions.append((row["symbol"], symbol["value"], symbol["value"] + symbol["size"]))
        for number, (name, start, stop) in enumerate(regions):
            command = [str(OBJDUMP), "-d", "--start-address=" + hex(start), "--stop-address=" + hex(stop), str(binary)]
            process = subprocess.run(command, capture_output=True, text=True)
            output = evidence / (tag + "-" + str(number) + ".txt")
            output.write_text(portable(process.stdout + process.stderr))
            index.append({"kind": "disassembly", "artifact": record["sha256"], "function": name,
                          "command": [portable(value) for value in command], "rc": process.returncode,
                          "path": audit.portable(output), "sha256": audit.digest(output)})
            if process.returncode:
                raise RuntimeError("disassembly failed")
    origin = json.loads((HERE / "libandroid-origin.json").read_text())
    baseline = Path(origin["base"]["path"].replace("$WORKSPACES", str(WS)))
    boat = Path(result["artifacts"]["boat"]["path"].replace("$WORKSPACES", str(WS)))
    for tag, binary in [("libandroid-base", baseline), ("boat", boat), ("u13", Path(result["artifacts"]["u13"]["path"].replace("$WORKSPACES", str(WS))))]:
        process = subprocess.run([str(OBJDUMP.with_name("llvm-readelf")), "-d", str(binary)], capture_output=True, text=True)
        output = evidence / (tag + "-dynamic.txt")
        output.write_text(portable(process.stdout + process.stderr))
        if process.returncode:
            raise RuntimeError("readelf failed")
        index.append({"kind": "dynamic", "artifact": audit.digest(binary), "rc": process.returncode,
                      "path": audit.portable(output), "sha256": audit.digest(output)})
    addresses = sorted({int(row["virtual_address"], 16) & ~3 for row in origin["changes"] if row["executable"]})
    for tag, binary in [("libandroid-base", baseline), ("boat", boat)]:
        output = evidence / (tag + "-patch-sites.txt")
        text = []
        for address in addresses:
            process = subprocess.run([str(OBJDUMP), "-d", "--start-address=" + hex(address), "--stop-address=" + hex(address + 4), str(binary)], capture_output=True, text=True)
            if process.returncode:
                raise RuntimeError("patch-site disassembly failed")
            text.append(portable(process.stdout + process.stderr))
        output.write_text("\n".join(text))
        index.append({"kind": "patch-sites", "artifact": audit.digest(binary), "rc": 0,
                      "path": audit.portable(output), "sha256": audit.digest(output)})
    source_sets_extra = [
        (WS / "westlake-harness/benchmark/2026-10-09-demo-boatattack/evidence/boat-side-facts.txt", [(5, 10)]),
        (WS / "westlake-harness/benchmark/2026-10-10-u13-autostart/payload/scripts/westlake-u13-boat-overlay.sh", [(10, 14), (29, 35)]),
    ]
    source_root = WS / "westlake-harness-bms-deploy/bms/src/.work/b87-native/adapter/framework/android-runtime/src"
    source_sets = [
        (WS / "westlake-inputs/generations/t2c-runtime-reproduction-20261010/r1/recipe.sh", [(370, 379), (505, 510)]),
        (WS / "westlake-inputs/generations/t2c-runtime-reproduction-20261010/r1/build.log", [(1, 115)]),
        (WS / "westlake-harness-t3/benchmark/2026-10-01-n10b-child/smoke-markers/src/AndroidRuntime.cpp", [(237, 255), (347, 399), (411, 421)]),
        (source_root / "android_database_SQLiteConnection.cpp", [(903, 977)]),
        (source_root / "android_database_CursorWindow.cpp", [(509, 571)]),
        (source_root / "android_database_SQLiteDebug.cpp", [(60, 80)]),
        (source_root / "android_database_SQLiteGlobal.cpp", [(84, 99)]),
        (ORCA / "00.Workspace-games-ad1ab0a7/src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp", [(56, 70)]),
        (ORCA / "00.Workspace-games-ad1ab0a7/src/adapter/build/inner/compile_oh_android_runtime_arm64_stage2unity.sh", [(19, 45), (266, 362), (366, 441)]),
    ] + source_sets_extra
    inventory = json.loads((WS / "westlake-inputs/generations/t2c-runtime-reproduction-20261010/input-inventory.json").read_text())["files"]
    inventory_sha = {record["path"]: record["sha256"] for record in inventory}
    for number, (source, ranges) in enumerate(source_sets):
        lines = source.read_text().splitlines()
        path = portable(str(source))
        output = evidence / ("source-" + str(number) + ".txt")
        selected = [path + " sha256=" + audit.digest(source)]
        for first, last in ranges:
            selected.extend(str(line) + ": " + lines[line - 1] for line in range(first, min(last, len(lines)) + 1))
        output.write_text(portable("\n".join(selected)) + "\n")
        record = {"kind": "source", "source": path, "source_sha256": audit.digest(source),
                  "ranges": ranges, "path": audit.portable(output), "sha256": audit.digest(output),
                  "t2c_inventory_sha256": inventory_sha.get(path),
                  "exact_u13_input": inventory_sha.get(path) == audit.digest(source)}
        if source.name.startswith("android_database_") and not record["exact_u13_input"]:
            raise ValueError("SQLite source differs from exact U13 input")
        index.append(record)
    audit.write_json("evidence-index.json", {"objdump_sha256": audit.digest(OBJDUMP), "records": index})
    print(json.dumps({"disassembly_rc": [row["rc"] for row in index if row["kind"] == "disassembly"],
                      "exact_sqlite_sources": 4, "board_access": False}, indent=2))


if __name__ == "__main__":
    main()
