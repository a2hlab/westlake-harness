#!/usr/bin/env python3
"""Host tests for the fail-closed J02 canonical demo validator."""

from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_canonical_demo_inputs as validator


class J02ValidatorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.journey = validator.load_yaml(cls.root / validator.J02_PATH)
        cls.unity = validator.load_yaml(
            cls.root / "docs/spec/unity-goal-ladder.yaml"
        )

    def validate(self, journey: dict) -> list[str]:
        return validator.validate_j02(self.root, journey, self.unity)

    def assert_failure_contains(
        self, journey: dict, expected_fragment: str
    ) -> None:
        failures = self.validate(journey)
        self.assertTrue(
            any(expected_fragment in failure for failure in failures),
            f"{expected_fragment!r} absent from {failures!r}",
        )

    def test_current_contract_passes(self) -> None:
        self.assertEqual(self.validate(copy.deepcopy(self.journey)), [])

    def test_missing_measurement_method_fails_closed(self) -> None:
        candidate = copy.deepcopy(self.journey)
        del candidate["measurement_methods"]["OH_PRESENT_TIMESTAMP"]
        self.assert_failure_contains(candidate, "measurement method set drifted")

    def test_generic_hilog_cannot_replace_typed_present(self) -> None:
        candidate = copy.deepcopy(self.journey)
        present = candidate["measurement_methods"]["OH_PRESENT_TIMESTAMP"]
        present["generic_hilog_accepted"] = True
        present["source"]["command"] = "hilog | grep present"
        failures = self.validate(candidate)
        self.assertTrue(any("generic hilog must be false" in f for f in failures))
        self.assertTrue(any("generic hilog source forbidden" in f for f in failures))

    def test_menu_reference_cannot_claim_missing_exit(self) -> None:
        candidate = copy.deepcopy(self.journey)
        menu = candidate["subjects"]["G7"]["apk_owned_visual_anchors"][0]
        menu["required_text"].append("Exit")
        self.assert_failure_contains(
            candidate, "screenshot_1 excludes Exit"
        )

    def test_three_by_three_reference_cannot_prove_two_by_two(self) -> None:
        candidate = copy.deepcopy(self.journey)
        board = candidate["subjects"]["G7"]["apk_owned_visual_anchors"][1]
        board["source_reference"]["known_grid_size"] = "2x2"
        board["source_reference"]["may_prove_runtime_2x2"] = True
        self.assert_failure_contains(
            candidate, "3x3 layout-only non-evidence"
        )

    def test_case_without_applies_to_fails_closed(self) -> None:
        candidate = copy.deepcopy(self.journey)
        del candidate["cases"]["negative"][0]["applies_to"]
        self.assert_failure_contains(candidate, "applies_to")

    def test_case_cannot_drop_required_measurement(self) -> None:
        candidate = copy.deepcopy(self.journey)
        play = next(
            case
            for case in candidate["cases"]["positive"]
            if case["id"] == "P-G7-PLAY"
        )
        play["measurement_methods"].remove("INPUT_CAUSALITY")
        self.assert_failure_contains(
            candidate, "P-G7-PLAY: measurement methods drifted"
        )

    def test_journey_identity_must_match_ladder(self) -> None:
        candidate = copy.deepcopy(self.journey)
        candidate["identity_contract"]["immutable_inputs"]["G7"][
            "apk_sha256"
        ] = "0" * 64
        self.assert_failure_contains(candidate, "G7: APK SHA-256 drifted")

    def test_pause_and_rebuild_do_not_gain_timer_guess(self) -> None:
        candidate = copy.deepcopy(self.journey)
        candidate["subjects"]["G7"]["pause_timer_oracle"] = "nondecreasing"
        self.assert_failure_contains(
            candidate, "without timer speculation"
        )


if __name__ == "__main__":
    unittest.main()
