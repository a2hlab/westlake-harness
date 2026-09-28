#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a self-contained strategy-review textbook page from atom artifacts."""

from __future__ import annotations

import argparse
import base64
from html import escape
import json
from pathlib import Path
import re

import markdown
import yaml


COLORS = {
    "primary": "#159947",
    "backup": "#F28C28",
    "third": "#7C3AED",
    "neutral": "#9AA0A6",
}
PROBABILITY = {
    "high": ("高概率", "#39D353"),
    "low": ("低概率", "#8B1E1E"),
    "almost_impossible": ("almost impossible / 几乎不可能", "#FF2B2B"),
    "undetermined": ("证据不足 / 未定", "#9AA0A6"),
}


def split_frontmatter(text: str) -> tuple[dict, str]:
    match = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    if not match:
        return {}, text
    return yaml.safe_load(match.group(1)) or {}, text[match.end():]


def route_rows(text: str) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and re.fullmatch(r"R\d+[A-Za-z]?", cells[0]):
            summary = re.sub(r"[`*_]", "", cells[1])
            evidence = re.sub(r"[`*_]", "", cells[2]) if len(cells) > 2 else "见 routemap.md"
            gap = re.sub(r"[`*_]", "", cells[-1]) if len(cells) > 3 else "待证条件见 routemap.md"
            rows.append((cells[0], summary, evidence, gap))
    if rows:
        return rows
    for match in re.finditer(r"^##+\s+(R\d+[A-Za-z]?)\s*[·.：:-]+\s*(.+)$", text, re.M):
        rows.append((match.group(1), match.group(2).strip(), "见 routemap.md", "待证条件见 routemap.md"))
    return rows


def md(text: str) -> str:
    text = re.sub(r"canonical\s+acceptance", "范本", text, flags=re.I)
    text = re.sub(r"canonical\s+scope", "范本范围", text, flags=re.I)
    text = re.sub(r"\bcanonical\b", "范本", text, flags=re.I)
    text = text.replace("权威验收口径", "范本")
    return markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])


def image_data(path: Path) -> str:
    mime = "image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def first_case_block(body: str, patterns: tuple[str, ...]) -> str:
    sections = re.split(r"(?=^###\s+\d+\.)", body, flags=re.M)
    for section in sections:
        if re.match(r"^###\s+\d+\.", section) and any(re.search(pattern, section, re.I) for pattern in patterns):
            return section.strip()
    return "该侧源码锚点见 usecase.md；本页不把对位能力自动等同为兼容语义。"


def usecase_overview(body: str) -> str:
    text = re.sub(r"^#\s+.*$", "", body, count=1, flags=re.M)
    text = re.split(r"^##\s+逐案详情", text, maxsplit=1, flags=re.M)[0]
    return text.strip()


def selected_strategy(body: str) -> str:
    body = re.sub(r"#(\d+)", r"案 \1", body)
    chunks = re.split(r"(?=^##\s+)", body, flags=re.M)
    wanted = ("结论", "为什么推荐", "排序规则", "为什么 R", "证伪条件", "最小下一证据", "与 draft", "与既有")
    selected = [chunk for chunk in chunks if chunk.startswith("## ") and any(key in chunk.splitlines()[0] for key in wanted)]
    return "\n\n".join(selected) if selected else body[:5000]


def route_ref(value: object, valid: set[str], fallback: str) -> str:
    return next((route_id for route_id in re.findall(r"\bR\d+[A-Za-z]?\b", str(value or "")) if route_id in valid), fallback)


