from datetime import datetime
import json
import platform
import shutil
import sys

from common import BASE, HERE, MASTER, PARTIAL, WS, capture, save, sha
from validation import CHANGES, check_review
import auto_approve_exceptions as auto
import generation_bundle
import generation_static_checks as static
from native_needed_gate import parse_dynamic


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
        raise ValueError("Pinned 219-member consumer inventory changed")
    return selected


def main():
    if platform.system() != "Darwin":
        raise ValueError("Mac-only static task; VM prohibited during windows")
    composition = json.loads((HERE / "composition.json").read_text())
    registry_path = MASTER / "knowledge/gates/native-predeploy-exceptions.json"
    registry_sha = sha(registry_path)
    registry_snapshot = HERE / ".artifacts/registry-snapshot.json"
    shutil.copyfile(registry_path, registry_snapshot)
    registry = json.loads(registry_snapshot.read_text())
    records = []
    native_reports = {}
    for label, root in [("u14", BASE / "native"), ("u15", PARTIAL / "native")]:
        records.append(capture("native-" + label, [sys.executable, MASTER / "scripts/lab/native_predeploy.py", "--package", root,
            "--inputs", root / "native-checks/native-gates.json", "--exceptions", registry_snapshot, "--readelf", "llvm-readelf"]))
        report = json.loads((HERE / ".artifacts/raw" / ("native-" + label + ".txt")).read_text())
        native_reports[label] = report
        save("evidence/native-" + label + ".json", report)
    matched, new = auto.classify(native_reports["u15"], [native_reports["u14"]], registry["exceptions"])
    evidence = ["benchmark/2026-10-03-u15-native-v2/evidence/native-" + label + ".json" for label in ["u14", "u15"]]
    preview = [dict(gate=gate, issue_id=finding["issue_id"], package_manifest_sha256=composition["native_manifest_sha256"],
        inputs_sha256=composition["native_inputs_sha256"], reason="Same approved U14 finding; draft binding preview only, not applied",
        approved_by="auto-identical(outer rule 2026-10-01)", approved_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        removal_condition=prior["removal_condition"], evidence=evidence,
        auto_from=dict(package_manifest_sha256=prior["package_manifest_sha256"], issue_id=prior["issue_id"])) for gate, finding, prior in matched]
    save("registry-delta.json", dict(schema_version=1, exceptions=preview, applied=False, execution_enabled=False))
    save("needs-outer-review.json", dict(package_manifest_sha256=composition["native_manifest_sha256"], inputs_sha256=composition["native_inputs_sha256"],
        new_findings=[dict(gate=gate, **finding) for gate, finding, _ in new], applied=False, approved_by=None,
        errors=native_reports["u15"]["errors"], scope="native-only draft; final BCP/manifest binding still pending"))
    selected = consumers()
    save("consumer-set.json", dict(count=len(selected), members=[dict(source=path, sha256=digest) for digest, path in sorted(selected.items())],
        scope="UND intersections only, not namespace accessibility or first-wall movement"))
    rows = []
    seen = set()
    for member, digest in CHANGES.items():
        if digest in seen:
            continue
        seen.add(digest)
        old = BASE / "native" / member
        candidate = PARTIAL / "native" / member
        label = "host" if member.endswith("appspawn-x") else "anl" if "libapp_native_loader" in member else "flutter" if "westlake_flutter" in member else "runtime"
        records.append(capture("whois-" + label, [sys.executable, MASTER / "scripts/lab/deployed_whois.py", old.name]))
        scans = {}
        dynamics = {}
        for version, path in [("u14", old), ("u15", candidate)]:
            output = HERE / ".artifacts" / ("open-" + label + "-" + version + ".json")
            records.append(capture("open-" + label + "-" + version, [sys.executable, MASTER / "scripts/lab/open_site_scan.py", path, "--json", output]))
            scans[version] = json.loads(output.read_text())
            save("evidence/open-" + label + "-" + version + ".json", scans[version])
            records.append(capture("dynamic-" + label + "-" + version, ["llvm-readelf", "-d", "--wide", path]))
            dynamics[version] = parse_dynamic((HERE / ".artifacts/raw" / ("dynamic-" + label + "-" + version + ".txt")).read_text())
            records.append(capture("dynsym-" + label + "-" + version, ["llvm-readelf", "--dyn-syms", "--wide", path]))
        records.append(capture("strings-" + label, [sys.executable, MASTER / "scripts/lab/deployed_strings_diff.py", candidate, "--deployed", old]))
        output = HERE / ".artifacts" / ("abi-" + label + ".json")
        records.append(capture("abi-" + label, [sys.executable, MASTER / "scripts/lab/abi_diff.py", "--old", old, "--new", candidate, "--calls", "--json", output,
            *[value for path in selected.values() for value in ["--consumer", path]]]))
        abi = json.loads(output.read_text())
        save("evidence/abi-" + label + ".json", abi)
        old_scan, new_scan = static.scan(old), static.scan(candidate)
        delta = static.site_delta(old_scan["binaries"][0]["sites"], new_scan["binaries"][0]["sites"])
        delta["namespace_api_changes"] = {name: dict(deployed=old_scan["namespace_api_calls"].get(name, []), candidate=new_scan["namespace_api_calls"].get(name, []))
            for name in sorted(old_scan["namespace_api_calls"].keys() | new_scan["namespace_api_calls"].keys())
            if old_scan["namespace_api_calls"].get(name) != new_scan["namespace_api_calls"].get(name)}
        delta["namespace_literal_changes"] = dict(added=sorted(set(new_scan["namespace_literals"]) - set(old_scan["namespace_literals"])),
            removed=sorted(set(old_scan["namespace_literals"]) - set(new_scan["namespace_literals"])))
        changed = bool(delta["added"] or delta["removed"] or delta["namespace_api_changes"] or any(delta["namespace_literal_changes"].values()))
        rows.append(dict(object=label, aliases=[name for name, value in CHANGES.items() if value == digest],
            deployed_sha256=sha(old), candidate_sha256=digest, dynamic=dynamics, needed_unchanged=dynamics["u14"]["needed"] == dynamics["u15"]["needed"],
            open_sites={version: len(data["binaries"][0]["sites"]) for version, data in scans.items()},
            namespace_edges={version: data["binaries"][0]["namespace_edges"] for version, data in scans.items()},
            findings={version: data["findings"] for version, data in scans.items()}, open_site_delta=delta, delta_sha256=generation_bundle.digest(delta),
            static_status="REVIEW_REQUIRED" if changed else "PASS_NO_OPEN_DELTA", approved_by=None,
            abi_summary={name: len(abi.get(name, [])) for name in ["removed", "added", "drift", "consumer_breaks", "call_diffs"]}))
    records.append(capture("frozen-native-only", [sys.executable, MASTER / "scripts/lab/check_frozen.py", "--package", PARTIAL / "native"]))
    save("static-deltas.json", dict(schema="u15-native-static-draft/v1", members=rows, approved_by=None, applied=False,
        production_schema="added/removed/namespace_api_changes/namespace_literal_changes identical to generation_static_checks delta hashing", 
        full_bundle_static="PENDING NSD BCP and paired images; no bundle descriptor"))
    summary = dict(records=records, native_baseline=native_reports["u14"]["status"], native_candidate=native_reports["u15"]["status"],
        native_errors=native_reports["u15"]["errors"], identical_preview_count=len(preview),
        new_findings_by_gate={gate: sum(selected_gate == gate for selected_gate, _, _ in new) for gate in ["N1", "N2"]},
        consumer_count=len(selected), abi={row["object"]: row["abi_summary"] for row in rows},
        namespace_inventory_rule="N2 closes each private domain without inheritance; package lists separately cross-checked",
        active_registry_sha256=registry_sha, registry_sha256_after=sha(registry_path), active_registry_updated=False,
        approvals_applied=False, execution_enabled=False, production_run=False, image_bake_run=False,
        native_manifest_sha256=composition["native_manifest_sha256"], native_inputs_sha256=composition["native_inputs_sha256"],
        actual_os=platform.system(), vm_used=False, device_access=False)
    check_review(summary)
    save("report-summary.json", summary)
    print("U15 NATIVE=" + summary["native_candidate"] + " auto-identical-preview=" + str(len(preview)) + " new=" + str(summary["new_findings_by_gate"]))
    print("consumer_count=219; raw string/call deltas retained; full-bundle/image/production gates pending; no approvals applied")


if __name__ == "__main__":
    main()
