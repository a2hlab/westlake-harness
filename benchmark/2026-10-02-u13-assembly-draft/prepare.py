"""Compose the three reviewed donors on the exact U12 base, without device or registry writes."""
import copy
import json
import shutil

from common import BASE, BASE_BUNDLE, BASE_MANIFEST, COMPAT, HERE, HOST, LANE, MASTER, PACKAGE, POLICY, REPO, RUNTIME, WORKSPACES, assert_disabled, portable, save, sha
import generation_bundle as gb
import generation_static_checks as static
import u7_executor as executor


def main():
    if sha(BASE / "bundle.json") != BASE_BUNDLE or sha(BASE / "native/package.json") != BASE_MANIFEST:
        raise ValueError("U12 base drift; do not substitute a rollout-marker variant or T8")
    if PACKAGE.exists():
        raise ValueError("fresh output required")
    data, original, _ = gb.validate(BASE)
    runtime_root = WORKSPACES / "westlake-inputs/generations/u13-runtime-m1-v1"
    vlc = LANE / "benchmark/2026-10-02-u12-vlc-bionic-residue"
    single = LANE / "benchmark/2026-10-02-u13-single-native"
    donors = {
        "runtime": (runtime_root / "liboh_android_runtime-u13-18763dd4.so", RUNTIME, ["payload/android/lib64/liboh_android_runtime.so"]),
        "compat": (vlc / ".artifacts/candidate1.so", COMPAT, ["payload/android/lib64/libbionic_compat.so", "payload/route/libbionic_compat.so"]),
        "policy": (single / ".artifacts/policy/candidate1/libnativeloader-candidate.so", POLICY, ["payload/android/lib64/libnativeloader.so", "payload/route/libnativeloader.so"])}
    for name, (source, digest, _) in donors.items():
        if sha(source) != digest:
            raise ValueError("donor drift: " + name)
    shutil.copytree(BASE, PACKAGE)
    native = PACKAGE / "native"
    manifest = copy.deepcopy(original)
    for _, (source, digest, members) in donors.items():
        for member in members:
            target = native / member
            target.chmod(target.stat().st_mode | 0o200)
            shutil.copyfile(source, target)
            manifest["files"][member] = digest
    for target in manifest["live_hashes"]:
        member = executor.native.replacement_source(manifest, target) if target.endswith(".so") or target == executor.HOST else None
        if member:
            manifest["live_hashes"][target] = manifest["files"][member]
    blocker = "U13 offline draft: U12 Stage A final acceptance, exact native/static review, Mac+VM production preflight and outer window authorization pending"
    manifest.update(variant="U13 draft: runtime18763 + VLCcompatb2be + policyb8be; U12 host retained", rollout_ready=False, rollout_blocker=blocker)
    manifest.pop("window_authorization", None)
    save(native / "package.json", manifest)
    manifest_sha = sha(native / "package.json")
    executor.native.validate_upgrade(original, executor.native.load_package(native))
    checks = native / "native-checks"
    scan = json.loads((checks / "scan-manifest.json").read_text())
    runtime_sources = MASTER / "benchmark/2026-10-02-m1-session-slots/runtime"
    overlays = [
        ("u10-1-native-policy.h", single / "sources/candidate/policy/include/nativeloader/native_bridge_policy.h", "payload/route/libnativeloader.so", None),
        ("u13-system-loader.cpp", single / "sources/candidate/policy/src/system_loader.cpp", "payload/route/libnativeloader.so", "namespace"),
        ("u13-m1-compat-shim.cpp", runtime_sources / "src/android_graphics_compat_shim.cpp", "payload/android/lib64/liboh_android_runtime.so", "namespace"),
        ("u13-asset-manager.cpp", runtime_root / "build/src-asset-manager/frameworks/base/native/android/asset_manager.cpp", "payload/android/lib64/liboh_android_runtime.so", "namespace"),
        ("u13-vlc-bionic-residue.c", vlc / "vlc_bionic_residue.c", "payload/android/lib64/libbionic_compat.so", "namespace")]
    source_bindings = []
    for name, source, artifact, rule in overlays:
        shutil.copyfile(source, checks / name)
        scan["sources"][name] = dict(path=name, sha256=sha(source), source_sha256=sha(source), origin=portable(source), first_line=1)
        if rule:
            scan["profiles"].append(dict(name=name, rule=rule, source=name, identity=dict(artifact=artifact)))
        source_bindings.append(dict(source=source, sha256=sha(source), artifact=artifact, artifact_sha256=manifest["files"][artifact]))
    for profile in scan["profiles"]:
        artifact = profile["identity"]["artifact"]
        profile["identity"].update(package="u13-offline-draft", manifest_sha256=manifest_sha, artifact_sha256=manifest["files"][artifact])
    save(checks / "scan-manifest.json", scan)
    gates = json.loads((checks / "native-gates.json").read_text())
    gates["package_manifest_sha256"] = manifest_sha
    gates["initialization"]["manifest"]["sha256"] = sha(checks / "scan-manifest.json")
    save(checks / "native-gates.json", gates)
    policy = dict(jars={}, native={})
    save(PACKAGE / "static-policy-u13-draft.json", policy)
    data["native"]["manifest"]["sha256"] = manifest_sha
    data["static_checks"] = dict(baseline_bundle_sha256=BASE_BUNDLE, policy=dict(source="static-policy-u13-draft.json", sha256=sha(PACKAGE / "static-policy-u13-draft.json")))
    data.update(rollout_ready=False, rollout_blocker=blocker)
    data.pop("window_authorization", None)
    assert_disabled(data, manifest)
    save(PACKAGE / "bundle.json", data)
    gb.validate(PACKAGE)
    plan = executor.prepare(PACKAGE, BASE / "native")
    before, after = static.effective(BASE), static.effective(PACKAGE)
    changes = {target: dict(before=before.get(target, {}).get("sha256"), after=row["sha256"]) for target, row in after.items() if before.get(target, {}).get("sha256") != row["sha256"]}
    if len(changes) != 5 or any(row["before"] is None for row in changes.values()):
        raise ValueError("expected precisely five existing targets, no new member")
    prior = json.loads((MASTER / "benchmark/2026-10-02-u12-final-assembly/composition.json").read_text())
    boards = copy.deepcopy(prior["candidate_boards"])
    for board in boards.values():
        for target, row in changes.items():
            board["expected"][target] = row["after"]
        board["fingerprints"] = executor.fingerprints(board["expected"], board["reference_paths"])
    receipts = [runtime_sources / "runtime-build-receipt-u13.json", vlc / "build-receipt.json", single / "policy-build-receipt.json"]
    provenance = dict(donors={name: dict(source=source, sha256=digest, targets=members) for name, (source, digest, members) in donors.items()}, receipts=[dict(path=path, sha256=sha(path)) for path in receipts], source_bindings=source_bindings, inherited_receipts_scope="U12 unchanged artifacts only; U13 donor receipts supersede inherited runtime/compat/policy claims", runtime_build_logs=[dict(path=path, sha256=sha(path)) for path in [runtime_root / "logs/build-session.log", runtime_root / "build/u13/build.log", runtime_root / "build/u13-repeat/build.log"]])
    save("donor-provenance.json", provenance)
    save("composition.json", dict(state="U13_OFFLINE_DRAFT_DISABLED", package=PACKAGE, base_bundle=BASE, base_bundle_sha256=BASE_BUNDLE, base_native_manifest_sha256=BASE_MANIFEST, bundle_sha256=sha(PACKAGE / "bundle.json"), native_manifest_sha256=manifest_sha, execution_enabled=False, rollout_ready=False, host_sha256=HOST, held_host_sha256="c28833762f845c89e7cadf0e8a49b431259959c2e21b2b80b381de177443bdd3", board_changes=changes, new_native_paths=[], candidate_boards=boards, boot_and_jars_unchanged=True, condition="Use U12 only if Stage A has no confirmed regression; a confirmed regression requires outer redesign, not automatic T8 substitution", pending=["U12 final Stage A acceptance", "native/static exact review", "fresh Mac+VM production dry-run", "outer window authorization"]))
    save("prepare-plan.json", plan)
    save("new-native-admission-draft.json", dict(admissions=[], package_manifest_sha256=manifest_sha, reason="All five changed targets already exist in U12; no new native path", execution_enabled=False))
    save("rollback.json", dict(base_bundle=BASE, bundle_sha256=BASE_BUNDLE, native_manifest_sha256=BASE_MANIFEST, restore=changes, atomic_alias_groups=[donors["compat"][2], donors["policy"][2]], unchanged_host=HOST, scope="Complete U12 bundle rollback by cx-t0 only; no execution in this draft"))
    print(json.dumps(dict(bundle_sha256=sha(PACKAGE / "bundle.json"), native_manifest_sha256=manifest_sha, changed_targets=len(changes), host=HOST, execution_enabled=False), indent=2))


if __name__ == "__main__":
    main()
