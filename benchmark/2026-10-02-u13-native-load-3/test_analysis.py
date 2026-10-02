import argparse
import hashlib
import json
from pathlib import Path
import unittest

from collect import app_context, matches_required, parse_symbols, portable

HERE = Path(__file__).resolve().parent


class EvidenceTests(unittest.TestCase):
    def test_pid_filter_preserves_full_file_line(self):
        lines = ["10-02 01:00:00.000 90 91 E MUSL-LDSO: wrong app symbol",
                 "10-02 01:00:00.001 30 31 E MUSL-LDSO: actual symbol",
                 "10-02 01:00:00.002 30 31 I CHILD_CK: J_invokeStaticMain_main_threw: failure"]
        result = app_context(lines)
        self.assertEqual(result["pid"], 30)
        self.assertEqual([row["line"] for row in result["rows"]], [2, 3])

    def test_sha_and_versioned_symbol_parser(self):
        self.assertFalse(matches_required("expected", "drift"))
        rows = parse_symbols(" 3: 00000000 0 FUNC GLOBAL DEFAULT UND __register_atfork@LIBC\n"
                             " 4: 00000020 88 FUNC GLOBAL DEFAULT 16 __register_atfork@@LIBC\n")
        self.assertEqual(rows[0]["name"], "__register_atfork")
        self.assertEqual(rows[1]["version"], "LIBC")
        self.assertEqual(rows[0]["section"], "UND")

    def test_real_lines_consumer_and_provider_completeness(self):
        logs = json.loads((HERE / "log-index.json").read_text())
        self.assertEqual({key: row["pid"] for key, row in logs.items()},
                         {"fd-im-vector-app": 26007, "mindustry": 6536, "fd-meet": 28539})
        for value in logs.values():
            self.assertTrue(all(row["pid"] == value["pid"] for row in value["rows"]))
        comparison = json.loads((HERE / "consumer-comparison.json").read_text())
        self.assertEqual(len(comparison["consumers"]), 5)
        for row in comparison["consumers"]:
            self.assertTrue(row["native_assembly_sha_verified"])
            self.assertEqual(len(row["undefined_inventory"]), len(row["strong_undefined"]) + len(row["weak_undefined"]))
            self.assertEqual(len(row["needed_inventory"]), len(row["needed"]))
        total = sum(len(row["strong_undefined"]) for row in comparison["consumers"])
        self.assertEqual(total, 1150)

    def test_published_outputs_and_portable_boundary(self):
        tools = json.loads((HERE / "raw-evidence.json").read_text())["tools"]
        for row in tools:
            path = HERE / row["evidence"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), row["evidence_sha256"])
        self.assertTrue(any(row["label"] == "artifact-identity-t8" and row["exit_code"] == 0 for row in tools))
        self.assertNotIn("$REPO-", portable(str(HERE.parents[2] / "westlake-harness-u7-executor/evidence")))


class PredictionTests(unittest.TestCase):
    def setUp(self):
        self.results = json.loads((HERE / "results.json").read_text())
        self.rows = {row["key"]: row for row in self.results["rows"]}
        self.providers = json.loads((HERE / "selected-provider-facts.json").read_text())

    def test_element_existing_u12_not_double_counted(self):
        row = self.rows["fd-im-vector-app"]
        self.assertEqual(row["conditional_move_vs_t8"], 1)
        self.assertEqual(row["incremental_move_vs_u12"], 0)
        self.assertEqual(self.results["counts"]["zlib_imports"], 0)
        self.assertIn("libz.so", row["terminal"]["text"])
        self.assertEqual(self.providers["u12-zlib-alias"]["needed"], ["libshared_libz.z.so"])

    def test_meet_is_not_private_permission_or_global_missing_export(self):
        row = self.rows["fd-meet"]
        self.assertEqual(row["permission_only_moves"], 0)
        self.assertEqual(row["namespace"]["name"], None)
        index = {value["line"]: value["text"] for value in row["evidence"]}
        self.assertIn("__register_atfork", index[25376])
        self.assertIn("android_set_abort_message", index[25527])
        bridge = {value["spelling"] for value in self.providers["pthread-bridge"]["exports"]}
        compat = {value["name"] for value in self.providers["compat"]["exports"]}
        self.assertIn("__register_atfork@@LIBC", bridge)
        self.assertIn("android_set_abort_message", compat)
        self.assertNotIn("__register_atfork", compat)

    def test_audio_loading_does_not_claim_play_completion(self):
        row = self.rows["mindustry"]
        self.assertEqual(row["conditional_move_vs_t8"], 1)
        facade = {value["name"] for value in self.providers["facade"]["exports"]}
        oh = {value["name"] for value in self.providers["oh-audio"]["exports"]}
        self.assertNotIn("slCreateEngine", facade)
        self.assertIn("slCreateEngine", oh)
        self.assertIn("returns12", row["next_first_fatal"])
        self.assertEqual(row["delivered_u13_prediction_vs_t8"], 0)

    def test_no_candidate_no_deployment_no_ui_claim(self):
        self.assertFalse(self.results["execution_enabled"])
        self.assertTrue(self.results["no_candidates"])
        self.assertTrue(self.results["no_device_operations"])
        self.assertEqual(self.results["observed_moves"], 0)
        self.assertEqual(self.results["current_delivered_u13_incremental_move_vs_u12"], 0)
        self.assertTrue(all(row["t20"] == "unknown" for row in self.rows.values()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", choices=["evidence", "predictions"])
    args = parser.parse_args()
    classes = {"evidence": EvidenceTests, "predictions": PredictionTests}
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(value)
        for key, value in classes.items() if args.part is None or key == args.part)
    raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
