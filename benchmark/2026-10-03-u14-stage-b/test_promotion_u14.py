import copy
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import platform
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

import promotion_hook_u14_runtime as hook
import promotion_dispatch_u14 as dispatch
import review_wait_u14 as review
from prepare import COPY_LIMITS, EXPECTED

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("u14_stage_a_tool", hook.M / "scripts/lab/stage_a_selftest.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def load(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def fixture(directory, variant="common"):
    value = copy.deepcopy(load(HERE / variant / "composition.json"))
    for name in ["package", "unarmed_package", "base_bundle"]:
        folder = directory / name
        folder.mkdir()
        shutil.copyfile(HERE / "inputs" / (variant + "-" + name + "-bundle.json"), folder / "bundle.json")
        value[name] = str(folder)
    folder = directory / "context"
    save(folder / "composition.json", value)
    hook.configure(HERE / variant)
    hook.H = folder
    hook.CANDIDATE = directory / "package"
    root = directory / "stage-a"
    pattern = "window*/u14-A*/*/runner/**/record.json"
    value["stage_a_selection"] = dict(root=str(root), pattern=pattern)
    save(folder / "composition.json", value)
    for index, key in enumerate(["helloworld", "zigzag"], 10):
        run = root / "window1/u14-A-fixture/5ea/runner/controls" / key
        save(run / "record.json", dict(key=key, package="fixture." + key, bms=dict(uid=1001), diagnostics=dict(complete=True)))
        (run / "processes-t20.txt").write_text(str(index) + " 1 1001 appspawn-x\n")
        (run / "hilog.txt").write_text("10-03 11:00:00.000 " + str(index) + " " + str(index) + " I app [WL-KS-PROBE] validateAead=OK\n")
    output = directory / "tool-output"
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        code = tool.main(["--root", str(root), "--pattern", pattern, "--out", str(output)])
    if code != 0:
        raise ValueError("synthetic stage_a_selftest refused")
    report = output / "stage-a-selftest.json"
    explanations = output / "stage-a-explanations.json"
    summary = output / "summary.json"
    summary.write_text(stdout.getvalue())
    reference = load(HERE / "inputs/reference.json")
    total = reference["total_lit"]
    decision = dict(schema="outer-stage-a/v1", signed_by="outer(claude)", signed_at="synthetic-known-answer-only", release="U14", phase="A", promotion_authorized=True,
        bundle_sha256=value["approved_unarmed_bundle_sha256"], native_manifest_sha256=value["native_manifest_sha256"], native_inputs_sha256=value["native_inputs_sha256"],
        effective_baseline_bundle_sha256=value["base_bundle_sha256"], reference_sha256=value["reference_sha256"], confirmed_regressions=[],
        stage_A_regression_verdict=dict(u14_reference_lit_total=total, measured=total, same_or_lit_within_k_of_n=total, confirmed_regressions=0),
        process_selftest_gate=dict(report=str(report), report_sha256=hook.gb.sha(report), explanations=str(explanations), explanations_sha256=hook.gb.sha(explanations),
            summary=str(summary), summary_sha256=hook.gb.sha(summary), root=str(root), pattern=pattern,
            measured_records=[row["record"] for row in load(report)["runs"]],
            tool=dict(path="$WORKSPACES/westlake-harness/scripts/lab/stage_a_selftest.py", sha256=hook.gb.sha(hook.M / "scripts/lab/stage_a_selftest.py"), exit_code=0)))
    decision_path = directory / "stage-a-decision.json"
    save(decision_path, decision)
    return value, reference, decision, decision_path


class BindingTests(unittest.TestCase):
    def test_exact_variants_full_maps_disabled(self):
        for variant in ["common", "61b"]:
            value = load(HERE / variant / "composition.json")
            self.assertEqual((value["bundle_sha256"], value["base_bundle_sha256"]), EXPECTED[variant])
            self.assertFalse(value["execution_enabled"])
            restore = load(HERE / variant / "recovery-u13.json")["boards"]
            for serial, identity in value["candidate_boards"].items():
                self.assertEqual((identity["identity_assertions"], identity["unique_paths"], len(identity["expected"])), (322, 320, 320))
                row = restore[serial]
                self.assertEqual((row["identity_assertions"], row["unique_paths"], len(row["expected"])), (321, 319, 319))
                smoke = load(HERE / variant / value["smoke_specs"][serial])
                self.assertTrue(smoke["control_selftest"])
                self.assertEqual(smoke["probe"]["copy_limits"], COPY_LIMITS)
                self.assertEqual(smoke["probe"]["single_copy"], ["libart.so", "libopenjdkjvm.so", *COPY_LIMITS])
            template = load(HERE / variant / "future-stage-a-decision-template.json")
            self.assertIsNone(template["signed_by"])
            self.assertFalse(template["promotion_authorized"])
            for plan_path in (HERE / variant).glob("plan-*.json"):
                plan = load(plan_path)
                self.assertFalse(plan["execution_enabled"] or plan["rollout_ready"])
                self.assertEqual(plan["phase"], "B")
                self.assertEqual(plan["restore"]["state"], "U13")
                self.assertEqual(plan["promotion_policy"]["signature_cutoff_from_lock_minutes"], 20)
                self.assertGreaterEqual(plan["promotion_policy"]["rollback_reserve_minutes"], 10)
                self.assertNotIn("after_shards", plan)

    def test_source_receipts(self):
        for row in load(HERE / "source-provenance.json")["files"]:
            suffix = row["snapshot"].split("/benchmark/" + HERE.name + "/", 1)[1]
            self.assertEqual(hook.gb.sha(HERE / suffix), row["sha256"])

    def test_arming_payload_drift_refuses(self):
        with tempfile.TemporaryDirectory() as temp:
            value, _, _, _ = fixture(Path(temp))
            self.assertEqual(hook.signed_composition(value)["bundle_sha256"], value["approved_unarmed_bundle_sha256"])
            value["bundle_sha256"] = "0" * 64
            with self.assertRaisesRegex(AssertionError, "armed bundle drift"):
                hook.signed_composition(value)

    def test_disabled_before_transport(self):
        hook.configure(HERE / "common")
        dispatch.H = HERE / "common"
        plan = load(dispatch.H / "plan-5ea.json")
        with patch.object(dispatch.subprocess, "run") as transport:
            with self.assertRaises(RuntimeError):
                dispatch.prelock(plan)
            transport.assert_not_called()
        with patch.object(hook.previous, "vm") as transport:
            with self.assertRaisesRegex(AssertionError, "disabled"):
                hook.require_enabled()
            transport.assert_not_called()

    def test_stage_a_tool_binding_drift_refuses(self):
        with tempfile.TemporaryDirectory() as temp:
            value, reference, decision, _ = fixture(Path(temp))
            self.assertIsNone(hook.retention_reason(decision, value, reference, {"passed": True}))
            decision["process_selftest_gate"]["explanations_sha256"] = "0" * 64
            self.assertIn("binding drift", hook.retention_reason(decision, value, reference, {"passed": True}))

    def test_stage_a_selection_and_any_pid_refuse(self):
        with tempfile.TemporaryDirectory() as temp:
            value, reference, decision, _ = fixture(Path(temp))
            value["stage_a_selection"]["pattern"] = "U13-controls-only/**/record.json"
            self.assertIn("complete U14", hook.retention_reason(decision, value, reference, {"passed": True}))
            summary_path = Path(decision["process_selftest_gate"]["summary"])
            summary = load(summary_path)
            summary["failure_lines_any_pid"] = 1
            save(summary_path, summary)
            decision["process_selftest_gate"]["summary_sha256"] = hook.gb.sha(summary_path)
            self.assertIn("any-pid", hook.retention_reason(decision, value, reference, {"passed": True}))

    def test_exact_candidate_verification_counts(self):
        hook.configure(HERE / "common")
        serial, expected = next(iter(hook.composition()["candidate_boards"].items()))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            identity = dict(diff={}, absent=[], fingerprints=expected["fingerprints"], identity_assertions=322, unique_paths=320)
            save(root / "identity.json", identity)
            with patch.object(hook.previous, "verify"):
                hook.verify_candidate(serial, root)
                identity["unique_paths"] = 319
                save(root / "identity.json", identity)
                with self.assertRaisesRegex(AssertionError, "320"):
                    hook.verify_candidate(serial, root)


def native_fixture(directory):
    value, _, _, _ = fixture(directory)
    trust = directory / "trusted-fixture-repo"
    for name in ["native_predeploy.py", "native_gate_common.py", "native_initialization_gate.py", "native_needed_gate.py"]:
        target = trust / "scripts/lab" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("fixture checker bytes: " + name)
    for name in ["scan_native_initialization.py", "rules_native_initialization.py"]:
        target = trust / "benchmark/2026-09-29-static-wall-prediction" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("fixture rule bytes: " + name)
    save(trust / "knowledge/gates/native-predeploy-exceptions.json", {"exceptions": []})
    packages = [Path(value["package"]) / "native", Path(value["base_bundle"]) / "native"]
    for package in packages:
        package.mkdir()
        (package / "fixture-payload.bin").write_bytes(b"fixture inventory; not an executable ELF")
        save(package / "package.json", {"files": {"fixture-payload.bin": hook.gb.sha(package / "fixture-payload.bin")}})
        save(package / "native-checks/native-gates.json", {"fixture": True})
    value.update(execution_enabled=True, native_manifest_sha256=hook.gb.sha(packages[0] / "package.json"),
        native_inputs_sha256=hook.gb.sha(packages[0] / "native-checks/native-gates.json"), stage_b_authorization=str(directory / "authorization.json"))
    save(Path(value["stage_b_authorization"]), dict(signed_by="outer(claude)", promotion_authorized=True,
        bundle_sha256=value["bundle_sha256"], native_manifest_sha256=value["native_manifest_sha256"]))
    for serial in value["smoke_specs"]:
        for name in [value["smoke_specs"][serial], value["recovery_smoke_specs"][serial]]:
            shutil.copyfile(HERE / "common" / name, hook.H / name)
    tickets = [dict(package=str(package.resolve()), binding=hook.native_gate.binding(package, trust)) for package in packages]
    for surface in ["mac", "vm"]:
        save(hook.H / ("gate-" + surface + "-pass.json"), dict(bundle_sha256=value["bundle_sha256"],
            native_manifest_sha256=value["native_manifest_sha256"], policy_binding="synthetic-policy",
            production_dry_run_exit_code=0, gates_passed=True, deployable=True, static="PASS", G1=True, G2=True,
            frozen_composed_violations=0, native_findings={gate: {"rejected": 0} for gate in ["N1", "N2"]}))
        save(hook.H / "gates" / surface / "executor", dict(deployable=True, gates_passed=True,
            bundle_sha256=value["bundle_sha256"], root=value["package"], baseline_native=str(packages[1]), native_tickets=tickets))
    save(hook.H / "composition.json", value)
    return value, trust, packages


class WiringTests(unittest.TestCase):
    def test_cutoff_leaves_ten_minutes_and_never_restarts_wait(self):
        started = 1000
        deadline = started + 20 * 60
        for current in [started, started + 15 * 60, deadline, deadline + 1]:
            self.assertEqual(review.decision_deadline(started, current), deadline)
        self.assertEqual(started + 30 * 60 - deadline, 10 * 60)
        for current in [started - 1, float("nan"), float("inf")]:
            with self.assertRaises(ValueError):
                review.decision_deadline(started, current)

    def test_existing_signature_at_exact_cutoff_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            decision = Path(temp) / "outer.json"
            save(decision, {"signed_by": "fixture-only"})
            with patch.object(review.time, "sleep") as sleep:
                self.assertTrue(review.wait_for_decision(decision, 1200, now=lambda: 1199, sleep=sleep))
                self.assertFalse(review.wait_for_decision(decision, 1200, now=lambda: 1200, sleep=sleep))
                self.assertFalse(review.wait_for_decision(decision, 1200, now=lambda: 1201, sleep=sleep))
                sleep.assert_not_called()

    def test_expiry_does_not_pass_late_signature_to_finish(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            save(root / "plan.json", dict(stage_a_decision=str(root / "stage-a.json"), before_unlock_restored_spec=str(root / "restore.json")))
            save(root / "runner/smoke/smoke-result.json", {"passed": True})
            save(root / "post-apply/candidate-identity.json", {"diff": {}, "absent": []})
            save(root / "composition.json", {"bundle_sha256": "fixture-only", "native_manifest_sha256": "fixture-only"})
            save(root / "outer-promotion.json", {"signed_by": "fixture-only"})
            for instant, available in [(1200, False), (1199, True), (1200, True)]:
                with patch.object(sys, "argv", ["review", "--serial", "fixture", "--root", str(root), "--plan", str(root / "plan.json")]), \
                        patch.object(hook, "require_enabled"), patch.object(review, "H", root), \
                        patch.object(review, "window_started", return_value=0), patch.object(review.time, "time", return_value=instant), \
                        patch.object(review, "wait_for_decision", return_value=available), patch.object(review.subprocess, "run"), \
                        patch.object(hook, "finish") as finish, redirect_stdout(io.StringIO()):
                    review.main()
                    expected = root / "outer-promotion.json" if instant < 1200 and available else None
                    self.assertEqual(finish.call_args.args[3], expected)
                    receipt = load(root / "approval-ready.json")
                    self.assertEqual(receipt["wait_until_epoch"], 1200)
                    self.assertEqual(receipt["rollback_reserve_minutes"], 10)

    def test_missing_prelock_birthtime_refuses_wait(self):
        from types import SimpleNamespace
        with patch.object(Path, "stat", return_value=SimpleNamespace(st_mtime=9999)):
            with self.assertRaisesRegex(ValueError, "birthtime absent"):
                review.window_started(Path("fixture-only"))

    def test_all_four_native_tickets_use_real_binding_assertion(self):
        with tempfile.TemporaryDirectory() as temp:
            _, trust, _ = native_fixture(Path(temp))
            with patch.object(hook.native_gate, "repository", return_value=trust), \
                    patch.object(hook.u, "policy_binding", return_value="synthetic-policy"), \
                    patch.object(hook.native_gate, "assert_unchanged", wraps=hook.native_gate.assert_unchanged) as assertion:
                hook.admission()
                self.assertEqual(assertion.call_count, 4)

    def test_native_drift_refuses_before_transport(self):
        for change in ["registry", "checker", "candidate-input", "baseline-input", "candidate-payload", "vm-ticket"]:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temp:
                value, trust, packages = native_fixture(Path(temp))
                if change == "vm-ticket":
                    receipt_path = hook.H / "gates/vm/executor"
                    receipt = load(receipt_path)
                    receipt["native_tickets"][1]["binding"] = "0" * 64
                    save(receipt_path, receipt)
                else:
                    changed = {"registry": trust / "knowledge/gates/native-predeploy-exceptions.json",
                        "checker": trust / "scripts/lab/native_needed_gate.py",
                        "candidate-input": packages[0] / "native-checks/extra-source.txt",
                        "baseline-input": packages[1] / "native-checks/extra-source.txt",
                        "candidate-payload": packages[0] / "fixture-payload.bin"}[change]
                    changed.write_text("drifted fixture bytes")
                plan = dict(execution_enabled=True, phase="B", bundle_sha256=value["bundle_sha256"], package_manifest_sha256=value["native_manifest_sha256"], stage_a_decision="fixture-only")
                with patch.object(dispatch, "H", hook.H), patch.object(dispatch.board_run, "precheck_problem", return_value=None), \
                        patch.object(hook, "validate_plan"), patch.object(hook, "stage_a_admission"), \
                        patch.object(hook.native_gate, "repository", return_value=trust), \
                        patch.object(hook.u, "policy_binding", return_value="synthetic-policy"), \
                        patch.object(dispatch.subprocess, "run") as transport:
                    with self.assertRaises(RuntimeError):
                        dispatch.prelock(plan)
                    transport.assert_not_called()

    def test_missing_wrong_owner_or_not_deployable_full_receipt_refuses(self):
        for change in ["missing", "truncated", "wrong-owner", "not-deployable", "wrong-bundle"]:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temp:
                value, trust, _ = native_fixture(Path(temp))
                receipt_path = hook.H / "gates/mac/executor"
                report = load(receipt_path)
                if change == "missing":
                    del report["native_tickets"]
                elif change == "truncated":
                    report["native_tickets"] = report["native_tickets"][:1]
                elif change == "wrong-owner":
                    report["native_tickets"][0]["package"] = report["native_tickets"][1]["package"]
                elif change == "not-deployable":
                    report["deployable"] = False
                else:
                    report["bundle_sha256"] = "0" * 64
                save(receipt_path, report)
                with patch.object(hook.native_gate, "repository", return_value=trust):
                    with self.assertRaises(AssertionError):
                        hook.native_tickets_admission("mac", value)


class KnownAnswers(unittest.TestCase):
    def test_correct_stage_a_outputs_both_variants(self):
        for variant in ["common", "61b"]:
            with tempfile.TemporaryDirectory() as temp:
                value, reference, decision, decision_path = fixture(Path(temp), variant)
                self.assertIsNone(hook.retention_reason(decision, value, reference, {"passed": True}))
                hook.stage_a_admission(decision_path)

    def test_wrong_bundle_refuses(self):
        with tempfile.TemporaryDirectory() as temp:
            value, reference, decision, _ = fixture(Path(temp))
            decision["bundle_sha256"] = "0" * 64
            self.assertEqual(hook.retention_reason(decision, value, reference, {"passed": True}), "signoff belongs to another bundle")

    def test_one_badtag_refuses_even_with_OK(self):
        with tempfile.TemporaryDirectory() as temp:
            value, reference, decision, _ = fixture(Path(temp))
            gate = decision["process_selftest_gate"]
            report_path = Path(gate["report"])
            data = load(report_path)
            data["runs"][0]["badtag_count"] = 1
            save(report_path, data)
            gate["report_sha256"] = hook.gb.sha(report_path)
            summary_path = Path(gate["summary"])
            summary = load(summary_path)
            summary["report_sha256"] = gate["report_sha256"]
            save(summary_path, summary)
            gate["summary_sha256"] = hook.gb.sha(summary_path)
            explanations_path = Path(gate["explanations"])
            explanations = load(explanations_path)
            explanations["report_sha256"] = gate["report_sha256"]
            save(explanations_path, explanations)
            gate["explanations_sha256"] = hook.gb.sha(explanations_path)
            self.assertIn("unconditionally rejects", hook.retention_reason(decision, value, reference, {"passed": True}))

    def run_finish(self, change=None, missing=False, malformed=False):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            value, _, _, stage_a = fixture(directory)
            serial = next(iter(value["candidate_boards"]))
            root = directory / "window-b"
            smoke = root / "runner/smoke/smoke-result.json"
            identity = root / "post-apply/candidate-identity.json"
            save(smoke, {"passed": True})
            save(identity, dict(diff={}, absent=[], identity_assertions=322, unique_paths=320, fingerprints=value["candidate_boards"][serial]["fingerprints"]))
            decision = dict(signed_by="outer(claude)", signed_at="synthetic-known-answer-only", release="U14", phase="B", serial=serial, window_root=str(root),
                bundle_sha256=value["bundle_sha256"], native_manifest_sha256=value["native_manifest_sha256"], controls_t20_lit=["helloworld", "zigzag"],
                confirmed_regressions=[], smoke_sha256=hook.gb.sha(smoke), identity_sha256=hook.gb.sha(identity))
            decision.update(change or {})
            signature = directory / "outer-fresh.json"
            if not missing:
                save(signature, decision)
                if malformed:
                    signature.write_text("{")
            with patch.object(hook, "admission"), patch.object(hook, "verify_candidate"), patch.object(hook.previous, "finish") as restore:
                hook.finish(serial, root, directory / "restore.json", signature, stage_a)
                result = load(root / "retention.json")
                self.assertEqual(restore.called, not result["retained"])
            return result

    def test_missing_fresh_signature_restores(self):
        result = self.run_finish(missing=True)
        self.assertFalse(result["retained"])
        self.assertIn("fresh outer screenshot review absent", result["reason"])

    def test_correct_fresh_input_retains_mock_only(self):
        self.assertTrue(self.run_finish()["retained"])

    def test_partial_signature_restores(self):
        self.assertFalse(self.run_finish(malformed=True)["retained"])

    def test_wrong_window_and_stale_smoke_restore(self):
        for change in [dict(window_root="another-window"), dict(smoke_sha256="0" * 64), dict(bundle_sha256="0" * 64), dict(controls_t20_lit=["helloworld"])]:
            self.assertFalse(self.run_finish(change)["retained"])

    def test_review_deadline_no_partial_signature(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "outer.json"
            path.write_text("{")
            ticks = iter([0, 0, 2])
            self.assertFalse(review.wait_for_decision(path, 1, now=lambda: next(ticks), sleep=lambda _: None))

    def test_malformed_smoke_still_finishes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            save(root / "plan.json", dict(stage_a_decision=str(root / "stage-a.json"), before_unlock_restored_spec=str(root / "restore.json")))
            smoke = root / "runner/smoke/smoke-result.json"
            smoke.parent.mkdir(parents=True)
            smoke.write_text("{")
            with patch.object(sys, "argv", ["review", "--serial", "fixture", "--root", str(root), "--plan", str(root / "plan.json")]), patch.object(hook, "require_enabled"), patch.object(hook, "finish") as finish:
                with self.assertRaises(ValueError):
                    review.main()
                finish.assert_called_once()


if __name__ == "__main__":
    case = BindingTests if "--binding" in sys.argv else KnownAnswers if "--known-answers" in sys.argv else WiringTests if "--wiring" in sys.argv else None
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(case) if case else unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps(dict(platform=sys.platform, machine=platform.machine(), tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        board_access=False, locked=False, execution_enabled=False, fixture_decisions_only=True), sort_keys=True))
    raise SystemExit(not result.wasSuccessful())
