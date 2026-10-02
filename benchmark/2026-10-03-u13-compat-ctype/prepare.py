import copy
import json
import shutil
import sys

from common import HERE, MASTER, OLD, REPO, WS, save, sha

sys.path.insert(0, str(MASTER / "scripts/lab"))
import generation_bundle as gb
import generation_static_checks as static
import u7_executor as executor

OLD_BUNDLE = "473ba28da411d0dacdffaf2931490b01bd18896e8ce713d259e80c816b7e75cb"
OLD_MANIFEST = "7615b424aad957518fd8884a5b0ee3b404d9a207e7ee495972dbd1fd87893dbc"
HOST = "2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e"
MEMBERS = ["payload/android/lib64/libbionic_compat.so", "payload/route/libbionic_compat.so"]


def main():
    previous = REPO / "benchmark/2026-10-02-u13-assembly-draft"
    old = previous / ".artifacts/bundle"
    if sha(old / "bundle.json") != OLD_BUNDLE or sha(old / "native/package.json") != OLD_MANIFEST:
        raise ValueError("frozen U13 old draft changed")
    bundle, native, _ = gb.validate(old)
    candidate = HERE / ".artifacts/candidate1.so"
    receipt = json.loads((HERE / "build-receipt.json").read_text())
    digest = receipt["repeated"][0]["candidate"]
    if sha(candidate) != digest or receipt["repeated"][0] != receipt["repeated"][1]:
        raise ValueError("candidate not twice identical")
    package = HERE / ".artifacts/bundle-v2"
    if package.exists():
        raise ValueError("new draft output already exists; do not overwrite a freeze")
    shutil.copytree(old, package)
    manifest = copy.deepcopy(native)
    for member in MEMBERS:
        if manifest["files"][member] != OLD:
            raise ValueError("old alias drift")
        target = package / "native" / member
        target.chmod(target.stat().st_mode | 0o200)
        shutil.copyfile(candidate, target)
        manifest["files"][member] = digest
    targets = []
    for target in manifest["live_hashes"]:
        member = executor.native.replacement_source(manifest, target) if target.endswith(".so") or target == executor.HOST else None
        if member in MEMBERS:
            manifest["live_hashes"][target] = digest
            targets.append(target)
    blocker = "U13 compat-v2 offline disabled draft; exact manifest native/static outer approvals and fresh production dry-runs pending"
    manifest.update(variant="U13 compat-v2: b2be657c plus single _ctype_ export; U12 host retained", rollout_ready=False, rollout_blocker=blocker)
    manifest.pop("window_authorization", None)
    save(package / "native/package.json", manifest)
    manifest_sha = sha(package / "native/package.json")
    checks = package / "native/native-checks"
    scan = json.loads((checks / "scan-manifest.json").read_text())
    source_name = "u13-ctype-compat.c"
    shutil.copyfile(HERE / "ctype_compat.c", checks / source_name)
    scan["sources"][source_name] = dict(path=source_name, sha256=sha(HERE / "ctype_compat.c"), source_sha256=sha(HERE / "ctype_compat.c"),
        origin="$REPO/benchmark/2026-10-03-u13-compat-ctype/ctype_compat.c", first_line=1)
    for profile in scan["profiles"]:
        artifact = profile["identity"]["artifact"]
        profile["identity"].update(package="u13-compat-v2-offline-draft", manifest_sha256=manifest_sha,
            artifact_sha256=manifest["files"][artifact])
    save(checks / "scan-manifest.json", scan)
    gates = json.loads((checks / "native-gates.json").read_text())
    gates["package_manifest_sha256"] = manifest_sha
    gates["initialization"]["manifest"]["sha256"] = sha(checks / "scan-manifest.json")
    save(checks / "native-gates.json", gates)
    policy_path = package / "static-policy-u13-draft.json"
    save(policy_path, dict(jars={}, native={}))
    bundle["native"]["manifest"]["sha256"] = manifest_sha
    bundle["static_checks"]["policy"]["sha256"] = sha(policy_path)
    bundle.update(rollout_ready=False, rollout_blocker=blocker)
    bundle.pop("window_authorization", None)
    save(package / "bundle.json", bundle)
    gb.validate(package)
    executor.native.validate_upgrade(native, executor.native.load_package(package / "native"))
    if manifest["files"]["payload/runtime/appspawn-x"] != HOST or len(targets) != 2:
        raise ValueError("host changed or aliases not atomic")
    changed = {name for name in native["files"] if native["files"][name] != manifest["files"][name]}
    if changed != set(MEMBERS):
        raise ValueError("unexpected payload change")
    composition = json.loads((previous / "composition.json").read_text())
    boards = copy.deepcopy(composition["candidate_boards"])
    for board in boards.values():
        for target in targets:
            board["expected"][target] = digest
        board["fingerprints"] = executor.fingerprints(board["expected"], board["reference_paths"])
    save("composition.json", dict(package=package, bundle_sha256=sha(package / "bundle.json"), native_manifest_sha256=manifest_sha,
         native_inputs_sha256=sha(checks / "native-gates.json"), previous_bundle_sha256=OLD_BUNDLE,
         previous_manifest_sha256=OLD_MANIFEST, compat_before=OLD, compat_after=digest, changed_payload_members=sorted(changed),
         changed_targets=targets, host_sha256=HOST, held_host_sha256="c28833762f845c89e7cadf0e8a49b431259959c2e21b2b80b381de177443bdd3",
         candidate_boards=boards, execution_enabled=False, rollout_ready=False, boot_and_jars_unchanged=True,
         inherited_status="Prior Mac/VM/static approvals do not transfer; no dry-run PASS claimed for new manifest"))
    save("rollback.json", dict(from_sha256=digest, to_sha256=OLD, atomic_members=MEMBERS, atomic_targets=targets,
         previous_bundle=old, previous_bundle_sha256=OLD_BUNDLE, previous_manifest_sha256=OLD_MANIFEST,
         host_unchanged=HOST, execution_enabled=False, scope="Restore whole approved baseline via executor only after outer authorization"))
    print("DRAFT " + sha(package / "bundle.json") + " manifest " + manifest_sha + " compat " + digest + " host unchanged, disabled")


if __name__ == "__main__":
    main()
