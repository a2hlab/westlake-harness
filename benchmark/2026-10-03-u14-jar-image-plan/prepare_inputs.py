import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys

from validation import DEX2OAT, DRIVER, HOST, IMAGE_NAMES, JARS, RUNTIME, STUBS, check_plan, check_slots


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = Path(os.environ.get("WORKSPACES", REPO.parent))
MASTER = WS / "westlake-harness"
BASE = WS / "westlake-harness-bms/benchmark/2026-10-03-u13-effective-rebind/.artifacts/bundle-v4"
BASE_SHA = "91272eaf4cdda30b0c079575cd269959c6f6dab9f23a09a0fed567c20478bd28"
PRIVATE = HERE / ".artifacts/inputs"
sys.path.insert(0, str(MASTER / "scripts/lab"))
import generation_bundle


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def portable(value):
    if isinstance(value, dict):
        return {name: portable(item) for name, item in value.items()}
    if isinstance(value, list):
        return [portable(item) for item in value]
    if isinstance(value, Path):
        value = str(value)
    if isinstance(value, str):
        for root, token in [(WS, "$WORKSPACES"), (Path.home(), "$HOME")]:
            value = value.replace(str(root) + "/", token + "/")
        value = re.sub(r"/home/[^/\s'\"]+", "$LAB_HOME", value)
    return value


def save(name, data):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(portable(data), indent=2) + "\n")


def stage(source, destination, expected):
    if sha(source) != expected:
        raise ValueError("Donor SHA mismatch: " + str(source))
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and sha(destination) != expected:
        raise ValueError("Existing snapshot changed")
    if not destination.exists():
        shutil.copyfile(source, destination)
    if sha(destination) != expected:
        raise ValueError("Staged SHA mismatch")
    return dict(source=source, snapshot=destination, sha256=expected, bytes=destination.stat().st_size)


