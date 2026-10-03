import argparse
import json
from pathlib import Path
import sys

from common import HERE, MASTER, NATIVE, load, save, sha
from validation import check_atomic
import auto_approve_exceptions as auto
import generation_bundle


def main():
    parser = argparse.ArgumentParser(description="Produce final-bound previews from a fresh report; never apply registry rows")
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    bundle, _, _ = generation_bundle.validate(args.bundle)
    manifest = generation_bundle.member(args.bundle, bundle["native"]["manifest"])
    inputs_path = manifest.parent / "native-checks/native-gates.json"
    expected = load("expected-pair.json")
    members = generation_bundle.bcp_members(args.bundle, bundle, json.loads(manifest.read_text()))
    if {name + ".jar": sha(path) for name, path in members.items()} != expected["inputs"]:
        raise ValueError("Complete final nine-input BCP pair is required")
    if bundle["runtime_jar"]["sha256"] == load("assembly-arrival.json")["runtime_jar"]["old_sha256"]:
        raise ValueError("New single U15 runtime JAR has not arrived")
    native = json.loads(manifest.read_text())
    check_atomic(native["files"])
    candidate = json.loads(args.report.read_text())
    if candidate.get("package_manifest_sha256") != sha(manifest) or candidate.get("inputs_sha256") != sha(inputs_path) or candidate.get("errors"):
        raise ValueError("Fresh report does not bind this exact package/inputs or has errors")
    gate_path = MASTER / "knowledge/gates/native-predeploy-exceptions.json"
    prior_registry = sha(gate_path)
    baseline = json.loads((NATIVE / "evidence/native-u14.json").read_text())
    matched, new = auto.classify(candidate, [baseline], json.loads(gate_path.read_text())["exceptions"])
    partial = json.loads((NATIVE / "evidence/native-u15.json").read_text())
    partial_ids = {auto.fingerprint(gate, finding): finding["issue_id"] for gate, data in partial["gates"].items() for finding in data["findings"]}
    if new or len(matched) != 204 or set(partial_ids) != {auto.fingerprint(gate, finding) for gate, finding, _ in matched}:
        raise ValueError("Final semantics differ; stop and ask outer, do not copy approvals")
    rows, mappings = [], []
    public_report = dict(package_manifest_sha256=candidate["package_manifest_sha256"], inputs_sha256=candidate["inputs_sha256"],
        status=candidate["status"], errors=candidate["errors"],
        gates={gate: dict(findings=data["findings"]) for gate, data in candidate["gates"].items()},
        original_report_sha256=sha(args.report), rule="Exact finding excerpt; full fresh report remains at caller's persistent path")
    save("evidence/final-findings.json", public_report)
    for gate, finding, prior in matched:
        rows.append(dict(gate=gate, issue_id=finding["issue_id"], package_manifest_sha256=sha(manifest), inputs_sha256=sha(inputs_path),
            reason="Same approved U14 finding; regenerated final binding preview, not applied",
            approved_by="auto-identical(outer rule 2026-10-01)", approved_at=prior["approved_at"],
            removal_condition=prior["removal_condition"],
            evidence=["benchmark/2026-10-03-u15-native-v2/evidence/native-u14.json", "benchmark/2026-10-03-u15-admission-prep/evidence/final-findings.json"],
            auto_from=dict(package_manifest_sha256=prior["package_manifest_sha256"], issue_id=prior["issue_id"])))
        mappings.append(dict(gate=gate, old_issue_id=prior["issue_id"], partial_issue_id=partial_ids[auto.fingerprint(gate, finding)], final_issue_id=finding["issue_id"]))
    if sha(gate_path) != prior_registry:
        raise ValueError("Active registry changed during preview")
    save("final-registry-delta.preview.json", dict(schema_version=1, exceptions=rows, applied=False, execution_enabled=False,
        final_binding_ready=True, production_admission=False, manifest_sha256=sha(manifest), inputs_sha256=sha(inputs_path)))
    save("final-id-mapping.json", mappings)
    print("FINAL PREVIEW 204 exact findings; new0; active registry not changed; production still requires outer")


if __name__ == "__main__":
    main()
