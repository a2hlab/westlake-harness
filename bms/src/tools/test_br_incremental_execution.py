#!/usr/bin/env python3
"""Adversarial regression tests for repository-bound incremental decisions."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "src/tools/br-incremental-execution"
H0 = "0" * 64
H1 = "1" * 64


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class IncrementalExecutionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        loader = importlib.machinery.SourceFileLoader("incremental", str(CLI))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        assert spec and spec.loader
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def setUp(self) -> None:
        evidence_root = ROOT / "var/evidence/workflow"
        evidence_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(
            prefix=".incremental-test-", dir=evidence_root
        )
        self.temp_path = Path(self.temp.name)
        self.original_checkpoint = self.module.CHECKPOINT
        self.original_authority = self.module.AUTHORITY_REGISTRY

    def tearDown(self) -> None:
        self.module.CHECKPOINT = self.original_checkpoint
        self.module.AUTHORITY_REGISTRY = self.original_authority
        self.temp.cleanup()

    def write_json(self, name: str, value: dict) -> Path:
        path = self.temp_path / name
        path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
        return path

    def ref(self, path: Path) -> dict:
        return {
            "path": str(path.relative_to(ROOT)),
            "sha256": digest(path),
        }

    def run_cli(self, command: str, request: dict | None = None):
        args = [str(CLI), command]
        if request is not None:
            request_path = self.write_json("request.json", request)
            args.extend(["--request", str(request_path)])
        return subprocess.run(
            args, cwd=ROOT, check=False, text=True, capture_output=True
        )

    def invoke(self, function, request: dict) -> tuple[int, dict]:
        path = self.write_json("request.json", request)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            rc = function(path)
        return rc, json.loads(output.getvalue())

    def install_checkpoint(
        self,
        *,
        baseline_sha: str | None = None,
        evidence_exists: bool = True,
    ) -> tuple[Path, dict]:
        verification = ROOT / "docs/spec/atoms/Fn01/A01/verification.md"
        evidence = self.write_json(
            "prior-evidence.json",
            {
                "action_id": "Fn01.A01",
                "verdict": "PASS",
                "verification_sha256": baseline_sha or digest(verification),
            },
        )
        evidence_sha = digest(evidence)
        if not evidence_exists:
            evidence.unlink()
        checkpoint = self.write_json(
            "checkpoint.json",
            {
                "actions": [
                    {
                        "action_id": "Fn01.A01",
                        "frozen_inputs": [
                            {
                                "path": str(verification.relative_to(ROOT)),
                                "sha256": baseline_sha or digest(verification),
                            }
                        ],
                        "reuse": {
                            "formal_verdict": "PASS",
                            "formal_scope": "host_contract",
                            "evidence": str(evidence.relative_to(ROOT)),
                            "evidence_sha256": evidence_sha,
                        },
                    }
                ]
            },
        )
        self.module.CHECKPOINT = checkpoint
        self.install_authority(
            prior_action_evidence=[
                {
                    "path": str(evidence.relative_to(ROOT)),
                    "sha256": evidence_sha,
                    "issuer": "independent_verifier",
                    "decision_id": "test-prior-pass",
                    "action_id": "Fn01.A01",
                    "scope": ["host"],
                    "verification_sha256": baseline_sha or digest(verification),
                }
            ]
        )
        return verification, {
            "schema_version": 2,
            "action_id": "Fn01.A01",
            "requested_scopes": ["host"],
            "impact_receipt": None,
        }

    def install_authority(
        self,
        *,
        prior_action_evidence: list[dict] | None = None,
        impact_receipts: list[dict] | None = None,
        change_sets: list[dict] | None = None,
        build_baselines: list[dict] | None = None,
        source_freeze_receipts: list[dict] | None = None,
        owner_approval_receipts: list[dict] | None = None,
        device_deploy_sets: list[dict] | None = None,
        probe_sets: list[dict] | None = None,
    ) -> Path:
        registry = self.write_json(
            "authority.json",
            {
                "schema_version": 1,
                "registry_id": "test-authority",
                "approval_state": "accepted",
                "owner": "project_owner",
                "prior_action_evidence": prior_action_evidence or [],
                "impact_receipts": impact_receipts or [],
                "change_sets": change_sets or [],
                "build_baselines": build_baselines or [],
                "source_freeze_receipts": source_freeze_receipts or [],
                "owner_approval_receipts": owner_approval_receipts or [],
                "device_deploy_sets": device_deploy_sets or [],
                "probe_sets": probe_sets or [],
            },
        )
        self.module.AUTHORITY_REGISTRY = registry
        return registry

    def impact_receipt(
        self,
        verification: Path,
        receipt_type: str,
        affected: list[str],
        drift: list[dict],
    ) -> dict:
        cases = sorted(
            set(self.module.CASE_RE.findall(verification.read_text(encoding="utf-8")))
        )
        receipt = {
            "schema_version": 1,
            "receipt_type": receipt_type,
            "action_id": "Fn01.A01",
            "verification_sha256": digest(verification),
            "canonical_cases": cases,
            "changed_artifacts": drift,
            "affected_cases": affected,
            "invalidates_all_cases": receipt_type == "accepted_semantic_change",
        }
        if receipt_type == "accepted_semantic_change":
            receipt.update(approval_state="accepted", owner="project_owner")
        else:
            receipt["auditor"] = "independent-agent"
        path = self.write_json("impact.json", receipt)
        ref = self.ref(path)
        authority = self.module.load_json(self.module.AUTHORITY_REGISTRY)
        authority["impact_receipts"].append(
            {
                **ref,
                "issuer": (
                    "project_owner"
                    if receipt_type == "accepted_semantic_change"
                    else "independent_verifier"
                ),
                "decision_id": "test-impact",
            }
        )
        self.module.AUTHORITY_REGISTRY.write_text(
            json.dumps(authority, sort_keys=True), encoding="utf-8"
        )
        return ref

    def change_manifest(self, product: bool) -> dict:
        changed = self.temp_path / ("source.cpp" if product else "receipt.md")
        changed.write_text("current", encoding="utf-8")
        manifest = self.write_json(
            "change-manifest.json",
            {
                "schema_version": 1,
                "change_id": "change-1",
                "changes": [
                    {
                        "path": str(changed.relative_to(ROOT)),
                        "role": "product_source" if product else "receipt",
                        "previous_sha256": H0,
                        "current_sha256": digest(changed),
                    }
                ],
            },
        )
        return self.ref(manifest)

    def build_request(self, product: bool = True) -> dict:
        request = {
            "schema_version": 2,
            "change_id": "change-1",
            "baseline_id": "baseline-1",
            "request_frozen_build_id_change": False,
            "change_manifest": self.change_manifest(product),
            "stage_receipts": {stage: None for stage in self.module.STAGES},
            "source_freeze_receipt": None,
        }
        self.stage_chain(request, write_receipts=False, product=product)
        return request

    def stage_chain(
        self,
        request: dict,
        changed_outputs: bool = False,
        write_receipts: bool = True,
        product: bool = True,
    ) -> None:
        manifest_path = ROOT / request["change_manifest"]["path"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        path_roles = manifest["changes"]
        previous_upstream = H0
        current_upstream_path = None
        current_stage_components = {}
        baseline_stages = {}
        for index, stage in enumerate(self.module.STAGES):
            output = self.temp_path / f"{stage.lower()}-output.bin"
            output.write_bytes(f"{stage}-output".encode())
            current_output = digest(output)
            previous_output = H1 if changed_outputs else current_output
            role_sets = {
                "LEAF": [
                    "SOURCE",
                    "TRANSITIVE_HEADERS",
                    "COMPILE_COMMAND",
                    "COMPILER",
                    "SYSROOT",
                    "PROVIDER_ABI",
                ],
                "LINK": [
                    "LEAF_OUTPUT",
                    "LINK_COMMAND",
                    "LINKER",
                    "LINKED_LIBRARY_ABI",
                ],
                "PACKAGE": ["LINK_OUTPUT", "PACKAGE_MANIFEST", "ARTIFACT_ROLES"],
                "DEPLOY": [
                    "PACKAGE_OUTPUT",
                    "BOOT_IMAGE_CONFIG",
                    "SECURITY_POLICY",
                    "DEPLOY_EXACT_SET",
                ],
            }[stage]
            current_components = []
            baseline_components = []
            for role_index, role in enumerate(role_sets):
                if role == "SOURCE" and product:
                    path = ROOT / path_roles[0]["path"]
                elif role.endswith("_OUTPUT"):
                    assert current_upstream_path is not None
                    path = current_upstream_path
                else:
                    path = self.temp_path / f"{stage.lower()}-{role.lower()}.bin"
                    path.write_bytes(f"{stage}-{role}".encode())
                current_sha = digest(path)
                identity = f"{stage.lower()}-{role.lower()}-{role_index}"
                current = {
                    "role": role,
                    "identity": identity,
                    "path": str(path.relative_to(ROOT)),
                    "sha256": current_sha,
                }
                previous = dict(current)
                if role == "SOURCE" and product:
                    previous["sha256"] = H0
                elif role.endswith("_OUTPUT"):
                    previous["sha256"] = previous_upstream
                current_components.append(current)
                baseline_components.append(previous)
            if not product:
                current_components = []
                baseline_components = []
            current_stage_components[stage] = current_components
            baseline_stages[stage] = {
                "input_components": baseline_components,
                "output_sha256": previous_output,
            }
            if write_receipts:
                receipt = self.write_json(
                    f"{stage.lower()}-receipt.json",
                    {
                        "schema_version": 1,
                        "change_id": "change-1",
                        "stage": stage,
                        "previous_input_components": baseline_components,
                        "current_input_components": current_components,
                        "previous_output_sha256": previous_output,
                        "current_output": {
                            "path": str(output.relative_to(ROOT)),
                            "sha256": current_output,
                        },
                    },
                )
                request["stage_receipts"][stage] = self.ref(receipt)
            previous_upstream = previous_output
            current_upstream_path = output
        change_set = {
            "change_id": "change-1",
            "manifest": request["change_manifest"],
            "path_roles": path_roles,
            "current_stage_components": current_stage_components,
        }
        baseline = {"baseline_id": "baseline-1", "stages": baseline_stages}
        self.install_authority(change_sets=[change_set], build_baselines=[baseline])

    def test_policy_schema_passes_and_returns_digest(self) -> None:
        result = self.run_cli("policy-check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("policy_id=", result.stdout)
        self.assertIn("sha256=", result.stdout)

    def deployment_authority(self) -> tuple[dict, dict, dict]:
        components = [
            {
                "role": "bridge",
                "identity": "candidate-bridge",
                "deployed_path": "/system/lib64/liboh_adapter_bridge.z.so",
                "sha256": H1,
            }
        ]
        candidate = self.write_json(
            "candidate-manifest.json",
            {
                "schema_version": 1,
                "manifest_type": "exact_device_candidate",
                "action_id": "Fn01.A11",
                "deploy_set_id": "deploy-1",
                "target_serial": "serial-1",
                "boot_id": "boot-1",
                "components": components,
            },
        )
        source_receipt = self.write_json(
            "source-deploy-receipt.json", {"historical_receipt": "bound"}
        )
        receipt = self.write_json(
            "deploy-receipt.json",
            {
                "schema_version": 1,
                "receipt_type": "device_deploy_observation",
                "action_id": "Fn01.A11",
                "deploy_set_id": "deploy-1",
                "target_serial": "serial-1",
                "boot_id": "boot-1",
                "candidate_manifest_sha256": digest(candidate),
                "components": components,
                "observed_state": "LIVE_EXACT",
                "source_receipt": self.ref(source_receipt),
                "producer": "independent-evidence-producer",
            },
        )
        operations = [
            "fixture_prepare",
            "query",
            "resolver",
            "launcher",
            "token",
            "process",
        ]
        manifest = self.write_json(
            "probe-manifest.json",
            {
                "schema_version": 1,
                "manifest_type": "target_fence_probe",
                "action_id": "Fn01.A11",
                "probe_set_id": "probe-1",
                "compatible_deploy_set_id": "deploy-1",
                "target_serial": "serial-1",
                "operations": operations,
                "entrypoint_path": "/data/local/tmp/fn01-a11-probe",
                "source_sha256": H1,
            },
        )
        artifacts = self.write_json(
            "probe-artifacts.json",
            {
                "schema_version": 1,
                "manifest_type": "target_fence_probe_artifacts",
                "action_id": "Fn01.A11",
                "probe_set_id": "probe-1",
                "artifacts": [
                    {
                        "role": "probe",
                        "path": "var/evidence/probe",
                        "sha256": H1,
                        "elf_machine": "AArch64",
                    }
                ],
            },
        )
        approval_receipt = self.write_json(
            "owner-approval.json",
            {
                "schema_version": 1,
                "receipt_type": "independent_owner_probe_approval_attestation",
                "approval_receipt_id": "approval-1",
                "decision_id": "owner-accepted-probe-1",
                "approval_state": "accepted",
                "owner": "project_owner",
                "owner_decision_ref": "conversation:user:accepted",
                "attester": "independent-verifier",
                "attester_role": "independent_verifier",
                "action_id": "Fn01.A11",
                "target_serial": "serial-1",
                "boot_id": "boot-1",
                "deploy_set_id": "deploy-1",
                "probe_set_id": "probe-1",
                "candidate_manifest_sha256": digest(candidate),
                "deploy_receipt_sha256": digest(receipt),
                "probe_manifest_sha256": digest(manifest),
                "artifact_manifest_sha256": digest(artifacts),
                "allowed_operations": operations,
            },
        )
        approval = {
            "approval_receipt_id": "approval-1",
            "path": str(approval_receipt.relative_to(ROOT)),
            "sha256": digest(approval_receipt),
            "issuer": "independent_verifier",
            "decision_id": "owner-accepted-probe-1",
        }
        deploy = {
            "deploy_set_id": "deploy-1",
            "action_id": "Fn01.A11",
            "approval_receipt_id": "approval-1",
            "target_serial": "serial-1",
            "boot_id": "boot-1",
            "receipt": self.ref(receipt),
            "candidate_manifest": self.ref(candidate),
            "components": components,
        }
        probe = {
            "probe_set_id": "probe-1",
            "action_id": "Fn01.A11",
            "approval_receipt_id": "approval-1",
            "compatible_deploy_set_id": "deploy-1",
            "target_serial": "serial-1",
            "manifest": self.ref(manifest),
            "artifact_manifest": self.ref(artifacts),
            "allowed_operations": operations,
        }
        return approval, deploy, probe

    def test_hash_bound_deploy_and_probe_authority_passes(self) -> None:
        approval, deploy, probe = self.deployment_authority()
        self.install_authority(
            owner_approval_receipts=[approval],
            device_deploy_sets=[deploy],
            probe_sets=[probe],
        )
        registry, registry_sha = self.module.authority_identity()
        self.assertEqual(registry["probe_sets"][0]["probe_set_id"], "probe-1")
        self.assertEqual(registry_sha, digest(self.module.AUTHORITY_REGISTRY))

    def test_probe_authority_rejects_unknown_deploy_set(self) -> None:
        approval, _, probe = self.deployment_authority()
        self.install_authority(
            owner_approval_receipts=[approval], probe_sets=[probe]
        )
        with self.assertRaisesRegex(ValueError, "unknown deploy set"):
            self.module.authority_identity()

    def test_probe_authority_rejects_action_or_target_mismatch(self) -> None:
        approval, deploy, probe = self.deployment_authority()
        probe["target_serial"] = "foreign-serial"
        self.install_authority(
            owner_approval_receipts=[approval],
            device_deploy_sets=[deploy],
            probe_sets=[probe],
        )
        with self.assertRaisesRegex(ValueError, "action/target differs"):
            self.module.authority_identity()

    def test_probe_authority_rejects_stale_manifest_hash(self) -> None:
        approval, deploy, probe = self.deployment_authority()
        probe["manifest"]["sha256"] = H0
        self.install_authority(
            owner_approval_receipts=[approval],
            device_deploy_sets=[deploy],
            probe_sets=[probe],
        )
        with self.assertRaisesRegex(ValueError, "manifest hash mismatch"):
            self.module.authority_identity()

    def test_probe_authority_rejects_partial_operation_scope(self) -> None:
        approval, deploy, probe = self.deployment_authority()
        probe["allowed_operations"].pop()
        self.install_authority(
            owner_approval_receipts=[approval],
            device_deploy_sets=[deploy],
            probe_sets=[probe],
        )
        with self.assertRaisesRegex(ValueError, "schema violation"):
            self.module.authority_identity()

    def test_semantically_empty_self_declared_owner_cannot_authorize(self) -> None:
        approval, deploy, probe = self.deployment_authority()
        receipt_path = ROOT / deploy["receipt"]["path"]
        receipt_path.write_text('{"verdict":"PASS"}', encoding="utf-8")
        deploy["receipt"]["sha256"] = digest(receipt_path)
        approval_path = ROOT / approval["path"]
        approval_body = json.loads(approval_path.read_text(encoding="utf-8"))
        approval_body["deploy_receipt_sha256"] = deploy["receipt"]["sha256"]
        approval_path.write_text(
            json.dumps(approval_body, sort_keys=True), encoding="utf-8"
        )
        approval["sha256"] = digest(approval_path)
        self.install_authority(
            owner_approval_receipts=[approval],
            device_deploy_sets=[deploy],
            probe_sets=[probe],
        )
        with self.assertRaisesRegex(ValueError, "schema violation"):
            self.module.authority_identity()

    def test_probe_requires_independent_owner_approval_registration(self) -> None:
        _, deploy, probe = self.deployment_authority()
        self.install_authority(
            device_deploy_sets=[deploy], probe_sets=[probe]
        )
        with self.assertRaisesRegex(ValueError, "no independent owner approval"):
            self.module.authority_identity()

    def test_probe_admission_allows_only_exact_registered_operation(self) -> None:
        approval, deploy, probe = self.deployment_authority()
        registry_path = self.install_authority(
            owner_approval_receipts=[approval],
            device_deploy_sets=[deploy],
            probe_sets=[probe],
        )
        request = {
            "schema_version": 1,
            "action_id": "Fn01.A11",
            "deploy_set_id": "deploy-1",
            "probe_set_id": "probe-1",
            "target_serial": "serial-1",
            "boot_id": "boot-1",
            "operation": "query",
            "authority_registry_sha256": digest(registry_path),
            "candidate_manifest_sha256": deploy["candidate_manifest"]["sha256"],
            "probe_manifest_sha256": probe["manifest"]["sha256"],
            "artifact_manifest_sha256": probe["artifact_manifest"]["sha256"],
        }
        rc, output = self.invoke(self.module.probe_admission_check, request)
        self.assertEqual(rc, 0)
        self.assertEqual(output["decision"], "ALLOW_REGISTERED_PROBE_OPERATION")
        self.assertEqual(output["approval_receipt_id"], "approval-1")

    def test_probe_admission_rejects_stale_registry_or_wrong_boot(self) -> None:
        approval, deploy, probe = self.deployment_authority()
        registry_path = self.install_authority(
            owner_approval_receipts=[approval],
            device_deploy_sets=[deploy],
            probe_sets=[probe],
        )
        request = {
            "schema_version": 1,
            "action_id": "Fn01.A11",
            "deploy_set_id": "deploy-1",
            "probe_set_id": "probe-1",
            "target_serial": "serial-1",
            "boot_id": "boot-1",
            "operation": "query",
            "authority_registry_sha256": H0,
            "candidate_manifest_sha256": deploy["candidate_manifest"]["sha256"],
            "probe_manifest_sha256": probe["manifest"]["sha256"],
            "artifact_manifest_sha256": probe["artifact_manifest"]["sha256"],
        }
        with self.assertRaisesRegex(ValueError, "stale registry"):
            self.module.probe_admission_check(self.write_json("stale.json", request))
        request["authority_registry_sha256"] = digest(registry_path)
        request["boot_id"] = "foreign-boot"
        with self.assertRaisesRegex(ValueError, "boot_id mismatch"):
            self.module.probe_admission_check(
                self.write_json("wrong-boot.json", request)
            )

    def test_old_caller_booleans_and_all_cases_are_rejected(self) -> None:
        _, request = self.install_checkpoint()
        request["all_cases"] = ["P01"]
        request["semantic_contract_invalidates_all"] = True
        result = self.run_cli("retest", request)
        self.assertEqual(result.returncode, 2)

    def test_repository_derived_cases_and_linked_evidence_reuse(self) -> None:
        _, request = self.install_checkpoint()
        rc, output = self.invoke(self.module.classify_retest, request)
        self.assertEqual(rc, 0)
        self.assertEqual(output["decision"], "REUSE_VERDICT")
        self.assertGreater(len(output["canonical_cases"]), 1)

    def test_missing_receipt_recovers_evidence_without_retest(self) -> None:
        _, request = self.install_checkpoint(evidence_exists=False)
        rc, output = self.invoke(self.module.classify_retest, request)
        self.assertEqual(rc, 0)
        self.assertEqual(output["decision"], "EVIDENCE_RECOVERY_PENDING")
        self.assertEqual(output["retest_cases"], [])

    def test_extension_cannot_reuse_scope_with_missing_receipt(self) -> None:
        _, request = self.install_checkpoint(evidence_exists=False)
        request["requested_scopes"] = ["host", "d600"]
        _, output = self.invoke(self.module.classify_retest, request)
        self.assertEqual(output["decision"], "EVIDENCE_RECOVERY_PENDING")
        self.assertEqual(output["reused_scopes"], [])

    def test_measured_drift_without_receipt_requires_impact_audit(self) -> None:
        _, request = self.install_checkpoint(baseline_sha=H0)
        rc, output = self.invoke(self.module.classify_retest, request)
        self.assertEqual(rc, 1)
        self.assertEqual(output["decision"], "IMPACT_AUDIT_REQUIRED")

    def test_targeted_retest_requires_hash_bound_exact_audit(self) -> None:
        verification, request = self.install_checkpoint(baseline_sha=H0)
        drift = self.module.baseline_drift(
            self.module.action_checkpoint("Fn01.A01")
        )
        request["impact_receipt"] = self.impact_receipt(
            verification, "independent_impact_audit", ["F01"], drift
        )
        _, output = self.invoke(self.module.classify_retest, request)
        self.assertEqual(output["decision"], "TARGETED_RETEST")
        self.assertEqual(output["retest_cases"], ["F01"])

    def test_no_impact_audit_cannot_create_new_scope_coverage(self) -> None:
        verification, request = self.install_checkpoint(baseline_sha=H0)
        request["requested_scopes"] = ["host", "d600"]
        drift = self.module.baseline_drift(
            self.module.action_checkpoint("Fn01.A01")
        )
        request["impact_receipt"] = self.impact_receipt(
            verification, "independent_impact_audit", [], drift
        )
        _, output = self.invoke(self.module.classify_retest, request)
        self.assertEqual(output["decision"], "EXTEND_SCOPE_ONLY")
        self.assertEqual(output["reused_scopes"], ["host"])
        self.assertEqual(output["new_scopes"], ["d600"])

    def test_no_impact_audit_cannot_bypass_missing_prior_receipt(self) -> None:
        verification, request = self.install_checkpoint(
            baseline_sha=H0, evidence_exists=False
        )
        drift = self.module.baseline_drift(
            self.module.action_checkpoint("Fn01.A01")
        )
        request["impact_receipt"] = self.impact_receipt(
            verification, "independent_impact_audit", [], drift
        )
        _, output = self.invoke(self.module.classify_retest, request)
        self.assertEqual(output["decision"], "EVIDENCE_RECOVERY_PENDING")
        self.assertEqual(output["reused_scopes"], [])

    def test_full_retest_uses_repository_complete_case_set(self) -> None:
        verification, request = self.install_checkpoint(baseline_sha=H0)
        drift = self.module.baseline_drift(
            self.module.action_checkpoint("Fn01.A01")
        )
        cases = sorted(
            set(self.module.CASE_RE.findall(verification.read_text(encoding="utf-8")))
        )
        request["impact_receipt"] = self.impact_receipt(
            verification, "accepted_semantic_change", cases, drift
        )
        _, output = self.invoke(self.module.classify_retest, request)
        self.assertEqual(output["decision"], "FULL_RETEST")
        self.assertEqual(output["retest_cases"], cases)

    def test_forged_impact_receipt_hash_is_rejected(self) -> None:
        verification, request = self.install_checkpoint(baseline_sha=H0)
        drift = self.module.baseline_drift(
            self.module.action_checkpoint("Fn01.A01")
        )
        request["impact_receipt"] = self.impact_receipt(
            verification, "independent_impact_audit", ["F01"], drift
        )
        request["impact_receipt"]["sha256"] = H0
        with self.assertRaisesRegex(
            ValueError, r"(hash mismatch|authority-registry entry)"
        ):
            self.invoke(self.module.classify_retest, request)

    def test_self_declared_owner_receipt_without_registry_is_rejected(self) -> None:
        verification, request = self.install_checkpoint(baseline_sha=H0)
        drift = self.module.baseline_drift(
            self.module.action_checkpoint("Fn01.A01")
        )
        cases = sorted(
            set(self.module.CASE_RE.findall(verification.read_text(encoding="utf-8")))
        )
        request["impact_receipt"] = self.impact_receipt(
            verification, "accepted_semantic_change", cases, drift
        )
        authority = self.module.load_json(self.module.AUTHORITY_REGISTRY)
        authority["impact_receipts"] = []
        self.module.AUTHORITY_REGISTRY.write_text(
            json.dumps(authority, sort_keys=True), encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "authority-registry entry"):
            self.invoke(self.module.classify_retest, request)

    def test_hash_linked_fail_receipt_cannot_reuse_verdict(self) -> None:
        _, request = self.install_checkpoint()
        checkpoint = self.module.load_json(self.module.CHECKPOINT)
        evidence_path = ROOT / checkpoint["actions"][0]["reuse"]["evidence"]
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        evidence["verdict"] = "FAIL"
        evidence_path.write_text(json.dumps(evidence, sort_keys=True), encoding="utf-8")
        checkpoint["actions"][0]["reuse"]["evidence_sha256"] = digest(evidence_path)
        self.module.CHECKPOINT.write_text(
            json.dumps(checkpoint, sort_keys=True), encoding="utf-8"
        )
        _, output = self.invoke(self.module.classify_retest, request)
        self.assertEqual(output["decision"], "EVIDENCE_RECOVERY_PENDING")

    def test_unregistered_pass_manifest_cannot_mint_reuse_verdict(self) -> None:
        _, request = self.install_checkpoint()
        authority = self.module.load_json(self.module.AUTHORITY_REGISTRY)
        authority["prior_action_evidence"] = []
        self.module.AUTHORITY_REGISTRY.write_text(
            json.dumps(authority, sort_keys=True), encoding="utf-8"
        )
        _, output = self.invoke(self.module.classify_retest, request)
        self.assertEqual(output["decision"], "EVIDENCE_RECOVERY_PENDING")
        self.assertEqual(output["reused_scopes"], [])

    def test_receipt_only_change_never_builds_or_bumps_generation(self) -> None:
        request = self.build_request(product=False)
        rc, output = self.invoke(self.module.classify_build, request)
        self.assertEqual(rc, 0)
        self.assertEqual(output["decision"], "REISSUE_METADATA_OR_RECEIPT_ONLY")
        request["request_frozen_build_id_change"] = True
        rc, output = self.invoke(self.module.classify_build, request)
        self.assertEqual(rc, 1)
        self.assertIn("RECEIPT_ONLY", output["formal_generation"])

    def test_product_change_stops_at_first_missing_stage_receipt(self) -> None:
        request = self.build_request()
        _, output = self.invoke(self.module.classify_build, request)
        self.assertEqual(output["blocked_after"], "LEAF")
        self.assertEqual(output["required_actions"], ["LEAF_RUN_AND_COMPARE_OUTPUT"])

    def test_manifest_role_cannot_override_registered_change_role(self) -> None:
        request = self.build_request()
        manifest_path = ROOT / request["change_manifest"]["path"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["changes"][0]["role"] = "receipt"
        manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
        request["change_manifest"] = self.ref(manifest_path)
        with self.assertRaisesRegex(ValueError, "registered manifest"):
            self.invoke(self.module.classify_build, request)

    def test_product_change_must_appear_in_leaf_closed_set(self) -> None:
        request = self.build_request()
        authority = self.module.load_json(self.module.AUTHORITY_REGISTRY)
        leaf = authority["change_sets"][0]["current_stage_components"]["LEAF"]
        authority["change_sets"][0]["current_stage_components"]["LEAF"] = [
            item for item in leaf if item["role"] != "SOURCE"
        ]
        self.module.AUTHORITY_REGISTRY.write_text(
            json.dumps(authority, sort_keys=True), encoding="utf-8"
        )
        with self.assertRaisesRegex(
            ValueError, r"(closed component roles differ|omits changed product)"
        ):
            self.invoke(self.module.classify_build, request)

    def test_leaf_closed_set_requires_compiler_sysroot_and_provider_abi(self) -> None:
        request = self.build_request()
        authority = self.module.load_json(self.module.AUTHORITY_REGISTRY)
        leaf = authority["change_sets"][0]["current_stage_components"]["LEAF"]
        authority["change_sets"][0]["current_stage_components"]["LEAF"] = [
            item
            for item in leaf
            if item["role"] not in {"COMPILER", "SYSROOT", "PROVIDER_ABI"}
        ]
        self.module.AUTHORITY_REGISTRY.write_text(
            json.dumps(authority, sort_keys=True), encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "closed component roles differ"):
            self.invoke(self.module.classify_build, request)

    def test_closed_stage_component_set_rejects_undeclared_extra_role(self) -> None:
        request = self.build_request()
        authority = self.module.load_json(self.module.AUTHORITY_REGISTRY)
        leaf = authority["change_sets"][0]["current_stage_components"]["LEAF"]
        extra_path = self.temp_path / "undeclared-extra.bin"
        extra_path.write_bytes(b"extra")
        leaf.append(
            {
                "role": "UNDECLARED_EXTRA",
                "identity": "undeclared-extra",
                "path": str(extra_path.relative_to(ROOT)),
                "sha256": digest(extra_path),
            }
        )
        self.module.AUTHORITY_REGISTRY.write_text(
            json.dumps(authority, sort_keys=True), encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "closed component roles differ"):
            self.invoke(self.module.classify_build, request)

    def test_computed_keys_allow_reuse_when_actual_outputs_are_identical(self) -> None:
        request = self.build_request()
        self.stage_chain(request, changed_outputs=False)
        rc, output = self.invoke(self.module.classify_build, request)
        self.assertEqual(rc, 0)
        self.assertIsNone(output["blocked_after"])
        self.assertEqual(output["reused_stages"], list(self.module.STAGES))

    def test_upstream_output_change_cannot_reuse_unchanged_downstream_key(self) -> None:
        request = self.build_request()
        self.stage_chain(request, changed_outputs=True)
        link_ref = request["stage_receipts"]["LINK"]
        link_path = ROOT / link_ref["path"]
        link = json.loads(link_path.read_text(encoding="utf-8"))
        link["current_input_components"][0]["sha256"] = H1
        link_path.write_text(json.dumps(link, sort_keys=True), encoding="utf-8")
        request["stage_receipts"]["LINK"] = self.ref(link_path)
        with self.assertRaisesRegex(
            ValueError,
            r"(registered closed set|not bound to LEAF_OUTPUT|component hash mismatch)",
        ):
            self.invoke(self.module.classify_build, request)

    def test_formal_generation_is_never_self_authorized(self) -> None:
        request = self.build_request()
        self.stage_chain(request, changed_outputs=True)
        request["request_frozen_build_id_change"] = True
        rc, output = self.invoke(self.module.classify_build, request)
        self.assertEqual(rc, 1)
        self.assertIn("NO_ACCEPTED_FREEZE_RECEIPT", output["formal_generation"])

    def test_previous_output_cannot_be_rewritten_by_caller(self) -> None:
        request = self.build_request()
        self.stage_chain(request, changed_outputs=True)
        leaf_path = ROOT / request["stage_receipts"]["LEAF"]["path"]
        receipt = json.loads(leaf_path.read_text(encoding="utf-8"))
        receipt["previous_output_sha256"] = receipt["current_output"]["sha256"]
        leaf_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
        request["stage_receipts"]["LEAF"] = self.ref(leaf_path)
        with self.assertRaisesRegex(ValueError, "registry-bound baseline"):
            self.invoke(self.module.classify_build, request)

    def test_previous_input_path_cannot_be_rewritten_by_caller(self) -> None:
        request = self.build_request()
        self.stage_chain(request, changed_outputs=True)
        leaf_path = ROOT / request["stage_receipts"]["LEAF"]["path"]
        receipt = json.loads(leaf_path.read_text(encoding="utf-8"))
        receipt["previous_input_components"][0]["path"] = "docs/progress.md"
        leaf_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
        request["stage_receipts"]["LEAF"] = self.ref(leaf_path)
        with self.assertRaisesRegex(ValueError, "registry-bound baseline"):
            self.invoke(self.module.classify_build, request)

    def test_fake_owner_freeze_receipt_cannot_reach_registry_transition(self) -> None:
        request = self.build_request()
        self.stage_chain(request, changed_outputs=True)
        freeze = self.write_json(
            "freeze.json",
            {
                "schema_version": 1,
                "change_id": "change-1",
                "approval_state": "accepted",
                "owner": "project_owner",
                "source_tree_sha256": H1,
                "toolchain_sha256": H1,
                "commands_sha256": H1,
            },
        )
        request["source_freeze_receipt"] = self.ref(freeze)
        request["request_frozen_build_id_change"] = True
        with self.assertRaisesRegex(ValueError, "authority registration"):
            self.invoke(self.module.classify_build, request)


if __name__ == "__main__":
    unittest.main(verbosity=2)
