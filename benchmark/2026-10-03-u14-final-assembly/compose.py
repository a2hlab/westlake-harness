import copy
import json
from pathlib import Path
import shutil
import subprocess

from common import BASE, BASE_SHA, BRIDGE_CHECKS, HERE, MASTER, PARTIAL, PLAN, WS, portable, save, sha
from validation import ADDITIONS, CHANGES, check_partial


def install(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.chmod(target.stat().st_mode | 0o200)
    shutil.copyfile(source, target)


def main():
    if sha(BASE / "bundle.json") != BASE_SHA or PARTIAL.exists():
        raise ValueError("Content base drift or existing immutable partial output")
    selected = {
        "payload/android/lib64/liboh_adapter_bridge.so": WS / "westlake-inputs/generations/u14-m5m6-m5m6-a/out/liboh_adapter_bridge.so",
        "payload/runtime/appspawn-x": PLAN / ".artifacts/inputs/native-slots/appspawn-x",
        "payload/android/lib64/westlake_flutter/libandroid.so": PLAN / ".artifacts/inputs/native-slots/westlake_flutter/libandroid.so",
        "payload/android/lib64/westlake_native/libwestlake_native_abi.so": PLAN / ".artifacts/inputs/native-slots/westlake_native/libwestlake_native_abi.so",
        "payload/android/lib64/libicuuc.so": PLAN / ".artifacts/inputs/native-slots/libicuuc.so",
        "payload/android/lib64/libicuuc.z.so": PLAN / ".artifacts/inputs/native-slots/libicuuc.so",
        "payload/android/lib64/libicu74compat.so": PLAN / ".artifacts/inputs/native-slots/libicu74compat.so",
        "payload/android/framework/oh-adapter-runtime.jar": PLAN / ".artifacts/inputs/runtime/oh-adapter-runtime.jar",
        "payload/android/framework/adapter-mainline-stubs.jar": PLAN / ".artifacts/inputs/jars9/adapter-mainline-stubs.jar",
    }
    expected = CHANGES | ADDITIONS
    for member, source in selected.items():
        if sha(source) != expected[member]:
            raise ValueError("Selected input drift: " + member)
    repeat = WS / "westlake-inputs/generations/u14-m5m6-m5m6-b/out/liboh_adapter_bridge.so"
    if sha(repeat) != expected["payload/android/lib64/liboh_adapter_bridge.so"]:
        raise ValueError("Bridge paired build mismatch")
    PARTIAL.mkdir(parents=True)
    for directory in ["native", "framework"]:
        subprocess.run(["/bin/cp", "-cR", BASE / directory, PARTIAL / directory], check=True)
    for member, source in selected.items():
        install(source, PARTIAL / "native" / member)
    for name in ["oh-adapter-runtime.jar", "adapter-mainline-stubs.jar"]:
        install(PARTIAL / "native/payload/android/framework" / name, PARTIAL / "framework" / name)
    old_manifest = json.loads((BASE / "native/package.json").read_text())
    manifest = copy.deepcopy(old_manifest)
    manifest["files"].update(expected)
    for member, digest in expected.items():
        target = "/system/android/" + member.removeprefix("payload/android/") if member.startswith("payload/android/") else "/system/bin/appspawn-x"
        manifest["live_hashes"][target] = digest
    manifest.update(bridge_sha256=expected["payload/android/lib64/liboh_adapter_bridge.so"], variant="U14 single batch native/JAR staging; images pending", rollout_ready=False, rollout_blocker="No bundle descriptor: new BCP images and actual paired receipt pending")
    save(PARTIAL / "native/package.json", manifest)
    checks = PARTIAL / "native/native-checks"
    shutil.rmtree(checks)
    subprocess.run(["/bin/cp", "-cR", BRIDGE_CHECKS, checks], check=True)
    scan = json.loads((checks / "scan-manifest.json").read_text())
    host_donor = WS / "westlake-harness-wiki/benchmark/2026-10-03-u14-appns-build"
    replacements = {
        "n4-host.c": host_donor / ".artifacts/candidate-stock-host.patched.c",
        "u10-1-resident-compat.h": host_donor / "inputs/resident-compat.h",
        "u12-zlib-route.h": host_donor / "inputs/zlib-route.h",
    }
    extra = {
        "u14-flutter-egl.cpp": (MASTER / "benchmark/2026-10-03-u14-flutter-libandroid/src/flutter_egl.cpp", "payload/android/lib64/westlake_flutter/libandroid.so"),
        "u14-gecko-abi.c": (MASTER / "benchmark/2026-10-03-u14-native-abi-gecko/src/gecko_abi.c", "payload/android/lib64/westlake_native/libwestlake_native_abi.so"),
        "u14-gecko-dlext.c": (MASTER / "benchmark/2026-10-03-u14-native-abi-gecko/src/android_dlopen_ext.c", "payload/android/lib64/westlake_native/libwestlake_native_abi.so"),
    }
    source_receipts = []
    for name, source in (replacements | {name: source for name, (source, _) in extra.items()}).items():
        install(source, checks / name)
        scan["sources"][name] = dict(path=name, sha256=sha(source), source_sha256=sha(source), origin=portable(source), first_line=1)
        proof = HERE / "inputs" / name
        proof.parent.mkdir(parents=True, exist_ok=True)
        proof.write_text(portable(source.read_text()))
        source_receipts.append(dict(source=source, source_sha256=sha(source), snapshot=proof.relative_to(HERE), snapshot_sha256=sha(proof)))
    for name, (_, artifact) in extra.items():
        scan["profiles"].append(dict(name=name, rule="namespace", source=name, identity=dict(artifact=artifact)))
    for profile in scan["profiles"]:
        profile["identity"].update(package="u14-single-batch-offline-staging", manifest_sha256=sha(PARTIAL / "native/package.json"), artifact_sha256=manifest["files"][profile["identity"]["artifact"]])
    save(checks / "scan-manifest.json", scan)
    inputs = json.loads((checks / "native-gates.json").read_text())
    inputs["package_manifest_sha256"] = sha(PARTIAL / "native/package.json")
    inputs["initialization"]["manifest"]["sha256"] = sha(checks / "scan-manifest.json")
    save(checks / "native-gates.json", inputs)
    state = dict(schema="westlake-u14-partial/v1", partial=PARTIAL, comparison_base=BASE, comparison_base_sha256=BASE_SHA,
        native_manifest_sha256=sha(PARTIAL / "native/package.json"), native_inputs_sha256=sha(checks / "native-gates.json"),
        changes=CHANGES, additions=ADDITIONS, sources=source_receipts, images="pending", paired_receipt=None,
        retained_native_image_underlay="Historical U13 bytes for inventory only; not a U14 boot group", transaction_base="required parameter at finalization; not inferred from content base",
        execution_enabled=False, final_batch_complete=False, deploy_allowed=False, vm_used=False)
    check_partial(old_manifest["files"], manifest["files"], state, (PARTIAL / "bundle.json").exists())
    for member, digest in manifest["files"].items():
        if sha(PARTIAL / "native" / member) != digest:
            raise ValueError("Native inventory mismatch: " + member)
    save("composition.json", state)
    for name, source in [("native-manifest.json", PARTIAL / "native/package.json"), ("native-inputs.json", checks / "native-gates.json"), ("scan-manifest.json", checks / "scan-manifest.json")]:
        save("manifests/" + name, json.loads(source.read_text()))
    print("PARTIAL changes=8 additions=1 images=pending bundle_descriptor=absent disabled=true")
    print("manifest=" + state["native_manifest_sha256"] + " inputs=" + state["native_inputs_sha256"])


if __name__ == "__main__":
    main()
