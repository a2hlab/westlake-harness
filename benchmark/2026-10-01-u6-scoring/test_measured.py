import copy
from collections import Counter
from pathlib import Path
import shutil
import unittest

import measured
import score
from test_score import Fixture


CHANGED = {"burgerking", "mcdonalds", "subwaysurfers", "x", "fd-seal", "toutiao"}
FLAKY = {"antennapod", "fd-noice", "fd-notes", "fd-uhabits"}


class MeasuredIntakeTests(Fixture):
    def setUp(self):
        super().setUp()
        entries = iter(self.index["selected"])
        self.summaries = []
        for shard, count in measured.SHARDS.items():
            board = self.root / shard / "run" / "serial"
            board.mkdir(parents=True)
            records = []
            for unused in range(count):
                entry = next(entries)
                source = self.root / entry["record"]
                records.append(score.read(source))
                shutil.copytree(source.parent, board / entry["key"])
            for filename in ["runtime-fingerprint.txt", "boot-image-fingerprint.txt"]:
                shutil.copyfile(self.root / "runs/u6-synthetic/serial" / filename, board / filename)
            for filename in ["plan.json", "baseline.json", "facts.txt"]:
                (board / filename).write_text("{}\n")
            summary = board / "summary.json"
            summary.write_text(score.encoded(dict(records=records)))
            self.summaries.append(summary)

    def test_four_shards_and_inventory(self):
        indexed, paths = measured.discover(self.root)
        self.assertEqual((66, 16, 66), (len(indexed[0]), len(indexed[1]), len(paths)))
        prepared = measured.prepare(self.root)
        self.assertEqual(66, len(prepared["rows"]))
        self.assertTrue(all(row["identity_verified"] and row["first_attempt"] for row in prepared["rows"]))

    def test_summary_tamper_missing_duplicate_and_extra(self):
        summary_path = self.summaries[0]
        original = score.read(summary_path)
        changed = copy.deepcopy(original)
        changed["records"][0]["apk_sha256"] = "0" * 64
        summary_path.write_text(score.encoded(changed))
        with self.assertRaisesRegex(ValueError, "differs"):
            measured.discover(self.root)
        changed = copy.deepcopy(original)
        changed["records"].pop()
        summary_path.write_text(score.encoded(changed))
        with self.assertRaisesRegex(ValueError, "cohort"):
            measured.discover(self.root)
        changed = copy.deepcopy(original)
        changed["records"][1] = changed["records"][0]
        summary_path.write_text(score.encoded(changed))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            measured.discover(self.root)
        summary_path.write_text(score.encoded(original))
        extra = summary_path.parent / "extra/record.json"
        extra.parent.mkdir()
        extra.write_text("{}")
        with self.assertRaisesRegex(ValueError, "extra"):
            measured.discover(self.root)
        extra.unlink()
        summary_path.unlink()
        with self.assertRaisesRegex(ValueError, "exactly one"):
            measured.discover(self.root)

    def test_actual_identity_pins(self):
        expected = score.read(score.FROZEN / "expected-run.json")
        index = score.read(score.HERE / "evidence/u6-index.json")
        self.assertEqual(66, len(index["files"]))
        self.assertEqual(16, len(index["indices"]))
        mismatch, captures = set(), 0
        for filename, digest in index["files"].items():
            path = score.HERE / "evidence/u6" / filename
            self.assertEqual(digest, score.sha(path))
            row = score.read(path)
            frozen = expected["apps"][row["key"]]
            self.assertEqual(frozen["apk_sha256"], row["identity"]["apk_sha256"])
            self.assertEqual(frozen["package"], row["identity"]["package"])
            self.assertEqual((119, 36), (row["runtime_count"], row["boot_count"]))
            self.assertTrue(row["candidate_comparable"])
            if frozen["sidecars"] != row["identity"]["sidecars"]:
                mismatch.add(row["key"])
                self.assertFalse(row["identity_verified"])
            else:
                self.assertTrue(row["identity_verified"])
            captures += bool(row["t20_sha256"])
        self.assertEqual(CHANGED, mismatch)
        self.assertEqual(65, captures)


class MeasuredReplayTests(unittest.TestCase):
    def setUp(self):
        self.scored = score.read(score.HERE / "SCORING.json")
        self.review = score.read(score.HERE / "REVIEW.json")
        self.predictions = {row["key"]: row for row in score.read(score.FROZEN / "PREDICTIONS.json")["rows"]}
        self.rows = {row["key"]: row for row in self.scored["rows"]}

    def test_all_rows_three_axes_and_witnesses(self):
        score.verify_freeze()
        self.assertEqual(score.seal(self.review), self.scored["review_sha256"])
        self.assertEqual(set(self.predictions), set(self.rows))
        for review in self.review["rows"]:
            key = review["key"]
            row = score.read(score.HERE / "evidence/u6" / (key + ".json"))
            observed = score.observation(row, review)
            self.assertEqual(self.rows[key]["observation"], observed)
            self.assertEqual(self.rows[key]["scores"], score.forecast.score_reviewed(self.predictions[key], observed))
            self.assertEqual(set(row["allowed_evidence_lines"]), {event["line"] for event in row["review_witnesses"]})
            for event in row["review_witnesses"]:
                self.assertIn(event["pid"], row["target_pids"])
                self.assertLessEqual(event["timestamp"], row["cutoff"])
        self.assertEqual(self.scored["counts"], {axis: dict(Counter(row["scores"][axis] for row in self.rows.values()))
                                             for axis in ["first_wall", "checkpoints", "t20"]})

    def test_strict_input_and_flaky_exclusions(self):
        for key in CHANGED:
            self.assertEqual({"unknown"}, set(self.rows[key]["scores"].values()))
        for key in FLAKY:
            self.assertEqual("unknown", self.rows[key]["scores"]["t20"])
        self.assertEqual(29, sum(row["observation"].get("own_ui") is True for row in self.rows.values()))
        self.assertEqual(27, self.scored["outer_lighting"]["stable_total"])

    def test_misses_are_not_laundered(self):
        self.assertEqual({"fd-client", "fd-feeder", "fd-immich", "fd-plus", "wikipedia"},
                         {key for key, row in self.rows.items() if row["scores"]["first_wall"] == "false_positive"})
        self.assertEqual({"fd-feeder"}, {key for key, row in self.rows.items() if row["scores"]["t20"] == "false_positive"})
        self.assertEqual({"fd-catima", "fd-uhabits", "fd-wifianalyzer", "opencamera", "firefox"},
                         {key for key, row in self.rows.items() if row["scores"]["checkpoints"] == "hit"})
        for key in ["firefox", "fd-fennec_fdroid", "ppsspp", "fd-reader"]:
            self.assertEqual("unknown", self.rows[key]["scores"]["first_wall"])

    def test_tampered_claim_rejected(self):
        row = score.read(score.HERE / "evidence/u6/fd-client.json")
        review = copy.deepcopy(self.rows["fd-client"]["review"])
        review["first_wall"]["lines"] = [50595]
        with self.assertRaisesRegex(ValueError, "selected termination"):
            score.observation(row, review)
        review = copy.deepcopy(self.rows["fd-client"]["review"])
        review["t20"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "unbound"):
            score.observation(row, review)


if __name__ == "__main__":
    unittest.main()
