#!/usr/bin/env python3
"""Host P/N/F tests for the F21 SELinux one-permission validator."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from e01_validate_f21_selinux_policy_delta import ValidationError, validate


BASE = """\
(handleunknown deny)
(typeattribute empty_attr)
(typeattributeset populated_attr (appspawn))
(allow appspawn system_file (file (read getattr map open)))
(allow appspawn system_file (dir (getattr mounton)))
"""
ROUNDTRIP = """\
(handleunknown deny)
(typeattribute empty_attr)
(typeattributeset populated_attr (appspawn))
(allow appspawn system_file (file (read getattr map open)))
(allow appspawn system_file (dir (getattr mounton)))
"""
CANDIDATE = """\
(handleunknown deny)
(typeattribute empty_attr)
(typeattributeset populated_attr (appspawn))
(allow appspawn system_file (file (read getattr lock map open)))
(allow appspawn system_file (dir (getattr mounton)))
"""
OVERLAY = "(allow appspawn system_file (file (lock)))\n"


class PolicyDeltaTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def write(self, name: str, content: str) -> Path:
        path = self.root / name
        path.write_text(content, encoding="utf-8")
        return path

    def run_validation(
        self,
        base: str = BASE,
        roundtrip: str = ROUNDTRIP,
        candidate: str = CANDIDATE,
        overlay: str = OVERLAY,
    ) -> dict[str, object]:
        return validate(
            self.write("base.cil", base),
            self.write("roundtrip.cil", roundtrip),
            self.write("candidate.cil", candidate),
            self.write("overlay.cil", overlay),
            "appspawn",
            "system_file",
            "file",
            "lock",
        )

    def test_positive_exact_one_permission(self) -> None:
        receipt = self.run_validation()
        self.assertTrue(receipt["baseline_roundtrip_semantically_equal"])
        self.assertTrue(receipt["baseline_roundtrip_full_structure_equal"])
        self.assertEqual(receipt["formal_verdict"], "NONE")
        self.assertEqual(receipt["only_delta"]["added_permission"], "lock")
        self.assertFalse(receipt["action_verdict"])

    def test_negative_rejects_removed_roundtrip_attribute(self) -> None:
        drifted = ROUNDTRIP.replace("(typeattribute empty_attr)\n", "")
        with self.assertRaisesRegex(ValidationError, "full policy structure"):
            self.run_validation(roundtrip=drifted)

    def test_negative_rejects_changed_candidate_attribute(self) -> None:
        drifted = CANDIDATE.replace(
            "(typeattributeset populated_attr (appspawn))",
            "(typeattributeset populated_attr (appspawn shell))",
        )
        with self.assertRaisesRegex(ValidationError, "full policy structure"):
            self.run_validation(candidate=drifted)

    def test_negative_rejects_baseline_semantic_drift(self) -> None:
        drifted = ROUNDTRIP.replace("(getattr mounton)", "(getattr mounton search)")
        with self.assertRaisesRegex(ValidationError, "baseline is not semantically"):
            self.run_validation(roundtrip=drifted)

    def test_negative_rejects_extra_candidate_permission(self) -> None:
        drifted = CANDIDATE.replace(
            "(read getattr lock map open)", "(read getattr lock map open write)"
        )
        with self.assertRaisesRegex(ValidationError, "not exactly"):
            self.run_validation(candidate=drifted)

    def test_negative_rejects_removed_candidate_permission(self) -> None:
        drifted = CANDIDATE.replace(
            "(read getattr lock map open)", "(read getattr lock map)"
        )
        with self.assertRaisesRegex(ValidationError, "not exactly"):
            self.run_validation(candidate=drifted)

    def test_negative_rejects_added_allow_key(self) -> None:
        drifted = CANDIDATE + "(allow appspawn system_file (lnk_file (read)))\n"
        with self.assertRaisesRegex(ValidationError, "set of allow rule keys"):
            self.run_validation(candidate=drifted)

    def test_negative_rejects_removed_allow_key(self) -> None:
        drifted = CANDIDATE.replace(
            "(allow appspawn system_file (dir (getattr mounton)))\n", ""
        )
        with self.assertRaisesRegex(ValidationError, "set of allow rule keys"):
            self.run_validation(candidate=drifted)

    def test_negative_rejects_non_allow_policy_change(self) -> None:
        drifted = CANDIDATE.replace("(handleunknown deny)", "(handleunknown allow)")
        with self.assertRaisesRegex(ValidationError, "non-allow policy semantics"):
            self.run_validation(candidate=drifted)

    def test_failure_rejects_overlay_drift(self) -> None:
        with self.assertRaisesRegex(ValidationError, "exactly"):
            self.run_validation(
                overlay="(allow appspawn system_file (file (lock write)))\n"
            )

    def test_full_structure_gate_rejects_removed_attribute(self) -> None:
        missing_attribute = ROUNDTRIP.replace("(typeattribute empty_attr)\n", "")
        with self.assertRaisesRegex(ValidationError, "full policy structure"):
            validate(
                self.write("base.cil", BASE),
                self.write("roundtrip.cil", missing_attribute),
                self.write("candidate.cil", CANDIDATE),
                self.write("overlay.cil", OVERLAY),
                "appspawn",
                "system_file",
                "file",
                "lock",
            )

    def test_full_structure_gate_accepts_preserved_attributes(self) -> None:
        candidate = BASE.replace(
            "(read getattr map open)", "(read getattr lock map open)"
        )
        receipt = validate(
            self.write("base.cil", BASE),
            self.write("roundtrip.cil", BASE),
            self.write("candidate.cil", candidate),
            self.write("overlay.cil", OVERLAY),
            "appspawn",
            "system_file",
            "file",
            "lock",
        )
        self.assertTrue(receipt["baseline_roundtrip_full_structure_equal"])


if __name__ == "__main__":
    unittest.main()
