#!/usr/bin/env python3
"""
Build authoritative self-contained HTML pages for each Bridge Concept Domain.

Reads structured YAML, Markdown, evidence, implementation, and review sources
under docs/spec/, docs/, var/evidence/, and src/, then produces:
  docs/authority/Fnxx.html      one page per Concept Domain
  docs/authority/index.html     catalog + cross-Concept map
  docs/authority/assets/        generated SVG diagrams and Gemini prompts

Usage:
    python3 src/tools/build-concept-authority-pages.py
    python3 src/tools/build-concept-authority-pages.py --concept Fn08
    python3 src/tools/build-concept-authority-pages.py --llm --gemini-key $KEY
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import markdown
import yaml

ROOT = Path(__file__).resolve().parent.parent
SPEC_CONCEPTS_DIR = ROOT / "spec" / "concepts"
DOCS_CONCEPTS_DIR = ROOT / "docs" / "concepts"
IMPROVED_DIR = ROOT / "docs" / "decisions" / "fnxx-strategies" / "improved-sources"
REVIEWS_DIR = ROOT / "docs" / "decisions" / "fnxx-strategies" / "reviews"
EVIDENCE_CONCEPTS_DIR = ROOT / "evidence" / "concepts"
EVIDENCE_ATOMS_DIR = ROOT / "evidence" / "atoms"
SRC_ATOMS_DIR = ROOT / "src" / "atoms"
SPEC_ATOMS_DIR = ROOT / "spec" / "atoms"
CONCEPT_GRAPH_FILE = ROOT / "spec" / "concept-graph.yaml"
CONCEPTS_YAML_FILE = ROOT / "spec" / "concepts.yaml"

OUTPUT_DIR = ROOT / "docs" / "authority"
ASSETS_DIR = OUTPUT_DIR / "assets"
CACHE_DIR = OUTPUT_DIR / ".cache"

ALL_FN = [f"Fn{n:02d}" for n in range(1, 13)]

# Files we look for in docs/concepts/Fnxx/ and improved-sources/Fnxx/
DOC_FILE_NAMES = [
    "CONCEPT_DOMAIN.md",
    "BRIDGE_CONTRACT.md",
    "ANDROID_MODEL.md",
    "OPENHARMONY_MODEL.md",
    "ROUTE_SPACE.md",
    "STRATEGY.md",
    "STRATEGY_DECISION.md",
    "ACTION_MAP.md",
    "RESEARCH_QUESTIONS.md",
    "CASE_LEDGER.md",
    "PATTERN_CATALOG.md",
    "SUBCONCEPT_MAP.md",
    "CONTEXT_MAP.md",
    "REVIEW_LOG.md",
    "D600_TEST_PLAN.md",
    "CURRENT_BRIDGE_AUDIT.md",
    "CONCEPT_DESIGN.md",
]

SUPPLEMENTAL_DOCS = {
    "Fn02": [
        (
            "FN02_ACTION_REPRODUCIBILITY.md",
            ROOT / "docs" / "workflows" / "FN02_ACTION_REPRODUCIBILITY.md",
        ),
        (
            "Fn02.A06.strategy.md",
            ROOT / "docs" / "atoms" / "Fn02" / "A06" / "strategy.md",
        ),
    ],
}

FN02_A06_ROUTE_RUN = (
    ROOT
    / "evidence"
    / "atoms"
    / "Fn02"
    / "A06"
    / "runs"
    / "20260728T123800Z-d600-policy-delta-r167"
)
FN02_A06_ROUTE_MANIFEST = FN02_A06_ROUTE_RUN / "RUN_MANIFEST.json"

YAML_FILE_NAMES = [
    "concept.yaml",
    "subconcepts.yaml",
    "action-map.yaml",
    "bridge-contract.yaml",
    "patterns.yaml",
    "cases.yaml",
    "research-queries.yaml",
    "implementation-order.yaml",
]


@dataclass
class ReviewAnnotation:
    role: str  # ieee | freshman
    round_num: int
    target_section: str
    concern: str
    verdict: str = ""
    raw_file: Path = field(default=Path())


@dataclass
class ConceptData:
    concept_id: str
    name: str = ""
    status: str = "IMPORTED_UNREVIEWED"
    action_count: int = 0
    yaml_data: Dict[str, Any] = field(default_factory=dict)
    docs: Dict[str, str] = field(default_factory=dict)
    improved: Dict[str, str] = field(default_factory=dict)
    reviews: List[ReviewAnnotation] = field(default_factory=list)
    evidence_files: List[Path] = field(default_factory=list)
    implementation_files: List[Path] = field(default_factory=list)
    spec_atom_files: List[Path] = field(default_factory=list)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    glossary: Dict[str, Dict[str, str]] = field(default_factory=dict)
    state_machine: Dict[str, Any] = field(default_factory=dict)
    data_structures: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    cases: List[Dict[str, Any]] = field(default_factory=list)
    routes: List[Dict[str, Any]] = field(default_factory=list)
    engineering: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


ALLOWED_HTML_TAGS = {
    "p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "strong", "em", "code", "pre", "a", "img",
    "table", "thead", "tbody", "tr", "th", "td", "blockquote",
    "div", "span", "sup", "sub", "del", "ins", "title", "head", "body", "html"
}


def _escape_unknown_tag(m: re.Match) -> str:
    raw = m.group(0)
    tag = raw.strip("</>").lower().split()[0]
    if tag in ALLOWED_HTML_TAGS:
        return raw
    return raw.replace("<", "&lt;").replace(">", "&gt;")


def sanitize_html(html_text: str) -> str:
    """Escape any tag not produced by markdown itself so source XML-like snippets don't break layout."""
    return re.sub(r"</?[a-zA-Z][a-zA-Z0-9_\-:]*[^>]*>", _escape_unknown_tag, html_text)


def md_to_html(text: str) -> str:
    if not text:
        return "<p class='empty'>（此文档当前为空或不存在）</p>"
    raw_html = markdown.markdown(text, extensions=["tables", "fenced_code", "toc"])
    return sanitize_html(raw_html)


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def find_first_paragraph(text: str) -> str:
    lines = text.splitlines()
    para = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            if para:
                break
            continue
        para.append(stripped)
        if len(para) >= 3:
            break
    return clean_text(" ".join(para))


def slugify(s: str) -> str:
    return re.sub(r"[^\w\-]", "-", s.lower()).strip("-")


# ---------------------------------------------------------------------------
# Source loading
# ---------------------------------------------------------------------------


