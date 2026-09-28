#!/usr/bin/env python3
"""Host tests for Action identity compatibility in audit_action_progress."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_action_progress import action_id_from_atom, preserve_existing_projection


class ActionIdFromAtomTest(unittest.TestCase):
    def setUp(self) -> None:
        self.path = Path("/repo/spec/atoms/Fn03/A07/atom.yaml")

    def test_accepts_atom_id(self) -> None:
        self.assertEqual(
            action_id_from_atom({"atom_id": "Fn03.A07"}, self.path),
            "Fn03.A07",
        )

    def test_accepts_action_id(self) -> None:
        self.assertEqual(
            action_id_from_atom({"action_id": "Fn03.A07"}, self.path),
            "Fn03.A07",
        )

    def test_rejects_missing_identity(self) -> None:
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            action_id_from_atom({}, self.path)

    def test_rejects_directory_mismatch(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected Fn03.A07"):
            action_id_from_atom({"action_id": "Fn04.A07"}, self.path)


class PreserveExistingProjectionTest(unittest.TestCase):
    def test_preserves_reviewed_projection(self) -> None:
        existing = {"stage": "INDEPENDENTLY_VERIFIED", "evidence_refs": ["run"]}
        derived = {"stage": "NOT_STARTED", "evidence_refs": []}
        self.assertIs(preserve_existing_projection(existing, derived), existing)

    def test_derives_only_when_projection_is_missing(self) -> None:
        derived = {"stage": "NOT_STARTED"}
        self.assertIs(preserve_existing_projection(None, derived), derived)


if __name__ == "__main__":
    unittest.main()
