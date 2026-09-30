"""Offline identity, coverage and strict prospective-scoring controls."""

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "benchmark/2026-09-29-static-wall-prediction"))
from rules_u5_feedback import input_findings
from forecast import OLD_CSVS, build, check_run, digest, outputs, read, score_reviewed, verify


class InputTests(unittest.TestCase):
    def test_five_real_merged_inputs_and_dex(self):
        document = read(HERE / "input-facts.json")
        old = read(ROOT / "benchmark/2026-10-01-u5-feedback-v1/static-facts.json")
        previous = {row["entry"]["key"]: row for row in old["apps"]}
        expected = {"burgerking": (34, "76ff64914f0bc25e"), "firefox": (18, "a72db02671ceddfb"),
                    "mcdonalds": (10, "340c0d59f4bd0b85"), "subwaysurfers": (20, "4b06bd74a49f364b"),
                    "x": (33, "eaed447b994a2d7d")}
        for row in document["apps"]:
            key = row["entry"]["key"]
            self.assertFalse(row["scan_errors"], key)
            if key not in expected:
                continue
            count, prefix = expected[key]
            self.assertEqual(len(row["apks"]), 1)
            self.assertEqual(len(row["sidecars"]), count)
            self.assertTrue(row["entry"]["apk_sha256"].startswith(prefix))
            self.assertNotEqual(row["entry"]["apk_sha256"], previous[key]["selected_apk"]["sha256"])
            self.assertEqual(row["dex"], previous[key]["dex"])
            self.assertEqual(row["input_findings"], [])
            self.assertEqual(row["scan_mode"], "fresh-all-dex-and-embedded-native")
        rows = {row["entry"]["key"]: row for row in document["apps"]}
        self.assertIn("mozglue-strerror", {risk["family"] for risk in rows["firefox"]["native_and_dex_requirements"]})
        self.assertIn("realm-libz", {risk["family"] for risk in rows["mcdonalds"]["native_and_dex_requirements"]})

    def test_metadata_only_cleanup_does_not_clear_physical_input(self):
        prior = read(HERE / "evidence/input-repair-gap.json")
        for key in ["fd-seal", "toutiao"]:
            bad = prior["keys"][key]["bad_sidecars"][0]["evidence"]
            facts = dict(entry=dict(apk_sha256="a" * 64), metadata_apk_sha256="a" * 64,
                         apks=[dict(sha256="a" * 64)], sidecars=bad, declared_sidecars=[])
            self.assertEqual(input_findings(facts)[0]["category"], "non-aarch64-sidecar")
            facts["sidecars"] = []
            self.assertEqual(input_findings(facts), [])


