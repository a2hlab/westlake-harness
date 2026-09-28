#!/usr/bin/env python3
"""Positive and single-variable negative controls for the M05 validator."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
VALIDATOR_PATH = REPO_ROOT / "adapter/scripts/ci/bionic_musl_validate_baseline.py"
CURRENT_PATH = (
    REPO_ROOT / "adapter/verification/bionic-musl/baselines/current.json"
)
SELF_TEST_PATH = (
    REPO_ROOT
    / "adapter/verification/bionic-musl/tests/fixtures/valid-self-test.json"
)

SPEC = importlib.util.spec_from_file_location("bionic_musl_validator", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator: {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


class BaselineValidatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.current = load(CURRENT_PATH)
        self.valid = load(SELF_TEST_PATH)

    def validate(
        self,
        document: dict,
        require_admission: bool = False,
        require_offline_ready: bool = False,
        require_runtime_ready: bool = False,
    ):
        validator = VALIDATOR.BaselineValidator(document)
        result = validator.validate(
            require_admission=require_admission,
            require_offline_ready=require_offline_ready,
            require_runtime_ready=require_runtime_ready,
        )
        return result, validator.errors

    def assert_invalid(self, document: dict, expected: str) -> None:
        result, errors = self.validate(document)
        self.assertFalse(result, errors)
        self.assertTrue(
            any(expected in error for error in errors),
            f"expected {expected!r} in {errors!r}",
        )

    def test_schema_file_and_current_missing_input_report_are_valid(self) -> None:
        VALIDATOR.validate_schema_file()
        result, errors = self.validate(self.current)
        self.assertTrue(result, errors)
        self.assertFalse(self.current["verdict"]["device_admission"])

    def test_complete_synthetic_positive_is_valid_but_non_promotable(self) -> None:
        result, errors = self.validate(self.valid)
        self.assertTrue(result, errors)
        self.assertEqual("verifier_self_test", self.valid["assessment_kind"])
        self.assertFalse(self.valid["verdict"]["device_admission"])

    def test_exactly_22_redteam_gates_are_required(self) -> None:
        mutant = copy.deepcopy(self.valid)
        mutant["runtime_generation_redteam"]["gates"].pop()
        self.assert_invalid(mutant, "must contain exactly 22 gates")

    def test_duplicate_redteam_gate_id_is_rejected(self) -> None:
        mutant = copy.deepcopy(self.valid)
        mutant["runtime_generation_redteam"]["gates"][1]["gate_id"] = "SYNTH-RG-01"
        self.assert_invalid(mutant, "gate IDs must be unique")

    def test_old_generation_gate_is_rejected(self) -> None:
        mutant = copy.deepcopy(self.valid)
        mutant["runtime_generation_redteam"]["gates"][7][
            "generation_token"
        ] = "stale-generation"
        self.assert_invalid(mutant, "does not match the exact current candidate")

    def test_current_byte_hash_mismatch_is_rejected(self) -> None:
        mutant = copy.deepcopy(self.valid)
        mutant["candidate"]["identities"][0]["sha256"] = "0" * 64
        self.assert_invalid(mutant, "SHA256 mismatch")

    def test_sibling_project_escape_is_rejected(self) -> None:
        mutant = copy.deepcopy(self.valid)
        mutant["candidate"]["identities"][0]["path"] = "../../02d/hp9/source.c"
        self.assert_invalid(mutant, "normalized repository-relative path")

    def test_self_test_cannot_set_device_admission(self) -> None:
        mutant = copy.deepcopy(self.valid)
        mutant["verdict"]["assessment"] = "admit"
        mutant["verdict"]["device_admission"] = True
        self.assert_invalid(mutant, "self-tests can never admit product bytes")

    def test_native_generation_receipt_does_not_substitute_runtime_ready(self) -> None:
        mutant = copy.deepcopy(self.valid)
        mutant["candidate"]["runtime_readiness"] = {
            "availability": "missing",
            "verification_status": "not_run",
            "missing_evidence": ["No child-ready binding."],
            "failure": "",
        }
        self.assert_invalid(
            mutant,
            "runtime gate cannot run before ChildRuntimeReadyReceiptV1 binding",
        )

    def test_offline_only_report_can_be_valid_but_remains_denied(self) -> None:
        offline_only = copy.deepcopy(self.valid)
        offline_only["candidate"]["runtime_readiness"] = {
            "availability": "missing",
            "verification_status": "not_run",
            "missing_evidence": ["No child-ready binding."],
            "failure": "",
        }
        for gate_name in [
            "six_entry_guard_tls",
            "namespace_lifecycle",
            "fault_classification",
            "bounded_soak",
        ]:
            offline_only["reliability_matrix"][gate_name] = {
                "status": "not_run",
                "evidence": [],
                "metrics": {},
                "failure": "",
            }
        result, errors = self.validate(offline_only)
        self.assertTrue(result, errors)
        self.assertFalse(offline_only["verdict"]["device_admission"])

    def test_child_ready_generation_must_bind_offline_generation(self) -> None:
        mutant = copy.deepcopy(self.valid)
        mutant["candidate"]["runtime_readiness"]["binding"][
            "generation_token"
        ] = "different-offline-generation"
        self.assert_invalid(mutant, "must bind the offline generation")

    def test_child_and_spawn_receipt_schema_names_are_not_interchangeable(self) -> None:
        mutant = copy.deepcopy(self.valid)
        mutant["candidate"]["runtime_readiness"][
            "child_receipt_schema"
        ] = "NativeGenerationReceiptV1"
        self.assert_invalid(mutant, "must be ChildRuntimeReadyReceiptV1")

    def test_require_admission_fails_the_checked_in_current_report(self) -> None:
        result, errors = self.validate(self.current, require_admission=True)
        self.assertFalse(result)
        self.assertTrue(
            any("required admission was not achieved" in error for error in errors),
            errors,
        )

    def test_current_report_fails_the_explicit_offline_ready_gate(self) -> None:
        result, errors = self.validate(self.current, require_offline_ready=True)
        self.assertFalse(result)
        self.assertTrue(
            any("offline generation gate was not achieved" in error for error in errors),
            errors,
        )

    def test_self_test_cannot_satisfy_runtime_ready_gate(self) -> None:
        result, errors = self.validate(self.valid, require_runtime_ready=True)
        self.assertFalse(result)
        self.assertTrue(
            any(
                "ChildRuntimeReadyReceiptV1/SpawnBirthReceiptV1 binding was not achieved"
                in error
                for error in errors
            ),
            errors,
        )


if __name__ == "__main__":
    unittest.main()
