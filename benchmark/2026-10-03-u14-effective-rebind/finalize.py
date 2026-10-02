import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from validation import ABI_MEMBER, ABI_TARGET, BASES, FIRST_BUNDLE, INSTALLER_PATHS, OLD_ABI, check_base, check_delta, check_disabled, check_local_plan, check_image_approval

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = Path(os.environ.get("WORKSPACES", REPO.parent))
MASTER = WS / "westlake-harness"
PRIOR = WS / "westlake-harness-bms/benchmark/2026-10-03-u14-final-assembly"
sys.path.insert(0, str(MASTER / "scripts/lab"))
import generation_bundle as bundle_tool
import generation_static_checks as static
import u7_executor as executor


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def portable(value):
    if isinstance(value, dict):
        return {name: portable(item) for name, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [portable(item) for item in value]
    if isinstance(value, Path):
        value = str(value)
    if isinstance(value, str):
        value = value.replace(str(REPO) + "/benchmark/", "$WORKSPACES/westlake-harness-bms/benchmark/")
        for root, token in [(REPO, "$REPO"), (WS, "$WORKSPACES"), (Path.home(), "$HOME")]:
            value = token if value == str(root) else value.replace(str(root) + "/", token + "/")
    return value


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(portable(value), indent=2) + "\n")


