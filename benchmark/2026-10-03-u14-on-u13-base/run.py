from datetime import datetime
import argparse
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from common import HERE, MASTER, PRIOR, capture, expand, load, save, sha
import generation_bundle as bundle
import generation_static_checks as static


def image(package, variant):
    result = bundle.image_checks(package)
    save(variant + "/evidence/image-gates.json", result)
    print(result["log"])
    return 0 if result["G1"] and result["G2"] else 1


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--image-only":
        raise SystemExit(image(Path(sys.argv[2]), sys.argv[3]))
    if platform.system() != "Darwin":
        raise ValueError("This lane's fresh run is Mac-only")
    parser = argparse.ArgumentParser(description="Fresh disabled U14 dry-runs with parameterized per-board U13 BASE")
    for variant in ["common", "61b"]:
        parser.add_argument("--" + variant + "-base", type=Path)
        parser.add_argument("--" + variant + "-base-sha256")
    args = vars(parser.parse_args())
    for variant in ["common", "61b"]:
        if bool(args[variant + "_base"]) != bool(args[variant + "_base_sha256"]):
            parser.error("BASE path and full SHA must be supplied together: " + variant)
    pins = load(HERE / "base-identities.json")["variants"]
    stamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
    tool_paths = [MASTER / "scripts/lab" / name for name in ["u7_executor.py", "generation_bundle.py", "generation_static_checks.py", "native_predeploy.py", "deployment_native_gate.py", "deployed_class_diff.py", "open_site_scan.py", "check_frozen.py"]]
    tool_paths += [MASTER / "knowledge/gates" / name for name in ["native-predeploy-exceptions.json", "new-native-admissions.json", "bcp-swap-exceptions.json"]]
    before = {str(path): sha(path) for path in tool_paths}
    records = []
    for variant in ["common", "61b"]:
        base = (args[variant + "_base"] or expand(pins[variant]["unarmed"])).resolve()
        base_sha = args[variant + "_base_sha256"] or pins[variant]["signed_unarmed_bundle_sha256"]
        package = HERE / ".artifacts" / (variant + "-" + stamp)
        records.append(capture("rebind-" + variant, [sys.executable, HERE / "rebind.py", "--variant", variant, "--base", base,
            "--base-sha256", base_sha, "--out", package]))
        if records[-1]["exit_code"]:
            raise ValueError("Metadata preparation refused; no production attempt")
        data = load(package / "bundle.json")
        records.append(capture("executor-" + variant, [sys.executable, MASTER / "scripts/lab/u7_executor.py", "--dry-run", "--package", package,
            "--baseline-native", base / "native", "--out", HERE / ".artifacts" / ("executor-" + variant + ".json")]))
        save(variant + "/evidence/executor.json", load(HERE / ".artifacts" / ("executor-" + variant + ".json")))
        policy = package / data["static_checks"]["policy"]["source"]
        output = HERE / ".artifacts" / ("static-" + variant + ".json")
        records.append(capture("static-" + variant, [sys.executable, MASTER / "scripts/lab/generation_static_checks.py", "--package", package,
            "--baseline", base, "--policy", policy, "--out", output]))
        save(variant + "/evidence/static.json", load(output))
        for label, native in [("candidate", package / "native"), ("baseline", base / "native")]:
            records.append(capture("native-" + variant + "-" + label, [sys.executable, MASTER / "scripts/lab/native_predeploy.py", "--package", native,
                "--inputs", native / "native-checks/native-gates.json", "--exceptions", MASTER / "knowledge/gates/native-predeploy-exceptions.json", "--readelf", "llvm-readelf"]))
            save(variant + "/evidence/native-" + label + ".json", load(HERE / ".artifacts/raw" / ("native-" + variant + "-" + label + ".txt")))
        records.append(capture("image-" + variant, [sys.executable, HERE / "run.py", "--image-only", package, variant]))
        build = HERE / "inputs/U14-BUILD.md"
        build.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PRIOR / "inputs/U14-BUILD.md", build)
        records.append(capture("rb-" + variant, [sys.executable, MASTER / "knowledge/toolchains/art-r155/check_boot_oat_rb.py",
            package / "boot/arm64/boot.oat", "--image", package / "boot/arm64/boot.art"]))
        output = HERE / ".artifacts" / ("t4b-" + variant + "-" + stamp + ".json")
        records.append(capture("t4b-" + variant, [sys.executable, MASTER / "knowledge/toolchains/art-r155/t4b_build_switch_gate.py",
            "--libart", package / "native/payload/route/libart.so", "--oat", package / "boot/arm64/boot.oat", "--build", build, "--out", output]))
        save(variant + "/evidence/t4b.json", load(output))
        records.append(capture("frozen-" + variant, [sys.executable, MASTER / "scripts/lab/check_frozen.py", "--package", package / "native"]))
    after = {str(path): sha(path) for path in tool_paths}
    if before != after:
        raise ValueError("Gate or active table changed during replay; fresh rerun required")
    save("tool-identity.json", dict(actual_os=platform.system() + " " + platform.machine(), master_head=subprocess.check_output(["git", "-C", str(MASTER), "rev-parse", "HEAD"], text=True).strip(),
        before=before, after=after, unchanged=True, gate_code_written=False, active_tables_written=False))
    save("gate-runs.json", dict(records=records, actual_os=platform.system() + " " + platform.machine(), vm_used=False, remote_oatdump=False,
        device_access=False, lock_taken=False, production_gates_passed=False, promotion_confirmed=False, execution_enabled=False,
        interpretation="Fresh production executor attempts; required G2 remains a refusal without executable oatdump. Component exits are independent, not borrowed PASS."))
    print("U14 on U13 Mac diagnostics complete; disabled, raw refusals retained")


if __name__ == "__main__":
    main()
