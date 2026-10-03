from collections import Counter
import json
import platform
import subprocess
import sys

from prepare import HERE, MASTER, WS, portable, save, sha
from native_stage import MEMBER, STAGING
import generation_static_checks as static
from native_needed_gate import parse_dynamic


def capture(label, argv):
    raw = HERE / ".artifacts/raw" / (label + ".txt")
    raw.parent.mkdir(parents=True, exist_ok=True)
    with raw.open("wb") as stream:
        result = subprocess.run([str(value) for value in argv], stdout=stream, stderr=subprocess.STDOUT)
    evidence = HERE / "evidence" / raw.name
    evidence.parent.mkdir(exist_ok=True)
    evidence.write_text(portable(raw.read_text(errors="backslashreplace")))
    print(label + " exit=" + str(result.returncode), flush=True)
    return dict(command=argv, exit_code=result.returncode, raw=raw, raw_sha256=sha(raw), evidence=str(evidence.relative_to(HERE)), evidence_sha256=sha(evidence))


def consumers():
    inventory_path = WS / "westlake-harness-bms/benchmark/2026-10-02-toutiao-bionic-scope/consumers.json"
    inventory = json.loads(inventory_path.read_text())
    root = inventory_path.parent / ".artifacts/members"
    selected = {member["sha256"]: root / (member["sha256"] + ".so") for app in inventory["apps"] for member in app["members"]
        if member["status"] == "ELF64-AArch64" and member["imports"]}
    for key in ["vlc", "fd-fennec_fdroid", "firefox", "ppsspp"]:
        for path in (WS / "westlake-harness-bms/benchmark/2026-10-02-u12-disappeared/.artifacts").glob(key + "-*.so"):
            selected[sha(path)] = path
    if len(selected) != 219 or any(sha(path) != digest for digest, path in selected.items()):
        raise ValueError("Pinned219 consumer inventory changed")
    save("native-consumers.json", dict(count=219, inventory_source=inventory_path, inventory_source_sha256=sha(inventory_path),
        members=[dict(source=path, sha256=digest) for digest, path in sorted(selected.items())], scope="exact existing219 ELF objects; ABI intersections only, not relocation namespace or app death proof"))
    return selected


