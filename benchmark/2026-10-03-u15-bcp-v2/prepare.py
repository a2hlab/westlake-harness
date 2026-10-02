import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys

from validation import BASES, DEX2OAT, DRIVER, FRAMEWORK, STUBS, FLUTTER, HOME_ID, IMAGE_NAMES, INSTALLERS, INSTALLER_PATHS, JARS, OLD_RUNTIME, RUNTIME, RUNTIME_JAR, check_plan, check_slots


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = Path(os.environ.get("WORKSPACES", REPO.parent))
MASTER = WS / "westlake-harness"
PRIVATE = HERE / ".artifacts/inputs"
RELEASE = WS / "westlake-inputs/generations"
sys.path.insert(0, str(MASTER / "scripts/lab"))
import generation_bundle


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def portable(value):
    if isinstance(value, dict):
        return {name: portable(item) for name, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [portable(item) for item in value]
    if isinstance(value, Path):
        value = str(value)
    if isinstance(value, str):
        for root, token in [(WS, "$WORKSPACES"), (Path.home(), "$HOME")]:
            value = token if value == str(root) else value.replace(str(root) + "/", token + "/")
        value = re.sub(r"/home/[^/\s'\"]+", "$HW248_HOME", value)
    return value


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(portable(value), indent=2, ensure_ascii=False) + "\n")


def stage(source, destination, expected):
    if sha(source) != expected:
        raise ValueError("Donor SHA mismatch: " + str(source))
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and sha(destination) != expected:
        raise ValueError("Existing snapshot changed: " + str(destination))
    if not destination.exists():
        shutil.copyfile(source, destination)
    if sha(destination) != expected:
        raise ValueError("Staged SHA mismatch: " + str(destination))
    return dict(source=source, snapshot=destination, sha256=sha(destination), bytes=destination.stat().st_size)