def build(atom_dir: Path, output: Path) -> None:
    atom_path = atom_dir / "atom.yaml"
    atom = yaml.safe_load(atom_path.read_text(encoding="utf-8")) if atom_path.exists() else {}
    use_meta, use_body = split_frontmatter((atom_dir / "usecase.md").read_text(encoding="utf-8"))
    route_meta, route_body = split_frontmatter((atom_dir / "routemap.md").read_text(encoding="utf-8"))
    strategy_meta, strategy_body = split_frontmatter((atom_dir / "strategy.md").read_text(encoding="utf-8"))
    routes = route_rows(route_body)
    if len(routes) < 2:
        raise RuntimeError(f"{atom_dir}: fewer than two routes")

    atom_id = atom.get("atom_id") or use_meta.get("atom_id") or strategy_meta.get("atom_id") or f"{atom_dir.parent.name}.{atom_dir.name}"
    alias = atom.get("alias") or strategy_meta.get("atom_name") or atom.get("title") or atom_id
    title = atom.get("title") or strategy_meta.get("atom_name") or alias
    acceptance = atom.get("acceptance") or []
    valid_routes = {route_id for route_id, *_ in routes}
    primary = route_ref(strategy_meta.get("recommended"), valid_routes, routes[0][0])
    backup = route_ref(strategy_meta.get("backup"), valid_routes, routes[1][0])
    if backup == primary:
        backup = next((route_id for route_id, *_ in routes if route_id != primary), routes[1][0])
    others = [route_id for route_id, _, _, _ in routes if route_id not in {primary, backup}]
    third = others[0] if others else ""
    role = {primary: ("主选", "primary"), backup: ("次选", "backup")}
    if third:
        role[third] = ("第三路线", "third")

    image_path = atom_dir / "strategy-route-3d.jpg"
    if not image_path.exists():
        image_path = atom_dir / "strategy-route-3d.png"
    if not image_path.exists():
        raise RuntimeError(f"{atom_dir}: missing Gemini route image")
    receipt_path = atom_dir / "strategy-route-3d.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.exists() else {}
    route_feasibility = receipt.get("route_feasibility") or {}
    review_log_text = (atom_dir / "REVIEW_LOG.md").read_text(encoding="utf-8") if (atom_dir / "REVIEW_LOG.md").exists() else ""
    six_round_complete = all(f"student-r{index}" in review_log_text for index in (1, 2, 3)) and all(
        f"ieee-r{index}" in review_log_text for index in (1, 2, 3)
    )
    review_badge = "六轮语义审稿：已闭合" if six_round_complete else "六轮语义审稿：未完成（初版）"
    review_notice = (
        "本原子已按 REVIEW_LOG 完成 3 轮新生 + 3 轮 IEEE 语义审稿；本次重建不改变其裁决状态。"
        if six_round_complete
        else "本轮只完成视觉与机械门，尚未逐原子完成 3 轮新生 + 3 轮 IEEE 语义审稿。"
    )

    route_legend = []
    route_cards = []
    for route_id, summary, evidence, gap in routes:
        label, css_role = role.get(route_id, ("其他/拒绝路线", "neutral"))
        feasibility = route_feasibility.get(route_id) or {}
        probability_class = str(feasibility.get("class", "undetermined"))
        probability_label = PROBABILITY.get(probability_class, PROBABILITY["undetermined"])[0]
        probability_html = (
            '<span class="probability-badge selected">当前主选（不使用备选可行概率徽标）</span>'
            if route_id == primary
            else f'<span class="probability-badge probability-{escape(probability_class)}">可行概率：{escape(probability_label)}</span>'
        )
        route_legend.append(
            f'<li class="legend-item {css_role}"><span class="swatch"></span><b>{escape(label)} {escape(route_id)}</b>'
            f'{probability_html}</li>'
        )
        route_cards.append(
            f'<article class="route-card {css_role}"><h3>{escape(label)} · {escape(route_id)}</h3>'
            f'<p>{escape(summary)}</p><p><b>主要差异/待证：</b>{escape(gap)}</p>'
            f'<p class="evidence">usecase 锚点：{escape(evidence)}</p>'
            f'<p class="evidence"><b>可行概率依据：</b>{escape(str(feasibility.get("basis", "receipt 未记录依据")))}</p></article>'
        )

    acceptance_display = [str(item) for item in acceptance] or ["验收合同见 atom.yaml 或 usecase.md 的原子功能界定；路线不得自行扩大范围。"]
    if atom_id == "L02.A06":
        acceptance_display = [
            "给出显式组件名时，Activity 与 Service 都必须能返回对应的 Android 类型信息。",
            "Intent 转成 Want 后，package/class 必须逐字保持，不得追加后缀或重选组件。",
        ]
    acceptance_html = "".join(f"<li>{escape(item)}</li>" for item in acceptance_display)
    route_order = " → ".join(route_id for route_id, _, _, _ in routes)
    alt = (
        f"{atom_id} 单图多路线三维软件栈比较图；灰色背景依次呈现 Android App、AOSP V14 Framework/API、"
        f"WestLake Adapter Boundary、OpenHarmony 6.1 System Services、OH 6.1 Kernel / Storage / Device。"
        f"绿色为主选 {primary}，橙色为次选 {backup}，"
        + (f"紫色为第三路线 {third}，" if third else "")
        + "灰色为共享软件栈、输入输出、系统边界、连接结构以及其余路线。"
    )
    a_side = first_case_block(use_body, (r"AOSP", r"Android.*正主"))
    b_side = first_case_block(use_body, (r"OpenHarmony", r"HarmonyOS", r"OH.*侧"))
    confidence = strategy_meta.get("confidence", "未标注")
    verdict = str(strategy_meta.get("verdict_status", "待用户确认"))
    review_status = str(strategy_meta.get("review_status", "未审视"))
    selected_route = str(strategy_meta.get("selected_route", ""))
    protected_decision = any(token in verdict + review_status for token in ("用户已确认", "已审视", "已确认"))
    default_confirmed = "默认选项" in verdict
    existing_protected = protected_decision and not default_confirmed
    default_route = selected_route if existing_protected and selected_route in valid_routes else primary
    recommendation_condition = str(strategy_meta.get("recommendation_condition", ""))
    if not recommendation_condition and "条件" in str(strategy_meta.get("recommended", "")):
        recommendation_condition = str(strategy_meta.get("recommended"))
    if existing_protected:
        preselection_label = f"用户已确认·既有选择受保护：{default_route}"
        preselection_guard = "既有人工选择不会被批量生成覆盖；仍可由用户重新调整。"
    else:
        preselection_label = f"用户已确认·默认选项·可重新调整：{default_route}"
        preselection_guard = "本轮以 strategy.md 的 recommended 作为正式方向选择；方向确认不等于实现批准或验收通过。"
    if recommendation_condition:
        preselection_guard += f" 条件性推荐前置：{recommendation_condition}；前置未满足不得进入实现。"
    evidence_blockers = []
    if str(confidence).strip().lower() == "low":
        evidence_blockers.append("低置信")
    if re.search(
        r"needs[-_ ]source",
        " ".join(str(strategy_meta.get(key, "") or "") for key in ("source_status", "evidence_status", "status"))
        + "\n"
        + strategy_body,
        re.I,
    ):
        evidence_blockers.append("needs-source")
    if evidence_blockers:
        preselection_guard += f" 证据阻断：{'、'.join(evidence_blockers)} 尚未闭合，不得进入实现批准或验收。"
    statement = str((atom.get("behavior_contract") or {}).get("statement", title))
    plain_statement = (
        "给定 Android 组件名，系统必须找到对应的 Activity 或 Service 信息；"
        "随后转换成 OpenHarmony Want 时，原包名和类名一个字都不能被改掉。"
        if atom_id == "L02.A06"
        else f"本原子要把“{statement}”变成可独立观察、可失败、可与原生系统比较的行为合同。"
    )
    generic_terms = """<dl><dt>范本</dt><dd>当前唯一有权决定“这个原子算不算通过”的最小验收合同。</dd><dt>oracle（对错基准）</dt><dd>用来比较对错的原生 Android 行为基准，不是西湖实现先例。</dd><dt>AonB</dt><dd>运行时 A 不改，在操作系统 B 的边界做兼容翻译。</dd><dt>adapter boundary（适配边界）</dt><dd>Android 可见语义与 OpenHarmony 能力之间显式翻译、校验和失败的位置。</dd><dt>fixture（固定测试样本）</dt><dd>为比较路线而固定不变的最小输入、状态和预期输出。</dd><dt>falsifier（证伪条件）</dt><dd>能具体推翻某条路线的观测条件，不是“尚未实现”或一般编码缺陷。</dd></dl>"""
    a06_terms = """<dl><dt>范本</dt><dd>当前唯一有权决定“这个原子算不算通过”的最小验收合同。</dd><dt>oracle（对错基准）</dt><dd>用来比较对错的原生行为基准，不是西湖实现先例。</dd><dt>AonB</dt><dd>运行时 A 不改，在操作系统 B 的边界做兼容翻译。</dd><dt>BMS</dt><dd>OpenHarmony 的 Bundle Manager Service，负责包与组件信息。</dd><dt>typed metadata（带类型的元数据）</dt><dd>有明确字段类型的 ActivityInfo/ServiceInfo 等结构，不是字符串猜测。</dd><dt>identity / projection（身份 / 投影）</dt><dd>identity 是原包名和类名；projection 是把已确定结果翻译成 Want，但不再做第二次选择。</dd><dt>sidecar（伴随进程）</dt><dd>主进程之外专门提供 resolver 的伴随进程。</dd><dt>fixture（固定测试样本）</dt><dd>为比较两条路线而固定不变的最小测试 APK/清单样本。</dd><dt>flags（查询标志）</dt><dd>调用 API 时控制查询范围和行为的选项位。</dd></dl>"""
    terms_html = a06_terms if atom_id == "L02.A06" else generic_terms
    route_lookup = {route_id: summary for route_id, summary, _, _ in routes}
    route_gap = {route_id: gap for route_id, _, _, gap in routes}
    caption = (
        f"<b>灰色软件栈上下文：</b>Android App → AOSP V14 Framework/API → WestLake Adapter Boundary → "
        f"OpenHarmony 6.1 System Services → OH 6.1 Kernel / Storage / Device。绿色 {escape(primary)}：{escape(route_lookup.get(primary, '见 routemap.md'))}；"
        f"橙色 {escape(backup)}：{escape(route_lookup.get(backup, '见 routemap.md'))}；"
        + (f"紫色 {escape(third)}：{escape(route_lookup.get(third, '见 routemap.md'))}；" if third else "本原子没有第三条合法候选，因此不伪造紫色路线；")
        + "灰色还表示共享输入输出、共享段、边界、非路线结构及第四/第五路线。"
    )
    third_notice = (
        f'<div class="notice"><b>为什么紫色 {escape(third)} 只排第三：</b>{escape(route_gap.get(third, "证据与适配条件见 routemap.md"))}。完整证据见 <code>routemap.md</code>。</div>'
        if third
        else '<div class="notice"><b>路线数诚实性：</b>routemap 只有两条合法候选；本页不为了配色要求伪造第三路线。反例或被拒路线只能以灰色背景出现。</div>'
    )
    flow_input = "Android Intent + 组件状态" if atom_id == "L02.A06" else "Android 可见请求 + 固定 fixture 状态"
    flow_output = "typed Activity/Service + 原样 Want identity" if atom_id == "L02.A06" else "Android 可观察结果 / 明确错误"
    questions_html = (
        '<ol><li><b>主选怎样才算被推翻？</b> 提示：同一 fixture 下显式 Activity/Service 无法对齐 AOSP，且修复会越过允许边界，才触发切线；普通实现 bug 不算。</li><li><b>为什么不是直接选次选？</b> 提示：R2 链路短，但 Service 正例缺失，OH 查询规则也不能自动当 Android 规则。</li><li><b>第三路线何时值得重开？</b> 提示：先有 guest/sidecar 项目决议，再有完整 typed query/response 原型；只有 launch forwarding 不够。</li><li><b>怎样避免案例数量误导？</b> 提示：分别标出 oracle、B 能力、拓扑类比、失败实现和反例，再判断每条路线真正被证明到哪一步。</li></ol>'
        if atom_id == "L02.A06"
        else '<ol><li><b>主选的最小证伪是什么？</b> 提示：必须是范本上可重复的差分，不能用“还没实现”代替。</li><li><b>何时切到次选？</b> 提示：先满足 strategy.md 的触发条件，再用同一 fixture 与同一 oracle 比较。</li><li><b>第三路线或其他路线为何靠后？</b> 提示：检查它缺的是语义、拓扑、权限、时序还是证据，而不是只比较开发成本。</li><li><b>图中软件栈如何帮助判断？</b> 提示：沿每条颜色看它跨过哪些灰色层、谁拥有状态、哪里发生翻译与失败。</li></ol>'
    )
    newer_reference_count = len(re.findall(r"AOSP[- ]V?15\b|(?:OpenHarmony|OH)[- ]V?7\b", use_body + route_body + strategy_body, re.I))
    version_gate = (
        f'<div class="notice"><b>目标版本证据门：</b>产品基线固定为 AOSP V14 + OpenHarmony 6.1。当前输入仍含 {newer_reference_count} 处 V15/V7 引用；逐项完成版本差分核验前，它们只能作为外部参考，不能直接证明目标版本可实现。</div>'
        if newer_reference_count
        else '<div class="notice"><b>目标版本证据门：</b>产品基线固定为 AOSP V14 + OpenHarmony 6.1；任何新版本资料只能作为外部参考。</div>'
    )

    html = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(atom_id)} {escape(alias)} · Strategy Review</title>