class CandidateTests(unittest.TestCase):
    def test_candidate_artifacts_and_exact_boot_api_delta(self):
        candidate = read(HERE / "candidate.json")
        members = read(HERE / "evidence/jar-api-members.json")
        self.assertEqual(candidate["boot_variant"], "T7c")
        self.assertEqual(len(candidate["boot_files"]), 28)
        self.assertEqual(candidate["j7b_sha256"], members["J7b"]["sha256"])
        self.assertEqual(candidate["j6_sha256"], members["J6"]["sha256"])
        self.assertEqual(candidate["boot_files"]["adapter-mainline-stubs.jar"], members["T7c-stubs"]["sha256"])
        expected = {"org/ccil/cowan/tagsoup/Parser": "setProperty:(Ljava/lang/String;Ljava/lang/Object;)V",
                    "android/net/NetworkRequest": "getNetworkSpecifier:()Landroid/net/NetworkSpecifier;",
                    "android/provider/MediaStore$Images$Media": "EXTERNAL_CONTENT_URI:Landroid/net/Uri;",
                    "android/net/NetworkInfo": "getState:()Landroid/net/NetworkInfo$State;",
                    "android/net/NetworkCapabilities": "getLinkUpstreamBandwidthKbps:()I"}
        for owner, member in expected.items():
            self.assertIn(member, members["T7c-stubs"]["selected"][owner])
            self.assertNotIn(member, members["U5-stubs"]["selected"][owner])
        self.assertIsNone(members["T7c-stubs"]["selected"]["android/net/ssl/SSLSockets"])
        self.assertNotIn("getSignalStrength:()I", members["T7c-stubs"]["selected"]["android/net/NetworkCapabilities"])
        self.assertEqual(len(read(HERE / "api-repairs.json")), 14)

    def test_run_binding_rejects_t7d_n5_and_input_drift(self):
        _, expected = build()
        check_run(expected, copy.deepcopy(expected))
        for section, key in [("boot_files", "/system/android/framework/adapter-mainline-stubs.jar"),
                             ("runtime_files", "/system/android/lib64/libapp_native_loader.so")]:
            observed = copy.deepcopy(expected)
            observed[section][key] = "0" * 64
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                check_run(expected, observed)
        observed = copy.deepcopy(expected)
        observed["apps"]["firefox"]["apk_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            check_run(expected, observed)


class CoverageTests(unittest.TestCase):
    def test_sixty_six_rows_have_criteria_and_bound_inputs(self):
        report, bindings = build()
        self.assertEqual(len(report["rows"]), 66)
        self.assertEqual({row["key"] for row in report["rows"]}, set(bindings["apps"]))
        for row in report["rows"]:
            for field in ["first_wall", "wall_id", "kind", "wall_criterion", "checkpoint_criterion", "t20_criterion", "evidence"]:
                self.assertTrue(row[field], (row["key"], field))
            self.assertEqual(row["apk_sha256"], bindings["apps"][row["key"]]["apk_sha256"])
            if row["input_findings"]:
                self.assertEqual(row["kind"], "input-blocked")
        by_key = {row["key"]: row for row in report["rows"]}
        self.assertEqual(by_key["fd-wifianalyzer"]["wall_id"], "country-preference-null")
        self.assertEqual(by_key["fd-reader"]["wall_id"], "unknown")
        self.assertEqual(by_key["wikipedia"]["wall_id"], "ssl-sockets-class")
        self.assertEqual(sum(row["flaky"] for row in report["rows"]), 4)


class FreezeTests(unittest.TestCase):
    def test_frozen_hash_drift_is_refused(self):
        with patch("forecast.digest", return_value="0" * 64):
            with self.assertRaisesRegex(ValueError, "Frozen file changed"):
                verify()

    def test_frozen_replay_and_historical_csvs(self):
        verify()
        for relative, expected in OLD_CSVS.items():
            self.assertEqual(digest(ROOT / relative), expected)
        for name, content in outputs().items():
            self.assertEqual((HERE / name).read_text(), content)

    def test_missing_masked_and_wrong_identity_never_pass(self):
        row = next(row for row in build()[0]["rows"] if row["key"] == "fd-catima")
        unknown = dict(first_wall="unknown", checkpoints="unknown", t20="unknown")
        self.assertEqual(score_reviewed(row, {}), unknown)
        observation = dict(identity_verified=True, first_attempt=True, old_error_absent=True, earlier_wall=True)
        self.assertEqual(score_reviewed(row, observation), unknown)
        observation.update(first_wall_confirmed=True, first_wall_id="none", positive_crossings=row["fix_ids"], t20_reviewed=True, own_ui=True)
        self.assertEqual(set(score_reviewed(row, observation).values()), {"hit"})
        observation["old_wall_reproduced"] = row["fix_ids"]
        self.assertEqual(score_reviewed(row, observation)["checkpoints"], "unknown")
        observation["identity_verified"] = False
        self.assertEqual(score_reviewed(row, observation), unknown)

    def test_old_wall_and_ui_failure_are_not_success(self):
        row = next(row for row in build()[0]["rows"] if row["key"] == "opencamera")
        observation = dict(identity_verified=True, first_attempt=True, first_wall_confirmed=True,
                           first_wall_id="battery-intent-null", old_wall_reproduced=["J7-battery"],
                           t20_reviewed=True, own_ui=False)
        self.assertEqual(set(score_reviewed(row, observation).values()), {"false_positive"})
        row = next(row for row in build()[0]["rows"] if row["key"] == "fd-uhabits")
        self.assertEqual(score_reviewed(row, observation)["t20"], "unknown")


if __name__ == "__main__":
    unittest.main()
