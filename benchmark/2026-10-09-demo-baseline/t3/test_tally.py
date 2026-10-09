import copy
import json
import unittest

import build_tally


class TallyTests(unittest.TestCase):
    def setUp(self):
        apps = [{"key": key, "package": "pkg." + key, "name_zh": key,
                 "historical_content_status": tier, "counts_as_first_content": tier == "shown"}
                for key, tier in (("content", "shown"), ("empty", "minimal"), ("error", "errors"))]
        self.manifest = {"schema": "demo-baseline-manifest/v1", "apps": apps, "signed_games": ["content"],
                         "summary": {"historical_first_content_packages": 1, "pending_first_tap_packages": 1,
                                     "error_screen_packages": 1, "distinct_packages": 3, "required_signed_games": 1}}
        self.signoff = {"schema": "demo-t3-outer-signoff/v1", "board": build_tally.summarize.BOARD,
                        "verdicts": {"content": {"verdict": "lit_splash", "batch": "window1"},
                                     "empty": {"verdict": "lit", "batch": "capture-04"}}}

    def test_empty_lit_not_added_to_content_and_unsigned_pending(self):
        report = build_tally.summarize.tally_signoff(self.manifest, self.signoff)
        self.assertEqual(report["first_content"]["signed_lit_keys"], ["content"])
        self.assertEqual(report["summary"]["tiers"]["minimal"]["signed_lit"], 1)
        self.assertEqual([row["key"] for row in report["pending"]], ["error"])
        self.assertFalse(report["required_games"][0]["interaction_verified"])

    def test_half_and_not_lit_are_not_counted(self):
        for verdict in ("half_empty", "half_loading", "not_lit"):
            self.signoff["verdicts"]["content"]["verdict"] = verdict
            report = build_tally.summarize.tally_signoff(self.manifest, self.signoff)
            self.assertEqual(report["first_content"]["signed_lit_keys"], [])

    def test_unknown_key_or_verdict_rejected(self):
        for key, verdict in (("other", "lit"), ("content", "own-content")):
            value = copy.deepcopy(self.signoff)
            value["verdicts"][key] = {"verdict": verdict, "batch": "capture-05"}
            with self.assertRaises(ValueError):
                build_tally.summarize.tally_signoff(self.manifest, value)

    def test_wrong_board_duplicate_package_and_tier_rejected(self):
        wrong_board = copy.deepcopy(self.signoff)
        wrong_board["board"] = "5ea"
        with self.assertRaises(ValueError):
            build_tally.summarize.tally_signoff(self.manifest, wrong_board)
        for changed in ("package", "counts_as_first_content"):
            value = copy.deepcopy(self.manifest)
            value["apps"][1][changed] = "pkg.content" if changed == "package" else True
            with self.assertRaises(ValueError):
                build_tally.summarize.tally_signoff(value, self.signoff)

    def test_updated_signoff_replaces_pending_without_retaining_prior_counts(self):
        self.signoff["verdicts"]["error"] = {"verdict": "not_lit", "batch": "capture-05"}
        report = build_tally.summarize.tally_signoff(self.manifest, self.signoff)
        self.assertEqual(report["pending"], [])
        self.assertEqual(report["summary"]["signed_packages"], 3)

    def test_published_inputs_regenerate_report_twice(self):
        manifest = json.loads((build_tally.HERE.parent / "demo-manifest.json").read_text())
        signoff = json.loads((build_tally.HERE / "outer-signoff-input.json").read_text())
        first = build_tally.summarize.tally_signoff(manifest, signoff)
        second = build_tally.summarize.tally_signoff(manifest, signoff)
        self.assertEqual(first, second)
        saved = json.loads((build_tally.HERE / "tally.json").read_text())
        self.assertEqual(first, {key: value for key, value in saved.items() if key != "inputs"})
        self.assertEqual(build_tally.markdown(saved), (build_tally.HERE / "tally.md").read_text())


if __name__ == "__main__":
    unittest.main()
