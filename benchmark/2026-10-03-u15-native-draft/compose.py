import copy
import json
import platform
import shutil
import subprocess

from common import BASE, DONOR, HERE, LOCAL, MASTER, PARTIAL, RELEASE, portable, save, sha
from validation import ANL, BASES, CHANGES, HOST, HOST_SOURCE, RUNTIME, check_partial, check_routes
import generation_bundle


def install(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.chmod(target.stat().st_mode | 0o200)
    shutil.copyfile(source, target)


def main():
    if platform.system() != "Darwin" or PARTIAL.exists():
        raise ValueError("Mac-only task requires a new immutable staging directory")
    originals = {}
    for label, root in [("common", BASE), ("61b", LOCAL)]:
        if sha(root / "bundle.json") != BASES[label]:
            raise ValueError("Accepted U14 content base changed")
        bundle, manifest, effective = generation_bundle.validate(root)
        originals[label] = dict(bundle_sha256=BASES[label], manifest_sha256=sha(root / "native/package.json"),
            installer_identity={target: effective[target] for target in ["/system/lib64/libinstalls.z.so", "/system/lib64/platformsdk/libinstalls.z.so"]},
            promotion_confirmed=False)
    domain = RELEASE / "u15-jitsi-native-domain-v1"
    runtime = RELEASE / "u15-runtime-m3-v1"
    selected = {
        "payload/android/lib64/liboh_android_runtime.so": runtime / "payload/android/lib64/liboh_android_runtime.so",
        "payload/runtime/appspawn-x": domain / "payload/host/appspawn-x",
        "payload/android/lib64/libapp_native_loader.so": domain / "payload/android/lib64/libapp_native_loader.so",
        "payload/route/libapp_native_loader.so": domain / "payload/android/lib64/libapp_native_loader.so",
    }
    repeats = [(runtime / "builds/rt-m3-a.so", RUNTIME), (runtime / "builds/rt-m3-b.so", RUNTIME),
        (domain / "builds/appspawn-x-u15jitsi-1", HOST), (domain / "builds/appspawn-x-u15jitsi-2", HOST),
        (domain / "builds/anl-jitsi-a.so", ANL), (domain / "builds/anl-jitsi-b.so", ANL)]
    for source, digest in repeats + [(source, CHANGES[member]) for member, source in selected.items()]:
        if sha(source) != digest:
            raise ValueError("Persistent donor or double-build mismatch")
    host_source = domain / "u15jitsi-stock-host.c"
    if sha(host_source) != HOST_SOURCE:
        raise ValueError("Final patched host source does not match the release receipt")
    packages = check_routes((DONOR / "src/anl/app_native_loader.c").read_text(), host_source.read_text())
    PARTIAL.mkdir(parents=True)
    subprocess.run(["/bin/cp", "-cR", BASE / "native", PARTIAL / "native"], check=True)
    old_manifest = json.loads((BASE / "native/package.json").read_text())
    manifest = copy.deepcopy(old_manifest)
    for member, source in selected.items():
        install(source, PARTIAL / "native" / member)
        manifest["files"][member] = CHANGES[member]
    for target, digest in manifest["live_hashes"].items():
        if target.endswith("/libapp_native_loader.so"):
            manifest["live_hashes"][target] = ANL
        elif target == "/system/android/lib64/liboh_android_runtime.so":
            manifest["live_hashes"][target] = RUNTIME
        elif target == "/system/bin/appspawn-x":
            manifest["live_hashes"][target] = HOST
    manifest.update(variant="U15 native-only offline draft; NSD stubs and all 27 images pending", rollout_ready=False,
        rollout_blocker="No bundle descriptor or new paired images; transaction base unbound")
    save(PARTIAL / "native/package.json", manifest)
    checks = PARTIAL / "native/native-checks"
    scan = json.loads((checks / "scan-manifest.json").read_text())
    replacements = {"egl.cpp": runtime / "oh_egl_impl.cpp", "n4-host.c": host_source,
        "u10-1-resident-compat.h": DONOR / "inputs/resident-compat.h", "u12-zlib-route.h": DONOR / "inputs/zlib-route.h",
        "u15-app-native-loader.c": DONOR / "src/anl/app_native_loader.c", "flutter_domain.inc": DONOR / "src/anl/flutter_domain.inc"}
    receipts = []
    for name, source in replacements.items():
        install(source, checks / name)
        scan["sources"][name] = dict(path=name, sha256=sha(source), source_sha256=sha(source), origin=portable(source), first_line=1)
        proof = HERE / "inputs/source" / name
        proof.parent.mkdir(parents=True, exist_ok=True)
        proof.write_text(portable(source.read_text()))
        receipts.append(dict(source=source, source_sha256=sha(source), snapshot=str(proof.relative_to(HERE)), snapshot_sha256=sha(proof)))
    scan["profiles"].append(dict(name="u15-app-native-loader", rule="namespace", source="u15-app-native-loader.c",
        identity=dict(artifact="payload/route/libapp_native_loader.so")))
    for profile in scan["profiles"]:
        identity = profile["identity"]
        identity.update(package="u15-native-only-offline-staging", manifest_sha256=sha(PARTIAL / "native/package.json"), artifact_sha256=manifest["files"][identity["artifact"]])
    save(checks / "scan-manifest.json", scan)
    namespaces = json.loads((checks / "namespace-manifest.json").read_text())
    for row in namespaces["config_sources"]:
        if row["path"] == "flutter_domain.inc":
            row["sha256"] = sha(checks / "flutter_domain.inc")
    save(checks / "namespace-manifest.json", namespaces)
    inputs = json.loads((checks / "native-gates.json").read_text())
    inputs["package_manifest_sha256"] = sha(PARTIAL / "native/package.json")
    inputs["initialization"]["manifest"]["sha256"] = sha(checks / "scan-manifest.json")
    inputs["namespaces"]["manifest"]["sha256"] = sha(checks / "namespace-manifest.json")
    inputs["namespaces"]["owner_artifact"]["sha256"] = ANL
    save(checks / "native-gates.json", inputs)
    sources = [(DONOR / relative, "jitsi/" + relative) for relative in ["README.md", "results.json", "build_anl_hw248.sh", "recipe/build_u15j_host.py",
        "src/anl/app_native_loader-vs-n3.diff", "src/host-u15-vs-jitsi.diff", "evidence/gates.txt", "evidence/replay-fd-meet-native.txt"]]
    sources += [(MASTER / "benchmark/2026-10-03-u15-host-mindustry" / relative, "mindustry/" + relative) for relative in
        ["results.json", "recipe/build_u15_host.py", "recipe/win-u15-mindustry-audio.patch"]]
    sources += [(MASTER / "benchmark/2026-10-03-u15-runtime-m3" / relative, "runtime-m3/" + relative) for relative in
        ["results.json", "build_m3_hw248.sh", "src/oh_egl_impl-vs-n4.diff"]]
    for source, relative in sources:
        proof = HERE / "inputs/source" / relative
        proof.parent.mkdir(parents=True, exist_ok=True)
        proof.write_text(portable(source.read_text()))
        receipts.append(dict(source=source, source_sha256=sha(source), snapshot=str(proof.relative_to(HERE)), snapshot_sha256=sha(proof)))
    save("source-snapshots.json", receipts)
    save("donor-receipt.json", dict(donors=[dict(source=source, sha256=digest) for source, digest in repeats],
        builds_run_by_this_lane=False, toolchain_records="source snapshots + persistent donor release logs/objects/SHA256SUMS", identical_builds_per_object=2))
    save("route-lists.json", dict(anl_packages=packages, host_packages=packages, meet_needs_runtime=True,
        namespace="westlake_native", predicted_first_fatal_keys=["fd-meet"], observed_moves=0,
        scope_limit="matching lists do not prove live relocation, resident owner uniqueness or screenshots"))
    state = dict(schema="u15-native-only-draft/v1", partial=PARTIAL, content_bases=originals, comparison_base=BASE,
        transaction_base={"common": None, "61b": None}, native_manifest_sha256=sha(PARTIAL / "native/package.json"),
        native_inputs_sha256=sha(checks / "native-gates.json"), changes=CHANGES, added={}, removed=[],
        images="pending framework+NSD single rebake", paired_receipt=None, final_bundle_sha256=None,
        execution_enabled=False, final_batch_complete=False, deploy_allowed=False, promotion_confirmed=False,
        bcp_changes_applied=False, retained_bcp="U14 effective framework3e106/stubs87cf; native inventory only",
        runtime_jar="0349 non-BCP unchanged", framework_candidate="9e55 staged in u15-plan, not installed here", nsd_stubs_candidate_sha256=None)
    check_partial(old_manifest["files"], manifest["files"], state, (PARTIAL / "bundle.json").exists())
    for member, digest in manifest["files"].items():
        if sha(PARTIAL / "native" / member) != digest:
            raise ValueError("Composed native payload hash mismatch")
    save("composition.json", state)
    for name, source in [("old-native-manifest.json", BASE / "native/package.json"), ("native-manifest.json", PARTIAL / "native/package.json"),
        ("native-inputs.json", checks / "native-gates.json"), ("scan-manifest.json", checks / "scan-manifest.json")]:
        save("manifests/" + name, json.loads(source.read_text()))
    print("U15 NATIVE STAGING: objects=3 changed_paths=4 no additions/deletions; ANL aliases+host atomic; BCP unchanged; no bundle descriptor")
    print("manifest=" + state["native_manifest_sha256"] + " inputs=" + state["native_inputs_sha256"])


if __name__ == "__main__":
    main()
