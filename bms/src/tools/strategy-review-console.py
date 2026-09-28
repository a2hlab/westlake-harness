#!/usr/bin/env python3
"""
Bridge Strategy Review Console

Interactive CLI for reviewing all Fn Concept Domain strategy decisions as a
coherent set. Supports per-Concept and per-group review, records owner choices,
and generates a human-readable summary.

Run:
    python3 src/tools/strategy-review-console.py

Controls:
    Type the letter/number shown in brackets and press Enter.
    'q' or 'b' usually means quit / go back.
"""

import os
import re
import sys
import yaml
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONCEPTS_DIR = ROOT / "docs" / "concepts"
DECISIONS_DIR = ROOT / "docs" / "decisions"
RECORDS_DIR = DECISIONS_DIR / "records"
SPEC_FILE = ROOT / "spec" / "concept-graph.yaml"

CHOICES = {
    "e": "继续做实验 / Evidence building",
    "h": "历史成功实践优先 / Historical precedent",
    "m": "维持历史决策 / Maintain historical decision",
    "p": "选择主导建议 / Select primary recommendation",
    "b": "选择备选路线 / Select backup route",
    "r": "看参考文档 / View reference documents",
    "s": "跳过，保持当前状态 / Skip",
}

GROUPS = {
    "A": {
        "name": "可见表面组 / Window · Input · Graphics",
        "concepts": ["Fn03", "Fn04", "Fn05", "Fn10"],
        "core_object": "generation-bound window/session/surface and callback thread",
        "questions": [
            "窗口生成单元是什么：Ability session、WindowRecord 还是 SceneBoard node？",
            "InputChannel 如何绑定到 window generation 和 owner Looper？",
            "HWUI/Skia buffer 和 RS transaction 在哪里终止，什么 receipt 证明帧已上屏？",
            "Activity attach/resume/finish 如何创建和失效 window generation？",
        ],
    },
    "B": {
        "name": "组件调度组 / Intent · Task · Service",
        "concepts": ["Fn01", "Fn03", "Fn06", "Fn07", "Fn08", "Fn11"],
        "core_object": "typed Intent/Want, task/service authority, caller identity and Binder endpoint",
        "questions": [
            "同一个 AXML 解析器和 BMS projection 是否同时输出 PAGE Activity 和 SERVICE extension 元数据？",
            "Service host 是什么：ServiceExtensionAbility、共享 runtime agent 还是 ServiceLifecycleAuthority？",
            "ActivityThread 调度模型如何同时覆盖 Activity 和 Service 生命周期回调？",
            "caller token 格式是什么，如何在 startService/bindService/Binder 事务中保持？",
            "Android Binder 是本地保留、OH remote proxy 还是二者兼有？",
        ],
    },
    "C": {
        "name": "身份授权基板 / Package · Permission · Binder",
        "concepts": ["Fn01", "Fn08", "Fn11"],
        "core_object": "package/signing identity, AccessToken/sandbox generation, caller token and verdict",
        "questions": [
            "包解析如何输出 signing、declared permissions 和 install generation？",
            "spawn 与受保护 API 边界的 caller identity 如何与 OH AccessToken 关联？",
            "权限撤销后旧 generation 的访问是否立即失效？",
            "Binder/system-service lookup 的 caller token 由谁生成和校验？",
        ],
    },
}

ALL_FN = [f"Fn{n:02d}" for n in range(1, 13)]


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def load_graph():
    if not SPEC_FILE.exists():
        return {}
    with open(SPEC_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def concept_status(graph, fn):
    """Return a short status string for a Concept Domain."""
    assessments = graph.get("direction_assessments", {})
    if fn not in assessments:
        return "UNASSESSED"
    dirs = assessments[fn]
    statuses = {d.get("status", "UNASSESSED") for d in dirs.values()}
    if "BLOCKED" in statuses:
        return "BLOCKED"
    if statuses == {"EVIDENCED"}:
        return "EVIDENCED"
    if "HYPOTHESIS" in statuses or "UNASSESSED" in statuses:
        return "PARTIAL"
    return "PARTIAL"


def concept_files(fn):
    """Return which strategy/design files exist for a Concept."""
    d = CONCEPTS_DIR / fn
    if not d.exists():
        return []
    names = {"STRATEGY.md", "STRATEGY_DECISION.md", "BRIDGE_CONTRACT.md",
             "ROUTE_SPACE.md", "ACTION_MAP.md", "CONCEPT_DESIGN.md"}
    return sorted(p.name for p in d.iterdir() if p.name in names)


def ensure_records_dir():
    RECORDS_DIR.mkdir(parents=True, exist_ok=True)


def save_record(group_or_fn, choice_key, reason, owner):
    ensure_records_dir()
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "-", group_or_fn)
    path = RECORDS_DIR / f"{ts}-{safe_name}.yaml"
    record = {
        "timestamp": datetime.now().isoformat(),
        "target": group_or_fn,
        "choice": CHOICES.get(choice_key, choice_key),
        "choice_key": choice_key,
        "owner": owner,
        "reason": reason,
    }
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(record, f, allow_unicode=True, sort_keys=False)
    return path


