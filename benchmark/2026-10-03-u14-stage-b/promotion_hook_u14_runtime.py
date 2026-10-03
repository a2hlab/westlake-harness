"""Disabled U14 retention hook; reuse full U14 transaction rollback to armed U13."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
H = HERE
R = HERE.parents[1]
W = Path(os.environ.get("WORKSPACES", R.parent))
M = W / "westlake-harness"
sys.path.insert(0, str(M / "scripts/lab"))
import generation_bundle as gb
import u7_executor as u
import lab_paths
import deployment_native_gate as native_gate
import retention_criteria as criteria

CANDIDATE = None
previous = None


def path(value):
    if not value:
        raise ValueError("explicit path required")
    return Path(os.path.expanduser(os.path.expandvars(str(value).replace("$WORKSPACES/", str(W) + "/"))))


def composition():
    return json.loads((H / "composition.json").read_text())


def configure(folder):
    global H, CANDIDATE, previous
    H = Path(folder)
    CANDIDATE = path(composition()["package"])
    source = H / "transaction_backend.py"
    spec = importlib.util.spec_from_file_location("u14_transaction_" + H.name, source)
    previous = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(previous)
    original_vm = previous.vm
    def configured_vm(command):
        if len(command) > 1 and str(command[1]) == str(source.resolve()):
            command = [command[0], H / "runner.py", "hook", *command[2:]]
        return original_vm(command)
    previous.vm = configured_vm


def require_enabled():
    assert composition().get("execution_enabled") is True, "U14 Stage B disabled; future outer authorization required"


def signed_composition(value, decision=None):
    armed_path = path(value["package"]) / "bundle.json"
    unarmed_path = path(value["unarmed_package"]) / "bundle.json"
    assert gb.sha(armed_path) == value["bundle_sha256"], "armed bundle drift"
    assert gb.sha(unarmed_path) == value["approved_unarmed_bundle_sha256"], "signed unarmed bundle drift"
    armed, unarmed = json.loads(armed_path.read_text()), json.loads(unarmed_path.read_text())
    assert armed["rollout_ready"] is True and unarmed["rollout_ready"] is False, "arming state mismatch"
    assert armed.get("rollout_blocker") == "", "armed blocker not cleared"
    armed["rollout_ready"] = False
    armed["rollout_blocker"] = unarmed["rollout_blocker"]
    assert armed == unarmed, "arming changed payload or other metadata"
    bound = value["approved_unarmed_bundle_sha256"]
    if decision and decision.get("bundle_sha256") == value["bundle_sha256"]:
        bound = value["bundle_sha256"]
    return dict(bundle_sha256=bound, native_manifest_sha256=value["native_manifest_sha256"])


def native_tickets_admission(surface, value):
    report = json.loads((H / "gates" / surface / "executor").read_text())
    assert report.get("deployable") is True and report.get("gates_passed") is True, "full executor native receipt not deployable"
    assert report.get("bundle_sha256") == value["bundle_sha256"], "full executor bundle drift"
    assert path(report.get("root")).resolve() == CANDIDATE.resolve(), "full executor candidate path drift"
    baseline = path(value["base_bundle"]) / "native"
    assert path(report.get("baseline_native")).resolve() == baseline.resolve(), "full executor baseline path drift"
    tickets = report.get("native_tickets")
    assert isinstance(tickets, list) and len(tickets) == 2, "full candidate and baseline native tickets required"
    for ticket, expected in zip(tickets, [CANDIDATE / "native", baseline]):
        assert isinstance(ticket, dict) and path(ticket.get("package")).resolve() == expected.resolve(), "native ticket owner path drift"
        assert isinstance(ticket.get("binding"), str) and ticket["binding"], "native ticket binding absent"
        normalized = dict(ticket, package=str(expected.resolve()))
        native_gate.assert_unchanged(normalized)


def admission():
    require_enabled()
    value = composition()
    signed_composition(value)
    assert gb.sha(CANDIDATE / "native/package.json") == value["native_manifest_sha256"], "manifest drift"
    assert gb.sha(CANDIDATE / "native/native-checks/native-gates.json") == value["native_inputs_sha256"], "native inputs drift"
    assert gb.sha(path(value["base_bundle"]) / "bundle.json") == value["base_bundle_sha256"], "armed U13 restoration base drift"
    authorization = json.loads(path(value["stage_b_authorization"]).read_text())
    assert authorization.get("signed_by") == "outer(claude)" and authorization.get("promotion_authorized") is True, "Stage B authorization absent"
    assert authorization.get("bundle_sha256") == value["bundle_sha256"] and authorization.get("native_manifest_sha256") == value["native_manifest_sha256"], "Stage B authorization package drift"
    review = json.loads((HERE / "inputs/outer-smoke-review.json").read_text())
    assert gb.sha(HERE / "inputs/outer-smoke-review.json") == value["smoke_review_sha256"] and review["signer"] == "outer(claude)", "smoke review drift"
    for serial, spec_name in value["smoke_specs"].items():
        assert gb.sha(H / spec_name) == value["smoke_sha256"][serial], "candidate smoke spec drift"
        assert gb.sha(H / value["recovery_smoke_specs"][serial]) == value["recovery_smoke_sha256"][serial], "restoration smoke spec drift"
        spec_body = json.loads((H / spec_name).read_text())
        assert spec_body.get("control_selftest") is True, "control crypto gate absent"
        assert spec_body["probe"]["copy_limits"] == value["copy_limits"], "signed copy ceiling changed"
        assert spec_body["probe"]["single_copy"] == ["libart.so", "libopenjdkjvm.so", *value["copy_limits"]], "ART/JVM single-copy gate changed"
        expected = value["candidate_boards"][serial]
        expected_fp = {"runtime_fp": expected["fingerprints"]["runtime"]["sha256_12"], "boot_fp": expected["fingerprints"]["boot"]["sha256_12"]}
        assert spec_body["expect"] == expected_fp, "smoke fingerprint mismatch"
    for surface in ["mac", "vm"]:
        proof = json.loads((H / ("gate-" + surface + "-pass.json")).read_text())
        assert proof["bundle_sha256"] == value["bundle_sha256"] and proof["native_manifest_sha256"] == value["native_manifest_sha256"], "offline receipt package drift"
        assert proof["policy_binding"] == u.policy_binding(CANDIDATE), "offline policy inputs changed"
        assert proof["production_dry_run_exit_code"] == 0 and proof["gates_passed"] and proof["deployable"], "offline gates not all green"
        assert proof["static"] == "PASS" and proof["G1"] and proof["G2"] and proof["frozen_composed_violations"] == 0, "static/image/frozen regression"
        assert all(proof["native_findings"][gate]["rejected"] == 0 for gate in ["N1", "N2"]), "native admission rejected"
        native_tickets_admission(surface, value)


def validate_plan(plan):
    value = composition()
    serial = plan["serial"]
    assert serial in value["candidate_boards"], "plan belongs to another board variant"
    assert plan["phase"] == "B" and plan["package"] == value["package"], "promotion package/phase mismatch"
    assert plan["native_inputs_sha256"] == value["native_inputs_sha256"], "plan native inputs mismatch"
    assert plan["restore"]["state"] == "U13" and plan["restore"]["bundle_sha256"] == value["base_bundle_sha256"], "plan restoration bundle mismatch"
    assert (plan["restore"]["identity_assertions"], plan["restore"]["unique_paths"]) == (321, 319), "plan restoration identity truncated"
    assert path(plan["smoke_spec"]) == H / value["smoke_specs"][serial], "plan candidate smoke path mismatch"
    assert path(plan["before_unlock_restored_spec"]) == H / value["recovery_smoke_specs"][serial], "plan restoration smoke path mismatch"
    assert "$" not in str(path(plan["out"])), "fresh U14_B_RUN_ID is required before enabling a plan"


def retention_reason(decision, value, reference, smoke):
    if not isinstance(decision, dict):
        return "outer screenshot signoff absent"
    gate = decision.get("process_selftest_gate") or {}
    if not gate.get("report") or not gate.get("explanations") or not gate.get("summary"):
        return "explicit stage_a_selftest report/explanations/summary paths required"
    report, explanations, summary = [path(gate[name]) for name in ["report", "explanations", "summary"]]
    if not all(item.is_file() for item in [report, explanations, summary]):
        return "stage_a_selftest output absent"
    if gb.sha(explanations) != gate.get("explanations_sha256") or gb.sha(summary) != gate.get("summary_sha256"):
        return "stage_a_selftest explanations/summary binding drift"
    tool = gate.get("tool") or {}
    if tool.get("path") != "$WORKSPACES/westlake-harness/scripts/lab/stage_a_selftest.py" or tool.get("exit_code") != 0 or tool.get("sha256") != gb.sha(M / "scripts/lab/stage_a_selftest.py"):
        return "fresh stage_a_selftest tool/exit binding absent"
    measured = json.loads(summary.read_text())
    data = json.loads(report.read_text())
    if measured.get("failure_lines_any_pid") != 0:
        return "any-pid selftest failure unconditionally rejects promotion"
    if measured.get("records") != len(data.get("runs", [])) or measured.get("report_sha256") != gb.sha(report):
        return "stage_a_selftest summary coverage drift"
    if measured.get("root") != gate.get("root") or measured.get("pattern") != gate.get("pattern"):
        return "stage_a_selftest root/pattern drift"
    if path(measured.get("root")) != path(value["stage_a_selection"]["root"]) or measured.get("pattern") != value["stage_a_selection"]["pattern"]:
        return "selftest selection is not the complete U14 candidate runner domain"
    review = json.loads(explanations.read_text())
    if review.get("report_sha256") != gb.sha(report):
        return "selftest explanations report mismatch"
    return criteria.retention_reason(decision, signed_composition(value, decision), reference, smoke, report, explanations)


def stage_a_admission(decision_path):
    value = composition()
    reference = json.loads((HERE / "inputs/reference.json").read_text())
    assert gb.sha(HERE / "inputs/reference.json") == value["reference_sha256"], "reference snapshot drift"
    assert decision_path and decision_path.is_file(), "Stage A screenshot signoff absent"
    decision = json.loads(decision_path.read_text())
    assert decision.get("release") == "U14" and decision.get("phase") == "A", "fresh U14 Stage A signoff required"
    assert decision.get("signed_at") and decision.get("promotion_authorized") is True, "separate Stage B outer authorization required"
    assert decision.get("reference_sha256") == value["reference_sha256"], "Stage A reference drift"
    assert decision.get("native_inputs_sha256") == value["native_inputs_sha256"], "Stage A inputs drift"
    assert decision.get("effective_baseline_bundle_sha256") == value["base_bundle_sha256"], "Stage A U13 baseline mismatch"
    reason = retention_reason(decision, value, reference, {"passed": True})
    assert reason is None, "Stage A prerequisite: " + str(reason)


def verify_candidate(serial, root):
    previous.verify(serial, root, candidate=True)
    identity = json.loads((root / "identity.json").read_text())
    expected = composition()["candidate_boards"][serial]
    assert identity["diff"] == {} and identity["absent"] == [], "candidate identity mismatch"
    assert identity["fingerprints"] == expected["fingerprints"], "candidate fingerprint mismatch"
    assert identity["identity_assertions"] == expected["identity_assertions"] == 322, "complete 322 assertions required"
    assert identity["unique_paths"] == expected["unique_paths"] == 320, "complete 320 unique paths required"
    (root / "candidate-identity.json").write_text(json.dumps(identity, indent=2) + "\n")


def record_window(serial, root, plan_path):
    plan = json.loads(plan_path.read_text())
    value = composition()
    assert plan["serial"] == serial and plan["phase"] == "B", "plan serial/phase mismatch"
    assert plan["execution_enabled"] is True and plan["bundle_sha256"] == value["bundle_sha256"] and plan["package_manifest_sha256"] == value["native_manifest_sha256"], "plan binding/authorization drift"
    root.mkdir(parents=True, exist_ok=True)
    receipt = root / "window-input.json"
    assert not receipt.exists() and not (root / "transaction/journal.json").exists(), "fresh window output required"
    receipt.write_text(json.dumps(dict(serial=serial, phase="B", bundle_sha256=value["bundle_sha256"],
        package_manifest_sha256=value["native_manifest_sha256"], expected_fingerprints=value["candidate_boards"][serial]["fingerprints"],
        plan_sha256=gb.sha(plan_path), plan=plan), indent=2) + "\n")


def finish(serial, root, restored_spec, decision_path, stage_a_path=None):
    value = composition()
    smoke_path = root / "runner/smoke/smoke-result.json"
    identity_path = root / "post-apply/candidate-identity.json"
    reason = "Stage A prerequisite absent"
    try:
        decision = json.loads(decision_path.read_text()) if decision_path and decision_path.is_file() else None
        stage_a_admission(stage_a_path)
        smoke = json.loads(smoke_path.read_text())
        assert smoke.get("passed") is True, "fresh activation smoke did not pass"
        assert isinstance(decision, dict) and decision.get("signed_by") == "outer(claude)" and decision.get("signed_at"), "fresh outer screenshot review absent"
        assert decision.get("release") == "U14" and decision.get("serial") == serial and decision.get("phase") == "B", "fresh same-board Stage B decision required"
        assert decision.get("window_root") == str(root), "fresh window-bound decision required"
        assert decision.get("bundle_sha256") == value["bundle_sha256"] and decision.get("native_manifest_sha256") == value["native_manifest_sha256"], "fresh decision package mismatch"
        assert decision.get("controls_t20_lit") == ["helloworld", "zigzag"] and decision.get("confirmed_regressions") == [], "fresh control screenshots/regressions refused"
        assert decision.get("smoke_sha256") == gb.sha(smoke_path) and decision.get("identity_sha256") == gb.sha(identity_path), "fresh smoke/identity SHA mismatch"
        admission()
        verify_candidate(serial, root / "retained-final")
        reason = None
    except Exception as error:
        reason = str(error)
    if reason is None:
        (root / "retention.json").write_text(json.dumps(dict(retained=True, basis=str(decision_path), release="U14", scope="complete fresh outer-signed promotion"), indent=2) + "\n")
        return
    (root / "retention.json").write_text(json.dumps(dict(retained=False, reason=reason, restore="U13"), indent=2) + "\n")
    previous.finish(serial, root, restored_spec)


def main():
    require_enabled()
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial", choices=sorted(lab_paths.boards("oh")), required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--restored-spec", type=Path)
    parser.add_argument("--decision", type=Path)
    parser.add_argument("--stage-a-decision", type=Path)
    parser.add_argument("--plan", type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    for name in ["apply", "finish", "verify-candidate", "verify-base"]:
        group.add_argument("--" + name, action="store_true")
    args = parser.parse_args()
    if args.apply:
        admission()
        stage_a_admission(args.stage_a_decision)
        record_window(args.serial, args.root, args.plan)
        previous.verify(args.serial, args.root / "baseline")
        previous.executor(args.serial, args.root)
        verify_candidate(args.serial, args.root / "post-apply")
    elif args.verify_base:
        previous.verify(args.serial, args.root)
    elif args.verify_candidate:
        verify_candidate(args.serial, args.root)
    else:
        assert args.restored_spec is not None and args.decision is not None
        finish(args.serial, args.root, args.restored_spec, args.decision, args.stage_a_decision)


if __name__ == "__main__":
    main()
