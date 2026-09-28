#!/usr/bin/env python3
"""Generate the read-only Fn01-Fn12 technology route atlas.

Truth remains in the existing Concept artifacts:

* docs/spec/concepts.yaml
* docs/concepts/Fnxx/ROUTE_SPACE.md
* docs/concepts/Fnxx/STRATEGY_DECISION.md
* docs/spec/concepts/Fnxx/{concept,bridge-contract}.yaml
* src/atoms/Fnxx/Ayy/STATUS.yaml

The generator never selects or promotes a route.  It only projects an accepted
primary/backup pair when the decision status is ``accepted`` and the decision's
route-space hash still matches the current ROUTE_SPACE.md bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = Path(__file__).resolve()
TEMPLATE = ROOT / "src/tools/templates/fn-route-atlas.html"
DEFAULT_HTML = ROOT / "docs/boards/fn-route-atlas.html"
DEFAULT_DATA = ROOT / "docs/boards/fn-route-atlas.data.json"

ROUTE_ID_RE = re.compile(r"\bR\d+[a-z]?\b", re.IGNORECASE)
TABLE_SEPARATOR_RE = re.compile(
    r"^\s*\|(?:\s*:?-{3,}:?\s*\|)+\s*$"
)

COMPOSITE_MARKERS = (
    "不是整域互斥路线",
    "可在不同单元组合",
    "完整组合必须",
    "不是一个全域路线问题",
    "分别拥有状态与生命周期",
    "不是同一路线，不能绑定推荐",
)


class AtlasError(RuntimeError):
    """Raised for a malformed or semantically unsafe atlas input."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AtlasError(f"{path.relative_to(ROOT)} must contain a YAML object")
    return value


