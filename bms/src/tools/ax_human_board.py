#!/usr/bin/env python3
"""Read-only AX workflow projection for a human-friendly HTML board."""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import os
import re
import signal
import socket
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AX_TASK_PATH = ROOT / ".agents/skills/ax-task/scripts/ax_task.py"
AX_SPEC = importlib.util.spec_from_file_location("ax_task_human_board", AX_TASK_PATH)
AX = importlib.util.module_from_spec(AX_SPEC)
assert AX_SPEC.loader is not None
AX_SPEC.loader.exec_module(AX)

BOARD_ROLES = {
    "5eab5860": "Golden（冻结成功代）",
    "5583f5be": "Integration（候选集成）",
    "5cd1e3dd": "Independent Verify（独立复验）",
    "61b06572": "Experiment-1",
    "654b3a6b": "Experiment-2",
    "5ea17192": "Experiment-3",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(raw, path)
    finally:
        if os.path.exists(raw):
            os.unlink(raw)


def command_output(command: list[str], timeout: float = 8.0) -> str:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout


def parse_orca(raw: str) -> dict[str, dict[str, Any]]:
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    terminals = payload.get("result", {}).get("terminals", payload.get("terminals", []))
    return {
        row["handle"]: row
        for row in terminals
        if isinstance(row, dict) and isinstance(row.get("handle"), str)
    }


def parse_hdc(raw: str) -> dict[str, str]:
    targets: dict[str, str] = {}
    for line in raw.splitlines():
        match = re.search(r"\b([0-9a-fA-F]{16,})\b.*\b(Connected|Offline)\b", line)
        if match:
            targets[match.group(1).lower()] = match.group(2)
    return targets


def ready_human_items(raw: str) -> list[str]:
    return re.findall(
        r"(?m)^- \[ \] \*\*([^*]+)\*\*.*?`READY_FOR_OWNER(?: · P0)?`",
        raw,
    )


def scan_results(path: Path) -> dict[str, str]:
    if not path.is_dir():
        return {}
    return {
        result.stem: str(result)
        for result in path.glob("*.result")
        if result.is_file()
    }


def dependency_wait(task: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> list[str]:
    return [
        dep
        for dep in task.get("deps", [])
        if by_id.get(dep, {}).get("state") != "completed"
    ]


def build_model(
    workflow: dict[str, Any],
    controller: dict[str, Any],
    human_todo: str,
    terminals: dict[str, dict[str, Any]],
    hdc_targets: dict[str, str],
    results: dict[str, str] | None = None,
) -> dict[str, Any]:
    flow = AX.human_flow_projection(workflow)
    if flow is None:
        raise ValueError("workflow does not contain the T16V fast-flow target")
    by_id = {task["id"]: task for task in workflow["tasks"]}
    controller_active = controller.get("active", {})
    results = results or {}
    active = []
    for task in workflow["tasks"]:
        if task.get("state") not in AX.ACTIVE_STATES:
            continue
        controller_row = controller_active.get(task["id"], {})
        worker = controller_row.get("worker") or task.get("orca", {}).get("worker")
        terminal = terminals.get(worker, {}) if worker else {}
        active.append(
            {
                "id": task["id"],
                "title": task["title"],
                "worker": worker or "未登记",
                "terminal_connected": terminal.get("connected"),
                "terminal_title": terminal.get("title") or "—",
                "attempt": controller_row.get("attempt") or task.get("attempts", 0),
                "result_received": task["id"] in results,
            }
        )
    blockers = [
        {
            "id": task["id"],
            "title": task["title"],
            "state": task["state"],
            "reason": task.get("blocker") or "未提供 blocker 摘要",
        }
        for task in workflow["tasks"]
        if task.get("state") in {"blocked", "failed"}
    ]
    ready_human = ready_human_items(human_todo)
    boards = []
    for prefix, role in BOARD_ROLES.items():
        matches = [
            (serial, status)
            for serial, status in hdc_targets.items()
            if serial.startswith(prefix)
        ]
        serial, status = matches[0] if matches else (prefix.upper(), "未枚举")
        boards.append({"serial": serial, "short": prefix.upper(), "role": role, "status": status})
    next_tasks = []
    goal_set = set(flow["goal_ids"])
    for task in workflow["tasks"]:
        if task["id"] not in goal_set or task["state"] != "queued":
            continue
        waits = dependency_wait(task, by_id)
        next_tasks.append(
            {
                "id": task["id"],
                "title": task["title"],
                "waits": waits,
                "ready": not waits,
            }
        )
    return {
        "generated_at": utc_now(),
        "workflow_id": workflow["workflow_id"],
        "title": workflow["title"],
        "flow": flow,
        "active": active,
        "blockers": blockers,
        "ready_human": ready_human,
        "boards": boards,
        "next_tasks": next_tasks,
        "controller_phase": workflow.get("runtime", {}).get("phase", "unknown"),
        "controller_paused": workflow.get("runtime", {}).get("paused", False),
        "result_count": len(results),
        "render_host": socket.gethostname(),
    }


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def state_badge(state: str) -> str:
    css = {
        "完成": "done",
        "在线": "done",
        "进行中": "active",
        "阻塞": "blocked",
        "离线": "blocked",
        "等待前置": "waiting",
    }.get(state, "waiting")
    return f'<span class="badge {css}">{esc(state)}</span>'


def render_html(model: dict[str, Any]) -> str:
    flow = model["flow"]
    percent = round(100 * flow["completed"] / flow["total"]) if flow["total"] else 0
    active_gates = "、".join(f"第 {index} 道门" for index in flow["active_gates"]) or "已抵达终点"
    milestone_rows = []
    for row in flow["milestones"]:
        ids = " ".join(f"<code>{esc(task_id)}</code>" for task_id in row["task_ids"])
        milestone_rows.append(
            "<tr>"
            f"<td class='gate'>{row['index']}</td>"
            f"<td><strong>{esc(row['title'])}</strong></td>"
            f"<td>{row['completed']} / {row['total']}</td>"
            f"<td>{state_badge(row['status'])}</td>"
            f"<td class='ids'>{ids}</td>"
            "</tr>"
        )
    active_cards = []
    for row in model["active"]:
        terminal_state = (
            "已连接" if row["terminal_connected"] is True
            else "未连接" if row["terminal_connected"] is False
            else "未查到"
        )
        active_cards.append(
            "<article class='task-card'>"
            f"<div><code>{esc(row['id'])}</code> <strong>{esc(row['title'])}</strong></div>"
            f"<div class='muted'>attempt {esc(row['attempt'])}</div>"
            f"<div class='terminal'>{esc(row['worker'])}</div>"
            f"<div class='muted'>{esc(terminal_state)} · {esc(row['terminal_title'])} · "
            f"result {'已到达' if row['result_received'] else '等待中'}</div>"
            "</article>"
        )
    if not active_cards:
        active_cards.append("<p class='quiet'>当前没有 active task。</p>")
    human_html = (
        "<div class='human-clear'>人类无需动作</div>"
        "<p class='muted'>没有 READY_FOR_OWNER · P0；WAITING_ON_AGENT_PACKET 仍由 Agent 先做实验。</p>"
        if not model["ready_human"]
        else "<div class='human-alert'>现在需要人类处理："
        + "、".join(f"<code>{esc(item)}</code>" for item in model["ready_human"])
        + "</div>"
    )
    if model["blockers"]:
        blocker_html = "".join(
            f"<li><code>{esc(row['id'])}</code> {esc(row['title'])}：{esc(row['reason'])}</li>"
            for row in model["blockers"]
        )
    else:
        waiting = next((row for row in model["next_tasks"] if row["waits"]), None)
        if waiting:
            blocker_html = (
                "<li>无 declared blocked/failed。下一结构门 "
                f"<code>{esc(waiting['id'])}</code> 正在等待 "
                + "、".join(f"<code>{esc(dep)}</code>" for dep in waiting["waits"])
                + "。</li>"
            )
        else:
            blocker_html = "<li>无 declared blocked/failed。</li>"
    board_rows = "".join(
        "<tr>"
        f"<td><code>{esc(row['short'])}</code></td>"
        f"<td>{esc(row['role'])}</td>"
        f"<td>{state_badge('在线') if row['status'] == 'Connected' else state_badge('离线')}</td>"
        f"<td class='ids'>{esc(row['serial'])}</td>"
        "</tr>"
        for row in model["boards"]
    )
    post_target = "、".join(f"<code>{esc(item)}</code>" for item in flow["after_target"]) or "无"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="20">
  <title>Bridge Unity 快线总体图</title>
  <style>
    :root {{ --bg:#08111f; --panel:#101d30; --line:#293b55; --text:#edf5ff;
      --muted:#9db0c8; --blue:#48a7ff; --green:#44d18d; --amber:#f5bd4f; --red:#ff6b78; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:linear-gradient(150deg,#07101d,#0b1830 55%,#07101d);
      color:var(--text); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
    main {{ max-width:1440px; margin:auto; padding:28px; }}
    header {{ display:flex; justify-content:space-between; gap:20px; align-items:flex-end; }}
    h1 {{ margin:0; font-size:clamp(28px,4vw,52px); }}
    h2 {{ margin:0 0 16px; font-size:21px; }}
    .muted,.quiet {{ color:var(--muted); }}
    .hero {{ display:grid; grid-template-columns:1.4fr 1fr 1fr; gap:14px; margin:22px 0; }}
    .panel,.metric {{ background:rgba(16,29,48,.92); border:1px solid var(--line);
      border-radius:16px; padding:20px; box-shadow:0 16px 50px rgba(0,0,0,.2); }}
    .metric strong {{ display:block; font-size:38px; margin:7px 0; }}
    .metric.primary strong {{ color:var(--blue); font-size:46px; }}
    .progress {{ height:14px; background:#1c2c42; border-radius:10px; overflow:hidden; margin-top:15px; }}
    .progress > div {{ height:100%; width:{percent}%; background:linear-gradient(90deg,var(--blue),#73e0ff); }}
    .grid {{ display:grid; grid-template-columns:1.4fr 1fr; gap:14px; margin-top:14px; }}
    table {{ width:100%; border-collapse:collapse; }}
    th,td {{ text-align:left; padding:11px 10px; border-bottom:1px solid var(--line); vertical-align:top; }}
    th {{ color:var(--muted); font-weight:600; }}
    .gate {{ width:42px; font-size:24px; color:var(--blue); font-weight:800; }}
    code,.terminal {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
    code {{ color:#b9ddff; }}
    .ids {{ font-size:12px; line-height:1.8; }}
    .badge {{ display:inline-block; border-radius:999px; padding:4px 9px; font-size:12px; font-weight:700; }}
    .done {{ color:var(--green); background:rgba(68,209,141,.13); }}
    .active {{ color:var(--blue); background:rgba(72,167,255,.13); }}
    .waiting {{ color:var(--amber); background:rgba(245,189,79,.12); }}
    .blocked {{ color:var(--red); background:rgba(255,107,120,.12); }}
    .tasks {{ display:grid; gap:10px; }}
    .task-card {{ border:1px solid var(--line); border-left:4px solid var(--blue); border-radius:10px; padding:13px; }}
    .terminal {{ margin-top:9px; font-size:12px; overflow-wrap:anywhere; color:#d9ebff; }}
    .human-clear,.human-alert {{ padding:16px; border-radius:12px; font-size:22px; font-weight:800; }}
    .human-clear {{ background:rgba(68,209,141,.13); color:var(--green); }}
    .human-alert {{ background:rgba(255,107,120,.13); color:var(--red); }}
    footer {{ margin-top:16px; color:var(--muted); font-size:12px; }}
    a {{ color:#85c8ff; }}
    @media (max-width:900px) {{ .hero,.grid {{ grid-template-columns:1fr; }} main {{ padding:16px; }} }}
  </style>
</head>
<body>
<main>
  <header>
    <div><div class="muted">Bridge ideal architecture → complex Unity G7</div>
      <h1>Unity 快线总体图</h1></div>
    <div class="muted">每 20 秒自动刷新 · renderer {esc(model['render_host'])}<br>{esc(model['generated_at'])}</div>
  </header>
  <section class="hero">
    <div class="metric primary"><span class="muted">通往 T16V</span>
      <strong>{flow['completed']} / {flow['total']} 步</strong>
      <div>前面已完成 {flow['completed']}，后面还剩 <b>{flow['remaining']}</b>。并行任务不是线性工期。</div>
      <div class="progress"><div></div></div></div>
    <div class="metric"><span class="muted">当前在哪</span><strong>{esc(active_gates)}</strong>
      <div>多道门可并行推进</div></div>
    <div class="metric"><span class="muted">当前终点</span><strong><code>T16V</code></strong>
      <div>复杂 Unity G7 的 main bytes 独立复验</div></div>
  </section>
  <section class="panel">
    <h2>七道门：一眼看清前后还有多少</h2>
    <table><thead><tr><th>门</th><th>里程碑</th><th>完成</th><th>状态</th><th>任务 ID</th></tr></thead>
      <tbody>{''.join(milestone_rows)}</tbody></table>
    <p class="muted">{post_target} 是目标完成后的工作，不计入上面的 {flow['total']} 步。</p>
  </section>
  <div class="grid">
    <section class="panel"><h2>现在正在跑（精确 terminal）</h2>
      <div class="tasks">{''.join(active_cards)}</div></section>
    <section class="panel"><h2>人类现在要做什么</h2>{human_html}
      <h2 style="margin-top:24px">当前卡点</h2><ul>{blocker_html}</ul></section>
  </div>
  <section class="panel" style="margin-top:14px"><h2>六台 D600 角色与在线状态</h2>
    <table><thead><tr><th>设备</th><th>角色</th><th>HDC</th><th>精确 serial</th></tr></thead>
      <tbody>{board_rows}</tbody></table>
  </section>
  <footer>只读聚合：workflow.json、controller-state.json、results/、.HumanTodoList.md、Orca terminal list、HDC target list。
    本页不写 workflow/controller/results，不派发任务，不操作设备。renderer
    <code>{esc(model['render_host'])}</code> · workflow <code>{esc(model['workflow_id'])}</code></footer>
</main>
</body>
</html>
"""


def render_once(args: argparse.Namespace) -> dict[str, Any]:
    if args.bundle_snapshot:
        bundle_path = Path(args.bundle_snapshot).expanduser().resolve()
        bundle = load_json(bundle_path)
        workflow = bundle["workflow"]
        controller = bundle["controller"]
        human_todo = bundle["human_todo"]
        terminals = parse_orca(bundle.get("orca_raw", ""))
        hdc_targets = parse_hdc(bundle.get("hdc_raw", ""))
        results = bundle.get("results", {})
        generated_dir = Path(args.output).expanduser().resolve().parent
    else:
        if not args.workflow or not args.controller_state:
            raise ValueError("--workflow and --controller-state are required without --bundle-snapshot")
        workflow_path = Path(args.workflow).expanduser().resolve()
        state_path = Path(args.controller_state).expanduser().resolve()
        human_path = Path(args.human_todo).expanduser().resolve()
        workflow = load_json(workflow_path)
        controller = load_json(state_path)
        human_todo = human_path.read_text(encoding="utf-8")
        results_path = (
            Path(args.results).expanduser().resolve()
            if args.results
            else workflow_path.parent / "results"
        )
        terminals = parse_orca(command_output(["orca", "terminal", "list", "--json"]))
        hdc_targets = parse_hdc(command_output([args.hdc, "list", "targets", "-v"]))
        results = scan_results(results_path)
        generated_dir = workflow_path.parent
    model = build_model(
        workflow,
        controller,
        human_todo,
        terminals,
        hdc_targets,
        results,
    )
    output = Path(args.output).expanduser().resolve()
    atomic_text(output, render_html(model))
    atomic_text(generated_dir / "TASKS.md", AX.render_tasks_md(workflow))
    atomic_text(generated_dir / "BACKLOG.md", AX.render_backlog_md(workflow))
    return {
        "generated_at": model["generated_at"],
        "output": str(output),
        "tasks_md": str(generated_dir / "TASKS.md"),
        "render_host": model["render_host"],
        "goal": {
            "completed": model["flow"]["completed"],
            "total": model["flow"]["total"],
            "remaining": model["flow"]["remaining"],
        },
        "active": [row["id"] for row in model["active"]],
        "human_action": model["ready_human"],
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--workflow")
    value.add_argument("--controller-state")
    value.add_argument("--bundle-snapshot")
    value.add_argument("--results")
    value.add_argument("--human-todo", default=str(ROOT / ".HumanTodoList.md"))
    value.add_argument("--output", required=True)
    value.add_argument(
        "--hdc",
        default="/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc",
    )
    sub = value.add_subparsers(dest="command", required=True)
    sub.add_parser("render")
    watch = sub.add_parser("watch")
    watch.add_argument("--interval", type=float, default=20.0)
    return value


def main() -> int:
    args = parser().parse_args()
    if args.command == "render":
        print(json.dumps(render_once(args), ensure_ascii=False, indent=2))
        return 0
    stop = False

    def request_stop(_signum: int, _frame: Any) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    while not stop:
        try:
            print(json.dumps(render_once(args), ensure_ascii=False), flush=True)
        except Exception as exc:  # keep the observer alive; never mutate controller state
            print(json.dumps({"generated_at": utc_now(), "error": str(exc)}, ensure_ascii=False), flush=True)
        deadline = time.monotonic() + max(args.interval, 1.0)
        while not stop and time.monotonic() < deadline:
            time.sleep(min(0.5, deadline - time.monotonic()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
