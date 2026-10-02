from datetime import datetime
import json
import platform
import sys

from common import ASSEMBLY_BASE, BRIDGE, HERE, INTERMEDIATE, MASTER, capture, expand, save, sha
import abi_diff
import auto_approve_exceptions as auto
import generation_bundle as bundle_tool
import generation_static_checks as static
from native_needed_gate import parse_dynamic


def main():
    if platform.system() != "Darwin":
        raise ValueError("This task is Mac-only during the U13 window")
    composition = json.loads((HERE / "composition.json").read_text())
    package = expand(composition["package"])
    transaction_base = expand(composition["transaction_base"])
    if sha(package / "bundle.json") != composition["bundle_sha256"]:
        raise ValueError("Draft changed")
    old = ASSEMBLY_BASE / "native/payload/android/lib64/liboh_adapter_bridge.so"
    candidate = package / "native/payload/android/lib64/liboh_adapter_bridge.so"
    records = [capture("deployed-whois", [sys.executable, MASTER / "scripts/lab/deployed_whois.py", "liboh_adapter_bridge.so"])]
    scans = {}
    for name, path in [("u13", old), ("e34", INTERMEDIATE), ("candidate", candidate)]:
        output = HERE / ".artifacts" / ("open-" + name + ".json")
        records.append(capture("open-" + name, [sys.executable, MASTER / "scripts/lab/open_site_scan.py", path, "--json", output]))
        scans[name] = json.loads(output.read_text())
        save("evidence/open-" + name + ".json", scans[name])
        records.append(capture("dynamic-" + name, ["llvm-readelf", "-d", "--wide", path]))
        records.append(capture("dynsym-" + name, ["llvm-readelf", "--dyn-syms", "--wide", path]))
    for label, baseline, replacement in [("846-to-e34", old, INTERMEDIATE), ("e34-to-candidate", INTERMEDIATE, candidate), ("846-to-candidate", old, candidate)]:
        records.append(capture("strings-" + label, [sys.executable, MASTER / "scripts/lab/deployed_strings_diff.py", replacement, "--deployed", baseline]))
        records.append(capture("equiv-" + label, [sys.executable, MASTER / "benchmark/2026-10-02-u14-bridge-r1r3/equiv.py", baseline, replacement, "--show"]))
    abi_output = HERE / ".artifacts/abi.json"
    records.append(capture("abi-calls", [sys.executable, MASTER / "scripts/lab/abi_diff.py", "--old", old, "--new", candidate, "--calls", "--json", abi_output]))
    save("evidence/abi-calls.json", json.loads(abi_output.read_text()))
    inputs = json.loads((package / "native/native-checks/native-gates.json").read_text())
    provider = next(row for row in inputs["namespaces"]["system_files"] if row["target"].endswith("/libwindow_scene_common.z.so"))
    provider_path = package / "native/native-checks" / provider["path"]
    if sha(provider_path) != provider["sha256"]:
        raise ValueError("Pinned direct provider changed")
    records.append(capture("zlevel-provider-dynsym", ["llvm-readelf", "--dyn-syms", "--wide", provider_path]))
    old_undefined = abi_diff.symbols(old, defined=False)
    new_undefined = abi_diff.symbols(candidate, defined=False)
    new_imports = sorted(new_undefined - old_undefined)
    intermediate_undefined = abi_diff.symbols(INTERMEDIATE, defined=False)
    patch_imports = sorted(new_undefined - intermediate_undefined)
    inherited_imports = sorted(intermediate_undefined - old_undefined)
    old_dynamic = parse_dynamic((HERE / ".artifacts/raw/dynamic-u13.txt").read_text())
    new_dynamic = parse_dynamic((HERE / ".artifacts/raw/dynamic-candidate.txt").read_text())
    defined = abi_diff.symbols(provider_path)
    import_ok = len(patch_imports) == 1 and "SetSubWindowZLevel" in patch_imports[0] and patch_imports[0] in defined
    import_ok = import_ok and set(new_imports) == set(patch_imports + inherited_imports) and len(inherited_imports) == 3
    if old_dynamic["needed"] != new_dynamic["needed"] or not import_ok or "libwindow_scene_common.z.so" not in new_dynamic["needed"]:
        raise ValueError("Unexpected bridge imports or direct-provider mismatch")
    provider_evidence = []
    for soname in ["libwindow_scene_common.z.so", "libdm.z.so"]:
        entry = next(row for row in inputs["namespaces"]["system_files"] if row["target"].endswith("/" + soname))
        path = package / "native/native-checks" / entry["path"]
        if sha(path) != entry["sha256"] or soname not in new_dynamic["needed"]:
            raise ValueError("Direct inherited provider drift")
        exports = abi_diff.symbols(path)
        owned = sorted(set(new_imports) & exports)
        provider_evidence.append(dict(**entry, matched_imports=owned))
        records.append(capture("provider-" + soname, ["llvm-readelf", "--dyn-syms", "--wide", path]))
    if set(new_imports) != {symbol for entry in provider_evidence for symbol in entry["matched_imports"]}:
        raise ValueError("Unresolved inherited import")
    save("imports.json", dict(needed_unchanged_ordered=True, needed=new_dynamic["needed"], needed_count=len(new_dynamic["needed"]),
        new_undefined=new_imports, inherited_e34_imports=inherited_imports, patch_new_undefined=patch_imports,
        removed_undefined=sorted(old_undefined-new_undefined), provider=provider, all_new_import_providers=provider_evidence,
        provider_export_matches=True, new_import_is_direct_needed=True, factory_copy_read_only=True,
        exports_removed=sorted(abi_diff.symbols(old)-abi_diff.symbols(candidate)), exports_added=sorted(abi_diff.symbols(candidate)-abi_diff.symbols(old))))
    delta = static.site_delta(scans["u13"]["binaries"][0]["sites"], scans["candidate"]["binaries"][0]["sites"])
    save("open-delta.json", dict(delta=delta, old_sites=len(scans["u13"]["binaries"][0]["sites"]), new_sites=len(scans["candidate"]["binaries"][0]["sites"]),
        old_namespace_edges=scans["u13"]["binaries"][0]["namespace_edges"], candidate_namespace_edges=scans["candidate"]["binaries"][0]["namespace_edges"]))
    native_reports = {}
    for name, root in [("u13", ASSEMBLY_BASE / "native"), ("candidate", package / "native")]:
        records.append(capture("native-" + name, [sys.executable, MASTER / "scripts/lab/native_predeploy.py", "--package", root,
            "--inputs", root / "native-checks/native-gates.json", "--readelf", "llvm-readelf"]))
        report = json.loads((HERE / ".artifacts/raw" / ("native-" + name + ".txt")).read_text())
        if report["errors"]:
            raise ValueError("Native gate invalid: " + str(report["errors"]))
        native_reports[name] = report
        save("evidence/native-" + name + ".json", report, compact=True)
    registry = json.loads((MASTER / "knowledge/gates/native-predeploy-exceptions.json").read_text())
    matched, new = auto.classify(native_reports["candidate"], [native_reports["u13"]], registry["exceptions"])
    mappings = []
    for gate, finding, prior in matched:
        mappings.append(dict(gate=gate, package_manifest_sha256=native_reports["candidate"]["package_manifest_sha256"],
            inputs_sha256=native_reports["candidate"]["inputs_sha256"], issue_id=finding["issue_id"],
            reason="Identical prior approved U13 finding; offline rebind preview only",
            evidence=["benchmark/2026-10-03-u14-native-assembly/evidence/native-candidate.json", "benchmark/2026-10-03-u14-native-assembly/evidence/native-u13.json"],
            removal_condition=prior["removal_condition"], approved_by="auto-identical(outer rule 2026-10-01)", approved_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            auto_from=dict(package_manifest_sha256=prior["package_manifest_sha256"], issue_id=prior["issue_id"])))
    save("registry-delta.json", dict(schema_version=1, exceptions=mappings, applied=False, execution_enabled=False))
    save("needs-outer-review.json", dict(new_findings=[dict(gate=gate, **finding) for gate, finding, _ in new],
        approved_by=None, package_manifest_sha256=native_reports["candidate"]["package_manifest_sha256"],
        inputs_sha256=native_reports["candidate"]["inputs_sha256"], new_coverage=True,
        reason="Old U13 N1 manifest has no bridge source profile; candidate adds namespace sources and bounded M6 callback JNI cache coverage"))
    records.append(capture("auto-identical-preview", [sys.executable, MASTER / "scripts/lab/auto_approve_exceptions.py", "--candidate",
        HERE / "evidence/native-candidate.json", "--baseline", HERE / "evidence/native-u13.json"]))
    static_report = static.check(package, ASSEMBLY_BASE, {})
    save("evidence/static-vs-u13.json", static_report, compact=True)
    transaction_policy = json.loads(bundle_tool.member(package, json.loads((package / "bundle.json").read_text())["static_checks"]["policy"]).read_text())
    transaction_report = static.check(package, transaction_base, transaction_policy)
    save("evidence/static-vs-transaction.json", transaction_report, compact=True)
    save("report-summary.json", dict(records=records, actual_os=platform.system(), architecture=platform.machine(), assembly_base_sha256=composition["assembly_base_sha256"],
        transaction_base_sha256=composition["transaction_base_sha256"], bundle_sha256=sha(package / "bundle.json"),
        imports_verified=True, open_site_delta=delta, static_vs_u13=static_report["status"], static_vs_transaction=transaction_report["status"],
        native_baseline=native_reports["u13"]["status"], native_candidate=native_reports["candidate"]["status"], auto_identical_count=len(matched),
        new_findings_count=len(new), new_findings_by_gate={gate: sum(selected == gate for selected, _, _ in new) for gate in ["N1", "N2"]},
        active_registry_written=False, vm_replay="deferred", production_run=False, device_access=False, execution_enabled=False))
    print("IMPORTS needed35=unchanged new_vs846=4 inherited_e34=3 patch_new=SetSubWindowZLevel provider=" + provider["sha256"][:12])
    print("OPEN sites=" + str(len(scans["candidate"]["binaries"][0]["sites"])) + " added=" + str(len(delta["added"])) + " removed=" + str(len(delta["removed"])))
    print("NATIVE candidate=" + native_reports["candidate"]["status"] + " auto_identical=" + str(len(matched)) + " new=" + str(len(new)))
    print("STATIC assembly=" + static_report["status"] + " transaction=" + transaction_report["status"] + " vm=deferred disabled=true")


if __name__ == "__main__":
    main()
