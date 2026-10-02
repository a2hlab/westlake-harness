import json
import shutil
import subprocess
import sys

from collect import BASE, HERE, MASTER, WS, portable, run, save, sha


def main():
    original = json.loads((BASE / "package.json").read_text())
    root = HERE / ".artifacts/audit-package"
    root.mkdir(exist_ok=True)
    replacements = {"payload/android/lib64/libmediandk.so": HERE / ".artifacts/libmediandk-build1.so",
                    "payload/android/lib64/libnativeloader.so": HERE / ".artifacts/policy/candidate1/libnativeloader-candidate.so",
                    "payload/route/libnativeloader.so": HERE / ".artifacts/policy/candidate1/libnativeloader-candidate.so"}
    files = dict(original["files"])
    files.update({name: sha(path) for name, path in replacements.items()})
    for name, digest in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        source = replacements.get(name, BASE / name)
        if sha(source) != digest:
            raise ValueError("input mismatch: " + name)
        if not target.exists() or sha(target) != digest:
            shutil.copyfile(source, target)
    manifest = dict(original, files=files, rollout_ready=False)
    save(".artifacts/audit-package/package.json", manifest)
    checks = root / "native-checks"
    if checks.exists():
        shutil.rmtree(checks)
    shutil.copytree(BASE / "native-checks", checks)
    scan = json.loads((checks / "scan-manifest.json").read_text())
    for name in ["candidate.c", "objects.c.inc"]:
        source = HERE / name
        target = "u12-mediandk-" + name
        shutil.copyfile(source, checks / target)
        scan["sources"][target] = dict(path=target, sha256=sha(source), origin=portable(source),
                                      source_sha256=sha(source), first_line=1)
        scan["profiles"].append(dict(name="u12-mediandk-" + name, rule="namespace", source=target,
                                     identity=dict(artifact="payload/android/lib64/libmediandk.so")))
    package_sha = sha(root / "package.json")
    for profile in scan["profiles"]:
        profile["identity"].update(package="offline-u12-mediandk", manifest_sha256=package_sha,
                                    artifact_sha256=files[profile["identity"]["artifact"]])
    save(".artifacts/audit-package/native-checks/scan-manifest.json", scan)
    inputs = json.loads((checks / "native-gates.json").read_text())
    inputs["package_manifest_sha256"] = package_sha
    inputs["initialization"]["manifest"]["sha256"] = sha(checks / "scan-manifest.json")
    save(".artifacts/audit-package/native-checks/native-gates.json", inputs)
    records = []
    reports = {}
    for name, package in [("baseline", BASE), ("candidate", root)]:
        records.append(run("native-" + name, ["python3", MASTER / "scripts/lab/native_predeploy.py", "--package", package,
                           "--inputs", package / "native-checks/native-gates.json"], allowed=(0, 1)))
        reports[name] = json.loads((HERE / ".artifacts" / ("native-" + name + ".txt")).read_text())
        if reports[name].get("errors"):
            raise ValueError("invalid gate input: " + name)
    def findings(report):
        return [{name: value for name, value in row.items() if name not in {"issue_id", "disposition", "exception"}}
                for row in report["gates"]["N2"]["findings"]]
    sys.path.insert(0, str(MASTER / "scripts/lab"))
    from native_needed_gate import ElfReader, scan_domains
    libc = WS / "westlake-inputs/oh61-link-inputs/system-lib64/ld-musl-aarch64.so.1"
    if sha(libc) != "fd3c4701acf719738fbd14cf1d419e4dd222c06a6df41f53d973354d648af7e2":
        raise ValueError("factory libc mismatch")
    virtual = {"/system/android/lib64/libmediandk.so": dict(path=replacements["payload/android/lib64/libmediandk.so"],
               sha256=files["payload/android/lib64/libmediandk.so"], package_path="candidate/libmediandk.so"),
               "/system/lib64/libc.so": dict(path=libc, sha256=sha(libc), package_path="factory/libc.so")}
    domains = [dict(name="provider-root", library_dirs=["/system/android/lib64", "/system/lib64"],
                    search_paths=["/system/android/lib64", "/system/lib64"], permitted_paths=["/system/android/lib64", "/system/lib64"])]
    closure_findings, closure = scan_domains(virtual, domains, ElfReader(shutil.which("llvm-readelf")))
    defined = set(subprocess.check_output(["llvm-nm", "-D", "--defined-only", "--format=just-symbols", libc], text=True).splitlines())
    undefined_lines = subprocess.check_output(["llvm-nm", "-D", "--undefined-only", virtual["/system/android/lib64/libmediandk.so"]["path"]], text=True).splitlines()
    required = {line.split()[-1] for line in undefined_lines if len(line.split()) == 2 and line.split()[0] == "U"}
    unresolved = sorted(required - defined)
    save("provider-closure.json", dict(factory_libc_sha256=sha(libc), factory_libc_path=portable(libc),
         search_model="explicit focused root+factory-libc domain; no inherit; NOT proof of live app namespace edges",
         findings=closure_findings, report=closure, strong_undefined=sorted(required), unresolved=unresolved))
    save("namespace-gates.json", dict(records=records, package_manifest_sha256=package_sha,
         baseline_status=reports["baseline"]["status"], candidate_status=reports["candidate"]["status"],
         n2_findings_identical=findings(reports["baseline"]) == findings(reports["candidate"]),
         n2_count=len(findings(reports["candidate"])),
         candidate_new_n1=[row for row in reports["candidate"]["gates"]["N1"]["findings"] if row["profile"].startswith("u12-mediandk-")],
         exception_rebinding_approved=False, rollout_ready=False))
    if closure_findings or unresolved:
        raise ValueError("focused provider closure unresolved")
    print("focused N2: inherit=false findings=0 strong-undefined=" + str(len(required)) + " unresolved=0")
    print("package N1/N2 baseline=" + reports["baseline"]["status"] + " candidate=" + reports["candidate"]["status"] + " (new manifest exceptions NOT approved)")


if __name__ == "__main__":
    main()
