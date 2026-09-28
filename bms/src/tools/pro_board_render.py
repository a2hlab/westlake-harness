#!/usr/bin/env python3
"""Render the Pro lifecycle kanban from var/state/pro-board/*.json fragments.

Each lane agent owns one fragment file; this script is the only writer of the
merged board:
  - worker/01.kanban/pro-lifecycle-board.md   (Markdown)
  - out/pro-lifecycle-board.json              (merged JSON)
  - worker/01.kanban/pro-lifecycle-board.html (self-refreshing HTML board)
Format follows out/lane-board.json conventions (headline + lanes + per-Fn status).
"""
import html as html_mod
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/Volumes/Bridge")
FRAG_DIR = ROOT / ".state" / "pro-board"
MD_OUT = ROOT / "worker" / "01.kanban" / "pro-lifecycle-board.md"
JSON_OUT = ROOT / "out" / "pro-lifecycle-board.json"
HTML_OUT = ROOT / "worker" / "01.kanban" / "pro-lifecycle-board.html"

FLOORS = [f"Fn{i:02d}" for i in range(1, 13)]
STAGES = ["define", "research", "case_mining", "route_map", "strategy_review",
          "design_closure", "action_design", "action_implement", "action_verify", "git_push"]
STAGE_SHORT = {"define": "Def", "research": "Res", "case_mining": "Case", "route_map": "Route",
               "strategy_review": "Strat", "design_closure": "DClos", "action_design": "ADes",
               "action_implement": "AImpl", "action_verify": "AVer", "git_push": "Push"}
STATUS_MARK = {"NOT_ENTERED": "·", "IN_PROGRESS": "▶", "PASS": "✓", "FAIL": "✗",
               "BLOCKED": "■", "SPEC_GAP": "?", None: "·"}
BAD_STATES = ("BLOCKED", "FAIL", "SPEC_GAP", "STALLED")


def esc(s):
    return html_mod.escape(str(s if s is not None else ""))


def load_fragments():
    frags = []
    for p in sorted(FRAG_DIR.glob("*.json")):
        try:
            frags.append(json.loads(p.read_text()))
        except Exception as e:
            print(f"WARN: skip {p.name}: {e}", file=sys.stderr)
    return frags


def floor_view(frags):
    view = {}
    for f in frags:
        # Completed audit snapshots stay visible in the lane history, but must
        # never overwrite the live Fn floor projection owned by active lanes.
        if (f.get("authoritative_global_audit") is False or
                f.get("phase") == "COMPLETED_SNAPSHOT_SUPERSEDED_BY_ACTIVE_GROUP_FRAGMENTS"):
            continue
        for floor, info in (f.get("floors") or {}).items():
            view[floor] = {
                "lane": f.get("lane"),
                "stage": info.get("stage"),
                "stage_status": info.get("stage_status"),
                "actions_done": info.get("actions_done", 0),
                "actions_total": info.get("actions_total", 0),
                "verdict": info.get("verdict"),
                "note": info.get("note", ""),
                "updated_at": info.get("updated_at"),
            }
    return view


def lane_list(frags):
    lanes = []
    for f in frags:
        if f.get("fragment_type") == "orchestration":
            continue
        ag = f.get("agent") or {}
        if isinstance(ag, str):
            ag = {"cli": ag}
        elif not isinstance(ag, dict):
            ag = {}
        lanes.append({
            "id": f.get("lane"),
            "agent_cli": ag.get("cli"),
            "orca_handle": ag.get("orca_handle"),
            "started_at": ag.get("started_at"),
            "status": f.get("status", "UNKNOWN"),
            "device_used": f.get("device_used"),
            "status_source": "var/state/pro-board fragments + orca terminal list",
        })
    return lanes


