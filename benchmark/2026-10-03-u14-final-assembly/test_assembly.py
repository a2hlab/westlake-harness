import ast
import copy
import json
from pathlib import Path
import sys
import unittest

from receipt import verify_wrapper
from validation import ADDITIONS, CHANGES, IMAGES, JARS, check_partial, check_receipt, check_review, check_transaction

HERE = Path(__file__).resolve().parent


class CompositionTests(unittest.TestCase):
    def setUp(self):
        self.old = {name: "0" * 64 for name in CHANGES}
        self.old["payload/android/lib64/libandroid.so"] = "1" * 64
        self.new = self.old | CHANGES | ADDITIONS
        self.state = dict(execution_enabled=False, final_batch_complete=False, images="pending", paired_receipt=None)

    def test_pinned_partial(self):
        check_partial(self.old, self.new, self.state)
        self.assertEqual(len(CHANGES), 8)
        self.assertEqual(len(ADDITIONS), 1)

    def test_private_alias_drift(self):
        for member in ["payload/android/lib64/libandroid.so", "payload/android/lib64/libwestlake_native_abi.so", "payload/android/lib64/westlake_native/libandroid.so"]:
            with self.subTest(member=member):
                with self.assertRaises(ValueError):
                    check_partial(self.old, self.new | {member: "f" * 64}, self.state)

    def test_selected_hash_drift(self):
        for member in CHANGES:
            with self.subTest(member=member):
                with self.assertRaises(ValueError):
                    check_partial(self.old, self.new | {member: "f" * 64}, self.state)

    def test_partial_cannot_borrow_receipt_or_descriptor(self):
        for state, descriptor in [(self.state, True), (self.state | {"paired_receipt": "U12"}, False), (self.state | {"execution_enabled": True}, False), (self.state | {"images": "verified"}, False)]:
            with self.assertRaises(ValueError):
                check_partial(self.old, self.new, state, descriptor)

    def test_explicit_transaction(self):
        check_transaction("signed-base", "a" * 64, "a" * 64)
        for path, expected, actual in [(None, "a" * 64, "a" * 64), ("base", None, "a" * 64), ("base", "a" * 64, "b" * 64)]:
            with self.assertRaises(ValueError):
                check_transaction(path, expected, actual)
        tree = ast.parse((HERE / "finalize.py").read_text())
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument"]
        for flag in ["--transaction-base", "--transaction-base-sha256", "--board-baseline"]:
            call = next(node for node in calls if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == flag)
            self.assertTrue(next(keyword.value.value for keyword in call.keywords if keyword.arg == "required"))

    def test_public_composition_requires_no_private_artifacts(self):
        composition = json.loads((HERE / "final-composition.json").read_text())
        manifest = json.loads((HERE / "manifests/final-native-manifest.json").read_text())
        self.assertFalse(composition["execution_enabled"])
        self.assertFalse(manifest["rollout_ready"])
        self.assertTrue(composition["all_27_images_from_actual_u14_build"])
        for member, digest in (CHANGES | ADDITIONS).items():
            self.assertEqual(manifest["files"][member], digest)
        self.assertEqual(manifest["files"]["payload/android/lib64/westlake_native/libandroid.so"], "ee2fb82c6351b1b8461ce214e8ef39c9b33731523f154f92137991afa0e26c45")
        self.assertEqual(manifest["files"]["payload/android/lib64/libwestlake_native_abi.so"], "d20530661a30b8af7bbfb30a6b7138d0b6a6bb5d82e6cb8d733a41ae23886c65")


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.inputs = {name + ".jar": "a" * 64 for name in JARS}
        self.outputs = {name: "b" * 64 for name in IMAGES}
        self.receipt = dict(status="verified", input_jars=self.inputs, outputs=self.outputs,
            toolchain_identity_sha256="c" * 64, build_log_sha256="d" * 64, session_log_sha256="e" * 64, wrapper_sha256="f" * 64,
            dex2oat_sha256="ae865ddd6a7e4b25a18b7c07402920c69e5599b329778eff647a08803948322b",
            driver_sha256="14b1f709cbeae35c2e606ee923d26a9f59e92dd827da84bdf5126de79a675d46",
            dex2oat_exit_code=0, tee_exit_code=0, session_tee_exit_code=0, build_command="actual compiler argv", actual_argv=["compiler"], exception_used=False)

    def test_complete_receipt(self):
        check_receipt(self.receipt, self.inputs, self.outputs)
        for number in [1, 2]:
            actual = json.loads((HERE / "receipts" / ("paired-run" + str(number) + ".json")).read_text())
            check_receipt(actual, actual["input_jars"], actual["outputs"])
            self.assertEqual(actual["t5_exit_code"], 6)
            self.assertFalse(actual["exception_used"])

    def test_missing_live_fields(self):
        for field in ["actual_argv", "build_command", "build_log_sha256", "toolchain_identity_sha256", "session_log_sha256", "wrapper_sha256"]:
            with self.subTest(field=field):
                broken = copy.deepcopy(self.receipt)
                broken.pop(field)
                with self.assertRaises(ValueError):
                    check_receipt(broken, self.inputs, self.outputs)

    def test_failed_logging_or_old_inputs(self):
        for field in ["dex2oat_exit_code", "tee_exit_code", "session_tee_exit_code"]:
            with self.assertRaises(ValueError):
                check_receipt(self.receipt | {field: 1}, self.inputs, self.outputs)
        with self.assertRaises(ValueError):
            check_receipt(self.receipt, self.inputs | {"adapter-mainline-stubs.jar": "0" * 64}, self.outputs)
        with self.assertRaises(ValueError):
            check_receipt(self.receipt, self.inputs, {name: digest for name, digest in self.outputs.items() if name != "boot.art"})

    def test_old_exception_is_not_approval(self):
        with self.assertRaises(ValueError):
            check_receipt(self.receipt | {"exception_used": True}, self.inputs, self.outputs)
        review = json.loads((HERE / "reproduction-review.json").read_text())
        self.assertEqual(review["strict_identical"], 26)
        self.assertEqual(review["status"], "REJECT")
        self.assertIsNone(review["approved_by"])
        proof = json.loads((HERE / "object-proof.json").read_text())
        self.assertEqual(proof["status"], "verified-object-chain")
        self.assertFalse(proof["paired_byte_exception_approved"])
        self.assertEqual([row["oatdump_exit_code"] for row in proof["rows"]], [0, 0])
        for row in proof["rows"]:
            self.assertEqual(row["object"], "sun.nio.ch.PendingFuture.CANCELLED.backtrace[0] long[2] element 0")

    def test_wrapper_amendment_exactly_two_changes(self):
        original = 'guard [ "$(hostname -s)" = hw248 ]\nexport U14_ROOT="$HOME/bake"\nother guard\n'
        lab_home = "/lab-frozen-root"
        amended = original.replace("= hw248", "= ecs-9f6c").replace("export U14_ROOT=", "export HOME=" + lab_home + "\nexport U14_ROOT=")
        verify_wrapper(original, amended, lab_home)
        with self.assertRaises(ValueError):
            verify_wrapper(original, amended.replace("other guard", "weakened guard"), lab_home)

    def test_rejections_are_not_approvals(self):
        records = [dict(exit_code=0), dict(exit_code=1), dict(exit_code=2)]
        check_review(records, dict(applied=False, approved_by=None))
        self.assertEqual([row["exit_code"] for row in records], [0, 1, 2])
        with self.assertRaises(ValueError):
            check_review(records, dict(applied=True, approved_by="outer"))
        report = json.loads((HERE / "report-summary.json").read_text())
        review = json.loads((HERE / "needs-outer-review.json").read_text())
        check_review(report["records"], review)
        self.assertEqual(report["native_candidate"], "REJECT")
        self.assertEqual(report["static_vs_u13"], "REJECT")


if __name__ == "__main__":
    suite = unittest.TestSuite()
    mode = sys.argv[1] if len(sys.argv) > 1 else "--all"
    if mode in ["--composition", "--all"]:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(CompositionTests))
    if mode in ["--evidence", "--all"]:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(EvidenceTests))
    if suite.countTestCases() == 0:
        raise SystemExit("Unknown test mode")
    raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
