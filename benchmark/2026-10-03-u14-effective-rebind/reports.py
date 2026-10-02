import argparse
from datetime import datetime
import json
from pathlib import Path
import platform
import subprocess
import sys

from finalize import HERE, MASTER, PRIOR, WS, portable, save, sha
from validation import map_pending
import auto_approve_exceptions as auto
import generation_static_checks as static


def expand(value):
    return Path(value.replace("$WORKSPACES", str(WS)).replace("$REPO", str(HERE.parents[1])))


def capture(root, name, command):
    process = subprocess.run([str(item) for item in command], capture_output=True, text=True, errors="replace")
    raw = root / ".artifacts/raw" / (name + ".txt")
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text(process.stdout + process.stderr)
    proof = root / "evidence" / (name + ".txt")
    proof.parent.mkdir(parents=True, exist_ok=True)
    proof.write_text(portable(raw.read_text()))
    print(name + " exit=" + str(process.returncode), flush=True)
    return dict(command=command, exit_code=process.returncode, raw=raw, raw_sha256=sha(raw), evidence=proof, evidence_sha256=sha(proof))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=["common", "61b"], required=True)
    args = parser.parse_args()
    if platform.system() != "Darwin":
        raise ValueError("Mac-only review during U13 windows")
    root = HERE / args.variant
    composition = json.loads((root / "composition.json").read_text())
    candidate = expand(composition["package"])
    baseline = expand(composition["transaction_base"])
    if sha(candidate / "bundle.json") != composition["bundle_sha256"] or sha(baseline / "bundle.json") != composition["transaction_base_sha256"]:
        raise ValueError("Variant identity changed")
    records = []
    native_reports = {}
    for label, package in [("u13", baseline), ("u14", candidate)]:
        records.append(capture(root, "native-" + label, [sys.executable, MASTER / "scripts/lab/native_predeploy.py",
            "--package", package / "native", "--inputs", package / "native/native-checks/native-gates.json", "--readelf", "llvm-readelf"]))
        report = json.loads((root / ".artifacts/raw" / ("native-" + label + ".txt")).read_text())
        if report["errors"]:
            raise ValueError("Invalid fresh report: " + str(report["errors"]))
        native_reports[label] = report
        save(root / "evidence" / ("native-" + label + ".json"), report)
    registry_path = MASTER / "knowledge/gates/native-predeploy-exceptions.json"
    registry_sha = sha(registry_path)
    registry = json.loads(registry_path.read_text())
    matched, new = auto.classify(native_reports["u14"], [native_reports["u13"]], registry["exceptions"])
    evidence = ["benchmark/2026-10-03-u14-effective-rebind/" + args.variant + "/evidence/native-" + label + ".json" for label in ["u13", "u14"]]
    preview = [dict(gate=gate, issue_id=finding["issue_id"], package_manifest_sha256=composition["native_manifest_sha256"],
        inputs_sha256=composition["native_inputs_sha256"], reason="Identical approved U13 finding; conditional binding preview, not applied",
        approved_by="auto-identical(outer rule 2026-10-01)", approved_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        removal_condition=prior["removal_condition"], evidence=evidence,
        auto_from=dict(package_manifest_sha256=prior["package_manifest_sha256"], issue_id=prior["issue_id"])) for gate, finding, prior in matched]
    fresh = [dict(gate=gate, **finding) for gate, finding, _ in new]
    save(root / "registry-delta.json", dict(schema_version=1, exceptions=preview, applied=False, execution_enabled=False))
    save(root / "needs-outer-review.json", dict(package_manifest_sha256=composition["native_manifest_sha256"], inputs_sha256=composition["native_inputs_sha256"], new_findings=fresh, approved_by=None, applied=False))
    old = json.loads((PRIOR / "needs-outer-review.json").read_text())
    mapping = map_pending(old["new_findings"], fresh)
    save(root / "pending-id-map.json", dict(old_manifest_sha256=old["package_manifest_sha256"], new_manifest_sha256=composition["native_manifest_sha256"],
        mappings=mapping, removed_old_issue_ids=sorted({row["issue_id"] for row in old["new_findings"]} - {row["old_issue_id"] for row in mapping}), applied=False))
    static_report = static.check(candidate, baseline, {})
    save(root / "evidence/static-vs-u13.json", static_report)
    records.append(capture(root, "auto-identical-preview", [sys.executable, MASTER / "scripts/lab/auto_approve_exceptions.py", "--candidate", root / "evidence/native-u14.json", "--baseline", root / "evidence/native-u13.json"]))
    if registry_sha != sha(registry_path):
        raise ValueError("Active exception registry changed during offline task")
    save(root / "results.json", dict(bundle_sha256=composition["bundle_sha256"], native_manifest_sha256=composition["native_manifest_sha256"],
        native_inputs_sha256=composition["native_inputs_sha256"], transaction_base_sha256=composition["transaction_base_sha256"],
        native_status=native_reports["u14"]["status"], static_status=static_report["status"], identical_preview_count=len(preview),
        new_findings={gate: sum(row["gate"] == gate for row in fresh) for gate in ["N1", "N2"]},
        pending_semantic_unchanged=sum(row["semantic_unchanged"] for row in mapping),
        active_registry_sha256=registry_sha, active_registry_updated=False, abi_v2_status=composition["abi_v2_status"],
        promotion_confirmed=False, execution_enabled=False, vm_used=False, records=records))
    print("preview=" + str(len(preview)) + " new=" + str(len(fresh)) + " pending_exact_matches=" + str(sum(row["semantic_unchanged"] for row in mapping)))


if __name__ == "__main__":
    main()
