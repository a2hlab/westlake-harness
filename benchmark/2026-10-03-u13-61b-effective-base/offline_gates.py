import argparse
from datetime import datetime
import json
import os
import platform
import re
import shutil
import sys
import zipfile

from common import BASE, HERE, INSTALLS, MASTER, ORIGINAL_PACKAGE, ORIGINAL_PACKAGE_SHA, PACKAGE, SERIAL, SOURCE, TARGETS, WS, capture, save, sha
from validation import require_board_local_identity
import generation_bundle as bundle
import u7_executor as executor
import deployed_class_diff


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--surface", choices=["mac", "vm"], required=True)
    args = parser.parse_args()
    expected_os = {"mac": "Darwin", "vm": "Linux"}[args.surface]
    if platform.system() != expected_os:
        raise ValueError("Requested surface is not actual OS")
    composition = json.loads((HERE / "composition.json").read_text())
    if sha(BASE / "bundle.json") != composition["base_bundle_sha256"] or sha(PACKAGE / "bundle.json") != composition["bundle_sha256"]:
        raise ValueError("61b metadata binding changed")
    if sha(SOURCE) != INSTALLS or sha(ORIGINAL_PACKAGE / "bundle.json") != ORIGINAL_PACKAGE_SHA:
        raise ValueError("Source or authorized original changed")
    for entry in json.loads((BASE / "bundle.json").read_text())["board_local_baseline"]["members"]:
        bundle.member(BASE, entry)
    if args.surface == "vm":
        os.environ["PATH"] = str(MASTER / "benchmark/2026-10-01-u7-executor/.vm-tools") + ":" + os.environ["PATH"]
        scratch = HERE / ".artifacts/vm-tmp"
        scratch.mkdir(parents=True, exist_ok=True)
        os.environ["TMPDIR"] = str(scratch)
    if not os.environ.get("LAB_HOME"):
        source = (WS / "westlake-inputs/aosp-14.0.0_r1-src/SOURCE.txt").read_text()
        match = re.search(r"hw248:([^\s,]+?)/aosp-14\.0\.0_r1-art", source)
        if not match:
            raise ValueError("Set LAB_HOME from pinned provenance")
        os.environ["LAB_HOME"] = match.group(1)
    plan = executor.prepare(PACKAGE, BASE / "native")
    require_board_local_identity(plan["baseline"], plan["expected"], TARGETS, INSTALLS, {row["target"] for row in plan["changes"]})
    if plan["baseline"] != composition["baseline"]["expected"] or plan["expected"] != composition["candidate"]["expected"]:
        raise ValueError("Full signed61b identity mismatch")
    prefix = args.surface + "-" + datetime.now().strftime("%H%M%S")
    records = []
    tools = {name: shutil.which(name) for name in ["dexdump", "llvm-readelf", "llvm-nm", "llvm-objdump"]}
    if args.surface == "mac" and not tools["dexdump"]:
        tools["dexdump"] = deployed_class_diff.dexdump()
    for name in ["llvm-readelf", "llvm-nm", "llvm-objdump"]:
        if tools[name]:
            records.append(capture(prefix + "-" + name, [tools[name], "--version"], timeout=20))
    with zipfile.ZipFile(PACKAGE / "framework/oh-adapter-runtime.jar") as archive:
        dex = HERE / ".artifacts" / (prefix + "-runtime.dex")
        dex.write_bytes(archive.read("classes.dex"))
    records.append(capture(prefix + "-dex-read", [tools["dexdump"] or "dexdump", "-f", dex], timeout=30))
    command = [sys.executable, MASTER / "scripts/lab/u7_executor.py", "--dry-run", "--package", PACKAGE,
        "--baseline-native", BASE / "native", "--oatdump", MASTER / "scripts/lab/oatdump_remote.sh",
        "--out", HERE / ".artifacts" / (prefix + "-executor-plan.json")]
    production = capture(prefix + "-production-dry-run", command)
    for label, root in [("base", BASE / "native"), ("candidate", PACKAGE / "native")]:
        records.append(capture(prefix + "-native-" + label, [sys.executable, MASTER / "scripts/lab/native_predeploy.py", "--package", root,
            "--inputs", root / "native-checks/native-gates.json"]))
    records.append(capture(prefix + "-rb", [sys.executable, MASTER / "knowledge/toolchains/art-r155/check_boot_oat_rb.py",
        PACKAGE / "boot/arm64/boot.oat", "--image", PACKAGE / "boot/arm64/boot.art"]))
    records.append(capture(prefix + "-t4b", [sys.executable, MASTER / "knowledge/toolchains/art-r155/t4b_build_switch_gate.py",
        "--libart", PACKAGE / "native/payload/route/libart.so", "--oat", PACKAGE / "boot/arm64/boot.oat",
        "--build", MASTER / "benchmark/2026-10-02-u12-jar-r2-bake/evidence/U12-BUILD-snapshot.md",
        "--out", HERE / "evidence" / (prefix + "-t4b.json")]))
    records.append(capture(prefix + "-frozen", [sys.executable, MASTER / "scripts/lab/check_frozen.py", "--package", PACKAGE / "native"]))
    result = dict(surface=args.surface, actual_os=platform.system(), architecture=platform.machine(), serial=SERIAL,
        base_bundle_sha256=sha(BASE / "bundle.json"), bundle_sha256=sha(PACKAGE / "bundle.json"),
        native_manifest_sha256=sha(PACKAGE / "native/package.json"), native_inputs_sha256=sha(PACKAGE / "native/native-checks/native-gates.json"),
        production=production, records=records, tools=tools, production_gates_passed=production["exit_code"] == 0 and all(row["exit_code"] == 0 for row in records),
        service_action_count=0, execution_enabled=False, device_access=False)
    save("gates/" + args.surface + ".json", result)
    save("gates/" + prefix + ".json", result)
    print(json.dumps({name: result[name] for name in ["surface", "actual_os", "architecture", "base_bundle_sha256", "bundle_sha256", "production_gates_passed", "service_action_count"]}))
    return 0 if result["production_gates_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
