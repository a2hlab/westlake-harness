import hashlib
import json
import os
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
WORKSPACES = Path(os.environ.get("WORKSPACES", HERE.parents[3]))
MASTER = WORKSPACES / "westlake-harness"
sys.path.insert(0, str(HERE.parent / "t3"))
import build_tally


def build(manifest, signoff):
    tally = build_tally.summarize.tally_signoff(manifest, signoff)
    judgments = signoff["verdicts"]
    games = set(manifest["signed_games"])
    included = [row for row in manifest["apps"] if judgments.get(row["key"], {}).get("verdict") == "lit"]
    included.sort(key=lambda row: (row["historical_content_status"] != "shown", row["key"] not in games, row["demo_order"]))
    excluded = [row for row in manifest["apps"] if row not in included]
    steps = []
    for index, row in enumerate(included):
        following = included[index + 1]["key"] if index + 1 < len(included) else "头条(仅经独立验收后) / 收尾"
        steps.append({"order": index + 1, "key": row["key"], "package": row["package"], "name": row["name_zh"],
                      "tier": row["historical_content_status"], "is_required_game": row["key"] in games,
                      "verdict": "lit", "skip_to": following,
                      "fallback": "打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 " + following + ";不重试、不现场修、不猜点击坐标"})
    return {"schema": "demo-runbook-order/v1", "execution_enabled": False, "seal_status": "pending",
            "count_source": "t3 tally_signoff; strict literal lit only, no lit_splash",
            "tally_summary": tally["summary"], "demo_steps": steps,
            "game_keys": [row["key"] for row in steps if row["is_required_game"]],
            "appendix": [{"key": row["key"], "name": row["name_zh"], "tier": row["historical_content_status"],
                          "verdict": judgments.get(row["key"], {}).get("verdict", "pending"),
                          "note": "启动页,不进入演示序列" if judgments.get(row["key"], {}).get("verdict") == "lit_splash" else "半亮/不亮/未签,不进入演示序列"}
                         for row in sorted(excluded, key=lambda row: row["key"])]}