def parse_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise AtlasError(f"{path.relative_to(ROOT)} has no YAML frontmatter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise AtlasError(f"{path.relative_to(ROOT)} has unterminated frontmatter")
    value = yaml.safe_load(parts[1])
    if not isinstance(value, dict):
        raise AtlasError(f"{path.relative_to(ROOT)} frontmatter is not an object")
    return value


def clean_markdown(value: str) -> str:
    value = value.strip()
    value = re.sub(r"!\[[^\]]*]\([^)]*\)", "", value)
    value = re.sub(r"\[([^\]]+)]\([^)]*\)", r"\1", value)
    value = value.replace("`", "").replace("**", "").replace("__", "")
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return []
    return [clean_markdown(cell) for cell in stripped.strip("|").split("|")]


def route_display_name(first_cell: str, second_cell: str, route_ids: list[str]) -> str:
    remainder = first_cell
    for route_id in route_ids:
        remainder = re.sub(
            rf"\b{re.escape(route_id)}\b",
            "",
            remainder,
            flags=re.IGNORECASE,
        )
    remainder = re.sub(r"^[\s/·:—–-]+|[\s/·:—–-]+$", "", remainder)
    return remainder or second_cell or "未命名技术路径"


def extract_route_table(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    for index in range(len(lines) - 2):
        if not lines[index].lstrip().startswith("|"):
            continue
        if not TABLE_SEPARATOR_RE.match(lines[index + 1]):
            continue
        headers = split_table_row(lines[index])
        if not headers:
            continue
        first_header = headers[0].lower()
        if first_header not in {"route", "component", "路线", "路径"}:
            continue

        routes: list[dict[str, Any]] = []
        cursor = index + 2
        while cursor < len(lines) and lines[cursor].lstrip().startswith("|"):
            cells = split_table_row(lines[cursor])
            cursor += 1
            if not cells:
                continue
            route_ids = [match.upper() for match in ROUTE_ID_RE.findall(cells[0])]
            if not route_ids:
                continue
            route_id = " / ".join(route_ids)
            padded = cells + [""] * max(0, len(headers) - len(cells))
            fields = {
                headers[cell_index]: padded[cell_index]
                for cell_index in range(min(len(headers), len(padded)))
                if padded[cell_index]
            }
            routes.append(
                {
                    "id": route_id,
                    "route_ids": route_ids,
                    "name": route_display_name(
                        cells[0],
                        cells[1] if len(cells) > 1 else "",
                        route_ids,
                    ),
                    "fields": fields,
                }
            )
        if routes:
            return headers, routes

    raise AtlasError(
        f"{path.relative_to(ROOT)} has no route comparison Markdown table"
    )


def normalize_route(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized or normalized.upper() == "NONE":
        return None
    return normalized.upper()


def normalize_advisory(value: Any) -> Any:
    """Preserve non-authoritative route proposals without promoting them."""
    if value is None:
        return None
    if isinstance(value, dict):
        return {
            str(key): normalize_advisory(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [normalize_advisory(item) for item in value]
    normalized = str(value).strip()
    if not normalized or normalized.upper() == "NONE":
        return None
    return normalized


def infer_route_model(route_space_text: str) -> str:
    compact_text = re.sub(r"\s+", "", route_space_text)
    if any(re.sub(r"\s+", "", marker) in compact_text for marker in COMPOSITE_MARKERS):
        return "COMPOSITE_ROUTE_VECTOR"
    return "EXCLUSIVE_ROUTE"


def route_binding_status(expected: Any, actual: str) -> str:
    if expected is None:
        return "MISSING"
    expected_text = str(expected)
    if expected_text.startswith("UNBOUND_"):
        return "UNBOUND"
    if expected_text == actual:
        return "MATCH"
    return "HASH_DRIFT"


def aggregate_action_projection(concept_id: str) -> dict[str, Any]:
    statuses = sorted((ROOT / f"src/atoms/{concept_id}").glob("A*/STATUS.yaml"))
    code_statuses: Counter[str] = Counter()
    verification_stages: Counter[str] = Counter()
    code_refs: set[str] = set()
    adapter_refs: set[str] = set()
    evidence_refs: set[str] = set()

    for status_path in statuses:
        data = load_yaml(status_path)
        code = data.get("code") or {}
        verification = data.get("verification") or {}
        code_statuses[str(code.get("status", "UNDECLARED"))] += 1
        verification_stages[str(verification.get("stage", "UNDECLARED"))] += 1
        for ref in code.get("code_refs") or []:
            ref_text = str(ref)
            code_refs.add(ref_text)
            if ref_text.startswith("src/adapter/"):
                adapter_refs.add(ref_text)
        for ref in code.get("evidence_refs") or []:
            evidence_refs.add(str(ref))
        for ref in verification.get("evidence_refs") or []:
            evidence_refs.add(str(ref))

    return {
        "action_status_files": len(statuses),
        "code_statuses": dict(sorted(code_statuses.items())),
        "verification_stages": dict(sorted(verification_stages.items())),
        "code_ref_count": len(code_refs),
        "adapter_ref_count": len(adapter_refs),
        "adapter_refs": sorted(adapter_refs),
        "evidence_ref_count": len(evidence_refs),
    }


def concept_definition(concept_path: Path) -> str:
    if not concept_path.exists():
        return ""
    value = load_yaml(concept_path).get("definition", "")
    return re.sub(r"\s+", " ", str(value)).strip()


def build_concept_record(
    concept: dict[str, Any],
    source_files: set[Path],
) -> dict[str, Any]:
    concept_id = str(concept["concept_id"])
    concept_dir = ROOT / f"docs/concepts/{concept_id}"
    spec_dir = ROOT / f"docs/spec/concepts/{concept_id}"
    route_path = concept_dir / "ROUTE_SPACE.md"
    decision_path = concept_dir / "STRATEGY_DECISION.md"
    concept_path = spec_dir / "concept.yaml"
    contract_path = spec_dir / "bridge-contract.yaml"

    required = (route_path, decision_path)
    for path in required:
        if not path.exists():
            raise AtlasError(f"missing required input: {path.relative_to(ROOT)}")

    source_files.update(required)
    for optional in (concept_path, contract_path):
        if optional.exists():
            source_files.add(optional)

    route_text = route_path.read_text(encoding="utf-8")
    headers, routes = extract_route_table(route_path)
    decision = parse_frontmatter(decision_path)
    actual_route_hash = sha256_bytes(route_path.read_bytes())
    binding = route_binding_status(
        decision.get("route_space_sha256"),
        actual_route_hash,
    )
    decision_status = str(decision.get("status", "unknown"))
    declared_selected = normalize_route(decision.get("selected_route"))
    declared_backup = normalize_route(decision.get("backup_route"))

    accepted_and_bound = decision_status.lower() == "accepted" and binding == "MATCH"
    effective_selected = declared_selected if accepted_and_bound else None
    effective_backup = declared_backup if accepted_and_bound else None

    available_ids = {
        route_id
        for route in routes
        for route_id in route["route_ids"]
    }
    for role, route_id in (
        ("selected_route", effective_selected),
        ("backup_route", effective_backup),
    ):
        if route_id and route_id not in available_ids:
            raise AtlasError(
                f"{concept_id} {role}={route_id} is absent from "
                f"{route_path.relative_to(ROOT)}"
            )

    return {
        "id": concept_id,
        "name": str(concept.get("name", concept_id)),
        "action_count": int(concept.get("action_count", 0)),
        "concept_status": str(concept.get("status", "UNKNOWN")),
        "definition": concept_definition(concept_path),
        "route_model": infer_route_model(route_text),
        "route_model_is_projection": True,
        "route_headers": headers,
        "routes": routes,
        "decision": {
            "status": decision_status,
            "owner": str(decision.get("owner", "")),
            "date": str(decision.get("date", "")),
            "declared_selected_route": declared_selected,
            "declared_backup_route": declared_backup,
            "future_upgrade_route": normalize_route(
                decision.get("future_upgrade_route")
            ),
            "proposed_route": normalize_advisory(
                decision.get("proposed_route")
            ),
            "proposed_backup": normalize_advisory(
                decision.get("proposed_backup")
            ),
            "effective_selected_route": effective_selected,
            "effective_backup_route": effective_backup,
            "route_binding_status": binding,
            "expected_route_space_sha256": str(
                decision.get("route_space_sha256", "")
            ),
            "actual_route_space_sha256": actual_route_hash,
            "owner_decision_evidence": str(
                decision.get("owner_decision_evidence", "")
            ),
        },
        "projection": aggregate_action_projection(concept_id),
        "refs": {
            "route_space": str(route_path.relative_to(ROOT)),
            "strategy_decision": str(decision_path.relative_to(ROOT)),
            "concept": (
                str(concept_path.relative_to(ROOT)) if concept_path.exists() else ""
            ),
            "bridge_contract": (
                str(contract_path.relative_to(ROOT))
                if contract_path.exists()
                else ""
            ),
        },
    }


def aggregate_source_digest(source_files: set[Path]) -> tuple[str, list[dict[str, str]]]:
    manifest: list[dict[str, str]] = []
    digest = hashlib.sha256()
    for path in sorted(source_files):
        relative = str(path.relative_to(ROOT))
        file_hash = sha256_bytes(path.read_bytes())
        manifest.append({"path": relative, "sha256": file_hash})
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest(), manifest


def build_atlas_data() -> dict[str, Any]:
    concepts_path = ROOT / "docs/spec/concepts.yaml"
    source_files: set[Path] = {GENERATOR, concepts_path, TEMPLATE}
    concepts_doc = load_yaml(concepts_path)
    concepts = concepts_doc.get("concepts")
    if not isinstance(concepts, list):
        raise AtlasError("docs/spec/concepts.yaml concepts must be a list")

    records = [
        build_concept_record(concept, source_files)
        for concept in concepts
    ]
    concept_ids = [record["id"] for record in records]
    expected_ids = [f"Fn{index:02d}" for index in range(1, 13)]
    if concept_ids != expected_ids:
        raise AtlasError(
            f"expected ordered Fn01-Fn12, got {', '.join(concept_ids)}"
        )

    source_digest, source_manifest = aggregate_source_digest(source_files)
    return {
        "schema_version": "1.0",
        "kind": "FN_TECHNOLOGY_ROUTE_ATLAS",
        "authority": "READ_ONLY_PROJECTION",
        "source_digest": source_digest,
        "source_manifest": source_manifest,
        "concepts": records,
        "summary": {
            "concept_count": len(records),
            "route_count": sum(len(record["routes"]) for record in records),
            "accepted_route_decisions": sum(
                record["decision"]["status"].lower() == "accepted"
                and record["decision"]["route_binding_status"] == "MATCH"
                for record in records
            ),
            "hash_drift_count": sum(
                record["decision"]["route_binding_status"] == "HASH_DRIFT"
                for record in records
            ),
            "unbound_count": sum(
                record["decision"]["route_binding_status"] == "UNBOUND"
                for record in records
            ),
        },
    }


def render_html(data: dict[str, Any]) -> str:
    template = TEMPLATE.read_text(encoding="utf-8")
    embedded = json.dumps(
        data,
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("<", "\\u003c")
    return (
        template.replace("__ATLAS_DATA__", embedded)
        .replace("__SOURCE_DIGEST__", data["source_digest"])
    )


def check_or_write(path: Path, content: str, check: bool) -> bool:
    encoded = content.encode("utf-8")
    if check:
        if not path.exists():
            print(f"STALE missing {path.relative_to(ROOT)}", file=sys.stderr)
            return False
        if path.read_bytes() != encoded:
            print(f"STALE differs {path.relative_to(ROOT)}", file=sys.stderr)
            return False
        print(f"OK {path.relative_to(ROOT)}")
        return True

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)
    print(f"WROTE {path.relative_to(ROOT)}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if outputs are stale")
    parser.add_argument("--output", type=Path, default=DEFAULT_HTML)
    parser.add_argument("--data-output", type=Path, default=DEFAULT_DATA)
    args = parser.parse_args()

    try:
        data = build_atlas_data()
        html_output = render_html(data)
        json_output = json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n"
        results = (
            check_or_write(args.output.resolve(), html_output, args.check),
            check_or_write(args.data_output.resolve(), json_output, args.check),
        )
    except (AtlasError, OSError, yaml.YAMLError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1

    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