def install(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.chmod(destination.stat().st_mode | 0o200)
    shutil.copyfile(source, destination)


def planned_identity(variant, mode="planned-u13"):
    common_path = WS / "westlake-harness-bms/benchmark/2026-10-03-u13-effective-rebind/composition.json"
    local_path = WS / "westlake-harness-bms/benchmark/2026-10-03-u13-61b-effective-base/composition.json"
    source = json.loads(common_path.read_text())
    group = "candidate_boards" if mode == "planned-u13" else "baseline_boards"
    serial = next(name for name in source[group] if name.startswith("61b" if variant == "61b" else "5ea"))
    identity = copy.deepcopy(source[group][serial])
    if variant == "common":
        other = next(row for name, row in source[group].items() if name.startswith("5cd"))
        if other["expected"] != identity["expected"] or other["fingerprints"] != identity["fingerprints"]:
            raise ValueError("5ea/5cd cannot share one effective baseline")
    local = json.loads(local_path.read_text())
    if variant == "61b":
        if local["candidate" if mode == "planned-u13" else "baseline"]["expected"] != identity["expected"]:
            raise ValueError("Common and board-local planned U13 identities differ")
    if executor.fingerprints(identity["expected"], identity["reference_paths"]) != identity["fingerprints"]:
        raise ValueError("Planned U13 fingerprint drift")
    return serial, identity, [dict(path=common_path, sha256=sha(common_path)), dict(path=local_path, sha256=sha(local_path))]


def verify_donor(path, digest, evidence_path):
    if sha(path) != digest or digest == OLD_ABI:
        raise ValueError("Incoming v2 hash mismatch or old v1 selected")
    evidence = json.loads(evidence_path.read_text())
    if evidence.get("artifact_sha256") != digest or evidence.get("build_rc") != [0, 0]:
        raise ValueError("Two successful v2 builds required")
    for group in ["artifacts", "logs", "sources"]:
        members = evidence.get(group, [])
        if len(members) < (2 if group in ["artifacts", "logs"] else 1):
            raise ValueError("Persistent v2 evidence incomplete: " + group)
        for row in members:
            source = Path(row["path"].replace("$WORKSPACES", str(WS)).replace("$REPO", str(REPO)))
            if sha(source) != row["sha256"] or (group == "artifacts" and row["sha256"] != digest):
                raise ValueError("V2 donor evidence hash mismatch")
    if not evidence.get("scan_sources"):
        raise ValueError("Exact compiled v2 scan-source mapping required")
    if not evidence.get("toolchain") or not evidence.get("build_commands"):
        raise ValueError("Frozen toolchain identity and actual build commands required")
    return evidence


def image_approval(output, bundle):
    approval_path = MASTER / "benchmark/2026-10-03-u14-review/outer-approval-image.json"
    draft_path = PRIOR / "image-exception-draft.json"
    approval = json.loads(approval_path.read_text())
    draft = json.loads(draft_path.read_text())
    receipt_path = output / bundle["paired_build_receipt"]["source"]
    receipt = json.loads(receipt_path.read_text())
    check_image_approval(approval, sha(draft_path), receipt["input_jars"], receipt["outputs"], draft)
    release = WS / "westlake-inputs/generations/u14-bt-bake-0349-87cf-v1"
    for name, digest in draft["paired_outputs"].items():
        if sha(release / "run2" / name) != digest:
            raise ValueError("Approved paired image drift")
    first = (output / "boot/arm64/boot.art").read_bytes()
    second = (release / "run2/boot.art").read_bytes()
    start, end = 0x3e3b8, 0x3e3c0
    if len(first) != len(second) or first[:start] != second[:start] or first[end:] != second[end:]:
        raise ValueError("Image differences extend beyond approved interval")
    for name, digest in draft["outputs"].items():
        if name != "boot.art" and digest != draft["paired_outputs"][name]:
            raise ValueError("Another image differs")
    destination = output / "receipts/u14-image-outer-approval.json"
    install(approval_path, destination)
    bundle["image_reproduction_approval"] = dict(source="receipts/u14-image-outer-approval.json", sha256=sha(destination),
        draft_sha256=sha(draft_path), status="approved-exact-pair", interval=["0x3e3b8", "0x3e3c0"])
    save(HERE / "image-approval-binding.json", dict(approval=approval_path, approval_sha256=sha(approval_path),
        draft=draft_path, draft_sha256=sha(draft_path), input_jars=draft["input_jars"], outputs=draft["outputs"],
        paired_outputs=draft["paired_outputs"], approved_by=approval["signer"], approved_at=approval["signed_at"],
        exact_interval=["0x3e3b8", "0x3e3c0"], masked_reproduction_status="PASS-with-exact-outer-exception",
        historical_receipt_unchanged=True, native_approvals_transferred=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=BASES, required=True)
    parser.add_argument("--baseline-mode", choices=["planned-u13", "diagnostic-t8"], default="planned-u13")
    parser.add_argument("--transaction-base", type=Path, required=True)
    parser.add_argument("--transaction-base-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--abi", type=Path)
    parser.add_argument("--abi-sha256")
    parser.add_argument("--abi-evidence", type=Path)
    args = parser.parse_args()
    transaction = args.transaction_base.resolve()
    output = args.out.resolve()
    serial, identity, origins = planned_identity(args.variant, args.baseline_mode)
    check_base(args.variant, args.transaction_base_sha256, sha(transaction / "bundle.json"), identity, args.baseline_mode)
    if output.exists():
        raise ValueError("Output exists; immutable attempt required")
    donor = None
    if any([args.abi, args.abi_sha256, args.abi_evidence]):
        if not all([args.abi, args.abi_sha256, args.abi_evidence]):
            raise ValueError("ABI path, full hash and donor evidence must be supplied together")
        donor = verify_donor(args.abi, args.abi_sha256, args.abi_evidence)
    first = PRIOR / ".artifacts/bundle"
    if sha(first / "bundle.json") != FIRST_BUNDLE:
        raise ValueError("Landed first U14 packet drift")
    _, first_manifest, _ = bundle_tool.validate(first)
    effective_base = static.effective(transaction)
    for target, row in effective_base.items():
        if identity["expected"].get(target) != row["sha256"]:
            raise ValueError("Planned U13 effective baseline disagrees: " + target)
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["/bin/cp", "-cR", first, output], check=True)
    bundle = json.loads((output / "bundle.json").read_text())
    manifest = json.loads((output / "native/package.json").read_text())
    if donor:
        install(args.abi, output / "native" / ABI_MEMBER)
        manifest["files"][ABI_MEMBER] = args.abi_sha256
        manifest["live_hashes"][ABI_TARGET] = args.abi_sha256
        save(output / "native/package.json", manifest)
        scan_path = output / "native/native-checks/scan-manifest.json"
        scan = json.loads(scan_path.read_text())
        for name, row in donor["scan_sources"].items():
            if Path(name).name != name:
                raise ValueError("Invalid scan source filename")
            source = Path(row["path"].replace("$WORKSPACES", str(WS)).replace("$REPO", str(REPO)))
            if sha(source) != row["sha256"]:
                raise ValueError("Compiled scan source changed")
            install(source, scan_path.parent / name)
            scan["sources"][name] = dict(path=name, sha256=row["sha256"], source_sha256=row["sha256"], origin=portable(source), first_line=1)
            if not any(profile.get("source") == name for profile in scan["profiles"]):
                if name != "u14-gecko-ctype.c":
                    raise ValueError("New callable scan profile requires explicit review: " + name)
        for profile in scan["profiles"]:
            profile["identity"]["manifest_sha256"] = sha(output / "native/package.json")
            if profile["identity"].get("artifact") == ABI_MEMBER:
                profile["identity"]["artifact_sha256"] = args.abi_sha256
        save(scan_path, scan)
        gates_path = output / "native/native-checks/native-gates.json"
        gates = json.loads(gates_path.read_text())
        gates["package_manifest_sha256"] = sha(output / "native/package.json")
        gates["initialization"]["manifest"]["sha256"] = sha(scan_path)
        save(gates_path, gates)
        bundle["native"]["manifest"]["sha256"] = sha(output / "native/package.json")
    changes = check_delta(first_manifest["files"], manifest["files"], args.abi_sha256 or OLD_ABI)
    for kind in ["runtime", "boot"]:
        row = bundle["reference"][kind]
        destination = output / row["source"]
        destination.chmod(destination.stat().st_mode | 0o200)
        destination.write_text("\n".join(sorted(identity["expected"][target] + "  " + target for target in identity["reference_paths"][kind])) + "\n")
        row["sha256"] = sha(destination)
    for row in bundle["image_gate_reference"]["members"]:
        baseline = effective_base[row["target"]]
        install(bundle_tool.member(transaction, baseline), output / row["source"])
        row["sha256"] = baseline["sha256"]
    bundle["image_gate_reference"].update(kind="conditional-post-U13-per-board-base", baseline_bundle_sha256=args.transaction_base_sha256)
    bundle["static_checks"]["baseline_bundle_sha256"] = args.transaction_base_sha256
    image_approval(output, bundle)
    bundle.update(rollout_ready=False, rollout_blocker="U13 promotion unconfirmed; v2 donor and outer approvals pending; conditional metadata only")
    save(output / "bundle.json", bundle)
    data, checked, _ = bundle_tool.validate(output)
    check_delta(first_manifest["files"], checked["files"], args.abi_sha256 or OLD_ABI)
    receipt = executor.receipt_check(output, data, checked)
    if receipt["status"] != "verified":
        raise ValueError("Unchanged image paired receipt drift")
    plan = executor.prepare(output, transaction / "native")
    check_local_plan(plan, identity)
    board_local = [dict(target=target, baseline_sha256=identity["expected"][target], expected_sha256=identity["expected"][target], changed=False) for target in INSTALLER_PATHS]
    effective_candidate = static.effective(output)
    candidate = copy.deepcopy(identity)
    for target, row in effective_candidate.items():
        candidate["expected"][target] = row["sha256"]
    new_target = "/system/android/lib64/libicu74compat.so"
    if new_target not in candidate["reference_paths"]["runtime"]:
        candidate["reference_paths"]["runtime"].append(new_target)
        candidate["reference_paths"]["runtime"].sort()
    candidate["fingerprints"] = executor.fingerprints(candidate["expected"], candidate["reference_paths"])
    composition = dict(package=output, variant=args.variant, comparison_base=transaction,
        comparison_base_sha256=args.transaction_base_sha256, transaction_base=transaction,
        transaction_base_sha256=args.transaction_base_sha256, bundle_sha256=sha(output / "bundle.json"),
        native_manifest_sha256=sha(output / "native/package.json"), native_inputs_sha256=sha(output / "native/native-checks/native-gates.json"),
        first_u14_bundle_sha256=FIRST_BUNDLE, changed_artifacts=changes, abi_sha256=args.abi_sha256 or OLD_ABI,
        abi_v2_status="verified-donor" if donor else "pending-not-arrived", donor_evidence=donor,
        paired_receipt_sha256=bundle["paired_build_receipt"]["sha256"], image_rebake=False,
        image_reproduction_approval=bundle["image_reproduction_approval"],
        board_local_members=board_local, reference_board=serial, baseline=identity, candidate=candidate,
        identity_role="planned-post-promotion-base-not-live-signoff", origins=origins,
        promotion_confirmed=False, execution_enabled=False, rollout_ready=False, vm_used=False, device_access=False)
    check_disabled(composition)
    report_root = HERE / (args.variant if args.baseline_mode == "planned-u13" else args.variant + "-diagnostic")
    composition["baseline_mode"] = args.baseline_mode
    save(report_root / "composition.json", composition)
    save(report_root / "transaction-plan.json", plan)
    save(report_root / "manifest.json", manifest)
    save(report_root / "bundle.json", bundle)
    print(args.variant + " bundle=" + composition["bundle_sha256"] + " manifest=" + composition["native_manifest_sha256"] + " inputs=" + composition["native_inputs_sha256"])
    print("promotion_confirmed=false execution_enabled=false abi_v2=" + composition["abi_v2_status"] + " images_unchanged=true installer_operations=0")


if __name__ == "__main__":
    main()
