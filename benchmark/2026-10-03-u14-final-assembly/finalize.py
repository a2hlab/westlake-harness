import argparse
import copy
import json
from pathlib import Path
import shutil
import subprocess

from common import BASE, BASE_SHA, HERE, PARTIAL, RELEASE, save, sha
from compose import install
from validation import IMAGES, check_receipt, check_transaction
import generation_bundle as bundle_tool
import generation_static_checks as static
import u7_executor as executor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--transaction-base", type=Path, required=True)
    parser.add_argument("--transaction-base-sha256", required=True)
    parser.add_argument("--board-baseline", type=Path, required=True)
    parser.add_argument("--reference-board")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    transaction = args.transaction_base.resolve()
    output = args.out.resolve()
    check_transaction(transaction, args.transaction_base_sha256, sha(transaction / "bundle.json"))
    if output.exists() or sha(BASE / "bundle.json") != BASE_SHA:
        raise ValueError("Output exists or content base changed")
    baseline_data = json.loads(args.board_baseline.read_text())
    boards = baseline_data.get("boards", baseline_data.get("baseline_boards"))
    if not boards or len(boards) != 3:
        raise ValueError("Signed three-board baseline evidence required")
    previous = json.loads((BASE.parents[1] / "composition.json").read_text())
    effective_base = static.effective(transaction)
    paths = {}
    for serial, board in boards.items():
        paths[serial] = board.get("reference_paths") or {kind: [target for target in members if target in board["expected"]] for kind, members in previous["candidate_boards"][serial]["reference_paths"].items()}
        if executor.fingerprints(board["expected"], paths[serial]) != board["fingerprints"]:
            raise ValueError("Signed board baseline fingerprint drift")
        for target, row in effective_base.items():
            if board["expected"].get(target) != row["sha256"]:
                raise ValueError("Explicit transaction baseline disagrees: " + target)
    receipt = json.loads((HERE / ".artifacts/receipts/paired-run1.json").read_text())
    check_receipt(receipt, receipt["input_jars"], {name: sha(RELEASE / "run1" / name) for name in IMAGES})
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["/bin/cp", "-cR", BASE, output], check=True)
    for directory in ["native", "framework"]:
        shutil.rmtree(output / directory)
        subprocess.run(["/bin/cp", "-cR", PARTIAL / directory, output / directory], check=True)
    manifest = json.loads((output / "native/package.json").read_text())
    bundle = json.loads((BASE / "bundle.json").read_text())
    changed_images = []
    for row in bundle["boot_group"]["members"]:
        name = Path(row["source"]).name
        if name in IMAGES:
            source = RELEASE / "run1" / name
            install(source, output / row["source"])
            install(source, output / "native/payload/android/framework/arm64" / name)
            manifest["files"]["payload/android/framework/arm64/" + name] = sha(source)
            manifest["live_hashes"][row["target"]] = sha(source)
            if row["sha256"] != sha(source):
                changed_images.append(name)
            row["sha256"] = sha(source)
        elif name == "adapter-mainline-stubs.jar":
            row["sha256"] = sha(output / row["source"])
    bundle["runtime_jar"]["sha256"] = sha(output / bundle["runtime_jar"]["source"])
    manifest.update(variant="U14 single native/JAR/27-image batch; offline review only", rollout_ready=False,
        rollout_blocker="Fresh N1/N2/static approvals and new U14 paired-byte exception pending; transaction base must be rebound after promotion")
    save(output / "native/package.json", manifest)
    checks = output / "native/native-checks"
    scan = json.loads((checks / "scan-manifest.json").read_text())
    for profile in scan["profiles"]:
        profile["identity"]["manifest_sha256"] = sha(output / "native/package.json")
    save(checks / "scan-manifest.json", scan)
    inputs = json.loads((checks / "native-gates.json").read_text())
    inputs["package_manifest_sha256"] = sha(output / "native/package.json")
    inputs["initialization"]["manifest"]["sha256"] = sha(checks / "scan-manifest.json")
    save(checks / "native-gates.json", inputs)
    bundle["native"]["manifest"]["sha256"] = sha(output / "native/package.json")
    selected_receipt = output / "receipts/u14-paired-build.json"
    install(HERE / ".artifacts/receipts/paired-run1.json", selected_receipt)
    bundle["paired_build_receipt"] = dict(source="receipts/u14-paired-build.json", sha256=sha(selected_receipt))
    bundle["static_checks"]["baseline_bundle_sha256"] = args.transaction_base_sha256
    policy_path = output / bundle["static_checks"]["policy"]["source"]
    save(policy_path, dict(schema_version=1, native={}, jars={}, execution_enabled=False, reason="U14 fresh review; no U13 or U12 pair approvals implicitly transferred"))
    bundle["static_checks"]["policy"]["sha256"] = sha(policy_path)
    serial = args.reference_board or next(iter(boards))
    if serial not in boards:
        raise ValueError("Reference board not in signed identity evidence")
    for kind in ["runtime", "boot"]:
        row = bundle["reference"][kind]
        destination = output / row["source"]
        destination.chmod(destination.stat().st_mode | 0o200)
        destination.write_text("\n".join(sorted(boards[serial]["expected"][target] + "  " + target for target in paths[serial][kind])) + "\n")
        row["sha256"] = sha(destination)
    for row in bundle["image_gate_reference"]["members"]:
        base_row = effective_base[row["target"]]
        install(bundle_tool.member(transaction, base_row), output / row["source"])
        row["sha256"] = base_row["sha256"]
    bundle["image_gate_reference"].update(kind="explicit-signed-transaction-baseline", baseline_bundle_sha256=args.transaction_base_sha256)
    bundle.update(rollout_ready=False, rollout_blocker="U14 complete bytes, disabled pending outer review, repro exception and promotion-specific transaction rebind")
    save(output / "bundle.json", bundle)
    data, actual, _ = bundle_tool.validate(output)
    receipt_result = executor.receipt_check(output, data, actual)
    if receipt_result["status"] != "verified":
        raise ValueError("Actual paired build receipt not accepted")
    plan = executor.prepare(output, transaction / "native")
    if data.get("rollout_ready") or plan.get("deployable", False):
        raise ValueError("U14 draft unexpectedly deployable")
    candidates = copy.deepcopy(previous["candidate_boards"])
    effective_candidate = static.effective(output)
    for candidate in candidates.values():
        for target, row in effective_candidate.items():
            candidate["expected"][target] = row["sha256"]
        new_target = "/system/android/lib64/libicu74compat.so"
        if new_target not in candidate["reference_paths"]["runtime"]:
            candidate["reference_paths"]["runtime"].append(new_target)
            candidate["reference_paths"]["runtime"].sort()
        candidate["fingerprints"] = executor.fingerprints(candidate["expected"], candidate["reference_paths"])
    composition = dict(package=output, comparison_base=BASE, comparison_base_sha256=BASE_SHA,
        transaction_base=transaction, transaction_base_sha256=args.transaction_base_sha256, reference_board=serial, transaction_baseline_evidence=args.board_baseline,
        transaction_baseline_evidence_sha256=sha(args.board_baseline), transaction_binding_status="pre-promotion diagnostic parameter; no board activation; rebind per-board after U13 promotion",
        bundle_sha256=sha(output / "bundle.json"), native_manifest_sha256=sha(output / "native/package.json"), native_inputs_sha256=sha(checks / "native-gates.json"),
        paired_receipt_sha256=sha(selected_receipt), paired_receipt_status=receipt_result["status"], reproduction_status="REJECT pending exact U14 exception",
        changed_images=sorted(changed_images), selected_run=1, all_27_images_from_actual_u14_build=True, candidate_boards=candidates, baseline_boards=boards,
        execution_enabled=False, rollout_ready=False, final_bytes_complete=True, device_access=False, vm_used=False)
    save("final-composition.json", composition)
    save("transaction-plan.json", plan)
    for name, source in [("bundle.json", output / "bundle.json"), ("native-manifest.json", output / "native/package.json"), ("native-inputs.json", checks / "native-gates.json"), ("scan-manifest.json", checks / "scan-manifest.json")]:
        save("manifests/final-" + name, json.loads(source.read_text()))
    print("U14 bytes_complete=true changed_images=" + str(len(changed_images)) + "/27 receipt=verified strict_repro=pending deployable=false")
    print("bundle=" + composition["bundle_sha256"] + " manifest=" + composition["native_manifest_sha256"] + " inputs=" + composition["native_inputs_sha256"])


if __name__ == "__main__":
    main()
