import json

from native_pair import PAIR
from prepare import HERE, MASTER, WS, save, sha


def main():
    binding = json.loads((HERE / "native-pair-binding.json").read_text())
    gates = json.loads((HERE / "native-pair-gates.json").read_text())
    manifest = json.loads((PAIR / "package.json").read_text())
    if sha(PAIR / "package.json") != binding["native_manifest_sha256"]:
        raise ValueError("Selected pair manifest changed")
    if sha(PAIR / "native-checks/native-gates.json") != binding["native_inputs_sha256"]:
        raise ValueError("Selected pair input binding changed")
    for name, digest in manifest["files"].items():
        if sha(PAIR / name) != digest:
            raise ValueError("Selected payload drift")
    for row in gates["records"]:
        raw = WS / row["raw"].removeprefix("$WORKSPACES/")
        if sha(raw) != row["raw_sha256"] or sha(HERE / row["evidence"]) != row["evidence_sha256"]:
            raise ValueError("Fresh native log changed")
    for name in ["native-source-snapshots.json", "flutter-source-snapshots.json", "source-snapshots.json"]:
        for row in json.loads((HERE / name).read_text()):
            if sha(HERE / row["snapshot"]) != row["snapshot_sha256"]:
                raise ValueError("Public source proof changed")
    current_registry = sha(MASTER / "knowledge/gates/native-predeploy-exceptions.json")
    if current_registry != gates["active_registry_sha256"] or current_registry != gates["active_registry_sha256_after"]:
        raise ValueError("Active table changed since fresh pair gates; rerun required")
    plan = json.loads((HERE / "plan.json").read_text())
    for row in plan["content_bases"].values():
        root = WS / row["path"].removeprefix("$WORKSPACES/")
        if sha(root / "bundle.json") != row["sha256"]:
            raise ValueError("Content baseline changed")
    composition = json.loads((HERE / "composition.json").read_text())
    if any(composition[name] is not False for name in ["execution_enabled", "rollout_ready"]):
        raise ValueError("No final execution permission")
    if composition["transaction_base"] != {"common": None, "61b": None}:
        raise ValueError("Transaction baseline must remain parameterized")
    if any(composition[name] is not None for name in ["final_bundle_sha256", "final_manifest_sha256", "final_inputs_sha256"]):
        raise ValueError("Incomplete bundle cannot have final identities")
    save("final-consistency.json", dict(exit_code=0, native_payloads_checked=len(manifest["files"]),
        native_commands_checked=len(gates["records"]), active_registry_sha256=current_registry,
        content_bases_unchanged=True, native_batch_artifacts_arrived=True, native_production_approved=False,
        final_bundle_sha256=None, execution_enabled=False, rollout_ready=False, board_access=False, vm_access=False,
        registry_updated=False, image_bake_executed=False, native_build_executed=False))
    print("CONSISTENCY PASS: selected payloads, source capsules, raw logs, active table and two U15 bases exact; final execution disabled")


if __name__ == "__main__":
    main()
