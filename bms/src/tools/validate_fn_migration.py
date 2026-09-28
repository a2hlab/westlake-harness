#!/usr/bin/env python3
"""Deterministically validate the Lxx.Ayy to Fnxx.Ayy migration."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote

import yaml

import migrate_fn_atoms as migration


ROOT = Path(__file__).resolve().parents[1]
INDEPENDENT_REVIEW_NAME = "independent-fn-migration-review.md"
KIMI_REVIEW_NAME = "kimi-fn-migration-review.md"
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*]\(([^)]+)\)")


def atom_path_parts(atom_id: str) -> tuple[str, str]:
    """Return (fn_id, ayy) for an atom ID such as Fn08.A01."""
    fn_id, ayy = atom_id.split(".", 1)
    return fn_id, ayy


def generated_markdown_paths(fn_ids: list[str]) -> list[Path]:
    paths = [
        ROOT / "README.md",
        ROOT / "docs/atom.md",
        ROOT / "docs/README.md",
        ROOT / "docs/atoms/README.md",
        ROOT / "docs/spec/README.md",
        ROOT / "docs/spec/atoms/README.md",
        ROOT / "var/evidence/README.md",
        ROOT / "var/evidence/atoms/README.md",
        ROOT / "src/README.md",
        ROOT / "src/atoms/README.md",
        ROOT / "src/tools/README.md",
        ROOT / "docs/archive/legacy-lxx/MIGRATION_MAP.md",
    ]
    paths.extend(action_dir(ROOT / "docs/atoms", atom_id) / "README.md" for atom_id in fn_ids)
    return paths


def action_dir(base: Path, action_id: str) -> Path:
    """Resolve a stable Fnxx.Ayy ID into the canonical nested Action directory."""
    fn_id, action_suffix = action_id.split(".", 1)
    return base / fn_id / action_suffix


def broken_relative_links(paths: list[Path]) -> list[str]:
    broken = []
    for document in paths:
        if not document.is_file():
            broken.append(f"{document.relative_to(ROOT)}: document missing")
            continue
        content = document.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(content):
            target = raw_target.strip().strip("<>")
            if (
                not target
                or target.startswith(("#", "/", "http://", "https://", "mailto:"))
            ):
                continue
            target = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not target:
                continue
            resolved = (document.parent / target).resolve()
            if not resolved.exists():
                broken.append(
                    f"{document.relative_to(ROOT)} -> {raw_target}"
                )
    return broken


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-reviews",
        action="store_true",
        help="fail unless every Fn atom has a completed independent Kimi review",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "optionally write the JSON report outside docs/archive/; validation is "
            "stdout-only by default because archived migration evidence is read-only"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    atoms = migration.canonical_atoms()
    fn_map = migration.assign_fn_ids(atoms)
    report = migration.validate(atoms, fn_map)
    errors = list(report["errors"])
    by_legacy = {atom["legacy_id"]: atom for atom in atoms}

    for legacy_id, atom_id in sorted(fn_map.items()):
        source = by_legacy[legacy_id]
        metadata_path = action_dir(ROOT / "docs/spec/atoms", atom_id) / "atom.yaml"
        metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
        expected_domain = f"Fn{int(legacy_id[1:3]) - 1:02d}"
        if atom_id.split(".")[0] != expected_domain:
            errors.append(f"{legacy_id}: wrong Fn domain {atom_id}")
        if atom_id.split(".")[1] != legacy_id.split(".")[1]:
            errors.append(f"{legacy_id}: A suffix changed in {atom_id}")
        if metadata.get("title") != migration.active_title(source):
            errors.append(f"{atom_id}: active title differs from migration rule")
        override = migration.FUNCTION_SCOPE_OVERRIDES.get(legacy_id)
        if override and metadata.get("legacy_title") != source["title"]:
            errors.append(f"{atom_id}: narrowed scope lost the legacy title")
        if metadata.get("legacy_ids") != [legacy_id]:
            errors.append(f"{atom_id}: legacy ID provenance differs")
        if metadata.get("depends_on") != migration.translated_dependencies(
            source, fn_map
        ):
            errors.append(f"{atom_id}: dependency translation differs")
        for dependency in metadata.get("depends_on", []):
            legacy_dependency = dependency.get("legacy_id")
            if legacy_dependency == "L05.A01" and dependency.get(
                "journey_id"
            ) != "J01-first-frame-visible":
                errors.append(
                    f"{atom_id}: first-frame dependency is not mapped to its Journey ID"
                )

    fn_ids = sorted(fn_map.values())
    broken = broken_relative_links(generated_markdown_paths(fn_ids))
    errors.extend(f"broken generated link: {item}" for item in broken)

    reviewed = []
    missing_reviews = []
    review_verdicts = {"ACCEPT": 0, "NEEDS_CORRECTION": 0, "UNKNOWN": 0}
    for atom_id in fn_ids:
        fn_id, ayy = atom_path_parts(atom_id)
        path = (
            action_dir(ROOT / "docs/atoms", atom_id)
            / "veration-reviews"
            / INDEPENDENT_REVIEW_NAME
        )
        if not path.is_file() or path.stat().st_size <= 100:
            missing_reviews.append(atom_id)
            continue
        reviewed.append(atom_id)
        content = path.read_text(encoding="utf-8")
        verdict_match = re.search(
            r"^## Verdict\s*\n+\s*`?(ACCEPT|NEEDS_CORRECTION)`?\s*$",
            content,
            re.MULTILINE,
        )
        if not verdict_match:
            verdict_match = re.search(
                r"^- Verdict:\s*(?:\*\*|`)?(ACCEPT|NEEDS_CORRECTION)(?:\*\*|`)?\b",
                content,
                re.MULTILINE,
            )
        verdict = verdict_match.group(1) if verdict_match else "UNKNOWN"
        if verdict == "NEEDS_CORRECTION":
            review_verdicts["NEEDS_CORRECTION"] += 1
        elif verdict == "ACCEPT":
            review_verdicts["ACCEPT"] += 1
        else:
            review_verdicts["UNKNOWN"] += 1

    if args.require_reviews and missing_reviews:
        errors.append(
            f"independent Kimi reviews missing: {len(missing_reviews)} atoms"
        )

    kimi_review_count = sum(
        1
        for atom_id in fn_ids
        for fn_id, ayy in [atom_path_parts(atom_id)]
        if (
            action_dir(ROOT / "docs/atoms", atom_id)
            / "veration-reviews"
            / KIMI_REVIEW_NAME
        ).is_file()
    )

    report.update(
        {
            "ok": not errors,
            "semantic_mapping_verified": len(fn_ids),
            "generated_markdown_links_checked": len(
                generated_markdown_paths(fn_ids)
            ),
            "broken_generated_links": broken,
            "independent_reviews": {
                "complete": len(reviewed),
                "required": len(fn_ids),
                "missing": missing_reviews,
                "verdicts": review_verdicts,
            },
            "kimi_reviews": {
                "complete": kimi_review_count,
                "required": len(fn_ids),
                "note": (
                    "Separate resumable Kimi review; not substituted or fabricated "
                    "when the configured account is unavailable."
                ),
            },
            "errors": errors,
        }
    )
    if args.output:
        output = args.output if args.output.is_absolute() else ROOT / args.output
        output = output.resolve()
        archive_root = (ROOT / "archive").resolve()
        if output == archive_root or archive_root in output.parents:
            raise ValueError("validation output must not modify read-only docs/archive/")
        migration.write_text(
            output, json.dumps(report, ensure_ascii=False, indent=2)
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
