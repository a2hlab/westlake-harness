import csv
import json
from pathlib import Path

from common import BASE, HERE, MASTER, PLAN, RELEASE, portable, save, sha
from validation import IMAGES, SHIM


def main():
    composition = json.loads((HERE / "final-composition.json").read_text())
    package = HERE / ".artifacts/bundle"
    report = json.loads((HERE / "report-summary.json").read_text())
    static = json.loads((HERE / "evidence/static-vs-u13.json").read_text())
    sources = json.loads((package / "native/native-checks/scan-manifest.json").read_text())["sources"]
    snapshots = []
    for name, row in sources.items():
        source = package / "native/native-checks" / row["path"]
        if sha(source) != row["sha256"]:
            raise ValueError("Bound scanner source changed")
        target = HERE / "inputs/native-checks" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(portable(source.read_text()))
        snapshots.append(dict(name=name, source_origin=row["origin"], original_sha256=row.get("source_sha256", row["sha256"]),
            native_sidecar_sha256=sha(source), snapshot=target.relative_to(HERE), snapshot_sha256=sha(target), first_line=row.get("first_line", 1)))
    save("source-snapshots.json", dict(sources=snapshots, source_sidecar_manifest_sha256=sha(package / "native/native-checks/scan-manifest.json"),
        recipe_and_full_closure_inventory=dict(source=PLAN / "source-snapshots.json", sha256=sha(PLAN / "source-snapshots.json")),
        bridge_closure_inventory=dict(source=HERE.parent / "2026-10-03-u14-native-assembly/provenance.json", sha256=sha(HERE.parent / "2026-10-03-u14-native-assembly/provenance.json")),
        native_rebuild=False, snapshots_are_portable_copies=True))
    images = []
    for name in sorted(IMAGES):
        old, new = BASE / "boot/arm64" / name, RELEASE / "run1" / name
        images.append(dict(name=name, u13_sha256=sha(old), u14_sha256=sha(new), bytes=new.stat().st_size, changed=sha(old) != sha(new), actual_source=new))
    save("image-delta.json", dict(changed=sum(row["changed"] for row in images), total=27, rows=images))
    with (HERE / "image-delta.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["name", "u13_sha256", "u14_sha256", "bytes", "changed"])
        writer.writeheader()
        writer.writerows({name: row[name] for name in writer.fieldnames} for row in images)
    native_allowances = [dict(target=row["target"], candidate_sha256=row["candidate_sha256"], deployed_sha256=row["deployed_sha256"],
        delta_sha256=row["delta_sha256"], delta=row["open_site_delta"], approved_by=None, evidence=["benchmark/2026-10-03-u14-final-assembly/evidence/static-vs-u13.json"])
        for row in static["members"] if row["status"] == "REVIEW_REQUIRED"]
    save("static-allowance-draft.json", dict(native=native_allowances, applied=False, approved_by=None, package_manifest_sha256=composition["native_manifest_sha256"], bundle_sha256=composition["bundle_sha256"]))
    save("new-native-admissions-draft.json", dict(schema="westlake-new-native-admissions/v1", applied=False, approved_by=None, admissions=[dict(
        target="/system/android/lib64/libicu74compat.so", sha256=SHIM, package_manifest_sha256=composition["native_manifest_sha256"],
        reason="ICU wall2 seven _74 tail aliases to the retained unique _72 provider; new library not approved for promotion yet",
        evidence=["benchmark/2026-10-03-u14-final-assembly/imports.json", "benchmark/2026-10-03-u14-final-assembly/evidence/dynamic-android-lib64-libicu74compat-u14.txt", "benchmark/2026-10-03-u14-final-assembly/evidence/dynsym-android-lib64-libicu74compat-u14.txt"]) ]))
    receipt = json.loads((HERE / "receipts/paired-run1.json").read_text())
    reproduction = json.loads((HERE / "reproduction-review.json").read_text())
    save("image-exception-draft.json", dict(id="U14-REPRO-BACKTRACE-001", status="pending-object-proof-and-outer-review", approved_by=None,
        input_jars=receipt["input_jars"], outputs=receipt["outputs"], paired_outputs=json.loads((HERE / "receipts/paired-run2.json").read_text())["outputs"],
        dex2oat_sha256=receipt["dex2oat_sha256"], driver_sha256=receipt["driver_sha256"], build_command=receipt["build_command"],
        object=dict(file="boot.art", file_offset_start="0x3e3b8", file_offset_end_exclusive="0x3e3c0", identity="unknown until fresh U14 oatdump"),
        actual_differences=[row for row in reproduction["comparisons"] if not row["identical"]], evidence=["benchmark/2026-10-03-u14-final-assembly/reproduction-review.json"], applied=False))
    summaries = []
    for path in sorted((HERE / "evidence").glob("abi-*.json")):
        abi = json.loads(path.read_text())
        summaries.append(dict(evidence=path.relative_to(HERE), added=len(abi["added"]), removed=len(abi["removed"]), drift=len(abi["drift"]),
            consumer_breaks=len(abi["consumer_breaks"]), call_diffs=abi["call_diffs"]))
    save("abi-summary.json", dict(rows=summaries, consumer_count=219, all_consumer_breaks_zero=all(row["consumer_breaks"] == 0 for row in summaries)))
    results = dict(composition={name: composition[name] for name in ["bundle_sha256", "native_manifest_sha256", "native_inputs_sha256", "comparison_base_sha256", "transaction_base_sha256", "paired_receipt_sha256"]},
        actual_bake_runs=2, incoming_inventory_verified=131, image_changes=19, strict_reproduction="26/27, REJECT pending fresh object proof and exact outer approval",
        native_gate=report["native_candidate"], auto_identical_preview=report["auto_identical_count"], new_findings=report["new_findings_by_gate"], static_gate=report["static_vs_u13"],
        rb_exit=next(row["exit_code"] for row in report["records"] if row["evidence"].endswith("/rb.txt")),
        t4b_exit=next(row["exit_code"] for row in report["records"] if row["evidence"].endswith("/t4b.txt")),
        frozen_package_exit=next(row["exit_code"] for row in report["records"] if row["evidence"].endswith("/frozen.txt")),
        frozen_package_scope="8 active entries, only 2 artifact entries checked; does not approve FZ-005 image replacement",
        image_layout_G1_G2="not run locally; frozen oatdump/production replay deferred to outer after U13 window",
        production_run=False, vm_used=False, execution_enabled=False, rollout_ready=False, artifact_bytes_not_rebuilt=True, partial_and_final_descriptors_distinct=True)
    save("results.json", results)
    proof_path = HERE / "object-proof.json"
    if proof_path.exists():
        proof = json.loads(proof_path.read_text())
        paired = [json.loads((HERE / "receipts" / ("paired-run" + str(number) + ".json")).read_text()) for number in [1, 2]]
        if len(proof["rows"]) != 2 or any(row["boot_art_sha256"] != paired[row["run"] - 1]["outputs"]["boot.art"] for row in proof["rows"]):
            raise ValueError("Fresh object evidence does not bind these paired outputs")
        draft_path = HERE / "image-exception-draft.json"
        draft = json.loads(draft_path.read_text())
        draft["status"] = "proposed"
        draft["object"]["identity"] = proof["rows"][0]["object"]
        draft["object"]["object"] = proof["rows"][0]["object"]
        draft["evidence"].append("benchmark/2026-10-03-u14-final-assembly/object-proof.json")
        draft["reason"] = "Fresh exact U14 object identity proved; only the sentinel backtrace element differs; no runtime-harmlessness or approval assertion"
        save(draft_path, draft)
        results.update(object_chain_verified=True, object_proof_sha256=sha(proof_path), strict_reproduction="26/27, REJECT pending exact outer U14 approval; new object chain verified")
        save("results.json", results)
    save("tool-identity.json", dict(tools=[dict(source=MASTER / "scripts/lab" / name, sha256=sha(MASTER / "scripts/lab" / name)) for name in ["open_site_scan.py", "deployed_strings_diff.py", "deployed_class_diff.py", "native_predeploy.py", "generation_static_checks.py", "abi_diff.py", "auto_approve_exceptions.py", "u7_executor.py"]]))
    print("REVIEW N1=" + str(results["new_findings"]["N1"]) + " N2=" + str(results["new_findings"]["N2"]) + " open_pairs=" + str(len(native_allowances)) + " new_native=1; all_unapproved")


if __name__ == "__main__":
    main()
