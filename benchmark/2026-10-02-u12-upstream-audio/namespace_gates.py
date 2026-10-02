import json
import shutil

from collect import FACADE, HERE, MASTER, PAYLOAD, REPO, portable, run, save, sha


def main():
    baseline = PAYLOAD.parent
    original = json.loads((baseline / "package.json").read_text())
    root = HERE / ".artifacts/audit-package"
    root.mkdir(exist_ok=True)
    artifact = "payload/android/lib64/libOpenSLES.so"
    candidate = HERE / ".artifacts/libOpenSLES-candidate.so"
    for name, digest in original["files"].items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        source = candidate if name == artifact else baseline / name
        expected = sha(candidate) if name == artifact else digest
        if not target.is_file() or sha(target) != expected:
            shutil.copyfile(source, target)
        if sha(target) != expected:
            raise ValueError("overlay input mismatch: " + name)
    manifest = dict(original)
    manifest["files"] = dict(original["files"], **{artifact: sha(candidate)})
    manifest["rollout_ready"] = False
    save(".artifacts/audit-package/package.json", manifest)
    checks = root / "native-checks"
    if not checks.exists():
        shutil.copytree(baseline / "native-checks", checks)
    scan = json.loads((baseline / "native-checks/scan-manifest.json").read_text())
    source = HERE / "candidate/opensles_android_adapter.c"
    source_name = "u12-opensles-adapter.c"
    shutil.copyfile(source, checks / source_name)
    scan["sources"][source_name] = dict(path=source_name, sha256=sha(source), origin=portable(source),
                                        source_sha256=sha(source), first_line=1)
    scan["profiles"].append(dict(name="u12-opensles-owner-injection", rule="namespace", source=source_name,
                                 identity=dict(artifact=artifact)))
    package_sha = sha(root / "package.json")
    for profile in scan["profiles"]:
        profile["identity"].update(package="offline-u12-primitive-probe", manifest_sha256=package_sha,
                                    artifact_sha256=manifest["files"][profile["identity"]["artifact"]])
    save(".artifacts/audit-package/native-checks/scan-manifest.json", scan)
    inputs = json.loads((baseline / "native-checks/native-gates.json").read_text())
    inputs["package_manifest_sha256"] = package_sha
    inputs["initialization"]["manifest"]["sha256"] = sha(checks / "scan-manifest.json")
    save(".artifacts/audit-package/native-checks/native-gates.json", inputs)
    records = []
    for name, package in [("baseline", baseline), ("candidate", root)]:
        records.append(run("native-" + name, ["python3", MASTER / "scripts/lab/native_predeploy.py", "--package", package,
                                              "--inputs", package / "native-checks/native-gates.json"]))
    reports = {name: json.loads((HERE / ".artifacts" / ("native-" + name + ".txt")).read_text())
               for name in ["baseline", "candidate"]}
    for name, report in reports.items():
        if report.get("errors"):
            raise ValueError("invalid native gate input: " + name)
    findings = lambda report: [{name: value for name, value in row.items() if name not in {"issue_id", "disposition", "exception"}}
                               for row in report["gates"]["N2"]["findings"]]
    summary = dict(device_io=False, package_manifest_sha256=package_sha, replaced_artifact=artifact,
         candidate_sha256=sha(candidate), deployed_sha256=sha(FACADE), records=records,
         baseline_status=reports["baseline"]["status"], candidate_status=reports["candidate"]["status"],
         n2_findings_identical=findings(reports["baseline"]) == findings(reports["candidate"]),
         candidate_new_n1=[row for row in reports["candidate"]["gates"]["N1"]["findings"] if row["profile"] == "u12-opensles-owner-injection"],
         exception_rebinding_approved=False, owner_injection_publication_implemented=False, rollout_ready=False)
    save("namespace-gates.json", summary)
    print(json.dumps({name: summary[name] for name in ["baseline_status", "candidate_status", "n2_findings_identical",
                                                     "candidate_new_n1", "rollout_ready"]}))


if __name__ == "__main__":
    main()
