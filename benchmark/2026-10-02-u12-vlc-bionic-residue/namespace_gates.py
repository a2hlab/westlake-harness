import json
import shutil

from collect import BASE, HERE, MASTER, capture, portable, save, sha


def main():
    original = json.loads((BASE / "package.json").read_text())
    root = HERE / ".artifacts/audit-package"
    root.mkdir(exist_ok=True)
    candidate = HERE / ".artifacts/candidate1.so"
    replacements = {name: candidate for name in original["files"] if name.endswith("/libbionic_compat.so")}
    if set(replacements) != {"payload/android/lib64/libbionic_compat.so", "payload/route/libbionic_compat.so"}:
        raise ValueError("unexpected deployed compat aliases")
    files = dict(original["files"])
    files.update({name: sha(path) for name, path in replacements.items()})
    for name, digest in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        source = replacements.get(name, BASE / name)
        if sha(source) != digest:
            raise ValueError("package input drift")
        if target.exists() and sha(target) != digest:
            target.unlink()
        if not target.exists():
            shutil.copyfile(source, target)
    save(".artifacts/audit-package/package.json", dict(original, files=files, rollout_ready=False))
    checks = root / "native-checks"
    if checks.exists():
        shutil.rmtree(checks)
    shutil.copytree(BASE / "native-checks", checks)
    scan = json.loads((checks / "scan-manifest.json").read_text())
    source_name = "u12-vlc-bionic-residue.c"
    shutil.copyfile(HERE / "vlc_bionic_residue.c", checks / source_name)
    scan["sources"][source_name] = dict(path=source_name, sha256=sha(HERE / "vlc_bionic_residue.c"),
                                      origin=portable(HERE / "vlc_bionic_residue.c"), source_sha256=sha(HERE / "vlc_bionic_residue.c"), first_line=1)
    scan["profiles"].append(dict(name="u12-vlc-residue", rule="namespace", source=source_name,
                                  identity=dict(artifact="payload/android/lib64/libbionic_compat.so")))
    package_sha = sha(root / "package.json")
    for profile in scan["profiles"]:
        profile["identity"].update(package="offline-u12-vlc", manifest_sha256=package_sha,
                                    artifact_sha256=files[profile["identity"]["artifact"]])
    save(".artifacts/audit-package/native-checks/scan-manifest.json", scan)
    inputs = json.loads((checks / "native-gates.json").read_text())
    inputs["package_manifest_sha256"] = package_sha
    inputs["initialization"]["manifest"]["sha256"] = sha(checks / "scan-manifest.json")
    save(".artifacts/audit-package/native-checks/native-gates.json", inputs)
    reports = {}
    records = []
    for name, package in [("baseline", BASE), ("candidate", root)]:
        records.append(capture("native-" + name, ["python3", MASTER / "scripts/lab/native_predeploy.py", "--package", package,
                                                   "--inputs", package / "native-checks/native-gates.json"], allowed=(0, 1)))
        reports[name] = json.loads((HERE / ".artifacts" / ("native-" + name + ".txt")).read_text())
        if reports[name].get("errors"):
            raise ValueError("invalid native gate input")

    def without_disposition(report, gate):
        return [{name: value for name, value in row.items() if name not in {"issue_id", "disposition", "exception"}}
                for row in report["gates"][gate]["findings"]]

    save("namespace-gates.json", dict(records=records, package_manifest_sha256=package_sha,
         baseline_status=reports["baseline"]["status"], candidate_status=reports["candidate"]["status"],
         n2_findings_identical=without_disposition(reports["baseline"], "N2") == without_disposition(reports["candidate"], "N2"),
         n2_count=len(without_disposition(reports["candidate"], "N2")),
         n1_new=[row for row in reports["candidate"]["gates"]["N1"]["findings"] if row.get("profile") == "u12-vlc-residue"],
         exception_rebinding_approved=False, rollout_ready=False))
    print("N1 new profile findings=" + str(len(json.loads((HERE / "namespace-gates.json").read_text())["n1_new"])))
    print("N1/N2 baseline=" + reports["baseline"]["status"] + " candidate=" + reports["candidate"]["status"] + "; new manifest not approved")


if __name__ == "__main__":
    main()