class SourceLoader:
    def __init__(self, concept_id: str):
        self.cid = concept_id

    def load_yaml_files(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        base = SPEC_CONCEPTS_DIR / self.cid
        if not base.exists():
            return data
        for name in YAML_FILE_NAMES:
            path = base / name
            if path.exists():
                try:
                    data[name.replace(".yaml", "")] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                except Exception as e:
                    data[name.replace(".yaml", "")] = {"_parse_error": str(e)}
        return data

    def load_markdown_dir(self, base: Path) -> Dict[str, str]:
        result: Dict[str, str] = {}
        if not base.exists():
            return result
        for name in DOC_FILE_NAMES:
            path = base / name
            if path.exists():
                result[name] = path.read_text(encoding="utf-8")
        return result

    def _load_one_review(self, path: Path, role: str, rnd: int) -> List[ReviewAnnotation]:
        """Parse a single review file into annotated concerns."""
        annotations: List[ReviewAnnotation] = []
        text = path.read_text(encoding="utf-8")
        # Try to extract a verdict line near the top
        verdict = ""
        for line in text.splitlines()[:30]:
            if "Verdict" in line or "verdict" in line or "结论" in line:
                verdict = clean_text(line.split(":", 1)[-1])
                break
        # Extract section concerns: headings like "## N. Title"
        sections = re.split(r"\n##\s+", text)
        for sec in sections[1:]:
            title_match = re.match(r"(.+?)\n", sec)
            if not title_match:
                continue
            title = clean_text(title_match.group(1).replace("###", "").replace("##", ""))
            body = sec[title_match.end():].strip()
            # Take first non-empty paragraph as the concern summary
            first_para = find_first_paragraph(body)
            if not first_para or len(first_para) < 20:
                continue
            target_section = self._guess_target_section(title, body)
            annotations.append(
                ReviewAnnotation(
                    role=role,
                    round_num=rnd,
                    target_section=target_section,
                    concern=first_para[:600],
                    verdict=verdict,
                    raw_file=path,
                )
            )
        return annotations

    def load_reviews(self) -> List[ReviewAnnotation]:
        annotations: List[ReviewAnnotation] = []
        if not REVIEWS_DIR.exists():
            return annotations
        # Round-based reviews (modern naming)
        for role, label in [("ieee", "ieee"), ("freshman", "freshman")]:
            for rnd in [1, 2]:
                fname = f"{self.cid}-round{rnd}-{label}.md"
                path = REVIEWS_DIR / fname
                if path.exists():
                    annotations.extend(self._load_one_review(path, role, rnd))
        # Legacy / consolidated review files
        legacy_map = {
            "ieee": f"{self.cid}-ieee-editor-review.md",
            "freshman": f"{self.cid}-freshman-review.md",
        }
        for role, fname in legacy_map.items():
            path = REVIEWS_DIR / fname
            if path.exists():
                annotations.extend(self._load_one_review(path, role, 0))
        return annotations

    def _guess_target_section(self, title: str, body: str) -> str:
        title_lower = title.lower()
        mapping = {
            "source baseline": "android_model",
            "aosp": "android_model",
            "android model": "android_model",
            "openharmony": "openharmony_model",
            "oh model": "openharmony_model",
            "bridge contract": "bridge_contract",
            "concept design": "concept_design",
            "route": "route_space",
            "strategy": "strategy",
            "action": "action_map",
            "case": "case_ledger",
            "pattern": "pattern_catalog",
            "context": "context_map",
            "subconcept": "subconcept_map",
            "review log": "review_log",
            "spec_gap": "concept_domain",
            "jargon": "glossary",
            "terminology": "glossary",
        }
        for key, sec in mapping.items():
            if key in title_lower or key in body.lower():
                return sec
        return "general"

    def scan_evidence(self) -> List[Path]:
        base = EVIDENCE_CONCEPTS_DIR / self.cid
        files: List[Path] = []
        if base.exists():
            for p in sorted(base.rglob("*")):
                if p.is_file() and p.suffix in {".md", ".yaml", ".json", ".txt", ".log"}:
                    files.append(p.relative_to(ROOT))
        # Per-atom evidence
        atom_base = EVIDENCE_ATOMS_DIR
        if atom_base.exists():
            for atom_dir in sorted(atom_base.glob(f"{self.cid}.*")):
                for p in sorted(atom_dir.rglob("*")):
                    if p.is_file() and p.suffix in {".md", ".yaml", ".json", ".txt", ".log"}:
                        files.append(p.relative_to(ROOT))
        return files

    def scan_implementations(self) -> List[Path]:
        files: List[Path] = []
        if SRC_ATOMS_DIR.exists():
            for atom_dir in sorted(SRC_ATOMS_DIR.glob(f"{self.cid}.*")):
                for p in sorted(atom_dir.rglob("*")):
                    if p.is_file():
                        files.append(p.relative_to(ROOT))
        return files

    def scan_spec_atoms(self) -> List[Path]:
        files: List[Path] = []
        if SPEC_ATOMS_DIR.exists():
            for atom_dir in sorted(SPEC_ATOMS_DIR.glob(f"{self.cid}.*")):
                for p in sorted(atom_dir.rglob("*")):
                    if p.is_file():
                        files.append(p.relative_to(ROOT))
        return files

    def load(self) -> ConceptData:
        cd = ConceptData(concept_id=self.cid)
        cd.yaml_data = self.load_yaml_files()
        cd.docs = self.load_markdown_dir(DOCS_CONCEPTS_DIR / self.cid)
        for name, path in SUPPLEMENTAL_DOCS.get(self.cid, []):
            if path.exists():
                cd.docs[name] = path.read_text(encoding="utf-8")
        cd.improved = self.load_markdown_dir(IMPROVED_DIR / self.cid)
        cd.reviews = self.load_reviews()
        cd.evidence_files = self.scan_evidence()
        cd.implementation_files = self.scan_implementations()
        cd.spec_atom_files = self.scan_spec_atoms()
        return cd


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


class Extractor:
    def __init__(self, data: ConceptData, graph: Dict[str, Any]):
        self.data = data
        self.graph = graph

    def extract_name_and_status(self) -> None:
        # From concepts.yaml
        try:
            concepts_yaml = yaml.safe_load(CONCEPTS_YAML_FILE.read_text(encoding="utf-8")) or {}
        except Exception:
            concepts_yaml = {}
        for c in concepts_yaml.get("concepts", []):
            if c.get("concept_id") == self.data.concept_id:
                self.data.name = c.get("name", "")
                self.data.action_count = c.get("action_count", 0)
                break
        # From concept.yaml
        concept = self.data.yaml_data.get("concept", {}) or {}
        if not self.data.name:
            self.data.name = concept.get("name", "") or concept.get("title", "")
        self.data.status = concept.get("status", self.data.status)

    def extract_actions(self) -> None:
        action_map = self.data.yaml_data.get("action-map", {})
        if action_map:
            self.data.actions = action_map.get("actions", [])
        if not self.data.actions:
            # Fallback: parse ACTION_MAP.md table rows
            text = self.data.improved.get("ACTION_MAP.md") or self.data.docs.get("ACTION_MAP.md") or ""
            for line in text.splitlines():
                m = re.match(r"\|\s*(Fn\d{2}\.A\d{2})\s*\|", line)
                if m:
                    self.data.actions.append({"id": m.group(1), "title": line.split("|")[2].strip() if len(line.split("|")) > 2 else ""})

    def extract_glossary(self) -> None:
        """Build a simple glossary from bold terms and section headings."""
        terms: Dict[str, Dict[str, str]] = {}
        sources = [
            ("CONCEPT_DOMAIN.md", self.data.improved.get("CONCEPT_DOMAIN.md") or self.data.docs.get("CONCEPT_DOMAIN.md", "")),
            ("BRIDGE_CONTRACT.md", self.data.improved.get("BRIDGE_CONTRACT.md") or self.data.docs.get("BRIDGE_CONTRACT.md", "")),
            ("ANDROID_MODEL.md", self.data.improved.get("ANDROID_MODEL.md") or self.data.docs.get("ANDROID_MODEL.md", "")),
            ("OPENHARMONY_MODEL.md", self.data.improved.get("OPENHARMONY_MODEL.md") or self.data.docs.get("OPENHARMONY_MODEL.md", "")),
        ]
        for src_name, text in sources:
            # Collect bold terms and their sentence context
            for match in re.finditer(r"\*\*([^*\n]{3,40})\*\*", text):
                term = match.group(1).strip()
                if term in terms or len(term) < 3:
                    continue
                # Get a short context sentence
                start = max(0, match.start() - 80)
                end = min(len(text), match.end() + 120)
                context = clean_text(text[start:end])
                terms[term] = {"source": src_name, "context": context}
        self.data.glossary = terms

    def extract_state_machine(self) -> None:
        text = (
            self.data.improved.get("BRIDGE_CONTRACT.md")
            or self.data.docs.get("BRIDGE_CONTRACT.md", "")
            or self.data.improved.get("CONCEPT_DESIGN.md", "")
            or self.data.docs.get("CONCEPT_DESIGN.md", "")
        )
        sm: Dict[str, Any] = {"states": [], "transitions": [], "raw": ""}
        # Look for explicit state machine sections
        m = re.search(r"#+\s*状态机[\s\S]*?(?=\n#+|$)", text, re.IGNORECASE)
        if m:
            sm["raw"] = m.group(0)
        # Heuristic: lines like "- STATE -> EVENT -> STATE"
        transitions = []
        for line in text.splitlines():
            line = line.strip()
            if "->" in line and ("-" in line[:2] or "*" in line[:2]):
                parts = [p.strip() for p in line.strip("-* ").split("->")]
                if len(parts) >= 2:
                    transitions.append({"from": parts[0], "to": parts[-1], "trigger": " ".join(parts[1:-1]) if len(parts) > 2 else ""})
        sm["transitions"] = transitions
        states = set()
        for t in transitions:
            states.add(t["from"])
            states.add(t["to"])
        sm["states"] = sorted(states)
        self.data.state_machine = sm

    def extract_data_structures(self) -> None:
        """Extract tables with structure-like headers from model docs."""
        structs: List[Dict[str, Any]] = []
        for src_name in ["ANDROID_MODEL.md", "OPENHARMONY_MODEL.md", "BRIDGE_CONTRACT.md", "CONCEPT_DESIGN.md"]:
            text = self.data.improved.get(src_name) or self.data.docs.get(src_name, "")
            tables = re.findall(r"\|(.+?)\|\n\|(?:[-:| ]+\|)+\n((?:\|.+?\|\n?)+)", text)
            for header, rows in tables:
                cols = [c.strip() for c in header.split("|") if c.strip()]
                if any(k in cols for k in ["字段", "Field", "成员", "属性", "Attribute", "Name", "Type"]):
                    structs.append({"source": src_name, "columns": cols, "rows": rows.strip()})
        self.data.data_structures = structs

    def extract_relationships(self) -> None:
        rels: List[Dict[str, Any]] = []
        # From concept-graph.yaml (uses 'from'/'to', not 'source'/'target')
        edges = self.graph.get("edges", [])
        for edge in edges:
            src = edge.get("from", "")
            dst = edge.get("to", "")
            if self.data.concept_id in (src, dst):
                rels.append(
                    {
                        "source": src,
                        "target": dst,
                        "kind": edge.get("relation", edge.get("kind", "related")),
                        "mechanism": edge.get("mechanism", ""),
                        "evidence": edge.get("status", edge.get("evidence_status", "")),
                    }
                )
        # From CONTEXT_MAP.md table (modern 7-col or legacy 3-4 col)
        text = self.data.improved.get("CONTEXT_MAP.md") or self.data.docs.get("CONTEXT_MAP.md", "")
        for line in text.splitlines():
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if not parts or parts[0] not in ("up", "down", "left", "right"):
                continue
            direction = {"up": "前置依赖", "down": "消费者", "left": "运行时输入", "right": "运行时输出"}.get(parts[0], parts[0])
            # New format: direction | hypothesis | evidence-for | evidence-against | missing | falsifier | status
            if len(parts) >= 7:
                target = parts[1]
                mechanism = parts[2] if parts[2] not in ("无", "—", "-") else ""
                evidence = parts[6]
            elif len(parts) >= 3:
                target = parts[1]
                mechanism = parts[2]
                evidence = parts[3] if len(parts) > 3 else ""
            else:
                continue
            rels.append({"source": self.data.concept_id, "target": target, "kind": direction, "mechanism": mechanism, "evidence": evidence})
        self.data.relationships = rels

    def extract_cases(self) -> None:
        cases_yaml = self.data.yaml_data.get("cases", {})
        if cases_yaml and "cases" in cases_yaml:
            self.data.cases = cases_yaml["cases"]
            return
        text = self.data.improved.get("CASE_LEDGER.md") or self.data.docs.get("CASE_LEDGER.md", "")
        for line in text.splitlines():
            if line.strip().startswith("|") and "verified" in line.lower():
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 3:
                    self.data.cases.append({"id": parts[0], "description": parts[1], "status": parts[2]})

    def extract_routes(self) -> None:
        route_text = self.data.improved.get("ROUTE_SPACE.md") or self.data.docs.get("ROUTE_SPACE.md", "")
        decision_text = self.data.improved.get("STRATEGY_DECISION.md") or self.data.docs.get("STRATEGY_DECISION.md", "")
        routes: List[Dict[str, Any]] = []
        # Collect headings under ROUTE_SPACE as candidate routes
        for m in re.finditer(r"#+\s*(R\d+[a-z]*|[A-Z]\d+[a-z]*)[:：]\s*(.+?)(?=\n#+|$)", route_text, re.DOTALL):
            routes.append({"id": m.group(1), "name": clean_text(m.group(2).split("\n")[0]), "description": clean_text(m.group(2)), "selected": False})
        # Mark selected routes from STRATEGY_DECISION
        selected_ids = set(re.findall(r"(R\d+[a-z]*|[A-Z]\d+[a-z]*)", decision_text))
        for r in routes:
            if r["id"] in selected_ids:
                r["selected"] = True
        if not routes:
            # Fallback: any heading that looks like a route
            for m in re.finditer(r"#+\s*(.+?)\n+([^#\n].*?)(?=\n#+|$)", route_text, re.DOTALL):
                title = clean_text(m.group(1))
                if any(k in title for k in ["路线", "Route", "方案", "策略", "R"]):
                    routes.append({"id": slugify(title), "name": title, "description": clean_text(m.group(2)), "selected": False})
        self.data.routes = routes

    def extract_engineering(self) -> None:
        eng: Dict[str, List[Dict[str, Any]]] = {"design": [], "code": [], "tests": [], "device": [], "git": []}
        # Design: from CONCEPT_DESIGN and STRATEGY_DECISION
        for src in ["CONCEPT_DESIGN.md", "STRATEGY_DECISION.md", "STRATEGY.md"]:
            text = self.data.improved.get(src) or self.data.docs.get(src, "")
            if text:
                eng["design"].append({"source": src, "snippet": find_first_paragraph(text)})
        # Code: implementation files
        for p in self.data.implementation_files[:20]:
            suffix = p.suffix.lower()
            if suffix in {".java", ".c", ".cpp", ".h", ".py", ".js", ".ts"}:
                eng["code"].append({"path": str(p), "kind": suffix.lstrip(".")})
        # Tests: look for test dirs in evidence or src
        for p in self.data.implementation_files + self.data.evidence_files:
            sp = str(p)
            if "/test" in sp or "/tests" in sp or "_test" in sp or "unittest" in sp:
                eng["tests"].append({"path": sp})
        # Device runs: evidence files with run/date patterns
        for p in self.data.evidence_files:
            sp = str(p)
            if any(k in sp for k in ["device-runs", "D600", "runs/", "var/evidence/"]) and p.suffix in {".md", ".log", ".yaml", ".json"}:
                eng["device"].append({"path": sp})
        # Git: search for commit hashes in review logs or evidence
        git_text = " ".join((self.data.improved.get("REVIEW_LOG.md") or self.data.docs.get("REVIEW_LOG.md", "")).split())
        for h in re.findall(r"\b([0-9a-f]{7,40})\b", git_text):
            eng["git"].append({"hash": h, "context": "REVIEW_LOG.md"})
        self.data.engineering = eng

    def run(self) -> None:
        self.extract_name_and_status()
        self.extract_actions()
        self.extract_glossary()
        self.extract_state_machine()
        self.extract_data_structures()
        self.extract_relationships()
        self.extract_cases()
        self.extract_routes()
        self.extract_engineering()


# ---------------------------------------------------------------------------
# Narrative generator (rule-based professor voice)
# ---------------------------------------------------------------------------


class Narrator:
    PROFESSOR_OPENINGS = [
        "从教学角度审视，{concept} 的核心问题可以概括为：",
        "若将 {concept} 放在 AOSP-on-OpenHarmony 的整体架构中讲授，首先应指出：",
        "本 Concept 的讲授应当从以下事实出发：",
    ]

    def __init__(self, data: ConceptData):
        self.data = data

    def abstract(self) -> str:
        name = self.data.name or self.data.concept_id
        text = self.data.improved.get("CONCEPT_DOMAIN.md") or self.data.docs.get("CONCEPT_DOMAIN.md", "")
        first = find_first_paragraph(text)
        opening = self.PROFESSOR_OPENINGS[hash(self.data.concept_id) % len(self.PROFESSOR_OPENINGS)]
        lines = [
            opening.format(concept=name),
            first or f"{name} 的研究工作仍在进行中，当前以 `SPEC_GAP` 占位符为主。",
            "",
            f"本页汇总了 {self.data.action_count} 个 Action、{len(self.data.relationships)} 条周边关系、"
            f"{len(self.data.cases)} 个历史案例与 {len(self.data.routes)} 条候选技术路线。",
        ]
        return "\n".join(lines)

    def section_intro(self, section: str) -> str:
        templates = {
            "glossary": "以下术语表按首次出现文档编排，便于读者在跟进本 Concept 时快速定位关键概念。",
            "relationships": "理解本 Concept 不能孤立进行。下图与表格展示了它与周边 Concept 的依赖、消费与数据流向。",
            "state_machine": "状态机是判断实现是否正确的首要依据。下表列出当前文档中显式或隐式提到的状态与迁移。",
            "data_structures": "数据结构是 Bridge Contract 的静态骨架。以下表格摘自模型文档，展示了关键对象及其字段。",
            "cases": "历史案例是避免重复试错的基础。下面记录已验证、被拒绝或待验证的实例。",
            "routes": "技术路线的选择必须基于可证伪的假设。下列路线来自 ROUTE_SPACE 与 STRATEGY_DECISION。",
            "engineering": "从设计到真机验证的链条必须可审计。以下按设计、代码、测试、设备运行与 git 轨迹组织。",
            "reviews": "独立评审是防止自我确认偏误的关键环节。IEEE 编辑关注证据与逻辑，大一学生关注可读性与术语解释。",
        }
        return templates.get(section, "")

    def closing(self) -> str:
        return (
            "综上所述，本 Concept 的权威页面应被视为一个持续演化的教学与工程档案。"
            "所有 `SPEC_GAP` 与评审意见都明确标注，未关闭的 gap 不应被当作已验证结论引用。"
        )


# ---------------------------------------------------------------------------
# Diagram generator
# ---------------------------------------------------------------------------


class DiagramGenerator:
    def __init__(self, data: ConceptData):
        self.data = data
        self.cid = data.concept_id

    def relationship_mermaid(self) -> str:
        lines = ["graph TD"]
        seen = set()
        for rel in self.data.relationships[:12]:
            src = rel.get("source", "")
            dst = rel.get("target", "")
            if not src or not dst:
                continue
            key = tuple(sorted([src, dst]))
            if key in seen:
                continue
            seen.add(key)
            kind = rel.get("kind", "related")
            lines.append(f"    {src} -->|{kind}| {dst}")
        if len(lines) == 1:
            lines.append(f"    {self.cid}[{self.cid}]")
        return "\n".join(lines)

    def state_machine_mermaid(self) -> str:
        lines = ["stateDiagram-v2"]
        states = self.data.state_machine.get("states", [])
        if not states:
            lines.append(f"    [*] --> {self.cid}_pending")
            return "\n".join(lines)
        for t in self.data.state_machine.get("transitions", [])[:20]:
            trigger = t.get("trigger", "")
            label = f" : {trigger}" if trigger else ""
            lines.append(f"    {t['from']} --> {t['to']}{label}")
        return "\n".join(lines)

    def architecture_svg(self) -> str:
        """Produce a simple SVG data-flow diagram as fallback when Gemini is unavailable."""
        width, height = 600, 320
        mid = width // 2
        rows = [
            ("Android APK", mid, 60, "#3b82f6"),
            ("Bridge Boundary", mid, 160, "#8b5cf6"),
            ("OpenHarmony", mid, 260, "#10b981"),
        ]
        lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            f'<rect width="{width}" height="{height}" fill="#0f172a"/>',
        ]
        for label, x, y, color in rows:
            lines.append(f'<rect x="{x-90}" y="{y-25}" width="180" height="50" rx="8" fill="{color}" opacity="0.2" stroke="{color}" stroke-width="2"/>')
            lines.append(f'<text x="{x}" y="{y+5}" text-anchor="middle" fill="#f8fafc" font-size="14" font-family="sans-serif">{label}</text>')
        # Arrows
        lines.append(f'<line x1="{mid}" y1="85" x2="{mid}" y2="135" stroke="#94a3b8" stroke-width="2" marker-end="url(#arrow)"/>')
        lines.append(f'<line x1="{mid}" y1="185" x2="{mid}" y2="235" stroke="#94a3b8" stroke-width="2" marker-end="url(#arrow)"/>')
        lines.append('<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L9,3 z" fill="#94a3b8"/></marker></defs>')
        lines.append(f'<text x="{mid+10}" y="110" fill="#94a3b8" font-size="11">{self.cid}</text>')
        lines.append("</svg>")
        return "\n".join(lines)

    def gemini_prompt(self, prompt_type: str) -> str:
        name = self.data.name or self.cid
        if prompt_type == "relationship":
            return (
                f"Generate a clean, publication-style architecture diagram for '{name}' ({self.cid}) "
                f"showing how Android APK semantics map to OpenHarmony. Include nodes for: {', '.join(r['target'] for r in self.data.relationships[:6])}. "
                "Use a dark blue background, white text, and flat modern style. No words other than labels."
            )
        if prompt_type == "state_machine":
            states = ", ".join(self.data.state_machine.get("states", ["pending"]))
            return (
                f"Generate a state machine diagram for '{name}' ({self.cid}). States: {states}. "
                "Publication style, dark background, clear transitions."
            )
        return f"Generate an illustration for '{name}' ({self.cid}) in a technical publication style."

    def generate(self) -> Dict[str, Path]:
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        assets: Dict[str, Path] = {}
        # Mermaid text files
        rel_mmd = ASSETS_DIR / f"{self.cid}-relationship.mmd"
        rel_mmd.write_text(self.relationship_mermaid(), encoding="utf-8")
        assets["relationship_mmd"] = rel_mmd.relative_to(ROOT)

        sm_mmd = ASSETS_DIR / f"{self.cid}-state-machine.mmd"
        sm_mmd.write_text(self.state_machine_mermaid(), encoding="utf-8")
        assets["state_machine_mmd"] = sm_mmd.relative_to(ROOT)

        # SVG fallback architecture diagram
        svg_path = ASSETS_DIR / f"{self.cid}-architecture.svg"
        svg_path.write_text(self.architecture_svg(), encoding="utf-8")
        assets["architecture_svg"] = svg_path.relative_to(ROOT)

        # Gemini prompts
        for ptype in ["relationship", "state_machine", "overview"]:
            prompt_path = ASSETS_DIR / f"{self.cid}-gemini-prompt-{ptype}.txt"
            prompt_path.write_text(self.gemini_prompt(ptype), encoding="utf-8")
            assets[f"gemini_prompt_{ptype}"] = prompt_path.relative_to(ROOT)

        return assets


