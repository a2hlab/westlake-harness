import copy
import json
import shutil

from common import HERE, HOST, JAR, MASTER, PACKAGE, PREVIOUS, WS, save, sha
import generation_bundle as bundle_tool
import u7_executor as executor


def main():
    old = PREVIOUS / ".artifacts/bundle-v2"
    expected = "adf3705043472de8797a677d76c16b5976cb9c0be11364daa3bbd1b882b1698b"
    if sha(old / "bundle.json") != expected:
        raise ValueError("Previous bundle identity changed")
    bundle, manifest, _ = bundle_tool.validate(old)
    donor = WS / "westlake-inputs/generations/u13-jar-v3/oh-adapter-runtime-u13-v3.jar"
    if sha(donor) != JAR or PACKAGE.exists():
        raise ValueError("Donor mismatch or frozen output already exists")
    shutil.copytree(old, PACKAGE)
    member = "payload/android/framework/oh-adapter-runtime.jar"
    target = "/system/android/framework/oh-adapter-runtime.jar"
    for path in [PACKAGE / "native" / member, bundle_tool.member(PACKAGE, bundle["runtime_jar"])]:
        path.chmod(path.stat().st_mode | 0o200)
        shutil.copyfile(donor, path)
    manifest = copy.deepcopy(manifest)
    manifest["files"][member] = JAR
    manifest["live_hashes"][target] = JAR
    save(PACKAGE / "native/package.json", manifest)
    checks = PACKAGE / "native/native-checks"
    scan = json.loads((checks / "scan-manifest.json").read_text())
    for profile in scan["profiles"]:
        profile["identity"]["manifest_sha256"] = sha(PACKAGE / "native/package.json")
    save(checks / "scan-manifest.json", scan)
    inputs = json.loads((checks / "native-gates.json").read_text())
    inputs["package_manifest_sha256"] = sha(PACKAGE / "native/package.json")
    inputs["initialization"]["manifest"]["sha256"] = sha(checks / "scan-manifest.json")
    save(checks / "native-gates.json", inputs)
    bundle["runtime_jar"]["sha256"] = JAR
    bundle["native"]["manifest"]["sha256"] = sha(PACKAGE / "native/package.json")
    save(PACKAGE / "bundle.json", bundle)
    new_bundle, new_manifest, _ = bundle_tool.validate(PACKAGE)
    if new_manifest["files"]["payload/runtime/appspawn-x"] != HOST:
        raise ValueError("Held host unexpectedly included")
    if new_bundle.get("rollout_ready") is not False or "window_authorization" in new_bundle:
        raise ValueError("Draft is not disabled")
    old_manifest = json.loads((old / "native/package.json").read_text())
    changed = {name for name in manifest["files"] if manifest["files"][name] != old_manifest["files"][name]}
    if changed != {member}:
        raise ValueError("Unexpected native inventory change")
    composition = json.loads((PREVIOUS / "composition.json").read_text())
    boards = copy.deepcopy(composition["candidate_boards"])
    for board in boards.values():
        board["expected"][target] = JAR
        board["fingerprints"] = executor.fingerprints(board["expected"], board["reference_paths"])
    save("composition.json", dict(package=PACKAGE, previous_bundle_sha256=expected,
        bundle_sha256=sha(PACKAGE / "bundle.json"), native_manifest_sha256=sha(PACKAGE / "native/package.json"),
        native_inputs_sha256=sha(checks / "native-gates.json"), runtime_jar_sha256=JAR,
        changed_payload_members=sorted(changed), host_sha256=HOST, candidate_boards=boards,
        boot_group_unchanged=new_bundle["boot_group"] == json.loads((old / "bundle.json").read_text())["boot_group"],
        execution_enabled=False, rollout_ready=False, approvals_transferred=False))
    save("evidence/outer-approval.json", json.loads((MASTER / "benchmark/2026-10-03-u13-gate-review/outer-approval.json").read_text()))
    save("evidence/jar-v3-results.json", json.loads((MASTER / "benchmark/2026-10-03-u13-jar-v3-gcm/results.json").read_text()))
    print("DISABLED_V3 bundle=" + sha(PACKAGE / "bundle.json") + " manifest=" + sha(PACKAGE / "native/package.json"))


if __name__ == "__main__":
    main()
