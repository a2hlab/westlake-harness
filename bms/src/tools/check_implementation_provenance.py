#!/usr/bin/env python3
"""Fail closed when a Bridge implementation is not project-derived and documented."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any

import yaml


SHA_RE = re.compile(r"^[0-9a-f]{64}$")
ACTION_RE = re.compile(r"^Fn(?:0[1-9]|1[0-2])\.A(?:0[1-9]|[1-9][0-9])$")
POLICY_ID = "BR-IMPLEMENTATION-PROVENANCE-1"
DERIVATION = "GENERATED_FROM_PROJECT_STRATEGY_AND_ACTION_DESIGN"
PAIRED_DOMAINS = ("spec", "docs", "implementation_handoff", "evidence", "progress")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_mapping(path: Path, label: str, failures: list[str]) -> dict[str, Any]:
    if not path.is_file():
        failures.append(f"missing {label}: {path}")
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as error:  # pragma: no cover - exercised by CLI callers
        failures.append(f"invalid {label} YAML: {error}")
        return {}
    if not isinstance(data, dict):
        failures.append(f"{label} root must be a mapping")
        return {}
    return data


def project_file(
    root: Path,
    value: object,
    field: str,
    failures: list[str],
    *,
    require_file: bool = True,
) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        failures.append(f"{field}: project-relative path is required")
        return None
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts:
        failures.append(f"{field}: path must be project-relative and cannot escape")
        return None
    candidate = root.joinpath(*pure.parts)
    try:
        candidate.resolve(strict=False).relative_to(root)
    except ValueError:
        failures.append(f"{field}: resolved path escapes project: {value}")
        return None
    if require_file and not candidate.is_file():
        failures.append(f"{field}: file does not exist: {value}")
    return candidate


def string_list(value: object, field: str, failures: list[str], *, allow_empty: bool) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        qualifier = "a list" if allow_empty else "a non-empty list"
        failures.append(f"{field} must be {qualifier}")
        return []
    if not all(isinstance(item, str) and item.strip() for item in value):
        failures.append(f"{field} entries must be non-empty strings")
        return []
    return list(value)


def validate_hash_bound_path(
    root: Path,
    provenance: dict[str, Any],
    path_key: str,
    hash_key: str,
    failures: list[str],
) -> Path | None:
    path = project_file(root, provenance.get(path_key), path_key, failures)
    expected = provenance.get(hash_key)
    if not isinstance(expected, str) or not SHA_RE.fullmatch(expected):
        failures.append(f"{hash_key} must be 64 lowercase hex")
    elif path is not None and path.is_file() and digest(path) != expected:
        failures.append(f"{hash_key} does not match current {path_key}")
    return path


def validate(root: Path, manifest_path: Path) -> list[str]:
    failures: list[str] = []
    root = root.resolve()
    try:
        manifest_path = manifest_path.resolve(strict=False)
        relative_manifest = manifest_path.relative_to(root).as_posix()
    except ValueError:
        return ["manifest resolved path escapes project"]

    project = load_mapping(root / "docs/spec/project.yaml", "project policy", failures)
    policy = project.get("implementation_provenance_policy")
    if not isinstance(policy, dict) or policy.get("policy_id") != POLICY_ID:
        failures.append(f"docs/spec/project.yaml must declare policy_id {POLICY_ID}")
    elif Path(str(policy.get("project_root", ""))).resolve() != root:
        failures.append("project policy root does not match --root")

    manifest = load_mapping(manifest_path, "implementation manifest", failures)
    action_id = manifest.get("action_id") or manifest.get("atom_id")
    if not isinstance(action_id, str) or not ACTION_RE.fullmatch(action_id):
        failures.append("implementation manifest requires a stable Fnxx.Ayy action_id")
        action_id = ""

    provenance = manifest.get("implementation_provenance")
    if not isinstance(provenance, dict):
        failures.append("implementation_provenance must be a mapping")
        provenance = {}
    if provenance.get("policy_id") != POLICY_ID:
        failures.append(f"implementation_provenance.policy_id must be {POLICY_ID}")
    if provenance.get("derivation") != DERIVATION:
        failures.append(f"implementation_provenance.derivation must be {DERIVATION}")
    if provenance.get("all_product_code_within_project") is not True:
        failures.append("all_product_code_within_project must be true")
    if provenance.get("external_code_as_implementation") is not False:
        failures.append("external_code_as_implementation must be false")
    if provenance.get("remote_source_import") is not False:
        failures.append("remote_source_import must be false")
    statement = provenance.get("derivation_statement")
    if not isinstance(statement, str) or len(statement.strip()) < 40:
        failures.append("derivation_statement must explain the project-owned derivation")
    string_list(provenance.get("use_case_ids"), "use_case_ids", failures, allow_empty=True)

    strategy = validate_hash_bound_path(
        root, provenance, "strategy_path", "strategy_sha256", failures
    )
    design = validate_hash_bound_path(
        root, provenance, "action_design_path", "action_design_sha256", failures
    )
    if strategy is not None:
        rel = strategy.relative_to(root).as_posix()
        if not (rel.startswith("docs/spec/concepts/") or rel.startswith("docs/concepts/")):
            failures.append("strategy_path must be in the project Concept docs/spec/docs domain")
    if design is not None and action_id:
        rel = design.relative_to(root).as_posix()
        fn_id, action_leaf = action_id.split(".", 1)
        accepted = {
            f"docs/spec/atoms/{fn_id}/{action_leaf}/DESIGN_SPEC.md",
            f"docs/spec/atoms/{action_id}/DESIGN_SPEC.md",
        }
        if rel not in accepted:
            failures.append("action_design_path does not belong to action_id")

    changed_files = string_list(
        manifest.get("changed_files"), "changed_files", failures, allow_empty=False
    )
    for index, value in enumerate(changed_files):
        project_file(root, value, f"changed_files[{index}]", failures)

    paired = provenance.get("paired_changes")
    if not isinstance(paired, dict):
        failures.append("implementation_provenance.paired_changes must be a mapping")
        paired = {}
    domain_paths: dict[str, list[str]] = {}
    for domain in PAIRED_DOMAINS:
        values = string_list(
            paired.get(domain), f"paired_changes.{domain}", failures, allow_empty=False
        )
        domain_paths[domain] = values
        for index, value in enumerate(values):
            project_file(root, value, f"paired_changes.{domain}[{index}]", failures)

    prefix_rules = {
        "spec": "docs/spec/",
        "docs": "docs/",
        "implementation_handoff": "src/atoms/",
        "evidence": "var/evidence/",
        "progress": "docs/progress.md",
    }
    for domain, prefix in prefix_rules.items():
        values = domain_paths.get(domain, [])
        if values and not any(value == prefix or value.startswith(prefix) for value in values):
            failures.append(f"paired_changes.{domain} does not contain a {prefix} path")
    if relative_manifest not in domain_paths.get("implementation_handoff", []):
        failures.append("paired_changes.implementation_handoff must include this manifest")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    manifest = Path(args.manifest)
    if not manifest.is_absolute():
        manifest = root / manifest
    failures = validate(root, manifest)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        print(f"IMPLEMENTATION_PROVENANCE_BLOCKED findings={len(failures)}")
        return 1
    print(f"IMPLEMENTATION_PROVENANCE_PASS manifest={manifest.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