def main():
    bases = {}
    data = {}
    for variant, digest in BASES.items():
        root = WS / "westlake-harness-bms/benchmark/2026-10-03-u14-effective-rebind/.artifacts" / (variant + "-reviewed")
        if sha(root / "bundle.json") != digest:
            raise ValueError("Accepted U14 content base changed")
        bundle, manifest, effective = generation_bundle.validate(root)
        jars = generation_bundle.bcp_members(root, bundle, manifest)
        receipt = json.loads(generation_bundle.member(root, bundle["paired_build_receipt"]).read_text())
        if receipt["input_jars"] != {name + ".jar": sha(path) for name, path in jars.items()}:
            raise ValueError("Effective BCP differs from accepted U14 receipt")
        if any(effective.get(target) != INSTALLERS[variant] for target in INSTALLER_PATHS):
            raise ValueError("Board-local U14 installer drift")
        if manifest["live_hashes"]["/system/android/lib64/liboh_android_runtime.so"] != OLD_RUNTIME:
            raise ValueError("Unexpected M3 content baseline")
        bases[variant] = dict(path=root, sha256=digest, native_manifest_sha256=sha(root / "native/package.json"),
            paired_receipt_sha256=sha(generation_bundle.member(root, bundle["paired_build_receipt"])),
            installers={target: effective[target] for target in INSTALLER_PATHS}, promotion_confirmed=False)
        data[variant] = (root, bundle, manifest, jars, effective)
    common, local = data["common"], data["61b"]
    if common[2]["live_hashes"] != local[2]["live_hashes"]:
        raise ValueError("U14 native content differs between profiles")
    if {name: sha(path) for name, path in common[3].items()} != {name: sha(path) for name, path in local[3].items()}:
        raise ValueError("U14 effective BCP differs between profiles")
    if common[1]["boot_group"] != local[1]["boot_group"] or common[1]["runtime_jar"] != local[1]["runtime_jar"]:
        raise ValueError("U14 boot or runtime JAR content differs")
    root, bundle, manifest, jars, _ = common
    rows = []
    for name in JARS:
        donor = RELEASE / "u15-framework-bitmap-v1/framework-u15.jar" if name == "framework" else RELEASE / "u15-stubs-nsd-v1/adapter-mainline-stubs-u15-nsd.jar" if name == "adapter-mainline-stubs" else jars[name]
        digest = FRAMEWORK if name == "framework" else STUBS if name == "adapter-mainline-stubs" else sha(jars[name])
        row = stage(donor, PRIVATE / "jars9" / (name + ".jar"), digest)
        row.update(name=name + ".jar", u14_sha256=sha(jars[name]), target=generation_bundle.FW + name + ".jar")
        rows.append(row)
    runtime_jar = stage(generation_bundle.member(root, bundle["runtime_jar"]), PRIVATE / "runtime/oh-adapter-runtime.jar", RUNTIME_JAR)
    runtime_jar.update(in_bcp=False, changed=False, target=bundle["runtime_jar"]["target"])
    native_release = RELEASE / "u15-runtime-m3-v1"
    runtime = stage(native_release / "payload/android/lib64/liboh_android_runtime.so", PRIVATE / "native/liboh_android_runtime.so", RUNTIME)
    for name in ["builds/rt-m3-a.so", "builds/rt-m3-b.so"]:
        if sha(native_release / name) != RUNTIME:
            raise ValueError("M3 donor double-build identity mismatch")
    images = []
    for member in bundle["boot_group"]["members"]:
        name = Path(member["target"]).name
        if name not in IMAGE_NAMES:
            continue
        generation_bundle.member(root, member)
        if name.startswith(("boot-framework.", "boot-adapter-mainline-stubs.")):
            forecast = "expected-change: modified framework DEX segment; actual comparison pending"
        elif name.endswith(".vdex"):
            forecast = "expected-same: unchanged DEX segment; actual comparison pending"
        else:
            forecast = "may-change: aggregate layout, references, compilation or embedded paths"
        images.append(dict(name=name, target=member["target"], u14_sha256=member["sha256"],
            candidate_sha256=None, rebake=True, prediction=forecast))
    images.sort(key=lambda row: row["name"])
    plan = dict(schema="westlake-u15-dual-bcp-preparation/v2", execution_enabled=False, bake_executed=False,
        deploy_allowed=False, promotion_confirmed=False, content_bases=bases,
        transaction_base={"common": None, "61b": None, "required": ["path", "sha256", "signed_identity", "expected"]},
        bcp=rows, runtime_jar=runtime_jar, changed_bcp=["adapter-mainline-stubs.jar", "framework.jar"], image_count=27,
        actual_changed_image_count=None, candidate_bundle_sha256=None,
        machine=dict(selected="hw248", hostname="ecs-9f6c", home="$HW248_HOME", home_identity_sha256=HOME_ID,
            home_source="$WORKSPACES/westlake-harness/knowledge/frozen/frozen.json#FZ-005",
            current_remote_verified=False, a2hlab_use=False, remote_root="$HW248_HOME/u15-bitmap-nsd-9e55-94a9-v1"),
        frozen_tools=dict(dex2oat64=dict(path="$HW248_HOME/aosp-14.0.0_r1-art/out/host/linux-x86/bin/dex2oat64", sha256=DEX2OAT),
            driver=dict(path="$HW248_HOME/cc-wiki-t5/tool/t5_gen_image.sh", sha256=DRIVER),
            repository_driver=dict(path=MASTER / "knowledge/toolchains/art-r155/t5_gen_image.sh", sha256=sha(MASTER / "knowledge/toolchains/art-r155/t5_gen_image.sh"), usable_as_frozen_driver=False)),
        pair=dict(same_work_path=True, selected_run=None, expected_outputs=27, status="NOT_RUN", exception_approved=False,
            historical_exception="U14 and T7d approvals are historical exact pairs only; new U15 inputs require fresh evidence and review"),
        framework_inventory=dict(target="/system/android/framework/framework.jar", native_underlay="native/payload/android/framework/framework.jar",
            update_both_on_future_composition=True, image_gate_reference="effective U14 36 members, not legacy baseline reference files"))
    partial = REPO / "benchmark/2026-10-03-u15-native-draft/composition.json"
    native_state = json.loads(partial.read_text())
    flutter_report = MASTER / "benchmark/2026-10-03-u15-flutter-libandroid-v2/results.json"
    slots = dict(execution_enabled=False, final_batch_complete=False, candidate_bundle_sha256=None,
        slots=[dict(id="native-partial", state="referenced-not-final", source=partial, source_sha256=sha(partial),
            manifest_sha256=native_state["native_manifest_sha256"], inputs_sha256=native_state["native_inputs_sha256"],
            objects=["runtime94c3", "host9e3a", "ANL b96a dual aliases"], applied=False),
            dict(id="flutter-atrace-v2", state="arrived-uncomposed", sha256=FLUTTER, applied=False,
                source_commit="3154a2d29c", receipt=flutter_report, receipt_sha256=sha(flutter_report),
                target="/system/android/lib64/westlake_flutter/libandroid.so",
                rule="fff9 plus three ATrace exports; compose into native v2, not this BCP plan")])
    check_plan(plan, images)
    check_slots(slots)
    save("plan.json", plan)
    save("native-slots.json", slots)
    save("expected-images.json", images)
    with (HERE / "expected-images.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(images[0]))
        writer.writeheader()
        writer.writerows(images)
    template = dict(status="NOT_RUN", input_jars={row["name"]: row["sha256"] for row in rows}, outputs={row["name"]: None for row in images},
        actual_argv=None, argv_sha256=None, dex2oat_sha256=DEX2OAT, driver_sha256=DRIVER, toolchain_identity_sha256=None,
        hostlibs_sha256=None, build_log_sha256=None, session_log_sha256=None, dex2oat_exit_code=None, tee_exit_code=None,
        session_tee_exit_code=None, script_exit_code=None, frozen_driver_exit_code=None, exception_used=False, u15_outer_exception_approval=None)
    save("paired-receipt.template.json", dict(schema="u15-paired-build-template/v1", status="NOT_RUN", selected_run=None,
        same_work_path=True, runs=[dict(run=number, **template) for number in [1, 2]], comparison=None, deploy_allowed=False))
    (HERE / "inputs").mkdir(exist_ok=True)
    (HERE / "inputs/jars9.sha256").write_text("".join(row["sha256"] + "  " + row["name"] + "\n" for row in rows))
    (HERE / "inputs/t5-ref-u15.sha256").write_text("".join(row["sha256"] + "  " + row["name"] + "\n" for row in rows) +
        "".join(row["u14_sha256"] + "  arm64/" + row["name"] + "\n" for row in images))
    old_logs = RELEASE / "u14-bt-bake-0349-87cf-v1/logs"
    if sha(old_logs / "hostlibs-run1.sha256") != sha(old_logs / "hostlibs-run2.sha256"):
        raise ValueError("Historical frozen hostlibs differed")
    hostlibs = []
    for line in (old_logs / "hostlibs-run1.sha256").read_text().splitlines():
        digest, path = line.split(None, 1)
        relative = path.split("/out/host/linux-x86/lib64/", 1)[1]
        if Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise ValueError("Unsafe historical hostlib path")
        hostlibs.append((relative, digest))
    (HERE / "inputs/hostlibs.expected.sha256").write_text("".join(digest + "  " + name + "\n" for name, digest in sorted(hostlibs)))
    save("inputs/hostlibs-provenance.json", dict(source=old_logs / "hostlibs-run1.sha256", sha256=sha(old_logs / "hostlibs-run1.sha256"),
        count=len(hostlibs), current_remote_verified=False, rule="fresh remote inventory must match before each compiler run"))
    save("inputs/u14-paired-receipt.json", json.loads(generation_bundle.member(root, bundle["paired_build_receipt"]).read_text()))
    frozen = json.loads((MASTER / "knowledge/frozen/frozen.json").read_text())
    save("inputs/FZ-005.json", next(row for row in frozen["entries"] if row["id"] == "FZ-005"))
    sources = []
    files = [(MASTER / "benchmark/2026-10-03-u15-runtime-m3" / name, "runtime-m3/" + name) for name in
        ["README.md", "results.json", "build_m3_hw248.sh", "src/oh_egl_impl-vs-n4.diff"]]
    files.extend((MASTER / "benchmark/2026-10-03-u15-framework-bitmap" / name, "framework-bitmap/" + name) for name in
        ["README.md", "results.json", "recipe/Bitmap.getColorSpace.smali.patch", "evidence/hw248-rebake-and-native-boundary.txt"])
    files.extend((RELEASE / "u14-bt-bake-0349-87cf-v1/plan" / name, "u14-actual-recipe/" + name) for name in ["planned-bake.sh", "dex2oat-tee.sh"])
    files.extend((source, name) for source, name in [(RELEASE / "u15-framework-bitmap-v1/build-commands.txt", "framework-bitmap/build-commands.txt"),
        (RELEASE / "u15-runtime-m3-v1/logs/m3-a.log", "runtime-m3/build-a.log"), (RELEASE / "u15-runtime-m3-v1/logs/m3-b.log", "runtime-m3/build-b.log")])
    files.extend((MASTER / "benchmark/2026-10-03-u15-stubs-nsd" / name, "stubs-nsd/" + name) for name in
        ["README.md", "results.json", "build_stubs_nsd.py", "stubs/members.tsv", "evidence/host-art-runs.txt"])
    files.extend((RELEASE / "u15-stubs-nsd-v1" / name, "stubs-nsd/release/" + name) for name in
        ["SHA256SUMS", "logs/build-stubs-nsd.log", "logs/class-diff-vs-87cf65cc.txt", "logs/stubs-merge-report.json"])
    files.extend([(flutter_report, "flutter-atrace-v2/results.json"), (partial, "native-partial/composition.json")])
    for line in (RELEASE / "u15-stubs-nsd-v1/SHA256SUMS").read_text().splitlines():
        digest, relative = line.split(None, 1)
        source = RELEASE / "u15-stubs-nsd-v1" / relative
        if sha(source) != digest:
            raise ValueError("NSD release inventory hash mismatch")
    for source, relative in files:
        destination = HERE / "inputs/source" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(portable(source.read_text()))
        sources.append(dict(source=source, source_sha256=sha(source), snapshot=str(destination.relative_to(HERE)),
            snapshot_sha256=sha(destination), transformation="portable home paths; historical donor evidence, not a U15 bake"))
    save("source-snapshots.json", sources)
    save("input-snapshot-receipt.json", dict(status="verified-local-inputs-only", bcp=rows, runtime_jar=runtime_jar,
        native_runtime=runtime, binaries_in_landing=False, donor_build_executed_by_this_lane=False, jars_changed=2,
        native_slots_selected=0, pending_slots=1, image_bake_executed=False))
    save("preservation.json", dict(content_bases=bases, after={key: sha(row["path"] / "bundle.json") for key, row in bases.items()},
        native_changed=False, jars_changed=False, images_changed=False, registries_changed=False))
    print("U15 INPUTS PASS: effective BCP 9/9 pinned, Bitmap+NSD 2 swaps; 27 outputs unknown; Flutter arrived, uncomposed; no bake/VM/board")


if __name__ == "__main__":
    main()
