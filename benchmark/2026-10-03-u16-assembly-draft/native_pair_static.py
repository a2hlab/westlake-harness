from collections import Counter
import json
import platform
import sys

from prepare import HERE, MASTER, WS, save, sha
import generation_static_checks as static
from native_needed_gate import parse_dynamic
from native_pair import FLUTTER, PAIR
from native_stage import MEMBER
from native_static import capture, consumers


def main():
    if platform.system() != "Darwin":
        raise ValueError("Mac-only offline static gates")
    binding = json.loads((HERE / "native-pair-binding.json").read_text())
    base = WS / binding["base"].removeprefix("$WORKSPACES/")
    registry = MASTER / "knowledge/gates/native-predeploy-exceptions.json"
    before = sha(registry)
    selected = consumers()
    records, members = [], {}
    for label, member in [("runtime", MEMBER), ("flutter", FLUTTER)]:
        old, candidate = base / "native" / member, PAIR / member
        if binding["changes"][member] != dict(old=sha(old), new=sha(candidate)):
            raise ValueError("Explicit member identity drift")
        records.append(capture("u16-a3-whois-" + label, [sys.executable, MASTER / "scripts/lab/deployed_whois.py", old.name, "--generation", base]))
        opens, dynamics = {}, {}
        for version, path in [("u15", old), ("u16", candidate)]:
            name = "u16-a3-" + label + "-" + version
            output = HERE / ".artifacts" / (name + "-open.json")
            records.append(capture(name + "-open", [sys.executable, MASTER / "scripts/lab/open_site_scan.py", path, "--json", output]))
            opens[version] = json.loads(output.read_text())
            save("evidence/" + name + "-open.json", opens[version])
            records.append(capture(name + "-needed", ["llvm-readelf", "-d", "--wide", path]))
            dynamics[version] = parse_dynamic((HERE / ".artifacts/raw" / (name + "-needed.txt")).read_text())
            records.append(capture(name + "-dynsym", ["llvm-readelf", "--dyn-syms", "--wide", path]))
        records.append(capture("u16-a3-" + label + "-strings", [sys.executable, MASTER / "scripts/lab/deployed_strings_diff.py", candidate, "--deployed", old]))
        output = HERE / ".artifacts" / ("u16-a3-" + label + "-abi.json")
        records.append(capture("u16-a3-" + label + "-abi-calls-219", [sys.executable, MASTER / "scripts/lab/abi_diff.py",
            "--old", old, "--new", candidate, "--calls", "--json", output,
            *[value for path in selected.values() for value in ["--consumer", path]]]))
        abi = json.loads(output.read_text())
        save("evidence/u16-a3-" + label + "-abi.json", abi)
        old_scan, new_scan = static.scan(old), static.scan(candidate)
        delta = static.site_delta(old_scan["binaries"][0]["sites"], new_scan["binaries"][0]["sites"])
        delta["namespace_api_changes"] = {name: dict(deployed=old_scan["namespace_api_calls"].get(name, []), candidate=new_scan["namespace_api_calls"].get(name, []))
            for name in sorted(old_scan["namespace_api_calls"].keys() | new_scan["namespace_api_calls"].keys())
            if old_scan["namespace_api_calls"].get(name) != new_scan["namespace_api_calls"].get(name)}
        delta["namespace_literal_changes"] = dict(added=sorted(set(new_scan["namespace_literals"]) - set(old_scan["namespace_literals"])),
            removed=sorted(set(old_scan["namespace_literals"]) - set(new_scan["namespace_literals"])))
        members[label] = dict(member=member, baseline_sha256=sha(old), candidate_sha256=sha(candidate),
            needed_unchanged=dynamics["u15"]["needed"] == dynamics["u16"]["needed"], dynamics=dynamics,
            open_counts={version: len(data["binaries"][0]["sites"]) for version, data in opens.items()},
            namespace_edges={version: data["binaries"][0]["namespace_edges"] for version, data in opens.items()},
            open_findings={version: data["findings"] for version, data in opens.items()},
            abi_summary={name: len(abi.get(name, [])) for name in ["removed", "added", "drift", "consumer_breaks", "call_diffs"]},
            delta=delta, delta_sha256=static.bundle.digest(delta), approved_by=None)
    reports, comparisons = {}, {}
    for label, root in [("u15", base / "native"), ("u16-pair", PAIR)]:
        reports[label] = {}
        for gate in ["N1", "N2"]:
            name = "u16-a3-native-" + label + "-" + gate
            records.append(capture(name, [sys.executable, MASTER / "scripts/lab/native_predeploy.py", "--package", root,
                "--inputs", root / "native-checks/native-gates.json", "--gate", gate, "--exceptions", registry, "--readelf", "llvm-readelf"]))
            report = json.loads((HERE / ".artifacts/raw" / (name + ".txt")).read_text())
            reports[label][gate] = report
            save("evidence/" + name + ".json", report)
    for gate in ["N1", "N2"]:
        old_rows = reports["u15"][gate].get("gates", {}).get(gate, {}).get("findings", [])
        new_rows = reports["u16-pair"][gate].get("gates", {}).get(gate, {}).get("findings", [])
        def normalize(row):
            return json.dumps({key: value for key, value in row.items() if key not in
                ["issue_id", "package_manifest_sha256", "inputs_sha256", "artifact_sha256", "exception", "decision"]}, sort_keys=True)
        previous, current = Counter(map(normalize, old_rows)), Counter(map(normalize, new_rows))
        comparisons[gate] = dict(baseline_findings=len(old_rows), candidate_findings=len(new_rows),
            exact_nonbinding_equal=sum((previous & current).values()),
            candidate_nonbinding_changes=[json.loads(row) for row in (current - previous).elements()],
            removed_nonbinding_rows=[json.loads(row) for row in (previous - current).elements()])
    after = sha(registry)
    if before != after:
        raise ValueError("Active table changed; retain logs and rerun against one identity")
    save("native-pair-gates.json", dict(execution_enabled=False, rollout_ready=False, actual_os=platform.system(),
        board_access=False, vm_access=False, remote_access=False, active_registry_updated=False,
        active_registry_sha256=before, active_registry_sha256_after=after, records=records, members=members,
        native_manifest_sha256=binding["native_manifest_sha256"], native_inputs_sha256=binding["native_inputs_sha256"],
        consumer_count=219, findings_comparison=comparisons,
        native_reports={label: {gate: dict(exit_code=report["exit_code"], status=report["status"], errors=report["errors"],
            rejected=report.get("gates", {}).get(gate, {}).get("rejected")) for gate, report in row.items()} for label, row in reports.items()},
        native_production_approved=False, registry_delta_applied=False, final_bundle_sha256=None))
    print("U16 pair STATIC COMPLETE: raw exits retained; one disabled native version; no registry writes")


if __name__ == "__main__":
    main()
