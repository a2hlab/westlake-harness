import copy
import hashlib
import json
from pathlib import Path
import unittest

from validation import class_allowance, known_delta, same_objects

HERE = Path(__file__).resolve().parent


def load(name):
    return json.loads((HERE / name).read_text())


class BindingTests(unittest.TestCase):
    def test_true_baseline_and_all_three_boards(self):
        composition = load("composition.json")
        expected = {"5ea34a4500000000000000001123012c": "f3b604c94df4", "5cd1e3dd00000000000000000923012c": "f3b604c94df4", "61b0657200000000000000000324012c": "d6848fa2c989"}
        self.assertEqual(composition["base_bundle_sha256"], "190afedd3ddb250752e67b83d19669b6a952eb04cd69db5edf0b06eafe119736")
        for serial, board in composition["baseline_boards"].items():
            self.assertEqual(len(board["expected"]), 316)
            self.assertEqual(board["identity_assertions"], 318)
            for kind, paths in board["reference_paths"].items():
                text = "\n".join(sorted(board["expected"][target] + "  " + target for target in paths))
                fingerprint = hashlib.sha256(text.encode()).hexdigest()[:12]
                self.assertEqual(fingerprint, expected[serial] if kind == "runtime" else "e3806b65a079")

    def test_only_metadata_changes_and_native_bindings_hold(self):
        composition = load("composition.json")
        self.assertEqual(composition["payload_changed_from_u13"], [])
        self.assertEqual(composition["boot_outputs_changed_from_u13"], [])
        self.assertTrue(composition["native_manifest_unchanged"])
        self.assertEqual(composition["native_manifest_sha256"], "85aef68eafbde98e6ac885264fe36f2f1e357618abf1d455de6ca15c0996cee6")
        self.assertEqual(composition["native_inputs_sha256"], "c40faa79d197f023dbe47a62ae186d5eb5671f9b8f4a448924098fdd5f02f185")
        manifest = load("manifests/native-manifest.json")
        self.assertEqual(manifest["files"]["payload/runtime/appspawn-x"][:8], "2a87118e")
        self.assertFalse(load("manifests/bundle.json")["rollout_ready"])

    def test_three_additions_and_twenty_seven_images(self):
        plan = load("transaction-plan.json")
        self.assertEqual(len(plan["additions"]), 3)
        self.assertEqual(len(plan["baseline"]), 316)
        self.assertEqual(len(plan["expected"]), 319)
        self.assertEqual(len(plan["changes"]), 40)
        self.assertEqual(plan["build_receipt"]["status"], "verified")
        self.assertEqual(load("image-binding-transfer.json")["count"], 27)
        self.assertEqual(len(load("new-native-admissions-delta.json")["admissions"]), 3)

    def test_exact_static_review_and_no_new_findings(self):
        transferred = load("evidence/static-transferred-preview.json")
        self.assertEqual(transferred["status"], "PASS")
        self.assertEqual(load("binding-transfer.json")["new_findings"], [])
        report = load("evidence/static-unapproved.json")
        member = next(row for row in report["members"] if row["target"] == "/system/bin/appspawn-x")
        self.assertTrue(known_delta(member, [member]))
        mutated = copy.deepcopy(member)
        mutated["open_site_delta"]["added"][0]["namespace"] = ["default"]
        self.assertFalse(known_delta(mutated, [member]))

    def test_class_union_cannot_admit_unknown_addition(self):
        policy = load("static-policy.json")
        self.assertEqual(len(policy["jars"]["/system/android/framework/oh-adapter-runtime.jar"]["allow_add"]), 19)
        self.assertEqual(len(policy["jars"]["/system/android/framework/adapter-mainline-stubs.jar"]["allow_add"]), 1)
        self.assertEqual(class_allowance(["Lknown;"], ["Lknown;"]), ["Lknown;"])
        with self.assertRaises(ValueError):
            class_allowance(["Lunknown;"], ["Lknown;"])

    def test_inventory_drift_refused(self):
        self.assertTrue(same_objects({"runtime": "same"}, {"runtime": "same"}))
        with self.assertRaises(ValueError):
            same_objects({"runtime": "same"}, {"runtime": "different"})

    def test_unrun_production_is_not_success(self):
        composition = load("composition.json")
        self.assertEqual(composition["production_status"], "PENDING_OUTER_FRESH_REPLAY")
        self.assertFalse(composition["active_registry_updated"])
        self.assertFalse(composition["execution_enabled"])
        self.assertFalse(load("new-native-admissions-delta.json")["applied"])
        source = (HERE / "common.py").read_text()
        self.assertIn('BASE = WS / "westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle"', source)
        self.assertIn('"--baseline-native", BASE / "native"', (HERE / "offline_gates.py").read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
