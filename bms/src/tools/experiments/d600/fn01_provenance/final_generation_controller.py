#!/usr/bin/env python3
"""Validate and pack one Fn01 final deployment generation.

The controller never builds or deploys.  It consumes only hash-bound producer
receipts from one explicit frozen_build_id.  Artifact paths and hashes are
imported from those receipts; caller-supplied PATH=HASH values are not an
oracle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


SHA_RE = re.compile(r"^[0-9a-f]{64}$")
ACTION_RE = re.compile(r"^Fn01[.]A(?:01|02|03|04)$")
DIRECT_ROLES = {
    "oh_adapter_bridge",
    "apk_installer",
    "oh_adapter_framework_jar",
}
BOOT_STEMS = (
    "boot",
    "boot-core-libart",
    "boot-core-icu4j",
    "boot-okhttp",
    "boot-bouncycastle",
    "boot-apache-xml",
    "boot-adapter-mainline-stubs",
    "boot-framework",
    "boot-oh-adapter-framework",
)
BOOT_ROLES = {
    f"boot:{stem}.{extension}"
    for stem in BOOT_STEMS
    for extension in ("art", "oat", "vdex")
}
REQUIRED_ARTIFACT_ROLES = DIRECT_ROLES | BOOT_ROLES


class ContractError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(value: Any) -> str:
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def load_bound_json(path: Path, expected_sha256: str, label: str) -> dict[str, Any]:
    if not SHA_RE.fullmatch(expected_sha256):
        raise ContractError(f"{label} expected sha256 is invalid")
    if not path.is_file():
        raise ContractError(f"{label} is missing: {path}")
    actual = sha256(path)
    if actual != expected_sha256:
        raise ContractError(
            f"{label} sha256 mismatch expected={expected_sha256} actual={actual}"
        )
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be a JSON object")
    return value


@dataclass(frozen=True)
class OutputFact:
    receipt_id: str
    role: str
    path: Path
    sha256: str
    bytes: int


@dataclass
class Validation:
    spec_path: Path
    spec_sha256: str
    frozen_build_id: str
    covered_actions: list[str]
    producer_receipts: dict[str, dict[str, Any]]
    producer_receipt_paths: dict[str, Path]
    outputs: dict[str, OutputFact]
    requested_eligible: bool
    eligible: bool
    report: dict[str, Any]


class Controller:
    def __init__(self, spec_path: Path, request_eligible: bool):
        self.spec_path = spec_path.resolve()
        self.spec = json.loads(self.spec_path.read_text(encoding="utf-8"))
        self.request_eligible = request_eligible
        self.frozen_build_id = self._required_string(self.spec, "frozen_build_id")
        self.receipts: dict[str, dict[str, Any]] = {}
        self.receipt_paths: dict[str, Path] = {}
        self.outputs_by_receipt: dict[tuple[str, str], OutputFact] = {}

    @staticmethod
    def _required_string(value: dict[str, Any], field: str) -> str:
        result = value.get(field)
        if not isinstance(result, str) or not result:
            raise ContractError(f"missing non-empty {field}")
        return result

    def _resolve_from_spec(self, path_value: str) -> Path:
        path = Path(path_value)
        if not path.is_absolute():
            path = self.spec_path.parent / path
        return path.resolve()

    def _validate_spec(self) -> None:
        if self.spec.get("schema_version") != "bridge.fn01.final-generation-spec.v1":
            raise ContractError("unsupported final generation spec schema")
        if self.spec.get("default_eligible") is not False:
            raise ContractError("default_eligible must be false")
        if self.spec.get("fixture_kind") is not None and self.request_eligible:
            raise ContractError("synthetic fixture cannot request eligible bundle")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,127}", self.frozen_build_id):
            raise ContractError("frozen_build_id format is invalid")

    def _load_receipts(self) -> None:
        refs = self.spec.get("producer_receipts")
        if not isinstance(refs, list) or not refs:
            raise ContractError("producer_receipts must be a non-empty list")
        forbidden = set(self.spec.get("forbidden_generation_ids", []))
        for index, ref in enumerate(refs):
            if not isinstance(ref, dict):
                raise ContractError(f"producer_receipts[{index}] must be an object")
            path = self._resolve_from_spec(self._required_string(ref, "path"))
            receipt = load_bound_json(
                path,
                self._required_string(ref, "sha256"),
                f"producer receipt {index}",
            )
            if receipt.get("schema_version") != "bridge.fn01.producer-receipt.v1":
                raise ContractError(f"unsupported producer receipt schema: {path}")
            receipt_id = self._required_string(receipt, "receipt_id")
            if receipt_id in self.receipts:
                raise ContractError(f"duplicate producer receipt_id: {receipt_id}")
            if receipt.get("frozen_build_id") != self.frozen_build_id:
                raise ContractError(f"{receipt_id} frozen_build_id mismatch")
            if receipt.get("qualification_only") is not False:
                raise ContractError(f"{receipt_id} is qualification-only")
            if receipt.get("status", {}).get("producer_pass") is not True:
                raise ContractError(f"{receipt_id} producer_pass is not true")
            generation_id = receipt.get("generation_id")
            if generation_id in forbidden:
                raise ContractError(f"{receipt_id} uses forbidden generation {generation_id}")
            for ancestor in path.parents:
                if ancestor.name == "boot-builder-qualification-r6":
                    raise ContractError(f"{receipt_id} reuses forbidden r6 qualification path")
            self.receipts[receipt_id] = receipt
            self.receipt_paths[receipt_id] = path
            outputs = receipt.get("outputs", [])
            if not isinstance(outputs, list):
                raise ContractError(f"{receipt_id} outputs must be a list")
            for output in outputs:
                if not isinstance(output, dict):
                    raise ContractError(f"{receipt_id} output must be an object")
                role = self._required_string(output, "role")
                key = (receipt_id, role)
                if key in self.outputs_by_receipt:
                    raise ContractError(f"{receipt_id} duplicate output role {role}")
                output_path = Path(self._required_string(output, "path"))
                if not output_path.is_absolute():
                    output_path = path.parent / output_path
                output_path = output_path.resolve()
                expected_hash = self._required_string(output, "sha256")
                expected_bytes = output.get("bytes")
                if not isinstance(expected_bytes, int) or expected_bytes < 1:
                    raise ContractError(f"{receipt_id}:{role} invalid bytes")
                if not output_path.is_file():
                    raise ContractError(f"{receipt_id}:{role} output missing: {output_path}")
                actual_hash = sha256(output_path)
                actual_bytes = output_path.stat().st_size
                if actual_hash != expected_hash:
                    raise ContractError(f"{receipt_id}:{role} output sha256 mismatch")
                if actual_bytes != expected_bytes:
                    raise ContractError(f"{receipt_id}:{role} output bytes mismatch")
                self.outputs_by_receipt[key] = OutputFact(
                    receipt_id=receipt_id,
                    role=role,
                    path=output_path,
                    sha256=actual_hash,
                    bytes=actual_bytes,
                )

    def _load_coverage(self) -> tuple[dict[str, Any], Path]:
        ref = self.spec.get("coverage_manifest")
        if not isinstance(ref, dict):
            raise ContractError("coverage_manifest ref is required")
        path = self._resolve_from_spec(self._required_string(ref, "path"))
        coverage = load_bound_json(
            path,
            self._required_string(ref, "sha256"),
            "coverage manifest",
        )
        if coverage.get("schema_version") != "bridge.fn01.final-coverage.v1":
            raise ContractError("unsupported final coverage schema")
        if coverage.get("frozen_build_id") != self.frozen_build_id:
            raise ContractError("coverage frozen_build_id mismatch")
        actions = self.spec.get("covered_actions")
        coverage_actions = coverage.get("covered_actions")
        if not isinstance(actions, list) or not actions:
            raise ContractError("covered_actions must be non-empty")
        if actions != coverage_actions:
            raise ContractError("spec and coverage covered_actions are not an exact list match")
        if len(set(actions)) != len(actions):
            raise ContractError("covered_actions contains duplicates")
        if any(not isinstance(action, str) or not ACTION_RE.fullmatch(action) for action in actions):
            raise ContractError("covered_actions includes unsupported Action")
        canonical = sorted(actions, key=lambda value: int(value.rsplit("A", 1)[1]))
        if actions != canonical:
            raise ContractError("covered_actions is not in canonical order")
        proofs = coverage.get("coverage_proofs")
        if not isinstance(proofs, dict) or set(proofs) != set(actions):
            raise ContractError("coverage_proofs keys are not exact-set covered_actions")
        for action in actions:
            proof = proofs[action]
            if not isinstance(proof, dict):
                raise ContractError(f"{action} proof must be an object")
            sources = proof.get("source_evidence")
            producers = proof.get("producer_receipt_ids")
            probes = proof.get("target_probe_receipt_ids")
            if not isinstance(sources, list) or not sources:
                raise ContractError(f"{action} source_evidence is empty")
            if not isinstance(producers, list) or not producers:
                raise ContractError(f"{action} producer_receipt_ids is empty")
            if any(receipt_id not in self.receipts for receipt_id in producers):
                raise ContractError(f"{action} references unknown producer receipt")
            if not isinstance(probes, list):
                raise ContractError(f"{action} target_probe_receipt_ids must be a list")
            if any(receipt_id not in self.receipts for receipt_id in probes):
                raise ContractError(f"{action} references unknown target probe receipt")
            if any(
                self.receipts[receipt_id].get("producer_kind") != "target_probe"
                for receipt_id in probes
            ):
                raise ContractError(f"{action} target probe receipt has wrong producer_kind")
            if self.request_eligible and not probes:
                raise ContractError(f"{action} has no passing target probe receipt")
        semantics = coverage.get("semantics", {})
        if semantics.get("authorizes_artifact_oracle_only") is not True:
            raise ContractError("coverage must authorize artifact oracle only")
        if semantics.get("does_not_imply_behavior_pass") is not True:
            raise ContractError("coverage must deny implied behavior PASS")
        return coverage, path

    def _bind_artifacts(self) -> dict[str, OutputFact]:
        bindings = self.spec.get("artifacts")
        if not isinstance(bindings, list):
            raise ContractError("artifacts must be a list")
        by_role: dict[str, OutputFact] = {}
        for binding in bindings:
            if not isinstance(binding, dict):
                raise ContractError("artifact binding must be an object")
            role = self._required_string(binding, "role")
            receipt_id = self._required_string(binding, "producer_receipt_id")
            output_role = self._required_string(binding, "output_role")
            if role in by_role:
                raise ContractError(f"duplicate artifact role {role}")
            key = (receipt_id, output_role)
            if key not in self.outputs_by_receipt:
                raise ContractError(f"artifact {role} has no receipt output {key}")
            by_role[role] = self.outputs_by_receipt[key]
        observed = set(by_role)
        if observed != REQUIRED_ARTIFACT_ROLES:
            raise ContractError(
                f"artifact exact-set mismatch missing={sorted(REQUIRED_ARTIFACT_ROLES - observed)} "
                f"extra={sorted(observed - REQUIRED_ARTIFACT_ROLES)}"
            )
        return by_role

    def validate(self) -> Validation:
        self._validate_spec()
        self._load_receipts()
        coverage, coverage_path = self._load_coverage()
        artifacts = self._bind_artifacts()
        eligible = self.request_eligible
        report = {
            "schema_version": "bridge.fn01.final-generation-check.v1",
            "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "spec": {
                "path": str(self.spec_path),
                "sha256": sha256(self.spec_path),
            },
            "frozen_build_id": self.frozen_build_id,
            "fixture_kind": self.spec.get("fixture_kind"),
            "coverage_manifest": {
                "path": str(coverage_path),
                "sha256": sha256(coverage_path),
            },
            "covered_actions": coverage["covered_actions"],
            "producer_receipts": [
                {
                    "receipt_id": receipt_id,
                    "path": str(self.receipt_paths[receipt_id]),
                    "sha256": sha256(self.receipt_paths[receipt_id]),
                    "producer_kind": self.receipts[receipt_id]["producer_kind"],
                    "producer_pass": True,
                }
                for receipt_id in sorted(self.receipts)
            ],
            "artifacts": [
                {
                    "role": role,
                    "producer_receipt_id": fact.receipt_id,
                    "output_role": fact.role,
                    "source_path": str(fact.path),
                    "sha256": fact.sha256,
                    "bytes": fact.bytes,
                }
                for role, fact in sorted(artifacts.items())
            ],
            "status": {
                "validation_pass": True,
                "eligible_requested": self.request_eligible,
                "eligible_for_deploy": eligible,
                "device_verified": False,
                "formal_verdict": "NOT_ISSUED",
            },
            "semantics": {
                "eligible_bundle_is_not_device_verified": True,
                "producer_pass_is_not_action_behavior_pass": True,
                "caller_reported_path_hash_is_not_an_oracle": True,
            },
        }
        return Validation(
            spec_path=self.spec_path,
            spec_sha256=sha256(self.spec_path),
            frozen_build_id=self.frozen_build_id,
            covered_actions=coverage["covered_actions"],
            producer_receipts=self.receipts,
            producer_receipt_paths=self.receipt_paths,
            outputs=artifacts,
            requested_eligible=self.request_eligible,
            eligible=eligible,
            report=report,
        )


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def pack(validation: Validation, output_dir: Path) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise ContractError(f"refuse existing output directory: {output_dir}")
    artifact_dir = output_dir / "artifacts"
    artifact_dir.mkdir(parents=True)
    packed = []
    for role, fact in sorted(validation.outputs.items()):
        safe_name = role.replace(":", "__")
        target = artifact_dir / safe_name
        shutil.copy2(fact.path, target)
        packed.append(
            {
                "role": role,
                "path": str(target.relative_to(output_dir)),
                "sha256": sha256(target),
                "bytes": target.stat().st_size,
                "producer_receipt_id": fact.receipt_id,
                "producer_output_role": fact.role,
            }
        )
    receipt_dir = output_dir / "producer-receipts"
    receipt_dir.mkdir()
    packed_receipts = []
    for receipt_id in sorted(validation.producer_receipts):
        source = validation.producer_receipt_paths[receipt_id]
        target = receipt_dir / f"{receipt_id}.json"
        shutil.copy2(source, target)
        packed_receipts.append(
            {"receipt_id": receipt_id, "path": str(target.relative_to(output_dir)), "sha256": sha256(target)}
        )
    bundle_receipt = {
        "schema_version": "bridge.fn01.final-generation-bundle.v1",
        "frozen_build_id": validation.frozen_build_id,
        "covered_actions": validation.covered_actions,
        "artifacts": packed,
        "producer_receipts": packed_receipts,
        "status": validation.report["status"],
        "semantics": validation.report["semantics"],
    }
    write_json(output_dir / "bundle-receipt.json", bundle_receipt)
    manifest_paths = sorted(
        path for path in output_dir.rglob("*")
        if path.is_file() and path.name not in {"closure-manifest.sha256", "generation-identity.json", "generation-identity.sha256"}
    )
    closure = output_dir / "closure-manifest.sha256"
    closure.write_text(
        "".join(f"{sha256(path)}  {path.relative_to(output_dir).as_posix()}\n" for path in manifest_paths),
        encoding="ascii",
    )
    identity = {
        "schema_version": "bridge.fn01.final-generation-identity.v1",
        "frozen_build_id": validation.frozen_build_id,
        "covered_actions": validation.covered_actions,
        "bundle_receipt_sha256": sha256(output_dir / "bundle-receipt.json"),
        "closure_manifest_sha256": sha256(closure),
        "status": validation.report["status"],
        "semantics": validation.report["semantics"],
    }
    identity["generation_digest"] = canonical_json_sha256(identity)
    identity["generation_id"] = f"Fn01.final-{identity['generation_digest'][:20]}"
    write_json(output_dir / "generation-identity.json", identity)
    (output_dir / "generation-identity.sha256").write_text(
        f"{sha256(output_dir / 'generation-identity.json')}  generation-identity.json\n",
        encoding="ascii",
    )
    return identity


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check")
    assemble = subparsers.add_parser("assemble")
    for child in (check, assemble):
        child.add_argument("--spec", type=Path, required=True)
        child.add_argument("--report", type=Path, required=True)
        child.add_argument("--request-eligible", action="store_true")
    assemble.add_argument("--output-dir", type=Path)
    assemble.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        validation = Controller(args.spec, args.request_eligible).validate()
        if args.command == "assemble" and not args.dry_run:
            if args.output_dir is None:
                raise ContractError("assemble requires --output-dir unless --dry-run")
            identity = pack(validation, args.output_dir)
            validation.report["packed_generation"] = identity
        elif args.command == "assemble" and args.output_dir is not None:
            raise ContractError("--output-dir is forbidden with --dry-run")
        write_json(args.report, validation.report)
    except Exception as error:
        failure = {
            "schema_version": "bridge.fn01.final-generation-check.v1",
            "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "spec": str(args.spec.resolve()),
            "status": {
                "validation_pass": False,
                "eligible_requested": bool(args.request_eligible),
                "eligible_for_deploy": False,
                "device_verified": False,
                "formal_verdict": "NOT_ISSUED",
            },
            "failure": f"{type(error).__name__}: {error}",
        }
        write_json(args.report, failure)
        print(f"REPORT={args.report.resolve()}")
        print("VALIDATION_PASS=false")
        print("ELIGIBLE_FOR_DEPLOY=false")
        print(f"FAILURE={failure['failure']}")
        return 1
    print(f"REPORT={args.report.resolve()}")
    print("VALIDATION_PASS=true")
    print(f"ELIGIBLE_FOR_DEPLOY={str(validation.eligible).lower()}")
    print("DEVICE_VERIFIED=false")
    print("FORMAL_VERDICT=NOT_ISSUED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
