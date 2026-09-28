#!/usr/bin/env python3
"""Host-only contract tests for current boot generation coverage."""

from __future__ import annotations

import unittest
import hashlib
import json
import tempfile
from pathlib import Path

from tools.experiments.d600.fn01_provenance.build_current_boot_generation import (
    Builder,
    validate_coverage_manifest,
)


def valid_manifest() -> dict:
    actions = ["Fn01.A04"]
    return {
        "covered_actions": actions,
        "coverage_proofs": {
            action: {
                "source_evidence": ["source-manifest:4e2677"],
                "producer_evidence": ["host-suite:6c6c3e"],
            }
            for action in actions
        },
        "semantics": {
            "authorizes_artifact_oracle_only": True,
            "does_not_imply_behavior_pass": True,
        },
    }


class CoverageManifestTest(unittest.TestCase):
    def test_explicit_a04_only_coverage_is_accepted(self) -> None:
        self.assertEqual(
            validate_coverage_manifest(valid_manifest()),
            ("Fn01.A04",),
        )

    def test_silent_cross_action_addition_is_rejected(self) -> None:
        manifest = valid_manifest()
        manifest["covered_actions"].append("Fn01.A05")
        manifest["coverage_proofs"]["Fn01.A05"] = {
            "source_evidence": ["invented"],
            "producer_evidence": ["invented"],
        }
        with self.assertRaisesRegex(ValueError, "unsupported action"):
            validate_coverage_manifest(manifest)

    def test_action_without_producer_evidence_is_rejected(self) -> None:
        manifest = valid_manifest()
        manifest["coverage_proofs"]["Fn01.A04"]["producer_evidence"] = []
        with self.assertRaisesRegex(ValueError, "producer_evidence"):
            validate_coverage_manifest(manifest)

    def test_coverage_cannot_imply_behavior_pass(self) -> None:
        manifest = valid_manifest()
        manifest["semantics"]["does_not_imply_behavior_pass"] = False
        with self.assertRaisesRegex(ValueError, "deny implicit behavior PASS"):
            validate_coverage_manifest(manifest)

    def test_worker_writes_standard_producer_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work = root / "work"
            for name in ("frozen", "logs", "products"):
                (work / name).mkdir(parents=True)
            output = work / "products" / "boot.art"
            output.write_bytes(b"fixture-boot\n")
            builder = Builder(
                root / "aosp",
                work,
                "fn01-final-fixture-20260728-r1",
            )
            builder.receipt["covered_actions"] = ["Fn01.A04"]
            builder.receipt["qualification_only"] = False
            builder.receipt["eligible_for_deploy"] = False
            builder.receipt["outputs"] = [
                {
                    "role": "boot:boot.art",
                    "path": "products/boot.art",
                    "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                    "bytes": output.stat().st_size,
                }
            ]
            builder.receipt["status"]["build_pass"] = True
            builder.write_receipt()
            receipt = json.loads(
                (work / "producer-receipt.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                receipt["frozen_build_id"],
                "fn01-final-fixture-20260728-r1",
            )
            self.assertEqual(receipt["producer_kind"], "boot")
            self.assertTrue(receipt["status"]["producer_pass"])
            self.assertEqual(receipt["outputs"][0]["role"], "boot:boot.art")

    def test_final_coverage_schema_is_accepted_without_inference(self) -> None:
        manifest = {
            "schema_version": "bridge.fn01.final-coverage.v1",
            "covered_actions": ["Fn01.A02", "Fn01.A03"],
            "coverage_proofs": {
                action: {
                    "source_evidence": [f"source:{action}"],
                    "producer_receipt_ids": ["native-r1"],
                    "target_probe_receipt_ids": [f"probe-{action}"],
                }
                for action in ("Fn01.A02", "Fn01.A03")
            },
            "semantics": {
                "authorizes_artifact_oracle_only": True,
                "does_not_imply_behavior_pass": True,
            },
        }
        self.assertEqual(
            validate_coverage_manifest(manifest),
            ("Fn01.A02", "Fn01.A03"),
        )


if __name__ == "__main__":
    unittest.main()