def build_headline(lanes, orchestration):
    lane_running = sum(1 for lane in lanes if lane["status"] == "RUNNING")
    lane_done = sum(1 for lane in lanes if lane["status"] == "DONE")
    lane_stalled = [lane["id"] for lane in lanes
                    if lane["status"] in ("STALLED", "BLOCKED")]
    tasks = orchestration.get("active_orca_tasks", [])
    task_statuses = [str(task.get("status", "")) for task in tasks]
    task_dispatched = sum(1 for status in task_statuses
                          if status.startswith("DISPATCHED"))
    task_ready = sum(1 for task in tasks
                     if str(task.get("status", "")).startswith(("READY", "PENDING")))
    task_completed = sum(1 for status in task_statuses
                         if status.startswith("COMPLETED"))
    task_failed = sum(1 for status in task_statuses
                      if status.startswith("FAILED"))
    stalled_text = "、".join(lane_stalled) if lane_stalled else "无"
    return (f"LANE 运行 {lane_running} / 完成 {lane_done}；"
            f"TASK 执行 {task_dispatched} / 排队 {task_ready} / 完成 {task_completed} / 失败替换 {task_failed}；"
            f"设备阻塞 {stalled_text}")


def stage_marks(v):
    marks = []
    cur, cur_st = v["stage"], v["stage_status"]
    for s in STAGES:
        if cur is None:
            marks.append(("·", "none"))
        elif STAGES.index(s) < STAGES.index(cur):
            marks.append(("✓", "pass"))
        elif s == cur:
            cls = {"IN_PROGRESS": "run", "PASS": "pass", "FAIL": "fail",
                   "BLOCKED": "block", "SPEC_GAP": "gap"}.get(cur_st, "none")
            marks.append((STATUS_MARK.get(cur_st, "?"), cls))
        else:
            marks.append(("·", "none"))
    return marks


def collect_difficulties(fv, apk_frags):
    """真实难点：楼层阻塞/失败 + APK 真机卡点。"""
    items = []
    for floor in FLOORS:
        v = fv.get(floor)
        if v and v["stage_status"] in BAD_STATES:
            items.append({
                "kind": "楼层阻塞", "floor": floor, "stage": v["stage"],
                "status": v["stage_status"], "symptom": v["note"],
                "evidence": "", "lane": v["lane"], "updated_at": v["updated_at"],
            })
    for frag in apk_frags:
        for a in frag.get("apks", []):
            if a.get("verdict") and a.get("verdict") != "PASS":
                items.append({
                    "kind": "APK 真机卡点", "floor": a.get("blocker_fn"),
                    "stage": a.get("name"), "status": a.get("verdict"),
                    "symptom": a.get("symptom"), "evidence": a.get("evidence"),
                    "lane": frag.get("lane"), "updated_at": a.get("updated_at"),
                })
    return items


