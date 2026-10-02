import argparse
from datetime import datetime
import json
import os
import platform
import re
import shutil
import sys
import zipfile

from common import BASE, HERE, MASTER, PACKAGE, WS, capture, save, sha
import check_frozen as frozen
import deployed_class_diff


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--surface", choices=["mac", "vm"], required=True)
    args = parser.parse_args()
    expected_os = {"mac": "Darwin", "vm": "Linux"}[args.surface]
    if platform.system() != expected_os:
        raise ValueError("OS identity disagrees with surface")
    composition = json.loads((HERE / "composition.json").read_text())
    if composition["bundle_sha256"] != sha(PACKAGE / "bundle.json"):
        raise ValueError("Final bundle changed")
    if args.surface == "vm":
        os.environ["PATH"] = str(MASTER / "benchmark/2026-10-01-u7-executor/.vm-tools") + ":" + os.environ["PATH"]
        scratch = HERE / ".artifacts/vm-tmp"
        scratch.mkdir(parents=True, exist_ok=True)
        os.environ["TMPDIR"] = str(scratch)
    if not os.environ.get("LAB_HOME"):
        provenance = (WS / "westlake-inputs/aosp-14.0.0_r1-src/SOURCE.txt").read_text()
        match = re.search(r"hw248:([^\s,]+?)/aosp-14\.0\.0_r1-art", provenance)
        if not match:
            raise ValueError("LAB_HOME not provided or recoverable from pinned source provenance")
        os.environ["LAB_HOME"] = match.group(1)
    tools = {name: shutil.which(name) for name in ["dexdump", "llvm-readelf", "llvm-nm", "llvm-objdump"]}
    if args.surface == "mac" and not tools["dexdump"]:
        tools["dexdump"] = deployed_class_diff.dexdump()
    prefix = args.surface + "-" + datetime.now().strftime("%H%M%S")
    records = []
    for name in ["llvm-readelf", "llvm-nm", "llvm-objdump"]:
        if tools[name]:
            records.append(capture(prefix + "-" + name, [tools[name], "--version"], timeout=20))
    with zipfile.ZipFile(PACKAGE / "framework/oh-adapter-runtime.jar") as archive:
        dex = HERE / ".artifacts" / (args.surface + "-runtime.dex")
        dex.write_bytes(archive.read("classes.dex"))
    records.append(capture(prefix + "-dex-read", [tools["dexdump"] or "dexdump", "-f", dex], timeout=30))
    production_command = [sys.executable, MASTER / "scripts/lab/u7_executor.py", "--dry-run", "--package", PACKAGE,
        "--baseline-native", BASE / "native", "--oatdump", MASTER / "scripts/lab/oatdump_remote.sh",
        "--out", HERE / ".artifacts" / (args.surface + "-executor-plan.json")]
    production = capture(prefix + "-production-dry-run", production_command, timeout=600)
    records.append(capture(prefix + "-native-active", [sys.executable, MASTER / "scripts/lab/native_predeploy.py",
        "--package", PACKAGE / "native", "--inputs", PACKAGE / "native/native-checks/native-gates.json"]))
    records.append(capture(prefix + "-rb", [sys.executable, MASTER / "knowledge/toolchains/art-r155/check_boot_oat_rb.py",
        PACKAGE / "boot/arm64/boot.oat", "--image", PACKAGE / "boot/arm64/boot.art"]))
    records.append(capture(prefix + "-t4b", [sys.executable, MASTER / "knowledge/toolchains/art-r155/t4b_build_switch_gate.py",
        "--libart", PACKAGE / "native/payload/route/libart.so", "--oat", PACKAGE / "boot/arm64/boot.oat",
        "--build", MASTER / "benchmark/2026-10-02-u12-jar-r2-bake/evidence/U12-BUILD-snapshot.md",
        "--out", HERE / "evidence" / (prefix + "-t4b.json")]))
    records.append(capture(prefix + "-frozen", [sys.executable, MASTER / "scripts/lab/check_frozen.py", "--package", PACKAGE / "native"]))
    composed = {}
    for serial, board in composition["candidate_boards"].items():
        lines, violations = frozen.check_artifacts(frozen.active(frozen.load(MASTER / "knowledge/frozen/frozen.json")),
            board["expected"], "U13 final " + serial[:8])
        composed[serial] = dict(lines=lines, violations=violations)
    save("evidence/" + args.surface + "-frozen-composed.json", composed)
    summary = dict(surface=args.surface, actual_os=platform.system(), architecture=platform.machine(), tools=tools,
        bundle_sha256=sha(PACKAGE / "bundle.json"), native_manifest_sha256=sha(PACKAGE / "native/package.json"),
        native_inputs_sha256=sha(PACKAGE / "native/native-checks/native-gates.json"), records=records, production=production,
        active_registry_sha256=sha(MASTER / "knowledge/gates/native-predeploy-exceptions.json"),
        production_gates_passed=production["exit_code"] == 0, composed_frozen_violations=sum(row["violations"] for row in composed.values()),
        execution_enabled=False, device_access=False, heavy_build=False)
    save("gates/" + args.surface + ".json", summary)
    save("gates/" + prefix + ".json", summary)
    print(json.dumps({name: summary[name] for name in ["surface", "actual_os", "architecture", "bundle_sha256", "production_gates_passed", "composed_frozen_violations"]}))
    return production["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
