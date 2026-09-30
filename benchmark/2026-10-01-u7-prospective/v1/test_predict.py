import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import predict


class CandidateTests(unittest.TestCase):
    def test_exact_composition_and_reject_native_drift(self):
        candidate = predict.read(predict.HERE / "candidate.json")
        inputs = predict.read(predict.HERE / "inputs.json")
        predict.validate(candidate, inputs)
        prior = predict.read(predict.U6 / "expected-run.json")
        self.assertEqual(prior["runtime_files"], candidate["runtime_files"])
        self.assertEqual((119, 36, 28), tuple(len(candidate[name]) for name in ["runtime_files", "boot_files", "replacements"]))
        self.assertEqual(candidate["stubs_sha256"], candidate["boot_files"]["/system/android/framework/adapter-mainline-stubs.jar"])
        candidate["runtime_files"]["/system/android/lib64/libz.so"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "drift"):
            predict.validate(candidate, inputs)


class InputTests(unittest.TestCase):
    def test_actual_inventory_and_negative_pins(self):
        candidate = predict.read(predict.HERE / "candidate.json")
        inputs = predict.read(predict.HERE / "inputs.json")
        selected = predict.validate(candidate, inputs)
        self.assertEqual(66, len(selected))
        expected = {"fd-seal": 6, "toutiao": 137, "firefox": 18, "burgerking": 0, "mcdonalds": 0, "x": 0, "subwaysurfers": 0}
        self.assertEqual(expected, {key: len(selected[key]["sidecars"]) for key in expected})
        self.assertEqual(7, sum(row["scan_mode"] == "fresh-all-dex-and-native" for row in inputs["apps"]))
        for key in expected.keys() - {"fd-seal", "toutiao"}:
            facts = predict.read(predict.HERE / "evidence/inputs" / (key + ".json"))
            self.assertEqual(1, len(facts["apks"]))
            self.assertTrue(selected[key]["merged_manifest_badging"])
            self.assertNotIn("split='", selected[key]["merged_manifest_badging"][0])
        for field, value in [("apk_sha256", "0" * 64), ("sidecars", {})]:
            changed = copy.deepcopy(inputs)
            next(row for row in changed["apps"] if row["key"] == "fd-seal")[field] = value
            with self.assertRaisesRegex(ValueError, "drift"):
                predict.validate(candidate, changed)


class PredictionTests(unittest.TestCase):
    def test_three_axes_and_prior_limits(self):
        report, expected, apps = predict.build()
        self.assertEqual((66, 66, 66), (len(report["rows"]), len(expected["apps"]), len(apps["apps"])))
        self.assertFalse(report["combined_u7_results_consumed"])
        rows = {row["key"]: row for row in report["rows"]}
        for key in predict.FLAKY:
            self.assertEqual(("unknown", "unknown"), (rows[key]["wall_id"], rows[key]["t20_prediction"]))
        for key in ["fd-gallery", "fd-libretube", "noice"]:
            self.assertEqual("own-ui", rows[key]["t20_prediction"])
        for key in ["wikipedia", "x"]:
            self.assertEqual(("unknown", "unlit"), (rows[key]["wall_id"], rows[key]["t20_prediction"]))
        self.assertEqual("accountmanager-null", rows["fd-client"]["wall_id"])
        self.assertEqual("flutter-field-id", rows["fd-immich"]["wall_id"])
        self.assertEqual("osmand-map-layer-null", rows["fd-plus"]["wall_id"])
        self.assertEqual("unity-mediandk-load", rows["subwaysurfers"]["wall_id"])
        for row in rows.values():
            self.assertEqual(set(row["fix_ids"]), set(row["checkpoint_criteria"]))
            self.assertTrue(row["evidence"] and row["wall_criterion"] and row["t20_criterion"])
        self.assertEqual({"own-ui": 28, "unlit": 32, "unknown": 6}, report["t20_counts"])


class FreezeTests(unittest.TestCase):
    def test_freeze_hashes_and_refreeze_rejected(self):
        frozen = predict.verify()
        self.assertEqual(predict.sha(predict.HERE / "PREDICTIONS.csv"), frozen["prediction_sha256"])
        with self.assertRaisesRegex(ValueError, "already frozen"):
            predict.freeze()
        with patch.object(predict, "sha", return_value="0" * 64):
            with self.assertRaisesRegex(ValueError, "frozen bytes changed"):
                predict.verify()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises((FileNotFoundError, ValueError)):
                predict.freeze(Path(directory))


if __name__ == "__main__":
    unittest.main()
