import json
import platform
import shutil
import subprocess

from native_stage import STAGING
from prepare import HERE, MASTER, PRIVATE, WS, portable, save, sha, stage

PAIR = HERE / ".artifacts/native-pair-a3/native"
FLUTTER = "payload/android/lib64/westlake_flutter/libandroid.so"
FLUTTER_TARGET = "/system/android/lib64/westlake_flutter/libandroid.so"
FLUTTER_SHA = "eb90a6409c9caaba058d2463cad9c193d344527051455d8aca8421e6b7011b4f"
OLD_FLUTTER_SHA = "9b8245022f9c98dac41a85acfa553e96e6385073fd7b15298199a1cce223647b"


def main():
    if platform.system() != "Darwin" or PAIR.exists():
        raise ValueError("Mac-only fresh immutable staging required")
    binding = json.loads((HERE / "native-slot-binding.json").read_text())
    base = WS / binding["base"].removeprefix("$WORKSPACES/")
    old = json.loads((base / "native/package.json").read_text())
    if old["files"][FLUTTER] != OLD_FLUTTER_SHA or sha(base / "native" / FLUTTER) != OLD_FLUTTER_SHA:
        raise ValueError("Actual U15 Flutter baseline identity drift")
    release = WS / "westlake-inputs/generations/u16-flutter-egl-names-libandroid-v1"
    donor = release / FLUTTER
    if sha(donor) != FLUTTER_SHA:
        raise ValueError("Corrected donor identity required; never select15e988")
    inventory = release / "SHA256SUMS"
    rows = [line.split(maxsplit=1) for line in inventory.read_text().splitlines() if line and not line.startswith("#")]
    if {row[1] for row in rows} != {FLUTTER, "logs/u16-eglnames-a.log", "logs/u16-eglnames-b.log"}:
        raise ValueError("Explicit A3 payload and two-build log inventory changed")
    for digest, relative in rows:
        if sha(release / relative) != digest:
            raise ValueError("Published A3 inventory hash mismatch")
    snapshot = stage(donor, PRIVATE / "native/flutter-libandroid-eb90.so", FLUTTER_SHA)
    history = HERE / "inputs/history-pair-b1c9"
    history.mkdir(parents=True, exist_ok=True)
    for name in ["native-slots.json", "composition.json", "results.json", "validation-runs.json", "preflight.json",
            "native-pair-binding.json", "native-pair-gates.json", "native-pair-review.pending.json", "flutter-source-snapshots.json"]:
        if (HERE / name).exists() and not (history / name).exists():
            shutil.copyfile(HERE / name, history / name)
    PAIR.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["/bin/cp", "-cR", STAGING, PAIR], check=True)
    destination = PAIR / FLUTTER
    destination.chmod(destination.stat().st_mode | 0o200)
    shutil.copyfile(donor, destination)
    manifest = json.loads((PAIR / "package.json").read_text())
    manifest["files"][FLUTTER] = FLUTTER_SHA
    manifest["live_hashes"][FLUTTER_TARGET] = FLUTTER_SHA
    manifest.update(variant="U16 single native batch: runtime1d42 + FlutterA3 eb90; disabled",
        execution_enabled=False, rollout_ready=False, rollout_blocker="BCP27 pair and future transaction BASE and outer native review pending")
    save(PAIR / "package.json", manifest)
    dossier = MASTER / "benchmark/2026-10-03-u16-flutter-egl-names"
    new_source = dossier / "src/flutter_egl_getprocaddress.cpp"
    checks = PAIR / "native-checks"
    name = "u16-flutter-impeller.cpp"
    shutil.copyfile(new_source, checks / name)
    scan = json.loads((checks / "scan-manifest.json").read_text())
    scan["sources"][name] = dict(path=name, sha256=sha(new_source), source_sha256=sha(new_source), origin=portable(new_source), first_line=1)
    scan["profiles"].append(dict(name="u16-flutter-impeller", rule="namespace", source=name, identity=dict(artifact=FLUTTER)))
    for profile in scan["profiles"]:
        profile["identity"].update(package="u16-single-native-disabled", manifest_sha256=sha(PAIR / "package.json"),
            artifact_sha256=manifest["files"][profile["identity"]["artifact"]])
    save(checks / "scan-manifest.json", scan)
    inputs = json.loads((checks / "native-gates.json").read_text())
    inputs["package_manifest_sha256"] = sha(PAIR / "package.json")
    inputs["initialization"]["manifest"]["sha256"] = sha(checks / "scan-manifest.json")
    save(checks / "native-gates.json", inputs)
    changes = {name: dict(old=old["files"].get(name), new=digest) for name, digest in manifest["files"].items() if old["files"].get(name) != digest}
    if set(changes) != {"payload/android/lib64/liboh_android_runtime.so", FLUTTER} or set(old["files"]) != set(manifest["files"]):
        raise ValueError("Exactly two payload changes required")
    for name, expected in manifest["files"].items():
        if sha(PAIR / name) != expected:
            raise ValueError("Selected native inventory drift")
    if sha(checks / "namespace-manifest.json") != sha(base / "native/native-checks/namespace-manifest.json"):
        raise ValueError("Native domain manifest changed")
    sources = []
    for source in [dossier / "README.md", dossier / "results.json",
            *sorted((dossier / "src").glob("*")), *sorted((dossier / "evidence").glob("*"))]:
        if not source.is_file() or source.suffix == ".so":
            continue
        proof = HERE / "inputs/flutter-source-a3" / source.relative_to(dossier)
        if proof.suffix == ".sh":
            proof = proof.with_name(proof.name + ".txt")
        proof.parent.mkdir(parents=True, exist_ok=True)
        proof.write_text(portable(source.read_text(errors="backslashreplace")))
        sources.append(dict(source=source, source_sha256=sha(source), snapshot=str(proof.relative_to(HERE)), snapshot_sha256=sha(proof)))
    for source in [inventory, *sorted((release / "logs").glob("*"))]:
        proof = HERE / "inputs/flutter-source-a3/release" / source.relative_to(release)
        proof.parent.mkdir(parents=True, exist_ok=True)
        proof.write_text(portable(source.read_text(errors="backslashreplace")))
        sources.append(dict(source=source, source_sha256=sha(source), snapshot=str(proof.relative_to(HERE)), snapshot_sha256=sha(proof)))
    save("flutter-source-snapshots.json", sources)
    save("native-pair-binding.json", dict(execution_enabled=False, rollout_ready=False, final_bundle_sha256=None,
        staging=PAIR, base=base, changes=changes, native_batch_artifacts_arrived=True, native_production_approved=False,
        flutter_snapshot=snapshot, namespace_manifest_unchanged=True, westlake_native_libandroid_unchanged=True,
        native_manifest_sha256=sha(PAIR / "package.json"), native_inputs_sha256=sha(checks / "native-gates.json"),
        donor_commit="a53534971f", donor_build_executed=False, source_count=len(sources)))
    for name, data in [("baseline-manifest.json", old), ("candidate-manifest.json", manifest), ("scan-manifest.json", scan), ("native-inputs.json", inputs)]:
        save("inputs/native-pair-metadata/" + name, data)
    slots = json.loads((HERE / "native-slots.json").read_text())
    slots["slots"][1].update(state="arrived-staged", sha256=FLUTTER_SHA, snapshot=snapshot["snapshot"], staged=True,
        applied=False, blocker="Full combined native review and27 images/transaction BASE pending")
    slots.update(native_partial_manifest_sha256=sha(PAIR / "package.json"), native_partial_inputs_sha256=sha(checks / "native-gates.json"))
    save("native-slots.json", slots)
    print("U16 single native batch STAGED: runtime1d42 + FlutterA3 eb90; exactly2 payloads; disabled")


if __name__ == "__main__":
    main()
