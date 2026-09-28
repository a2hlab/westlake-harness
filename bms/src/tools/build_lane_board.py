#!/usr/bin/env python3
"""build_lane_board.py — Bridge 并行 lane 状态看板生成器。

读 worker/lanes.yaml，结合进程状态、日志年龄、全库成熟度（STATUS.yaml /
DESIGN_SPEC）与 evidence 验证产出，生成：
  - docs/progress-lanes.md  人读看板
  - out/lane-board.json     机读版

仅依赖 stdlib + pyyaml。Python 3.9+。
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from collections import OrderedDict

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANES_YAML = os.path.join(REPO_ROOT, "worker", "lanes.yaml")
DEFAULT_OUT_MD = os.path.join(REPO_ROOT, "docs", "progress-lanes.md")
DEFAULT_OUT_JSON = os.path.join(REPO_ROOT, "out", "lane-board.json")

STALL_THRESHOLD_SEC = 10 * 60  # 日志 10 分钟无写入视为 STALLED
RECENT_RUN_DAYS = 7
FN_IDS = ["Fn%02d" % i for i in range(1, 13)]

ACTION_DIR_RE = re.compile(r"^Fn(\d{2})\.A(\d+)$")       # 扁平旧式 FnXX.AYY
ACTION_SUBDIR_RE = re.compile(r"^A(\d+)$")               # 两层新式 FnXX/AYY


# ---------------------------------------------------------------- lane 部分

def fmt_age(seconds):
    """把秒数格式化成人类可读的年龄字符串。"""
    if seconds is None:
        return "-"
    if seconds < 0:
        seconds = 0
    if seconds < 120:
        return "%ds" % seconds
    if seconds < 7200:
        return "%dm%02ds" % (seconds // 60, seconds % 60)
    if seconds < 172800:
        return "%dh%02dm" % (seconds // 3600, (seconds % 3600) // 60)
    return "%.1fd" % (seconds / 86400.0)


def fmt_size(nbytes):
    if nbytes is None:
        return "-"
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024 or unit == "GB":
            return "%.1f%s" % (nbytes, unit) if unit != "B" else "%dB" % nbytes
        nbytes /= 1024.0


def script_alive(lane_script):
    """pgrep -f 判断脚本进程是否存活。返回 (alive, pids)。"""
    try:
        out = subprocess.run(
            ["pgrep", "-f", lane_script],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, "pgrep 失败: %s" % exc
    pids = [p for p in out.stdout.split() if p.strip()]
    return (len(pids) > 0), pids


def assess_lane(lane, now):
    """对单条 lane 计算健康状态。"""
    entry = OrderedDict()
    entry["id"] = lane.get("id", "?")
    entry["scope"] = lane.get("scope", "")
    entry["host"] = lane.get("host", "")
    entry["device_needs"] = lane.get("device_needs", "")
    entry["note"] = lane.get("note", "")
    entry["status_source"] = lane.get("status_source", "")

    status_source = lane.get("status_source") or ""
    if "人工同步" in status_source:
        entry["status"] = "MANUAL"
        entry["detail"] = "status_source 标注人工同步，不做进程判定"
        return entry
    if (lane.get("status") or "").upper() == "PLANNED":
        entry["status"] = "PLANNED"
        entry["detail"] = "yaml 中登记为 PLANNED"
        return entry

    lane_script = lane.get("lane_script")
    log_rel = lane.get("log")
    entry["lane_script"] = lane_script
    entry["log"] = log_rel

    alive, pids = (None, [])
    if lane_script:
        alive, pids = script_alive(lane_script)
        entry["process_alive"] = alive
        entry["pids"] = pids if isinstance(pids, list) else []
    else:
        entry["process_alive"] = None  # 无脚本，跳过进程检查

    log_age = None
    log_size = None
    log_exists = False
    if log_rel:
        log_path = os.path.join(REPO_ROOT, log_rel)
        if os.path.isfile(log_path):
            log_exists = True
            st = os.stat(log_path)
            log_age = now - st.st_mtime
            log_size = st.st_size
    entry["log_exists"] = log_exists
    entry["log_age_sec"] = log_age
    entry["log_size_bytes"] = log_size
    entry["log_age_human"] = fmt_age(log_age)
    entry["log_size_human"] = fmt_size(log_size)

    fresh = log_age is not None and log_age <= STALL_THRESHOLD_SEC
    if alive and fresh:
        entry["status"] = "RUNNING"
    elif alive and not fresh:
        entry["status"] = "STALLED"
    elif alive is False and log_exists:
        entry["status"] = "EXITED"
    else:
        entry["status"] = "NO_SIGNAL"
        entry["detail"] = "无 lane_script/日志可判定，依赖 status_source 人工解读"
    return entry


# ------------------------------------------------------- atom 目录遍历工具

def iter_actions(base):
    """遍历 base 下的 Action 目录，兼容两种布局：
    新式两层 FnXX/AYY/ 与旧式扁平 FnXX.AYY/。
    产出 (fn_id, action_id, abs_path)。FnXX 目录下的非 AYY 子目录忽略。
    """
    if not os.path.isdir(base):
        return
    for fn_name in sorted(os.listdir(base)):
        fn_path = os.path.join(base, fn_name)
        if not os.path.isdir(fn_path):
            continue
        m_flat = ACTION_DIR_RE.match(fn_name)
        if m_flat:
            yield "Fn%s" % m_flat.group(1), fn_name, fn_path
            continue
        if re.match(r"^Fn\d{2}$", fn_name):
            for sub in sorted(os.listdir(fn_path)):
                sub_path = os.path.join(fn_path, sub)
                if os.path.isdir(sub_path) and ACTION_SUBDIR_RE.match(sub):
                    yield fn_name, "%s.%s" % (fn_name, sub), sub_path


# ------------------------------------------------------------ 成熟度扫描

def scan_maturity():
    """扫 src/atoms 的 STATUS.yaml 与 docs/spec/atoms 的设计文档，按 Fn 汇总。"""
    per_fn = {fn: {"actions": 0, "status_counts": OrderedDict(),
                   "design_done": 0, "design_total": 0}
              for fn in FN_IDS}

    # code.status：优先新式两层布局的 STATUS.yaml；扁平旧式 src/atoms/FnXX.AYY
    # 下若有 STATUS.yaml 也计入。
    src_base = os.path.join(REPO_ROOT, "src", "atoms")
    for fn_id, action_id, action_path in iter_actions(src_base):
        status_file = os.path.join(action_path, "STATUS.yaml")
        if not os.path.isfile(status_file):
            continue
        if fn_id not in per_fn:
            per_fn[fn_id] = {"actions": 0, "status_counts": OrderedDict(),
                             "design_done": 0, "design_total": 0}
        try:
            with open(status_file, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
        except (yaml.YAMLError, OSError) as exc:
            status = "STATUS_YAML_UNPARSEABLE(%s)" % type(exc).__name__
        else:
            status = str((data.get("code") or {}).get("status") or "MISSING")
        per_fn[fn_id]["actions"] += 1
        counts = per_fn[fn_id]["status_counts"]
        counts[status] = counts.get(status, 0) + 1

    # 设计完成度：docs/spec/atoms 下含 DESIGN_SPEC.md 或 DESIGN.md 的 Action 数。
    spec_base = os.path.join(REPO_ROOT, "spec", "atoms")
    for fn_id, action_id, action_path in iter_actions(spec_base):
        if fn_id not in per_fn:
            per_fn[fn_id] = {"actions": 0, "status_counts": OrderedDict(),
                             "design_done": 0, "design_total": 0}
        per_fn[fn_id]["design_total"] += 1
        if (os.path.isfile(os.path.join(action_path, "DESIGN_SPEC.md"))
                or os.path.isfile(os.path.join(action_path, "DESIGN.md"))):
            per_fn[fn_id]["design_done"] += 1

    return per_fn


# ------------------------------------------------------------ 验证产出扫描

VERDICT_LINE_RE = re.compile(r'"?verdict"?\s*[:=]\s*["\']?([A-Za-z_]+)', re.I)


def scan_verification(now):
    """扫 var/evidence/atoms/**/runs/：最近 7 天 run 目录计数 + verdict 粗计数。"""
    per_fn = {fn: {"recent_runs": 0, "verdicts": OrderedDict()} for fn in FN_IDS}
    ev_base = os.path.join(REPO_ROOT, "evidence", "atoms")
    cutoff = now - RECENT_RUN_DAYS * 86400

    for fn_id, action_id, action_path in iter_actions(ev_base):
        if fn_id not in per_fn:
            per_fn[fn_id] = {"recent_runs": 0, "verdicts": OrderedDict()}
        runs_dir = os.path.join(action_path, "runs")
        if not os.path.isdir(runs_dir):
            continue
        for entry in sorted(os.listdir(runs_dir)):
            run_path = os.path.join(runs_dir, entry)
            if not os.path.isdir(run_path):
                continue
            try:
                mtime = os.stat(run_path).st_mtime
            except OSError:
                continue
            if mtime >= cutoff:
                per_fn[fn_id]["recent_runs"] += 1
            # verdict 粗计数：json/md 里找 verdict 字段
            for root, _dirs, files in os.walk(run_path):
                for name in files:
                    if not name.lower().endswith((".json", ".md")):
                        continue
                    fpath = os.path.join(root, name)
                    try:
                        with open(fpath, "r", encoding="utf-8",
                                  errors="replace") as fh:
                            text = fh.read()
                    except OSError:
                        continue
                    for m in VERDICT_LINE_RE.finditer(text):
                        val = m.group(1).upper()
                        counts = per_fn[fn_id]["verdicts"]
                        counts[val] = counts.get(val, 0) + 1
    return per_fn


# ---------------------------------------------------------------- 输出生成

def verdict_summary(verdicts):
    """把 verdict 计数浓缩为 PASS/BLOCK/FAIL/其他 的短串。"""
    parts = []
    for key in ("PASS", "BLOCK", "FAIL"):
        n = sum(v for k, v in verdicts.items() if key in k)
        if n:
            parts.append("%s:%d" % (key, n))
    other = sum(v for k, v in verdicts.items()
                if not any(key in k for key in ("PASS", "BLOCK", "FAIL")))
    if other:
        parts.append("其他:%d" % other)
    return " ".join(parts) if parts else "-"


def host_pass_count(status_counts):
    return sum(v for k, v in status_counts.items() if "HOST_PASS" in k)


def device_pass_count(status_counts):
    return sum(v for k, v in status_counts.items()
               if "RUNTIME_OBSERVED" in k or "DEVICE" in k)


def build_markdown(board):
    lines = []
    a = lines.append
    a("# Bridge 并行 Lane 状态看板")
    a("")
    a("生成时间：%s（由 `src/tools/build_lane_board.py` 生成，真源 `worker/lanes.yaml`）"
      % board["generated_at"])
    a("")
    a("**总体判断**：%s" % board["headline"])
    a("")
    a("## Lane 状态")
    a("")
    a("| Lane | Scope | 状态 | 日志年龄 | 日志大小 | device_needs |")
    a("|---|---|---|---|---|---|")
    for lane in board["lanes"]:
        a("| %s | %s | %s | %s | %s | %s |" % (
            lane["id"], lane["scope"], lane["status"],
            lane.get("log_age_human", "-"), lane.get("log_size_human", "-"),
            lane["device_needs"]))
    a("")
    manual = [l for l in board["lanes"] if l["status"] in ("MANUAL", "PLANNED",
                                                           "NO_SIGNAL")]
    if manual:
        a("备注：")
        for l in manual:
            a("- `%s`：%s（%s）" % (l["id"], l["status"],
                                    l.get("detail") or l.get("status_source", "")))
        a("")

    a("## 全库 Fn × 成熟度矩阵")
    a("")
    a("| Fn | Action 数 | 设计完成 | Host Pass | Device/Runtime Pass | 近 7 天 run | verdict 计数 |")
    a("|---|---|---|---|---|---|---|")
    for fn in FN_IDS:
        row = board["maturity"].get(fn)
        ver = board["verification"].get(fn)
        if row is None and ver is None:
            continue
        row = row or {"actions": 0, "status_counts": {}, "design_done": 0,
                      "design_total": 0}
        ver = ver or {"recent_runs": 0, "verdicts": {}}
        a("| %s | %d | %d/%d | %d | %d | %d | %s |" % (
            fn, row["actions"],
            row["design_done"], row["design_total"],
            host_pass_count(row["status_counts"]),
            device_pass_count(row["status_counts"]),
            ver["recent_runs"],
            verdict_summary(ver["verdicts"])))
    a("")

    a("## code.status 明细（原样归类）")
    a("")
    for fn in FN_IDS:
        row = board["maturity"].get(fn)
        if not row or not row["status_counts"]:
            continue
        detail = ", ".join("%s × %d" % (k, v)
                           for k, v in sorted(row["status_counts"].items()))
        a("- **%s**：%s" % (fn, detail))
    a("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="生成 Bridge lane 状态看板")
    parser.add_argument("--out-md", default=DEFAULT_OUT_MD,
                        help="markdown 输出路径（默认 docs/progress-lanes.md）")
    parser.add_argument("--out-json", default=DEFAULT_OUT_JSON,
                        help="json 输出路径（默认 out/lane-board.json）")
    args = parser.parse_args()

    now = datetime.datetime.now().timestamp()
    generated_at = datetime.datetime.now().astimezone().isoformat(
        timespec="seconds")

    with open(LANES_YAML, "r", encoding="utf-8") as fh:
        lanes_doc = yaml.safe_load(fh) or {}
    lane_entries = [assess_lane(l, now) for l in lanes_doc.get("lanes", [])]

    maturity = scan_maturity()
    verification = scan_verification(now)

    stalled = [l["id"] for l in lane_entries if l["status"] == "STALLED"]
    exited = [l["id"] for l in lane_entries if l["status"] == "EXITED"]
    running = [l["id"] for l in lane_entries if l["status"] == "RUNNING"]
    bits = []
    bits.append("RUNNING: %s" % (", ".join(running) if running else "无"))
    bits.append("STALLED: %s" % (", ".join(stalled) if stalled else "无"))
    bits.append("EXITED: %s" % (", ".join(exited) if exited else "无"))
    headline = "；".join(bits) + "。"

    board = OrderedDict([
        ("generated_at", generated_at),
        ("source", os.path.relpath(LANES_YAML, REPO_ROOT)),
        ("headline", headline),
        ("lanes", lane_entries),
        ("maturity", maturity),
        ("verification", verification),
    ])

    md = build_markdown(board)
    os.makedirs(os.path.dirname(os.path.abspath(args.out_md)), exist_ok=True)
    with open(args.out_md, "w", encoding="utf-8") as fh:
        fh.write(md)
    os.makedirs(os.path.dirname(os.path.abspath(args.out_json)), exist_ok=True)
    with open(args.out_json, "w", encoding="utf-8") as fh:
        json.dump(board, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print("wrote %s" % args.out_md)
    print("wrote %s" % args.out_json)
    print(headline)
    return 0


if __name__ == "__main__":
    sys.exit(main())
