#!/usr/bin/env python3
"""Import legacy Lxx.Axx material into the Bridge Fn atom namespace.

The legacy repositories are read-only inputs. This tool copies selected documents,
creates new metadata, and records a reversible mapping. It never deletes or rewrites
the source repositories.
"""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import shutil
from collections import OrderedDict
from pathlib import Path

import yaml


BRIDGE_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ROOT = Path(
    "/opt/15.WestLake/03new_Requirement/02.AtomFunctionGit/atoms"
)
LEGACY_DOC_ROOT = Path(
    "/opt/21.Game/02.unity.cardwords/adapter/research/atoms"
)

DOMAIN_META = OrderedDict(
    [
        ("Fn01", ("APK 安装与包元数据", "Legacy L02: APK install, metadata, paths and component resolution")),
        ("Fn02", ("进程、Runtime、JNI 与 Native", "Legacy L03: process, runtime, JNI, SO and ABI")),
        ("Fn03", ("Activity 生命周期", "Legacy L04: Activity lifecycle and OH state mapping")),
        ("Fn04", ("Window、Surface 与 Rendering", "Legacy L05: window, Surface, EGL and drawing")),
        ("Fn05", ("输入", "Legacy L06: input channel, conversion, dispatch, focus and ACK")),
        ("Fn06", ("Intent / Task", "Legacy L07: Intent/Want, launch, flags and task stack")),
        ("Fn07", ("Android Service", "Legacy L08: Service lifecycle and connection scope")),
        ("Fn08", ("权限 / 身份 / 沙箱", "Legacy L09: permission, token, SELinux and identity")),
        ("Fn09", ("Resource / ContentProvider", "Legacy L10: assets, resources, provider and DataShare")),
        ("Fn10", ("HWUI / Skia / Graphics JNI", "Legacy L11: graphics buffers, HWUI, Skia and JNI")),
        ("Fn11", ("系统服务 / Binder / Framework Native", "Legacy L12: services, Binder, broadcasts and natives")),
        ("Fn12", ("Logging / Trace API / 并发", "Functional subset of legacy L13")),
        ("Fn13", ("保留功能域", "Reserved for a future real functional domain")),
        ("Fn14", ("保留功能域", "Reserved for a future real functional domain")),
    ]
)

RESEARCH_SPEC_FILES = {
    "atom.yaml",
    "DESIGN_SPEC.md",
    "veration.md",
    "ATOM_VALIDATION.md",
}
RESEARCH_EVIDENCE_FILES = {
    "KANBAN_DATA.md",
    "COMPARISON_DATA.md",
    "INTEGRATION_CURSOR.json",
}
ACTIVE_ACTION_SPEC_FILES = {
    "ATOM_VALIDATION.md",
    "DESIGN_SPEC.md",
}
CANONICAL_SPEC_FILES = {
    "atom.yaml",
    "GAP.yaml",
    "REQUIREMENT.md",
    "DESIGN.md",
}
IGNORED_NAMES = {".DS_Store"}
INDEPENDENT_REVIEW_FILE = "independent-fn-migration-review.md"

FUNCTION_SCOPE_OVERRIDES = {
    "L09.A04": {
        "title": "APK signatures are verified and invalid signatures are rejected",
        "legacy_title": "APK signature verification policy is enforced or explicitly scoped",
        "scope_correction": (
            "Only observable signature verification and rejection remain in Fn; "
            "documentation or bypass-governance clauses are not functional acceptance."
        ),
        "behavior_contract": {
            "statement": (
                "The install path verifies APK signature metadata under the selected "
                "policy and returns an explicit compatible rejection for invalid or "
                "unacceptable signatures."
            )
        },
        "acceptance": [
            "An APK with an accepted valid signature proceeds through the signature gate.",
            "An invalid, missing, or unacceptable signature is rejected with an observable failure.",
        ],
    },
    "L09.A06": {
        "title": "Android permission checks return compatible allow or deny results in call order",
        "legacy_title": (
            "Android @EnforcePermission and permission checks preserve call ordering semantics"
        ),
        "scope_correction": (
            "Only observable permission allow/deny and ordering behavior remain in Fn; "
            "documentation and anti-silent-bypass rules remain quality gates."
        ),
        "behavior_contract": {
            "statement": (
                "At the Android-defined call point, the bridge evaluates caller identity "
                "and permission, permits authorized calls, and rejects unauthorized calls "
                "with compatible failure semantics."
            )
        },
        "acceptance": [
            "An authorized caller continues after the permission check at the required call point.",
            "An unauthorized caller is denied before the protected operation becomes observable.",
        ],
    },
}

