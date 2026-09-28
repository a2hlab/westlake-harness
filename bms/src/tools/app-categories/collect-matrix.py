#!/usr/bin/env python3
"""汇总四条 APP 大类分支的状态文件,渲染成 Fn 楼层 × 大类矩阵。

横轴大类定义读 docs/spec/apk-sample-set.yaml 的 categories 字段。

用法:
    python3 src/tools/app-categories/collect-matrix.py            # 打印 markdown
    python3 src/tools/app-categories/collect-matrix.py --write    # 写入 docs/app-category-matrix.md
    python3 src/tools/app-categories/collect-matrix.py --local    # 读本地分支而非 origin/

用 `git show <ref>:docs/spec/app-status/<slug>.yaml` 直接读各分支,不切换分支、不建 worktree。
读不到状态文件的大类整列按 blank 处理并在脚注说明,不静默跳过。
"""
import subprocess
import sys
import pathlib
import re

ROOT = pathlib.Path(
    subprocess.run(["git", "rev-parse", "--show-toplevel"],
                   capture_output=True, text=True, check=True).stdout.strip())

FLOORS = {
    "Fn01": "APK 安装与包元数据",
    "Fn02": "进程、Runtime、JNI 与 Native",
    "Fn03": "Activity 生命周期",
    "Fn04": "Window、Surface 与 Rendering",
    "Fn05": "输入",
    "Fn06": "Intent / Task",
    "Fn07": "Android Service",
    "Fn08": "权限 / 身份 / 沙箱",
    "Fn09": "Resource / ContentProvider",
    "Fn10": "HWUI / Skia / Graphics JNI",
    "Fn11": "系统服务 / Binder / Framework Native",
    "Fn12": "Logging / Trace API / 并发",
}

MARK = {"green": "🟩", "yellow": "🟨", "red": "🟥",
        "blank": "·", "na": "—"}


def load_yaml(text):
    try:
        import yaml
        return yaml.safe_load(text)
    except ImportError:
        return _mini_yaml(text)


def _mini_yaml(text):
    """只解析状态文件用到的子集:顶层 key、floors 下的 FnNN: {k: v} 行。"""
    out, floors = {}, {}
    in_floors = False
    for raw in text.split("\n"):
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if re.match(r"^floors\s*:", line):
            in_floors = True
            continue
        if in_floors and re.match(r"^\S", line):
            in_floors = False
        if in_floors:
            m = re.match(r"^\s+(Fn\d\d)\s*:\s*(.*)$", line)
            if m:
                key, rest = m.group(1), m.group(2).strip()
                cell = {}
                if rest.startswith("{"):
                    for part in re.findall(r"(\w+)\s*:\s*([^,}]+)", rest):
                        cell[part[0]] = part[1].strip().strip('"\'')
                elif rest:
                    cell["status"] = rest.strip('"\'')
                floors[key] = cell
            continue
        m = re.match(r"^(\w+)\s*:\s*(.*)$", line)
        if m and m.group(2):
            out[m.group(1)] = m.group(2).strip().strip('"\'')
    out["floors"] = floors
    return out


def git_show(ref, path):
    r = subprocess.run(["git", "show", f"{ref}:{path}"],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def main():
    write = "--write" in sys.argv
    prefix = "" if "--local" in sys.argv else "origin/"

    spec = load_yaml(
        (ROOT / "spec" / "apk-sample-set.yaml").read_text(encoding="utf-8"))
    cats = spec.get("categories") or []
    floors = FLOORS
    if not isinstance(cats, list) or not floors:
        sys.exit("docs/spec/apk-sample-set.yaml 缺少 categories;请先确认该文件完整")

    fn_ids = sorted(floors)
    data, notes = {}, []

    for cat in cats:
        slug = cat["slug"]
        ref = f"{prefix}{cat['branch']}"
        raw = git_show(ref, f"docs/spec/app-status/{slug}.yaml")
        if raw is None:
            notes.append(f"`{ref}` 上没有 `docs/spec/app-status/{slug}.yaml`,整列按 blank 计。")
            data[slug] = {}
            continue
        data[slug] = (load_yaml(raw) or {}).get("floors") or {}

    head = "| 楼层 | " + " | ".join(c["name"] for c in cats) + " |"
    sep = "| --- | " + " | ".join(":---:" for _ in cats) + " |"
    rows = [head, sep]

    for fn in fn_ids:
        cells = []
        for cat in cats:
            cell = data[cat["slug"]].get(fn) or {}
            st = (cell.get("status") or "blank").strip()
            cells.append(MARK.get(st, f"?{st}"))
        rows.append(f"| **{fn}** {floors[fn]} | " + " | ".join(cells) + " |")

    out = ["# Fn 楼层 × APP 大类 矩阵", "",
           "> 由 `src/tools/app-categories/collect-matrix.py` 生成,不要手改。",
           "> 横轴定义 `docs/spec/apk-sample-set.yaml#categories`,各列数据来自对应分支的 "
           "`docs/spec/app-status/<slug>.yaml`。", "",
           "🟩 green 板上独立 verdict · 🟨 yellow 部分通过或仅基准机 · "
           "🟥 red 已定位阻塞点 · · blank 未走到 · — na 不经过", ""]
    out += rows

    blockers = []
    for cat in cats:
        for fn in fn_ids:
            cell = data[cat["slug"]].get(fn) or {}
            if (cell.get("status") or "").strip() == "red" and cell.get("blocker"):
                blockers.append(f"| {cat['name']} | {fn} | {cell['blocker']} |")
    if blockers:
        out += ["", "## 未解除的阻塞点", "",
                "| 大类 | 楼层 | 阻塞点 |", "| --- | --- | --- |"] + blockers

    if notes:
        out += ["", "## 数据缺口", ""] + [f"- {n}" for n in notes]

    text = "\n".join(out) + "\n"
    if write:
        p = ROOT / "docs" / "app-category-matrix.md"
        p.write_text(text, encoding="utf-8")
        print(f"已写入 {p.relative_to(ROOT)}")
    else:
        print(text)


if __name__ == "__main__":
    main()
