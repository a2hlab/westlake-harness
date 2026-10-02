import json
import shutil

from common import BASE, HERE, JAR, MASTER, PACKAGE, PREVIOUS, capture, save, sha
import auto_approve_exceptions as auto
import generation_bundle as bundle_tool
import generation_static_checks as static
from validation import compare_new

PREFIX = "benchmark/2026-10-03-u13-final-assembly/"
APPROVAL = "benchmark/2026-10-03-u13-gate-review/outer-approval.json"


def main():
    approval = json.loads((MASTER / APPROVAL).read_text())
    delta = approval["addendum_production_delta"]["approved_delta_sha256"]
    if delta != "ab8d10e396a0288b9fa6195b517ad272616d0e0ba2efd350955c94c7f007a866":
        raise ValueError("Unexpected production delta authorization")
    jar_authority = approval["addendum_jar_allow_drop"]["approved"]
    if "Ladapter/core/GcmDefaultNonce$2;" not in jar_authority or "bbc3f530" not in jar_authority or "0482c9b1" not in jar_authority:
        raise ValueError("Missing exact JAR authority")
    check = json.loads((HERE / "transfer-check.json").read_text())
    if not check["exact_new_findings"] or not check["strings_equal"]:
        raise ValueError("Semantic or strings drift")
    for row in check["compat_aliases"]:
        if (row["candidate_sha256"], row["deployed_sha256"], row["delta_sha256"]) != (
            "b8a87f6fe2902b1d1c9e8440714d32dbdfd05d75dc1a2993fd2624af91d15abc",
            "015aa3a632eabe057bd8d6ce0e0ff181209da7dcab8de22409a79addc0a56d58", delta):
            raise ValueError("Unapproved pair or delta")
    candidate = json.loads((HERE / "evidence/native-v3.json").read_text())
    baseline = json.loads((HERE / "evidence/native-u12.json").read_text())
    prior = json.loads((PREVIOUS / "evidence/native-v2.json").read_text())
    mapping = compare_new(prior, candidate)
    registry_path = MASTER / "knowledge/gates/native-predeploy-exceptions.json"
    registry = json.loads(registry_path.read_text())
    matched, new = auto.classify(candidate, [baseline], registry["exceptions"])
    if len(matched) != 157 or len(new) != 2 or not all(row["equal"] for row in mapping):
        raise ValueError("Finding set changed")
    evidence = [PREFIX + "evidence/native-v3.json", PREFIX + "evidence/native-u12.json", APPROVAL]
    rows = []
    for gate, finding, source in matched:
        rows.append(dict(gate=gate, package_manifest_sha256=candidate["package_manifest_sha256"],
            inputs_sha256=candidate["inputs_sha256"], issue_id=finding["issue_id"], reason="Identical approved U12 finding; final U13 binding authorized by outer.",
            removal_condition=source["removal_condition"], evidence=evidence, approved_by="outer(claude)", approved_at=approval["signed_at"],
            auto_from=dict(package_manifest_sha256=source["package_manifest_sha256"], issue_id=source["issue_id"])))
    for gate, finding, _ in new:
        row_mapping = next(row for row in mapping if row["new_issue_id"] == finding["issue_id"])
        rows.append(dict(gate=gate, package_manifest_sha256=candidate["package_manifest_sha256"],
            inputs_sha256=candidate["inputs_sha256"], issue_id=finding["issue_id"], reason="Outer-reviewed unchanged resident-only NOLOAD statement newly covered by full-gfx N1; availability and rendering are not proven.",
            removal_condition="Remove after owner namespace/timing proof or fix; any binding/source/owner drift requires new review.",
            evidence=evidence + ["benchmark/2026-10-03-u13-gate-review/lineage.json"], approved_by="outer(claude)",
            approved_at=approval["signed_at"], old_issue_id=row_mapping["old_issue_id"], new_issue_id=finding["issue_id"]))
    save("registry-delta.json", dict(schema_version=1, exceptions=rows, execution_enabled=False, applied=False,
        package_manifest_sha256=candidate["package_manifest_sha256"], inputs_sha256=candidate["inputs_sha256"],
        approval=APPROVAL, old_to_new_issue_ids=mapping))
    combined = dict(registry)
    existing = {(row["gate"], row["package_manifest_sha256"], row["issue_id"]) for row in registry["exceptions"]}
    combined["exceptions"] = registry["exceptions"] + [row for row in rows
        if (row["gate"], row["package_manifest_sha256"], row["issue_id"]) not in existing]
    save(".artifacts/combined-registry.json", combined)
    policy = dict(jars={}, native={})
    for row in check["compat_aliases"]:
        policy["native"][row["target"]] = dict(candidate_sha256=row["candidate_sha256"], deployed_sha256=row["deployed_sha256"],
            delta_sha256=delta, reason="Same reviewed backend diagnostic relocation; production-schema hash explicitly approved.",
            evidence=[APPROVAL, PREFIX + "evidence/static-v3.json"], approved_by="outer(claude)",
            approved_at=approval["addendum_production_delta"]["at"], old_delta_sha256=check["approved_delta_sha256"],
            package_manifest_sha256=candidate["package_manifest_sha256"])
    target = "/system/android/framework/oh-adapter-runtime.jar"
    policy["jars"][target] = dict(candidate_sha256=JAR, deployed_sha256="0482c9b13fbc6ab5bce3902807eb7972736463b772773fde276cae679ce9bd4f",
        allow_drop=["Ladapter/core/GcmDefaultNonce$2;"], reason="Exact anonymous Cipher subclass carrying the R3 defect removed by approved v3 fix; all other drops remain forbidden.",
        evidence=[APPROVAL, PREFIX + "evidence/jar-v3-results.json"], approved_by="outer(claude)", approved_at=approval["addendum_jar_allow_drop"]["at"])
    jar_report = next(item for item in json.loads((HERE / "evidence/static-v3.json").read_text())["members"] if item.get("kind") == "DEX-JAR")
    added = [line.split()[1] for line in jar_report["check"]["stdout"].splitlines() if line.startswith("ADDED")]
    source_roots = {
        "Ladapter/activity/TelephonyRegistryStub;": ("benchmark/2026-10-03-u13-jar-v2/src/adapter/activity/TelephonyRegistryStub.java", "03876fe658f50001978b2b668fa42f8008b0b541", "present-but-off telephony.registry binder, previously accepted U13 v2"),
        "Ladapter/activity/ThemeProbe;": ("benchmark/2026-10-03-u13-java-walls-2/src/adapter/activity/ThemeProbe.java", "ee0656b2b6", "default-off read-only theme diagnostic, accepted U13 Java walls"),
        "Ladapter/activity/WebkitSupportGlue;": ("benchmark/2026-10-03-u13-java-walls-2/src/adapter/activity/WebkitSupportGlue.java", "ee0656b2b6", "single-feature webkit glue, not a renderer"),
        "Lorg/chromium/support_lib_glue/SupportLibReflectionUtil;": ("benchmark/2026-10-03-u13-java-walls-2/src/org/chromium/support_lib_glue/SupportLibReflectionUtil.java", "ee0656b2b6", "support-lib reflection handlers for accepted single-feature glue")}
    reviewed = []
    for descriptor in added:
        outer_descriptor = descriptor.split("$")[0].rstrip(";") + ";"
        if outer_descriptor not in source_roots:
            raise ValueError("Unreviewed JAR addition")
        source, commit, reason = source_roots[outer_descriptor]
        reviewed.append(dict(descriptor=descriptor, source=source, source_sha256=sha(MASTER / source), source_commit=commit,
            reason=reason, reviewed_by="cx-bms", provenance="Previously outer-accepted U13 source; v3 asserts all non-GCM smali byte-identical to506abe23"))
    if len(reviewed) != 10:
        raise ValueError("JAR addition count changed")
    save("jar-additions-review.json", dict(rows=reviewed, candidate_sha256=JAR, deployed_sha256=jar_report["deployed_sha256"],
        exact_descriptors_only=True, namespace_renderer_claim=False))
    policy["jars"][target]["allow_add"] = added
    policy["jars"][target]["evidence"].append(PREFIX + "jar-additions-review.json")
    bundle = json.loads((PACKAGE / "bundle.json").read_text())
    policy_path = bundle_tool.member(PACKAGE, bundle["static_checks"]["policy"])
    save(policy_path, policy)
    bundle["static_checks"]["policy"]["sha256"] = sha(policy_path)
    save(PACKAGE / "bundle.json", bundle)
    save("static-policy.json", policy)
    save("evidence/outer-approval-final.json", approval)
    record = capture("native-v3-approved", ["python3", MASTER / "scripts/lab/native_predeploy.py", "--package", PACKAGE / "native",
        "--inputs", PACKAGE / "native/native-checks/native-gates.json", "--exceptions", HERE / ".artifacts/combined-registry.json"])
    native = json.loads((HERE / ".artifacts/raw/native-v3-approved.txt").read_text())
    save("evidence/native-v3-approved.json", native)
    final_static = static.check(PACKAGE, BASE, policy)
    save("evidence/static-v3-approved.json", final_static)
    if native["status"] != "PASS" or final_static["status"] != "PASS":
        raise ValueError("Approved fresh reports did not pass")
    composition = json.loads((HERE / "composition.json").read_text())
    composition.update(bundle_sha256=sha(PACKAGE / "bundle.json"), approvals_transferred=True,
        approved_registry_rows=len(rows), approved_native_report=record, static_status=final_static["status"])
    save("composition.json", composition)
    for name, path in [("bundle.json", PACKAGE / "bundle.json"), ("native-manifest.json", PACKAGE / "native/package.json"),
                       ("native-inputs.json", PACKAGE / "native/native-checks/native-gates.json"), ("scan-manifest.json", PACKAGE / "native/native-checks/scan-manifest.json")]:
        destination = HERE / "manifests" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    print("TRANSFERRED159 native=" + native["status"] + " static=" + final_static["status"] + " bundle=" + composition["bundle_sha256"])


if __name__ == "__main__":
    main()
