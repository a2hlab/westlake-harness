#!/usr/bin/env python3
"""Contract tests for the Fn01 final generation controller."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.experiments.d600.fn01_provenance.final_generation_controller import (
    BOOT_ROLES,
    ContractError,
    Controller,
    DIRECT_ROLES,
    pack,
)
from tools.experiments.d600.fn01_provenance.run_final_generation_pipeline import (
    BOOT_RECEIPT_MARKER,
    resolve_spec_template,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def make_fixture(root: Path) -> Path:
    frozen_id = "fn01-final-fixture-20260728-r1"
    receipts = root / "receipts"
    outputs = root / "outputs"
    outputs.mkdir(parents=True)

    native_outputs = []
    for role in sorted(DIRECT_ROLES):
        path = outputs / role
        path.write_bytes(f"fixture:{role}\n".encode())
        native_outputs.append(
            {"role": role, "path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size}
        )
    boot_outputs = []
    for role in sorted(BOOT_ROLES):
        path = outputs / role.replace(":", "__")
        path.write_bytes(f"fixture:{role}\n".encode())
        boot_outputs.append(
            {"role": role, "path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size}
        )

    receipt_values = {
        "native-r1": {
            "schema_version": "bridge.fn01.producer-receipt.v1",
            "receipt_id": "native-r1",
            "frozen_build_id": frozen_id,
            "producer_kind": "native_and_java",
            "generation_id": "Fn01.native-fresh-r1",
            "qualification_only": False,
            "status": {"producer_pass": True},
            "outputs": native_outputs,
        },
        "boot-r1": {
            "schema_version": "bridge.fn01.producer-receipt.v1",
            "receipt_id": "boot-r1",
            "frozen_build_id": frozen_id,
            "producer_kind": "boot",
            "generation_id": "Fn01.boot-fresh-r1",
            "qualification_only": False,
            "status": {"producer_pass": True},
            "outputs": boot_outputs,
        },
    }
    for action in ("Fn01.A01", "Fn01.A02", "Fn01.A03", "Fn01.A04"):
        receipt_id = f"probe-{action}"
        receipt_values[receipt_id] = {
            "schema_version": "bridge.fn01.producer-receipt.v1",
            "receipt_id": receipt_id,
            "frozen_build_id": frozen_id,
            "producer_kind": "target_probe",
            "generation_id": f"Fn01.probe-{action}",
            "qualification_only": False,
            "status": {"producer_pass": True},
            "outputs": [],
        }
    receipt_refs = []
    for receipt_id, value in receipt_values.items():
        path = receipts / f"{receipt_id}.json"
        write_json(path, value)
        receipt_refs.append({"path": str(path), "sha256": sha256(path)})

    actions = ["Fn01.A01", "Fn01.A02", "Fn01.A03", "Fn01.A04"]
    coverage = {
        "schema_version": "bridge.fn01.final-coverage.v1",
        "frozen_build_id": frozen_id,
        "covered_actions": actions,
        "coverage_proofs": {
            action: {
                "source_evidence": [f"fixture-source:{action}"],
                "producer_receipt_ids": ["native-r1", "boot-r1"],
                "target_probe_receipt_ids": [f"probe-{action}"],
            }
            for action in actions
        },
        "semantics": {
            "authorizes_artifact_oracle_only": True,
            "does_not_imply_behavior_pass": True,
        },
    }
    coverage_path = root / "coverage.json"
    write_json(coverage_path, coverage)
    artifacts = [
        {"role": role, "producer_receipt_id": "native-r1", "output_role": role}
        for role in sorted(DIRECT_ROLES)
    ]
    artifacts.extend(
        {"role": role, "producer_receipt_id": "boot-r1", "output_role": role}
        for role in sorted(BOOT_ROLES)
    )
    spec = {
        "schema_version": "bridge.fn01.final-generation-spec.v1",
        "frozen_build_id": frozen_id,
        "default_eligible": False,
        "covered_actions": actions,
        "coverage_manifest": {"path": str(coverage_path), "sha256": sha256(coverage_path)},
        "producer_receipts": receipt_refs,
        "artifacts": artifacts,
        "forbidden_generation_ids": ["Fn01.boot-0bdfcec3166c2e61a46f"],
    }
    spec_path = root / "spec.json"
    write_json(spec_path, spec)
    return spec_path


class FinalControllerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.spec_path = make_fixture(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def rewrite_spec(self, mutate) -> None:
        spec = json.loads(self.spec_path.read_text())
        mutate(spec)
        write_json(self.spec_path, spec)

    def rewrite_json_and_rebind(self, path: Path, mutate) -> None:
        value = json.loads(path.read_text())
        mutate(value)
        write_json(path, value)
        spec = json.loads(self.spec_path.read_text())
        for ref in spec["producer_receipts"]:
            if Path(ref["path"]) == path:
                ref["sha256"] = sha256(path)
        if Path(spec["coverage_manifest"]["path"]) == path:
            spec["coverage_manifest"]["sha256"] = sha256(path)
        write_json(self.spec_path, spec)

    def test_default_is_valid_but_not_eligible(self) -> None:
        result = Controller(self.spec_path, request_eligible=False).validate()
        self.assertTrue(result.report["status"]["validation_pass"])
        self.assertFalse(result.eligible)

    def test_explicit_eligible_requires_and_accepts_all_receipts(self) -> None:
        result = Controller(self.spec_path, request_eligible=True).validate()
        self.assertTrue(result.eligible)

    def test_failed_producer_receipt_rejects_eligible(self) -> None:
        path = self.root / "receipts" / "native-r1.json"
        self.rewrite_json_and_rebind(
            path, lambda value: value["status"].update(producer_pass=False)
        )
        with self.assertRaisesRegex(ContractError, "producer_pass"):
            Controller(self.spec_path, request_eligible=True).validate()

    def test_qualification_receipt_is_rejected(self) -> None:
        path = self.root / "receipts" / "boot-r1.json"
        self.rewrite_json_and_rebind(
            path, lambda value: value.update(qualification_only=True)
        )
        with self.assertRaisesRegex(ContractError, "qualification-only"):
            Controller(self.spec_path, request_eligible=False).validate()

    def test_forbidden_r6_generation_is_rejected(self) -> None:
        path = self.root / "receipts" / "boot-r1.json"
        self.rewrite_json_and_rebind(
            path,
            lambda value: value.update(
                generation_id="Fn01.boot-0bdfcec3166c2e61a46f"
            ),
        )
        with self.assertRaisesRegex(ContractError, "forbidden generation"):
            Controller(self.spec_path, request_eligible=False).validate()

    def test_frozen_build_id_mismatch_is_rejected(self) -> None:
        path = self.root / "receipts" / "boot-r1.json"
        self.rewrite_json_and_rebind(
            path, lambda value: value.update(frozen_build_id="another-build")
        )
        with self.assertRaisesRegex(ContractError, "frozen_build_id mismatch"):
            Controller(self.spec_path, request_eligible=False).validate()

    def test_caller_cannot_rewrite_output_bytes(self) -> None:
        path = self.root / "receipts" / "native-r1.json"
        receipt = json.loads(path.read_text())
        artifact = Path(receipt["outputs"][0]["path"])
        artifact.write_bytes(b"tampered\n")
        with self.assertRaisesRegex(ContractError, "output (sha256|bytes) mismatch"):
            Controller(self.spec_path, request_eligible=False).validate()

    def test_artifact_exact_set_rejects_missing_boot_segment(self) -> None:
        self.rewrite_spec(lambda value: value["artifacts"].pop())
        with self.assertRaisesRegex(ContractError, "artifact exact-set mismatch"):
            Controller(self.spec_path, request_eligible=False).validate()

    def test_coverage_proofs_must_exact_set_actions(self) -> None:
        path = self.root / "coverage.json"
        self.rewrite_json_and_rebind(
            path, lambda value: value["coverage_proofs"].pop("Fn01.A03")
        )
        with self.assertRaisesRegex(ContractError, "exact-set"):
            Controller(self.spec_path, request_eligible=False).validate()

    def test_eligible_requires_target_probe_for_every_action(self) -> None:
        path = self.root / "coverage.json"
        self.rewrite_json_and_rebind(
            path,
            lambda value: value["coverage_proofs"]["Fn01.A02"].update(
                target_probe_receipt_ids=[]
            ),
        )
        self.assertFalse(Controller(self.spec_path, request_eligible=False).validate().eligible)
        with self.assertRaisesRegex(ContractError, "no passing target probe"):
            Controller(self.spec_path, request_eligible=True).validate()

    def test_pack_seals_thirty_artifacts_and_identity(self) -> None:
        result = Controller(self.spec_path, request_eligible=True).validate()
        out = self.root / "packed"
        identity = pack(result, out)
        self.assertTrue(identity["status"]["eligible_for_deploy"])
        self.assertEqual(len(list((out / "artifacts").iterdir())), 30)
        self.assertTrue((out / "generation-identity.sha256").is_file())

    def test_pipeline_template_binds_fresh_boot_receipt(self) -> None:
        boot_receipt = self.root / "receipts" / "boot-r1.json"
        template = json.loads(self.spec_path.read_text())
        for ref in template["producer_receipts"]:
            if Path(ref["path"]) == boot_receipt:
                ref.clear()
                ref["path"] = BOOT_RECEIPT_MARKER
        resolved = resolve_spec_template(
            template,
            boot_receipt,
            "fn01-final-fixture-20260728-r1",
        )
        matching = [
            ref for ref in resolved["producer_receipts"]
            if ref["path"] == str(boot_receipt.resolve())
        ]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["sha256"], sha256(boot_receipt))

    def test_pipeline_template_rejects_missing_marker(self) -> None:
        template = json.loads(self.spec_path.read_text())
        with self.assertRaisesRegex(ContractError, "exactly one"):
            resolve_spec_template(
                template,
                self.root / "receipts" / "boot-r1.json",
                "fn01-final-fixture-20260728-r1",
            )

    def test_labeled_synthetic_fixture_cannot_be_eligible(self) -> None:
        self.rewrite_spec(
            lambda value: value.update(fixture_kind="SYNTHETIC_CONTRACT_ONLY")
        )
        with self.assertRaisesRegex(ContractError, "synthetic fixture"):
            Controller(self.spec_path, request_eligible=True).validate()


if __name__ == "__main__":
    unittest.main()