# ---------------------------------------------------------------------------
# HTML renderer
# ---------------------------------------------------------------------------


CSS = """
:root {
  --bg: #0f172a;
  --surface: #1e293b;
  --surface-2: #334155;
  --text: #f8fafc;
  --text-dim: #94a3b8;
  --accent: #38bdf8;
  --accent-2: #818cf8;
  --ok: #22c55e;
  --warn: #eab308;
  --danger: #ef4444;
  --neutral: #64748b;
  --ieee: #f87171;
  --freshman: #60a5fa;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.7;
}
header {
  background: var(--surface);
  border-bottom: 1px solid var(--surface-2);
  padding: 1.25rem 2rem;
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem;
}
header h1 { margin: 0; font-size: 1.25rem; color: var(--accent); }
header nav { display: flex; gap: 0.5rem; flex-wrap: wrap; }
header a {
  color: var(--text-dim);
  text-decoration: none;
  font-size: 0.9rem;
  border: 1px solid var(--surface-2);
  padding: 0.35rem 0.7rem;
  border-radius: 0.4rem;
}
header a:hover { color: var(--accent); border-color: var(--accent); }
main { padding: 2rem; max-width: 1100px; margin: 0 auto; }
main a { color: var(--accent); }
.professor-abstract {
  background: rgba(56, 189, 248, 0.08);
  border-left: 4px solid var(--accent);
  padding: 1.25rem 1.5rem;
  border-radius: 0 0.5rem 0.5rem 0;
  margin-bottom: 2rem;
  font-size: 1.05rem;
}
.professor-abstract p { margin: 0.5rem 0; }
h2 { color: var(--accent); margin-top: 2.5rem; border-bottom: 1px solid var(--surface-2); padding-bottom: 0.4rem; }
h3 { color: var(--accent-2); margin-top: 1.75rem; }
.status {
  display: inline-block;
  padding: 0.2rem 0.7rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.status.evidenced { background: rgba(34, 197, 94, 0.2); color: var(--ok); }
.status.partial { background: rgba(234, 179, 8, 0.2); color: var(--warn); }
.status.blocked { background: rgba(239, 68, 68, 0.2); color: var(--danger); }
.status.unassessed { background: rgba(100, 116, 139, 0.2); color: var(--neutral); }
.status.draft { background: rgba(56, 189, 248, 0.15); color: var(--accent); }
.status.researched_pending_human_decision { background: rgba(234, 179, 8, 0.15); color: var(--warn); }
.glossary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}
.glossary-card {
  background: var(--surface);
  border: 1px solid var(--surface-2);
  border-radius: 0.5rem;
  padding: 1rem;
}
.glossary-card dt { color: var(--accent); font-weight: 700; margin-bottom: 0.3rem; }
.glossary-card dd { margin: 0; color: var(--text-dim); font-size: 0.9rem; }
.glossary-card .source { font-size: 0.75rem; color: var(--neutral); margin-top: 0.5rem; }
table {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
  background: var(--surface);
  border-radius: 0.5rem;
  overflow: hidden;
}
th, td { padding: 0.65rem 0.9rem; text-align: left; border-bottom: 1px solid var(--surface-2); }
th { background: var(--surface-2); }
tr:hover { background: rgba(255,255,255,0.03); }
.diagram {
  background: var(--surface);
  border: 1px solid var(--surface-2);
  border-radius: 0.5rem;
  padding: 1rem;
  margin: 1rem 0;
  overflow-x: auto;
}
.diagram svg { max-width: 100%; height: auto; }
.diagram pre { margin: 0; color: var(--text-dim); }
.review-note {
  border-left: 4px solid;
  padding: 0.75rem 1rem;
  margin: 0.75rem 0;
  border-radius: 0 0.4rem 0.4rem 0;
  background: var(--surface);
}
.review-note.ieee { border-color: var(--ieee); }
.review-note.freshman { border-color: var(--freshman); }
.review-note .role { font-weight: 700; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }
.review-note.ieee .role { color: var(--ieee); }
.review-note.freshman .role { color: var(--freshman); }
.review-note p { margin: 0.3rem 0 0; color: var(--text-dim); font-size: 0.92rem; }
.section-intro { color: var(--text-dim); margin-bottom: 1rem; }
.evidence-identity {
  margin: 1rem 0;
  padding: 1rem;
  border: 1px solid var(--surface-2);
  border-left: 4px solid var(--accent-2);
  border-radius: 0.45rem;
  background: rgba(129, 140, 248, 0.08);
}
.evidence-identity h3 { margin-top: 0; }
.evidence-identity code { overflow-wrap: anywhere; }
.empty { color: var(--text-dim); font-style: italic; }
.spec-gap { color: var(--warn); font-weight: 600; }
.code-list, .file-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 0.35rem;
}
.code-list li, .file-list li {
  background: var(--surface);
  border: 1px solid var(--surface-2);
  border-radius: 0.35rem;
  padding: 0.45rem 0.7rem;
  font-size: 0.88rem;
  font-family: "SF Mono", Monaco, monospace;
}
.footer {
  margin-top: 4rem;
  padding-top: 1rem;
  border-top: 1px solid var(--surface-2);
  color: var(--text-dim);
  font-size: 0.85rem;
}
.badge {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 0.3rem;
  font-size: 0.75rem;
  margin-left: 0.5rem;
  background: var(--surface-2);
}
.mermaid { background: var(--surface); padding: 1rem; border-radius: 0.5rem; }
.source-doc-section { margin-bottom: 0.75rem; }
.source-toggle {
  width: 100%;
  background: var(--surface);
  border: 1px solid var(--surface-2);
  color: var(--text);
  padding: 0.8rem 1rem;
  border-radius: 0.5rem;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 1rem;
  text-align: left;
}
.source-toggle:hover { border-color: var(--accent); }
.source-toggle .icon { color: var(--accent); font-size: 1.2rem; }
.source-content {
  background: var(--surface);
  border: 1px solid var(--surface-2);
  border-top: none;
  border-radius: 0 0 0.5rem 0.5rem;
  padding: 1.25rem;
  display: none;
}
.source-content.active { display: block; }
.source-content h1, .source-content h2, .source-content h3 { color: var(--accent); margin-top: 1.25rem; }
.source-content p, .source-content li { color: #e2e8f0; }
.source-content code { background: var(--bg); padding: 0.15rem 0.35rem; border-radius: 0.25rem; }
.source-content pre { background: var(--bg); padding: 1rem; border-radius: 0.5rem; overflow-x: auto; }
@media (max-width: 700px) {
  .glossary-grid { grid-template-columns: 1fr; }
  header { flex-direction: column; align-items: flex-start; }
}
"""


