import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys

from validation import ADDED, BASES, DEX2OAT, DRIVER, HOME_ID, IMAGE_NAMES, JARS, OLD_RUNTIME_JAR, REMOTE_ROOT, RUNTIME_JAR, STUBS, check_plan

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = Path(os.environ.get("WORKSPACES", REPO.parent))
MASTER = WS / "westlake-harness"
PRIVATE = HERE / ".artifacts/inputs"
sys.path.insert(0, str(MASTER / "scripts/lab"))
import generation_bundle as gb


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def portable(value):
    if isinstance(value, dict):
        return {key: portable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [portable(item) for item in value]
    if isinstance(value, Path):
        value = str(value)
    if isinstance(value, str):
        value = value.replace(str(WS) + "/", "$WORKSPACES/")
        value = value.replace(str(Path.home()) + "/", "$HOME/")
        value = re.sub(r"/home/[A-Za-z0-9._-]+/", "$HW248_HOME/", value)
    return value


def save(name, value):
    destination = HERE / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(portable(value), indent=2, ensure_ascii=False) + "\n")


def stage(source, destination, expected):
    if sha(source) != expected:
        raise ValueError("Source identity drift: " + str(source))
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and sha(destination) != expected:
        raise ValueError("Existing private snapshot drift")
    if not destination.exists():
        shutil.copyfile(source, destination)
    if sha(destination) != expected:
        raise ValueError("Copied input drift")
    return dict(source=source, snapshot=destination, sha256=expected, bytes=destination.stat().st_size)


