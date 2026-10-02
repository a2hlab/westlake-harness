import json
from pathlib import Path

from finalize import HERE, PRIOR, install, save, sha
from reports import expand
from validation import ABI_TARGET, FIRST_BUNDLE, OLD_ABI, check_local_plan
import generation_bundle as bundle_tool
import generation_static_checks as static


def main():
    first = PRIOR / ".artifacts/bundle"
    if sha(first / "bundle.json") != FIRST_BUNDLE:
        raise ValueError("Immutable first packet changed")
    old_effective = static.effective(first)
    first_data, _, _ = bundle_tool.validate(first)
    variants = {}
    for variant in ["common", "61b"]:
        root = HERE / variant
        composition = json.loads((root / "composition.json").read_text())
        if composition["donor_evidence"] != json.loads((HERE / "donor-evidence.json").read_text()):
            raise ValueError("Normalized donor receipt changed after finalization")
        composition["donor_evidence_sha256"] = sha(HERE / "donor-evidence.json")
        save(root / "composition.json", composition)
        package = expand(composition["package"])
        data, _, _ = bundle_tool.validate(package)
        effective = static.effective(package)
        if old_effective.keys() != effective.keys():
            raise ValueError("Effective artifact inventory drift")
        differences = [target for target in effective if effective[target]["sha256"] != old_effective[target]["sha256"]]
        if differences != ([] if composition["abi_sha256"] == OLD_ABI else [ABI_TARGET]):
            raise ValueError("Unrelated effective artifact changed")
        if data["boot_group"] != first_data["boot_group"] or data["runtime_jar"] != first_data["runtime_jar"] or data["paired_build_receipt"] != first_data["paired_build_receipt"]:
            raise ValueError("Images/JAR/paired receipt changed during ABI-only task")
        plan = json.loads((root / "transaction-plan.json").read_text())
        check_local_plan(plan, composition["baseline"])
        report = json.loads((root / "evidence/static-vs-u13.json").read_text())
        prior_static = json.loads((PRIOR / "evidence/static-vs-u13.json").read_text())
        current_deltas = {row["target"]: row["delta_sha256"] for row in report["members"] if row.get("delta_sha256")}
        previous_deltas = {row["target"]: row["delta_sha256"] for row in prior_static["members"] if row.get("delta_sha256")}
        if len(current_deltas) < 4 or len(previous_deltas) < 4:
            raise ValueError("Full native open-delta report missing")
        save(root / "artifact-stability.json", dict(first_bundle_sha256=FIRST_BUNDLE,
            effective_members=len(effective), changed_effective_targets=differences,
            images_27_unchanged=True, runtime_and_stubs_unchanged=True, paired_receipt_unchanged=True,
            candidate_artifact_fingerprint={target: row["sha256"] for target, row in sorted(effective.items())},
            previous_open_deltas=previous_deltas, current_open_deltas=current_deltas,
            open_deltas_identical=current_deltas == previous_deltas, board_local_members=composition["board_local_members"]))
        variants[variant] = dict(bundle_sha256=composition["bundle_sha256"], transaction_base_sha256=composition["transaction_base_sha256"],
            native_manifest_sha256=composition["native_manifest_sha256"], native_inputs_sha256=composition["native_inputs_sha256"],
            planned_base_fingerprints=composition["baseline"]["fingerprints"], planned_candidate_fingerprints=composition["candidate"]["fingerprints"],
            results=json.loads((root / "results.json").read_text()))
    save(HERE / "results.json", dict(variants=variants, first_packet_immutable=True,
        abi_v2_status=variants["common"]["results"]["abi_v2_status"], promotion_confirmed=False,
        execution_enabled=False, active_registry_updated=False, device_access=False, vm_used=False))
    save(HERE / "documentation.json", dict(readme_layout_row="| **2026-10-03 U14 conditional U13 per-board binding** | `benchmark/2026-10-03-u14-effective-rebind/` | Disabled common/61b transaction metadata, exact board-local installers and unapplied exception previews. |",
        digest_line="- U14 conditional rebind (2026-10-03, cx-bms): U13 bundle reference files still describe T8, so planned post-promotion identities must come from U13 candidate_boards; common9127/61b8861 retain their two installer hashes with zero installer operations. Native issue IDs do not change for bundle-only metadata rebinding; ABI v2 changes require a fresh native manifest/inputs and unapplied semantic mapping. Promotion remains unconfirmed. See benchmark/2026-10-03-u14-effective-rebind/."))
    print("Two conditional variants: effective artifact stability verified; image bake and approvals unchanged")


if __name__ == "__main__":
    main()
