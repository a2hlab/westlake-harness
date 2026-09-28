#!/usr/bin/env python3
"""Render the Fn technical decision console from checked-in atom documents."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ATOM_INDEX = DOCS / "atom.md"
OUT = DOCS / "boards" / "fn-decision-console.html"


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def strip_markdown(value: str) -> str:
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"<[^>]+>", "", value)
    return value.strip()


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    data: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def first_matching_line(text: str, patterns: list[str]) -> str:
    for line in text.splitlines():
        raw = line.strip()
        if not raw:
            continue
        for pattern in patterns:
            if re.search(pattern, raw, re.IGNORECASE):
                return strip_markdown(raw.lstrip("-#> ").strip())
    return ""


def excerpt(text: str, limit: int = 520) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            text = parts[2]
    lines: list[str] = []
    for line in text.splitlines():
        raw = strip_markdown(line)
        if not raw or raw.startswith("<!--"):
            continue
        if raw.startswith("[!"):
            continue
        lines.append(raw.lstrip("-#> ").strip())
        if len(" ".join(lines)) > limit:
            break
    joined = " ".join(lines)
    return joined[:limit].rstrip() + ("..." if len(joined) > limit else "")


def link_if_exists(path: Path) -> str | None:
    return path.relative_to(DOCS).as_posix() if path.exists() else None


def split_atom_id(atom_id: str) -> str:
    """Return canonical split form Fnxx/Ayy for filesystem paths and links."""
    return atom_id.replace(".", "/", 1)


def parse_atoms() -> list[dict[str, object]]:
    atoms: list[dict[str, object]] = []
    for line in read_text(ATOM_INDEX).splitlines():
        if not line.startswith("| `Fn"):
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) < 8:
            continue
        atom_id = parts[0].strip("`")
        atom_dir = DOCS / "atoms" / split_atom_id(atom_id)
        strategy = read_text(atom_dir / "strategy.md")
        strategy_fm = frontmatter(strategy)
        decision_text = read_text(atom_dir / "STRATEGY_DECISION.md")
        review_log = read_text(atom_dir / "REVIEW_LOG.md")
        review_html = link_if_exists(atom_dir / "strategy-review.html") or link_if_exists(atom_dir / "strategy_review.html")
        previous_decision = first_matching_line(
            decision_text,
            [r"^-\s*决定:", r"^-\s*decision:", r"^decision:"],
        )
        previous_route = first_matching_line(
            decision_text,
            [r"^-\s*生效路线:", r"^-\s*selected_route:", r"^selected_route:"],
        )
        atoms.append(
            {
                "id": atom_id,
                "domain": strip_markdown(parts[1]),
                "description": strip_markdown(parts[2]),
                "legacy": strip_markdown(parts[3]),
                "status": strip_markdown(parts[7]),
                "recommended": strategy_fm.get("recommended", ""),
                "backup": strategy_fm.get("backup", ""),
                "confidence": strategy_fm.get("confidence", ""),
                "reviewStatus": strategy_fm.get("review_status", ""),
                "decisionChoice": strategy_fm.get("decision_choice", ""),
                "selectedRoute": strategy_fm.get("selected_route", ""),
                "previousDecision": previous_decision,
                "previousRoute": previous_route,
                "strategyExcerpt": excerpt(strategy) if strategy else "",
                "reviewExcerpt": excerpt(review_log, 420) if review_log else "",
                "links": {
                    "strategyReview": review_html,
                    "strategy": link_if_exists(atom_dir / "strategy.md"),
                    "routemap": link_if_exists(atom_dir / "routemap.md"),
                    "usecase": link_if_exists(atom_dir / "usecase.md"),
                    "reviewLog": link_if_exists(atom_dir / "REVIEW_LOG.md"),
                    "decision": link_if_exists(atom_dir / "STRATEGY_DECISION.md"),
                    "readme": link_if_exists(atom_dir / "README.md"),
                    "spec": f"../spec/atoms/{split_atom_id(atom_id)}/",
                    "evidence": f"../evidence/atoms/{split_atom_id(atom_id)}/",
                    "source": f"../src/atoms/{split_atom_id(atom_id)}/",
                },
            }
        )
    return atoms


def render(atoms: list[dict[str, object]]) -> str:
    data = json.dumps(atoms, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fn 技术决策控制台</title>
<style>
:root {{
  color-scheme: light;
  --bg: #f6f7f9;
  --surface: #ffffff;
  --surface-2: #f0f3f5;
  --ink: #1f2933;
  --muted: #64717f;
  --line: #d8dee4;
  --accent: #0f766e;
  --accent-2: #b45309;
  --danger: #b42318;
  --ok: #166534;
  --shadow: 0 10px 30px rgba(31, 41, 51, 0.08);
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  min-height: 100vh;
  background: var(--bg);
  color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", sans-serif;
  font-size: 14px;
  line-height: 1.45;
}}
button, input, textarea {{ font: inherit; }}
a {{ color: var(--accent); font-weight: 650; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
.shell {{ display: grid; grid-template-rows: auto 1fr; min-height: 100vh; }}
.topbar {{
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 14px 18px;
  background: var(--surface);
  border-bottom: 1px solid var(--line);
  position: sticky;
  top: 0;
  z-index: 5;
}}
.brand {{ min-width: 250px; }}
.brand h1 {{ margin: 0; font-size: 20px; letter-spacing: 0; }}
.brand p {{ margin: 2px 0 0; color: var(--muted); }}
.metrics {{ display: flex; gap: 8px; flex-wrap: wrap; }}
.metric {{
  min-width: 86px;
  padding: 7px 10px;
  border: 1px solid var(--line);
  background: var(--surface-2);
  border-radius: 7px;
}}
.metric strong {{ display: block; font-size: 17px; }}
.metric span {{ color: var(--muted); font-size: 12px; }}
.layout {{
  display: grid;
  grid-template-columns: 320px minmax(420px, 1fr) 360px;
  min-height: 0;
}}
.sidebar, .detail, .decision {{
  min-height: calc(100vh - 74px);
  overflow: auto;
}}
.sidebar {{
  border-right: 1px solid var(--line);
  background: #fbfcfd;
}}
.searchbox {{ padding: 14px; border-bottom: 1px solid var(--line); }}
.searchbox input {{
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--surface);
}}
.atom-list {{ list-style: none; margin: 0; padding: 0; }}
.atom-item {{
  width: 100%;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
  padding: 10px 14px;
  border: 0;
  border-bottom: 1px solid var(--line);
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}}
.atom-item:hover, .atom-item.active {{ background: #e9f5f3; }}
.atom-id {{ font-weight: 760; }}
.atom-title {{ margin-top: 2px; color: var(--muted); font-size: 12px; }}
.badge {{
  align-self: start;
  padding: 2px 7px;
  border-radius: 999px;
  border: 1px solid var(--line);
  color: var(--muted);
  font-size: 11px;
  white-space: nowrap;
}}
.badge.done {{ color: var(--ok); border-color: #86c79a; background: #eef9f1; }}
.badge.todo {{ color: var(--accent-2); border-color: #e9c46a; background: #fff7e6; }}
.detail {{ padding: 18px 22px; }}
.decision {{
  border-left: 1px solid var(--line);
  background: var(--surface);
  padding: 18px;
}}
.section {{
  margin-bottom: 14px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: var(--shadow);
}}
.section h2, .section h3 {{
  margin: 0;
  padding: 12px 14px;
  border-bottom: 1px solid var(--line);
  font-size: 15px;
  letter-spacing: 0;
}}
.section-body {{ padding: 14px; }}
.headline {{ display: flex; justify-content: space-between; gap: 12px; align-items: start; }}
.headline h2 {{ border: 0; padding: 0; font-size: 23px; }}
.headline .domain {{ color: var(--muted); margin-top: 4px; }}
.kv {{
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 7px 12px;
}}
.kv dt {{ color: var(--muted); }}
.kv dd {{ margin: 0; }}
.route-grid {{
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}}
.route-box {{
  border: 1px solid var(--line);
  border-radius: 7px;
  padding: 10px;
  min-height: 78px;
  background: #fbfcfd;
}}
.route-box strong {{ display: block; font-size: 18px; margin-bottom: 3px; }}
.excerpt {{
  max-height: 220px;
  overflow: auto;
  color: #344054;
  white-space: pre-wrap;
}}
.links {{ display: flex; flex-wrap: wrap; gap: 8px; }}
.links a, .links span {{
  border: 1px solid var(--line);
  background: #fbfcfd;
  border-radius: 6px;
  padding: 6px 8px;
}}
.links span {{ color: var(--muted); }}
.decision-buttons {{ display: grid; gap: 8px; }}
.decision-buttons button, .nav button, .export-actions button {{
  border: 1px solid var(--line);
  border-radius: 7px;
  padding: 10px 11px;
  background: #fbfcfd;
  color: var(--ink);
  cursor: pointer;
  text-align: left;
}}
.decision-buttons button:hover, .nav button:hover, .export-actions button:hover {{ border-color: var(--accent); }}
.decision-buttons button.selected {{
  border-color: var(--accent);
  background: #e8f6f4;
  box-shadow: inset 4px 0 0 var(--accent);
}}
.decision-buttons button:disabled {{
  color: #9aa4af;
  cursor: not-allowed;
  background: #f2f4f7;
}}
.checks {{ display: grid; gap: 8px; margin-top: 12px; }}
.checks label {{ display: flex; gap: 8px; align-items: center; }}
textarea {{
  width: 100%;
  min-height: 116px;
  resize: vertical;
  border: 1px solid var(--line);
  border-radius: 7px;
  padding: 10px;
}}
.nav {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px; }}
.export-actions {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
pre {{
  white-space: pre-wrap;
  max-height: 260px;
  overflow: auto;
  background: #20262d;
  color: #eef2f6;
  border-radius: 7px;
  padding: 12px;
}}
.empty {{ padding: 22px; color: var(--muted); text-align: center; }}
@media (max-width: 1100px) {{
  .layout {{ grid-template-columns: 280px 1fr; }}
  .decision {{ grid-column: 1 / -1; min-height: auto; border-left: 0; border-top: 1px solid var(--line); }}
}}
@media (max-width: 760px) {{
  .topbar {{ position: static; align-items: flex-start; flex-direction: column; }}
  .layout {{ display: block; }}
  .sidebar, .detail, .decision {{ min-height: auto; max-height: none; }}
  .route-grid {{ grid-template-columns: 1fr; }}
  .kv {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<div class="shell">
  <header class="topbar">
    <div class="brand">
      <h1>Fn 技术决策控制台</h1>
      <p>逐个审核主选、备选、保留旧决定、补实验或要求深化。</p>
    </div>
    <div class="metrics" id="metrics"></div>
  </header>
  <main class="layout">
    <aside class="sidebar">
      <div class="searchbox">
        <input id="filter" type="search" placeholder="筛选 Fn、领域、说明、路线">
      </div>
      <ul class="atom-list" id="atomList"></ul>
    </aside>
    <section class="detail" id="detail"></section>
    <aside class="decision" id="decisionPanel"></aside>
  </main>
</div>
<script>
const ATOMS = {data};
const STORE_KEY = "bridge.fn.decision.console.v1";
const labels = {{
  primary: "选择主选",
  backup: "选择备选",
  unchanged: "选择不变",
  experiment: "继续做实验",
  deepen: "描述不直观需要深化"
}};
const deepenLabels = {{
  principle: "深化原理",
  logic: "深化逻辑",
  experiment: "深化实验"
}};
let state = loadState();
let currentId = ATOMS[0]?.id || "";

function loadState() {{
  try {{ return JSON.parse(localStorage.getItem(STORE_KEY) || "{{}}"); }}
  catch (_) {{ return {{}}; }}
}}
function saveState() {{
  try {{ localStorage.setItem(STORE_KEY, JSON.stringify(state)); }}
  catch (_) {{}}
  render();
}}
function recordFor(id) {{
  if (!state[id]) state[id] = {{ atomId: id, decision: "", deepen: [], note: "", updatedAt: "" }};
  return state[id];
}}
function atomById(id) {{ return ATOMS.find(atom => atom.id === id) || null; }}
function materialLink(atom, key, label) {{
  const href = atom.links[key];
  if (!href) return `<span>${{label}} 缺失</span>`;
  return `<a href="${{href}}">${{label}}</a>`;
}}
function selectedRoute(atom, decision) {{
  if (decision === "primary") return atom.recommended || "";
  if (decision === "backup") return atom.backup || "";
  if (decision === "unchanged") return atom.previousRoute || atom.selectedRoute || "";
  return "";
}}
function filteredAtoms() {{
  const q = document.getElementById("filter")?.value.trim().toLowerCase() || "";
  if (!q) return ATOMS;
  return ATOMS.filter(atom =>
    [atom.id, atom.domain, atom.description, atom.legacy, atom.recommended, atom.backup, atom.previousDecision]
      .join(" ")
      .toLowerCase()
      .includes(q)
  );
}}
function renderMetrics() {{
  const records = Object.values(state).filter(r => r.decision);
  const reviewed = records.length;
  const experiments = records.filter(r => r.decision === "experiment").length;
  const deepens = records.filter(r => r.decision === "deepen" || (r.deepen || []).length).length;
  document.getElementById("metrics").innerHTML = [
    ["总数", ATOMS.length],
    ["已选", reviewed],
    ["剩余", Math.max(ATOMS.length - reviewed, 0)],
    ["实验", experiments],
    ["深化", deepens],
  ].map(([label, value]) => `<div class="metric"><strong>${{value}}</strong><span>${{label}}</span></div>`).join("");
}}
function renderList() {{
  const items = filteredAtoms();
  const list = document.getElementById("atomList");
  if (!items.length) {{
    list.innerHTML = `<li class="empty">没有匹配的 atom</li>`;
    return;
  }}
  list.innerHTML = items.map(atom => {{
    const rec = state[atom.id];
    const done = rec && rec.decision;
    const active = atom.id === currentId ? " active" : "";
    return `<li><button class="atom-item${{active}}" data-id="${{atom.id}}">
      <span><span class="atom-id">${{atom.id}}</span><span class="atom-title">${{atom.description}}</span></span>
      <span class="badge ${{done ? "done" : "todo"}}">${{done ? labels[rec.decision] : "待审"}}</span>
    </button></li>`;
  }}).join("");
  list.querySelectorAll("button[data-id]").forEach(btn => btn.addEventListener("click", () => {{
    currentId = btn.dataset.id;
    render();
  }}));
}}
function renderDetail(atom) {{
  document.getElementById("detail").innerHTML = `<div class="section">
    <div class="section-body headline">
      <div>
        <h2>${{atom.id}} · ${{atom.description}}</h2>
        <div class="domain">${{atom.domain}} · legacy ${{atom.legacy || "n/a"}}</div>
      </div>
      <span class="badge">${{atom.status || "unknown"}}</span>
    </div>
  </div>
  <div class="section">
    <h3>路线概览</h3>
    <div class="section-body route-grid">
      <div class="route-box"><strong>${{atom.recommended || "未标注"}}</strong><span>当前推荐 / 主选候选</span></div>
      <div class="route-box"><strong>${{atom.backup || "未标注"}}</strong><span>备选候选</span></div>
      <div class="route-box"><strong>${{atom.confidence || "未标注"}}</strong><span>推荐置信度</span></div>
    </div>
  </div>
  <div class="section">
    <h3>旧决定与状态</h3>
    <div class="section-body">
      <dl class="kv">
        <dt>旧裁决</dt><dd>${{atom.previousDecision || atom.reviewStatus || "无有效旧决定"}}</dd>
        <dt>旧路线</dt><dd>${{atom.previousRoute || atom.selectedRoute || "无"}}</dd>
        <dt>旧选择</dt><dd>${{atom.decisionChoice || "未标注"}}</dd>
      </dl>
    </div>
  </div>
  <div class="section">
    <h3>背景摘要</h3>
    <div class="section-body excerpt">${{atom.strategyExcerpt || "没有 strategy 摘要。请打开材料链接查看。"}}${{atom.reviewExcerpt ? "\\n\\n审核日志摘要：" + atom.reviewExcerpt : ""}}</div>
  </div>
  <div class="section">
    <h3>材料入口</h3>
    <div class="section-body links">
      ${{materialLink(atom, "strategyReview", "策略审核页")}}
      ${{materialLink(atom, "strategy", "strategy")}}
      ${{materialLink(atom, "routemap", "routemap")}}
      ${{materialLink(atom, "usecase", "usecase")}}
      ${{materialLink(atom, "reviewLog", "review log")}}
      ${{materialLink(atom, "decision", "旧 decision")}}
      ${{materialLink(atom, "readme", "README")}}
      ${{materialLink(atom, "spec", "spec")}}
      ${{materialLink(atom, "evidence", "evidence")}}
      ${{materialLink(atom, "source", "source")}}
    </div>
  </div>`;
}}
function setDecision(id, decision) {{
  const atom = atomById(id);
  const rec = recordFor(id);
  rec.decision = decision;
  rec.route = selectedRoute(atom, decision);
  rec.updatedAt = new Date().toISOString();
  if (decision !== "deepen") rec.deepen = [];
  saveState();
}}
function updateNote(id, value) {{
  const rec = recordFor(id);
  rec.note = value;
  rec.updatedAt = new Date().toISOString();
  try {{ localStorage.setItem(STORE_KEY, JSON.stringify(state)); }} catch (_) {{}}
  renderExport();
}}
function toggleDeepen(id, value, checked) {{
  const rec = recordFor(id);
  const set = new Set(rec.deepen || []);
  if (checked) set.add(value); else set.delete(value);
  rec.deepen = [...set];
  rec.updatedAt = new Date().toISOString();
  saveState();
}}
function renderDecision(atom) {{
  const rec = recordFor(atom.id);
  const hasPrevious = Boolean(atom.previousDecision || atom.reviewStatus || atom.selectedRoute);
  const index = ATOMS.findIndex(item => item.id === atom.id);
  document.getElementById("decisionPanel").innerHTML = `<div class="nav">
    <button id="prevBtn"${{index <= 0 ? " disabled" : ""}}>上一项</button>
    <button id="nextBtn"${{index >= ATOMS.length - 1 ? " disabled" : ""}}>下一项</button>
  </div>
  <div class="section">
    <h3>本轮裁决</h3>
    <div class="section-body">
      <div class="decision-buttons">
        <button data-decision="primary" class="${{rec.decision === "primary" ? "selected" : ""}}">选择主选<br><small>采用推荐路线：${{atom.recommended || "未标注"}}</small></button>
        <button data-decision="backup" class="${{rec.decision === "backup" ? "selected" : ""}}">选择备选<br><small>采用备选路线：${{atom.backup || "未标注"}}</small></button>
        <button data-decision="unchanged" class="${{rec.decision === "unchanged" ? "selected" : ""}}" ${{hasPrevious ? "" : "disabled"}}>选择不变<br><small>${{hasPrevious ? "沿用已有裁决" : "没有可沿用旧决定"}}</small></button>
        <button data-decision="experiment" class="${{rec.decision === "experiment" ? "selected" : ""}}">继续做实验<br><small>证据不足，先补实验再定</small></button>
        <button data-decision="deepen" class="${{rec.decision === "deepen" ? "selected" : ""}}">描述不直观需要深化<br><small>要求补原理、逻辑或实验说明</small></button>
      </div>
      <div class="checks">
        <label><input type="checkbox" data-deepen="principle" ${{(rec.deepen || []).includes("principle") ? "checked" : ""}}> 深化原理</label>
        <label><input type="checkbox" data-deepen="logic" ${{(rec.deepen || []).includes("logic") ? "checked" : ""}}> 深化逻辑</label>
        <label><input type="checkbox" data-deepen="experiment" ${{(rec.deepen || []).includes("experiment") ? "checked" : ""}}> 深化实验</label>
      </div>
    </div>
  </div>
  <div class="section">
    <h3>批注</h3>
    <div class="section-body">
      <textarea id="note" placeholder="写下采用原因、拒绝原因、补证要求或具体实验问题。">${{rec.note || ""}}</textarea>
    </div>
  </div>
  <div class="section">
    <h3>导出</h3>
    <div class="section-body">
      <div class="export-actions">
        <button id="exportMd">Markdown</button>
        <button id="exportJson">JSON</button>
      </div>
      <pre id="exportBox"></pre>
    </div>
  </div>`;
  document.getElementById("prevBtn")?.addEventListener("click", () => {{ if (index > 0) {{ currentId = ATOMS[index - 1].id; render(); }} }});
  document.getElementById("nextBtn")?.addEventListener("click", () => {{ if (index < ATOMS.length - 1) {{ currentId = ATOMS[index + 1].id; render(); }} }});
  document.querySelectorAll("[data-decision]").forEach(btn => btn.addEventListener("click", () => setDecision(atom.id, btn.dataset.decision)));
  document.querySelectorAll("[data-deepen]").forEach(box => box.addEventListener("change", event => toggleDeepen(atom.id, box.dataset.deepen, event.target.checked)));
  document.getElementById("note").addEventListener("input", event => updateNote(atom.id, event.target.value));
  document.getElementById("exportMd").addEventListener("click", () => copyExport("md"));
  document.getElementById("exportJson").addEventListener("click", () => copyExport("json"));
  renderExport();
}}
function recordsInOrder() {{
  return ATOMS.map(atom => {{
    const rec = state[atom.id];
    if (!rec || !rec.decision) return null;
    return {{
      atomId: atom.id,
      description: atom.description,
      domain: atom.domain,
      decision: rec.decision,
      decisionLabel: labels[rec.decision],
      route: rec.route || selectedRoute(atom, rec.decision),
      recommended: atom.recommended,
      backup: atom.backup,
      previousDecision: atom.previousDecision || atom.reviewStatus,
      previousRoute: atom.previousRoute || atom.selectedRoute,
      deepen: rec.deepen || [],
      note: rec.note || "",
      updatedAt: rec.updatedAt || ""
    }};
  }}).filter(Boolean);
}}
function markdownExport() {{
  const records = recordsInOrder();
  if (!records.length) return "本轮尚无决策记录。";
  return ["# Fn 技术决策本轮记录", "", `- generated_at: ${{new Date().toISOString()}}`, `- record_count: ${{records.length}}`, ""].concat(records.map(r => [
    `## ${{r.atomId}} · ${{r.description}}`,
    "",
    `- 决策: ${{r.decisionLabel}}`,
    `- 生效路线: ${{r.route || "(待定)"}}`,
    `- 推荐路线: ${{r.recommended || "(未标注)"}}`,
    `- 备选路线: ${{r.backup || "(未标注)"}}`,
    `- 旧决定: ${{r.previousDecision || "(无)"}}`,
    `- 旧路线: ${{r.previousRoute || "(无)"}}`,
    `- 深化方向: ${{r.deepen.length ? r.deepen.map(x => deepenLabels[x]).join(", ") : "(无)"}}`,
    `- 时间: ${{r.updatedAt || "(未记录)"}}`,
    "",
    `批注: ${{r.note || "(无)"}}`,
    ""
  ].join("\\n"))).join("\\n");
}}
function jsonExport() {{
  return JSON.stringify({{ generatedAt: new Date().toISOString(), records: recordsInOrder() }}, null, 2);
}}
async function copyExport(type) {{
  const value = type === "json" ? jsonExport() : markdownExport();
  document.getElementById("exportBox").textContent = value;
  try {{ await navigator.clipboard.writeText(value); }} catch (_) {{}}
}}
function renderExport() {{
  const box = document.getElementById("exportBox");
  if (box) box.textContent = markdownExport();
}}
function renderEmpty() {{
  document.getElementById("detail").innerHTML = `<div class="section"><div class="section-body excerpt">没有匹配的 atom，请清空或调整筛选条件。</div></div>`;
  document.getElementById("decisionPanel").innerHTML = "";
}}
function render() {{
  renderMetrics();
  renderList();
  const atom = atomById(currentId);
  if (!atom) {{
    renderEmpty();
    return;
  }}
  renderDetail(atom);
  renderDecision(atom);
}}
document.getElementById("filter").addEventListener("input", () => {{
  const visible = filteredAtoms();
  if (!visible.find(atom => atom.id === currentId)) {{
    currentId = visible.length ? visible[0].id : "";
  }}
  render();
}});
render();
</script>
</body>
</html>
"""


def main() -> None:
    atoms = parse_atoms()
    OUT.write_text(render(atoms), encoding="utf-8")
    print(f"Rendered {len(atoms)} atoms to {OUT}")


if __name__ == "__main__":
    main()
