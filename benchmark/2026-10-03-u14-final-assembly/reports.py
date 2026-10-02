from datetime import datetime
import json
from pathlib import Path
import platform
import re
import sys

from common import BASE, HERE, MASTER, WS, capture, save, sha
from validation import ADDITIONS, CHANGES, check_review
import abi_diff
import auto_approve_exceptions as auto
import generation_bundle as bundle_tool
import generation_static_checks as static
from native_needed_gate import parse_dynamic


def consumers():
    inventory_path = WS / "westlake-harness-bms/benchmark/2026-10-02-toutiao-bionic-scope/consumers.json"
    inventory = json.loads(inventory_path.read_text())
    member_root = inventory_path.parent / ".artifacts/members"
    selected = {member["sha256"]: member_root / (member["sha256"] + ".so") for app in inventory["apps"] for member in app["members"] if member["status"] == "ELF64-AArch64" and member["imports"]}
    for key in ["vlc", "fd-fennec_fdroid", "firefox", "ppsspp"]:
        for path in (WS / "westlake-harness-bms/benchmark/2026-10-02-u12-disappeared/.artifacts").glob(key + "-*.so"):
            selected[sha(path)] = path
    if len(selected) != 219 or any(sha(path) != digest for digest, path in selected.items()):
        raise ValueError("Pinned 219-member consumer set changed")
    return selected