MIGRATED_TEXT_REWRITES = {
    **{
        (atom_id, "L03_A15_CROSS_REFERENCE.md"): (
            (
                "../../L03/A15/UNITY_TLS_SELINUX_SPECIALIZATION_REQUIREMENTS_DESIGN.md",
                "../Fn02/A15/UNITY_TLS_SELINUX_SPECIALIZATION_REQUIREMENTS_DESIGN.md",
            ),
        )
        for atom_id in ("Fn01.A01", "Fn01.A07", "Fn01.A12", "Fn01.A13")
    },
    **{
        (atom_id, "L03_A15_CROSS_REFERENCE.md"): (
            (
                "../A15/UNITY_TLS_SELINUX_SPECIALIZATION_REQUIREMENTS_DESIGN.md",
                "../Fn02/A15/UNITY_TLS_SELINUX_SPECIALIZATION_REQUIREMENTS_DESIGN.md",
            ),
        )
        for atom_id in (
            "Fn02.A01",
            "Fn02.A02",
            "Fn02.A04",
            "Fn02.A12",
            "Fn02.A13",
            "Fn02.A14",
        )
    },
    ("Fn02.A06", "L03_A15_CROSS_REFERENCE.md"): (
        (
            "../A02/DESIGN_SPEC.md",
            "../../../../spec/atoms/Fn02/A02/DESIGN_SPEC.md",
        ),
    ),
    ("Fn02.A15", "UNITY_TLS_APERTURE_FIVE_STAGE_DESIGN.html"): (
        (
            'href="COMPARISON_DATA.md"',
            'href="../../../../evidence/atoms/Fn02/A15/COMPARISON_DATA.md"',
        ),
        (
            'href="../../../architecture-six-way/specs/L03-RUNTIME-NATIVE-BOUNDARY-SPEC.md"',
            'href="/opt/21.Game/02.unity.cardwords/adapter/research/architecture-six-way/specs/L03-RUNTIME-NATIVE-BOUNDARY-SPEC.md"',
        ),
    ),
}


def parse_coordinate(atom_id: str) -> tuple[int, int]:
    layer, atom = atom_id.split(".")
    return int(layer[1:]), int(atom[1:])


def classify(atom_id: str) -> tuple[str, str]:
    """Return (disposition, target)."""
    layer_number, atom_number = parse_coordinate(atom_id)

    if atom_id == "L05.A01":
        return "JOURNEY", "J01-first-frame-visible"
    if layer_number in {1, 14} or atom_id in {
        "L13.A01",
        "L13.A02",
        "L13.A07",
        "L13.A08",
        "L13.A11",
        "L13.A13",
    }:
        return "NON_FUNCTION", "cross-cutting-gates"

    if 2 <= layer_number <= 13:
        return "FUNCTION", f"Fn{layer_number - 1:02d}"

    raise ValueError(f"Unclassified canonical atom: {atom_id}")


