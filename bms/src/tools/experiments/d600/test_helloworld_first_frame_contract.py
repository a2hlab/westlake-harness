#!/usr/bin/env python3
"""Host-only fail-closed tests for the HelloWorld first-frame contracts."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import helloworld_first_frame_contract as contract


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def valid_change_set() -> dict[str, object]:
    return {
        "change_set_id": "p0-loader-001",
        "hypothesis": "The selected target provider is absent from the namespace.",
        "atomic_reason": "The provider, bridge and manifest must be deployed together.",
        "members": [
            {
                "path": "src/adapter/framework/core/jni/skia_codec_register.cpp",
                "component": "skia-loader",
                "before_sha256": "1" * 64,
                "after_sha256": "2" * 64,
                "mechanism": "bind the selected target provider",
                "expected_effect": "resolve the first missing Skia symbol",
            }
        ],
        "earliest_transition": "NativeLoader initialized -> bridge loaded",
        "expected_observation": "The child advances beyond the current loader first-bad.",
        "falsifier": "The same unresolved symbol remains with exact cohort readback.",
        "unchanged_invariants": ["ART tuple", "appspawn parent generation"],
        "pnf_cases": {
            "positive": "exact cohort advances",
            "negative": "wrong provider is rejected",
            "failure": "partial cohort is rejected",
        },
        "reused_receipts": [
            {"path": "var/evidence/old.json", "sha256": "3" * 64, "reuse_reason": "same inputs"}
        ],
        "rollback": {
            "restore_all_members": True,
            "procedure_ref": "rollback/restore-set.json",
            "post_rollback_oracle": "all member hashes equal before_sha256",
        },
        "status": "DRAFT",
    }


def valid_candidate() -> dict[str, object]:
    return {
        "candidate_id": "candidate-001",
        "run_id": "p0-run-001",
        "apk": {
            "sha256": contract.HELLOWORLD_APK_SHA256,
            "package_name": contract.HELLOWORLD_PACKAGE,
            "activity_name": contract.HELLOWORLD_ACTIVITY,
            "unmodified": True,
        },
        "device": {
            "serial": "dynamic-lease-serial",
            "boot_id": "3b219a52-cc25-4afb-8854-0a96bf091b68",
            "oh_version": "OpenHarmony-6.1.0.31",
            "selinux": "Enforcing",
            "lease_ref": "lease.json@" + "4" * 64,
        },
        "generation": {
            "generation_id": "5" * 64,
            "device_readback_receipt": "device-generation.json@" + "6" * 64,
            "identity_valid": True,
        },
        "change_set_ref": "change-set.json@" + "7" * 64,
        "launch": {
            "cold_precondition": True,
            "started_at_utc": "2026-08-04T12:00:00Z",
            "started_at_monotonic": 100.0,
            "request_id": "request-001",
        },
        "process": {
            "pid": 4321,
            "start_ticks": 9988,
            "parent_pid": 1200,
            "package_bound": True,
            "alive_at_hold_end": True,
        },
        "observations": {
            "on_resume": True,
            "app_window_visible": True,
            "present_observed": True,
            "hello_world_visible": True,
            "first_frame_seconds": 3.2,
            "hold_seconds": 5.1,
            "screens": [
                {
                    "role": "FIRST_FRAME",
                    "path": "candidate/first-frame.png",
                    "sha256": "8" * 64,
                    "captured_at_utc": "2026-08-04T12:00:03Z",
                },
                {
                    "role": "HOLD_END",
                    "path": "candidate/hold-end.png",
                    "sha256": "9" * 64,
                    "captured_at_utc": "2026-08-04T12:00:09Z",
                },
            ],
        },
        "pnf": {"positive": "PASS", "negative": "PASS", "failure": "PASS"},
        "first_bad": "NONE",
        "terminal_state": "DEVELOPER_OBSERVED_FIRST_FRAME",
        "evidence_manifest_sha256": "a" * 64,
    }


class HelloWorldContractTest(unittest.TestCase):
    def test_project_frozen_apk_receipt_binds_the_checked_in_artifact(self) -> None:
        receipt = (
            contract.PROJECT_ROOT
            / "specs/005-helloworld-first-frame/inputs/frozen-apk.json"
        )
        frozen = contract.load_frozen_apk(receipt)
        self.assertEqual(frozen["sha256"], contract.HELLOWORLD_APK_SHA256)
        self.assertEqual(frozen["schema_version"], "bridge.p0.frozen-apk.v1")

    def test_frozen_apk_binds_path_size_and_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            apk = root / "HelloWorld.apk"
            apk.write_bytes(b"exact-apk-bytes")
            actual = digest_bytes(apk.read_bytes())
            receipt_path = root / "frozen-apk.json"
            receipt_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "resolved_path": "HelloWorld.apk",
                        "size_bytes": apk.stat().st_size,
                        "sha256": actual,
                        "package_name": contract.HELLOWORLD_PACKAGE,
                        "activity_name": contract.HELLOWORLD_ACTIVITY,
                        "unmodified": True,
                    }
                ),
                encoding="utf-8",
            )
            frozen = contract.load_frozen_apk(
                receipt_path, project_root=root, expected_sha256=actual
            )
            self.assertEqual(frozen["sha256"], actual)
            self.assertEqual(Path(frozen["resolved_path"]), apk)

            apk.write_bytes(b"changed")
            with self.assertRaisesRegex(contract.ContractError, "size_bytes|sha256"):
                contract.load_frozen_apk(
                    receipt_path, project_root=root, expected_sha256=actual
                )

    def test_digest_references_are_scoped_and_verified(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            receipt = root / "receipt.json"
            receipt.write_text("{}\n", encoding="utf-8")
            reference = contract.make_digest_ref(receipt, project_root=root)
            self.assertEqual(reference["path"], "receipt.json")
            self.assertEqual(
                contract.load_digest_ref(reference, project_root=root), receipt
            )
            bad = dict(reference)
            bad["sha256"] = "f" * 64
            with self.assertRaisesRegex(contract.ContractError, "digest mismatch"):
                contract.load_digest_ref(bad, project_root=root)
            with self.assertRaisesRegex(contract.ContractError, "inside project root"):
                contract.resolve_project_path("../outside", project_root=root)

    def test_change_set_accepts_atomic_complete_document(self) -> None:
        self.assertEqual(
            contract.validate_change_set(valid_change_set())["change_set_id"],
            "p0-loader-001",
        )

    def test_change_set_rejects_partial_duplicate_or_noop_cohort(self) -> None:
        for mutation, message in (
            (lambda value: value.pop("rollback"), "missing fields"),
            (
                lambda value: value["members"].append(copy.deepcopy(value["members"][0])),
                "duplicate member path",
            ),
            (
                lambda value: value["members"][0].update(
                    after_sha256=value["members"][0]["before_sha256"]
                ),
                "must change identity",
            ),
            (
                lambda value: value["rollback"].update(restore_all_members=False),
                "restore_all_members",
            ),
        ):
            with self.subTest(message=message):
                document = valid_change_set()
                mutation(document)
                with self.assertRaisesRegex(contract.ContractError, message):
                    contract.validate_change_set(document)

    def test_candidate_success_requires_complete_same_run_oracle(self) -> None:
        self.assertEqual(
            contract.validate_candidate(valid_candidate())["terminal_state"],
            "DEVELOPER_OBSERVED_FIRST_FRAME",
        )
        mutations = (
            lambda value: value["apk"].update(sha256="f" * 64),
            lambda value: value["generation"].update(identity_valid=False),
            lambda value: value["process"].update(start_ticks=None),
            lambda value: value["observations"].update(first_frame_seconds=15.01),
            lambda value: value["observations"].update(hold_seconds=4.99),
            lambda value: value["observations"]["screens"].pop(),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                candidate = valid_candidate()
                mutation(candidate)
                with self.assertRaises(contract.ContractError):
                    contract.validate_candidate(candidate)

    def test_failure_candidate_may_have_no_process_but_remains_typed(self) -> None:
        candidate = valid_candidate()
        candidate["process"] = {
            "pid": None,
            "start_ticks": None,
            "parent_pid": None,
            "package_bound": False,
            "alive_at_hold_end": False,
        }
        candidate["observations"].update(
            on_resume=False,
            app_window_visible=False,
            present_observed=False,
            hello_world_visible=False,
            first_frame_seconds=None,
            hold_seconds=0,
            screens=[],
        )
        candidate["pnf"] = {"positive": "FAIL", "negative": "PASS", "failure": "NOT_RUN"}
        candidate["first_bad"] = "PROCESS_NOT_OBSERVED"
        candidate["terminal_state"] = "FAIL_NO_PROCESS"
        self.assertEqual(
            contract.validate_candidate(candidate)["terminal_state"], "FAIL_NO_PROCESS"
        )

    def test_receipt_reuse_fails_closed_for_every_identity_axis(self) -> None:
        cached = {
            "apk_sha256": "1" * 64,
            "source_manifest_sha256": "2" * 64,
            "builder_identity_sha256": "3" * 64,
            "toolchain_sha256": "4" * 64,
            "generation_id": "5" * 64,
            "serial": "lease-serial",
            "boot_id": "3b219a52-cc25-4afb-8854-0a96bf091b68",
            "device_readback_sha256": "6" * 64,
            "log_timeline_sha256": "7" * 64,
            "screenshot_timeline_sha256": "8" * 64,
        }
        self.assertEqual(
            contract.receipt_reuse_errors("candidate", cached, dict(cached)), []
        )
        for field in cached:
            with self.subTest(field=field):
                current = dict(cached)
                current[field] = "changed"
                errors = contract.receipt_reuse_errors("candidate", cached, current)
                self.assertTrue(any(field in error for error in errors), errors)
        current = dict(cached)
        current.pop("boot_id")
        self.assertTrue(
            contract.receipt_reuse_errors("candidate", cached, current),
            "missing current binding was accepted",
        )

    def test_receipt_kinds_do_not_require_unrelated_later_layer_bindings(self) -> None:
        apk = {"apk_sha256": "1" * 64}
        self.assertEqual(contract.receipt_reuse_errors("apk", apk, dict(apk)), [])
        build = {
            "apk_sha256": "1" * 64,
            "source_manifest_sha256": "2" * 64,
            "builder_identity_sha256": "3" * 64,
            "toolchain_sha256": "4" * 64,
            "generation_id": "5" * 64,
        }
        self.assertEqual(contract.receipt_reuse_errors("build", build, dict(build)), [])

    def test_developer_verdict_cannot_issue_independent_pass(self) -> None:
        candidate = valid_candidate()
        verdict = {
            "candidate_ref": "candidate.json@" + "b" * 64,
            "evidence_manifest_sha256": candidate["evidence_manifest_sha256"],
            "verdict": "DEVELOPER_OBSERVED_FIRST_FRAME",
            "first_bad": "NONE",
            "issued_by": "implementation-agent",
            "claim_boundary": "DEVELOPER_DEVICE_OBSERVATION_ONLY",
            "formal_journey_verdict": "NOT_ISSUED",
        }
        self.assertEqual(
            contract.validate_developer_verdict(verdict, candidate)["verdict"],
            "DEVELOPER_OBSERVED_FIRST_FRAME",
        )
        for field, value in (
            ("claim_boundary", "JOURNEY_PASS"),
            ("formal_journey_verdict", "PASS"),
            ("verdict", "PASS"),
            ("evidence_manifest_sha256", "c" * 64),
        ):
            with self.subTest(field=field):
                bad = dict(verdict)
                bad[field] = value
                with self.assertRaises(contract.ContractError):
                    contract.validate_developer_verdict(bad, candidate)


if __name__ == "__main__":
    unittest.main(verbosity=2)