def main():
    parser = argparse.ArgumentParser()
    for variant in BASES:
        default = WS / "westlake-harness-bms/benchmark/2026-10-03-u15-on-u14-base/.artifacts" / (variant + "-20261003T101943")
        parser.add_argument("--" + variant + "-content-base", type=Path, default=default)
    args = parser.parse_args()
    bases, data, sources = {}, {}, []
    def snapshot(source, relative):
        destination = HERE / "inputs/source" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(portable(source.read_text(errors="backslashreplace")))
        sources.append(dict(source=source, source_sha256=sha(source), snapshot=str(destination.relative_to(HERE)), snapshot_sha256=sha(destination), transformation="portable paths only; no source edits"))
    for variant, expected in BASES.items():
        root = getattr(args, variant + "_content_base")
        if sha(root / "bundle.json") != expected:
            raise ValueError("Exact U15 content base required")
        bundle, manifest, effective = gb.validate(root)
        jars = gb.bcp_members(root, bundle, manifest)
        receipt_path = gb.member(root, bundle["paired_build_receipt"])
        receipt = json.loads(receipt_path.read_text())
        if receipt["input_jars"] != {name + ".jar": sha(path) for name, path in jars.items()}:
            raise ValueError("U15 effective BCP differs from actual paired receipt")
        installers = {target: effective[target] for target in ["/system/lib64/libinstalls.z.so", "/system/lib64/platformsdk/libinstalls.z.so"]}
        bases[variant] = dict(path=root, sha256=expected, native_manifest_sha256=sha(root / "native/package.json"), installers=installers, promotion_confirmed=False)
        data[variant] = root, bundle, manifest, jars, effective
        for name, path in [("bundle.json", root / "bundle.json"), ("paired-receipt.json", receipt_path)]:
            snapshot(path, "u15-" + variant + "/" + name)
    if data["common"][2]["live_hashes"] != data["61b"][2]["live_hashes"]:
        raise ValueError("U15 native content differs between board profiles")
    if {name: sha(path) for name, path in data["common"][3].items()} != {name: sha(path) for name, path in data["61b"][3].items()}:
        raise ValueError("U15 BCP differs between board profiles")
    root, bundle, manifest, jars, _ = data["common"]
    donor_root = WS / "westlake-harness-t4/benchmark"
    stubs_root = donor_root / "2026-10-03-u16-t1-wifimanager"
    runtime_root = donor_root / "2026-10-03-u16-t3-build"
    rows = []
    for name in JARS:
        source = stubs_root / "adapter-mainline-stubs-u16t1.jar" if name == "adapter-mainline-stubs" else jars[name]
        row = stage(source, PRIVATE / "jars9" / (name + ".jar"), STUBS if name == "adapter-mainline-stubs" else sha(jars[name]))
        row.update(name=name + ".jar", u15_source=jars[name], u15_sha256=sha(jars[name]), target=gb.FW + name + ".jar")
        rows.append(row)
    runtime = stage(runtime_root / "oh-adapter-runtime-u16-t3.jar", PRIVATE / "runtime/oh-adapter-runtime.jar", RUNTIME_JAR)
    old_runtime = gb.member(root, bundle["runtime_jar"])
    runtime.update(in_bcp=False, u15_source=old_runtime, u15_sha256=sha(old_runtime), target=bundle["runtime_jar"]["target"])
    if runtime["u15_sha256"] != OLD_RUNTIME_JAR:
        raise ValueError("Unexpected U15 runtime JAR")
    images = []
    for member in bundle["boot_group"]["members"]:
        name = Path(member["target"]).name
        if name not in IMAGE_NAMES:
            continue
        if name.startswith("boot-adapter-mainline-stubs."):
            forecast = "expected-change: changed stubs DEX segment"
        elif name.endswith(".vdex"):
            forecast = "expected-same: unchanged DEX segment; actual verification pending"
        else:
            forecast = "may-change: cross-segment layout or embedded work paths"
        images.append(dict(name=name, target=member["target"], u15_sha256=member["sha256"], candidate_sha256=None, rebake=True, prediction=forecast))
    images.sort(key=lambda row: row["name"])
    frozen_plan = json.loads((MASTER / "benchmark/2026-10-03-u15-bcp-v2/plan.json").read_text())
    tools = frozen_plan["frozen_tools"]
    plan = dict(schema="u16-disabled-assembly-preparation/v1", execution_enabled=False, rollout_ready=False, bake_executed=False,
        promotion_confirmed=False, final_bundle_sha256=None, content_bases=bases, transaction_base={"common": None, "61b": None},
        bcp=rows, changed_bcp=["adapter-mainline-stubs.jar"], runtime_jar=runtime, image_count=27, actual_changed_image_count=None,
        frozen_tools=tools, machine=dict(selected="hw248", hostname="ecs-9f6c", home="$HW248_HOME", home_identity_sha256=HOME_ID,
            home_source="$WORKSPACES/westlake-harness/knowledge/frozen/frozen.json#FZ-005", remote_root=REMOTE_ROOT,
            current_remote_verified=False, a2hlab_use=False), pair=dict(status="NOT_RUN", same_work_path=True, selected_run=None,
            exception_approved=False, historical_exception_transfer=False))
    slots = dict(execution_enabled=False, rollout_ready=False, final_native_manifest_sha256=None,
        inherited_native=bases["common"]["native_manifest_sha256"], slots=[
            dict(id="t4-m1-split-runtime", state="pending", sha256=None, applied=False, owner="oc-t4", target="/system/android/lib64/liboh_android_runtime.so"),
            dict(id="flutter-impeller-extension-proc", state="pending", sha256=None, applied=False, owner="cc-t3", target="pending diagnosed owner")],
        excluded=["t2-icon-raster"], dependency_blocked=["t5-webview-A0"])
    check_plan(plan, images, slots)
    save("plan.json", plan)
    save("native-slots.json", slots)
    save("expected-images.json", images)
    with (HERE / "expected-images.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(images[0]))
        writer.writeheader()
        writer.writerows(images)
    argv = [tools["dex2oat64"]["path"], "--android-root=/system", "--instruction-set=arm64", "--base=0x70000000", "--compiler-filter=speed",
        "--runtime-arg", "-Xms64m", "--runtime-arg", "-Xmx512m", "--runtime-arg", "-Xverify:none",
        "--image=" + REMOTE_ROOT + "/work/products/arm64/boot.art", "--oat-file=" + REMOTE_ROOT + "/work/products/arm64/boot.oat"]
    for row in rows:
        argv += ["--dex-file=" + REMOTE_ROOT + "/work/incoming/" + row["name"], "--dex-location=" + row["target"]]
    save("planned-argv.json", dict(status="PLANNED_NOT_EXECUTED", run1=argv, run2=argv, actual_argv_sha256=None))
    template = dict(status="NOT_RUN", input_jars={row["name"]: row["sha256"] for row in rows}, outputs={row["name"]: None for row in images},
        actual_argv=None, argv_sha256=None, dex2oat_sha256=DEX2OAT, driver_sha256=DRIVER, toolchain_identity_sha256=None,
        hostlibs_sha256=None, build_log_sha256=None, session_log_sha256=None, dex2oat_exit_code=None, tee_exit_code=None,
        session_tee_exit_code=None, script_exit_code=None, frozen_driver_exit_code=None, exception_used=False, u16_outer_exception_approval=None)
    save("paired-receipt.template.json", dict(schema="u16-paired-build-template/v1", status="NOT_RUN", selected_run=None, same_work_path=True,
        execution_enabled=False, rollout_ready=False, runs=[dict(run=number, **template) for number in [1, 2]], comparison=None, deploy_allowed=False))
    for name, content in [("jars9.sha256", "".join(row["sha256"] + "  " + row["name"] + "\n" for row in rows)),
        ("t5-ref-u16.sha256", "".join(row["sha256"] + "  " + row["name"] + "\n" for row in rows) + "".join(row["u15_sha256"] + "  arm64/" + row["name"] + "\n" for row in images))]:
        (HERE / "inputs" / name).write_text(content)
    recipe = MASTER / "benchmark/2026-10-03-u15-bcp-v2"
    for name in ["hostlibs.expected.sha256", "FZ-005.json"]:
        source = recipe / "inputs" / name
        shutil.copyfile(source, HERE / "inputs" / name)
        snapshot(source, "u15-recipe/" + name)
    for source_root, names, prefix in [(stubs_root, ["README.md", "build-deterministic.sh", "class-diff.txt", "members.tsv", "adapter-mainline-stubs-u16t1.jar.receipt.json"], "t1"),
        (runtime_root, ["README.md", "build.sh", "class-diff.txt"], "t3"),
        (recipe, ["planned-bake.sh", "dex2oat-tee.sh", "planned-argv.json", "plan.json"], "u15-recipe")]:
        for name in names:
            snapshot(source_root / name, prefix + "/" + name + (".txt" if name.endswith(".sh") else ""))
    for name in ["planned-bake.sh", "dex2oat-tee.sh"]:
        expected = (recipe / name).read_text().replace("U15", "U16").replace("u15", "u16").replace("bitmap-nsd-9e55-94a9-v1", "stubs-8593-runtime-f6f5-v1")
        if (HERE / name).read_text() != expected:
            raise ValueError("Recipe differs beyond U16 labels/root: " + name)
    save("source-snapshots.json", sources)
    donor_receipt = json.loads((stubs_root / "adapter-mainline-stubs-u16t1.jar.receipt.json").read_text())
    save("donor-receipt-status.json", dict(artifact_sha256=STUBS, receipt_output_sha256=donor_receipt.get("out_jar_sha256"),
        receipt_matches_current_artifact=donor_receipt.get("out_jar_sha256") == STUBS,
        state="current deterministic artifact verified; historical merge receipt is not current artifact build proof",
        correction_owner="oc-t4/outer", replacement_receipt=None, blocks_final_provenance_claim=True))
    save("input-inventory.json", dict(root=PRIVATE, files=[dict(path=str(path.relative_to(PRIVATE)), sha256=sha(path), bytes=path.stat().st_size)
        for path in sorted(PRIVATE.rglob("*")) if path.is_file()], binary_landing=False, bcp_count=9, runtime_jar_in_bcp=False))
    save("allow-add.pending.json", dict(execution_enabled=False, rollout_ready=False, approved=False,
        candidate_sha256=STUBS, deployed_sha256=rows[6]["u15_sha256"], descriptors=ADDED, approval_owner="outer(claude)", source_commit="357808ce3f"))
    save("transaction-base.template.json", dict(execution_enabled=False, rollout_ready=False, promotion_confirmed=False,
        parameters=["--common-base", "--common-base-sha256", "--61b-base", "--61b-base-sha256"],
        profiles={variant: dict(content_base_sha256=BASES[variant], transaction_base=dict(path=None, sha256=None, signed_identity=None, expected=None),
            required_state="U15 actually promoted armed per-board package; not the content candidate", installers=bases[variant]["installers"]) for variant in BASES}))
    save("preservation.json", dict(content_bases={variant: dict(before=BASES[variant], after=sha(data[variant][0] / "bundle.json")) for variant in BASES},
        donor_after={"stubs": sha(stubs_root / "adapter-mainline-stubs-u16t1.jar"), "runtime_jar": sha(runtime_root / "oh-adapter-runtime-u16-t3.jar")},
        board_access=False, vm_access=False, bake_executed=False, native_rebuilt=False, gate_registry_updated=False))
    print("U16 DRAFT INPUTS: U15 bases pinned; BCP9 with1 stubs swap; runtime JAR outside BCP;27 images NOT_RUN;2 native slots pending")


if __name__ == "__main__":
    main()