def render_review_note(note: ReviewAnnotation) -> str:
    role_label = "IEEE 编辑" if note.role == "ieee" else "大一学生"
    return f"""
    <div class="review-note {note.role}">
      <div class="role">Round {note.round_num} · {role_label} · {html.escape(note.target_section)}</div>
      <p>{html.escape(note.concern)}</p>
      {f'<p><strong>结论：</strong>{html.escape(note.verdict)}</p>' if note.verdict else ''}
    </div>
    """


class HtmlRenderer:
    def __init__(self, data: ConceptData, assets: Dict[str, Path], narrator: Narrator):
        self.data = data
        self.assets = assets
        self.narrator = narrator

    def _section(self, title: str, section_key: str, body: str) -> str:
        intro = self.narrator.section_intro(section_key)
        return f"""
        <section id="{slugify(title)}">
          <h2>{title}</h2>
          {f'<p class="section-intro">{intro}</p>' if intro else ''}
          {body}
        </section>
        """

    def render_glossary(self) -> str:
        if not self.data.glossary:
            return self._section("术语表", "glossary", "<p class='empty'>未从源文档中提取到术语。</p>")
        cards = []
        for term, info in sorted(self.data.glossary.items())[:60]:
            cards.append(f"""
            <div class="glossary-card">
              <dt>{term}</dt>
              <dd>{html.escape(info['context'])}</dd>
              <div class="source">来源：{html.escape(info['source'])}</div>
            </div>
            """)
        body = f'<dl class="glossary-grid">{ "".join(cards) }</dl>'
        return self._section("术语表", "glossary", body)

    def render_relationships(self) -> str:
        if not self.data.relationships:
            body = "<p class='empty'>未提取到周边关系。</p>"
        else:
            rows = []
            for rel in self.data.relationships[:30]:
                rows.append(
                    f"<tr><td>{html.escape(str(rel.get('source', '')))}</td><td>{html.escape(str(rel.get('kind', '')))}</td>"
                    f"<td>{html.escape(str(rel.get('target', '')))}</td><td>{html.escape(str(rel.get('mechanism', '')))}</td>"
                    f"<td><span class='status unassessed'>{html.escape(str(rel.get('evidence', 'UNASSESSED')))}</span></td></tr>"
                )
            table = "<table><tr><th>Source</th><th>关系</th><th>Target</th><th>机制</th><th>证据状态</th></tr>" + "".join(rows) + "</table>"
            mmd_path = self.assets.get("relationship_mmd")
            mermaid_block = f"<pre class='mermaid'>{(ROOT / mmd_path).read_text(encoding='utf-8') if mmd_path else ''}</pre>" if mmd_path else ""
            body = f"""
            <div class="diagram">
              <h3>关系图（Mermaid）</h3>
              {mermaid_block}
            </div>
            {table}
            """
        return self._section("周边名词关系", "relationships", body)

    def render_state_machine(self) -> str:
        sm = self.data.state_machine
        if not sm.get("states") and not sm.get("transitions"):
            body = "<p class='empty'>未在源文档中定位到显式状态机。</p>"
        else:
            mmd_path = self.assets.get("state_machine_mmd")
            mermaid_block = f"<pre class='mermaid'>{(ROOT / mmd_path).read_text(encoding='utf-8') if mmd_path else ''}</pre>" if mmd_path else ""
            rows = "".join(
                f"<tr><td>{html.escape(str(t.get('from', '')))}</td><td>{html.escape(str(t.get('trigger', '')))}</td><td>{html.escape(str(t.get('to', '')))}</td></tr>"
                for t in sm.get("transitions", [])
            )
            table = "<table><tr><th>From</th><th>触发条件</th><th>To</th></tr>" + rows + "</table>" if rows else ""
            body = f"""
            <div class="diagram">
              <h3>状态机图（Mermaid）</h3>
              {mermaid_block}
            </div>
            {table}
            """
        return self._section("状态机", "state_machine", body)

    def render_data_structures(self) -> str:
        if not self.data.data_structures:
            body = "<p class='empty'>未提取到结构化数据表。</p>"
        else:
            blocks = []
            for s in self.data.data_structures[:10]:
                html_table = md_to_html(s["rows"])
                blocks.append(f"<h3>{s['source']}</h3>{html_table}")
            body = "\n".join(blocks)
        return self._section("数据结构", "data_structures", body)

    def render_cases(self) -> str:
        if not self.data.cases:
            body = "<p class='empty'>未提取到历史案例。</p>"
        else:
            rows = "".join(
                f"<tr><td>{html.escape(str(c.get('id', '')))}</td><td>{html.escape(str(c.get('description', '')))}</td><td>{html.escape(str(c.get('status', '')))}</td></tr>"
                for c in self.data.cases[:30]
            )
            body = "<table><tr><th>ID</th><th>描述</th><th>状态</th></tr>" + rows + "</table>"
        return self._section("历史案例", "cases", body)

    def render_routes(self) -> str:
        if not self.data.routes:
            body = "<p class='empty'>未提取到技术路线。</p>"
        else:
            rows = []
            for r in self.data.routes[:20]:
                sel = '<span class="badge status evidenced">已选</span>' if r.get("selected") else '<span class="badge">候选</span>'
                rows.append(f"<tr><td>{html.escape(str(r.get('id', '')))}{sel}</td><td>{html.escape(str(r.get('name', '')))}</td><td>{html.escape(str(r.get('description', '')))}</td></tr>")
            body = "<table><tr><th>ID</th><th>名称</th><th>描述</th></tr>" + "".join(rows) + "</table>"
        return self._section("技术路线与决策", "routes", body)

    def render_engineering(self) -> str:
        eng = self.data.engineering
        parts = []
        # Design
        if eng.get("design"):
            items = "".join(f"<li><strong>{html.escape(d['source'])}:</strong> {html.escape(d['snippet'])}</li>" for d in eng["design"])
            parts.append(f"<h3>设计</h3><ul>{items}</ul>")
        # Code
        if eng.get("code"):
            items = "".join(f"<li>{c['path']} <span class='badge'>{c['kind']}</span></li>" for c in eng["code"][:30])
            parts.append(f"<h3>代码实现</h3><ul class='code-list'>{items}</ul>")
        # Tests
        if eng.get("tests"):
            items = "".join(f"<li>{t['path']}</li>" for t in eng["tests"][:20])
            parts.append(f"<h3>单元测试 / 验证</h3><ul class='file-list'>{items}</ul>")
        # Device
        if eng.get("device"):
            items = "".join(f"<li>{d['path']}</li>" for d in eng["device"][:20])
            parts.append(f"<h3>真机测试结果</h3><ul class='file-list'>{items}</ul>")
        # Git
        if eng.get("git"):
            items = "".join(f"<li><code>{g['hash']}</code> from {g['context']}</li>" for g in eng["git"][:10])
            parts.append(f"<h3>Git 轨迹</h3><ul class='file-list'>{items}</ul>")
        if not parts:
            parts.append("<p class='empty'>未提取到工程轨迹。</p>")
        return self._section("工程轨迹", "engineering", "\n".join(parts))

    def render_reviews(self) -> str:
        ieee_notes = [n for n in self.data.reviews if n.role == "ieee"]
        freshman_notes = [n for n in self.data.reviews if n.role == "freshman"]

        def subsection(title: str, notes: List[ReviewAnnotation], placeholder: str) -> str:
            if notes:
                content = "\n".join(render_review_note(n) for n in notes)
            else:
                content = f"<p class='empty'>{placeholder}</p>"
            return f"<h3>{title}</h3>\n{content}"

        body = (
            subsection(
                "IEEE 编辑评审批注",
                ieee_notes,
                "暂无 IEEE 编辑评审批注。占位符保留，待后续评审补充。",
            )
            + "\n"
            + subsection(
                "大一学生评审批注",
                freshman_notes,
                "暂无大一学生评审批注。占位符保留，待后续评审补充。",
            )
        )
        return self._section("独立评审批注", "reviews", body)

    @staticmethod
    def _linkify_repo_paths(rendered: str) -> str:
        """Turn repo-root paths inside Markdown code spans into local links."""

        def replace(match: re.Match) -> str:
            path = html.unescape(match.group("path"))
            if not (ROOT / path).exists():
                return match.group(0)
            href = "../../" + path
            return (
                f'<a href="{html.escape(href, quote=True)}">'
                f"<code>{html.escape(path)}</code></a>"
            )

        return re.sub(
            r"<code>(?P<path>(?:docs|evidence|spec|src|tools)/[^<]+)</code>",
            replace,
            rendered,
        )

    def render_fn02_route_evidence_identity(self) -> str:
        if not FN02_A06_ROUTE_MANIFEST.exists():
            return (
                "<div class='evidence-identity'><strong>路线实证索引：</strong>"
                "<span class='status blocked'>BLOCKED</span> "
                "r167 RUN_MANIFEST.json 不存在，不能展示身份绑定。</div>"
            )
        try:
            manifest_bytes = FN02_A06_ROUTE_MANIFEST.read_bytes()
            manifest = json.loads(manifest_bytes)
        except (OSError, json.JSONDecodeError) as exc:
            return (
                "<div class='evidence-identity'><strong>路线实证索引：</strong>"
                "<span class='status blocked'>SPEC_GAP</span> "
                f"{html.escape(str(exc))}</div>"
            )

        device = manifest.get("device", {}) or {}
        artifacts = manifest.get("artifacts", {}) or {}
        limitations = manifest.get("evidence_limitations", []) or []
        manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
        relative_manifest = FN02_A06_ROUTE_MANIFEST.relative_to(ROOT).as_posix()
        limitation_items = "".join(
            f"<li>{html.escape(str(item))}</li>" for item in limitations
        )
        action_verdict = str(manifest.get("action_verdict", False)).lower()
        return f"""
        <div class="evidence-identity">
          <h3>r167 路线实证身份</h3>
          <table>
            <tr><th>设备 / boot</th><td><code>{html.escape(str(device.get("serial", "UNKNOWN")))}</code><br><code>{html.escape(str(device.get("boot_id", "UNKNOWN")))}</code></td></tr>
            <tr><th>环境</th><td>SELinux <code>{html.escape(str(device.get("selinux_mode", "UNKNOWN")))}</code> · policy v{html.escape(str(device.get("policy_version", "UNKNOWN")))}</td></tr>
            <tr><th>边界</th><td><code>{html.escape(str(manifest.get("claim_boundary", "UNKNOWN")))}</code></td></tr>
            <tr><th>实验结果</th><td><code>{html.escape(str(manifest.get("experiment_result", "UNKNOWN")))}</code></td></tr>
            <tr><th>正式结论</th><td><code>formal_verdict: {html.escape(str(manifest.get("formal_verdict", "NONE")))}</code> · <code>action_verdict: {action_verdict}</code></td></tr>
            <tr><th>证据封装</th><td>{len(artifacts)} 个 hash-bound artifacts</td></tr>
            <tr><th>Manifest 验证码</th><td><a href="../../{html.escape(relative_manifest, quote=True)}"><code>{manifest_sha}</code></a></td></tr>
          </table>
          <h4>证据限制</h4>
          <ul>{limitation_items}</ul>
        </div>
        """

    def render_reproducibility(self) -> str:
        if self.data.concept_id != "Fn02":
            return ""
        contract = self.data.docs.get("FN02_ACTION_REPRODUCIBILITY.md", "")
        strategy = self.data.docs.get("Fn02.A06.strategy.md", "")
        if not contract and not strategy:
            return ""

        problem_ledger = ""
        if strategy:
            match = re.search(
                r"^##\s+问题多路线回归[^\n]*\n(?P<body>[\s\S]*?)(?=^##\s|\Z)",
                strategy,
                re.MULTILINE,
            )
            if match:
                problem_ledger = (
                    "## Fn02.A06 当前问题与错误路线账本\n\n"
                    + match.group("body").strip()
                )

        parts = [
            "<p><a href='../workflows/FN02_ACTION_REPRODUCIBILITY.md'>"
            "打开 Markdown 真源：Fn02 Action 可复现记录合同</a></p>",
            self._linkify_repo_paths(md_to_html(contract)),
        ]
        if problem_ledger:
            parts.extend(
                [
                    "<hr>",
                    "<p><a href='../atoms/Fn02/A06/strategy.md'>"
                    "打开 Markdown 真源：Fn02.A06 strategy.md</a></p>",
                    self.render_fn02_route_evidence_identity(),
                    self._linkify_repo_paths(md_to_html(problem_ledger)),
                ]
            )
        return self._section(
            "Action 实现问题、路线选择与复现合同",
            "reproducibility",
            "\n".join(parts),
        )

    def render_source_documents(self) -> str:
        """Render all source Markdown files as collapsible sections."""
        docs: List[Tuple[str, str, str]] = []
        # Prefer improved sources, fallback to raw docs
        for name in DOC_FILE_NAMES:
            text = self.data.improved.get(name) or self.data.docs.get(name)
            if text:
                docs.append((name, "improved" if name in self.data.improved else "raw", text))
        # Also include review files
        for review in self.data.reviews:
            if review.raw_file and review.raw_file.exists():
                docs.append((review.raw_file.name, "review", review.raw_file.read_text(encoding="utf-8")))
        if not docs:
            return self._section("源文档库", "sources", "<p class='empty'>未找到源文档。</p>")
        panels = []
        for idx, (name, source_kind, text) in enumerate(docs):
            section_id = f"srcdoc-{self.data.concept_id}-{idx}"
            badge = f'<span class="badge">{source_kind}</span>'
            panels.append(f"""
            <div class="source-doc-section" id="{section_id}">
              <button class="source-toggle" onclick="toggleSource('{section_id}')">
                <span>{name} {badge}</span>
                <span class="icon">+</span>
              </button>
              <div class="source-content" id="{section_id}-content">
                {md_to_html(text)}
              </div>
            </div>
            """)
        body = "\n".join(panels)
        return self._section("源文档库", "sources", body)

    def render_diagrams_gallery(self) -> str:
        svg_path = self.assets.get("architecture_svg")
        body = f"""
        <div class="diagram">
          <h3>架构概览（本地 SVG）</h3>
          {(ROOT / svg_path).read_text(encoding='utf-8') if svg_path else '<p class="empty">无图</p>'}
        </div>
        <p class="section-intro">以下 Gemini prompt 文件可在外部 API 可用时生成更精美的示意图：</p>
        <ul class="file-list">
          <li>{self.assets.get('gemini_prompt_relationship', 'N/A')} — 关系图 prompt</li>
          <li>{self.assets.get('gemini_prompt_state_machine', 'N/A')} — 状态机 prompt</li>
          <li>{self.assets.get('gemini_prompt_overview', 'N/A')} — 总览 prompt</li>
        </ul>
        """
        return self._section("Gemini 图形", "diagrams", body)

    def render(self) -> str:
        generated_at = datetime.now().isoformat()
        status = self.data.status or "UNASSESSED"
        nav = "<nav>" + "".join(f'<a href="{fn}.html">{fn}</a>' for fn in ALL_FN) + "</nav>"
        sections = [
            self.render_source_documents(),
            self.render_reproducibility(),
            self.render_glossary(),
            self.render_relationships(),
            self.render_state_machine(),
            self.render_data_structures(),
            self.render_cases(),
            self.render_routes(),
            self.render_engineering(),
            self.render_reviews(),
            self.render_diagrams_gallery(),
        ]
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{self.data.concept_id} Authority — {self.data.name}</title>
  <style>{CSS}</style>
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});
  </script>