def main():
    if platform.system() != "Darwin":
        raise ValueError("Mac-only static task during U13 windows")
    composition = json.loads((HERE / "final-composition.json").read_text())
    package = Path(composition["package"].replace("$WORKSPACES", str(WS)).replace("$REPO", str(HERE.parents[1])))
    if sha(package / "bundle.json") != composition["bundle_sha256"]:
        raise ValueError("Composed bundle changed")
    data, manifest, _ = bundle_tool.validate(package)
    old_manifest = json.loads((BASE / "native/package.json").read_text())
    records = []
    native_reports = {}
    for label, root in [("u13", BASE / "native"), ("u14", package / "native")]:
        records.append(capture("native-" + label, [sys.executable, MASTER / "scripts/lab/native_predeploy.py", "--package", root,
            "--inputs", root / "native-checks/native-gates.json", "--readelf", "llvm-readelf"]))
        report = json.loads((HERE / ".artifacts/raw" / ("native-" + label + ".txt")).read_text())
        if report["errors"]:
            raise ValueError("Native report invalid: " + str(report["errors"]))
        native_reports[label] = report
        save("evidence/native-" + label + ".json", report, compact=True)
    registry = json.loads((MASTER / "knowledge/gates/native-predeploy-exceptions.json").read_text())
    matched, new = auto.classify(native_reports["u14"], [native_reports["u13"]], registry["exceptions"])
    preview = []
    for gate, finding, prior in matched:
        preview.append(dict(gate=gate, issue_id=finding["issue_id"], package_manifest_sha256=composition["native_manifest_sha256"], inputs_sha256=composition["native_inputs_sha256"],
            reason="Same approved U13 finding, binding preview only; active registry unchanged", approved_by="auto-identical(outer rule 2026-10-01)", approved_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            removal_condition=prior["removal_condition"], evidence=["benchmark/2026-10-03-u14-final-assembly/evidence/native-u13.json", "benchmark/2026-10-03-u14-final-assembly/evidence/native-u14.json"],
            auto_from=dict(package_manifest_sha256=prior["package_manifest_sha256"], issue_id=prior["issue_id"])))
    save("registry-delta.json", dict(schema_version=1, exceptions=preview, applied=False, execution_enabled=False))
    review = dict(package_manifest_sha256=composition["native_manifest_sha256"], inputs_sha256=composition["native_inputs_sha256"],
        new_findings=[dict(gate=gate, **finding) for gate, finding, _ in new], applied=False, approved_by=None, execution_enabled=False)
    save("needs-outer-review.json", review)
    records.append(capture("auto-identical-preview", [sys.executable, MASTER / "scripts/lab/auto_approve_exceptions.py", "--candidate", HERE / "evidence/native-u14.json", "--baseline", HERE / "evidence/native-u13.json"]))
    production_static = static.check(package, BASE, {})
    save("evidence/static-vs-u13.json", production_static, compact=True)
    changed = []
    selected = consumers()
    save("consumer-set.json", dict(count=len(selected), members=[dict(source=path, sha256=digest) for digest, path in sorted(selected.items())],
        scope="Import intersection against each replaced provider; no assertion of namespace visibility or app gains"))
    seen_pairs = set()
    inputs = json.loads((package / "native/native-checks/native-gates.json").read_text())
    providers = [(package / "native" / name, name) for name in manifest["files"] if name.endswith(".so")]
    providers += [(package / "native/native-checks" / row["path"], row["target"]) for row in inputs["namespaces"]["system_files"]]
    symbol_cache = {}
    import_rows = []
    for member, digest in (CHANGES | ADDITIONS).items():
        candidate = package / "native" / member
        old = BASE / "native" / member
        label = member.removeprefix("payload/").replace("/", "-").replace(".so", "")
        if candidate.suffix == ".jar":
            records.append(capture("class-" + label, [sys.executable, MASTER / "scripts/lab/deployed_class_diff.py", candidate, "--deployed", old, "--frozen"]))
            continue
        previous_sha = old_manifest["files"].get(member)
        pair = (previous_sha, digest)
        if pair in seen_pairs:
            changed.append(dict(member=member, old_sha256=previous_sha, sha256=digest, same_pair_alias=True))
            continue
        seen_pairs.add(pair)
        records.append(capture("whois-" + label, [sys.executable, MASTER / "scripts/lab/deployed_whois.py", Path(member).name]))
        scans = {}
        for version, path in [("u14", candidate)] + ([("u13", old)] if old.exists() else []):
            output = HERE / ".artifacts" / ("open-" + label + "-" + version + ".json")
            records.append(capture("open-" + label + "-" + version, [sys.executable, MASTER / "scripts/lab/open_site_scan.py", path, "--json", output]))
            scans[version] = json.loads(output.read_text())
            save("evidence/open-" + label + "-" + version + ".json", scans[version])
            records.append(capture("dynamic-" + label + "-" + version, ["llvm-readelf", "-d", "--wide", path]))
            records.append(capture("dynsym-" + label + "-" + version, ["llvm-readelf", "--dyn-syms", "--wide", path]))
        if old.exists():
            records.append(capture("strings-" + label, [sys.executable, MASTER / "scripts/lab/deployed_strings_diff.py", candidate, "--deployed", old]))
            abi_output = HERE / ".artifacts" / ("abi-" + label + ".json")
            records.append(capture("abi-consumers-" + label, [sys.executable, MASTER / "scripts/lab/abi_diff.py", "--old", old, "--new", candidate, "--calls", "--json", abi_output,
                *[item for path in selected.values() for item in ["--consumer", path]]]))
            save("evidence/abi-" + label + ".json", json.loads(abi_output.read_text()), compact=True)
            new_imports = sorted(abi_diff.symbols(candidate, defined=False) - abi_diff.symbols(old, defined=False))
        else:
            new_imports = sorted(abi_diff.symbols(candidate, defined=False))
        dynamic = parse_dynamic((HERE / ".artifacts/raw" / ("dynamic-" + label + "-u14.txt")).read_text())
        matches = []
        for symbol in new_imports:
            direct = []
            for provider_path, target in providers:
                if Path(target).name not in dynamic["needed"]:
                    continue
                if provider_path not in symbol_cache:
                    symbol_cache[provider_path] = abi_diff.symbols(provider_path)
                if symbol in symbol_cache[provider_path]:
                    direct.append(dict(target=target, sha256=sha(provider_path)))
            dynsym = (HERE / ".artifacts/raw" / ("dynsym-" + label + "-u14.txt")).read_text()
            weak = any(" WEAK " in line and " UND " in line and re.search(r"\b" + re.escape(symbol) + r"(?:@[^ ]*)?\s*$", line) for line in dynsym.splitlines())
            matches.append(dict(symbol=symbol, weak=weak, required_for_relocation=not weak, direct_needed_exporters=direct, byte_provider_found=bool(direct), namespace_resolution="not proven by export intersection"))
        import_rows.append(dict(member=member, needed=dynamic["needed"], new_undefined=matches,
            needed_unchanged=old.exists() and dynamic["needed"] == parse_dynamic((HERE / ".artifacts/raw" / ("dynamic-" + label + "-u13.txt")).read_text())["needed"]))
        changed.append(dict(member=member, old_sha256=previous_sha, sha256=digest, scans={version: dict(sites=len(scan["binaries"][0]["sites"]), namespace_edges=scan["binaries"][0]["namespace_edges"], findings=scan["findings"]) for version, scan in scans.items()},
            new_native=not old.exists()))
    save("imports.json", dict(rows=import_rows, all_new_imports_have_byte_provider=all(row["byte_provider_found"] for group in import_rows for row in group["new_undefined"]),
        all_new_strong_imports_have_byte_provider=all(row["byte_provider_found"] for group in import_rows for row in group["new_undefined"] if row["required_for_relocation"])))
    save("open-summary.json", dict(members=changed, scanner_diagnostics_unchanged=True, approved_by=None))
    records.append(capture("rb", [sys.executable, MASTER / "knowledge/toolchains/art-r155/check_boot_oat_rb.py", package / "boot/arm64/boot.oat", "--image", package / "boot/arm64/boot.art"]))
    t4b_output = HERE / ".artifacts" / ("t4b-" + datetime.now().strftime("%Y%m%dT%H%M%S%f") + ".json")
    records.append(capture("t4b", [sys.executable, MASTER / "knowledge/toolchains/art-r155/t4b_build_switch_gate.py", "--libart", package / "native/payload/route/libart.so", "--oat", package / "boot/arm64/boot.oat", "--build", HERE / "inputs/U14-BUILD.md", "--out", t4b_output]))
    save("evidence/t4b.json", json.loads(t4b_output.read_text()))
    records.append(capture("frozen", [sys.executable, MASTER / "scripts/lab/check_frozen.py", "--package", package / "native"]))
    check_review(records, review)
    save("report-summary.json", dict(records=records, actual_os=platform.system(), architecture=platform.machine(),
        bundle_sha256=composition["bundle_sha256"], native_manifest_sha256=composition["native_manifest_sha256"], native_inputs_sha256=composition["native_inputs_sha256"], comparison_base_sha256=composition["comparison_base_sha256"],
        native_baseline=native_reports["u13"]["status"], native_candidate=native_reports["u14"]["status"], native_errors=[],
        auto_identical_count=len(matched), new_findings_count=len(new), new_findings_by_gate={gate: sum(selected_gate == gate for selected_gate, _, _ in new) for gate in ["N1", "N2"]},
        static_vs_u13=production_static["status"], consumers=219, active_registry_written=False, approvals_applied=False, vm_replay="deferred outer after window", production_run=False, device_access=False, execution_enabled=False))
    print("NATIVE=" + native_reports["u14"]["status"] + " auto_identical=" + str(len(matched)) + " new=" + str(len(new)))
    print("STATIC_U13=" + production_static["status"] + " consumers=219 production=false vm=false disabled=true")


if __name__ == "__main__":
    main()
