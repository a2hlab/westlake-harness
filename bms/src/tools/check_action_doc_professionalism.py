#!/usr/bin/env python3
"""Audit Action docs against the professional template checklist.

Scans docs/atoms/Fn*/A*/README.md and reports missing required sections.
This is a read-only diagnostic; it does not modify files.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs" / "atoms"

REQUIRED_README_KEYWORDS = [
    ("Action 身份", "Action identity section"),
    ("Concept 上下文", "Concept context section"),
    ("四域导航", "Four-domain navigation"),
]

REQUIRED_SIDE_FILES = [
    ("AONB_INTEND.md", "AonB boundary intent document"),
    ("VERIFICATION_CONTRACT.md", "Verification contract document"),
]

OPTIONAL_BUT_RECOMMENDED = [
    ("REVIEW_LOG.md", "Review log"),
]


def list_actions() -> list[tuple[str, Path]]:
    actions = []
    for fn_dir in sorted(DOCS_DIR.glob("Fn*")):
        for ayy_dir in sorted(fn_dir.glob("A*")):
            atom_id = f"{fn_dir.name}.{ayy_dir.name}"
            actions.append((atom_id, ayy_dir))
    return actions


def audit_action(atom_id: str, ayy_dir: Path) -> dict:
    readme = ayy_dir / "README.md"
    readme_exists = readme.is_file()
    readme_text = readme.read_text(encoding="utf-8") if readme_exists else ""

    missing_readme = []
    for keyword, description in REQUIRED_README_KEYWORDS:
        if keyword not in readme_text:
            missing_readme.append({"keyword": keyword, "description": description})

    missing_files = []
    for filename, description in REQUIRED_SIDE_FILES:
        if not (ayy_dir / filename).is_file():
            missing_files.append({"file": filename, "description": description})

    missing_recommended = []
    for filename, description in OPTIONAL_BUT_RECOMMENDED:
        if not (ayy_dir / filename).is_file():
            missing_recommended.append({"file": filename, "description": description})

    # Heuristic: detect legacy language pollution outside legacy_ids block
    legacy_pollution = False
    if readme_exists:
        for line in readme_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("-") and "旧坐标" in stripped:
                continue
            if "Lxx.Ayy" in line or "Lxx" in line:
                if "legacy_ids" not in line and "旧坐标" not in line:
                    legacy_pollution = True
                    break

    score = 100
    score -= len(missing_readme) * 25
    score -= len(missing_files) * 20
    score -= len(missing_recommended) * 5
    if legacy_pollution:
        score -= 10
    score = max(0, score)

    return {
        "atom_id": atom_id,
        "readme_exists": readme_exists,
        "missing_readme_sections": missing_readme,
        "missing_required_files": missing_files,
        "missing_recommended_files": missing_recommended,
        "legacy_pollution": legacy_pollution,
        "score": score,
    }


def main() -> int:
    actions = list_actions()
    reports = [audit_action(atom_id, ayy_dir) for atom_id, ayy_dir in actions]

    by_fn: dict[str, list[dict]] = {}
    for report in reports:
        fn_id = report["atom_id"].split(".")[0]
        by_fn.setdefault(fn_id, []).append(report)

    summary = {
        "total_actions": len(reports),
        "actions_with_missing_readme_sections": sum(
            1 for r in reports if r["missing_readme_sections"]
        ),
        "actions_missing_aonb_intend": sum(
            1 for r in reports if any(m["file"] == "AONB_INTEND.md" for m in r["missing_required_files"])
        ),
        "actions_missing_verification_contract": sum(
            1 for r in reports if any(m["file"] == "VERIFICATION_CONTRACT.md" for m in r["missing_required_files"])
        ),
        "actions_with_legacy_pollution": sum(1 for r in reports if r["legacy_pollution"]),
        "average_score": round(sum(r["score"] for r in reports) / len(reports), 1) if reports else 0,
        "per_domain": {
            fn_id: {
                "count": len(domain_reports),
                "average_score": round(
                    sum(r["score"] for r in domain_reports) / len(domain_reports), 1
                ),
            }
            for fn_id, domain_reports in sorted(by_fn.items())
        },
        "details": reports,
    }

    output = ROOT / "docs/templates/action-doc-professionalism-audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