def main():
    if platform.system() != "Darwin":
        raise ValueError("Mac-only static task; no VM during windows")
    binding = json.loads((HERE / "native-slot-binding.json").read_text())
    base = WS / binding["base"].removeprefix("$WORKSPACES/")
    old, candidate = base / "native" / MEMBER, STAGING / MEMBER
    if sha(old) != binding["baseline_runtime_sha256"] or sha(candidate) != binding["candidate_runtime_sha256"]:
        raise ValueError("Explicit runtime comparison identity drift")
    registry = MASTER / "knowledge/gates/native-predeploy-exceptions.json"
    before = sha(registry)
    records = [capture("u16-whois-runtime-u15-content", [sys.executable, MASTER / "scripts/lab/deployed_whois.py", old.name, "--generation", base])]
    open_data, dynamics = {}, {}
    for label, path in [("u15", old), ("u16-t4", candidate)]:
        output = HERE / ".artifacts" / ("u16-open-" + label + ".json")
        records.append(capture("u16-open-" + label, [sys.executable, MASTER / "scripts/lab/open_site_scan.py", path, "--json", output]))
        data = json.loads(output.read_text())
        open_data[label] = data
        save("evidence/u16-open-" + label + ".json", data)
        records.append(capture("u16-needed-" + label, ["llvm-readelf", "-d", "--wide", path]))
        dynamics[label] = parse_dynamic((HERE / ".artifacts/raw" / ("u16-needed-" + label + ".txt")).read_text())
        records.append(capture("u16-dynsym-" + label, ["llvm-readelf", "--dyn-syms", "--wide", path]))
    records.append(capture("u16-strings-runtime", [sys.executable, MASTER / "scripts/lab/deployed_strings_diff.py", candidate, "--deployed", old]))
    selected = consumers()
    abi_out = HERE / ".artifacts/u16-abi-runtime.json"
    records.append(capture("u16-abi-calls-219", [sys.executable, MASTER / "scripts/lab/abi_diff.py", "--old", old, "--new", candidate, "--calls", "--json", abi_out,
        *[value for path in selected.values() for value in ["--consumer", path]]]))
    abi = json.loads(abi_out.read_text())
    save("evidence/u16-abi-runtime.json", abi)
    reports = {}
    for label, root in [("u15", base / "native"), ("u16-t4", STAGING)]:
        reports[label] = {}
        for gate in ["N1", "N2"]:
            name = "u16-native-" + label + "-" + gate
            records.append(capture(name, [sys.executable, MASTER / "scripts/lab/native_predeploy.py", "--package", root,
                "--inputs", root / "native-checks/native-gates.json", "--gate", gate, "--exceptions", registry, "--readelf", "llvm-readelf"]))
            report = json.loads((HERE / ".artifacts/raw" / (name + ".txt")).read_text())
            reports[label][gate] = report
            save("evidence/" + name + ".json", report)
    old_static, candidate_static = static.scan(old), static.scan(candidate)
    delta = static.site_delta(old_static["binaries"][0]["sites"], candidate_static["binaries"][0]["sites"])
    delta["namespace_api_changes"] = {name: dict(deployed=old_static["namespace_api_calls"].get(name, []), candidate=candidate_static["namespace_api_calls"].get(name, []))
        for name in sorted(old_static["namespace_api_calls"].keys() | candidate_static["namespace_api_calls"].keys())
        if old_static["namespace_api_calls"].get(name) != candidate_static["namespace_api_calls"].get(name)}
    delta["namespace_literal_changes"] = dict(added=sorted(set(candidate_static["namespace_literals"]) - set(old_static["namespace_literals"])),
        removed=sorted(set(old_static["namespace_literals"]) - set(candidate_static["namespace_literals"])))
    save("native-open-delta.json", dict(deployed_sha256=sha(old), candidate_sha256=sha(candidate), delta=delta,
        delta_sha256=static.bundle.digest(delta), approved_by=None, production_schema=True))
    comparisons = {}
    for gate in ["N1", "N2"]:
        old_report, new_report = reports["u15"][gate], reports["u16-t4"][gate]
        old_rows = old_report.get("gates", {}).get(gate, {}).get("findings", [])
        new_rows = new_report.get("gates", {}).get(gate, {}).get("findings", [])
        def normalized(row):
            return json.dumps({key: value for key, value in row.items() if key not in ["issue_id", "package_manifest_sha256", "inputs_sha256", "artifact_sha256", "exception", "decision"]}, sort_keys=True)
        previous = Counter(normalized(row) for row in old_rows)
        current = Counter(normalized(row) for row in new_rows)
        comparisons[gate] = dict(baseline_findings=len(old_rows), candidate_findings=len(new_rows), exact_nonbinding_equal=sum((previous & current).values()),
            candidate_nonbinding_changes=list((current - previous).elements()), removed_nonbinding_rows=list((previous - current).elements()),
            rule="Only top-level package/artifact/issue identity removed; preserve evidence paths lines text sequence and all semantic fields")
    after = sha(registry)
    if after != before:
        raise ValueError("Active exception table changed during static task; rerun against one identity")
    save("native-gate-runs.json", dict(records=records, execution_enabled=False, rollout_ready=False, actual_os=platform.system(),
        board_access=False, vm_access=False, remote_access=False, active_registry_sha256=before, active_registry_sha256_after=after,
        active_registry_updated=False, native_manifest_sha256=binding["native_manifest_sha256"], native_inputs_sha256=binding["native_inputs_sha256"],
        baseline_runtime_sha256=sha(old), candidate_runtime_sha256=sha(candidate), consumer_count=219,
        needed_unchanged=dynamics["u15"]["needed"] == dynamics["u16-t4"]["needed"], dynamics=dynamics,
        open_counts={label: len(data["binaries"][0]["sites"]) for label, data in open_data.items()},
        namespace_edges={label: data["binaries"][0]["namespace_edges"] for label, data in open_data.items()},
        open_findings={label: data["findings"] for label, data in open_data.items()},
        abi_summary={name: len(abi.get(name, [])) for name in ["removed", "added", "drift", "consumer_breaks", "call_diffs"]},
        findings_comparison=comparisons, native_reports={label: {gate: dict(exit_code=report["exit_code"], status=report["status"], errors=report["errors"],
            rejected=report.get("gates", {}).get(gate, {}).get("rejected")) for gate, report in row.items()} for label, row in reports.items()},
        native_production_approved=False, registry_delta_applied=False, final_bundle_sha256=None))
    print("U16 T4 STATIC COMPLETE: raw exits retained; current active registry unchanged; Flutter/27images/final binding pending")


if __name__ == "__main__":
    main()