def main():
    if sha(BASE / "bundle.json") != BASE_SHA:
        raise ValueError("Immutable U13 content base changed")
    bundle, manifest, _ = generation_bundle.validate(BASE)
    bcp = generation_bundle.bcp_members(BASE, bundle, manifest)
    old_receipt = json.loads(generation_bundle.member(BASE, bundle["paired_build_receipt"]).read_text())
    bt = WS / "westlake-inputs/generations/u14-stubs-bt-v1/adapter-mainline-stubs-u14-bt.jar"
    runtime_source = WS / "westlake-inputs/generations/u14-jar-v1/oh-adapter-runtime-u14-v1.jar"
    rows = []
    for name in JARS:
        old_sha = sha(bcp[name])
        if old_receipt["input_jars"][name + ".jar"] != old_sha:
            raise ValueError("Effective U13 BCP differs from accepted paired receipt")
        source = bt if name == "adapter-mainline-stubs" else bcp[name]
        digest = STUBS if name == "adapter-mainline-stubs" else old_sha
        row = stage(source, PRIVATE / "jars9" / (name + ".jar"), digest)
        row.update(name=name + ".jar", u13_sha256=old_sha, target=generation_bundle.FW + name + ".jar")
        rows.append(row)
    runtime = stage(runtime_source, PRIVATE / "runtime/oh-adapter-runtime.jar", RUNTIME)
    runtime.update(in_bcp=False, source_commit="2c70182c73", target=generation_bundle.FW + "oh-adapter-runtime.jar")
    images = []
    for member in bundle["boot_group"]["members"]:
        name = Path(member["target"]).name
        if name not in IMAGE_NAMES:
            continue
        stage(generation_bundle.member(BASE, member), PRIVATE / "reference-u13/arm64" / name, member["sha256"])
        if "adapter-mainline-stubs" in name:
            prediction = "expected-change: changed segment"
        elif name.endswith(".vdex"):
            prediction = "expected-same: unchanged DEX; verify after bake"
        else:
            prediction = "may-change: aggregate layout, compilation or embedded path"
        images.append(dict(name=name, target=member["target"], u13_sha256=member["sha256"],
            candidate_sha256=None, rebake=True, prediction=prediction))
    images.sort(key=lambda row: row["name"])
    driver_local = MASTER / "knowledge/toolchains/art-r155/t5_gen_image.sh"
    plan = dict(schema="westlake-u14-image-preparation/v1", execution_enabled=False, bake_executed=False,
        deploy_allowed=False, content_base=dict(source=BASE, sha256=BASE_SHA), transaction_base="parameter required at final composition; signed per-board state, not inferred U13 promotion",
        bcp=rows, runtime=runtime, changed_bcp=["adapter-mainline-stubs.jar"], image_count=27,
        actual_changed_image_count=None, candidate_bundle_sha256=None,
        machine=dict(selected="hw248", historical_evidence="U12 bake-receipt.json: two successful dex2oat runs on hw248",
            current_remote_verified=False, a2hlab_use=False, remote_root="$LAB_HOME/u14-bt-bake-0349-87cf-v1"),
        frozen_tools=dict(dex2oat64=dict(path="$LAB_HOME/aosp-14.0.0_r1-art/out/host/linux-x86/bin/dex2oat64", sha256=DEX2OAT),
            driver=dict(path="$LAB_HOME/cc-wiki-t5/tool/t5_gen_image.sh", sha256=DRIVER),
            local_repository_driver=dict(path=driver_local, sha256=sha(driver_local), usable_as_frozen_driver=False)),
        pair=dict(same_work_path=True, selected_run=1, expected_outputs=27, status="NOT_RUN",
            historical_exception="T7D-REPRO-BACKTRACE-001 is evidence only; changed U14 inputs need exact outer review if nondeterminism occurs"))
    check_plan(plan, images)
    save("plan.json", plan)
    save("expected-images.json", images)
    with (HERE / "expected-images.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(images[0]))
        writer.writeheader()
        writer.writerows(images)
    save("paired-receipt.template.json", dict(status="NOT_RUN", input_jars={row["name"]: row["sha256"] for row in rows},
        outputs={row["name"]: None for row in images}, build_command=None, dex2oat_sha256=DEX2OAT, driver_sha256=DRIVER,
        toolchain_identity_sha256=None, build_log_sha256=None, session_log_sha256=None,
        dex2oat_exit_code=None, tee_exit_code=None, session_tee_exit_code=None, exception_used=False, u14_outer_exception_approval=None))
    references = ["benchmark/2026-10-02-u12-jar-r2-bake/README.md",
        "benchmark/2026-10-02-u12-jar-r2-bake/bake/bake_u12.sh",
        "benchmark/2026-10-02-u12-jar-r2-bake/bake/dex2oat64-tee.sh",
        "benchmark/2026-10-02-u12-jar-r2-bake/gates/bake-receipt.json",
        "benchmark/2026-10-02-u12-jar-r2-bake/compare_runs.py",
        "benchmark/2026-10-02-u12-jar-r2-bake/evidence/U12-BUILD-snapshot.md",
        "benchmark/2026-10-03-u14-jar-v1/src/adapter/activity/InProcessBindOrder.java",
        "benchmark/2026-10-03-u14-jar-v1/build_v1.py",
        "benchmark/2026-10-03-u14-jar-v1/results.json",
        "benchmark/2026-10-03-u14-jar-v1/gates/needle-ActivityManagerBindProxy.diff",
        "benchmark/2026-10-03-bt-le-scancallback/build_stubs_bt.py",
        "benchmark/2026-10-03-bt-le-scancallback/results.json",
        "benchmark/2026-10-03-bt-le-scancallback/stubs/members.tsv",
        "benchmark/2026-10-03-bt-le-scancallback/stubs/donor/android/bluetooth/le/ScanCallback.java",
        "benchmark/2026-10-03-bt-le-scancallback/stubs/compile-only/android/annotation/IntDef.java",
        "benchmark/2026-10-03-u14-appns-build/README.md",
        "benchmark/2026-10-03-u14-appns-build/recipe/reproduce_host.py",
        "benchmark/2026-10-03-u14-appns-build/recipe/win-u14-appns-public-libs.patch",
        "benchmark/2026-10-03-u14-appns-build/recipe/icu74_shim.S",
        "benchmark/2026-10-03-u14-appns-build/recipe/icu74_shim.map",
        "benchmark/2026-10-03-u14-appns-build/evidence/wall2-shim-and-elfedit.txt",
        "benchmark/2026-10-03-u14-flutter-libandroid/README.md",
        "benchmark/2026-10-03-u14-flutter-libandroid/results.json",
        "benchmark/2026-10-03-u14-native-abi-gecko/README.md",
        "benchmark/2026-10-03-u14-native-abi-gecko/results.json",
        "benchmark/2026-10-03-u14-native-abi-gecko/src/gecko_abi.c",
        "benchmark/2026-10-03-u14-native-abi-gecko/src/android_dlopen_ext.c",
        "benchmark/2026-10-03-u14-native-abi-gecko/src/android_dlext_abi.h"]
    snapshots = []
    for relative in references:
        source = MASTER / relative
        destination = HERE / "inputs/source" / relative.removeprefix("benchmark/")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(portable(source.read_text()))
        snapshots.append(dict(source=source, source_sha256=sha(source), snapshot=str(destination.relative_to(HERE)),
            snapshot_sha256=sha(destination), transformation="home paths made portable; evidence snapshot, not an executed build recipe"))
    frozen = json.loads((MASTER / "knowledge/frozen/frozen.json").read_text())
    save("inputs/FZ-005.json", [entry for entry in frozen["entries"] if entry["id"] == "FZ-005"])
    save("inputs/accepted-u13-paired-receipt.json", old_receipt)
    save("source-snapshots.json", snapshots)
    donor_evidence = []
    for relative in ["westlake-inputs/generations/u14-jar-v1/logs/build-20261003T022814.log",
        "westlake-inputs/generations/u14-stubs-bt-v1/logs/build-20261003T030913.log",
        "westlake-harness-wiki/benchmark/2026-10-03-u14-appns-build/.artifacts/u141-compile.log",
        "westlake-harness-wiki/benchmark/2026-10-03-u14-appns-build/.artifacts/u141-link.log",
        "westlake-harness-wiki/benchmark/2026-10-03-u14-appns-build/.artifacts/u142-compile.log",
        "westlake-harness-wiki/benchmark/2026-10-03-u14-appns-build/.artifacts/u142-link.log",
        "westlake-harness-wiki/benchmark/2026-10-03-u14-appns-build/.artifacts/candidate-stock-host.patched.c",
        "westlake-inputs/generations/u14-icu-wall2-v1/build-commands.txt",
        "westlake-inputs/generations/u14-icu-wall2-v1/logs/build-shim.log",
        "westlake-inputs/generations/u14-icu-wall2-v1/logs/patchelf-libicuuc.log",
        "westlake-inputs/generations/u14-flutter-libandroid-v1/SHA256SUMS",
        "westlake-inputs/generations/u14-native-abi-gecko-v2/SHA256SUMS"]:
        source = WS / relative
        destination = HERE / "inputs/donor-evidence" / relative.replace("/", "--")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(portable(source.read_text()))
        donor_evidence.append(dict(source=source, source_sha256=sha(source), snapshot=str(destination.relative_to(HERE)),
            snapshot_sha256=sha(destination), execution="donor historical build, not a new cx-bms build"))
    save("inputs/donor-evidence.json", donor_evidence)
    checksum_path = HERE / "inputs/jars9.sha256"
    checksum_path.write_text("".join(row["sha256"] + "  " + row["name"] + "\n" for row in rows))
    reference_lines = [row["sha256"] + "  " + row["name"] for row in rows]
    reference_lines.extend(row["u13_sha256"] + "  arm64/" + row["name"] for row in images)
    (HERE / "inputs/t5-ref-u14.sha256").write_text("\n".join(reference_lines) + "\n")
    host_source = WS / "westlake-harness-wiki/benchmark/2026-10-03-u14-appns-build/.artifacts"
    host = stage(host_source / "appspawn-x-u141", PRIVATE / "native-slots/appspawn-x", HOST)
    if sha(host_source / "appspawn-x-u142") != HOST:
        raise ValueError("Host double build mismatch")
    releases = WS / "westlake-inputs/generations"
    flutter = stage(releases / "u14-flutter-libandroid-v1/payload/android/lib64/westlake_flutter/libandroid.so",
        PRIVATE / "native-slots/westlake_flutter/libandroid.so",
        "fff9be3190f1b1c99c3fd4559d258cbac131fb657d10b1fa7060f61c4002d5e5")
    abi = stage(releases / "u14-native-abi-gecko-v2/payload/android/lib64/westlake_native/libwestlake_native_abi.so",
        PRIVATE / "native-slots/westlake_native/libwestlake_native_abi.so",
        "7605812cc5249534950bb0533baa3199b380daf6e763af12ed216c2c70649515")
    icu = stage(releases / "u14-icu-wall2-v1/libicuuc-u14.so", PRIVATE / "native-slots/libicuuc.so",
        "9b36b989dd10f29434cc60b6b7d1895878442d07f1d6b0674db9b1379420d93f")
    shim = stage(releases / "u14-icu-wall2-v1/libicu74compat.so", PRIVATE / "native-slots/libicu74compat.so",
        "4886bc5c2b4ef0486ecda6fa3248ace4af6a1c57ed7029b17cfd4868ad2c92af")
    slots = dict(execution_enabled=False, final_batch_complete=False,
        historical_bridge_only_bundle="90de6c7e405667dfc3900ab2960a440a2e72f3c704b919d36f96e869f66b1199",
        stage="input slots only; immutable bridge-only bundle not changed; final native composition deferred",
        slots=[dict(id="stock-host-app-ns", state="staged", applied=False, sha256=HOST, repeat_sha256=HOST,
            artifact=host, source_commit="77dc6c6251", supersedes="2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e",
            baseline_reproduction="outer-approved semantic A-prime, not byte-identical"),
            dict(id="flutter-private-libandroid", state="staged", applied=False, sha256=flutter["sha256"], artifact=flutter,
                owner="cc-t3", source_commit="8b4769aeeb/8e0d415721", target="/system/android/lib64/westlake_flutter/libandroid.so",
                unchanged="westlake_native/libandroid.so and root libandroid.so"),
            dict(id="native-abi-gecko", state="staged", applied=False, sha256=abi["sha256"], artifact=abi,
                owner="cc-t3", source_commit="8b4769aeeb/8e0d415721", target="/system/android/lib64/westlake_native/libwestlake_native_abi.so",
                unchanged="root and westlake_flutter native_abi d2053066; superseded86882caf must not be selected"),
            dict(id="icu-wall-two", state="staged", applied=False, sha256=icu["sha256"], artifact=icu, new_dependency=shim,
                owner="cc-wiki", source_commit="bf00e19466; persisted release from donor follow-up",
                targets=["/system/android/lib64/libicuuc.so", "/system/android/lib64/libicuuc.z.so"],
                new_target="/system/android/lib64/libicu74compat.so",
                approved_design="option4; exact same bytes for both existing aliases; new shim admission, closure and single-owner gates still required")])
    check_slots(slots)
    save("native-slot-inputs.json", slots)
    print("U14 inputs: 9 effective BCP JARs, exactly 1 stubs swap; runtime0349 outside BCP")
    print("Images: 27 rebake rows, 3 expected-change / 16 may-change / 8 expected-same; 0 output hashes invented")
    print("Machine: hw248 historical FZ-005; remote current SHA PENDING; local05252808 is NOT frozen14b1")
    print("Native slots staged: host341c / Flutterfff9 / Gecko7605 / ICU9b36+4886; old bridge-only90de unchanged")
    print("BAKE NOT_RUN; execution_enabled=false; no VM, board, compiler or registry operations")


if __name__ == "__main__":
    main()
