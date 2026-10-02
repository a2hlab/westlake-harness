"""N1/N2 and identical-exception preview; master registry is never modified."""
from datetime import datetime
import json
import sys

from common import BASE, HERE, MASTER, PACKAGE, capture, save, sha
import auto_approve_exceptions as auto
import native_predeploy


def main():
    registry_path = MASTER / "knowledge/gates/native-predeploy-exceptions.json"
    registry_before = sha(registry_path)
    reports = {}
    for name, package in [("u12", BASE / "native"), ("u13", PACKAGE / "native")]:
        command = capture("native-" + name, [sys.executable, MASTER / "scripts/lab/native_predeploy.py", "--package", package, "--inputs", package / "native-checks/native-gates.json", "--readelf", "llvm-readelf"])
        report = json.loads((HERE / ".artifacts/raw" / ("native-" + name + ".txt")).read_text())
        if report["errors"]:
            raise ValueError(report["errors"])
        reports[name] = report
        save("evidence/native-" + name + ".json", report)
        save("evidence/native-" + name + "-command.json", command)
    preview = capture("auto-identical-preview", [sys.executable, MASTER / "scripts/lab/auto_approve_exceptions.py", "--candidate", HERE / "evidence/native-u13.json", "--baseline", HERE / "evidence/native-u12.json"])
    registry = json.loads(registry_path.read_text())
    matched, new = auto.classify(reports["u13"], [reports["u12"]], registry["exceptions"])
    delta = []
    evidence = ["benchmark/2026-10-02-u13-assembly-draft/evidence/native-" + name + ".json" for name in ["u13", "u12"]]
    for gate, finding, source in matched:
        delta.append(dict(gate=gate, package_manifest_sha256=reports["u13"]["package_manifest_sha256"], inputs_sha256=reports["u13"]["inputs_sha256"], issue_id=finding["issue_id"], reason="Semantically identical to approved U12 finding; preview only, no registry application", removal_condition=source["removal_condition"], evidence=evidence, approved_by=auto.AUTO, approved_at=datetime.now().astimezone().isoformat(timespec="seconds"), auto_from=dict(package_manifest_sha256=source["package_manifest_sha256"], issue_id=source["issue_id"])))
    save("registry-delta.json", dict(exceptions=delta, applied=False, registry_before_sha256=registry_before))
    save("outer-review.json", dict(package_manifest_sha256=reports["u13"]["package_manifest_sha256"], inputs_sha256=reports["u13"]["inputs_sha256"], new_findings=[dict(finding, gate=gate) for gate, finding, _ in new], approved_by=None, execution_enabled=False))
    proposed = HERE / ".artifacts/proposed-exceptions.json"
    save(proposed, dict(registry, exceptions=registry["exceptions"] + delta))
    replay = native_predeploy.check_package(PACKAGE / "native", PACKAGE / "native/native-checks/native-gates.json", exceptions=proposed, readelf="llvm-readelf")
    save("evidence/native-proposed-registry.json", replay)
    if sha(registry_path) != registry_before:
        raise ValueError("master registry changed during preview; rerun on stable registry")
    summary = dict(bundle_sha256=sha(PACKAGE / "bundle.json"), native_manifest_sha256=sha(PACKAGE / "native/package.json"), baseline_status=reports["u12"]["status"], default_status=reports["u13"]["status"], findings={gate: dict(baseline=len(reports["u12"]["gates"][gate]["findings"]), candidate=len(reports["u13"]["gates"][gate]["findings"])) for gate in ["N1", "N2"]}, identical=len(matched), new=len(new), preview=preview, proposed_registry_replay_status=replay["status"], registry_unchanged=True, execution_enabled=False)
    save("native-gates.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
