import copy
import importlib.util
import subprocess
import sys
import unittest

import skeleton


class CoverageTests(unittest.TestCase):
    def test_reproduce_66_pending_rows(self):
        report = skeleton.build()
        self.assertEqual(report, skeleton.read(skeleton.HERE / "SKELETON.json"))
        self.assertEqual(66, len(report["rows"]))
        self.assertEqual(66, len({row["key"] for row in report["rows"]}))
        for row in report["rows"]:
            self.assertEqual("draft-not-frozen", row["status"])
            self.assertIsNone(row["u6_measured_first_wall"])
            for field in ("u7_input_identity", "u7_first_wall_prediction", "u7_checkpoint_predictions", "u7_t20_prediction"):
                self.assertIsNone(row[field])
        blocked = {row["key"]: row for row in report["rows"]}
        for key in ("fd-seal", "toutiao"):
            self.assertTrue(blocked[key]["u6_reference_only"]["input_findings"])
            self.assertIsNone(blocked[key]["u7_input_identity"])


class CatalogTests(unittest.TestCase):
    def test_source_hashes_methods_and_limits(self):
        skeleton.verify_priors()
        catalog = skeleton.read(skeleton.HERE / "repair-catalog.json")
        groups = catalog["t7d"]["groups"]
        self.assertEqual(6, len(groups))
        self.assertEqual(7, sum(len(group["methods"]) for group in groups))
        self.assertFalse(any("MediaServiceManager" in group["owner"] for group in groups))
        self.assertEqual(6, len(set(catalog["n6"]["keys"])))
        self.assertTrue(any("JNI fid=null" in limit for limit in catalog["n6"]["limits"]))
        sources = {source["id"]: source for source in skeleton.read(skeleton.HERE / "evidence/source-priors.json")["sources"]}
        for group in groups:
            witness = group["evidence"]
            self.assertLessEqual(witness["last_line"], len(sources[witness["source"]]["lines"]))
            for method in group["methods"]:
                self.assertIn(method.split("(")[0], "\n".join(line["text"] for line in sources["t7d-patch"]["lines"]))

    def test_out_of_scope_keys_not_claimed(self):
        rows = {row["key"]: row for row in skeleton.build()["rows"]}
        for key in ("fd-libretube", "fd-feeder"):
            self.assertEqual([], rows[key]["candidate_repair_ids"])
        self.assertEqual(["N6-flutter-window"], rows["localsend"]["candidate_repair_ids"])


class IntakeTests(unittest.TestCase):
    def test_absent_evidence_is_pending(self):
        intake = skeleton.read(skeleton.HERE / "intake.json")
        result = skeleton.readiness(intake)
        self.assertEqual(16, len(result["missing"]))
        self.assertFalse(result["ready_for_evidence_review"])
        self.assertFalse(result["freeze_authorized"])
        result = subprocess.run([sys.executable, str(skeleton.HERE / "skeleton.py"), "--check", "--readiness"], capture_output=True, text=True)
        self.assertEqual(2, result.returncode, result.stderr)
        self.assertFalse((skeleton.HERE / "FREEZE.json").exists())
        self.assertFalse((skeleton.HERE / "PREDICTIONS.csv").exists())

    def test_completed_checklist_is_not_authorization(self):
        intake = copy.deepcopy(skeleton.read(skeleton.HERE / "intake.json"))
        for section in ("u6_scoring", "u7_prediction"):
            for name in intake[section]:
                intake[section][name] = {"evidence": "synthetic-not-a-real-receipt", "reviewer": "fixture"}
        self.assertTrue(skeleton.readiness(intake)["ready_for_evidence_review"])
        self.assertFalse(skeleton.readiness(intake)["freeze_authorized"])
        intake["u7_prediction"] = True
        self.assertFalse(skeleton.readiness(intake)["ready_for_evidence_review"])


class ScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(skeleton.U6))
        spec = importlib.util.spec_from_file_location("u6_frozen_forecast", skeleton.U6 / "forecast.py")
        cls.forecast = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.forecast)

    def setUp(self):
        self.row = {"wall_id": "next-wall", "fix_ids": ["repair-one", "repair-two"], "flaky": False, "t20_prediction": "own-ui"}
        self.observation = {"identity_verified": True, "first_attempt": True, "first_wall_confirmed": True, "first_wall_id": "next-wall", "positive_crossings": ["repair-one", "repair-two"], "t20_reviewed": True, "own_ui": False}

    def test_independent_axes(self):
        self.assertEqual({"first_wall": "hit", "checkpoints": "hit", "t20": "false_positive"}, self.forecast.score_reviewed(self.row, self.observation))
        self.observation["positive_crossings"] = ["repair-one"]
        self.observation["t20_reviewed"] = False
        self.assertEqual({"first_wall": "hit", "checkpoints": "unknown", "t20": "unknown"}, self.forecast.score_reviewed(self.row, self.observation))

    def test_missing_identity_or_retries_unknown(self):
        for field in ("identity_verified", "first_attempt"):
            observation = dict(self.observation, **{field: False})
            self.assertEqual({"first_wall": "unknown", "checkpoints": "unknown", "t20": "unknown"}, self.forecast.score_reviewed(self.row, observation))

    def test_contradiction_and_flaky_unknown(self):
        self.row["flaky"] = True
        self.observation["old_wall_reproduced"] = ["repair-one"]
        result = self.forecast.score_reviewed(self.row, self.observation)
        self.assertEqual("unknown", result["checkpoints"])
        self.assertEqual("unknown", result["t20"])


if __name__ == "__main__":
    unittest.main()
