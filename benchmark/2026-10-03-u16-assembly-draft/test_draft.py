import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

from validation import ADDED, DEX2OAT, DRIVER, IMAGE_NAMES, check_plan, check_receipt

HERE = Path(__file__).resolve().parent


def load(name):
    return json.loads((HERE / name).read_text())


class InputTests(unittest.TestCase):
    def test_effective_nine_and_one_swap(self):
        check_plan(load("plan.json"), load("expected-images.json"), load("native-slots.json"))
        self.assertEqual(load("plan.json")["changed_bcp"], ["adapter-mainline-stubs.jar"])

    def test_no_inferred_transaction_promotion(self):
        plan = load("plan.json")
        plan["transaction_base"]["common"] = plan["content_bases"]["common"]
        with self.assertRaisesRegex(ValueError, "inferred"):
            check_plan(plan, load("expected-images.json"), load("native-slots.json"))

    def test_wrong_input_and_runtime_in_bcp(self):
        for change in ["wrong-stubs", "runtime-in-bcp"]:
            plan = load("plan.json")
            if change == "wrong-stubs":
                plan["bcp"][6]["sha256"] = "f" * 64
            else:
                plan["runtime_jar"]["in_bcp"] = True
            with self.assertRaises(ValueError):
                check_plan(plan, load("expected-images.json"), load("native-slots.json"))

    def test_pending_native_and_exclusions(self):
        slots = load("native-slots.json")
        slots["slots"][0]["applied"] = True
        with self.assertRaisesRegex(ValueError, "arrival"):
            check_plan(load("plan.json"), load("expected-images.json"), slots)
        slots["slots"] = []
        with self.assertRaisesRegex(ValueError, "Both pending"):
            check_plan(load("plan.json"), load("expected-images.json"), slots)

    def test_exact_adds_remain_unsigned(self):
        approval = load("allow-add.pending.json")
        self.assertEqual(approval["descriptors"], ADDED)
        self.assertFalse(approval["approved"])
        self.assertFalse(approval["execution_enabled"])

    def test_cold_source_snapshots(self):
        for row in load("source-snapshots.json"):
            self.assertEqual(hashlib.sha256((HERE / row["snapshot"]).read_bytes()).hexdigest(), row["snapshot_sha256"])
        receipt = load("donor-receipt-status.json")
        self.assertEqual(receipt["receipt_matches_current_artifact"], receipt["artifact_sha256"] == receipt["receipt_output_sha256"])
        self.assertTrue(receipt["blocks_final_provenance_claim"])


class BakeTests(unittest.TestCase):
    def test_disabled_before_probe(self):
        result = subprocess.run(["bash", str(HERE / "planned-bake.sh")], capture_output=True, text=True,
            env={"PATH": "/usr/bin:/bin", "HOME": "/nonexistent"})
        self.assertEqual(result.returncode, 78)
        self.assertIn("DISABLED", result.stdout)

    def test_exact_recipe_delta_and_machine(self):
        for name in ["planned-bake.sh", "dex2oat-tee.sh"]:
            subprocess.run(["bash", "-n", str(HERE / name)], check=True)
            old = (HERE / "inputs/source/u15-recipe" / (name + ".txt")).read_text()
            expected = old.replace("U15", "U16").replace("u15", "u16").replace("bitmap-nsd-9e55-94a9-v1", "stubs-8593-runtime-f6f5-v1")
            self.assertEqual((HERE / name).read_text(), expected)
        script = (HERE / "planned-bake.sh").read_text()
        for marker in ["ecs-9f6c", "HW248_HOME", "session_tee_exit_code", "hostlibs-run1", DEX2OAT, DRIVER]:
            self.assertIn(marker, script)

    def test_identical_planned_argv_not_actual(self):
        argv = load("planned-argv.json")
        self.assertEqual(argv["run1"], argv["run2"])
        self.assertIsNone(argv["actual_argv_sha256"])
        self.assertEqual(sum(arg.startswith("--dex-file=") for arg in argv["run1"]), 9)
        self.assertFalse(any("oh-adapter-runtime.jar" in arg for arg in argv["run1"]))

    def test_complete_unexecuted_pair(self):
        inputs = {row["name"]: row["sha256"] for row in load("plan.json")["bcp"]}
        pair = load("paired-receipt.template.json")
        self.assertIsNone(pair["selected_run"])
        self.assertEqual([row["run"] for row in pair["runs"]], [1, 2])
        for row in pair["runs"]:
            self.assertEqual(row["input_jars"], inputs)
            self.assertEqual(set(row["outputs"]), IMAGE_NAMES)
            self.assertTrue(all(value is None for value in row["outputs"].values()))
            with self.assertRaises(ValueError):
                check_receipt(row, inputs, row["outputs"])

    def test_incomplete_images_and_fake_hash(self):
        images = load("expected-images.json")
        with self.assertRaisesRegex(ValueError, "27 distinct"):
            check_plan(load("plan.json"), images[:-1], load("native-slots.json"))
        images[0]["candidate_sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "unknown"):
            check_plan(load("plan.json"), images, load("native-slots.json"))

    def test_failed_logging_and_old_approval(self):
        inputs = {row["name"]: row["sha256"] for row in load("plan.json")["bcp"]}
        outputs = {name: "a" * 64 for name in IMAGE_NAMES}
        receipt = dict(status="verified", input_jars=inputs, outputs=outputs, actual_argv=["synthetic-not-a-bake"],
            dex2oat_sha256=DEX2OAT, driver_sha256=DRIVER, frozen_driver_exit_code=6, dex2oat_exit_code=0, tee_exit_code=0,
            session_tee_exit_code=0, script_exit_code=0, exception_used=False,
            **{name: "a" * 64 for name in ["argv_sha256", "toolchain_identity_sha256", "hostlibs_sha256", "build_log_sha256", "session_log_sha256"]})
        check_receipt(receipt, inputs, outputs)
        for field in ["dex2oat_exit_code", "tee_exit_code", "session_tee_exit_code", "script_exit_code"]:
            broken = copy.deepcopy(receipt)
            broken[field] = 1
            with self.assertRaisesRegex(ValueError, "failed"):
                check_receipt(broken, inputs, outputs)
        receipt["exception_used"] = True
        receipt["u15_outer_exception_approval"] = {"approved_by": "outer(claude)"}
        with self.assertRaisesRegex(ValueError, "Historical"):
            check_receipt(receipt, inputs, outputs)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    cases = [InputTests] if mode == "--inputs" else [BakeTests] if mode == "--bake" else [InputTests, BakeTests]
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(case) for case in cases)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps(dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        execution_enabled=False, rollout_ready=False, board_access=False, vm_access=False, bake_executed=False)))
    sys.exit(0 if result.wasSuccessful() else 1)
