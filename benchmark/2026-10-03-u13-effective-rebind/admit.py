import copy
from datetime import datetime
import json
import shutil

from common import BASE, BASE_SHA, HERE, MASTER, PACKAGE, PREVIOUS, save, sha
from validation import class_allowance, known_delta, same_objects
import generation_bundle as bundle_tool
import generation_static_checks as static
import u7_executor as executor

PREFIX = "benchmark/2026-10-03-u13-effective-rebind/"
U12 = MASTER / "benchmark/2026-10-02-u12-final-assembly"


def main():
    report = json.loads((HERE / "evidence/static-unapproved.json").read_text())
    native = json.loads((HERE / "evidence/native-active.json").read_text())
    if native["status"] != "PASS" or native["errors"]:
        raise ValueError("New native rejection")
    u12_report = json.loads((U12 / "gates/mac/static-checks.json").read_text())
    u13_report = json.loads((PREVIOUS / "evidence/static-v3-approved.json").read_text())
    u12_root = BASE.parents[1] / "u12-final-j0482c9b1-s615b8bbe-icu-media-zlib-v2/bundle"
    u12_bundle = json.loads((u12_root / "bundle.json").read_text())
    u12_policy = json.loads(bundle_tool.member(u12_root, u12_bundle["static_checks"]["policy"]).read_text())
    u13_policy = json.loads((PREVIOUS / "static-policy.json").read_text())
    historical = u12_report["members"] + u13_report["members"]
    u12_effective = static.effective(u12_root)
    u13_effective = static.effective(PREVIOUS / ".artifacts/bundle-v3")
    admissions = json.loads((MASTER / "knowledge/gates/new-native-admissions.json").read_text())
    manifest_sha = sha(PACKAGE / "native/package.json")
    mapping = []
    transferred_admissions = []
    policy = dict(jars={}, native={})
    for row in report["members"]:
        target = row["target"]
        prior_object = u12_effective.get(target)
        origin = "U12"
        prior_bundle_sha = sha(u12_root / "bundle.json")
        if not prior_object or prior_object["sha256"] != row["candidate_sha256"]:
            prior_object = u13_effective[target]
            origin = "U13"
            prior_bundle_sha = sha(PREVIOUS / ".artifacts/bundle-v3/bundle.json")
        if prior_object["sha256"] != row["candidate_sha256"]:
            raise ValueError("Object not approved under either original binding")
        mapping.append(dict(target=target, origin=origin, artifact_sha256=row["candidate_sha256"], old_bundle_sha256=prior_bundle_sha,
            old_package_manifest_sha256=(u12_bundle if origin == "U12" else json.loads((PREVIOUS / ".artifacts/bundle-v3/bundle.json").read_text()))["native"]["manifest"]["sha256"],
            new_package_manifest_sha256=manifest_sha,
            new_base_bundle_sha256=BASE_SHA, old_deployed_sha256=next((old.get("deployed_sha256") for old in historical
                if old["target"] == target and old["candidate_sha256"] == row["candidate_sha256"]), None),
            new_deployed_sha256=row["deployed_sha256"], reason="Same approved object SHA; explicit outer 02:42 effective-baseline transfer rule"))
        if row["deployed_sha256"] is None:
            matches = [entry for entry in admissions["admissions"] if entry["target"] == target and entry["sha256"] == row["candidate_sha256"]]
            if len(matches) != 1:
                raise ValueError("Missing exact prior new-native admission")
            entry = copy.deepcopy(matches[0])
            old_manifest_sha = entry["package_manifest_sha256"]
            entry["package_manifest_sha256"] = manifest_sha
            entry["added"] = datetime.now().astimezone().isoformat(timespec="seconds")
            entry["auto_from"] = dict(package_manifest_sha256=old_manifest_sha, sha256=entry["sha256"], target=target)
            entry["reason"] += "; same-object binding transfer authorized by outer 2026-10-03 02:42"
            transferred_admissions.append(entry)
        elif row.get("kind") == "DEX-JAR":
            output = row["check"]["stdout"]
            if any(line.startswith(("DROPPED", "RESHAPED")) for line in output.splitlines()):
                raise ValueError("New class deletion/reshape against real baseline")
            actual = [line.split()[1] for line in output.splitlines() if line.startswith("ADDED")]
            reviewed = u12_policy["jars"].get(target, {}).get("allow_add", []) + u13_policy["jars"].get(target, {}).get("allow_add", [])
            allowed = class_allowance(actual, reviewed)
            policy["jars"][target] = dict(candidate_sha256=row["candidate_sha256"], deployed_sha256=row["deployed_sha256"],
                allow_add=allowed, reason="Exact already-reviewed class additions composed against real U10.1T8; no class drops or reshapes permitted",
                approved_by="outer(claude)", approved_at="2026-10-03T02:42:53+08:00",
                evidence=["benchmark/2026-10-03-u13-gate-review/outer-approval.json", "benchmark/2026-10-02-u12-final-assembly/jar-additions.json"])
        elif row.get("kind") == "ELF" and row["status"] == "REVIEW_REQUIRED":
            if not known_delta(row, historical):
                save("needs-outer-review.json", dict(new_finding=row, admission_stopped=True))
                raise ValueError("Unmatched effective-baseline open/namespace finding: " + target)
            policy["native"][target] = dict(candidate_sha256=row["candidate_sha256"], deployed_sha256=row["deployed_sha256"],
                delta_sha256=row["delta_sha256"], package_manifest_sha256=manifest_sha,
                reason="Exact already-reviewed pair and full production-schema delta; same-object binding transfer authorized by outer",
                approved_by="outer(claude)", approved_at="2026-10-03T02:42:53+08:00",
                evidence=["benchmark/2026-10-03-u13-gate-review/outer-approval.json", "benchmark/2026-10-02-u12-final-assembly/host-open-delta-review.json"])
    if len(transferred_admissions) != 3:
        raise ValueError("Expected exactly three newly visible native additions")
    save("new-native-admissions-delta.json", dict(schema="westlake-new-native-admissions/v1", admissions=transferred_admissions, applied=False))
    save("static-policy.json", policy)
    bundle = json.loads((PACKAGE / "bundle.json").read_text())
    path = PACKAGE / bundle["static_checks"]["policy"]["source"]
    path.chmod(path.stat().st_mode | 0o200)
    save(path, policy)
    bundle["static_checks"]["policy"]["sha256"] = sha(path)
    save(PACKAGE / "bundle.json", bundle)
    combined = dict(admissions)
    combined["admissions"] = admissions["admissions"] + transferred_admissions
    save(".artifacts/combined-admissions.json", combined)
    original_registry_path = static.NEW_NATIVE_ADMISSIONS
    static.NEW_NATIVE_ADMISSIONS = HERE / ".artifacts/combined-admissions.json"
    try:
        approved = static.check(PACKAGE, BASE, policy)
    finally:
        static.NEW_NATIVE_ADMISSIONS = original_registry_path
    save("evidence/static-transferred-preview.json", approved, compact=True)
    if approved["status"] != "PASS":
        raise ValueError("New static finding after exact allowance transfer")
    _, manifest, _ = bundle_tool.validate(PACKAGE)
    old_manifest = json.loads((PREVIOUS / ".artifacts/bundle-v3/native/package.json").read_text())
    same_objects(manifest, old_manifest)
    composition = json.loads((HERE / "composition.json").read_text())
    composition.update(bundle_sha256=sha(PACKAGE / "bundle.json"), static_preview_status=approved["status"], native_status=native["status"],
        new_admission_rows=3, active_registry_updated=False, pending=["outer append exact three admission rows", "fresh real-base Mac/VM production replay", "outer renew window SHA"])
    save("composition.json", composition)
    save("binding-transfer.json", dict(rows=mapping, new_bundle_sha256=sha(PACKAGE / "bundle.json"), native_manifest_sha256=manifest_sha,
        native_inputs_sha256=native["inputs_sha256"], native_issue_ids_unchanged=True, transferred_rows=len(mapping),
        basis="Outer ACK(90) 2026-10-03 02:42:53 and direct task authorization; object bytes unchanged",
        new_findings=[], active_registry_written=False))
    plan = executor.prepare(PACKAGE, BASE / "native")
    save("transaction-plan.json", plan)
    image_rows = []
    for entry in bundle["boot_group"]["members"]:
        if entry["target"] not in bundle_tool.IMAGE_TARGETS:
            continue
        old_entry = next(row for row in u12_bundle["boot_group"]["members"] if row["target"] == entry["target"])
        if old_entry["sha256"] != entry["sha256"]:
            raise ValueError("FZ-005 image object changed")
        image_rows.append(dict(target=entry["target"], sha256=entry["sha256"], old_bundle_sha256=sha(u12_root / "bundle.json"),
            old_package_manifest_sha256=u12_bundle["native"]["manifest"]["sha256"], new_package_manifest_sha256=manifest_sha,
            new_bundle_sha256=sha(PACKAGE / "bundle.json"), old_base_bundle_sha256=BASE_SHA, new_base_bundle_sha256=BASE_SHA,
            approved_object_unchanged=True, receipt_sha256=bundle["paired_build_receipt"]["sha256"]))
    save("image-binding-transfer.json", dict(rows=image_rows, count=len(image_rows), rebuild=False, build_receipt_status=plan["build_receipt"]["status"]))
    for name, source in [("bundle.json", PACKAGE / "bundle.json"), ("native-manifest.json", PACKAGE / "native/package.json"),
                         ("native-inputs.json", PACKAGE / "native/native-checks/native-gates.json")]:
        destination = HERE / "manifests" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    print("REBIND static_preview=PASS native_active=PASS new_admissions=3 native_registry_rows_changed=0")
    print("bundle=" + sha(PACKAGE / "bundle.json") + " manifest=" + manifest_sha + " inputs=" + native["inputs_sha256"])
    print("transaction additions=3 changes=" + str(len(plan["changes"])) + " FZ005_objects=" + str(len(image_rows)))


if __name__ == "__main__":
    main()
