"""Actual production dry-run on the executing OS; no Board imports or device commands."""
import argparse
import json
import platform
import shutil
import sys
import zipfile

from common import BASE, HERE, MASTER, PACKAGE, capture, save, sha
import check_frozen as frozen
import generation_bundle as gb


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--surface", choices=["mac", "vm"], required=True)
    args = parser.parse_args()
    system = platform.system()
    expected_system = {"mac": "Darwin", "vm": "Linux"}[args.surface]
    if system != expected_system:
        raise ValueError("surface label disagrees with actual OS: " + system)
    composition = json.loads((HERE / "composition.json").read_text())
    if sha(PACKAGE / "bundle.json") != composition["bundle_sha256"]:
        raise ValueError("draft bundle changed")
    tools = {name: shutil.which(name) for name in ["dexdump", "llvm-readelf", "llvm-nm", "llvm-objdump", "readelf"]}
    records = []
    for name, path in tools.items():
        if path and name != "dexdump":
            records.append(capture(args.surface + "-tool-" + name, [path, "--version"], timeout=20))
    data, manifest, _ = gb.validate(PACKAGE)
    with zipfile.ZipFile(gb.member(PACKAGE, data["runtime_jar"])) as archive:
        dex = HERE / ".artifacts" / (args.surface + "-runtime.dex")
        dex.write_bytes(archive.read("classes.dex"))
    dex_record = capture(args.surface + "-dex-read", [tools["dexdump"] or "dexdump", "-f", dex], timeout=30)
    output = HERE / ".artifacts" / (args.surface + "-executor")
    command = [sys.executable, MASTER / "scripts/lab/u7_executor.py", "--dry-run", "--package", PACKAGE, "--baseline-native", BASE / "native", "--oatdump", MASTER / "scripts/lab/oatdump_remote.sh", "--out", output]
    production = capture(args.surface + "-production-dry-run", command, timeout=600)
    rb = capture(args.surface + "-rb", [sys.executable, MASTER / "knowledge/toolchains/art-r155/check_boot_oat_rb.py", PACKAGE / "boot/arm64/boot.oat", "--image", PACKAGE / "boot/arm64/boot.art"])
    t4b = capture(args.surface + "-t4b", [sys.executable, MASTER / "knowledge/toolchains/art-r155/t4b_build_switch_gate.py", "--libart", PACKAGE / "native/payload/route/libart.so", "--oat", PACKAGE / "boot/arm64/boot.oat", "--build", MASTER / "benchmark/2026-10-02-u12-jar-r2-bake/evidence/U12-BUILD-snapshot.md", "--out", HERE / "evidence" / (args.surface + "-t4b.json")])
    check = capture(args.surface + "-frozen", [sys.executable, MASTER / "scripts/lab/check_frozen.py", "--package", PACKAGE / "native"])
    composition_checks = {}
    for serial, board in composition["candidate_boards"].items():
        lines, count = frozen.check_artifacts(frozen.active(frozen.load(MASTER / "knowledge/frozen/frozen.json")), board["expected"], "U13 draft " + serial[:8])
        composition_checks[serial] = dict(lines=lines, violations=count)
    save("evidence/" + args.surface + "-frozen-composed.json", composition_checks)
    image = capture(args.surface + "-images", [sys.executable, MASTER / "scripts/lab/generation_bundle.py", "--package", PACKAGE, "--dry-run", "--run-image-gates", "--oatdump", MASTER / "scripts/lab/oatdump_remote.sh", "--out", HERE / ".artifacts" / (args.surface + "-image-plan.json")], timeout=150)
    image_path = HERE / ".artifacts" / (args.surface + "-image-plan.json")
    image_gates = json.loads(image_path.read_text()).get("image_gates") if image_path.exists() else None
    summary = dict(surface=args.surface, actual_os=system, architecture=platform.machine(), bundle_sha256=sha(PACKAGE / "bundle.json"), native_manifest_sha256=sha(PACKAGE / "native/package.json"), tools=tools, tool_checks=records, dex_read=dex_record, production=production, rb=rb, t4b=t4b, frozen=check, composed_frozen_violations=sum(row["violations"] for row in composition_checks.values()), image_command=image, image_gates=image_gates, execution_enabled=False, rollout_ready=False, device_access=False, production_gates_passed=production["exit_code"] == 0)
    save("gates/" + args.surface + ".json", summary)
    print(json.dumps({name: summary[name] for name in ["surface", "actual_os", "architecture", "bundle_sha256", "production", "production_gates_passed", "composed_frozen_violations", "image_gates", "execution_enabled"]}, indent=2))
    return production["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
