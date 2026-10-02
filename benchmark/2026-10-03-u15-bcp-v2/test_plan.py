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


class InputTests(unittest.TestCase):
    def test_exact_two_swaps_and_27_outputs(self):
        check_plan(load("plan.json"), load("expected-images.json"))
        self.assertEqual(load("plan.json")["changed_bcp"], ["adapter-mainline-stubs.jar", "framework.jar"])

    def test_changed_unchanged_hash_is_rejected(self):
        plan = load("plan.json")
        plan["bcp"][0]["sha256"] = "f" * 64
        plan["bcp"][0]["u14_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "Unchanged BCP"):
            check_plan(plan, load("expected-images.json"))

    def test_historical_one_swap_is_rejected(self):
        plan = load("plan.json")
        plan["bcp"][6]["sha256"] = plan["bcp"][6]["u14_sha256"]
        with self.assertRaisesRegex(ValueError, "dual BCP"):
            check_plan(plan, load("expected-images.json"))

    def test_no_inferred_promotion(self):
        plan = load("plan.json")
        plan["transaction_base"]["common"] = plan["content_bases"]["common"]
        with self.assertRaisesRegex(ValueError, "implicit"):
            check_plan(plan, load("expected-images.json"))

    def test_arrived_flutter_is_not_composed(self):
        ledger = load("native-slots.json")
        check_slots(ledger)
        ledger["slots"][1]["applied"] = True
        with self.assertRaisesRegex(ValueError, "Flutter arrival"):
            check_slots(ledger)

    def test_cold_source_hashes(self):
        for row in load("source-snapshots.json"):
            self.assertEqual(hashlib.sha256((HERE / row["snapshot"]).read_bytes()).hexdigest(), row["snapshot_sha256"])

    def test_board_local_identity_and_signed_baseline(self):
        for variant, digest in BASES.items():
            binding = dict(path="$WORKSPACES/fixture", sha256=digest,
                signed_identity=dict(path="fixture.json", sha256="a" * 64, approved_by="outer(claude)"),
                expected={target: INSTALLERS[variant] for target in INSTALLER_PATHS})
            check_transaction(binding, variant)
            binding["signed_identity"] = None
            with self.assertRaisesRegex(ValueError, "Signed per-board"):
                check_transaction(binding, variant)


class RecipeTests(unittest.TestCase):
    def test_disabled_before_any_probe(self):
        run = subprocess.run(["bash", str(HERE / "planned-bake.sh")], capture_output=True, text=True,
            env={"PATH": "/usr/bin:/bin", "HOME": "/nonexistent"})
        self.assertEqual(run.returncode, 78)
        self.assertIn("DISABLED", run.stdout)

    def test_shell_syntax_and_logging_guards(self):
        for name in ["planned-bake.sh", "dex2oat-tee.sh"]:
            subprocess.run(["bash", "-n", str(HERE / name)], check=True)
        script = (HERE / "planned-bake.sh").read_text()
        for marker in ["ecs-9f6c", "HW248_HOME", "session_tee_exit_code", "hostlibs-run1", "u15-bitmap-nsd-9e55-94a9-v1"]:
            self.assertIn(marker, script)
        argv = load("planned-argv.json")
        self.assertEqual(argv["run1"], argv["run2"])
        self.assertEqual(sum(arg.startswith("--dex-file=") for arg in argv["run1"]), 9)

    def test_complete_unexecuted_pair_template(self):
        plan = load("plan.json")
        inputs = {row["name"]: row["sha256"] for row in plan["bcp"]}
        pair = load("paired-receipt.template.json")
        self.assertIsNone(pair["selected_run"])
        self.assertEqual([row["run"] for row in pair["runs"]], [1, 2])
        for row in pair["runs"]:
            self.assertEqual(row["input_jars"], inputs)
            self.assertEqual(set(row["outputs"]), IMAGE_NAMES)
            self.assertTrue(all(value is None for value in row["outputs"].values()))
            with self.assertRaises(ValueError):
                check_receipt(row, inputs, {name: "a" * 64 for name in IMAGE_NAMES})

    def test_incomplete_images_or_fake_output(self):
        with self.assertRaisesRegex(ValueError, "27 distinct"):
            check_plan(load("plan.json"), load("expected-images.json")[:-1])
        images = load("expected-images.json")
        images[0]["candidate_sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "unknown"):
            check_plan(load("plan.json"), images)

    def test_receipt_failures_and_historical_exception(self):
        inputs = {row["name"]: row["sha256"] for row in load("plan.json")["bcp"]}
        outputs = {name: "a" * 64 for name in IMAGE_NAMES}
        receipt = dict(status="verified", input_jars=inputs, outputs=outputs, actual_argv=["synthetic-test-only"],
            argv_sha256="a" * 64, dex2oat_sha256=DEX2OAT, driver_sha256=DRIVER, toolchain_identity_sha256="a" * 64,
            hostlibs_sha256="a" * 64, build_log_sha256="a" * 64, session_log_sha256="a" * 64,
            dex2oat_exit_code=0, tee_exit_code=0, session_tee_exit_code=0, script_exit_code=0, exception_used=False)
        check_receipt(receipt, inputs, outputs)
        for field in ["dex2oat_exit_code", "tee_exit_code", "session_tee_exit_code", "script_exit_code"]:
            changed = copy.deepcopy(receipt)
            changed[field] = 1
            with self.assertRaisesRegex(ValueError, "failed"):
                check_receipt(changed, inputs, outputs)
        receipt["exception_used"] = True
        receipt["u14_outer_exception_approval"] = {"sha256": "a" * 64}
        with self.assertRaisesRegex(ValueError, "automatic U15"):
            check_receipt(receipt, inputs, outputs)


if __name__ == "__main__":
    groups = [InputTests] if "--inputs" in sys.argv else [RecipeTests] if "--recipe" in sys.argv else [InputTests, RecipeTests]
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(group) for group in groups)
    raise SystemExit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