</head>
<body>
  <header>
    <h1>{self.data.concept_id} — {self.data.name} <span class="status {status.lower()}">{status}</span></h1>
    {nav}
  </header>
  <main>
    <section class="professor-abstract">
      <h2 style="margin-top:0;border:none;padding:0;">教授导读</h2>
      {md_to_html(self.narrator.abstract())}
    </section>
    {''.join(sections)}
    <section>
      <h2>结语</h2>
      <p>{self.narrator.closing()}</p>
    </section>
    <div class="footer">
      Generated at {generated_at} from docs/spec/, docs/, var/evidence/ and src/.<br>
      SPEC_GAP and uncited claims are preserved, not hidden.
    </div>
  </main>
  <script>
    function toggleSource(id) {{
      const content = document.getElementById(id + '-content');
      const icon = document.querySelector('#' + id + ' .icon');
      if (content.classList.contains('active')) {{
        content.classList.remove('active');
        icon.textContent = '+';
      }} else {{
        content.classList.add('active');
        icon.textContent = '−';
      }}
    }}
  </script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Index renderer
# ---------------------------------------------------------------------------


def render_index(all_data: List[ConceptData]) -> str:
    rows = []
    for d in all_data:
        status = d.status or "UNASSESSED"
        rows.append(
            f"<tr><td><a href='{d.concept_id}.html'>{d.concept_id}</a></td>"
            f"<td>{d.name}</td>"
            f"<td><span class='status {status.lower()}'>{status}</span></td>"
            f"<td>{len(d.actions)}</td>"
            f"<td>{len(d.relationships)}</td>"
            f"<td>{len(d.reviews)}</td></tr>"
        )
    table = "<table><tr><th>Concept</th><th>名称</th><th>状态</th><th>Actions</th><th>关系</th><th>评审批注</th></tr>" + "".join(rows) + "</table>"

    # Simple graph of all relationships
    def extract_fn_ids(text: str) -> List[str]:
        return sorted(set(re.findall(r"Fn\d{2}(?:\.C\d{2})?", text or "")))

    graph_lines = ["graph TD"]
    seen = set()
    for d in all_data:
        for rel in d.relationships:
            src_candidates = extract_fn_ids(rel.get("source", ""))
            dst_text = " ".join([rel.get("target", ""), rel.get("mechanism", "")])
            dst_candidates = extract_fn_ids(dst_text)
            for src in src_candidates:
                for dst in dst_candidates:
                    if src == dst:
                        continue
                    key = tuple(sorted([src, dst]))
                    if key not in seen:
                        seen.add(key)
                        graph_lines.append(f"    {src} --> {dst}")
    mermaid_graph = "\n".join(graph_lines)

    generated_at = datetime.now().isoformat()
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Bridge Concept Authority Index</title>
  <style>{CSS}</style>
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});
  </script>
