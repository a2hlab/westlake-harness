import argparse
import copy
import json
from pathlib import Path
import shutil
import subprocess

from common import ASSEMBLY_BASE, ASSEMBLY_SHA, BRIDGE, DONOR, HERE, MASTER, OLD_BRIDGE, REPEAT, save, sha
from validation import require_single_delta, require_transaction_identity
import generation_bundle as bundle_tool
import generation_static_checks as static
import u7_executor as executor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--transaction-base", type=Path, required=True)
    parser.add_argument("--transaction-base-sha256", required=True)
    parser.add_argument("--board-baseline", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    base = args.transaction_base.resolve()
    output = args.out.resolve()
    require_transaction_identity(args.transaction_base_sha256, sha(base / "bundle.json"))
    if sha(ASSEMBLY_BASE / "bundle.json") != ASSEMBLY_SHA or output.exists():
        raise ValueError("Assembly base changed or immutable output already exists")
    for donor in [DONOR, REPEAT]:
        if sha(donor / "out/liboh_adapter_bridge.so") != BRIDGE:
            raise ValueError("Bridge double-build identity changed")
    old_bundle, old_manifest, _ = bundle_tool.validate(ASSEMBLY_BASE)
    bridge_member = "payload/android/lib64/liboh_adapter_bridge.so"
    if old_manifest["files"][bridge_member] != OLD_BRIDGE:
        raise ValueError("Assembly bridge is not the mapped owner")
    baseline = json.loads(args.board_baseline.read_text())
    boards = baseline.get("boards", baseline.get("candidate_boards"))
    if not boards or len(boards) != 3:
        raise ValueError("Explicit signed three-board baseline evidence required")
    base_files = static.effective(base)
    previous = json.loads((ASSEMBLY_BASE.parents[1] / "composition.json").read_text())
    reference_paths = {}
    for serial, board in boards.items():
        paths = board.get("reference_paths") or {
            kind: [target for target in members if target in board["expected"]]
            for kind, members in previous["candidate_boards"][serial]["reference_paths"].items()}
        if executor.fingerprints(board["expected"], paths) != board["fingerprints"]:
            raise ValueError("Signed transaction baseline fingerprints disagree")
        for target, row in base_files.items():
            if board["expected"].get(target) != row["sha256"]:
                raise ValueError("Transaction base / signed board identity drift: " + target)
        reference_paths[serial] = paths
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["/bin/cp", "-cR", ASSEMBLY_BASE, output], check=True)
    bridge_path = output / "native" / bridge_member
    bridge_path.chmod(bridge_path.stat().st_mode | 0o200)
    shutil.copyfile(DONOR / "out/liboh_adapter_bridge.so", bridge_path)
    manifest = copy.deepcopy(old_manifest)
    manifest["files"][bridge_member] = BRIDGE
    manifest["live_hashes"]["/system/android/lib64/liboh_adapter_bridge.so"] = BRIDGE
    manifest["bridge_sha256"] = BRIDGE
    manifest["variant"] = "U14 bridge-only draft: U13 plus R1/R2/R3 M5/M6; other slots held"
    manifest["rollout_ready"] = False
    manifest["rollout_blocker"] = "Offline draft; native/static approval and final slots plus two-surface replay pending"
    save(output / "native/package.json", manifest)
    changed = require_single_delta(old_manifest["files"], manifest["files"], bridge_member, BRIDGE)
    checks = output / "native/native-checks"
    scan = json.loads((checks / "scan-manifest.json").read_text())
    sources = {
        "u14-bridge-core.cpp": DONOR / "src/bms/src/adapter/framework/core/jni/adapter_bridge.cpp",
        "u14-bridge-input.cpp": DONOR / "window-jni/input_event_bridge.cpp",
        "u14-bridge-window.cpp": DONOR / "window-jni/oh_window_manager_client.cpp",
        "u14-bridge-ability.cpp": DONOR / "src/bms/src/adapter/framework/activity/jni/ability_scheduler_adapter.cpp"}
    for name, source in sources.items():
        shutil.copyfile(source, checks / name)
        scan["sources"][name] = dict(path=name, sha256=sha(source), source_sha256=sha(source), origin=str(source), first_line=1)
        destination = HERE / "inputs" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        scan["profiles"].append(dict(name=name.removesuffix(".cpp"), rule="namespace", source=name,
            identity=dict(package="u14-bridge-only-offline-draft", manifest_sha256=sha(output / "native/package.json"),
                artifact=bridge_member, artifact_sha256=BRIDGE)))
    scan["profiles"].append(dict(name="u14-bridge-m6-jni-cache", rule="jni-order", source="u14-bridge-ability.cpp",
        sources=["u14-bridge-ability.cpp"], entry_source="u14-bridge-ability.cpp", entry_function="ScheduleAbilityTransaction",
        identity=dict(package="u14-bridge-only-offline-draft", manifest_sha256=sha(output / "native/package.json"), artifact=bridge_member, artifact_sha256=BRIDGE)))
    for profile in scan["profiles"]:
        profile["identity"]["manifest_sha256"] = sha(output / "native/package.json")
    save(checks / "scan-manifest.json", scan)
    inputs = json.loads((checks / "native-gates.json").read_text())
    inputs["package_manifest_sha256"] = sha(output / "native/package.json")
    inputs["initialization"]["manifest"]["sha256"] = sha(checks / "scan-manifest.json")
    save(checks / "native-gates.json", inputs)
    bundle = copy.deepcopy(old_bundle)
    bundle["native"]["manifest"]["sha256"] = sha(output / "native/package.json")
    bundle["static_checks"]["baseline_bundle_sha256"] = args.transaction_base_sha256
    bundle["rollout_ready"] = False
    bundle["rollout_blocker"] = "U14 incomplete disabled draft; explicit transaction base must be re-bound after promotion"
    board = boards[next(iter(boards))]
    for kind in ["runtime", "boot"]:
        entry = bundle["reference"][kind]
        destination = output / entry["source"]
        destination.chmod(destination.stat().st_mode | 0o200)
        destination.write_text("\n".join(sorted(board["expected"][target] + "  " + target for target in reference_paths[next(iter(boards))][kind])) + "\n")
        entry["sha256"] = sha(destination)
    for entry in bundle["image_gate_reference"]["members"]:
        current = base_files[entry["target"]]
        destination = output / entry["source"]
        destination.chmod(destination.stat().st_mode | 0o200)
        shutil.copyfile(bundle_tool.member(base, current), destination)
        entry["sha256"] = sha(destination)
    bundle["image_gate_reference"].update(kind="explicit-signed-transaction-baseline", baseline_bundle_sha256=args.transaction_base_sha256)
    save(output / "bundle.json", bundle)
    bundle_tool.validate(output)
    plan = executor.prepare(output, base / "native")
    candidate_boards = copy.deepcopy(previous["candidate_boards"])
    for candidate in candidate_boards.values():
        candidate["expected"]["/system/android/lib64/liboh_adapter_bridge.so"] = BRIDGE
        candidate["fingerprints"] = executor.fingerprints(candidate["expected"], candidate["reference_paths"])
    slots = [dict(id="stock-host-app-ns", kind="native", applied=False, state="awaiting cc-wiki candidate", source_commit="a1aa32f178"),
        dict(id="icu-wall-two", kind="native", applied=False, state="awaiting cc-wiki a/b decision and candidate"),
        dict(id="u14-jar-v1", kind="JAR", applied=False, state="reserved; final assembly pending", source_commit="2c70182c73",
            proposed_sha256="0349eb834e66bc1bf142fd31f08aa0c8a0536534e3ec6b01b5dcc1d930b0a0d4")]
    save("slots.json", dict(slots=slots, final_batch_complete=False))
    save("composition.json", dict(package=output, assembly_base=ASSEMBLY_BASE, assembly_base_sha256=ASSEMBLY_SHA,
        transaction_base=base, transaction_base_sha256=args.transaction_base_sha256, transaction_baseline_evidence=args.board_baseline,
        transaction_baseline_evidence_sha256=sha(args.board_baseline), bundle_sha256=sha(output / "bundle.json"),
        native_manifest_sha256=sha(output / "native/package.json"), native_inputs_sha256=sha(checks / "native-gates.json"),
        changed_payload_members=changed, bridge_sha256=BRIDGE, previous_bridge_sha256=OLD_BRIDGE,
        host_sha256=manifest["files"]["payload/runtime/appspawn-x"], candidate_boards=candidate_boards,
        baseline_boards=boards, pending_slots=slots, boot_and_jars_unchanged_from_u13=True,
        execution_enabled=False, rollout_ready=False, device_access=False, vm_replay="deferred outer after U13 window"))
    save("transaction-plan.json", plan)
    for name, source in [("bundle.json", output / "bundle.json"), ("native-manifest.json", output / "native/package.json"),
                         ("native-inputs.json", checks / "native-gates.json"), ("scan-manifest.json", checks / "scan-manifest.json")]:
        destination = HERE / "manifests" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    save("evidence/transaction-base-evidence.json", baseline)
    print("U14_DRAFT assembly_base=" + ASSEMBLY_SHA[:12] + " transaction_base=" + args.transaction_base_sha256[:12])
    print("bundle=" + sha(output / "bundle.json") + " manifest=" + sha(output / "native/package.json") + " inputs=" + sha(checks / "native-gates.json"))
    print("changed_payload=1 additions=" + str(len(plan["additions"])) + " changes=" + str(len(plan["changes"])) + " disabled=true")


if __name__ == "__main__":
    main()
