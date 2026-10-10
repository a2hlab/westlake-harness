#!/usr/bin/env python3
"""Exact-artifact, read-only geometry analysis; never builds or deploys."""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess

HERE = Path(__file__).resolve().parent
WORKSPACES = Path(os.environ.get("WORKSPACES", HERE.parents[2]))
LLVM = Path(os.environ.get("LLVM_BIN", "/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin"))
ARTIFACTS = {
    "9cc": ("westlake-inputs/generations/u13-stageA-91272eaf-20261003/armed-bundle/native/payload/android/lib64/libandroid.so", "9ccf64f8d1f6e1748665057273eaa4c2770098934d39afa160f2c6b4c18b06db"),
    "adc": ("westlake-harness-tools-inventory/benchmark/2026-10-10-5cd-demo-regression/boat-full128/signed-artifacts/liboh_android_runtime.so", "adc125f4dfb800c25d80e7d73216c8885fd64a31c6b91f064494166c63a59130"),
    "187": ("westlake-inputs/generations/t2c-runtime-reproduction-20261010/r1/runtime-out/liboh_android_runtime.so", "18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae"),
}
SOURCE = "westlake-harness-t3/benchmark/2026-10-02-m1-session-slots/runtime/src/android_graphics_compat_shim.cpp"
SOURCE_SHA = "e28f4bc3a7c863defd74bb173146ea89308a6bf952ea1d11c80b00dd87ecd658"
SOURCES = {
    "gfx": SOURCE,
    "startup": "westlake-harness-t3/benchmark/2026-10-01-n10b-child/smoke-markers/src/AndroidRuntime.cpp",
    "publication": "westlake-harness-bms-deploy/benchmark/2026-09-30-n3b-webview/src/webview_publication.cpp",
    "input_receiver": "westlake-harness-bms-deploy/bms/src/.work/b87-native/adapter/framework/android-runtime/src/android_view_InputEventReceiver.cpp",
}
FUNCTIONS = {
    "nwfs_seed_window_geometry": "nwfs_seed_window_geometry",
    "ANativeWindow_fromSurface": "ANativeWindow_fromSurface",
    "ANativeWindow_setBuffersGeometry": "ANativeWindow_setBuffersGeometry",
    "BBQ_nativeUpdate": "_ZN7android12_GLOBAL__N_116BBQ_nativeUpdateEP7_JNIEnvP7_jclasslllli",
    "BBQ_nativeGetSurface": "_ZN7android12_GLOBAL__N_120BBQ_nativeGetSurfaceEP7_JNIEnvP7_jclasslh",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def portable(text):
    return str(text).replace(str(WORKSPACES) + "/", "$WORKSPACES/")


class Elf:
    def __init__(self, path):
        self.data = path.read_bytes()
        header = struct.unpack_from("<16sHHIQQQIHHHHHH", self.data)
        if header[0][:6] != b"\x7fELF\x02\x01" or header[2] != 183:
            raise ValueError("expected little-endian AArch64 ELF")
        self.sections = []
        for index in range(header[12]):
            fields = struct.unpack_from("<IIQQQQIIQQ", self.data, header[6] + index * header[11])
            self.sections.append(dict(zip(("name", "type", "flags", "addr", "offset", "size", "link", "info", "align", "entsize"), fields)))
        self.symbols = {}
        for section in self.sections:
            if section["type"] != 2:
                continue
            names = self.sections[section["link"]]
            for offset in range(0, section["size"], section["entsize"]):
                name, info, other, ndx, value, size = struct.unpack_from("<IBBHQQ", self.data, section["offset"] + offset)
                start = names["offset"] + name
                end = self.data.find(b"\0", start)
                if ndx and info & 15 == 2:
                    self.symbols[self.data[start:end].decode()] = {"value": value, "size": size}

    def bytes_at(self, address, length):
        for section in self.sections:
            if section["type"] != 8 and section["addr"] <= address and address + length <= section["addr"] + section["size"]:
                offset = section["offset"] + address - section["addr"]
                return self.data[offset:offset + length]
        raise ValueError("address outside file: " + hex(address))


def instructions(text):
    rows = {}
    for line in text.splitlines():
        match = re.match(r"\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+(.+)", line)
        if match:
            rows[int(match[1], 16)] = {"word": match[2], "assembly": match[3].strip()}
    return rows


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("source anchor not unique: " + old[:80])
    return text.replace(old, new, 1)


def transform(source):
    if sha(source.encode()) != SOURCE_SHA:
        raise ValueError("wrong geometry TU; source SHA mismatch")
    result = replace_once(source,
        '// [S23 cut5] fwd decl (definition ~line 1090); poke geometry on the exact nw\n'
        '// instance stamped into b->ohNativeWindow at resolve/stamp time (belt) — the\n'
        '// STAGE0 handoff (suspenders) covers the cached/pre-resolved case.\n', '')
    result = replace_once(result,
        'namespace android {\n__attribute__((weak)) int register_android_database_SQLiteConnection',
        'static void nwfs_apply_window_geometry(void* nw, const char* where, int32_t w, int32_t h);\n'
        'namespace android {\n__attribute__((weak)) int register_android_database_SQLiteConnection')
    result = replace_once(result,
        '    nwfs_seed_window_geometry(nw, "BBQ.update-stamp");  // [S23 cut5 belt]',
        '    nwfs_apply_window_geometry(nw, "BBQ.update-stamp", b->width, b->height);')
    helper_start = result.index('extern "C" void nwfs_seed_window_geometry(void* nw, const char* where) {')
    comment_start = result.rfind('\n\n', 0, helper_start) + 2
    helper_end = result.index('\n}\n', helper_start) + 3
    old_helper = result[helper_start:helper_end]
    new_helper = replace_once(old_helper,
        'extern "C" void nwfs_seed_window_geometry(void* nw, const char* where) {',
        'static void nwfs_apply_window_geometry(void* nw, const char* where, int32_t w, int32_t h) {')
    new_helper = replace_once(new_helper,
        '    int32_t w = 1200, h = 1920;  // TODO: prefer live display bounds; 5bb5 panel is 1200x1920\n', '')
    new_helper += ('\nextern "C" void nwfs_seed_window_geometry(void* nw, const char* where) {\n'
                   '    if (!nw) return;\n'
                   '    OHNativeWindow* oh = anw_unwrap(reinterpret_cast<ANativeWindow*>(nw));\n'
                   '    HiLogPrint(3, 4, 0xD000F00u, "OH_NWSeed",\n'
                   '               "[%{public}s] PRESERVE_BUFFER_GEOMETRY shim=%{public}p oh=%{public}p",\n'
                   '               where, nw, (void*)oh);\n'
                   '}\n')
    result = result[:comment_start] + new_helper + result[helper_end:]
    result = replace_once(result,
        '    // [S23 cut5 PRIMARY] last-mile: this is the exact instance Unity dequeues\n'
        '    // from — seed its geometry before returning so its first RequestBuffer\n'
        '    // carries 1200x1920 (not Buffer[0 0]). Instance-identity nailed via the log.\n', '')
    result = replace_once(result,
        '    int32_t rc = NativeWindowHandleOpt(oh, OH_OP_SET_BUFFER_GEOMETRY, width, height);',
        '    int32_t rc = 0;\n'
        '    if (width != 0) {\n'
        '        rc = NativeWindowHandleOpt(oh, OH_OP_SET_BUFFER_GEOMETRY, width, height);\n'
        '    } else {\n'
        '        NWFS_INFO("ANativeWindow_setBuffersGeometry PRESERVE_BUFFER_GEOMETRY width=0");\n'
        '    }')
    return result


def patch_text(source):
    return ''.join(difflib.unified_diff(source.splitlines(True), transform(source).splitlines(True),
        fromfile="a/android_graphics_compat_shim.cpp", tofile="b/android_graphics_compat_shim.cpp"))


def write_json(out, name, value):
    (out / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=HERE)
    args = parser.parse_args()
    out = args.out.resolve()
    (out / "evidence").mkdir(parents=True, exist_ok=True)
    (out / "source").mkdir(exist_ok=True)
    elfs = {}
    identities = {}
    disassembly = {}
    commands = []
    for tag, (relative, expected) in ARTIFACTS.items():
        path = WORKSPACES / relative
        elf = Elf(path)
        if sha(elf.data) != expected:
            raise ValueError("wrong ELF: " + tag)
        elfs[tag] = elf
        identities[tag] = {"path": portable(path), "sha256": expected, "bytes": len(elf.data)}
        disassembly[tag] = {}
        for name, symbol in FUNCTIONS.items():
            command = [str(LLVM / "llvm-objdump"), "-d", "--disassemble-symbols=" + symbol, str(path)]
            proc = subprocess.run(command, capture_output=True, text=True, check=False)
            if proc.returncode:
                raise ValueError(portable(proc.stderr))
            evidence = portable(proc.stdout + proc.stderr)
            evidence_name = f"evidence/{tag}-{name}.txt"
            (out / evidence_name).write_text(evidence)
            disassembly[tag][name] = instructions(evidence)
            commands.append({"argv": [portable(item) for item in command], "exit": proc.returncode,
                             "evidence": evidence_name, "sha256": sha(evidence.encode())})
    changes = []
    covered_offsets = set()
    for name, symbol in FUNCTIONS.items():
        if name == "BBQ_nativeGetSurface":
            continue
        base = elfs["9cc"].symbols[symbol]
        boat = elfs["adc"].symbols[symbol]
        if base != boat:
            raise ValueError("patch shifted function layout")
        for address in range(base["value"], base["value"] + base["size"], 4):
            before = elfs["9cc"].bytes_at(address, 4)
            after = elfs["adc"].bytes_at(address, 4)
            if before != after:
                changes.append({"function": name, "pc": hex(address), "before": disassembly["9cc"][name][address],
                                "after": disassembly["adc"][name][address],
                                "changed_bytes": sum(left != right for left, right in zip(before, after))})
                for section in elfs["9cc"].sections:
                    if section["addr"] <= address < section["addr"] + section["size"] and section["flags"] & 4:
                        for index, (left, right) in enumerate(zip(before, after)):
                            if left != right:
                                covered_offsets.add(section["offset"] + address - section["addr"] + index)
    all_offsets = {index for index, (left, right) in enumerate(zip(elfs["9cc"].data, elfs["adc"].data)) if left != right}
    if len(all_offsets) != 49 or len(covered_offsets) != 47 or len(changes) != 13:
        raise ValueError("unexpected byte/instruction delta")
    literals = []
    for separator in ("/", "."):
        correct = ("adapter" + separator + "activity" + separator + "AppSchedulerBridge").encode() + b"\0"
        wrong = correct.replace(b"Bridge", b"BridgX")
        literals.append({"correct": correct[:-1].decode(), "wrong": wrong[:-1].decode(),
                         "counts": {tag: {"correct": elf.data.count(correct), "wrong": elf.data.count(wrong)} for tag, elf in elfs.items()}})
    inventory_path = WORKSPACES / "westlake-inputs/generations/t2c-runtime-reproduction-20261010/input-inventory.json"
    inventory = json.loads(inventory_path.read_text())
    if sha(inventory_path.read_bytes()) != "68924eaf25b164ed19faa5412325a0d0487026cfa7401fa62642203e549d400e":
        raise ValueError("t2c inventory SHA mismatch")
    sources = {}
    for tag, relative in SOURCES.items():
        path = WORKSPACES / relative
        portable_path = portable(path)
        matches = [item for item in inventory["files"] if item["path"] == portable_path]
        if len(matches) != 1 or sha(path.read_bytes()) != matches[0]["sha256"]:
            raise ValueError("unverified source inventory: " + tag)
        sources[tag] = {**matches[0], "inventory_sha256": sha(inventory_path.read_bytes())}
        text = path.read_text()
        excerpt = []
        if tag == "gfx":
            ranges = [(538, 609), (631, 651), (1212, 1277), (1325, 1344)]
            (out / "source/android_graphics_compat_shim.cpp").write_bytes(path.read_bytes())
        elif tag == "input_receiver":
            ranges = [(249, 270)]
        elif tag == "startup":
            ranges = [(128, 150)]
        else:
            ranges = []
        for number, line in enumerate(text.splitlines(), 1):
            if any(start <= number <= end for start, end in ranges):
                excerpt.append(f"{number:5d} {line}")
        evidence_name = f"evidence/{tag}-source.txt"
        (out / evidence_name).write_text(portable_path + "\nsha256=" + sources[tag]["sha256"] + "\n" + "\n".join(excerpt) + "\n")
        sources[tag]["geometry_function_name_occurrences"] = {name: text.count(name) for name in FUNCTIONS}
    recipe_path = WORKSPACES / "westlake-inputs/generations/t2c-runtime-reproduction-20261010/r1/recipe.sh"
    if sha(recipe_path.read_bytes()) != "613102d30077037abd08cc741e65ffbaa3ffd85e157d5100631dc331cfae8ef4":
        raise ValueError("t2c recipe SHA mismatch")
    recipe_lines = recipe_path.read_text().splitlines()
    selected = [(number, line) for number, line in enumerate(recipe_lines, 1)
                if any(relative in line for relative in SOURCES.values()) or "N3B_WITH_PUBLICATION" in line or "N3B_SOURCE" in line or "android_view_InputEventReceiver.cpp" in line]
    (out / "evidence/recipe-selection.txt").write_text(portable(recipe_path) + "\nsha256=" + sha(recipe_path.read_bytes()) + "\n" + '\n'.join(portable(f"{number:5d} {line}") for number, line in selected) + "\n")
    source = (out / "source/android_graphics_compat_shim.cpp").read_text()
    patch = patch_text(source)
    (out / "u13-geometry-draft.patch").write_text(patch)
    added = sum(line.startswith('+') and not line.startswith('+++') for line in patch.splitlines())
    removed = sum(line.startswith('-') and not line.startswith('---') for line in patch.splitlines())
    counts = {name: sum(item["changed_bytes"] for item in changes if item["function"] == name) for name in FUNCTIONS if name != "BBQ_nativeGetSurface"}
    write_json(out, "instruction-deltas.json", changes)
    write_json(out, "source-bindings.json", sources)
    write_json(out, "class-name-check.json", literals)
    write_json(out, "commands.json", {"tool": {"path": str(LLVM / "llvm-objdump"), "sha256": sha((LLVM / "llvm-objdump").read_bytes())}, "commands": commands})
    write_json(out, "results.json", {"schema": "boat-runtime-port/v1", "board_access": False, "build_executed": False,
        "deployment_enabled": False, "identities": identities, "changed_bytes": len(all_offsets),
        "changed_executable_bytes": len(covered_offsets), "changed_instructions": len(changes), "function_changed_bytes": counts,
        "class_name_changed_file_offsets": [hex(offset) for offset in sorted(all_offsets - covered_offsets)],
        "draft": {"source_files": 1, "added_lines": added, "removed_lines": removed,
                  "transformed_sha256": sha(transform(source).encode()), "patch_sha256": sha(patch.encode())},
        "source_level_feasible": True, "rendering_verified": False, "single_owner_live_verified": False})
    print(f"OFFLINE-PORT bytes=49 code=47 instructions=13 TU=1 draft=+{added}/-{removed} board=false build=false")


if __name__ == "__main__":
    main()
