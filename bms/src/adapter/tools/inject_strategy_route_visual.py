#!/usr/bin/env python3
"""Inject or replace one self-contained multi-route software-stack figure in an existing strategy HTML."""

from __future__ import annotations

import argparse
import base64
from html import escape
import json
from pathlib import Path
import re

import yaml


MARKER_ID = "technical-route-stack-map-v3"
COLORS = {"primary": "#159947", "backup": "#F28C28", "third": "#7C3AED", "neutral": "#9AA0A6"}
PROBABILITY = {
    "high": ("高概率", "#39D353"),
    "low": ("低概率", "#8B1E1E"),
    "almost_impossible": ("almost impossible / 几乎不可能", "#FF2B2B"),
    "undetermined": ("证据不足 / 未定", "#9AA0A6"),
}


def normalize_visible_terms(source: str) -> str:
    """Chinese-localize prose while preserving code/pre/script/style and attributes."""
    protected = re.split(r'(<(?:script|style|pre|code)\b[^>]*>.*?</(?:script|style|pre|code)>)', source, flags=re.I | re.S)
    for index in range(0, len(protected), 2):
        tokens = re.split(r'(<[^>]+>)', protected[index])
        for token_index in range(0, len(tokens), 2):
            text = tokens[token_index]
            text = re.sub(r"canonical\s+acceptance", "范本", text, flags=re.I)
            text = re.sub(r"canonical\s+scope", "范本范围", text, flags=re.I)
            text = re.sub(r"\bcanonical\b", "范本", text, flags=re.I)
            text = text.replace("权威验收口径", "范本")
            tokens[token_index] = text
        protected[index] = "".join(tokens)
    return "".join(protected)


def split_frontmatter(text: str) -> tuple[dict, str]:
    match = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    if not match:
        return {}, text
    return yaml.safe_load(match.group(1)) or {}, text[match.end():]