</head>
<body>
  <header>
    <h1>Bridge Concept Authority Index</h1>
  </header>
  <main>
    <section class="professor-abstract">
      <h2 style="margin-top:0;border:none;padding:0;">总览</h2>
      <p>本索引聚合全部 12 个 Bridge Concept Domain 的权威页面。每页包含术语、关系、状态机、数据结构、案例、路线、工程轨迹、独立评审批注及 Gemini 图形提示。</p>
    </section>
    {table}
    <section>
      <h2>跨 Concept 关系图</h2>
      <div class="diagram"><pre class="mermaid">{mermaid_graph}</pre></div>
    </section>
    <div class="footer">Generated at {generated_at}.</div>
  </main>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def load_graph() -> Dict[str, Any]:
    try:
        return yaml.safe_load(CONCEPT_GRAPH_FILE.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def build_concept(concept_id: str, graph: Dict[str, Any]) -> Tuple[ConceptData, Path]:
    loader = SourceLoader(concept_id)
    data = loader.load()
    Extractor(data, graph).run()
    narrator = Narrator(data)
    diagrams = DiagramGenerator(data)
    assets = diagrams.generate()
    renderer = HtmlRenderer(data, assets, narrator)
    html = "\n".join(line.rstrip() for line in renderer.render().splitlines()) + "\n"
    out_path = OUTPUT_DIR / f"{concept_id}.html"
    out_path.write_text(html, encoding="utf-8")
    return data, out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Bridge Concept authority HTML pages.")
    parser.add_argument("--concept", help="Build only this Concept, e.g. Fn08")
    parser.add_argument("--llm", action="store_true", help="Enable LLM-enhanced generation if GEMINI_API_KEY is set")
    parser.add_argument("--gemini-key", default=os.environ.get("GEMINI_API_KEY", ""), help="Gemini API key")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    graph = load_graph()
    targets = [args.concept] if args.concept else ALL_FN

    all_data: List[ConceptData] = []
    for cid in targets:
        print(f"Building authority page for {cid}...")
        data, out_path = build_concept(cid, graph)
        all_data.append(data)
        print(f"  -> {out_path.relative_to(ROOT)}")

    if not args.concept:
        index_path = OUTPUT_DIR / "index.html"
        index_path.write_text(render_index(all_data), encoding="utf-8")
        print(f"Generated index: {index_path.relative_to(ROOT)}")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
