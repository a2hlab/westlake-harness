import copy
import json
import platform
import shutil
import subprocess

from prepare import HERE, MASTER, PRIVATE, WS, portable, save, sha, stage
from validation import OLD_RUNTIME, RUNTIME

STAGING = HERE / ".artifacts/native-t4-v1/native"
MEMBER = "payload/android/lib64/liboh_android_runtime.so"
TARGET = "/system/android/lib64/liboh_android_runtime.so"


def main():
    if platform.system() != "Darwin" or STAGING.exists():
        raise ValueError("Mac-only preparation requires a fresh immutable native staging path")
    history = HERE / "inputs/history-v1"
    for name in ["native-slots.json", "donor-receipt-status.json", "composition.json", "results.json"]:
        source = HERE / name
        destination = history / name
        if source.exists() and not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
    plan = json.loads((HERE / "plan.json").read_text())
    base = WS / plan["content_bases"]["common"]["path"].removeprefix("$WORKSPACES/")
    if sha(base / "bundle.json") != plan["content_bases"]["common"]["sha256"]:
        raise ValueError("U15 content baseline drift")
    baseline = json.loads((base / "native/package.json").read_text())
    if baseline["files"][MEMBER] != OLD_RUNTIME or sha(base / "native" / MEMBER) != OLD_RUNTIME:
        raise ValueError("U15 runtime baseline is not94c3")
    donor = WS / "westlake-harness-t4/benchmark/2026-10-03-u16-t4-m1-runtime/payload/liboh_android_runtime.so"
    candidate = stage(donor, PRIVATE / "native/liboh_android_runtime.so", RUNTIME)
    split = WS / "westlake-harness-wiki/benchmark/2026-10-03-m1-split"
    object_sha = {"shim_split.o": "003a4edbcbbb8cc9a2f6d4da9c788bd1e1e040953042bd4c1cbd20664a0f115f",
        "m1_copy.o": "3e2b4323700f535798827548264012e649e528c0d7d5ae64de48229a92d95b45"}
    for name, expected in object_sha.items():
        if sha(split / "build" / name) != expected:
            raise ValueError("Accepted split object identity drift")
    STAGING.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["/bin/cp", "-cR", base / "native", STAGING], check=True)
    destination = STAGING / MEMBER
    destination.chmod(destination.stat().st_mode | 0o200)
    shutil.copyfile(donor, destination)
    manifest = copy.deepcopy(baseline)
    manifest["files"][MEMBER] = RUNTIME
    manifest["live_hashes"][TARGET] = RUNTIME
    manifest.update(variant="U16 runtime-only t4 native staging; Flutter pending", execution_enabled=False, rollout_ready=False,
        rollout_blocker="Native batch incomplete; new BCP/images and future transaction BASE pending")
    save(STAGING / "package.json", manifest)
    checks = STAGING / "native-checks"
    scan = json.loads((checks / "scan-manifest.json").read_text())
    replacements = {"u13-m1-compat-shim.cpp": split / "build/cmp/android_graphics_compat_shim.cpp",
        "u16-m1-copy.cpp": MASTER / "benchmark/2026-10-03-m1-split/src/android_graphics_m1_copy.cpp"}
    sources = []
    for name, source in replacements.items():
        destination = checks / name
        if destination.exists():
            destination.chmod(destination.stat().st_mode | 0o200)
        shutil.copyfile(source, destination)
        scan["sources"][name] = dict(path=name, sha256=sha(source), source_sha256=sha(source), origin=portable(source), first_line=1)
        proof = HERE / "inputs/native-source" / name
        proof.parent.mkdir(parents=True, exist_ok=True)
        proof.write_text(portable(source.read_text()))
        sources.append(dict(source=source, source_sha256=sha(source), snapshot=str(proof.relative_to(HERE)), snapshot_sha256=sha(proof)))
    scan["profiles"].append(dict(name="u16-m1-copy", rule="namespace", source="u16-m1-copy.cpp", identity=dict(artifact=MEMBER)))
    for profile in scan["profiles"]:
        profile["identity"].update(package="u16-runtime-only-offline-staging", manifest_sha256=sha(STAGING / "package.json"),
            artifact_sha256=manifest["files"][profile["identity"]["artifact"]])
    save(checks / "scan-manifest.json", scan)
    inputs = json.loads((checks / "native-gates.json").read_text())
    inputs["package_manifest_sha256"] = sha(STAGING / "package.json")
    inputs["initialization"]["manifest"]["sha256"] = sha(checks / "scan-manifest.json")
    save(checks / "native-gates.json", inputs)
    for path, expected in manifest["files"].items():
        if sha(STAGING / path) != expected:
            raise ValueError("Staged package inventory mismatch")
    changes = {path: dict(old=baseline["files"].get(path), new=digest) for path, digest in manifest["files"].items()
        if baseline["files"].get(path) != digest}
    if changes != {MEMBER: dict(old=OLD_RUNTIME, new=RUNTIME)} or set(manifest["files"]) != set(baseline["files"]):
        raise ValueError("Runtime-only staging must preserve every other member")
    if sha(checks / "namespace-manifest.json") != sha(base / "native/native-checks/namespace-manifest.json"):
        raise ValueError("Namespace domains changed")
    dossier = MASTER / "benchmark/2026-10-03-u16-t4-m1-runtime"
    for source in [dossier / "README.md", dossier / "build_t4_hw248.sh", *sorted((dossier / "evidence").glob("*"))]:
        if not source.is_file():
            continue
        proof = HERE / "inputs/native-source/donor-t4" / str(source.relative_to(dossier))
        proof = proof.with_name(proof.name + ".txt") if proof.suffix == ".sh" else proof
        proof.parent.mkdir(parents=True, exist_ok=True)
        proof.write_text(portable(source.read_text(errors="backslashreplace")))
        sources.append(dict(source=source, source_sha256=sha(source), snapshot=str(proof.relative_to(HERE)), snapshot_sha256=sha(proof)))
    save("native-source-snapshots.json", sources)
    save("native-slot-binding.json", dict(execution_enabled=False, rollout_ready=False, native_batch_complete=False,
        staging=STAGING, base=base, baseline_runtime_sha256=OLD_RUNTIME, candidate_runtime_sha256=RUNTIME, candidate=candidate,
        baseline_native_manifest_sha256=sha(base / "native/package.json"), native_manifest_sha256=sha(STAGING / "package.json"),
        native_inputs_sha256=sha(checks / "native-gates.json"), source_count=len(sources), changes=changes,
        object_sha256=object_sha, changed_live_targets=[TARGET], added_payloads=[], removed_payloads=[],
        namespace_manifest_unchanged=True, bcp_changed=False, images_changed=False, donor_build_executed=False,
        source_alias_note="u13-m1-compat-shim.cpp profile name retained; contents replaced with actual split shim, plus separate M1 TU"))
    slots = json.loads((HERE / "native-slots.json").read_text())
    slots["slots"][0].update(state="arrived-staged", sha256=RUNTIME, snapshot=candidate["snapshot"], staged=True, applied=False)
    slots.update(native_partial_manifest_sha256=sha(STAGING / "package.json"), native_partial_inputs_sha256=sha(checks / "native-gates.json"))
    save("native-slots.json", slots)
    for name, data in [("baseline-manifest.json", baseline), ("candidate-manifest.json", manifest), ("scan-manifest.json", scan), ("native-inputs.json", inputs)]:
        save("inputs/native-metadata/" + name, data)
    print("U16 T4 STAGED: runtime94c3→1d42 only; Flutter pending; native batch disabled; no build or bundle descriptor")


if __name__ == "__main__":
    main()
