#!/usr/bin/env python3
"""Fail-closed semantic validator for the M05 reliability baseline.

The JSON Schema freezes the M05-private report shape. This program checks the
cross-field, current-byte, local-path and promotion rules that JSON Schema does
not express conveniently. It never builds or loads product code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = (
    REPO_ROOT
    / "adapter/verification/bionic-musl/schema/reliability-baseline.v1.schema.json"
)
CANONICAL_BOOTSTRAP_NAME = "BIONIC-MUSL-UNITY-INDEPENDENT-VERIFIER-BOOTSTRAP.md"
CANONICAL_REDTEAM_PATH = (
    "adapter/research/atoms/L03/A12/runtime-generation-redteam"
)

TOP_KEYS = {
    "schema_version",
    "baseline_id",
    "boundary",
    "assessment_kind",
    "evidence_label",
    "product_claim",
    "device_verified",
    "architecture_contract",
    "environment",
    "external_inputs",
    "candidate",
    "runtime_generation_redteam",
    "closure_gates",
    "reliability_matrix",
    "shim_inventory",
    "verdict",
}
EVIDENCE_LABELS = {"stub", "build_pass", "real_impl", "device_verified"}
GATE_STATUSES = {"not_run", "blocked", "pass", "fail"}
CLOSURE_GATE_KEYS = {
    "recursive_provider_closure",
    "strong_undefined_resolution",
    "namespace_isolation",
    "identity_match",
    "common_generation_token",
    "sealed_fd_identity",
}
RELIABILITY_GATE_KEYS = {
    "host_sanitizer_failure_atomicity",
    "pthread_stress",
    "six_entry_guard_tls",
    "namespace_lifecycle",
    "fault_classification",
    "bounded_soak",
}
IDENTITY_ROLES = {
    "apk",
    "unity_dso",
    "loader",
    "musl",
    "typed_bridge",
    "provider",
    "tool",
    "input_manifest",
    "synthetic",
}
SHA256_LENGTH = 64


class BaselineValidator:
    def __init__(self, document: Any) -> None:
        self.document = document
        self.errors: list[str] = []

    def error(self, location: str, message: str) -> None:
        self.errors.append(f"{location}: {message}")

    def require_object(self, value: Any, location: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            self.error(location, "must be an object")
            return {}
        return value

    def exact_keys(
        self,
        value: dict[str, Any],
        location: str,
        required: set[str],
        optional: set[str] | None = None,
    ) -> None:
        optional = optional or set()
        missing = sorted(required - value.keys())
        extra = sorted(value.keys() - required - optional)
        if missing:
            self.error(location, f"missing keys: {', '.join(missing)}")
        if extra:
            self.error(location, f"unexpected keys: {', '.join(extra)}")

    def require_nonempty_string(self, value: Any, location: str) -> str:
        if not isinstance(value, str) or not value.strip():
            self.error(location, "must be a nonempty string")
            return ""
        return value

    def require_bool(self, value: Any, location: str) -> bool:
        if not isinstance(value, bool):
            self.error(location, "must be a boolean")
            return False
        return value

    def require_string_list(
        self, value: Any, location: str, *, minimum: int = 0, maximum: int | None = None
    ) -> list[str]:
        if not isinstance(value, list):
            self.error(location, "must be an array")
            return []
        if len(value) < minimum:
            self.error(location, f"must contain at least {minimum} item(s)")
        if maximum is not None and len(value) > maximum:
            self.error(location, f"must contain at most {maximum} item(s)")
        for index, item in enumerate(value):
            self.require_nonempty_string(item, f"{location}[{index}]")
        return value

    def validate_sha256(self, value: Any, location: str) -> str:
        if (
            not isinstance(value, str)
            or len(value) != SHA256_LENGTH
            or any(char not in "0123456789abcdef" for char in value)
        ):
            self.error(location, "must be 64 lowercase hexadecimal characters")
            return ""
        return value

    def repo_path(self, value: Any, location: str) -> Path | None:
        text = self.require_nonempty_string(value, location)
        if not text:
            return None
        if "\\" in text:
            self.error(location, "backslash paths are forbidden")
            return None
        pure = PurePosixPath(text)
        if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
            self.error(location, "must be a normalized repository-relative path")
            return None
        candidate = REPO_ROOT.joinpath(*pure.parts)
        try:
            resolved = candidate.resolve(strict=False)
            resolved.relative_to(REPO_ROOT)
        except (OSError, ValueError):
            self.error(location, "escapes the current worktree")
            return None
        return candidate

    @staticmethod
    def sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @classmethod
    def sha256_tree(cls, path: Path) -> str:
        digest = hashlib.sha256()
        for child in sorted(path.rglob("*"), key=lambda item: item.as_posix()):
            if child.is_symlink():
                raise ValueError(f"symlink in evidence tree: {child}")
            if not child.is_file():
                continue
            relative = child.relative_to(path).as_posix()
            digest.update(cls.sha256_file(child).encode("ascii"))
            digest.update(b"  ")
            digest.update(relative.encode("utf-8"))
            digest.update(b"\n")
        return digest.hexdigest()

    def validate_local_hash(
        self, path_value: Any, hash_value: Any, location: str
    ) -> Path | None:
        path = self.repo_path(path_value, f"{location}.path")
        expected = self.validate_sha256(hash_value, f"{location}.sha256")
        if path is None or not expected:
            return path
        if not path.exists():
            self.error(f"{location}.path", "does not exist in the current worktree")
            return path
        if path.is_symlink():
            self.error(f"{location}.path", "symlink evidence is forbidden")
            return path
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(REPO_ROOT)
        except (OSError, ValueError):
            self.error(f"{location}.path", "does not resolve inside the current worktree")
            return path
        if not (path.is_file() or path.is_dir()):
            self.error(f"{location}.path", "must be a regular file or directory")
            return path
        try:
            observed = self.sha256_file(path) if path.is_file() else self.sha256_tree(path)
        except (OSError, ValueError) as error:
            self.error(location, f"cannot hash local evidence: {error}")
            return path
        if observed != expected:
            self.error(location, f"SHA256 mismatch: observed {observed}")
        return path

    def validate_evidence_ref(self, value: Any, location: str) -> None:
        ref = self.require_object(value, location)
        self.exact_keys(ref, location, {"path", "sha256"})
        if "path" in ref and "sha256" in ref:
            self.validate_local_hash(ref["path"], ref["sha256"], location)

    def validate_gate(self, value: Any, location: str) -> str:
        gate = self.require_object(value, location)
        self.exact_keys(gate, location, {"status", "evidence", "metrics", "failure"})
        status = gate.get("status")
        if status not in GATE_STATUSES:
            self.error(f"{location}.status", f"must be one of {sorted(GATE_STATUSES)}")
            status = "not_run"
        evidence = gate.get("evidence")
        if not isinstance(evidence, list):
            self.error(f"{location}.evidence", "must be an array")
            evidence = []
        for index, ref in enumerate(evidence):
            self.validate_evidence_ref(ref, f"{location}.evidence[{index}]")
        metrics = gate.get("metrics")
        if not isinstance(metrics, dict):
            self.error(f"{location}.metrics", "must be an object")
        else:
            for key, metric in metrics.items():
                if not isinstance(key, str) or not key:
                    self.error(f"{location}.metrics", "metric names must be nonempty strings")
                if not isinstance(metric, (str, int, float, bool)) or metric is None:
                    self.error(
                        f"{location}.metrics.{key}",
                        "must be a string, number or boolean",
                    )
        failure = gate.get("failure")
        if not isinstance(failure, str):
            self.error(f"{location}.failure", "must be a string")
            failure = ""
        if status == "pass" and not evidence:
            self.error(location, "a passing gate requires current local evidence")
        if status == "pass" and failure:
            self.error(location, "a passing gate cannot carry a failure")
        if status == "fail" and not failure:
            self.error(location, "a failing gate must preserve its failure")
        return status

    def validate_architecture(self, assessment_kind: str) -> dict[str, Any]:
        architecture = self.require_object(
            self.document.get("architecture_contract"), "architecture_contract"
        )
        self.exact_keys(architecture, "architecture_contract", {"three_domains", "bootstrap"})
        if architecture.get("three_domains") != [
            "oh_musl",
            "per_app_bionic",
            "typed_bridge",
        ]:
            self.error(
                "architecture_contract.three_domains",
                "must preserve the ordered three-domain model",
            )
        bootstrap = self.require_object(
            architecture.get("bootstrap"), "architecture_contract.bootstrap"
        )
        self.exact_keys(
            bootstrap,
            "architecture_contract.bootstrap",
            {"path", "availability", "s1_s7_mapping_available", "missing_evidence"},
            {"sha256"},
        )
        path_text = bootstrap.get("path")
        path = self.repo_path(path_text, "architecture_contract.bootstrap.path")
        if assessment_kind == "candidate_audit" and isinstance(path_text, str):
            if PurePosixPath(path_text).name != CANONICAL_BOOTSTRAP_NAME:
                self.error(
                    "architecture_contract.bootstrap.path",
                    f"must name {CANONICAL_BOOTSTRAP_NAME}",
                )
        availability = bootstrap.get("availability")
        mapping_available = self.require_bool(
            bootstrap.get("s1_s7_mapping_available"),
            "architecture_contract.bootstrap.s1_s7_mapping_available",
        )
        missing = self.require_string_list(
            bootstrap.get("missing_evidence"),
            "architecture_contract.bootstrap.missing_evidence",
        )
        if availability == "missing":
            if "sha256" in bootstrap:
                self.error("architecture_contract.bootstrap", "missing input cannot have a SHA256")
            if mapping_available:
                self.error(
                    "architecture_contract.bootstrap.s1_s7_mapping_available",
                    "cannot be true while the canonical bootstrap is missing",
                )
            if not missing:
                self.error(
                    "architecture_contract.bootstrap.missing_evidence",
                    "must explain the missing canonical input",
                )
        elif availability == "present":
            if not mapping_available:
                self.error(
                    "architecture_contract.bootstrap.s1_s7_mapping_available",
                    "present bootstrap must carry the S1-S7 mapping",
                )
            if missing:
                self.error(
                    "architecture_contract.bootstrap.missing_evidence",
                    "must be empty when the canonical input is present",
                )
            if "sha256" not in bootstrap:
                self.error("architecture_contract.bootstrap.sha256", "is required")
            elif path is not None:
                self.validate_local_hash(
                    path_text,
                    bootstrap["sha256"],
                    "architecture_contract.bootstrap",
                )
        else:
            self.error(
                "architecture_contract.bootstrap.availability",
                "must be missing or present",
            )
        return bootstrap

    def validate_environment(self) -> dict[str, Any]:
        environment = self.require_object(self.document.get("environment"), "environment")
        self.exact_keys(environment, "environment", {"host", "device"})
        host = self.require_object(environment.get("host"), "environment.host")
        self.exact_keys(host, "environment.host", {"description", "tool_receipts"})
        self.require_nonempty_string(host.get("description"), "environment.host.description")
        receipts = host.get("tool_receipts")
        if not isinstance(receipts, list):
            self.error("environment.host.tool_receipts", "must be an array")
        else:
            for index, ref in enumerate(receipts):
                self.validate_evidence_ref(ref, f"environment.host.tool_receipts[{index}]")
        device = self.require_object(environment.get("device"), "environment.device")
        self.exact_keys(device, "environment.device", {"accessed"}, {"serial", "boot_id", "receipt"})
        accessed = self.require_bool(device.get("accessed"), "environment.device.accessed")
        if accessed:
            self.require_nonempty_string(device.get("serial"), "environment.device.serial")
            self.require_nonempty_string(device.get("boot_id"), "environment.device.boot_id")
            if "receipt" not in device:
                self.error("environment.device.receipt", "is required for device evidence")
            else:
                self.validate_evidence_ref(device["receipt"], "environment.device.receipt")
        elif set(device) != {"accessed"}:
            self.error(
                "environment.device",
                "serial, boot_id and receipt are forbidden when no device was accessed",
            )
        return device

    def validate_external_inputs(self) -> None:
        inputs = self.document.get("external_inputs")
        if not isinstance(inputs, list):
            self.error("external_inputs", "must be an array")
            return
        for index, item_value in enumerate(inputs):
            location = f"external_inputs[{index}]"
            item = self.require_object(item_value, location)
            self.exact_keys(
                item,
                location,
                {"origin", "origin_path", "origin_sha256", "local_path", "local_sha256"},
            )
            if item.get("origin") not in {
                "aosp-14",
                "openharmony-6.1.0.31-wukong100",
            }:
                self.error(f"{location}.origin", "is not an approved standard upstream")
            self.require_nonempty_string(item.get("origin_path"), f"{location}.origin_path")
            self.validate_sha256(item.get("origin_sha256"), f"{location}.origin_sha256")
            if "local_path" in item and "local_sha256" in item:
                self.validate_local_hash(item["local_path"], item["local_sha256"], location)

    def validate_identity(
        self,
        value: Any,
        location: str,
        generation_token: str,
        assessment_kind: str,
    ) -> str:
        identity = self.require_object(value, location)
        self.exact_keys(
            identity,
            location,
            {"role", "kind", "path", "sha256", "bytes", "generation_token"},
            {"elf_machine", "soname", "build_id", "apk_entry"},
        )
        role = identity.get("role")
        if role not in IDENTITY_ROLES:
            self.error(f"{location}.role", "is not an allowed identity role")
            role = "synthetic"
        kind = identity.get("kind")
        if kind not in {"apk", "elf", "manifest", "tool", "synthetic"}:
            self.error(f"{location}.kind", "is not an allowed identity kind")
        if assessment_kind == "candidate_audit" and (role == "synthetic" or kind == "synthetic"):
            self.error(location, "synthetic identities are forbidden in a candidate audit")
        if identity.get("generation_token") != generation_token:
            self.error(f"{location}.generation_token", "does not match the candidate generation")
        size = identity.get("bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            self.error(f"{location}.bytes", "must be a positive integer")
        path = None
        if "path" in identity and "sha256" in identity:
            path = self.validate_local_hash(identity["path"], identity["sha256"], location)
        if path is not None and path.is_file() and isinstance(size, int):
            observed_size = path.stat().st_size
            if observed_size != size:
                self.error(f"{location}.bytes", f"size mismatch: observed {observed_size}")
        if assessment_kind == "candidate_audit" and kind == "elf":
            self.require_nonempty_string(identity.get("elf_machine"), f"{location}.elf_machine")
            self.require_nonempty_string(identity.get("build_id"), f"{location}.build_id")
            if role != "unity_dso":
                self.require_nonempty_string(identity.get("soname"), f"{location}.soname")
        if assessment_kind == "candidate_audit" and role == "unity_dso":
            self.require_nonempty_string(identity.get("apk_entry"), f"{location}.apk_entry")
        return role

    def validate_runtime_readiness(
        self,
        value: Any,
        candidate_availability: str,
        generation_token: str,
    ) -> dict[str, Any]:
        location = "candidate.runtime_readiness"
        runtime = self.require_object(value, location)
        self.exact_keys(
            runtime,
            location,
            {"availability", "verification_status", "missing_evidence", "failure"},
            {
                "child_receipt_schema",
                "child_receipt",
                "spawn_receipt_schema",
                "spawn_receipt",
                "binding",
            },
        )
        availability = runtime.get("availability")
        status = runtime.get("verification_status")
        missing = self.require_string_list(
            runtime.get("missing_evidence"), f"{location}.missing_evidence"
        )
        failure = runtime.get("failure")
        if not isinstance(failure, str):
            self.error(f"{location}.failure", "must be a string")
            failure = ""
        receipt_keys = {
            "child_receipt_schema",
            "child_receipt",
            "spawn_receipt_schema",
            "spawn_receipt",
            "binding",
        }
        if availability == "missing":
            if status != "not_run":
                self.error(
                    f"{location}.verification_status",
                    "missing runtime receipts must remain not_run",
                )
            if not missing:
                self.error(
                    f"{location}.missing_evidence",
                    "must list the missing child/spawn binding evidence",
                )
            if failure:
                self.error(
                    f"{location}.failure",
                    "missing/not-run input is not an observed runtime failure",
                )
            unexpected = sorted(receipt_keys & runtime.keys())
            if unexpected:
                self.error(
                    location,
                    f"missing runtime input cannot carry: {', '.join(unexpected)}",
                )
        elif availability == "present":
            if candidate_availability != "present":
                self.error(location, "runtime readiness cannot precede an offline candidate")
            if status not in {"pass", "fail"}:
                self.error(
                    f"{location}.verification_status",
                    "present runtime receipts must be verified pass or fail",
                )
            missing_keys = sorted(receipt_keys - runtime.keys())
            if missing_keys:
                self.error(location, f"missing keys: {', '.join(missing_keys)}")
            if missing:
                self.error(
                    f"{location}.missing_evidence",
                    "must be empty when runtime receipts are present",
                )
            if runtime.get("child_receipt_schema") != "ChildRuntimeReadyReceiptV1":
                self.error(
                    f"{location}.child_receipt_schema",
                    "must be ChildRuntimeReadyReceiptV1",
                )
            if runtime.get("spawn_receipt_schema") != "SpawnBirthReceiptV1":
                self.error(
                    f"{location}.spawn_receipt_schema",
                    "must be SpawnBirthReceiptV1",
                )
            if "child_receipt" in runtime:
                self.validate_evidence_ref(runtime["child_receipt"], f"{location}.child_receipt")
            if "spawn_receipt" in runtime:
                self.validate_evidence_ref(runtime["spawn_receipt"], f"{location}.spawn_receipt")
            binding = self.require_object(runtime.get("binding"), f"{location}.binding")
            self.exact_keys(
                binding,
                f"{location}.binding",
                {"pid", "start_seq", "generation_token", "epoch"},
            )
            pid = binding.get("pid")
            if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
                self.error(f"{location}.binding.pid", "must be a positive integer")
            self.require_nonempty_string(
                binding.get("start_seq"), f"{location}.binding.start_seq"
            )
            self.require_nonempty_string(binding.get("epoch"), f"{location}.binding.epoch")
            bound_generation = self.require_nonempty_string(
                binding.get("generation_token"),
                f"{location}.binding.generation_token",
            )
            if status == "pass" and bound_generation != generation_token:
                self.error(
                    f"{location}.binding.generation_token",
                    "passing child-ready receipt must bind the offline generation",
                )
            if status == "pass" and failure:
                self.error(f"{location}.failure", "a passing binding cannot carry a failure")
            if status == "fail" and not failure:
                self.error(f"{location}.failure", "a failed binding must preserve its failure")
        else:
            self.error(f"{location}.availability", "must be missing or present")
        return runtime

    def validate_candidate(
        self, assessment_kind: str
    ) -> tuple[dict[str, Any], str, dict[str, Any]]:
        candidate = self.require_object(self.document.get("candidate"), "candidate")
        self.exact_keys(
            candidate,
            "candidate",
            {"availability", "missing_evidence", "identities", "runtime_readiness"},
            {
                "generation_token",
                "offline_generation_receipt_schema",
                "offline_generation_receipt",
            },
        )
        availability = candidate.get("availability")
        missing = self.require_string_list(
            candidate.get("missing_evidence"), "candidate.missing_evidence"
        )
        identities = candidate.get("identities")
        if not isinstance(identities, list):
            self.error("candidate.identities", "must be an array")
            identities = []
        generation_token = ""
        if availability == "missing":
            if not missing:
                self.error("candidate.missing_evidence", "must explain why no candidate exists")
            if identities:
                self.error("candidate.identities", "must be empty when candidate is missing")
            forbidden = {
                "generation_token",
                "offline_generation_receipt_schema",
                "offline_generation_receipt",
            } & candidate.keys()
            if forbidden:
                self.error(
                    "candidate",
                    "missing candidate cannot carry an offline generation receipt",
                )
        elif availability == "present":
            generation_token = self.require_nonempty_string(
                candidate.get("generation_token"), "candidate.generation_token"
            )
            if missing:
                self.error("candidate.missing_evidence", "must be empty for a present candidate")
            if candidate.get("offline_generation_receipt_schema") != "NativeGenerationReceiptV1":
                self.error(
                    "candidate.offline_generation_receipt_schema",
                    "must be NativeGenerationReceiptV1",
                )
            if "offline_generation_receipt" not in candidate:
                self.error(
                    "candidate.offline_generation_receipt",
                    "is required for a present candidate",
                )
            else:
                self.validate_evidence_ref(
                    candidate["offline_generation_receipt"],
                    "candidate.offline_generation_receipt",
                )
            roles: list[str] = []
            for index, identity in enumerate(identities):
                roles.append(
                    self.validate_identity(
                        identity,
                        f"candidate.identities[{index}]",
                        generation_token,
                        assessment_kind,
                    )
                )
            required_counts = {
                "apk": 1,
                "unity_dso": 4,
                "loader": 1,
                "musl": 1,
                "typed_bridge": 1,
            }
            for role, expected in required_counts.items():
                if roles.count(role) != expected:
                    self.error(
                        "candidate.identities",
                        f"requires exactly {expected} {role} identity/identities",
                    )
            if roles.count("provider") < 1:
                self.error("candidate.identities", "requires at least one recursive provider")
            if assessment_kind == "candidate_audit":
                paths = [item.get("path") for item in identities if isinstance(item, dict)]
                if len(paths) != len(set(paths)):
                    self.error("candidate.identities", "candidate identity paths must be unique")
        else:
            self.error("candidate.availability", "must be missing or present")
        runtime = self.validate_runtime_readiness(
            candidate.get("runtime_readiness"),
            availability if isinstance(availability, str) else "missing",
            generation_token,
        )
        return candidate, generation_token, runtime

    def validate_redteam(
        self, assessment_kind: str, generation_token: str
    ) -> dict[str, Any]:
        redteam = self.require_object(
            self.document.get("runtime_generation_redteam"),
            "runtime_generation_redteam",
        )
        self.exact_keys(
            redteam,
            "runtime_generation_redteam",
            {
                "source_path",
                "availability",
                "expected_gate_count",
                "transfer_policy",
                "gates",
                "all_pass",
                "missing_evidence",
            },
            {"source_sha256"},
        )
        source_path = redteam.get("source_path")
        self.repo_path(source_path, "runtime_generation_redteam.source_path")
        if assessment_kind == "candidate_audit" and source_path != CANONICAL_REDTEAM_PATH:
            self.error(
                "runtime_generation_redteam.source_path",
                f"must be {CANONICAL_REDTEAM_PATH}",
            )
        if redteam.get("expected_gate_count") != 22:
            self.error("runtime_generation_redteam.expected_gate_count", "must equal 22")
        if redteam.get("transfer_policy") != "recompute_for_exact_current_generation":
            self.error(
                "runtime_generation_redteam.transfer_policy",
                "old verdict transfer is forbidden",
            )
        gates = redteam.get("gates")
        if not isinstance(gates, list):
            self.error("runtime_generation_redteam.gates", "must be an array")
            gates = []
        missing = self.require_string_list(
            redteam.get("missing_evidence"),
            "runtime_generation_redteam.missing_evidence",
        )
        availability = redteam.get("availability")
        all_pass = self.require_bool(
            redteam.get("all_pass"), "runtime_generation_redteam.all_pass"
        )
        if availability == "missing":
            if "source_sha256" in redteam:
                self.error("runtime_generation_redteam", "missing source cannot have a SHA256")
            if gates:
                self.error("runtime_generation_redteam.gates", "must be empty when source is missing")
            if all_pass:
                self.error("runtime_generation_redteam.all_pass", "cannot pass without source")
            if not missing:
                self.error(
                    "runtime_generation_redteam.missing_evidence",
                    "must explain the missing canonical source",
                )
        elif availability == "present":
            if "source_sha256" not in redteam:
                self.error("runtime_generation_redteam.source_sha256", "is required")
            else:
                self.validate_local_hash(
                    source_path,
                    redteam["source_sha256"],
                    "runtime_generation_redteam.source",
                )
            if missing:
                self.error(
                    "runtime_generation_redteam.missing_evidence",
                    "must be empty when source is present",
                )
            if len(gates) != 22:
                self.error(
                    "runtime_generation_redteam.gates",
                    f"must contain exactly 22 gates, observed {len(gates)}",
                )
            gate_ids: list[str] = []
            observed_all_pass = True
            for index, gate_value in enumerate(gates):
                location = f"runtime_generation_redteam.gates[{index}]"
                gate = self.require_object(gate_value, location)
                self.exact_keys(
                    gate,
                    location,
                    {"gate_id", "result", "generation_token", "evidence"},
                )
                gate_id = self.require_nonempty_string(gate.get("gate_id"), f"{location}.gate_id")
                gate_ids.append(gate_id)
                if gate.get("result") not in {"pass", "fail"}:
                    self.error(f"{location}.result", "must be pass or fail")
                    observed_all_pass = False
                elif gate["result"] != "pass":
                    observed_all_pass = False
                if gate.get("generation_token") != generation_token:
                    self.error(
                        f"{location}.generation_token",
                        "does not match the exact current candidate",
                    )
                if "evidence" in gate:
                    self.validate_evidence_ref(gate["evidence"], f"{location}.evidence")
            if len(gate_ids) != len(set(gate_ids)):
                self.error("runtime_generation_redteam.gates", "gate IDs must be unique")
            if all_pass != observed_all_pass:
                self.error(
                    "runtime_generation_redteam.all_pass",
                    "does not equal the recomputed 22-gate result",
                )
        else:
            self.error("runtime_generation_redteam.availability", "must be missing or present")
        return redteam

    def validate_gate_set(
        self, key: str, expected_keys: set[str]
    ) -> tuple[dict[str, Any], dict[str, str]]:
        gate_set = self.require_object(self.document.get(key), key)
        self.exact_keys(gate_set, key, expected_keys)
        statuses: dict[str, str] = {}
        for gate_name in sorted(expected_keys):
            statuses[gate_name] = self.validate_gate(
                gate_set.get(gate_name), f"{key}.{gate_name}"
            )
        return gate_set, statuses

    def validate_shims(self) -> None:
        inventory = self.document.get("shim_inventory")
        if not isinstance(inventory, list):
            self.error("shim_inventory", "must be an array")
            return
        identifiers: list[str] = []
        for index, item_value in enumerate(inventory):
            location = f"shim_inventory[{index}]"
            item = self.require_object(item_value, location)
            self.exact_keys(
                item,
                location,
                {"shim_id", "owner", "reason", "removal_condition", "test_coverage", "scope"},
            )
            for field in ["shim_id", "owner", "reason", "removal_condition", "test_coverage"]:
                self.require_nonempty_string(item.get(field), f"{location}.{field}")
            if item.get("scope") not in {"app_specific", "common_adapter", "verifier_only"}:
                self.error(f"{location}.scope", "is not an allowed scope")
            if isinstance(item.get("shim_id"), str):
                identifiers.append(item["shim_id"])
        if len(identifiers) != len(set(identifiers)):
            self.error("shim_inventory", "shim IDs must be unique")

    @staticmethod
    def metric(gate: dict[str, Any], name: str) -> Any:
        metrics = gate.get("metrics", {})
        return metrics.get(name) if isinstance(metrics, dict) else None

    def validate_admission_metrics(self, reliability: dict[str, Any]) -> None:
        pthread_gate = self.require_object(reliability.get("pthread_stress"), "reliability_matrix.pthread_stress")
        operations = self.metric(pthread_gate, "operations")
        if not isinstance(operations, int) or isinstance(operations, bool) or operations < 10_000_000:
            self.error(
                "reliability_matrix.pthread_stress.metrics.operations",
                "admission requires at least 10,000,000 operations",
            )

        entry_gate = self.require_object(
            reliability.get("six_entry_guard_tls"),
            "reliability_matrix.six_entry_guard_tls",
        )
        for entry in ["main", "pthread", "jni", "callback", "post_fork", "signal"]:
            if self.metric(entry_gate, entry) is not True:
                self.error(
                    f"reliability_matrix.six_entry_guard_tls.metrics.{entry}",
                    "admission requires this entry oracle",
                )

        namespace_gate = self.require_object(
            reliability.get("namespace_lifecycle"),
            "reliability_matrix.namespace_lifecycle",
        )
        cycles = self.metric(namespace_gate, "cycles")
        if not isinstance(cycles, int) or isinstance(cycles, bool) or cycles < 1:
            self.error(
                "reliability_matrix.namespace_lifecycle.metrics.cycles",
                "admission requires repeated lifecycle evidence",
            )
        for delta in ["fd_delta", "thread_delta", "tls_key_delta"]:
            if self.metric(namespace_gate, delta) != 0:
                self.error(
                    f"reliability_matrix.namespace_lifecycle.metrics.{delta}",
                    "admission requires convergence to the recorded baseline",
                )

        fault_gate = self.require_object(
            reliability.get("fault_classification"),
            "reliability_matrix.fault_classification",
        )
        for fault in ["crash", "hang", "d_state_or_device_freeze", "hdc_loss"]:
            if self.metric(fault_gate, fault) is not True:
                self.error(
                    f"reliability_matrix.fault_classification.metrics.{fault}",
                    "admission requires a distinct reproducible classifier",
                )

        soak_gate = self.require_object(
            reliability.get("bounded_soak"), "reliability_matrix.bounded_soak"
        )
        numeric_minimums = {"interaction_seconds": 300, "soak_seconds": 1800}
        for metric_name, minimum in numeric_minimums.items():
            observed = self.metric(soak_gate, metric_name)
            if not isinstance(observed, (int, float)) or isinstance(observed, bool) or observed < minimum:
                self.error(
                    f"reliability_matrix.bounded_soak.metrics.{metric_name}",
                    f"admission requires at least {minimum}",
                )
        if self.metric(soak_gate, "restarts") != 0:
            self.error(
                "reliability_matrix.bounded_soak.metrics.restarts",
                "admission requires the same uninterrupted process generation",
            )
        for metric_name in [
            "present_progress",
            "fd_monotonic_growth_absent",
            "thread_monotonic_growth_absent",
            "rss_pss_monotonic_growth_absent",
        ]:
            if self.metric(soak_gate, metric_name) is not True:
                self.error(
                    f"reliability_matrix.bounded_soak.metrics.{metric_name}",
                    "admission requires this bounded-soak observation",
                )

    def validate_verdict(
        self,
        assessment_kind: str,
        candidate: dict[str, Any],
        runtime: dict[str, Any],
        bootstrap: dict[str, Any],
        redteam: dict[str, Any],
        device: dict[str, Any],
        closure_statuses: dict[str, str],
        reliability: dict[str, Any],
        reliability_statuses: dict[str, str],
        require_admission: bool,
        require_offline_ready: bool,
        require_runtime_ready: bool,
    ) -> bool:
        verdict = self.require_object(self.document.get("verdict"), "verdict")
        self.exact_keys(
            verdict,
            "verdict",
            {
                "assessment",
                "device_admission",
                "first_failure_gate",
                "proven",
                "not_proven",
                "failed",
                "next_evidence",
            },
        )
        assessment = verdict.get("assessment")
        if assessment not in {"not_evaluated", "fail", "admit"}:
            self.error("verdict.assessment", "must be not_evaluated, fail or admit")
        admission = self.require_bool(verdict.get("device_admission"), "verdict.device_admission")
        self.require_nonempty_string(
            verdict.get("first_failure_gate"), "verdict.first_failure_gate"
        )
        self.require_string_list(verdict.get("proven"), "verdict.proven")
        self.require_string_list(
            verdict.get("not_proven"), "verdict.not_proven", minimum=1
        )
        self.require_string_list(verdict.get("failed"), "verdict.failed")
        self.require_string_list(
            verdict.get("next_evidence"), "verdict.next_evidence", minimum=1, maximum=1
        )
        if admission != (assessment == "admit"):
            self.error(
                "verdict",
                "device_admission=true if and only if assessment=admit",
            )
        if assessment_kind == "verifier_self_test":
            if admission:
                self.error("verdict.device_admission", "self-tests can never admit product bytes")
            if self.document.get("device_verified"):
                self.error("device_verified", "self-tests can never be device verified")
        if candidate.get("availability") == "missing":
            if assessment != "not_evaluated" or admission:
                self.error("verdict", "missing candidate must remain not_evaluated and denied")
            if verdict.get("first_failure_gate") != "F00_REQUIRED_LOCAL_INPUTS":
                self.error(
                    "verdict.first_failure_gate",
                    "missing candidate must stop at F00_REQUIRED_LOCAL_INPUTS",
                )
        if runtime.get("availability") == "missing":
            for gate_name in [
                "six_entry_guard_tls",
                "namespace_lifecycle",
                "fault_classification",
                "bounded_soak",
            ]:
                if reliability_statuses.get(gate_name) not in {"not_run", "blocked"}:
                    self.error(
                        f"reliability_matrix.{gate_name}.status",
                        "runtime gate cannot run before ChildRuntimeReadyReceiptV1 binding",
                    )
        offline_ready = (
            assessment_kind == "candidate_audit"
            and candidate.get("availability") == "present"
            and bootstrap.get("availability") == "present"
            and bootstrap.get("s1_s7_mapping_available") is True
            and redteam.get("availability") == "present"
            and redteam.get("all_pass") is True
            and all(status == "pass" for status in closure_statuses.values())
        )
        runtime_ready = (
            offline_ready
            and runtime.get("availability") == "present"
            and runtime.get("verification_status") == "pass"
        )
        if admission:
            if assessment_kind != "candidate_audit":
                self.error("verdict.device_admission", "only a candidate audit may admit bytes")
            if candidate.get("availability") != "present":
                self.error("candidate.availability", "admission requires a present candidate")
            if runtime.get("availability") != "present" or runtime.get(
                "verification_status"
            ) != "pass":
                self.error(
                    "candidate.runtime_readiness",
                    "admission requires ChildRuntimeReadyReceiptV1 bound to SpawnBirthReceiptV1, pid, startSeq, generation and epoch",
                )
            if bootstrap.get("availability") != "present" or not bootstrap.get(
                "s1_s7_mapping_available"
            ):
                self.error("architecture_contract.bootstrap", "admission requires canonical S1-S7")
            if redteam.get("availability") != "present" or not redteam.get("all_pass"):
                self.error(
                    "runtime_generation_redteam",
                    "admission requires all 22 current-generation gates",
                )
            if any(status != "pass" for status in closure_statuses.values()):
                self.error("closure_gates", "admission requires every closure gate to pass")
            if any(status != "pass" for status in reliability_statuses.values()):
                self.error("reliability_matrix", "admission requires every reliability gate to pass")
            if not self.document.get("device_verified"):
                self.error("device_verified", "admission requires true-device evidence")
            if self.document.get("evidence_label") != "device_verified":
                self.error("evidence_label", "admission requires device_verified label")
            if not device.get("accessed"):
                self.error("environment.device.accessed", "admission requires a device receipt")
            self.validate_admission_metrics(reliability)
        if require_offline_ready and not offline_ready:
            self.error(
                "candidate.offline_generation_receipt",
                "required exact-current offline generation gate was not achieved",
            )
        if require_runtime_ready and not runtime_ready:
            self.error(
                "candidate.runtime_readiness",
                "required ChildRuntimeReadyReceiptV1/SpawnBirthReceiptV1 binding was not achieved",
            )
        if require_admission and not admission:
            self.error("verdict.device_admission", "required admission was not achieved")
        return admission

    def validate(
        self,
        require_admission: bool = False,
        require_offline_ready: bool = False,
        require_runtime_ready: bool = False,
    ) -> bool:
        document = self.require_object(self.document, "$" )
        self.exact_keys(document, "$", TOP_KEYS)
        if document.get("schema_version") != 1:
            self.error("schema_version", "must equal 1")
        self.require_nonempty_string(document.get("baseline_id"), "baseline_id")
        if document.get("boundary") != "bionic-musl-unity-independent-verifier":
            self.error("boundary", "does not match the M05-owned boundary")
        assessment_kind = document.get("assessment_kind")
        if assessment_kind not in {"candidate_audit", "verifier_self_test"}:
            self.error("assessment_kind", "must be candidate_audit or verifier_self_test")
            assessment_kind = "candidate_audit"
        if document.get("evidence_label") not in EVIDENCE_LABELS:
            self.error("evidence_label", f"must be one of {sorted(EVIDENCE_LABELS)}")
        if document.get("product_claim") is not False:
            self.error("product_claim", "M05 baselines must keep product_claim=false")
        device_verified = self.require_bool(document.get("device_verified"), "device_verified")
        if document.get("evidence_label") == "device_verified" and not device_verified:
            self.error("evidence_label", "device_verified label requires device_verified=true")

        bootstrap = self.validate_architecture(assessment_kind)
        device = self.validate_environment()
        if device_verified and not device.get("accessed"):
            self.error("device_verified", "requires an exact device receipt")
        self.validate_external_inputs()
        candidate, generation_token, runtime = self.validate_candidate(assessment_kind)
        redteam = self.validate_redteam(assessment_kind, generation_token)
        _, closure_statuses = self.validate_gate_set("closure_gates", CLOSURE_GATE_KEYS)
        reliability, reliability_statuses = self.validate_gate_set(
            "reliability_matrix", RELIABILITY_GATE_KEYS
        )
        self.validate_shims()
        self.validate_verdict(
            assessment_kind,
            candidate,
            runtime,
            bootstrap,
            redteam,
            device,
            closure_statuses,
            reliability,
            reliability_statuses,
            require_admission,
            require_offline_ready,
            require_runtime_ready,
        )
        return not self.errors


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def validate_schema_file() -> None:
    schema = load_json(SCHEMA_PATH)
    if not isinstance(schema, dict):
        raise ValueError("baseline schema must be a JSON object")
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise ValueError("baseline schema must declare JSON Schema draft 2020-12")
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        raise ValueError("baseline schema top level must be a closed object")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path, help="repository-local baseline JSON")
    required_stage = parser.add_mutually_exclusive_group()
    required_stage.add_argument(
        "--require-offline-ready",
        action="store_true",
        help="fail unless exact offline bytes pass bootstrap, 22 red-team and closure gates",
    )
    required_stage.add_argument(
        "--require-runtime-ready",
        action="store_true",
        help="fail unless offline-ready bytes also have the child/spawn runtime binding",
    )
    required_stage.add_argument(
        "--require-admission",
        action="store_true",
        help="fail unless the exact current candidate is device-admissible",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    try:
        validate_schema_file()
        baseline_path = args.baseline
        if baseline_path.is_symlink():
            raise ValueError("baseline path must not be a symlink")
        resolved = baseline_path.resolve(strict=True)
        resolved.relative_to(REPO_ROOT)
        document = load_json(resolved)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"FAIL input: {error}", file=sys.stderr)
        return 2

    validator = BaselineValidator(document)
    if not validator.validate(
        require_admission=args.require_admission,
        require_offline_ready=args.require_offline_ready,
        require_runtime_ready=args.require_runtime_ready,
    ):
        for error in validator.errors:
            print(f"FAIL {error}", file=sys.stderr)
        return 1

    verdict = document["verdict"]
    print(
        "PASS "
        f"baseline_id={document['baseline_id']} "
        f"assessment={verdict['assessment']} "
        f"device_admission={str(verdict['device_admission']).lower()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
