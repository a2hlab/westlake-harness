#!/usr/bin/env python3
"""analyze-trace.py — 把 hitrace/atrace 的 ftrace 文本按 ab-compare-plan §4 里程碑归类。

**为什么不是简单 grep 计数**：里程碑分布在不同进程里。§4「谁能看见」列写明——
M04/M06/M15 由应用进程自己发；M05/M14 由 AMS（foundation）发；M09/M12/M13 由
RenderService / sceneboard 发。一刀切按应用 PID 过滤会把后两组错误归零，
那是把「事件在别的进程」误报成「事件没发生」，触犯 §6.3（`—` 不得写成 `✗`）。

故本脚本对每个里程碑输出：命中总数 + **按发出进程分布**，由读表人依 §4 判定，
脚本本身**不产出 ✓/✗ 结论**（§6.1 产物限定）。

用法:
  ./analyze-trace.py <framework.ftrace> [--app-pid N] [--out OBSERVABILITY.md]
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# ftrace 行首：  comm-TID  (  PGID) [cpu] flags  ts: event: payload
# PGID 为 "-----" 表示内核线程，无所属进程。
LINE_RE = re.compile(
    r"^\s*(?P<comm>.+?)-(?P<tid>\d+)\s+\(\s*(?P<pgid>[\d-]+)\)\s+"
    r"\[(?P<cpu>\d+)\]\s+\S+\s+(?P<ts>[\d.]+):\s+(?P<event>\w+):\s*(?P<payload>.*)$"
)

# 里程碑 → 关键字正则。关键字来自 OH 6.1 LTS 源码里的实际 trace 点名。
# 改动此表须同步 ab-compare-plan.md §4，并作废受影响的缺步清单。
MILESTONES: list[tuple[str, str]] = [
    ("M05 宿主派发启动", r"StartAbility|LoadAbility|AbilityTransaction"),
    ("M06 页面 onCreate", r"OnAbilityStart|AbilityWindowConfig|OnForeground"),
    ("M07 消息循环", r"EventRunner|EventHandler|FFRTQos"),
    # M08/M09 的关键字曾按 AOSP 命名猜测（CreateWindow / AddWindow），在 OH 6.1 上
    # 恒为 0。20260807-231552 那轮实测板上真实词汇是 SceneSession / ssm: 一族，
    # 已据此改写；`NativeWindow*` 是应用侧真正拿到画布后的调用。
    ("M08 应用要窗口", r"CreateAndConnectSpecificSession|RequestSceneSession|"
                       r"NativeWindowCreate|Window::Create|WindowScene|CreateSurface"),
    ("M09 宿主给窗口", r"SceneSession::Connect|SetWindowRect|UpdateSessionRect|"
                       r"WindowStage|NativeWindowFlushBuffer|ssm:.*Session"),
    ("M10/M11 测量绘制", r"FlushLayout|FlushRender|MarkDirtyNode|FlushVsync"),
    ("M12 帧交合成器", r"CommitAndReleaseLayers|RSMainThread|RequestNextVSync|ProcessData"),
    ("M13 首帧上屏", r"FirstFrame|CompleteFirstFrame|Repaint|DoComposition"),
    ("M14 前台报到完成", r"ForegroundTimeout|DispatchForeground|AbilityTransactionDone"),
    ("M15 触摸送达", r"PointerEvent|DispatchTouchEvent|InputHandler|OnInputEvent"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ftrace", type=Path)
    ap.add_argument("--app-pid", type=int, default=None,
                    help="应用进程 PID，用于标注哪些命中来自应用自身")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--top", type=int, default=5, help="每个里程碑列出前 N 个发出进程")
    args = ap.parse_args()

    if not args.ftrace.is_file():
        print(f"缺文件: {args.ftrace}", file=sys.stderr)
        return 1

    compiled = [(name, re.compile(pat, re.IGNORECASE)) for name, pat in MILESTONES]
    # pgid -> 该进程最常见的 comm，用作进程可读名
    pgid_names: dict[str, Counter] = defaultdict(Counter)
    # milestone -> pgid -> 命中数
    hits: dict[str, Counter] = {name: Counter() for name, _ in MILESTONES}
    total_lines = 0
    mark_lines = 0

    with args.ftrace.open("r", errors="replace") as fh:
        for line in fh:
            total_lines += 1
            m = LINE_RE.match(line)
            if not m:
                continue
            pgid = m.group("pgid")
            payload = m.group("payload")
            if m.group("event") == "tracing_mark_write":
                mark_lines += 1
                # B|pid|name 与 E|pid 的 pid 才是真正的发出进程；comm 那列是线程
                bar = payload.split("|", 2)
                if len(bar) >= 2 and bar[1].isdigit():
                    pgid = bar[1]
            pgid_names[pgid][m.group("comm").strip()] += 1
            for name, rx in compiled:
                if rx.search(payload):
                    hits[name][pgid] += 1

    def pname(pgid: str) -> str:
        if not pgid_names[pgid]:
            return f"pid{pgid}"
        return f"{pgid_names[pgid].most_common(1)[0][0]}({pgid})"

    out_lines: list[str] = []
    w = out_lines.append
    # 标题不写死「② 线」：本脚本已被 src/tools/devices/capture-oh-trace.sh 用于 ③ 线，
    # 写死会让 ③ 的产物自称 ②，是会误导读表人的产物污染。
    w("# 框架层观测面")
    w("")
    w("**本文件只报「哪个进程发了多少条」，不报「里程碑达没达」。**")
    w("判定须依 ab-compare-plan.md §4 的证据等级与 §6.3 三记号，由读表人做，脚本不越权。")
    w("")
    w(f"- trace 文件: `{args.ftrace.name}`（{args.ftrace.stat().st_size // 1024 // 1024} MB）")
    w(f"- 总行数: {total_lines:,}　可解析 mark 行: {mark_lines:,}")
    if args.app_pid:
        w(f"- 应用进程 PID: **{args.app_pid}**（下表中标 ★ 的即应用自身发出）")
    w("")
    w("## 按里程碑：命中数与发出进程分布")
    w("")
    w("| 里程碑 | 命中 | 发出进程（前若干） |")
    w("|---|---:|---|")
    for name, _ in MILESTONES:
        c = hits[name]
        total = sum(c.values())
        if total == 0:
            w(f"| {name} | 0 | **无命中 → 记 `—`（本轮关键字未覆盖 / 无观测能力），不得记 `✗`** |")
            continue
        parts = []
        for pgid, n in c.most_common(args.top):
            star = " ★" if args.app_pid and pgid == str(args.app_pid) else ""
            parts.append(f"{pname(pgid)}={n}{star}")
        w(f"| {name} | {total} | {', '.join(parts)} |")
    w("")
    w("## 读表提醒")
    w("")
    w("- 命中数**不是**里程碑达成度。同一个关键字可能被系统其他应用触发；")
    w("  必须看「发出进程」列确认它属于本次采集的应用或其宿主服务。")
    w("- M05/M14 预期由 AMS（`foundation`）发出，M09/M12/M13 预期由 RenderService /")
    w("  sceneboard 发出——它们**不在应用进程里**是正常的，不得因此记 `✗`。")
    w("- 关键字表改动须同步 §4 并作废受影响清单（§6.4）。")

    text = "\n".join(out_lines) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"写入 {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
