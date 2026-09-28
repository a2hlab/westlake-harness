#!/usr/bin/env python3
"""Generate the read-only Fn01-Fn12 operating-system object map."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

import build_fn_route_atlas


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = Path(__file__).resolve()
PROJECTION = ROOT / "src/tools/data/fn-os-object-projection.yaml"
TEMPLATE = ROOT / "src/tools/templates/fn-os-object-map.html"
CONCEPTS = ROOT / "docs/spec/concepts.yaml"
GRAPH = ROOT / "docs/spec/concept-graph.yaml"
DEFAULT_HTML = ROOT / "docs/boards/fn-os-object-map.html"
DEFAULT_DATA = ROOT / "docs/boards/fn-os-object-map.data.json"

LANES = ("android", "bridge", "openharmony")
DIRECTIONS = ("up", "down", "left", "right")
INVERSE_DIRECTION = {
    "up": "down",
    "down": "up",
    "left": "right",
    "right": "left",
}
FN_RE = re.compile(r"^(Fn\d{2})")


class ObjectMapError(RuntimeError):
    """Raised when the presentation projection is unsafe or malformed."""


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ObjectMapError(f"{path.relative_to(ROOT)} must contain a YAML object")
    return value


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def root_fn(node_id: str) -> str | None:
    match = FN_RE.match(node_id)
    return match.group(1) if match else None


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if slug:
        return slug
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]


def read_subconcepts(
    concept_id: str,
    graph_nodes: list[dict[str, Any]],
    source_files: set[Path],
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for node in graph_nodes:
        node_id = str(node.get("id", ""))
        if node.get("kind") != "SUBCONCEPT" or root_fn(node_id) != concept_id:
            continue
        readme = ROOT / f"docs/concepts/{node_id.replace('.', '/')}/README.md"
        name = node_id
        definition = ""
        source = ""
        if readme.exists():
            source_files.add(readme)
            text = readme.read_text(encoding="utf-8")
            heading = next(
                (line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("# ")),
                node_id,
            )
            name = re.sub(
                rf"^{re.escape(node_id)}\s*[·—-]?\s*",
                "",
                heading,
            ).strip() or node_id
            definition_match = re.search(
                r"##\s+定义\s*\n+(.*?)(?:\n\s*\n|\n##|\Z)",
                text,
                flags=re.DOTALL,
            )
            if definition_match:
                definition = re.sub(
                    r"\s+",
                    " ",
                    re.sub(r"[*`]", "", definition_match.group(1)),
                ).strip()
            source = str(readme.relative_to(ROOT))
        result.append(
            {
                "id": node_id,
                "name": name,
                "definition": definition,
                "source": source,
            }
        )
    return result


def local_graph_edges(
    concept_id: str,
    graph_edges: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    projection: dict[str, list[dict[str, Any]]] = {
        direction: [] for direction in DIRECTIONS
    }
    seen: set[tuple[str, str, str, str]] = set()

    for edge in graph_edges:
        from_id = str(edge.get("from", ""))
        to_id = str(edge.get("to", ""))
        from_fn = root_fn(from_id)
        to_fn = root_fn(to_id)
        if not from_fn or not to_fn or from_fn == to_fn:
            continue

        if from_fn == concept_id:
            direction = str(edge.get("direction", ""))
            neighbor = to_fn
            local_node = from_id
            remote_node = to_id
            relation = str(edge.get("relation", ""))
        elif to_fn == concept_id:
            source_direction = str(edge.get("direction", ""))
            direction = INVERSE_DIRECTION.get(source_direction, "")
            neighbor = from_fn
            local_node = to_id
            remote_node = from_id
            relation = f"inverse:{edge.get('relation', '')}"
        else:
            continue

        if direction not in DIRECTIONS:
            raise ObjectMapError(
                f"invalid graph direction {direction!r} on {from_id} -> {to_id}"
            )
        relation_base = relation.removeprefix("inverse:")
        key = (direction, neighbor, relation_base, str(edge.get("status", "")))
        if key in seen:
            continue
        seen.add(key)
        projection[direction].append(
            {
                "neighbor": neighbor,
                "local_node": local_node,
                "remote_node": remote_node,
                "relation": relation,
                "status": str(edge.get("status", "UNKNOWN")),
                "mechanism": str(edge.get("mechanism", "")),
                "transfer": str(edge.get("transfer", "")),
                "ordering": str(edge.get("ordering", "")),
                "failure_propagation": str(
                    edge.get("failure_propagation", "")
                ),
                "actions": [str(item) for item in edge.get("actions") or []],
                "evidence": [str(item) for item in edge.get("evidence") or []],
            }
        )

    for direction in DIRECTIONS:
        projection[direction].sort(
            key=lambda item: (
                item["neighbor"],
                item["relation"],
                item["local_node"],
            )
        )
    return projection


def validate_and_expand_objects(
    concept_id: str,
    lanes: dict[str, Any],
    column_ids: set[str],
    source_files: set[Path],
) -> dict[str, list[dict[str, str]]]:
    expanded: dict[str, list[dict[str, str]]] = {}
    object_ids: set[str] = set()
    for lane in LANES:
        objects = lanes.get(lane)
        if not isinstance(objects, list) or not objects:
            raise ObjectMapError(f"{concept_id} lane {lane} must be a non-empty list")
        expanded[lane] = []
        for item in objects:
            if not isinstance(item, dict):
                raise ObjectMapError(f"{concept_id} lane {lane} has a non-object item")
            column = str(item.get("column", ""))
            title = str(item.get("title", "")).strip()
            note = str(item.get("note", "")).strip()
            source = str(item.get("source", "")).strip()
            if column not in column_ids:
                raise ObjectMapError(
                    f"{concept_id} {lane} object {title!r} has invalid column {column!r}"
                )
            if not title or not note or not source:
                raise ObjectMapError(
                    f"{concept_id} {lane} object requires title, note and source"
                )
            source_path = ROOT / source
            if not source_path.exists():
                raise ObjectMapError(f"missing object source: {source}")
            source_files.add(source_path)
            object_id = f"{concept_id}.{lane}.{slugify(title)}"
            if object_id in object_ids:
                raise ObjectMapError(f"duplicate object id: {object_id}")
            object_ids.add(object_id)
            expanded[lane].append(
                {
                    "id": object_id,
                    "column": column,
                    "title": title,
                    "note": note,
                    "source": source,
                }
            )
    return expanded


def aggregate_source_digest(
    source_files: set[Path],
) -> tuple[str, list[dict[str, str]]]:
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


def build_object_map_data() -> dict[str, Any]:
    projection = load_yaml(PROJECTION)
    concepts_doc = load_yaml(CONCEPTS)
    graph = load_yaml(GRAPH)
    route_atlas = build_fn_route_atlas.build_atlas_data()

    columns = projection.get("columns")
    projection_concepts = projection.get("concepts")
    concepts = concepts_doc.get("concepts")
    graph_nodes = graph.get("nodes")
    graph_edges = graph.get("edges")
    if not all(
        isinstance(value, list)
        for value in (columns, concepts, graph_nodes, graph_edges)
    ):
        raise ObjectMapError("columns, concepts, graph nodes and graph edges must be lists")
    if not isinstance(projection_concepts, dict):
        raise ObjectMapError("projection concepts must be an object")

    column_ids = {str(column.get("id", "")) for column in columns}
    if len(column_ids) != len(columns) or not all(column_ids):
        raise ObjectMapError("column ids must be unique and non-empty")

    source_files: set[Path] = {
        GENERATOR,
        PROJECTION,
        TEMPLATE,
        CONCEPTS,
        GRAPH,
    }
    for item in route_atlas["source_manifest"]:
        route_source = ROOT / item["path"]
        if route_source.exists():
            source_files.add(route_source)

    route_by_id = {
        record["id"]: record
        for record in route_atlas["concepts"]
    }
    records: list[dict[str, Any]] = []
    for concept in concepts:
        concept_id = str(concept.get("concept_id", ""))
        config = projection_concepts.get(concept_id)
        if not isinstance(config, dict):
            raise ObjectMapError(f"missing presentation projection for {concept_id}")
        lanes = config.get("lanes")
        if not isinstance(lanes, dict):
            raise ObjectMapError(f"{concept_id} lanes must be an object")
        objects = validate_and_expand_objects(
            concept_id,
            lanes,
            column_ids,
            source_files,
        )
        records.append(
            {
                "id": concept_id,
                "name": str(concept.get("name", concept_id)),
                "status": str(concept.get("status", "UNKNOWN")),
                "action_count": int(concept.get("action_count", 0)),
                "story": str(config.get("story", "")).strip(),
                "objects": objects,
                "subconcepts": read_subconcepts(
                    concept_id,
                    graph_nodes,
                    source_files,
                ),
                "neighbors": local_graph_edges(concept_id, graph_edges),
                "route": {
                    "model": route_by_id[concept_id]["route_model"],
                    "status": route_by_id[concept_id]["decision"]["status"],
                    "binding": route_by_id[concept_id]["decision"][
                        "route_binding_status"
                    ],
                    "selected": route_by_id[concept_id]["decision"][
                        "effective_selected_route"
                    ],
                    "backup": route_by_id[concept_id]["decision"][
                        "effective_backup_route"
                    ],
                    "future_upgrade": route_by_id[concept_id]["decision"][
                        "future_upgrade_route"
                    ],
                    "proposed_route": route_by_id[concept_id]["decision"][
                        "proposed_route"
                    ],
                },
            }
        )

    expected_ids = [f"Fn{index:02d}" for index in range(1, 13)]
    actual_ids = [record["id"] for record in records]
    if actual_ids != expected_ids:
        raise ObjectMapError(
            f"expected ordered Fn01-Fn12, got {', '.join(actual_ids)}"
        )

    source_digest, source_manifest = aggregate_source_digest(source_files)
    object_count = sum(
        len(objects)
        for record in records
        for objects in record["objects"].values()
    )
    relationship_count = sum(
        len(edges)
        for record in records
        for edges in record["neighbors"].values()
    )
    return {
        "schema_version": "1.0",
        "kind": "FN_OS_OBJECT_MAP",
        "authority": "READ_ONLY_PRESENTATION_PROJECTION",
        "disclaimer": str(projection.get("disclaimer", "")),
        "source_digest": source_digest,
        "source_manifest": source_manifest,
        "columns": columns,
        "concepts": records,
        "summary": {
            "concept_count": len(records),
            "object_count": object_count,
            "relationship_count": relationship_count,
            "graph_status": str(graph.get("status", "UNKNOWN")),
            "evidenced_relationship_count": sum(
                edge["status"] == "EVIDENCED"
                for record in records
                for edges in record["neighbors"].values()
                for edge in edges
            ),
        },
    }


def render_html(data: dict[str, Any]) -> str:
    embedded = json.dumps(
        data,
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("<", "\\u003c")
    return (
        TEMPLATE.read_text(encoding="utf-8")
        .replace("__OBJECT_MAP_DATA__", embedded)
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
        data = build_object_map_data()
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
        return 0 if all(results) else 1
    except (ObjectMapError, OSError, yaml.YAMLError) as error:
        print(f"ERROR {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
