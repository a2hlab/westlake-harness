import json
from pathlib import Path

from common import BCP, HERE, MASTER, NATIVE, REPO, load, save, sha
from validation import FLUTTER, MANIFEST, INPUTS, READONLY_STRINGS_SHA, check_admission, check_atomic, check_pair_template, check_preview
import auto_approve_exceptions as auto


def main():
    gate_path = MASTER / "knowledge/gates/native-predeploy-exceptions.json"
    admission_path = MASTER / "knowledge/gates/new-native-admissions.json"
    before = {str(path.relative_to(MASTER)): sha(path) for path in [gate_path, admission_path]}
    approval_path = MASTER / "benchmark/2026-10-03-u15-review/outer-approval-strings.json"
    approval = json.loads(approval_path.read_text())
    if sha(NATIVE / "strings-review.json") != READONLY_STRINGS_SHA or READONLY_STRINGS_SHA not in approval["object"]:
        raise ValueError("Signed strings object drift")
    if approval["signer"] != "outer(claude)" or approval["decision"] != "approve all 20 rows":
        raise ValueError("Unexpected strings approval")
    save("evidence/outer-approval-strings.json", approval)
    old_path, new_path = [NATIVE / "evidence" / ("native-" + label + ".json") for label in ["u14", "u15"]]
    old, new = [json.loads(path.read_text()) for path in [old_path, new_path]]
    registry = json.loads(gate_path.read_text())
    matched, rejected = auto.classify(new, [old], registry["exceptions"])
    if new["errors"] or len(matched) != 204 or rejected or new["package_manifest_sha256"] != MANIFEST or new["inputs_sha256"] != INPUTS:
        raise ValueError("Native partial no longer has exactly 204 inherited findings")
    native = json.loads((NATIVE / "manifests/native-manifest.json").read_text())
    baseline = json.loads((NATIVE / "manifests/old-native-manifest.json").read_text())
    check_atomic(native["files"])
    rows, mappings = [], []
    old_findings = {(gate, finding["issue_id"]): finding for gate, data in old["gates"].items() for finding in data["findings"]}
    for gate, finding, prior in matched:
        rows.append(dict(gate=gate, issue_id=finding["issue_id"], package_manifest_sha256=MANIFEST, inputs_sha256=INPUTS,
            reason="Same approved U14 finding; current partial preview only. Fresh final report and binding required.",
            approved_by="auto-identical(outer rule 2026-10-01)", approved_at=prior["approved_at"],
            removal_condition=prior["removal_condition"],
            evidence=["benchmark/2026-10-03-u15-native-v2/evidence/native-u14.json", "benchmark/2026-10-03-u15-native-v2/evidence/native-u15.json"],
            auto_from=dict(package_manifest_sha256=prior["package_manifest_sha256"], issue_id=prior["issue_id"])))
        semantic = auto.fingerprint(gate, finding).encode()
        previous = old_findings[(gate, prior["issue_id"])]
        import hashlib
        mappings.append(dict(gate=gate, old_issue_id=prior["issue_id"], partial_issue_id=finding["issue_id"], final_issue_id=None,
            semantic_sha256=hashlib.sha256(semantic).hexdigest(), baseline_semantic_sha256=hashlib.sha256(auto.fingerprint(gate, previous).encode()).hexdigest()))
    preview = dict(schema_version=1, exceptions=rows, applied=False, execution_enabled=False, final_binding_ready=False,
        partial_manifest_sha256=MANIFEST, partial_inputs_sha256=INPUTS, final_manifest_sha256=None, final_inputs_sha256=None)
    check_preview(preview, mappings)
    save("registry-delta.preview.json", preview)
    save("old-partial-final-mapping.json", mappings)
    target = "/system/android/lib64/westlake_flutter/libandroid.so"
    decision = dict(target=target, candidate_sha256=FLUTTER, target_present_in_baseline=target in baseline["live_hashes"],
        baseline_sha256=baseline["live_hashes"].get(target), new_native_row_required=False, admissions=[], applied=False,
        content_baseline="U14 common9b42 / 61bf589; no promotion claim",
        gate_rule="generation_static_checks.py:128 only enters new-native admission when deployed is None",
        conditional_rule="Re-evaluate actual per-board effective transaction base. If target absent, stop and seek exact final-bound admission; never forge a replacement row.")
    check_admission(decision)
    save("flutter-admission-decision.json", decision)
    save("evidence/atomic-files.json", {name: digest for name, digest in native["files"].items() if name in
        ["payload/runtime/appspawn-x", "payload/android/lib64/libapp_native_loader.so", "payload/route/libapp_native_loader.so", "payload/android/lib64/westlake_flutter/libandroid.so"]})
    pair = json.loads((BCP / "paired-receipt.template.json").read_text())
    plan = json.loads((BCP / "plan.json").read_text())
    images = [row["name"] for row in json.loads((BCP / "expected-images.json").read_text())]
    inputs = {row["name"]: row["sha256"] for row in plan["bcp"]}
    check_pair_template(pair, inputs, images)
    pair["receipt_rule"] = "Validate both actual live runs; strict bytes and any new paired exception separately reviewed. Driver rc6 is only historical reference mismatch."
    pair["argv_hash_encoding"] = "SHA256 of compact JSON actual_argv; original argv-file raw SHA is separately retained"
    save("paired-receipt.template.json", pair)
    save("expected-pair.json", dict(inputs=inputs, images=images, planned_argv=json.loads((BCP / "planned-argv.json").read_text()),
        plan_sha256=sha(BCP / "plan.json"), input_inventory_sha256=sha(BCP / "input-inventory.json")))
    arrival = dict(execution_enabled=False, promotion_confirmed=False, final_bundle_sha256=None, final_native_manifest_sha256=None,
        final_inputs_sha256=None, transaction_base={"common": None, "61b": None},
        native_partial=dict(path="$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u15-native-v2/.artifacts/native-only", manifest_sha256=MANIFEST, inputs_sha256=INPUTS),
        bcp_images=dict(status="WAITING_COMPLETE_RELEASE_AND_PAIRED_PROOF", selected_run=None, output_sha256=None,
            release="$WORKSPACES/westlake-inputs/generations/u15-bt-bake-9e55-94a9-v1", count=27),
        runtime_jar=dict(status="WAITING_SINGLE_U15_V1", sha256=None, path=None, old_sha256="0349eb834e66bc1bf142fd31f08aa0c8a0536534e3ec6b01b5dcc1d930b0a0d4",
            in_bcp=False, patches=["same-package trampoline delayed terminate", "fd-api alias target theme", "ActivityManagerAdapter nativeConsumeConnectionFailure declaration"]),
        checklist=["validate incoming release SHA256SUMS and both complete runs plus frozen tool/live tee/actual argv/rc",
            "strict compare all27; no U14/T7d exception transfer; any difference requires fresh object-chain and outer review",
            "pin one runtime JAR donor and actual recipe/logs; inspect class changes against explicit effective baseline",
            "compose native partial + both BCP underlays/effective overlays +27images +runtime JAR as one disabled version",
            "fresh N1/N2/static/strings/classes/imports/ABI/consumer; reclassify exact204 and recompute final issue IDs",
            "re-evaluate per-board transaction base and local installer; no implicit U14 promotion",
            "apply strings approval only to same bytes and both ANL aliases+host; do not write active tables in this lane",
            "outer signs exact final findings/images/admissions and production replay before any execution"])
    save("assembly-arrival.json", arrival)
    save("source-receipts.json", [dict(path="$WORKSPACES/westlake-harness-bms/" + str(path.relative_to(REPO)), sha256=sha(path))
        for path in [old_path, new_path, NATIVE / "strings-review.json", BCP / "paired-receipt.template.json", BCP / "plan.json"]] +
        [dict(path="benchmark/2026-10-03-u15-review/outer-approval-strings.json", master_commit="d8858dd1d1", sha256=sha(approval_path)),
         dict(path="scripts/lab/generation_static_checks.py", sha256=sha(MASTER / "scripts/lab/generation_static_checks.py")),
         dict(path="scripts/lab/auto_approve_exceptions.py", sha256=sha(MASTER / "scripts/lab/auto_approve_exceptions.py"))])
    after = {str(path.relative_to(MASTER)): sha(path) for path in [gate_path, admission_path]}
    if before != after:
        raise ValueError("Active input changed while preparing the packet")
    save("active-inputs-unchanged.json", dict(before=before, after=after, writes=False))
    print("U15 PREP: 204 preview mappings (N1=99/N2=105), final binding null, Flutter replacement needs 0 new-native rows")
    print("PAIR: 9 pinned inputs / 27 null outputs x2; JAR and complete bake pending; gates untouched")


if __name__ == "__main__":
    main()
