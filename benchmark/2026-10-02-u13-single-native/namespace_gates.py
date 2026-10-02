import json
from pathlib import Path
import shutil

from build import HERE, MASTER, U12, portable, run, save, sha


def main():
    base = U12 / "native"
    root = HERE / ".artifacts/two-piece-package"
    root.mkdir(exist_ok=True)
    original = json.loads((base / "package.json").read_text())
    replacements = {
        "payload/runtime/appspawn-x": HERE / ".artifacts/host/candidate1/appspawn-x-candidate1",
        "payload/android/lib64/libnativeloader.so": HERE / ".artifacts/policy/candidate1/libnativeloader-candidate.so",
        "payload/route/libnativeloader.so": HERE / ".artifacts/policy/candidate1/libnativeloader-candidate.so"}
    files = dict(original["files"])
    for name, path in replacements.items():
        files[name] = sha(path)
    for name, digest in files.items():
        source = replacements.get(name, base / name)
        if sha(source) != digest:
            raise ValueError("package input drift: " + name)
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or sha(target) != digest:
            shutil.copyfile(source, target)
    manifest = dict(original, files=files, rollout_ready=False)
    (root / "package.json").write_text(json.dumps(manifest, indent=2) + "\n")
    checks = root / "native-checks"
    if not checks.exists():
        shutil.copytree(base / "native-checks", checks)
    scan = json.loads((base / "native-checks/scan-manifest.json").read_text())
    overlays = {"u10-1-native-policy.h": HERE / "sources/candidate/policy/include/nativeloader/native_bridge_policy.h"}
    for name, source in overlays.items():
        shutil.copyfile(source, checks / name)
        scan["sources"][name].update(sha256=sha(source), source_sha256=sha(source), origin=portable(source))
    for name, source, artifact in [
        ("u13-zlib-route.h", HERE / "sources/candidate/host/zlib-route.h", "payload/runtime/appspawn-x"),
        ("u13-system-loader.cpp", HERE / "sources/candidate/policy/src/system_loader.cpp", "payload/android/lib64/libnativeloader.so")]:
        shutil.copyfile(source, checks / name)
        scan["sources"][name] = dict(path=name, sha256=sha(source), origin=portable(source), source_sha256=sha(source), first_line=1)
        scan["profiles"].append(dict(name=name, rule="namespace", source=name, identity=dict(artifact=artifact)))
    manifest_sha = sha(root / "package.json")
    for profile in scan["profiles"]:
        artifact = profile["identity"]["artifact"]
        profile["identity"].update(package="offline-u13-two-piece", manifest_sha256=manifest_sha, artifact_sha256=files[artifact])
    (checks / "scan-manifest.json").write_text(json.dumps(scan, indent=2) + "\n")
    inputs = json.loads((base / "native-checks/native-gates.json").read_text())
    inputs["package_manifest_sha256"] = manifest_sha
    inputs["initialization"]["manifest"]["sha256"] = sha(checks / "scan-manifest.json")
    (checks / "native-gates.json").write_text(json.dumps(inputs, indent=2) + "\n")
    reports, records = {}, []
    for name, package in [("u12", base), ("candidate", root)]:
        records.append(run("native-" + name, ["python3", MASTER / "scripts/lab/native_predeploy.py",
            "--package", package, "--inputs", package / "native-checks/native-gates.json"], allowed=(0, 1)))
        reports[name] = json.loads((HERE / ".artifacts/raw" / ("native-" + name + ".txt")).read_text())
        save("evidence/native-" + name + ".json", reports[name])
        if reports[name].get("errors"):
            raise ValueError("invalid native gate input")
    def structural(row):
        return {key: value for key, value in row.items() if key not in {"issue_id", "disposition", "exception"}}
    delta = {}
    for gate in ["N1", "N2"]:
        before = reports["u12"]["gates"][gate]["findings"]
        after = reports["candidate"]["gates"][gate]["findings"]
        delta[gate] = dict(before_count=len(before), after_count=len(after),
                          structurally_identical=[structural(row) for row in before] == [structural(row) for row in after],
                          new=[row for row in after if structural(row) not in [structural(value) for value in before]])
    save("namespace-gates.json", dict(commands=records, delta=delta,
        package_manifest_sha256=manifest_sha, status={name: report["status"] for name, report in reports.items()},
        execution_enabled=False, scope="U12 plus only these host/policy replacements, NOT final U13 runtime/compat assembly",
        exception_rebinding_approved=False, rollout_ready=False))
    print(json.dumps(delta, indent=2))


if __name__ == "__main__":
    main()
