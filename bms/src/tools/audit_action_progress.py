#!/usr/bin/env python3
"""Materialize conservative doc/code/verification progress in every Action."""

from __future__ import annotations

from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = PROJECT_ROOT / "spec" / "atoms"

DOC_CANDIDATES = (
    "README.md",
    "ATOM_PROFILE.md",
    "usecase.md",
    "routemap.md",
    "strategy.md",
    "STRATEGY_DECISION.md",
    "REVIEW_LOG.md",
)
SPEC_CANDIDATES = (
    "ATOM_VALIDATION.md",
    "veration.md",
    "verification.md",
    "DESIGN_SPEC.md",
)


def relative(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))


def action_id_from_atom(atom: object, atom_path: Path) -> str:
    if not isinstance(atom, dict):
        raise ValueError(f"atom metadata is not a mapping: {atom_path}")
    action_id = atom.get("atom_id") or atom.get("action_id")
    expected_id = f"{atom_path.parents[1].name}.{atom_path.parent.name}"
    if action_id != expected_id:
        raise ValueError(
            f"atom identity mismatch: {atom_path} -> {action_id!r}, expected {expected_id}"
        )
    return action_id


def preserve_existing_projection(
    existing: object, derived: dict[str, object]
) -> dict[str, object]:
    """Keep an authoritative projection; derive only when it is absent.

    STATUS.yaml may contain independently reviewed stages and evidence that a
    filesystem scan cannot reconstruct.  The audit is therefore allowed to
    initialize a missing projection, but never to replace an existing one.
    """
    return existing if isinstance(existing, dict) else derived


def load_kanban_counts(path: Path) -> dict[str, int]:
    counts = {"activities": 0, "proven": 0, "not_proven": 0, "failed": 0}
    if not path.is_file():
        return counts
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text:
        return counts
    data = yaml.safe_load(text.split("\n---\n", 1)[0][4:]) or {}
    for key in counts:
        value = data.get(key)
        counts[key] = len(value) if isinstance(value, list) else 0
    return counts


def document_progress(docs_dir: Path, spec_dir: Path) -> dict[str, object]:
    refs = [
        relative(path)
        for name in DOC_CANDIDATES
        if (path := docs_dir / name).is_file()
    ]
    design_path = spec_dir / "DESIGN_SPEC.md"
    if design_path.is_file():
        refs.append(relative(design_path))

    if design_path.is_file():
        stage = "DESIGN_DRAFT"
    elif (docs_dir / "STRATEGY_DECISION.md").is_file():
        stage = "DECISION_RECORDED"
    elif (docs_dir / "routemap.md").is_file() and (docs_dir / "strategy.md").is_file():
        stage = "ROUTE_DRAFT"
    elif refs:
        stage = "RESEARCH_PACKET"
    else:
        stage = "NOT_STARTED"

    migration_review = (
        docs_dir / "veration-reviews" / "independent-fn-migration-review.md"
    )
    review_status = "NOT_REVIEWED"
    review_refs: list[str] = []
    if migration_review.is_file():
        review_text = migration_review.read_text(encoding="utf-8")
        if "ACCEPT" in review_text:
            review_status = "MIGRATION_SCOPE_ACCEPTED"
            review_refs = [relative(migration_review)]

    return {
        "stage": stage,
        "artifact_refs": refs,
        "review_status": review_status,
        "review_refs": review_refs,
        "review_scope": (
            "L_TO_FN_MIGRATION_ONLY"
            if review_status == "MIGRATION_SCOPE_ACCEPTED"
            else "NONE"
        ),
    }


def verification_progress(
    spec_dir: Path, evidence_dir: Path, code: dict[str, object]
) -> dict[str, object]:
    spec_refs = [
        relative(path)
        for name in SPEC_CANDIDATES[:-1]
        if (path := spec_dir / name).is_file()
    ]
    kanban_path = evidence_dir / "KANBAN_DATA.md"
    historical_counts = load_kanban_counts(kanban_path)
    evidence_refs = [relative(kanban_path)] if any(historical_counts.values()) else []
    runtime_receipts = sorted(evidence_dir.glob("runs/*/RUN_RECEIPT.md"))
    evidence_refs.extend(relative(path) for path in runtime_receipts)

    goal_states: dict[str, dict[str, object]] = {}
    if code.get("status") == "RUNTIME_OBSERVED_PASS":
        for goal in code.get("goals", []):
            goal_states[str(goal)] = {
                "status": "POSITIVE_RUNTIME_OBSERVED",
                "evidence_refs": list(code.get("evidence_refs", [])),
                "review_status": "NOT_INDEPENDENTLY_VERIFIED",
            }

    if runtime_receipts:
        stage = "POSITIVE_RUNTIME_OBSERVED"
    elif evidence_refs:
        stage = "EVIDENCE_PRESENT_UNREVIEWED"
    elif spec_refs:
        stage = "SPEC_READY_UNEXECUTED"
    else:
        stage = "NOT_STARTED"

    return {
        "stage": stage,
        "spec_refs": spec_refs,
        "evidence_refs": evidence_refs,
        "goal_states": goal_states,
        "historical_counts": historical_counts,
        "review_status": "NOT_INDEPENDENTLY_VERIFIED",
    }


def main() -> int:
    atom_paths = sorted(SPEC_ROOT.glob("Fn*/A*/atom.yaml"))
    if not atom_paths:
        raise SystemExit("no stable Actions found under docs/spec/atoms")

    counts: dict[str, dict[str, int]] = {
        "documentation": {},
        "implementation": {},
        "verification": {},
    }
    for atom_path in atom_paths:
        atom = yaml.safe_load(atom_path.read_text(encoding="utf-8"))
        try:
            action_id = action_id_from_atom(atom, atom_path)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        fn_id, action_suffix = action_id.split(".")
        docs_dir = PROJECT_ROOT / "docs" / "atoms" / fn_id / action_suffix
        spec_dir = PROJECT_ROOT / "spec" / "atoms" / fn_id / action_suffix
        evidence_dir = PROJECT_ROOT / "evidence" / "atoms" / fn_id / action_suffix
        status_path = PROJECT_ROOT / "src" / "atoms" / fn_id / action_suffix / "STATUS.yaml"
        original_text = status_path.read_text(encoding="utf-8")
        status = yaml.safe_load(original_text)
        if status.get("action_id") != action_id:
            raise SystemExit(f"status identity mismatch: {status_path}")

        had_missing_projection = any(
            not isinstance(status.get(key), dict)
            for key in ("documentation", "code", "verification")
        )
        code = preserve_existing_projection(
            status.get("code"),
            {
                "status": "SOURCE_UNMAPPED",
                "summary": "尚未建立本 Action 到实现源码的可复核映射。",
            },
        )
        documentation = preserve_existing_projection(
            status.get("documentation"), document_progress(docs_dir, spec_dir)
        )
        verification = preserve_existing_projection(
            status.get("verification"),
            verification_progress(spec_dir, evidence_dir, code),
        )
        status["documentation"] = documentation
        status["code"] = code
        status["verification"] = verification
        if had_missing_projection:
            status_path.write_text(
                yaml.safe_dump(status, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

        for bucket, stage in (
            ("documentation", documentation["stage"]),
            ("implementation", code["status"]),
            ("verification", verification["stage"]),
        ):
            counts[bucket][stage] = counts[bucket].get(stage, 0) + 1

    print(yaml.safe_dump(counts, allow_unicode=True, sort_keys=True).strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
