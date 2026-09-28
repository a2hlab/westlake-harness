#!/usr/bin/env python3
"""Incrementally check Fn01-Fn06 Concept domain documents.

Each run processes exactly one Fn and rotates to the next. Before scanning, it
checks whether the previously generated issue file for that Fn still contains
unchecked items; if so, the run is skipped to avoid burning tokens on
unprocessed work.

State is kept in docs/workflows/.fn01-fn06-doc-check-state.json.
Issue files are written to docs/workflows/fn01-fn06-doc-check/<Fn>-latest.md.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_CONCEPTS = ROOT / "docs" / "concepts"
SPEC_CONCEPTS = ROOT / "spec" / "concepts"
AUDITS_DIR = ROOT / "docs" / "audits"
WORKFLOWS_DIR = ROOT / "docs" / "workflows"
TEMPLATE_MENTORS = ROOT / "docs" / "templates" / ".template.mentors.md"
STATE_FILE = WORKFLOWS_DIR / ".fn01-fn06-doc-check-state.json"
ISSUE_DIR = WORKFLOWS_DIR / "fn01-fn06-doc-check"

FN_IDS = [f"Fn{i:02d}" for i in range(1, 7)]

CORE_DOCS = [
    ("CONCEPT_DOMAIN.md", "concept-domain", True),
    ("ANDROID_MODEL.md", "android-model", True),
    ("BRIDGE_CONTRACT.md", "bridge-contract", True),
    ("ACTION_MAP.md", "action-map", True),
    ("CONTEXT_MAP.md", "context-map", True),
    ("CASE_LEDGER.md", "case-ledger", True),
    ("OPENHARMONY_MODEL.md", "openharmony-model", False),
    ("PATTERN_CATALOG.md", "pattern-catalog", False),
    ("RESEARCH_QUESTIONS.md", "research-questions", False),
    ("ROUTE_SPACE.md", "route-space", False),
    ("STRATEGY.md", "strategy", False),
    ("STRATEGY_DECISION.md", "strategy-decision", False),
    ("REVIEW_LOG.md", "concept-review-log", False),
    ("CONCEPT_DESIGN.md", "concept-design", False),
]

SIGNATURE_RE = re.compile(r"^<!--\s*TEMPLATE-SIGNATURE:\s*([^\s>]+)\s*-->", re.MULTILINE)
UNCHECKED_RE = re.compile(r"^- \[ \]", re.MULTILINE)


def parse_signature_target(target: str) -> tuple[str | None, str | None]:
    if "#" in target:
        path, anchor = target.split("#", 1)
        return anchor, None
    filename = Path(target).name
    if filename.endswith("-template.md"):
        return filename[: -len("-template.md")], filename
    return None, filename


def load_mentor_anchors() -> set[str]:
    if not TEMPLATE_MENTORS.is_file():
        return set()
    text = TEMPLATE_MENTORS.read_text(encoding="utf-8")
    return set(re.findall(r"^##\s+([a-z0-9-]+)\s*$", text, re.MULTILINE))


def load_state() -> dict:
    if not STATE_FILE.is_file():
        return {"current_fn_index": 0, "cycle": 1}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"current_fn_index": 0, "cycle": 1}


def save_state(state: dict) -> None:
    WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def issue_file_for(fn_id: str) -> Path:
    return ISSUE_DIR / f"{fn_id}-latest.md"


def has_unchecked_items(path: Path) -> bool:
    if not path.is_file():
        return False
    return bool(UNCHECKED_RE.search(path.read_text(encoding="utf-8")))


def check_fn_docs(fn_id: str, mentor_anchors: set[str]) -> list[dict]:
    issues = []
    fn_dir = DOCS_CONCEPTS / fn_id
    if not fn_dir.is_dir():
        issues.append({
            "severity": "ERROR",
            "category": "missing_dir",
            "message": f"{fn_id} concept docs directory missing: {fn_dir}",
            "path": str(fn_dir),
        })
        return issues

    for filename, mentor, required in CORE_DOCS:
        path = fn_dir / filename
        if not path.is_file():
            severity = "ERROR" if required else "WARNING"
            issues.append({
                "severity": severity,
                "category": "missing_doc",
                "message": f"{fn_id}: missing {'required' if required else 'recommended'} document {filename}",
                "path": str(path),
            })
            continue

        text = path.read_text(encoding="utf-8", errors="replace")
        match = SIGNATURE_RE.search(text)
        if not match:
            issues.append({
                "severity": "ERROR",
                "category": "missing_signature",
                "message": f"{fn_id}/{filename}: missing TEMPLATE-SIGNATURE",
                "path": str(path),
            })
            continue

        target = match.group(1)
        anchor, _ = parse_signature_target(target)
        if anchor is None:
            issues.append({
                "severity": "ERROR",
                "category": "invalid_signature",
                "message": f"{fn_id}/{filename}: cannot parse template anchor from '{target}'",
                "path": str(path),
            })
        elif anchor not in mentor_anchors:
            issues.append({
                "severity": "ERROR",
                "category": "unknown_anchor",
                "message": f"{fn_id}/{filename}: unknown template mentor anchor '{anchor}'",
                "path": str(path),
            })
        elif anchor != mentor:
            issues.append({
                "severity": "WARNING",
                "category": "anchor_mismatch",
                "message": f"{fn_id}/{filename}: signature anchor '{anchor}' does not match expected mentor '{mentor}'",
                "path": str(path),
            })

    spec_dir = SPEC_CONCEPTS / fn_id
    if not spec_dir.is_dir():
        issues.append({
            "severity": "ERROR",
            "category": "missing_spec_dir",
            "message": f"{fn_id}: spec concept directory missing: {spec_dir}",
            "path": str(spec_dir),
        })

    return issues


def check_error_history(fn_id: str) -> list[dict]:
    issues = []
    if not AUDITS_DIR.is_dir():
        return issues
    pattern = re.compile(rf"\b{fn_id}\b", re.IGNORECASE)
    found_files = []
    for path in AUDITS_DIR.rglob("*.md"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if pattern.search(text):
            found_files.append(path)
    if not found_files:
        issues.append({
            "severity": "INFO",
            "category": "no_error_history",
            "message": f"{fn_id}: no related audit/error-history files found under docs/audits/",
            "path": str(AUDITS_DIR),
        })
    return issues


def write_issues(fn_id: str, issues: list[dict]) -> Path:
    ISSUE_DIR.mkdir(parents=True, exist_ok=True)
    path = issue_file_for(fn_id)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        f"# {fn_id} Concept Docs Check",
        "",
        f"Generated: {now}",
        "",
        "Mark items as `[x]` when addressed. The next hourly run will skip this Fn until all items are checked.",
        "",
    ]
    for issue in issues:
        lines.append(f"- [ ] [{issue['severity']}] {issue['category']}: {issue['message']}  ")
        lines.append(f"  path: `{issue['path']}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    state = load_state()
    fn_index = state.get("current_fn_index", 0) % len(FN_IDS)
    fn_id = FN_IDS[fn_index]
    issue_path = issue_file_for(fn_id)

    print("=" * 72)
    print(f"Fn01-Fn06 Incremental Docs Check")
    print(f"Target: {fn_id} (index {fn_index}, cycle {state.get('cycle', 1)})")
    print("=" * 72)

    if has_unchecked_items(issue_path):
        print(f"SKIP: {issue_path} still has unchecked items.")
        print("Please address them and mark `[x]` before the next run.")
        return 0

    mentor_anchors = load_mentor_anchors()
    issues = check_fn_docs(fn_id, mentor_anchors)
    issues.extend(check_error_history(fn_id))

    if issues:
        written = write_issues(fn_id, issues)
        print(f"Found {len(issues)} issue(s). Written to: {written}")
        for issue in issues:
            print(f"  [{issue['severity']}] {issue['category']}: {issue['message']}")
    else:
        print("OK: no issues found.")
        if issue_path.is_file():
            issue_path.unlink()
            print(f"Cleared previous issue file: {issue_path}")

    next_index = (fn_index + 1) % len(FN_IDS)
    state["current_fn_index"] = next_index
    if next_index == 0:
        state["cycle"] = state.get("cycle", 1) + 1
    state["last_run_at"] = datetime.now(timezone.utc).isoformat()
    state["last_checked_fn"] = fn_id
    save_state(state)

    print(f"Next target: {FN_IDS[next_index]}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