HTML_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="120">
<title>Fn01–Fn12 Pro 生命周期看板</title>
<style>
  :root {{ --bg:#0f1420; --card:#1a2233; --line:#2a3550; --fg:#dbe4f5; --dim:#8fa0bf; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--fg);
         font:14px/1.5 -apple-system,"PingFang SC","Helvetica Neue",sans-serif; }}
  header {{ padding:16px 24px; border-bottom:1px solid var(--line); display:flex;
           align-items:baseline; gap:16px; flex-wrap:wrap; }}
  h1 {{ font-size:20px; margin:0; }}
  .headline {{ color:var(--dim); }}
  .refresh {{ margin-left:auto; color:var(--dim); font-size:12px; }}
  section {{ padding:16px 24px; }}
  h2 {{ font-size:15px; color:var(--dim); text-transform:uppercase; letter-spacing:.08em; }}
  .lanes {{ display:flex; gap:12px; flex-wrap:wrap; }}
  .lane {{ background:var(--card); border:1px solid var(--line); border-radius:10px;
          padding:10px 14px; min-width:230px; }}
  .lane b {{ font-size:14px; }}
  .lane .meta {{ color:var(--dim); font-size:12px; margin-top:4px; }}
  .badge {{ display:inline-block; padding:1px 8px; border-radius:8px; font-size:12px; margin-left:6px; }}
  .st-RUNNING {{ background:#123a2a; color:#4ade80; }}
  .st-PASS {{ background:#123a2a; color:#4ade80; }}
  .st-DONE,.st-COMPLETED {{ background:#1e3a5f; color:#60a5fa; }}
  .st-DISPATCHED {{ background:#1e3a5f; color:#60a5fa; }}
  .st-READY_QUEUED,.st-PENDING_DEP {{ background:#3a3a12; color:#facc15; }}
  .st-LAUNCHING {{ background:#3a3a12; color:#facc15; }}
  .st-STALLED,.st-BLOCKED,.st-FAIL {{ background:#4a1a1a; color:#f87171; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(340px,1fr)); gap:12px; }}
  .floor {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:12px 14px; }}
  .floor.bad {{ border-color:#7f2a2a; }}
  .floor h3 {{ margin:0 0 8px; font-size:15px; display:flex; justify-content:space-between; }}
  .floor h3 .v {{ font-size:12px; color:var(--dim); font-weight:normal; }}
  .pipe {{ display:flex; gap:4px; }}
  .cell {{ flex:1; text-align:center; background:#101828; border:1px solid var(--line);
          border-radius:6px; padding:4px 0 2px; }}
  .cell .m {{ font-size:15px; display:block; }}
  .cell .s {{ font-size:9px; color:var(--dim); display:block; }}
  .m.pass {{ color:#4ade80; }} .m.run {{ color:#60a5fa; }} .m.fail {{ color:#f87171; }}
  .m.block {{ color:#f87171; }} .m.gap {{ color:#fb923c; }} .m.none {{ color:#3b4a68; }}
  .fnote {{ color:var(--dim); font-size:12px; margin-top:8px; }}
  table {{ border-collapse:collapse; width:100%; }}
  th,td {{ border:1px solid var(--line); padding:6px 10px; text-align:left; font-size:13px; }}
  th {{ color:var(--dim); font-weight:600; background:#141b2c; }}
  .hard {{ background:var(--card); border:1px solid #7f2a2a; border-radius:10px; padding:4px 14px 12px; }}
  .hard td:first-child {{ white-space:nowrap; }}
  .ok {{ color:#4ade80; }}
  code {{ background:#101828; padding:1px 5px; border-radius:4px; font-size:12px; }}
</style>
</head>
<body>
<header>
  <h1>Fn01–Fn12 Pro 生命周期看板</h1>
  <span class="headline">{headline}</span>
  <span class="refresh">生成 {now} ｜ 每 120s 自刷新 ｜ 里程碑手动刷新 ｜ 真源 var/state/pro-board/*.json</span>
</header>

<section>
  <h2>四层并推分工</h2>
  <div class="lanes">{levels_html}</div>
  <div class="fnote">每个 Fn 同时核对四视图：{machine_views_html}；D600/Journey 是独立验证轴，不冒充语义层。</div>
  <div class="hard">{validation_axis_html}</div>
</section>

<section>
  <h2>Orca 任务 DAG</h2>
  {tasks_html}
</section>

<section>
  <h2>Agent 名册</h2>
  <div class="lanes">{lanes_html}</div>
</section>

<section>
  <h2>楼层进度（Fn01–Fn12 × 生命周期阶段）</h2>
  <div class="grid">{floors_html}</div>
</section>

<section>
  <h2>真实难点墙（真机 D600 / 真实 APK 暴露的阻塞）</h2>
  <div class="hard">{hard_html}</div>
</section>

<section>
  <h2>APK 全栈卡点台账</h2>
  {apk_html}
</section>

<section>
  <h2>上报（escalations）</h2>
  {esc_html}
</section>
</body>
</html>
"""


def render_html(now, headline, lanes, fv, apks, difficulties, escalations, orchestration):
    levels_html = "".join(
        f'<div class="lane"><b>{esc(level.get("level"))}</b>'
        f'<span class="badge st-{esc(level.get("status", "BLOCKED"))}">{esc(level.get("status", "BLOCKED"))}</span>'
        f'<div class="meta">owner {esc(level.get("owner", "-"))}<br>{esc(level.get("focus", ""))}</div></div>'
        for level in orchestration.get("levels", []))
    machine_views_html = " → ".join(esc(v) for v in orchestration.get("machine_views", [])) or "未登记"
    validation = orchestration.get("validation_axis", {})
    validation_axis_html = (
        f'<b>{esc(validation.get("name", "D600 / Journey"))}</b>'
        f'<span class="badge st-{esc(validation.get("status", "BLOCKED"))}">{esc(validation.get("status", "BLOCKED"))}</span>'
        f'<div class="fnote">{esc(validation.get("reason", "未登记"))}</div>'
    )
    tasks = orchestration.get("active_orca_tasks", [])
    if tasks:
        task_rows = "".join(
            f'<tr><td><code>{esc(task.get("id", "-"))}</code></td>'
            f'<td>{esc(task.get("lane", "-"))}</td><td>{esc(task.get("agent", "-"))}</td>'
            f'<td><span class="badge st-{esc(task.get("status", "BLOCKED"))}">'
            f'{esc(task.get("status", "BLOCKED"))}</span></td>'
            f'<td>{esc(task.get("boundary", ""))}</td></tr>'
            for task in tasks
        )
        tasks_html = ("<table><tr><th>Task</th><th>工作线</th><th>Agent</th>"
                      "<th>状态</th><th>权限/证据边界</th></tr>" + task_rows + "</table>")
    else:
        tasks_html = '<p class="fnote">当前没有登记 Orca 任务。</p>'
    lanes_html = "".join(
        f'<div class="lane"><b>{esc(l["id"])}</b>'
        f'<span class="badge st-{esc(l["status"])}">{esc(l["status"])}</span>'
        f'<div class="meta">{esc(l["agent_cli"])} ｜ <code>{esc((l["orca_handle"] or "-")[:18])}</code><br>'
        f'设备 {esc(l["device_used"] or "-")} ｜ 启动 {esc(l["started_at"] or "-")}</div></div>'
        for l in lanes)

    floors_html = ""
    for floor in FLOORS:
        v = fv.get(floor)
        bad = " bad" if v and v["stage_status"] in BAD_STATES else ""
        if not v:
            floors_html += (f'<div class="floor"><h3>{floor}<span class="v">未登记</span></h3>'
                            f'<div class="fnote">等待 lane 认领</div></div>')
            continue
        cells = "".join(
            f'<div class="cell"><span class="m {cls}">{mark}</span>'
            f'<span class="s">{STAGE_SHORT[s]}</span></div>'
            for (mark, cls), s in zip(stage_marks(v), STAGES))
        acts = f'{v["actions_done"]}/{v["actions_total"]}' if v["actions_total"] else "-"
        floors_html += (f'<div class="floor{bad}"><h3>{floor}'
                        f'<span class="v">{esc(v["lane"])} ｜ Actions {acts} ｜ {esc(v["verdict"] or "-")}</span></h3>'
                        f'<div class="pipe">{cells}</div>'
                        f'<div class="fnote">{esc(v["note"])} ｜ {esc(v["updated_at"] or "")}</div></div>')

    if difficulties:
        rows = "".join(
            f'<tr><td>{esc(d["kind"])}</td><td>{esc(d["floor"] or "-")}</td>'
            f'<td>{esc(d["stage"] or "-")}</td><td><span class="badge st-BLOCKED">{esc(d["status"])}</span></td>'
            f'<td>{esc(d["symptom"])}</td><td>{esc(d["evidence"] or "-")}</td>'
            f'<td>{esc(d["lane"])}</td><td>{esc(d["updated_at"] or "-")}</td></tr>'
            for d in difficulties)
        hard_html = ("<table><tr><th>类型</th><th>楼层</th><th>对象/阶段</th><th>状态</th>"
                     "<th>现象</th><th>证据</th><th>来源 lane</th><th>时间</th></tr>" + rows + "</table>")
    else:
        hard_html = '<p class="ok">当前无已上报的真机阻塞；demo-apk lane 探测结果出现后此处自动填充。</p>'

    if apks:
        rows = "".join(
            f'<tr><td>{esc(a.get("name"))}</td><td>{esc(a.get("deepest_fn") or "-")}</td>'
            f'<td>{esc(a.get("blocker_fn") or "-")}</td><td>{esc(a.get("verdict") or "-")}</td>'
            f'<td>{esc(a.get("symptom") or "")}</td><td>{esc(a.get("evidence") or "-")}</td>'
            f'<td>{esc(a.get("updated_at") or "-")}</td></tr>'
            for a in apks)
        apk_html = ("<table><tr><th>APK</th><th>最深到达</th><th>卡点 Fn</th><th>结论</th>"
                    "<th>现象</th><th>证据</th><th>时间</th></tr>" + rows + "</table>")
    else:
        apk_html = '<p class="fnote">尚无探测结果；明细台账见 <code>worker/01.kanban/pro-apk-blockers.md</code></p>'

    esc_html = f"<pre>{esc(escalations)}</pre>" if escalations else '<p class="fnote">无</p>'

    return HTML_PAGE.format(now=esc(now), headline=esc(headline), levels_html=levels_html,
                            machine_views_html=machine_views_html,
                            validation_axis_html=validation_axis_html, tasks_html=tasks_html,
                            lanes_html=lanes_html,
                            floors_html=floors_html, hard_html=hard_html,
                            apk_html=apk_html, esc_html=esc_html)


def main():
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    frags = load_fragments()
    fv = floor_view(frags)
    lanes = lane_list(frags)
    orchestration = next((f for f in frags if f.get("fragment_type") == "orchestration"), {})
    apk_frags = [f for f in frags if isinstance(f.get("apks"), list)]
    apks = [dict(a, source_lane=f.get("lane"))
            for f in apk_frags for a in f.get("apks", [])]

    headline = build_headline(lanes, orchestration)

    escalations = ""
    esc_file = FRAG_DIR / "escalations.md"
    if esc_file.exists():
        escalations = esc_file.read_text().strip()

    # ---- markdown ----
    lines = [
        "# Fn01–Fn12 Pro 生命周期看板",
        "",
        f"> 生成时间：{now}；真源：`var/state/pro-board/*.json`（各 lane 自报），由 `src/tools/pro_board_render.py` 渲染。",
        f">  headline：**{headline}**",
        "",
        "## 四层并推分工",
        "",
        "| 层级 | Owner | 状态 | 当前焦点 |",
        "|---|---|---|---|",
    ]
    for level in orchestration.get("levels", []):
        lines.append(f"| {level.get('level')} | {level.get('owner')} | {level.get('status')} | {level.get('focus')} |")
    lines += [
        "",
        "每个 Fn 的四视图：" + " → ".join(orchestration.get("machine_views", [])) + "；D600/Journey 为独立验证轴。",
        "",
        f"验证轴：{orchestration.get('validation_axis', {}).get('name', 'D600 / Journey')} ｜ "
        f"{orchestration.get('validation_axis', {}).get('status', 'BLOCKED')} ｜ "
        f"{orchestration.get('validation_axis', {}).get('reason', '未登记')}",
        "",
        "## Orca 任务 DAG",
        "",
        "| Task | 工作线 | Agent | 状态 | 权限/证据边界 |",
        "|---|---|---|---|---|",
    ]
    for task in orchestration.get("active_orca_tasks", []):
        lines.append(f"| {task.get('id', '-')} | {task.get('lane', '-')} | "
                     f"{task.get('agent', '-')} | {task.get('status', '-')} | "
                     f"{task.get('boundary', '')} |")

    lines += [
        "",
        "## Agent 名册",
        "",
        "| Lane | CLI | Orca handle | 状态 | 设备 | 启动时间 |",
        "|---|---|---|---|---|---|",
    ]
    for l in lanes:
        lines.append(f"| {l['id']} | {l['agent_cli']} | {l['orca_handle'] or '-'} | {l['status']} | {l['device_used'] or '-'} | {l['started_at'] or '-'} |")

    lines += [
        "",
        "## 楼层 × 生命周期阶段矩阵",
        "",
        "标记：`·` 未进入　`▶` 进行中　`✓` 通过　`✗` 失败　`■` 阻塞　`?` SPEC_GAP",
        "",
        "| 楼层 | Lane | " + " | ".join(STAGE_SHORT[s] for s in STAGES) + " | Actions | Verdict | 更新时间 | 备注 |",
        "|---|---|---|" + "---|" * (len(STAGES) + 3),
    ]
    for floor in FLOORS:
        v = fv.get(floor)
        if not v:
            lines.append(f"| {floor} | - | " + " | ".join("·" for _ in STAGES) + " | - | - | - | 未登记 |")
            continue
        marks = [m for m, _ in stage_marks(v)]
        acts = f"{v['actions_done']}/{v['actions_total']}" if v["actions_total"] else "-"
        lines.append(f"| {floor} | {v['lane']} | " + " | ".join(marks) +
                     f" | {acts} | {v['verdict'] or '-'} | {v['updated_at'] or '-'} | {v['note']} |")

    lines += ["", "## APK 全栈卡点（全部真机 APK lane）", ""]
    if apks:
        lines.append("| APK | 最深到达 | 卡点 Fn | 结论 | 现象 | 证据 | 时间 |")
        lines.append("|---|---|---|---|---|---|---|")
        for a in apks:
            lines.append(f"| {a.get('name')} | {a.get('deepest_fn') or '-'} | {a.get('blocker_fn') or '-'} | "
                         f"{a.get('verdict') or '-'} | {a.get('symptom') or ''} | {a.get('evidence') or '-'} | {a.get('updated_at') or '-'} |")
    else:
        lines.append("（尚无探测结果；明细台账见 `worker/01.kanban/pro-apk-blockers.md`）")

    difficulties = collect_difficulties(fv, apk_frags)
    lines += ["", "## 真实难点墙", ""]
    if difficulties:
        lines.append("| 类型 | 楼层 | 对象/阶段 | 状态 | 现象 | 证据 | 来源 | 时间 |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for d in difficulties:
            lines.append(f"| {d['kind']} | {d['floor'] or '-'} | {d['stage'] or '-'} | {d['status']} | "
                         f"{d['symptom']} | {d['evidence'] or '-'} | {d['lane']} | {d['updated_at'] or '-'} |")
    else:
        lines.append("当前无已上报的真机阻塞。")

    if escalations:
        lines += ["", "## 上报（escalations）", "", escalations]

    MD_OUT.parent.mkdir(parents=True, exist_ok=True)
    MD_OUT.write_text("\n".join(lines) + "\n")

    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps({
        "generated_at": now,
        "source": "var/state/pro-board/*.json",
        "headline": headline,
        "lanes": lanes,
        "floors": fv,
        "apks": apks,
        "difficulties": difficulties,
        "orchestration": orchestration,
    }, ensure_ascii=False, indent=2) + "\n")

    HTML_OUT.write_text(render_html(now, headline, lanes, fv, apks, difficulties, escalations, orchestration))
    print(f"OK board -> {MD_OUT} , {JSON_OUT} , {HTML_OUT}; headline: {headline}")


if __name__ == "__main__":
    main()
