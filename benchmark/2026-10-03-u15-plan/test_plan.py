import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

from validation import BASES, DEX2OAT, DRIVER, IMAGE_NAMES, INSTALLERS, INSTALLER_PATHS, check_plan, check_receipt, check_slots, check_transaction


HERE = Path(__file__).resolve().parent


def load(name):
    return json.loads((HERE / name).read_text())


class ImageTests(unittest.TestCase):
    def test_effective_bcp_and_forecast(self):
        check_plan(load("plan.json"), load("expected-images.json"))
        self.assertEqual(len(load("expected-images.json")), 27)

    def test_second_bcp_swap_rejected(self):
        plan = load("plan.json")
        plan["bcp"][6]["sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "single BCP swap"):
            check_plan(plan, load("expected-images.json"))

    def test_missing_image_rejected(self):
        with self.assertRaisesRegex(ValueError, "27 distinct"):
            check_plan(load("plan.json"), load("expected-images.json")[:-1])

    def test_claimed_output_rejected(self):
        rows = load("expected-images.json")
        rows[0]["candidate_sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "unknown"):
            check_plan(load("plan.json"), rows)

    def test_wrong_machine_or_home_rejected(self):
        for field, value in [("hostname", "hw248"), ("home_identity_sha256", "a" * 64)]:
            plan = load("plan.json")
            plan["machine"][field] = value
            with self.assertRaisesRegex(ValueError, "hw248 identity"):
                check_plan(plan, load("expected-images.json"))

    def test_disabled_before_machine_probe(self):
        result = subprocess.run(["bash", str(HERE / "planned-bake.sh")], env={"PATH": "/usr/bin:/bin", "HOME": "/nonexistent"}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 78)
        self.assertIn("DISABLED", result.stdout)

    def test_sources_are_cold_portable_and_hash_bound(self):
        for row in load("source-snapshots.json"):
            self.assertEqual(hashlib.sha256((HERE / row["snapshot"]).read_bytes()).hexdigest(), row["snapshot_sha256"])

    def test_receipt_template_is_not_verified(self):
        plan = load("plan.json")
        inputs = {row["name"]: row["sha256"] for row in plan["bcp"]}
        outputs = {name: "a" * 64 for name in IMAGE_NAMES}
        for receipt in load("paired-receipt.template.json")["runs"]:
            with self.assertRaises(ValueError):
                check_receipt(receipt, inputs, outputs)

    def test_synthetic_receipt_and_failures(self):
        inputs = {row["name"]: row["sha256"] for row in load("plan.json")["bcp"]}
        outputs = {name: "a" * 64 for name in IMAGE_NAMES}
        receipt = dict(status="verified", input_jars=inputs, outputs=outputs, actual_argv=["synthetic-test-only"],
            argv_sha256="b" * 64, dex2oat_sha256=DEX2OAT, driver_sha256=DRIVER, toolchain_identity_sha256="c" * 64,
            hostlibs_sha256="d" * 64, build_log_sha256="e" * 64, session_log_sha256="f" * 64,
            dex2oat_exit_code=0, tee_exit_code=0, session_tee_exit_code=0, script_exit_code=0, exception_used=False)
        check_receipt(receipt, inputs, outputs)
        for field in ["dex2oat_exit_code", "tee_exit_code", "session_tee_exit_code", "script_exit_code"]:
            changed = copy.deepcopy(receipt)
            changed[field] = 1
            with self.assertRaisesRegex(ValueError, "failed"):
                check_receipt(changed, inputs, outputs)
        changed = copy.deepcopy(receipt)
        changed["exception_used"] = True
        changed["u14_outer_exception_approval"] = {"sha256": "a" * 64}
        with self.assertRaisesRegex(ValueError, "automatic U15"):
            check_receipt(changed, inputs, outputs)


class NativeTests(unittest.TestCase):
    def test_arrived_and_pending_slots(self):
        check_slots(load("native-slots.json"))

    def test_pending_fake_identity_rejected(self):
        ledger = load("native-slots.json")
        ledger["slots"][1]["sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "fake candidate"):
            check_slots(ledger)

    def test_wrong_native_runtime_rejected(self):
        ledger = load("native-slots.json")
        ledger["slots"][0]["sha256"] = load("plan.json")["runtime_jar"]["sha256"]
        with self.assertRaisesRegex(ValueError, "runtime identity"):
            check_slots(ledger)

    def test_content_is_not_promotion(self):
        plan = load("plan.json")
        plan["transaction_base"]["common"] = plan["content_bases"]["common"]
        with self.assertRaisesRegex(ValueError, "implicit transaction"):
            check_plan(plan, load("expected-images.json"))

    def test_parameterized_binding_and_board_local_rejection(self):
        for variant, digest in BASES.items():
            binding = dict(path="$WORKSPACES/example-base", sha256=digest,
                signed_identity=dict(path="$WORKSPACES/example-signed-identity.json", sha256="a" * 64, approved_by="outer(claude)"),
                expected={target: INSTALLERS[variant] for target in INSTALLER_PATHS})
            check_transaction(binding, variant)
            binding["signed_identity"] = None
            with self.assertRaisesRegex(ValueError, "Signed per-board"):
                check_transaction(binding, variant)
        binding["signed_identity"] = dict(path="example", sha256="a" * 64, approved_by="outer(claude)")
        binding["expected"][INSTALLER_PATHS[0]] = INSTALLERS["common"]
        with self.assertRaisesRegex(ValueError, "Board-local"):
            check_transaction(binding, "61b")


if __name__ == "__main__":
    groups = [NativeTests] if "--native" in sys.argv else [ImageTests] if "--images" in sys.argv else [ImageTests, NativeTests]
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(group) for group in groups)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