def canonical_atoms() -> list[dict]:
    atoms = []
    for path in sorted(CANONICAL_ROOT.glob("L*/A*/atom.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        atom_id = data["atom_id"]
        disposition, target = classify(atom_id)
        atoms.append(
            {
                "legacy_id": atom_id,
                "title": " ".join(str(data.get("title", "")).split()),
                "data": data,
                "canonical_path": path,
                "legacy_doc_path": LEGACY_DOC_ROOT / atom_id.split(".")[0] / atom_id.split(".")[1],
                "disposition": disposition,
                "target": target,
            }
        )
    return atoms


def assign_fn_ids(atoms: list[dict]) -> dict[str, str]:
    return {
        atom["legacy_id"]: f"{atom['target']}.{atom['legacy_id'].split('.')[1]}"
        for atom in atoms
        if atom["disposition"] == "FUNCTION"
    }


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = content.rstrip() + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == normalized:
        return
    path.write_text(normalized, encoding="utf-8")


def copy_if_exists(source: Path, destination: Path) -> bool:
    if not source.is_file():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.read_bytes() == source.read_bytes():
        return True
    shutil.copy2(source, destination)
    return True


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def active_title(atom: dict) -> str:
    override = FUNCTION_SCOPE_OVERRIDES.get(atom["legacy_id"])
    return override["title"] if override else atom["title"]


def migrated_bytes(source: Path, destination: Path, atom_id: str) -> bytes:
    content = source.read_bytes()
    rewrites = MIGRATED_TEXT_REWRITES.get((atom_id, destination.name), ())
    if not rewrites:
        return content
    text = content.decode("utf-8")
    for old, new in rewrites:
        if old not in text:
            raise RuntimeError(
                f"{atom_id}: expected migration link not found in {source}: {old}"
            )
        text = text.replace(old, new)
    return text.encode("utf-8")


def copy_migrated_file(source: Path, destination: Path, atom_id: str) -> None:
    content = migrated_bytes(source, destination, atom_id)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.read_bytes() == content:
        return
    destination.write_bytes(content)


def is_active_action_contract(path: Path) -> bool:
    """Return true for migrated seeds that became live Action contracts."""
    try:
        relative = path.relative_to(BRIDGE_ROOT)
    except ValueError:
        return False
    return (
        len(relative.parts) == 5
        and relative.parts[0:2] == ("spec", "atoms")
        and relative.parts[2].startswith("Fn")
        and relative.parts[3].startswith("A")
        and relative.name in ACTIVE_ACTION_SPEC_FILES
    )


def research_destination(
    relative: Path,
    docs_dir: Path,
    spec_dir: Path,
    evidence_dir: Path,
) -> Path:
    """Route a historical research file without changing its historical name/tree."""
    if relative.name in IGNORED_NAMES:
        raise ValueError(f"ignored file has no destination: {relative}")
    if relative.parts[0] == "evidence":
        return evidence_dir.joinpath(*relative.parts[1:])
    if relative.name == "atom.yaml" and len(relative.parts) == 1:
        # The canonical seed atom remains the provenance baseline.  The research
        # copy had the same historical name, so keep the already-established
        # unambiguous filename instead of silently merging two YAML documents.
        return spec_dir / "legacy-local-atom.yaml"
    if len(relative.parts) == 1 and relative.name in RESEARCH_SPEC_FILES:
        return spec_dir / relative.name
    if len(relative.parts) == 1 and relative.name in RESEARCH_EVIDENCE_FILES:
        return evidence_dir / relative.name
    return docs_dir / relative


def canonical_destination(
    relative: Path,
    docs_dir: Path,
    spec_dir: Path,
    evidence_dir: Path,
) -> Path:
    """Route the canonical seed files using their historical filenames."""
    if relative.name in IGNORED_NAMES:
        raise ValueError(f"ignored file has no destination: {relative}")
    if relative.parts[0] == "evidence":
        return evidence_dir.joinpath(*relative.parts[1:])
    if relative.name == "atom.yaml" and len(relative.parts) == 1:
        return spec_dir / "legacy-atom.yaml"
    if len(relative.parts) == 1 and relative.name in CANONICAL_SPEC_FILES:
        return spec_dir / relative.name
    return docs_dir / relative


def archived_research_destination(relative: Path, target: Path) -> Path:
    if relative == Path("atom.yaml"):
        return target / "legacy-local-atom.yaml"
    return target / relative


def copy_historical_tree(
    source_dir: Path,
    destination_for,
    atom_id: str | None = None,
) -> list[tuple[Path, Path]]:
    """Copy every historical file, preserving names and nested directories."""
    copied = []
    if not source_dir.is_dir():
        return copied
    for source in sorted(path for path in source_dir.rglob("*") if path.is_file()):
        relative = source.relative_to(source_dir)
        if source.name in IGNORED_NAMES:
            continue
        destination = destination_for(relative)
        if atom_id and not (
            destination.exists() and is_active_action_contract(destination)
        ):
            copy_migrated_file(source, destination, atom_id)
        elif not atom_id:
            copy_if_exists(source, destination)
        copied.append((source, destination))
    return copied


def remove_generated_projection_readme(path: Path, marker: str) -> None:
    """Remove only first-round generated boilerplate, never user-authored files."""
    if not path.is_file():
        return
    content = path.read_text(encoding="utf-8")
    if marker not in content:
        raise RuntimeError(f"refusing to remove non-generated README: {path}")
    path.unlink()


def translated_dependencies(atom: dict, fn_map: dict[str, str]) -> list[dict]:
    result = []
    for dependency in atom["data"].get("depends_on_atoms") or []:
        legacy_dependency = dependency.get("id")
        entry = {
            "required_state": dependency.get("required_state"),
            "reason": dependency.get("reason"),
        }
        if legacy_dependency in fn_map:
            entry["atom_id"] = fn_map[legacy_dependency]
            entry["legacy_id"] = legacy_dependency
        elif legacy_dependency == "L05.A01":
            entry["journey_id"] = "J01-first-frame-visible"
            entry["legacy_id"] = legacy_dependency
        else:
            entry["external_gate"] = legacy_dependency
        result.append(entry)
    return result


def import_function_atom(atom: dict, new_id: str, fn_map: dict[str, str]) -> None:
    domain = new_id.split(".")[0]
    domain_name, domain_boundary = DOMAIN_META[domain]
    legacy_id = atom["legacy_id"]
    title = active_title(atom)
    legacy_source = atom["legacy_doc_path"]

    fn_id, ayy = new_id.split(".", 1)
    docs_dir = BRIDGE_ROOT / "docs/atoms" / fn_id / ayy
    spec_dir = BRIDGE_ROOT / "docs/spec/atoms" / fn_id / ayy
    evidence_dir = BRIDGE_ROOT / "var/evidence/atoms" / fn_id / ayy
    source_dir = BRIDGE_ROOT / "src/atoms" / fn_id / ayy
    for directory in (docs_dir, spec_dir, evidence_dir, source_dir):
        directory.mkdir(parents=True, exist_ok=True)

    canonical_atom_dir = atom["canonical_path"].parent
    canonical_copies = copy_historical_tree(
        canonical_atom_dir,
        lambda relative: canonical_destination(
            relative, docs_dir, spec_dir, evidence_dir
        ),
        new_id,
    )
    research_copies = copy_historical_tree(
        legacy_source,
        lambda relative: research_destination(
            relative, docs_dir, spec_dir, evidence_dir
        ),
        new_id,
    )
    (evidence_dir / "runs").mkdir(parents=True, exist_ok=True)
    evidence_keep = evidence_dir / "runs/.gitkeep"
    source_keep = source_dir / ".gitkeep"
    if not evidence_keep.exists():
        evidence_keep.touch()
    if not source_keep.exists():
        source_keep.touch()

    new_metadata = {
        "schema_version": "0.1",
        "atom_id": new_id,
        "kind": "FUNCTION_ATOM",
        "title": title,
        "domain": {
            "id": domain,
            "name": domain_name,
            "boundary": domain_boundary,
        },
        "legacy_ids": [legacy_id],
        "migration_status": "IMPORTED_UNREVIEWED",
        "capability_bits": "UNCLASSIFIED",
        "maturity": {
            "CM": "UNRATED",
            "VM": "UNRATED",
            "DM": "UNRATED",
        },
        "depends_on": translated_dependencies(atom, fn_map),
        "source_refs": {
            "canonical_atom": str(atom["canonical_path"]),
            "legacy_documents": str(legacy_source),
        },
    }
    if legacy_id in FUNCTION_SCOPE_OVERRIDES:
        new_metadata.update(FUNCTION_SCOPE_OVERRIDES[legacy_id])
    write_text(
        spec_dir / "atom.yaml",
        yaml.safe_dump(new_metadata, allow_unicode=True, sort_keys=False),
    )

    write_text(
        docs_dir / "README.md",
        f"""# {new_id} — {title}

- 功能域：{domain} / {domain_name}
- 旧坐标：`{legacy_id}`
- 迁移状态：`IMPORTED_UNREVIEWED`
- 成熟度：`CM UNRATED · VM UNRATED · DM UNRATED`

## 四域导航

- [Spec](../../../../spec/atoms/{fn_id}/{ayy}/)
- [Evidence](../../../../evidence/atoms/{fn_id}/{ayy}/)
- [Source](../../../../src/atoms/{fn_id}/{ayy}/)

## 导入材料

历史 canonical 目录：`{canonical_atom_dir}`

历史研究目录：`{legacy_source}`

本次按历史文件名和相对子目录增量搬迁，共核对：

- canonical seed 文件：{len(canonical_copies)}
- research 文件：{len(research_copies)}

这些文件是旧文档的可追溯副本。导入不代表内容已通过新 Fn 功能原子质量门。
""",
    )
    remove_generated_projection_readme(
        spec_dir / "README.md", f"# {new_id} specification"
    )
    remove_generated_projection_readme(
        evidence_dir / "README.md", f"# {new_id} evidence"
    )
    remove_generated_projection_readme(
        source_dir / "README.md", f"# {new_id} source ownership"
    )


def import_non_function(atom: dict) -> None:
    legacy_id = atom["legacy_id"]
    target = BRIDGE_ROOT / "docs/archive/legacy-lxx/non-function-atoms" / legacy_id
    target.mkdir(parents=True, exist_ok=True)
    copied = copy_historical_tree(
        atom["canonical_path"].parent,
        lambda relative: target / relative,
    )
    copied.extend(
        copy_historical_tree(
            atom["legacy_doc_path"],
            lambda relative: archived_research_destination(relative, target),
        )
    )
    write_text(
        target / "README.md",
        f"""# {legacy_id} — archived non-function item

- 标题：{atom["title"]}
- 处置：`NON_FUNCTION`
- 原因：该条目是架构原则、质量门或工作治理，不具备独立功能契约。
- 活跃规则：[`docs/architecture/cross-cutting-gates.md`](../../../../docs/architecture/cross-cutting-gates.md)
- 来源：`{atom["canonical_path"]}`
- 已复制：{len(copied)} 个历史文件，保持原文件名和相对子目录。

本目录是冻结历史，不分配 Fn ID。
""",
    )


def import_journey(atom: dict) -> None:
    target = BRIDGE_ROOT / "docs/spec/journeys/J01-first-frame-visible"
    legacy_target = target / "legacy"
    legacy_target.mkdir(parents=True, exist_ok=True)
    copied = copy_historical_tree(
        atom["canonical_path"].parent,
        lambda relative: legacy_target / relative,
    )
    copied.extend(
        copy_historical_tree(
            atom["legacy_doc_path"],
            lambda relative: archived_research_destination(
                relative, legacy_target
            ),
        )
    )
    write_text(
        target / "README.md",
        f"""# J01 — First frame visible

`{atom["legacy_id"]}` 串联 Activity、Window、Surface、Rendering 与 Resource 等多个
功能原子，是 Journey / Flow Anchor，不是单一 Fn atom。

- 旧标题：{atom["title"]}
- 来源：`{atom["canonical_path"]}`
- 历史副本：[`legacy/`](legacy/)
- 已复制：{len(copied)} 个历史文件，保持原文件名和相对子目录。

后续应在本目录维护 `covers_atoms`，而不是把首帧截图当作任一底层 atom 的 PASS。
""",
    )


def generate_maps(atoms: list[dict], fn_map: dict[str, str]) -> None:
    archive_root = BRIDGE_ROOT / "docs/archive/legacy-lxx"
    archive_root.mkdir(parents=True, exist_ok=True)
    rows = []
    for atom in sorted(atoms, key=lambda item: parse_coordinate(item["legacy_id"])):
        new_id = fn_map.get(atom["legacy_id"], "")
        rows.append(
            {
                "legacy_id": atom["legacy_id"],
                "new_id": new_id,
                "disposition": atom["disposition"],
                "target": atom["target"],
                "title": atom["title"],
                "canonical_path": str(atom["canonical_path"]),
                "legacy_document_path": str(atom["legacy_doc_path"]),
            }
        )

    csv_buffer = io.StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    write_text(archive_root / "MIGRATION_MAP.csv", csv_buffer.getvalue())

    table_rows = "\n".join(
        f"| `{row['legacy_id']}` | `{row['new_id'] or '—'}` | {row['disposition']} | "
        f"{row['target']} | {row['title'].replace('|', '/')} |"
        for row in rows
    )
    write_text(
        archive_root / "MIGRATION_MAP.md",
        f"""# Legacy Lxx → Fn migration map

生成工具：`src/tools/migrate_fn_atoms.py`

| 旧 ID | 新 ID | 处置 | 目标 | 标题 |
|---|---|---|---|---|
{table_rows}
""",
    )
    write_text(
        archive_root / "README.md",
        """# Legacy Lxx archive

- `MIGRATION_MAP.md`：人类可读映射。
- `MIGRATION_MAP.csv`：机器可读映射。
- `non-function-atoms/`：不再作为功能原子的架构原则、质量门与治理条目。

旧源仓库保持不动；本目录记录 Bridge 的可逆导入。
""",
    )


def generate_atom_index(atoms: list[dict], fn_map: dict[str, str]) -> None:
    by_legacy = {atom["legacy_id"]: atom for atom in atoms}
    lines = [
        "# Bridge Fn Atoms",
        "",
        "本索引只列功能原子。Journey、架构原则和质量门不占 Fn 编号。",
        "",
        "迁移仅建立新身份与旧材料副本；所有 CM/VM/DM 初始为 `UNRATED`。",
        "",
        "| Atom ID | 功能域 | 功能说明 | Legacy | Spec | Evidence | Source | 状态 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for legacy_id, new_id in sorted(fn_map.items(), key=lambda pair: pair[1]):
        atom = by_legacy[legacy_id]
        domain = new_id.split(".")[0]
        fn_id, ayy = new_id.split(".", 1)
        domain_name = DOMAIN_META[domain][0]
        lines.append(
            f"| `{new_id}` | {domain_name} | {active_title(atom).replace('|', '/')} | "
            f"`{legacy_id}` | [spec](../spec/atoms/{fn_id}/{ayy}/) | "
            f"[evidence](../evidence/atoms/{fn_id}/{ayy}/) | "
            f"[src](../src/atoms/{fn_id}/{ayy}/) | IMPORTED_UNREVIEWED |"
        )
    lines.extend(
        [
            "",
            "完整旧坐标处置见 [`docs/archive/legacy-lxx/MIGRATION_MAP.md`](../archive/legacy-lxx/MIGRATION_MAP.md)。",
        ]
    )
    write_text(BRIDGE_ROOT / "docs/atom.md", "\n".join(lines))


def generate_progress(atoms: list[dict], fn_map: dict[str, str]) -> None:
    counts = {domain: 0 for domain in DOMAIN_META}
    for new_id in fn_map.values():
        counts[new_id.split(".")[0]] += 1
    non_function_count = sum(atom["disposition"] == "NON_FUNCTION" for atom in atoms)
    journey_count = sum(atom["disposition"] == "JOURNEY" for atom in atoms)
    independent_review_count = sum(
        (
            BRIDGE_ROOT
            / "docs/atoms"
            / atom_id
            / "veration-reviews"
            / INDEPENDENT_REVIEW_FILE
        ).is_file()
        for atom_id in fn_map.values()
    )
    review_status = (
        "complete"
        if independent_review_count == len(fn_map)
        else "pending"
    )
    count_lines = "\n".join(
        f"- `{domain}` {DOMAIN_META[domain][0]}：{count} atoms"
        for domain, count in counts.items()
    )
    progress = f"""# Bridge Progress

## Current status

- Status: Fn namespace imported, independent review {review_status}
- Canonical legacy inventory: {len(atoms)}
- Fn function atoms: {len(fn_map)}
- Journeys: {journey_count}
- Non-function architecture/policy items: {non_function_count}
- Independent migration reviews: {independent_review_count} / {len(fn_map)}
- CM/VM/DM PASS automatically created by migration: 0

## Fn domain inventory

{count_lines}

## Next

1. Classify the eight capability bits from the functional contract, not from title keywords.
2. Promote migrated documents through DM quality gates.
3. Bind accepted implementation and device evidence before any CM/VM PASS.

## Board

- [`fn-maturity-board.html`](fn-maturity-board.html)
"""
    write_text(BRIDGE_ROOT / "docs/progress.md", progress)

    list_items = "".join(
        f"<li><code>{html.escape(domain)}</code> {html.escape(DOMAIN_META[domain][0])}: {count}</li>"
        for domain, count in counts.items()
    )
    progress_html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Bridge Progress</title>
</head>
<body>
  <!-- Generated view. Edit progress.md and rerun src/tools/migrate_fn_atoms.py. -->
  <main>
    <h1>Bridge Progress</h1>
    <p>Status: Fn namespace imported, independent review {review_status}</p>
    <ul>
      <li>Canonical legacy inventory: {len(atoms)}</li>
      <li>Fn function atoms: {len(fn_map)}</li>
      <li>Journeys: {journey_count}</li>
      <li>Non-function items: {non_function_count}</li>
      <li>Independent migration reviews: {independent_review_count} / {len(fn_map)}</li>
      <li>Migration-created PASS: 0</li>
    </ul>
    <h2>Fn domains</h2>
    <ul>{list_items}</ul>
    <p><a href="fn-maturity-board.html">Fn × APP maturity board</a></p>
  </main>
</body>
</html>
"""
    write_text(BRIDGE_ROOT / "docs/boards/progress.html", progress_html)


def validate(atoms: list[dict], fn_map: dict[str, str]) -> dict:
    domain_ids = {}
    for domain in DOMAIN_META:
        domain_ids[domain] = sorted(
            new_id for new_id in fn_map.values() if new_id.startswith(f"{domain}.")
        )

    projections = {}
    for projection in ("docs", "spec", "evidence", "src"):
        ids = sorted(
            f"{fn_dir.name}.{ayy_dir.name}"
            for fn_dir in (BRIDGE_ROOT / projection / "atoms").iterdir()
            if fn_dir.is_dir() and fn_dir.name.startswith("Fn")
            for ayy_dir in fn_dir.iterdir()
            if ayy_dir.is_dir() and ayy_dir.name.startswith("A")
        )
        projections[projection] = ids

    expected = sorted(fn_map.values())
    errors = []
    if len(atoms) != 167:
        errors.append(f"expected 167 canonical atoms, found {len(atoms)}")
    if len(fn_map) != 143:
        errors.append(f"expected 143 function atoms, found {len(fn_map)}")
    for projection, ids in projections.items():
        if ids != expected:
            errors.append(f"{projection}/atoms IDs differ from mapping")
    if len(set(fn_map.values())) != len(fn_map):
        errors.append("duplicate Fn IDs")

    imported_file_count = 0
    transformed_file_count = 0
    for new_id in expected:
        fn_id, ayy = new_id.split(".", 1)
        legacy_id = next(
            legacy for legacy, mapped in fn_map.items() if mapped == new_id
        )
        atom = next(item for item in atoms if item["legacy_id"] == legacy_id)
        docs_dir = BRIDGE_ROOT / "docs/atoms" / fn_id / ayy
        spec_dir = BRIDGE_ROOT / "docs/spec/atoms" / fn_id / ayy
        evidence_dir = BRIDGE_ROOT / "var/evidence/atoms" / fn_id / ayy
        metadata = yaml.safe_load(
            (spec_dir / "atom.yaml").read_text(encoding="utf-8")
        )
        if metadata.get("atom_id") != new_id:
            errors.append(f"{new_id}: atom.yaml ID mismatch")
        if metadata.get("kind") != "FUNCTION_ATOM":
            errors.append(f"{new_id}: non-functional kind in Fn namespace")
        if metadata.get("maturity") != {
            "CM": "UNRATED",
            "VM": "UNRATED",
            "DM": "UNRATED",
        }:
            errors.append(f"{new_id}: migration must not promote maturity")
        for projection in ("spec", "evidence", "src"):
            if (BRIDGE_ROOT / projection / "atoms" / fn_id / ayy / "README.md").exists():
                errors.append(f"{new_id}: redundant {projection} README remains")

        expected_copies = []
        canonical_dir = atom["canonical_path"].parent
        for source in sorted(path for path in canonical_dir.rglob("*") if path.is_file()):
            relative = source.relative_to(canonical_dir)
            if source.name in IGNORED_NAMES:
                continue
            destination = canonical_destination(
                relative, docs_dir, spec_dir, evidence_dir
            )
            expected_copies.append((source, destination))
        research_dir = atom["legacy_doc_path"]
        if research_dir.is_dir():
            for source in sorted(
                path for path in research_dir.rglob("*") if path.is_file()
            ):
                relative = source.relative_to(research_dir)
                if source.name in IGNORED_NAMES:
                    continue
                destination = research_destination(
                    relative, docs_dir, spec_dir, evidence_dir
                )
                expected_copies.append((source, destination))

        imported_file_count += len(expected_copies)
        for source, destination in expected_copies:
            if not destination.is_file():
                errors.append(
                    f"{new_id}: missing historical file {destination.relative_to(BRIDGE_ROOT)}"
                )
            elif is_active_action_contract(destination):
                continue
            elif migrated_bytes(source, destination, new_id) != destination.read_bytes():
                errors.append(
                    f"{new_id}: changed historical copy {destination.relative_to(BRIDGE_ROOT)}"
                )
            elif MIGRATED_TEXT_REWRITES.get((new_id, destination.name)):
                transformed_file_count += 1

    archived_file_count = 0
    for atom in atoms:
        if atom["disposition"] == "FUNCTION":
            continue
        if atom["disposition"] == "JOURNEY":
            target = (
                BRIDGE_ROOT
                / "docs/spec/journeys/J01-first-frame-visible/legacy"
            )
        else:
            target = (
                BRIDGE_ROOT
                / "docs/archive/legacy-lxx/non-function-atoms"
                / atom["legacy_id"]
            )

        expected_copies = []
        canonical_dir = atom["canonical_path"].parent
        for source in sorted(path for path in canonical_dir.rglob("*") if path.is_file()):
            relative = source.relative_to(canonical_dir)
            if source.name in IGNORED_NAMES:
                continue
            expected_copies.append((source, target / relative))
        research_dir = atom["legacy_doc_path"]
        if research_dir.is_dir():
            for source in sorted(
                path for path in research_dir.rglob("*") if path.is_file()
            ):
                relative = source.relative_to(research_dir)
                if source.name in IGNORED_NAMES:
                    continue
                expected_copies.append(
                    (
                        source,
                        archived_research_destination(relative, target),
                    )
                )

        archived_file_count += len(expected_copies)
        for source, destination in expected_copies:
            if not destination.is_file():
                errors.append(
                    f"{atom['legacy_id']}: missing archived file "
                    f"{destination.relative_to(BRIDGE_ROOT)}"
                )
            elif sha256(source) != sha256(destination):
                errors.append(
                    f"{atom['legacy_id']}: changed archived copy "
                    f"{destination.relative_to(BRIDGE_ROOT)}"
                )

    return {
        "ok": not errors,
        "canonical_count": len(atoms),
        "function_atom_count": len(fn_map),
        "journey_count": sum(atom["disposition"] == "JOURNEY" for atom in atoms),
        "non_function_count": sum(atom["disposition"] == "NON_FUNCTION" for atom in atoms),
        "domains": {domain: len(ids) for domain, ids in domain_ids.items()},
        "projections": {name: len(ids) for name, ids in projections.items()},
        "functional_historical_files_verified": imported_file_count,
        "migration_link_rewrites_verified": transformed_file_count,
        "archived_historical_files_verified": archived_file_count,
        "historical_files_verified": imported_file_count + archived_file_count,
        "errors": errors,
    }


def main() -> int:
    atoms = canonical_atoms()
    fn_map = assign_fn_ids(atoms)

    for atom in atoms:
        if atom["disposition"] != "FUNCTION":
            continue
        new_id = fn_map[atom["legacy_id"]]
        fn_id, ayy = new_id.split(".", 1)
        metadata_path = BRIDGE_ROOT / "docs/spec/atoms" / fn_id / ayy / "atom.yaml"
        if not metadata_path.is_file():
            continue
        metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
        if (
            metadata.get("migration_status") == "IMPORTED_UNREVIEWED"
            and metadata.get("legacy_ids") != [atom["legacy_id"]]
        ):
            raise RuntimeError(
                f"{new_id}: existing metadata maps to a different legacy atom; "
                "refusing automatic replacement"
            )

    for atom in atoms:
        if atom["disposition"] == "FUNCTION":
            import_function_atom(atom, fn_map[atom["legacy_id"]], fn_map)
        elif atom["disposition"] == "JOURNEY":
            import_journey(atom)
        else:
            import_non_function(atom)

    generate_maps(atoms, fn_map)
    generate_atom_index(atoms, fn_map)
    generate_progress(atoms, fn_map)

    report = validate(atoms, fn_map)
    write_text(
        BRIDGE_ROOT / "docs/archive/legacy-lxx/MIGRATION_VALIDATION.json",
        json.dumps(report, ensure_ascii=False, indent=2),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