def markdown(report):
    summary = report["tally_summary"]
    content = summary["tiers"]["shown"]["verdict_counts"]["lit"]
    empty = summary["tiers"]["minimal"]["verdict_counts"]["lit"]
    signed_content = summary["tiers"]["shown"]["signed_lit"]
    lines = ["# 演示手册终稿（离线文字版；封存启用仍待验收）", "", "## Evidence first / 状态与来源", "",
             f"- 签认表机械汇总:内容档 `{content}/{summary['tiers']['shown']['total']}` 为严格 lit（含 lit_splash 为{signed_content}/{summary['tiers']['shown']['total']}）；空态档 `{empty}/{summary['tiers']['minimal']['total']}` 为 lit；游戏 `{len(report['game_keys'])}/{summary['required_games']['total']}` 为 lit。",
             f"- 本手册仅列 `{len(report['demo_steps'])}` 个精确 `lit` key；游戏是其中子集，不加总第二次。半亮、不亮、启动页见附录。",
             "- 61b 演示板：`61b0657200000000000000000324012c`。此稿没有操作板、VM/SSH、安装、改运行时或签封存。",
             "- 最终 `seal.json`、t4 两轮稳定性、封存恢复 provider、空闲板真实恢复演练尚未形成；不能凭文字终稿把它们判成 PASS。",
             "- oc-t4 草稿中的游戏12全亮、任意FAB/固定坐标、联网空态当成功均不沿用；每个演示 key 有明确跳过兜底。", ""]
    for label, item in sorted(report["inputs"].items()):
        lines.append(f"- {label}: `{item['path']}`, SHA256 `{item['sha256']}`。")
    lines += ["", "## 0. 开机就绪", "",
              "等待已验收的自启恢复完成、桌面就绪；先跑只读自检：", "", "```sh",
              "bash scripts/lab/demo_selfcheck.sh --seal benchmark/2026-10-09-demo-baseline/t5/seal.json \\",
              "  --serial 61b0657200000000000000000324012c --out /tmp/demo-selfcheck-fresh.json", "```", "",
              "每次使用新的输出文件名。只有 live-readonly PASS 才说明封存身份匹配；OFFLINE_MATCH 不等于板上通过。",
              "自检非零立即停演示、保存路径/期望/实际差异，交外环审；不得在封存板自行 restore、重启、重装或修运行时。",
              "显示黑/白/报错不据活进程报亮。展示操作只用前台桌面与实际控件，不写死未核坐标。", "",
              "## 1. 演示顺序（内容档优先，10个lit游戏在内容档最前）", "",
              "每项前台点击真实桌面图标；等待自身界面。空态档的历史32个不混入首屏内容数字，虽本轮签lit仍按现场画面决定是否跳过。",
              "游戏可在真实按钮上手动进入并演示一次触摸；本轮截图签认不证明玩法交互通过。", "",
              "| 顺序 | key / 包名 | 显示名 | 分档 | 失败时跳过兜底 |", "|---:|---|---|---|---|"]
    for row in report["demo_steps"]:
        name = row["name"].replace("|", "\\|")
        lines.append(f"| {row['order']} | `{row['key']}` / `{row['package']}` | {name} | {row['tier']} | {row['fallback']} |")
    lines += ["", "## 2. 今日头条：前台桌面点击，不用后台 aa start", "",
              "仅在 Route B 与最终封存叠加件独立验收后纳入。前台桌面找到「今日头条」图标点击；",
              "不要用 `aa start` 当演示入口：现场后台启动会被拒 `10107101`。图标坐标必须取当前界面，不照抄草稿固定坐标。",
              "首页出现自身内容后，按真实控件刷新/下拉一次，滚动信息流，点一篇文章确认正文，再返回首页；无网/不刷新/正文打不开就记现象并跳过。",
              "看门狗只按已验收 Route B 配方管理隔离的 `asx-spawner` 与子进程，绝不按名字清理 U13 `appspawn-x`。",
              "宿主被杀后不能依赖被拒的后台启动自愈：前台再点桌面图标；一次仍无内容则直接收尾，不现场改权限/preauth或运行时。",
              "观察到进程抖动不等于界面稳定；最终演示要求刷新与点文章的实际画面证据。", "",
              "## 3. BoatAttack", "", "**待 PR03 渲染移植验收后补。**",
              "不把偏紫/低分辨率、旧候选五绑定或尚未验收的私有件当封存配置；本稿不列部署/点击坐标。",
              "待验收后补真实前台入口、分辨率/色彩/操控判据及经签部署/回滚层。未就绪时跳过BoatAttack，直接收尾。", "",
              "## 4. 恢复入口与禁止现场修复", "",
              "恢复默认 dry-run；封存后任何写操作仅用户能解封授权。先在外环指定空闲板演练，不修改原 seal 的 serial：", "",
              "```sh", "bash scripts/lab/demo_restore.sh --dry-run --rehearsal \\",
              "  --seal benchmark/2026-10-09-demo-baseline/t5/seal.json \\",
              "  --deployment benchmark/2026-10-09-demo-baseline/t5/restore-deployment.json \\",
              "  --serial <外环指定空闲板完整serial> --out <新的持久日志目录>", "```", "",
              "正式封存 provider 尚无。底座候选二选一待外环定：① cx-t0 fresh native票据回放（master `5a172dd057`,",
              "`benchmark/2026-10-09-demo-baseline/t3/restore5cd-u13-ticket/`），319 diff{}→父子视图/单ART→HW/ZZ t20；",
              "② cc-wiki `benchmark/2026-10-10-u13-autostart/payload/scripts/install-westlake-u13-autostart.sh`（5cd真实reboot只证明机制，未落master）。",
              "自启就绪/文件相同不能代替foundation实际加载宿主库和截图验收；5cd/5ea宿主库mount与61b物理文件的差异不能外推。",
              "选定适配器后，顺序为 U13 → 已封存头条 Route B → 已封存BoatAttack，三层provider/rollback都逐SHA绑定；不拿候选源码当已签恢复配方。",
              "恢复前只读校验源SHA、系统版本/安装器等不可替换前提；缺读回/未知漂移拒绝，保留外部锁；不得重用旧native票据绕过门。",
              "真实空闲板演练及最终封存/AGENTS演示板登记由外环另行安排，此离线包不执行。", "",
              "## 5. 收尾", "", "返回桌面，保存演示日志（每项 key/画面/skip 原因）；再跑新的只读 selfcheck。",
              "若有漂移停止并交外环；不现场改 settings、安装、文件、权限或重启。封存板只读巡检，解封只有用户能批。", "",
              "## 附录：不进入演示序列", "", "| key | 显示名 | 签认 | 原因 |", "|---|---|---|---|"]
    for row in report["appendix"]:
        name = row["name"].replace("|", "\\|")
        lines.append(f"| `{row['key']}` | {name} | {row['verdict']} | {row['note']} |")
    return "\n".join(lines) + "\n"


def main():
    manifest_path = HERE.parent / "demo-manifest.json"
    signoff_path = MASTER / "benchmark/2026-10-09-demo-baseline/t3-outer-signoff.json"
    draft = WORKSPACES / "westlake-harness-t4/benchmark/2026-10-09-demo-baseline/t5/demo-runbook.md"
    report = build(json.loads(manifest_path.read_text()), json.loads(signoff_path.read_text()))
    report["inputs"] = {label: build_tally.binding(path, path.read_bytes()) for label, path in
                        (("manifest", manifest_path), ("outer-signoff", signoff_path), ("oc-t4-draft", draft))}
    (HERE / "runbook-signoff-input.json").write_bytes(signoff_path.read_bytes())
    (HERE / "runbook-order.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    (HERE / "demo-runbook.md").write_text(markdown(report))
    print(json.dumps({"demo_keys": len(report["demo_steps"]), "lit_games": len(report["game_keys"]), "appendix": len(report["appendix"])}))


if __name__ == "__main__":
    main()