<style>
:root{{--primary:{COLORS['primary']};--backup:{COLORS['backup']};--third:{COLORS['third']};--neutral:{COLORS['neutral']};--ink:#20242b;--muted:#66707c;--paper:#fff;--bg:#f4f5f7;--line:#d7dadd}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.75 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}}
main{{max-width:1040px;margin:auto;background:var(--paper);padding:42px clamp(20px,5vw,64px) 80px}}h1{{margin:0;font-size:clamp(26px,4vw,42px);line-height:1.2}}h2{{margin:46px 0 14px;padding-bottom:8px;border-bottom:2px solid var(--line);font-size:23px}}h3{{font-size:18px}}p,li{{max-width:82ch}}code{{background:#f0f1f3;padding:1px 4px;border-radius:4px}}table{{width:100%;border-collapse:collapse;margin:16px 0;font-size:14px}}th,td{{padding:9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}th{{background:#f1f2f4}}
.meta{{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0 28px}}.badge{{border:1px solid var(--line);border-radius:999px;padding:4px 10px;color:var(--muted)}}.notice{{padding:14px 16px;border-left:4px solid var(--neutral);background:#f4f5f6}}.route-figure{{margin:24px 0}}.route-figure img{{display:block;width:100%;height:auto;background:#f5f5f5}}.route-figure figcaption{{color:var(--muted);font-size:13px;margin-top:8px}}.flow-key{{display:grid;grid-template-columns:1fr auto 1.4fr auto 1fr;gap:8px;align-items:center;margin:12px 0;color:#4f565e;text-align:center}}.flow-key .arrow{{color:var(--neutral);font-size:24px}}.legend{{list-style:none;padding:0;display:flex;flex-wrap:wrap;gap:12px;margin:12px 0}}.legend-item{{display:flex;flex-wrap:wrap;gap:7px;align-items:center}}.swatch{{width:28px;height:10px;border-radius:3px;background:var(--neutral)}}.primary .swatch{{background:var(--primary)}}.backup .swatch{{background:var(--backup)}}.third .swatch{{background:var(--third)}}.probability-badge{{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:700;border:1px solid #70757a;background:#9AA0A6;color:#111}}.probability-high{{background:#39D353;color:#071b0d}}.probability-low{{background:#8B1E1E;color:#fff}}.probability-almost_impossible{{background:#FF2B2B;color:#111}}.probability-undetermined{{background:#9AA0A6;color:#111}}.probability-badge.selected{{background:#fff;border-color:var(--primary)}}
.route-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}}.route-card{{border-top:7px solid var(--neutral);padding:12px 14px;background:#f7f7f7}}.route-card.primary{{border-color:var(--primary);background:#eef9f2}}.route-card.backup{{border-color:var(--backup);background:#fff6e8}}.route-card.third{{border-color:var(--third);background:#f5efff}}.route-card h3{{margin:0 0 6px}}.evidence{{font-size:13px;color:var(--muted)}}
.decision{{margin-top:28px;padding:20px;border:2px solid var(--neutral)}}.preselection{{padding:12px 14px;border-left:5px solid var(--primary);background:#eef9f2}}button{{font:600 14px inherit;padding:10px 14px;margin:6px;border:0;border-radius:6px;cursor:pointer}}button.primary{{background:var(--primary);color:#fff}}button.backup{{background:var(--backup);color:#23170a}}button.default-selected{{outline:4px solid #20242b;outline-offset:2px}}button.concern{{background:#d8dadd;color:#24272b}}button.reject{{background:#b8bcc1;color:#181a1d}}textarea{{width:100%;min-height:90px;padding:10px;border:1px solid var(--line)}}#fallback{{display:none;background:#f0f1f3;padding:10px;overflow:auto}}@media(max-width:600px){{main{{padding:24px 16px 56px}}table{{display:block;overflow-x:auto}}}}
</style></head><body><main>
<header><p>WestLake · 原子路线推荐教科书</p><h1>{escape(atom_id)} · {escape(alias)}</h1><p>{escape(title)}</p>
<div class="meta"><span class="badge">主选 {escape(primary)}</span><span class="badge">次选 {escape(backup)}</span><span class="badge">目标基线 AOSP V14 + OH 6.1</span><span class="badge">置信度 {escape(str(confidence))}</span><span class="badge">{escape(str(verdict))}</span><span class="badge">{escape(review_badge)}</span></div></header>

<section><h2>导论 · 学习目标</h2><p>读完本页，应能用范本（原子唯一验收合同）判断各路线，而不是被实现投入、图像颜色或案例数量代替证据；后文简称“范本”。</p><div class="notice"><b>方向确认不等于实现批准或验收通过。</b> 图中的绿色、橙色、紫色表达已确认方向的路线角色，不表达“已经实现”或“设备已验证”。{escape(review_notice)}</div>{version_gate}</section>

<section><h2>第一章 · 问题背景（Why）</h2><p><b>先说人话：</b>{escape(plain_statement)}</p><p class="evidence">规格原句：{escape(statement)}</p><h3>范本</h3><ul>{acceptance_html}</ul><p>范围以 <code>atom.yaml</code>（若本地未镜像则以 usecase.md 的原子界定）为准；扩展目标必须先修改原子合同，再进入路线淘汰和验证。</p><details><summary>本页术语</summary>{terms_html}</details></section>

<section><h2>第二章 · 历史先例（What others did）</h2>{md(usecase_overview(use_body))}<p>逐案源码 locator 保留在 <code>usecase.md</code>；这里先建立“谁是 oracle、谁只是 B 能力、谁是反例”的地图，避免案例数量冒充路线成熟度。</p></section>

<section><h2>第三章 · Android 侧做法（A-side authority）</h2>{md(a_side)}</section>

<section><h2>第四章 · OpenHarmony 侧做法（B-side counterpart）</h2>{md(b_side)}<div class="notice">B 侧“有相似能力”不自动等于 Android 可观察语义等价；差异必须留给 adapter 显式处理或响亮失败。</div></section>

<section><h2>第五章 · 西湖路线设计空间</h2>
<p class="notice"><b>双编码读图：</b>路线线色只表示主绿、次橙、第三紫及其余灰的身份；每条非主选路线旁的“可行概率”徽标另以颜色+文字表达高概率、低概率、almost impossible 或证据不足。徽标不得改染路线；缺证据只能保持灰色未定。</p>
<figure class="route-figure"><div class="flow-key"><span>共同输入<br>{escape(flow_input)}</span><span class="arrow">→</span><b>同一灰色软件栈中的多条跨层技术路线</b><span class="arrow">→</span><span>共同输出<br>{escape(flow_output)}</span></div><img src="{image_data(image_path)}" alt="{escape(alt)}"><ul class="legend">{''.join(route_legend)}</ul><figcaption>{caption} Gemini model={escape(str(receipt.get('model', 'gemini')))}；image SHA-256={escape(str(receipt.get('image_sha256', 'not-recorded')))}。</figcaption></figure>
<div class="route-grid">{''.join(route_cards)}</div>{third_notice}</section>

<section><h2>第六章 · 教授推荐</h2>{md(selected_strategy(strategy_body))}<p class="evidence">完整原则矩阵、证据状态和边界原文见 <code>strategy.md</code>。</p></section>

<section><h2>第七章 · 思考与判断</h2>{questions_html}</section>

<section class="decision"><h2>第八章 · 方向选择</h2><p class="preselection"><b>{escape(preselection_label)}</b>。{escape(preselection_guard)} 当前版本证据门、needs-source 与低置信状态不因方向确认而解除。</p><form id="decision-form"><input type="hidden" name="atom_id" value="{escape(atom_id)}"><input type="hidden" name="default_route" value="{escape(default_route)}"><p><button class="primary{' default-selected' if default_route == primary else ''}" name="choice" value="primary" data-route="{escape(primary)}" aria-pressed="{'true' if default_route == primary else 'false'}">保持主选 {escape(primary)}</button><button class="backup{' default-selected' if default_route == backup else ''}" name="choice" value="backup" data-route="{escape(backup)}" aria-pressed="{'true' if default_route == backup else 'false'}">重新调整为次选 {escape(backup)}</button><button class="concern" name="choice" value="concern">CONCERN</button><button class="reject" name="choice" value="reject">拒绝</button></p><ul><li><b>保持主选：</b>维持 {escape(primary)} 的方向选择并进入最小证伪，不代表路线已实现或验收通过。</li><li><b>重新调整为次选：</b>改为 {escape(backup)}，接受其窄范围和待证条件，并用同一 oracle 验证。</li><li><b>CONCERN：</b>方向先不改，记录必须补齐的证据或规格问题。</li><li><b>拒绝：</b>撤销当前方向选择，回到 usecase/routemap 重开空间。</li></ul><label for="note">调整意见</label><textarea id="note" name="note" placeholder="写明理由、接受的代价和下一证据"></textarea><p><button type="button" id="export">导出 JSON / Markdown</button></p><div id="result"></div><pre id="fallback"></pre></form></section>
<footer><p class="evidence">路线顺序：{escape(route_order)} · 本页不改变 strategy.md 的 <code>review_status</code>，确认由人类架构师完成。</p></footer>
</main><script>
const form=document.getElementById('decision-form'),result=document.getElementById('result'),fallback=document.getElementById('fallback');
function record(choice){{return{{atom_id:form.atom_id.value,default_route:form.default_route.value,choice,note:form.note.value.trim(),ts:new Date().toISOString()}}}}
form.addEventListener('click',async e=>{{if(e.target.tagName!=='BUTTON'||!e.target.name)return;e.preventDefault();const rec=record(e.target.value);try{{const r=await fetch('http://127.0.0.1:8577/decide',{{method:'POST',headers:{{'Content-Type':'application/x-www-form-urlencoded'}},body:new URLSearchParams(rec)}});if(!r.ok)throw Error();result.textContent='✓ 已记录：'+e.target.textContent}}catch(_){{fallback.style.display='block';fallback.textContent=JSON.stringify(rec,null,2)}}}});
document.getElementById('export').addEventListener('click',()=>{{const rec=record('export'),md=`# ${{rec.atom_id}} strategy decision\\n\\n- choice: ${{rec.choice}}\\n- note: ${{rec.note}}\\n- ts: ${{rec.ts}}\\n`,blob=new Blob([JSON.stringify(rec,null,2)+'\\n\\n'+md],{{type:'text/plain'}}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=rec.atom_id.replace('.','-')+'-strategy-decision.txt';a.click();URL.revokeObjectURL(a.href)}});
</script></body></html>"""
    output.write_text(html, encoding="utf-8")
    print(f"OK {atom_id} {output} {output.stat().st_size}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("atom_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    atom_dir = args.atom_dir.resolve()
    output = args.output.resolve() if args.output else atom_dir / "strategy-review.html"
    build(atom_dir, output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
