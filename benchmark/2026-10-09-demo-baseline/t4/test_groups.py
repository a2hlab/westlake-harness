import json
from pathlib import Path
import unittest

import build_groups


def app(**changes):
    row = {"key": "sample", "package": "org.sample", "apk_sha256": "a" * 64,
           "name_zh": "sample", "historical_content_status": "shown", "is_game": False}
    row.update(changes)
    return row


def observation(board, **changes):
    row = {"board": board, "runs": 1, "lit_runs": 1, "selected_apk_identity": True, "white_observed": False}
    row.update(changes)
    return row


class AssignmentTests(unittest.TestCase):
    def test_two_lit_runs_on_two_real_boards_is_stable(self):
        result = build_groups.assignment(app(), [observation("5ea"), observation("61b")])
        self.assertEqual(result["group"], "stable")
        self.assertEqual(result["screenshot_seconds"], 10)

    def test_two_runs_on_only_one_board_remains_edge(self):
        result = build_groups.assignment(app(), [observation("5ea", runs=6, lit_runs=6)])
        self.assertEqual(result["group"], "edge")

    def test_white_at_any_time_overrides_two_lit_boards(self):
        result = build_groups.assignment(app(), [observation("5ea"), observation("61b"),
                                                observation("5cd", lit_runs=0, white_observed=True)])
        self.assertEqual(result["group"], "edge")

    def test_game_empty_and_error_overrides(self):
        for changes in ({"is_game": True}, {"historical_content_status": "minimal"}, {"historical_content_status": "errors"}):
            with self.subTest(changes=changes):
                result = build_groups.assignment(app(**changes), [observation("5ea"), observation("61b")])
                self.assertEqual(result["group"], "edge")
                self.assertEqual(result["screenshot_seconds"], 20)

    def test_different_apk_alias_cannot_supply_second_board(self):
        result = build_groups.assignment(app(), [observation("5ea", runs=6, lit_runs=6),
                                                observation("61b", selected_apk_identity=False)])
        self.assertEqual(result["group"], "edge")
        self.assertEqual(result["history"]["lit_boards"], ["5ea"])

    def test_invalid_counts_reject(self):
        with self.assertRaises(ValueError):
            build_groups.counts({"runs": 1, "lit_runs": 2})

    def test_shipped_groups_have_complete_and_eligible_partition(self):
        groups = json.loads((Path(__file__).parent / "groups.json").read_text())
        self.assertEqual(len(groups["apps"]), 128)
        self.assertEqual(len(set(groups["stable_keys"]) | set(groups["edge_keys"])), 128)
        self.assertFalse(set(groups["stable_keys"]) & set(groups["edge_keys"]))
        for row in groups["apps"]:
            if row["group"] == "stable":
                self.assertGreaterEqual(row["history"]["lit_runs"], 2)
                self.assertGreaterEqual(len(row["history"]["lit_boards"]), 2)
                self.assertFalse(row["history"]["white_observed"])
                self.assertFalse(row["reasons"])
        self.assertTrue(all(row["group"] == "edge" for row in groups["special_slots"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
