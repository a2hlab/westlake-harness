import copy
import json
from pathlib import Path
import re
import subprocess
import sys

from finalize import HERE, MASTER, install, save, sha
from reports import capture, expand
from validation import map_pending
import generation_bundle as bundle_tool
import generation_static_checks as static


def main():
    approval_path = MASTER / "benchmark/2026-10-03-u14-review/outer-approval-findings.json"
    approval = json.loads(approval_path.read_text())
    if approval["signer"] != "outer(claude)" or "f8619ad5" not in approval["transfer_condition"]:
        raise ValueError("Signed v2 transfer condition missing")
    old_review = json.loads((HERE.parent / "2026-10-03-u14-final-assembly/needs-outer-review.json").read_text())
    current_review = json.loads((HERE / "common/needs-outer-review.json").read_text())
    mapping = map_pending(old_review["new_findings"], current_review["new_findings"])
    if len(mapping) != 45 or len(old_review["new_findings"]) != 45 or not all(row["semantic_unchanged"] for row in mapping):
        raise ValueError("Additional or changed finding; stop for outer review")
    delta = json.loads((HERE / "delta-review.json").read_text())
    if not all(row["equal_after_diagnostic_pc_normalization"] for row in delta["mappings"]):
        raise ValueError("Additional namespace/open delta; stop for outer review")
    abi = json.loads((HERE / "slot-checks.json").read_text())["abi_results"]["u14-v1"]
    if abi["added"] != ["_ctype_"] or any(abi[key] for key in ["removed", "drift", "consumer_breaks", "call_diffs"]):
        raise ValueError("ABI changes exceed approved data export")
    evidence = ["benchmark/2026-10-03-u14-review/outer-approval-findings.json"]
    rows = copy.deepcopy(json.loads((HERE / "common/registry-delta.json").read_text())["exceptions"])
    for row in rows:
        row.update(approved_by=approval["signer"], approved_at=approval["signed_at"])
        row["evidence"] = sorted(set(row["evidence"] + evidence))
    for finding, link in zip(current_review["new_findings"], mapping):
        rows.append(dict(gate=finding["gate"], issue_id=finding["issue_id"], package_manifest_sha256=current_review["package_manifest_sha256"],
            inputs_sha256=current_review["inputs_sha256"], approved_by=approval["signer"], approved_at=approval["signed_at"],
            reason="Signed U14 review transferred field-for-field to the exact native ABI v2; " + finding.get("profile", finding["gate"]),
            removal_condition="Rerun upon source, artifact, inputs or owner-routing change; remove when finding no longer applies", evidence=evidence,
            auto_from=dict(package_manifest_sha256=old_review["package_manifest_sha256"], issue_id=link["old_issue_id"])))
    signed_mapping = [dict(row, approved_by=approval["signer"], approved_at=approval["signed_at"], transferred=True) for row in mapping]
    save(HERE / "registry-delta-signed.json", dict(schema_version=1, exceptions=rows, applied=False, approved_by=approval["signer"],
        approval_sha256=sha(approval_path), old_manifest_sha256=old_review["package_manifest_sha256"],
        new_manifest_sha256=current_review["package_manifest_sha256"], old_inputs_sha256=old_review["inputs_sha256"],
        new_inputs_sha256=current_review["inputs_sha256"], old_to_new=signed_mapping))
    active = json.loads((MASTER / "knowledge/gates/native-predeploy-exceptions.json").read_text())
    present = {(row["package_manifest_sha256"], row["issue_id"]) for row in active["exceptions"]}
    active["exceptions"] += [row for row in rows if (row["package_manifest_sha256"], row["issue_id"]) not in present]
    save(HERE / ".artifacts/combined-registry.json", active)
    admission = dict(target="/system/android/lib64/libicu74compat.so", sha256="4886bc5c2b4ef0486ecda6fa3248ace4af6a1c57ed7029b17cfd4868ad2c92af",
        package_manifest_sha256=current_review["package_manifest_sha256"], reason="Signed U14 ICU _74 tail-alias shim; exact owner dependency tree and no second copy",
        added=approval["signed_at"], evidence=evidence)
    admissions = json.loads((MASTER / "knowledge/gates/new-native-admissions.json").read_text())
    if not any(row["target"] == admission["target"] and row["package_manifest_sha256"] == admission["package_manifest_sha256"] for row in admissions["admissions"]):
        admissions["admissions"].append(admission)
    save(HERE / "new-native-admissions-signed.json", dict(schema="westlake-new-native-admissions/v1", admissions=[admission], applied=False))
    save(HERE / ".artifacts/combined-admissions.json", admissions)
    static.NEW_NATIVE_ADMISSIONS = HERE / ".artifacts/combined-admissions.json"
    for variant in ["common", "61b"]:
        root = HERE / variant
        composition = json.loads((root / "composition.json").read_text())
        package = expand(composition["package"])
        output = HERE / ".artifacts" / (variant + "-reviewed")
        if output.exists():
            raise ValueError("Immutable reviewed output exists")
        subprocess.run(["/bin/cp", "-cR", package, output], check=True)
        raw_static = json.loads((root / "evidence/static-vs-u13.json").read_text())
        policy = dict(schema_version=1, native={}, jars={}, execution_enabled=False)
        for row in raw_static["members"]:
            if row.get("delta_sha256"):
                policy["native"][row["target"]] = dict(candidate_sha256=row["candidate_sha256"], deployed_sha256=row["deployed_sha256"], delta_sha256=row["delta_sha256"],
                    approved_by=approval["signer"], approved_at=approval["signed_at"], evidence=evidence)
            if row.get("kind") == "DEX-JAR":
                stdout = row["check"]["stdout"]
                classes = re.findall(r"^ADDED\s+(L[^\s]+;)$", stdout, re.M)
                expected = ["Landroid/bluetooth/le/ScanCallback;", "Landroid/bluetooth/le/ScanCallback$ScanFailed;"] if "stubs.jar" in row["target"] else ["Ladapter/activity/InProcessBindOrder;", "Ladapter/activity/InProcessBindOrder$1;", "Ladapter/activity/InProcessBindOrder$2;"]
                if sorted(classes) != sorted(expected) or "0 dropped, 0 reshaped" not in stdout:
                    raise ValueError("Unapproved JAR class change")
                policy["jars"][row["target"]] = dict(allow_add=classes, candidate_sha256=row["candidate_sha256"], deployed_sha256=row["deployed_sha256"],
                    approved_by=approval["signer"], approved_at=approval["signed_at"], evidence=evidence)
        bundle = json.loads((output / "bundle.json").read_text())
        policy_path = output / bundle["static_checks"]["policy"]["source"]
        save(policy_path, policy)
        bundle["static_checks"]["policy"]["sha256"] = sha(policy_path)
        install(approval_path, output / "receipts/u14-findings-outer-approval.json")
        bundle["native_review_approval"] = dict(source="receipts/u14-findings-outer-approval.json", sha256=sha(output / "receipts/u14-findings-outer-approval.json"))
        bundle["rollout_blocker"] = "Production gates, actual U13 promotion and window authorization pending; offline only"
        save(output / "bundle.json", bundle)
        bundle_tool.validate(output)
        native_run = capture(root, "native-combined-approved", [sys.executable, MASTER / "scripts/lab/native_predeploy.py", "--package", output / "native", "--inputs", output / "native/native-checks/native-gates.json", "--exceptions", HERE / ".artifacts/combined-registry.json"])
        reviewed_static = static.check(output, expand(composition["transaction_base"]), policy)
        save(root / "evidence/static-with-approved-local-admissions.json", reviewed_static)
        if native_run["exit_code"] or reviewed_static["status"] != "PASS":
            raise ValueError("Signed local gate failed")
        signed = dict(composition, package=output, bundle_sha256=sha(output / "bundle.json"), static_status="PASS-with-local-signed-admissions",
            native_status="PASS-with-local-signed-registry", approval_sha256=sha(approval_path), active_registry_updated=False,
            local_native_record=native_run, native_rows=204, window_authorized=False)
        save(root / "reviewed-composition.json", signed)
        print(variant + " reviewed bundle=" + signed["bundle_sha256"] + " native/static local PASS; active registries unchanged", flush=True)


if __name__ == "__main__":
    main()