def load_records():
    ensure_records_dir()
    records = []
    for p in sorted(RECORDS_DIR.glob("*.yaml")):
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            data["_file"] = p.name
            records.append(data)
    return records


def prompt(text, default=""):
    if default:
        return input(f"{text} [{default}]: ").strip() or default
    return input(f"{text}: ").strip()


def print_header(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def print_status_table(graph):
    print_header("Concept Domain 当前状态")
    print(f"{'ID':<8}{'Status':<12}{'Strategy files':<50}")
    print("-" * 70)
    for fn in ALL_FN:
        status = concept_status(graph, fn)
        files = ", ".join(concept_files(fn)) or "(none)"
        marker = "*" if status in ("BLOCKED", "UNASSESSED") else " "
        print(f"{marker}{fn:<7}{status:<12}{files:<50}")
    print("\n* = BLOCKED or UNASSESSED")


def review_group_menu(graph, group_id):
    g = GROUPS[group_id]
    while True:
        clear()
        print_header(f"Group {group_id}: {g['name']}")
        print(f"核心共享对象: {g['core_object']}\n")
        print("包含 Concept:", ", ".join(g["concepts"]))
        print()
        for fn in g["concepts"]:
            print(f"  {fn}: {concept_status(graph, fn)}  [{', '.join(concept_files(fn)) or 'no docs'}]")
        print("\n关键问题:")
        for i, q in enumerate(g["questions"], 1):
            print(f"  {i}. {q}")
        print("\n选项:")
        for k, v in CHOICES.items():
            print(f"  [{k}] {v}")
        print("  [c] 查看该组已保存的 review 记录")
        print("  [n] 下一组")
        print("  [q] 返回主菜单")
        choice = prompt("选择", "s").lower()
        if choice == "q":
            break
        if choice == "n":
            return "next"
        if choice == "c":
            show_records_for(group_id)
            prompt("按 Enter 继续")
            continue
        if choice in CHOICES:
            owner = prompt("决策负责人", "human-required")
            reason = prompt("理由 / 备注")
            path = save_record(group_id, choice, reason, owner)
            print(f"\n已保存记录: {path.relative_to(ROOT)}")
            prompt("按 Enter 继续")
    return None


def review_concept_menu(graph, fn):
    while True:
        clear()
        print_header(f"Concept Domain: {fn}")
        status = concept_status(graph, fn)
        files = concept_files(fn)
        print(f"当前状态: {status}")
        print(f"已有文档: {', '.join(files) or '(none)'}")
        print("\n参考路径:")
        d = CONCEPTS_DIR / fn
        if d.exists():
            for name in files:
                print(f"  - docs/concepts/{fn}/{name}")
        print("\n选项:")
        for k, v in CHOICES.items():
            print(f"  [{k}] {v}")
        print("  [c] 查看该 Concept 的 review 记录")
        print("  [q] 返回")
        choice = prompt("选择", "s").lower()
        if choice == "q":
            break
        if choice == "c":
            show_records_for(fn)
            prompt("按 Enter 继续")
            continue
        if choice in CHOICES:
            owner = prompt("决策负责人", "human-required")
            reason = prompt("理由 / 备注")
            path = save_record(fn, choice, reason, owner)
            print(f"\n已保存记录: {path.relative_to(ROOT)}")
            prompt("按 Enter 继续")


def show_records_for(target):
    records = [r for r in load_records() if r.get("target") == target]
    print_header(f"Review 记录: {target}")
    if not records:
        print("(无记录)")
        return
    for r in records:
        print(f"- {r.get('timestamp', '?')}")
        print(f"  选择: {r.get('choice', '?')}")
        print(f"  负责人: {r.get('owner', '?')}")
        print(f"  理由: {r.get('reason', '?')}")
        print(f"  文件: {r.get('_file', '?')}")
        print()


def show_all_records():
    records = load_records()
    print_header("全部 Review 记录")
    if not records:
        print("(无记录)")
        return
    by_target = defaultdict(list)
    for r in records:
        by_target[r.get("target", "unknown")].append(r)
    for target in sorted(by_target):
        print(f"\n[{target}]")
        for r in by_target[target]:
            print(f"  {r.get('timestamp', '?')} | {r.get('choice_key', '?')} | {r.get('owner', '?')} | {r.get('reason', '')[:40]}")


def generate_report(graph):
    records = load_records()
    path = DECISIONS_DIR / "strategy-review-latest-report.md"
    lines = [
        "# Strategy Review Report",
        "",
        f"生成时间: {datetime.now().isoformat()}",
        f"记录数量: {len(records)}",
        "",
        "## Concept Domain 状态摘要",
        "",
        "| Concept | Status | Strategy files |",
        "|---|---|---|",
    ]
    for fn in ALL_FN:
        status = concept_status(graph, fn)
        files = ", ".join(concept_files(fn)) or "(none)"
        lines.append(f"| {fn} | {status} | {files} |")
    lines += [
        "",
        "## 统一决策分组",
        "",
    ]
    for gid, g in GROUPS.items():
        lines.append(f"### Group {gid}: {g['name']}")
        lines.append(f"- Concepts: {', '.join(g['concepts'])}")
        lines.append(f"- 核心对象: {g['core_object']}")
        lines.append("- 关键问题:")
        for q in g["questions"]:
            lines.append(f"  - {q}")
        lines.append("")
    lines += [
        "## Review 记录",
        "",
    ]
    if not records:
        lines.append("(无记录)")
    else:
        by_target = defaultdict(list)
        for r in records:
            by_target[r.get("target", "unknown")].append(r)
        for target in sorted(by_target):
            lines.append(f"### {target}")
            for r in by_target[target]:
                lines.append(f"- **{r.get('choice', '?')}** ({r.get('timestamp', '?')}) — {r.get('owner', '?')}")
                lines.append(f"  - {r.get('reason', '')}")
            lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n报告已生成: {path.relative_to(ROOT)}")


def main():
    graph = load_graph()
    while True:
        try:
            clear()
            print_header("Bridge Strategy Review Console")
            print("完成全部技术 strategy review 的交互式入口。\n")
            print("[1] 按统一分组 review (Group A / B / C)")
            print("[2] 按单个 Concept Domain review (Fn01–Fn12)")
            print("[3] 查看 Concept 当前状态总览")
            print("[4] 查看已保存的 review 记录")
            print("[5] 生成 strategy review 报告")
            print("[h] 帮助 / 操作说明")
            print("[q] 退出")
            choice = prompt("选择").lower()
        except EOFError:
            print("\n输入结束，退出。")
            sys.exit(0)
        if choice == "q":
            print("再见。")
            sys.exit(0)
        elif choice == "1":
            group_ids = list(GROUPS.keys())
            idx = 0
            while idx < len(group_ids):
                result = review_group_menu(graph, group_ids[idx])
                if result == "next":
                    idx += 1
                elif result is None:
                    break
        elif choice == "2":
            print_status_table(graph)
            fn = prompt("输入要 review 的 Concept ID (如 Fn07)", "Fn07")
            if fn in ALL_FN:
                review_concept_menu(graph, fn)
            else:
                print("无效 ID")
                prompt("按 Enter 继续")
        elif choice == "3":
            print_status_table(graph)
            prompt("按 Enter 继续")
        elif choice == "4":
            show_all_records()
            prompt("按 Enter 继续")
        elif choice == "5":
            generate_report(graph)
            prompt("按 Enter 继续")
        elif choice == "h":
            show_help()
            prompt("按 Enter 继续")
        else:
            print("无效选择")
            prompt("按 Enter 继续")


def show_help():
    print_header("帮助")
    print("""
本控制台用于对 Bridge 项目的全部 Fn Concept Domain 进行 strategy review。

你可以：
1. 按统一分组 review — 推荐方式，避免相关 Concept 分开决策。
2. 按单个 Concept review — 适合补充某个具体 domain 的判断。
3. 查看状态总览 — 快速了解哪些 Concept 已被 evidence 支持、哪些仍 blocked。
4. 查看/生成记录 — 所有选择都会保存到 docs/decisions/records/，并生成报告。

每个 review 选项含义：
  e = 继续做实验 / Evidence building
  h = 历史成功实践优先 / Historical precedent
  m = 维持历史决策 / Maintain historical decision
  p = 选择主导建议 / Select primary recommendation
  b = 选择备选路线 / Select backup route
  r = 看参考文档 / View reference documents
  s = 跳过，保持当前状态 / Skip

注意：真正的路线接受仍需要人工负责人记录 primary + backup + rollback trigger。
""")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已中断。")
        sys.exit(0)
