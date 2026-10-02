import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

from validation import DEX2OAT, DRIVER, IMAGE_NAMES, check_plan, check_receipt, check_slots


HERE = Path(__file__).resolve().parent


def load(name):
    return json.loads((HERE / name).read_text())


class PlanTests(unittest.TestCase):
    def test_effective_order_and_one_swap(self):
        check_plan(load("plan.json"), load("expected-images.json"))

    def test_forecast_does_not_claim_actual_changes(self):
        plan = load("plan.json")
        rows = load("expected-images.json")
        self.assertIsNone(plan["actual_changed_image_count"])
        self.assertEqual(sum(row["prediction"].startswith("expected-change") for row in rows), 3)
        self.assertEqual(sum(row["prediction"].startswith("may-change") for row in rows), 16)
        self.assertEqual(sum(row["prediction"].startswith("expected-same") for row in rows), 8)

    def test_wrong_bcp_is_rejected(self):
        plan = load("plan.json")
        plan["bcp"][0]["sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "single BCP swap"):
            check_plan(plan, load("expected-images.json"))

    def test_missing_or_duplicate_image_is_rejected(self):
        images = load("expected-images.json")
        images[-1] = images[0]
        with self.assertRaisesRegex(ValueError, "27 distinct"):
            check_plan(load("plan.json"), images)

    def test_repository_driver_is_not_frozen_driver(self):
        tools = load("plan.json")["frozen_tools"]
        self.assertNotEqual(tools["local_repository_driver"]["sha256"], DRIVER)
        self.assertFalse(tools["local_repository_driver"]["usable_as_frozen_driver"])

    def test_source_snapshots_exist_and_match(self):
        for row in load("source-snapshots.json"):
            path = HERE / row["snapshot"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), row["snapshot_sha256"])

    def test_bake_is_disabled_before_any_machine_probe(self):
        result = subprocess.run(["bash", str(HERE / "planned-bake.sh")], capture_output=True, text=True,
            env={"PATH": "/usr/bin:/bin", "HOME": "/nonexistent"})
        self.assertEqual(result.returncode, 78)
        self.assertIn("DISABLED", result.stdout)


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.inputs = {row["name"]: row["sha256"] for row in load("plan.json")["bcp"]}
        self.outputs = {name: "a" * 64 for name in IMAGE_NAMES}
        self.receipt = dict(status="verified", input_jars=self.inputs, outputs=self.outputs,
            build_command="synthetic unit-test command; never executed", dex2oat_sha256=DEX2OAT,
            driver_sha256=DRIVER, toolchain_identity_sha256="b" * 64, build_log_sha256="c" * 64,
            session_log_sha256="d" * 64, dex2oat_exit_code=0, tee_exit_code=0, session_tee_exit_code=0, exception_used=False)

    def test_structurally_complete_receipt(self):
        check_receipt(self.receipt, self.inputs, self.outputs)

    def test_not_run_template_rejected(self):
        with self.assertRaises(ValueError):
            check_receipt(load("paired-receipt.template.json"), self.inputs, self.outputs)

    def test_receipt_mismatch_rejected(self):
        receipt = copy.deepcopy(self.receipt)
        receipt["input_jars"].pop("framework.jar")
        with self.assertRaisesRegex(ValueError, "input_jars"):
            check_receipt(receipt, self.inputs, self.outputs)

    def test_compiler_and_tee_failures_rejected(self):
        for field in ["dex2oat_exit_code", "tee_exit_code", "session_tee_exit_code"]:
            receipt = copy.deepcopy(self.receipt)
            receipt[field] = 1
            with self.assertRaisesRegex(ValueError, "failed"):
                check_receipt(receipt, self.inputs, self.outputs)

    def test_old_backtrace_exception_not_automatic(self):
        receipt = copy.deepcopy(self.receipt)
        receipt["exception_used"] = True
        with self.assertRaisesRegex(ValueError, "automatic U14"):
            check_receipt(receipt, self.inputs, self.outputs)


class SlotTests(unittest.TestCase):
    def test_host_staged_and_old_bundle_preserved(self):
        check_slots(load("native-slot-inputs.json"))

    def test_false_byte_reproduction_rejected(self):
        ledger = load("native-slot-inputs.json")
        ledger["slots"][0]["baseline_reproduction"] = "byte-identical"
        with self.assertRaisesRegex(ValueError, "invent byte"):
            check_slots(ledger)

    def test_pending_with_fake_hash_rejected(self):
        ledger = load("native-slot-inputs.json")
        ledger["slots"][1]["state"] = "pending"
        ledger["slots"][1]["sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "fake candidate"):
            check_slots(ledger)

    def test_superseded_gecko_rejected(self):
        ledger = load("native-slot-inputs.json")
        ledger["slots"][2]["sha256"] = "86882caf" + "0" * 56
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            check_slots(ledger)

    def test_flutter_does_not_modify_native_domain(self):
        ledger = load("native-slot-inputs.json")
        ledger["slots"][1]["target"] = "/system/android/lib64/westlake_native/libandroid.so"
        with self.assertRaisesRegex(ValueError, "private scope"):
            check_slots(ledger)

    def test_icu_aliases_move_together(self):
        ledger = load("native-slot-inputs.json")
        ledger["slots"][3]["targets"].pop()
        with self.assertRaisesRegex(ValueError, "move together"):
            check_slots(ledger)


if __name__ == "__main__":
    if "--slots" in sys.argv:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(SlotTests)
    else:
        suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(group)
            for group in [PlanTests, ReceiptTests])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