def route_rows(text: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and re.fullmatch(r"R\d+[A-Za-z]?", cells[0]):
            rows.append((cells[0], re.sub(r"[`*_]", "", cells[1])))
    if rows:
        return rows
    return [(m.group(1), m.group(2).strip()) for m in re.finditer(r"^##+\s+(R\d+[A-Za-z]?)\s*[·.：:-]+\s*(.+)$", text, re.M)]


def route_ref(value: object, valid: set[str], fallback: str) -> str:
    return next((route_id for route_id in re.findall(r"\bR\d+[A-Za-z]?\b", str(value or "")) if route_id in valid), fallback)


def image_data(path: Path) -> str:
    mime = "image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def fragment(atom_dir: Path) -> tuple[str, str]:
    strategy_text = (atom_dir / "strategy.md").read_text(encoding="utf-8")
    routemap_text = (atom_dir / "routemap.md").read_text(encoding="utf-8")
    usecase_text = (atom_dir / "usecase.md").read_text(encoding="utf-8") if (atom_dir / "usecase.md").exists() else ""
    review_log_text = (atom_dir / "REVIEW_LOG.md").read_text(encoding="utf-8") if (atom_dir / "REVIEW_LOG.md").exists() else ""
    strategy_meta, _ = split_frontmatter(strategy_text)
    _, routemap = split_frontmatter(routemap_text)
    routes = route_rows(routemap)
    if len(routes) < 2:
        raise RuntimeError(f"{atom_dir}: fewer than two route rows")
    valid_routes = {route_id for route_id, _ in routes}
    primary = route_ref(strategy_meta.get("recommended"), valid_routes, routes[0][0])
    backup = route_ref(strategy_meta.get("backup"), valid_routes, routes[1][0])
    if backup == primary:
        backup = next((route_id for route_id, _ in routes if route_id != primary), routes[1][0])
    others = [route_id for route_id, _ in routes if route_id not in {primary, backup}]
    third = others[0] if others else ""
    roles = {primary: ("主选", "primary"), backup: ("次选", "backup")}
    if third:
        roles[third] = ("第三路线", "third")
    atom_id = strategy_meta.get("atom_id") or f"{atom_dir.parent.name}.{atom_dir.name}"
    verdict_status = str(strategy_meta.get("verdict_status", "待用户确认"))
    review_status = str(strategy_meta.get("review_status", "未审视"))
    selected_route = str(strategy_meta.get("selected_route", ""))
    protected_decision = any(token in verdict_status + review_status for token in ("用户已确认", "已审视", "已确认"))
    default_confirmed = "默认选项" in verdict_status
    existing_protected = protected_decision and not default_confirmed
    recommendation_condition = str(strategy_meta.get("recommendation_condition", ""))
    if not recommendation_condition and "条件" in str(strategy_meta.get("recommended", "")):
        recommendation_condition = str(strategy_meta.get("recommended"))
    confidence = str(strategy_meta.get("confidence", "未标注"))
    needs_source = "needs-source" in strategy_text.lower()
    low_confidence = confidence.strip().lower() in {"low", "very-low", "very low"} or "低置信" in confidence
    decision_label = (
        f"既有人工裁决（受保护）：{review_status} · {verdict_status}"
        + ((" · selected=" + selected_route) if selected_route else "")
        if existing_protected
        else f"用户已确认·默认选项·可重新调整：recommended={primary}"
    )
    decision_guard = (
        "人工选择不会被批量生成覆盖。方向确认不等于实现批准，也不等于验收通过。"
        if existing_protected
        else "这是本轮正式方向裁决，后续仍可重新调整；方向确认不等于实现批准，也不等于验收通过。"
    )
    if recommendation_condition:
        decision_guard += f" 条件性推荐前置：{recommendation_condition}；前置未满足不得进入实现。"
    if needs_source:
        decision_guard += " 证据门阻断：needs-source 未闭合，不得升级为可实现或已验收。"
    if low_confidence:
        decision_guard += f" 证据门阻断：当前置信度 {confidence}，不得升级为可实现或已验收。"
    six_round_complete = all(f"student-r{index}" in review_log_text for index in (1, 2, 3)) and all(
        f"ieee-r{index}" in review_log_text for index in (1, 2, 3)
    )
    review_message = (
        "逐原子 3 轮新生 + 3 轮 IEEE 语义审稿已有 REVIEW_LOG receipt；本轮只审核新增视觉与机械结构，不改原结论。"
        if six_round_complete
        else "逐原子 3 轮新生 + 3 轮 IEEE 语义审稿未完成；本轮只完成新增视觉与机械结构，不得冒充最终语义 PASS。"
    )
    newer_reference_count = len(re.findall(r"AOSP[- ]V?15\b|(?:OpenHarmony|OH)[- ]V?7\b", usecase_text + routemap_text + strategy_text, re.I))
    version_message = (
        f"目标基线固定 AOSP V14 + OpenHarmony 6.1；当前输入仍含 {newer_reference_count} 处 V15/V7 引用，逐项差分闭合前只算外部参考。"
        if newer_reference_count
        else "目标基线固定 AOSP V14 + OpenHarmony 6.1；新版本资料不得直接冒充目标权威证据。"
    )
    image_path = atom_dir / "strategy-route-3d.jpg"
    if not image_path.exists():
        image_path = atom_dir / "strategy-route-3d.png"
    if not image_path.exists():
        raise RuntimeError(f"{atom_dir}: no strategy-route-3d image")
    receipt_path = atom_dir / "strategy-route-3d.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.exists() else {}
    route_feasibility = receipt.get("route_feasibility") or {}
    route_items = []
    for route_id, summary in routes:
        label, css = roles.get(route_id, ("其他路线", "neutral"))
        probability_html = ""
        if route_id != primary:
            probability_class = str((route_feasibility.get(route_id) or {}).get("class", "undetermined"))
            probability_label = PROBABILITY.get(probability_class, PROBABILITY["undetermined"])[0]
            probability_html = (
                f'<em class="srsv-probability probability-{escape(probability_class)}">'
                f"可行概率：{escape(probability_label)}</em>"
            )
        route_items.append(
            f'<li class="srsv-route {css}"><span>{escape(label)} · {escape(route_id)}</span>{probability_html}'
            f'<small>{escape(summary)}</small></li>'
        )
    alt = (
        f"{atom_id} 单图多路线三维软件栈图。灰色背景包含 Android App、AOSP V14 Framework/API、WestLake Adapter Boundary、"
        f"OpenHarmony 6.1 System Services 与 OH 6.1 Kernel / Storage / Device；绿色主选 {primary}，橙色次选 {backup}"
        + (f"，紫色第三路线 {third}" if third else "；本原子没有第三条合法路线")
        + "；其余结构和连线为灰色。"
    )
    purple_note = f"紫色={escape(third)} 第三路线" if third else "无合法第三路线，不伪造紫色候选"
    html = f'''<section id="{MARKER_ID}" class="srsv-section" data-version="3" data-single-diagram="true">
<h2>多技术路线 · 三维软件栈总图</h2>
<p class="srsv-decision"><b>{escape(decision_label)}</b>。{escape(decision_guard)} 范本（原子唯一验收合同）保持不变；本图只补充路线比较，不改变 <code>strategy.md</code>，目标版本证据门与低置信度状态不因方向确认而解除。</p>
<p class="srsv-version"><b>目标版本证据门：</b>{escape(version_message)}</p>
<p class="srsv-review"><b>审稿状态：</b>{escape(review_message)}</p>
<p class="srsv-rule"><b>读图规则：</b>所有候选位于同一图；灰色是共享软件栈、系统/进程边界与非路线连线。绿色={escape(primary)} 主选；橙色={escape(backup)} 次选；{purple_note}。颜色只表示路线排序，不表示已经实现或设备已验证。</p>
<p class="srsv-probability-rule"><b>可行概率（仅非主选路线的旁置徽标/光环）：</b><span class="srsv-probability probability-high">高概率</span><span class="srsv-probability probability-low">低概率</span><span class="srsv-probability probability-almost_impossible">almost impossible / 几乎不可能</span><span class="srsv-probability probability-undetermined">证据不足 / 未定</span>。概率颜色不改变路线身份线色；缺证据只能保持灰色未定。</p>
<figure class="srsv-figure"><img src="{image_data(image_path)}" alt="{escape(alt)}"><figcaption>共同目标上下文：Android App → AOSP V14 Framework/API → WestLake Adapter Boundary → OpenHarmony 6.1 System Services → OH 6.1 Kernel / Storage / Device。沿颜色可看到每条路线穿过的层、状态 owner 与翻译位置。Gemini model={escape(str(receipt.get('model', 'gemini')))}；image SHA-256={escape(str(receipt.get('image_sha256', 'not-recorded')))}。</figcaption></figure>
<ul class="srsv-routes">{''.join(route_items)}</ul>
</section>'''
    css = f'''<style id="{MARKER_ID}-style">
:root{{--srsv-primary:{COLORS['primary']};--srsv-backup:{COLORS['backup']};--srsv-third:{COLORS['third']};--srsv-neutral:{COLORS['neutral']}}}
.srsv-section{{margin:28px 0;padding:20px;border:2px solid var(--srsv-neutral);border-radius:12px;background:#fff;color:#20242b}}.srsv-section h2{{border-color:var(--srsv-neutral)!important}}.srsv-decision,.srsv-version,.srsv-rule,.srsv-review,.srsv-probability-rule{{padding:12px 14px;border-left:5px solid var(--srsv-neutral);background:#f3f4f5}}.srsv-decision{{border-left-color:var(--srsv-primary);background:#edf8f1}}.srsv-version,.srsv-review{{border-left-color:var(--srsv-backup);background:#fff4e6}}.srsv-figure{{margin:18px 0}}.srsv-figure img{{display:block;width:100%;height:auto;background:#f4f5f6}}.srsv-figure figcaption{{margin-top:8px;color:#626a73;font-size:13px}}.srsv-routes{{list-style:none;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px}}.srsv-route{{border-top:7px solid var(--srsv-neutral);background:#f5f5f5;padding:10px}}.srsv-route span{{display:block;font-weight:700}}.srsv-route small{{display:block;margin-top:5px}}.srsv-route.primary{{border-color:var(--srsv-primary);background:#edf8f1}}.srsv-route.backup{{border-color:var(--srsv-backup);background:#fff4e6}}.srsv-route.third{{border-color:var(--srsv-third);background:#f4edff}}.srsv-probability{{display:inline-block;margin:4px 5px;padding:2px 8px;border-radius:999px;font-style:normal;font-weight:700;border:1px solid #70757a;background:#9AA0A6;color:#111}}.probability-high{{background:#39D353;color:#071b0d}}.probability-low{{background:#8B1E1E;color:#fff}}.probability-almost_impossible{{background:#FF2B2B;color:#111}}.probability-undetermined{{background:#9AA0A6;color:#111}}
</style>'''
    return css, html


def inject(atom_dir: Path, output: Path) -> None:
    source = output.read_text(encoding="utf-8")
    css, section = fragment(atom_dir)
    source = re.sub(rf'<style id="{MARKER_ID}-style">.*?</style>', '', source, flags=re.S)
    source = re.sub(rf'<section id="{MARKER_ID}"[^>]*>.*?</section>', '', source, flags=re.S)
    source = source.replace("</head>", css + "\n</head>", 1)
    heading = re.search(r"<h1\b[^>]*>.*?</h1>", source, re.S | re.I)
    if heading:
        source = source[: heading.end()] + "\n" + section + source[heading.end():]
    else:
        source = source.replace("<body>", "<body>\n" + section, 1)
    output.write_text(normalize_visible_terms(source), encoding="utf-8")
    print(f"OK {atom_dir.parent.name}.{atom_dir.name} {output} {output.stat().st_size}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("atom_dir", type=Path)
    parser.add_argument("--output")
    args = parser.parse_args()
    atom_dir = args.atom_dir.resolve()
    if args.output:
        output = Path(args.output).resolve()
    elif (atom_dir / "strategy-review.html").exists():
        output = atom_dir / "strategy-review.html"
    elif (atom_dir / "strategy_review.html").exists():
        output = atom_dir / "strategy_review.html"
    else:
        raise RuntimeError(f"{atom_dir}: no existing strategy HTML")
    inject(atom_dir, output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
