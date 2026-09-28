#!/usr/bin/env python3
"""通用 FnXX Action Design hash-bound 独立评审：delta 增量、并行、超时降级。

与 src/tools/run_kimi_fn01_action_design_review.py（Fn01 专用、保持可用）相比：
- 任意 --concept FnXX；按 docs/spec/atoms/FnXX/*/atom.yaml 动态发现 Action；
- 共享 concept 文档与每个 Action 的 atom/design/verification 按实际存在动态收集，
  缺文件只记 warning，不崩；
- 默认 delta 模式：ledger 记录输入文件 sha256，只评审有变化或从未评审的组；
- --jobs N 并行评审多个 Action 组；
- 超时/空输出自动降级重试一次（仅变更文件、600s），仍失败则写
  BLOCKED_NO_ARTIFACT 评审记录并以退出码 2 结束，绝不留无产物的等待。

kimi headless 调用方式（_kimi.alex wrapper、--prompt/--output-format text、
临时目录 cwd、subprocess timeout、wire 恢复）照抄 Fn01 脚本；wrapper 自行从
macOS 备忘录读取凭据，无需额外 source 环境文件。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import yaml

from run_kimi_concept_approval_review import (
    parse_verdict,
    recover_review_from_alex_wire,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REVIEW_COMMAND = Path("/Users/alexyang/.local/bin/_kimi.alex")
DEFAULT_TIMEOUT = 900
RETRY_TIMEOUT = 600
GROUP_SIZE = 5
LEDGER_NAME = ".review-ledger.json"

# 共享 concept 文档候选：按实际存在动态收集，缺失记 warning。
SHARED_CANDIDATES = (
    "docs/concepts/{concept}/BRIDGE_CONTRACT.md",
    "docs/spec/concepts/{concept}/bridge-contract.yaml",
    "docs/concepts/{concept}/STRATEGY_DECISION.md",
    "docs/concepts/{concept}/STRATEGY.md",
    "docs/concepts/{concept}/CONCEPT_DESIGN.md",
    "docs/concepts/{concept}/CONCEPT_DOMAIN.md",
    "docs/concepts/{concept}/ACTION_MAP.md",
    "docs/spec/concepts/{concept}/action-map.yaml",
    "docs/spec/concepts/{concept}/concept.yaml",
    "docs/concepts/{concept}/ANDROID_MODEL.md",
    "docs/concepts/{concept}/OPENHARMONY_MODEL.md",
    "docs/concepts/{concept}/ROUTE_SPACE.md",
)
# 每个 Action 的设计文档候选（DESIGN_SPEC.md 与 DESIGN.md 取存在的）。
ACTION_DESIGN_CANDIDATES = ("DESIGN_SPEC.md", "DESIGN.md")
ACTION_OTHER_CANDIDATES = ("verification.md", "ATOM_VALIDATION.md")

ACTION_DIR_RE = re.compile(r"^A(\d{2})$")


def warn(message: str) -> None:
    print(f"WARNING: {message}", file=sys.stderr)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pack_digest(hashes: dict[str, str]) -> str:
    canonical = json.dumps(
        hashes, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def discover_actions(concept: str) -> list[str]:
    """扫描 docs/spec/atoms/<concept>/A*/atom.yaml，返回排序后的 Action ID（如 A01）。"""
    base = ROOT / "spec" / "atoms" / concept
    if not base.is_dir():
        raise SystemExit(f"找不到 Action 目录：{base.relative_to(ROOT)}")
    actions = []
    for child in base.iterdir():
        if not child.is_dir() or not ACTION_DIR_RE.match(child.name):
            continue
        if (child / "atom.yaml").is_file():
            actions.append(child.name)
        else:
            warn(f"{child.relative_to(ROOT)} 缺少 atom.yaml，跳过")
    if not actions:
        raise SystemExit(f"{base.relative_to(ROOT)} 下没有任何含 atom.yaml 的 Action")
    return sorted(actions)


def collect_shared_inputs(concept: str) -> list[Path]:
    inputs = []
    for pattern in SHARED_CANDIDATES:
        relative = Path(pattern.format(concept=concept))
        if (ROOT / relative).is_file():
            inputs.append(relative)
        else:
            warn(f"共享评审输入缺失：{relative}")
    if not inputs:
        warn(f"{concept} 没有任何共享 concept 文档，评审只基于 Action 文件")
    return inputs


def collect_action_inputs(concept: str, action: str) -> list[Path]:
    root = Path("docs/spec/atoms") / concept / action
    inputs = [root / "atom.yaml"]
    design = None
    for name in ACTION_DESIGN_CANDIDATES:
        if (ROOT / root / name).is_file():
            design = root / name
            break
    if design is None:
        warn(f"{root} 缺少设计文档（{'/'.join(ACTION_DESIGN_CANDIDATES)}）")
    else:
        inputs.append(design)
    for name in ACTION_OTHER_CANDIDATES:
        candidate = root / name
        if (ROOT / candidate).is_file():
            inputs.append(candidate)
        else:
            warn(f"Action 评审输入缺失：{candidate}")
    return inputs


def group_actions(actions: list[str], size: int) -> list[tuple[str, list[str]]]:
    """把排序后的 Action 按 size 切组；组名取首尾（与 Fn01 的 A01-A05 习惯一致）。"""
    groups = []
    for start in range(0, len(actions), size):
        chunk = actions[start : start + size]
        name = chunk[0] if len(chunk) == 1 else f"{chunk[0]}-{chunk[-1]}"
        groups.append((name, chunk))
    return groups


def expand_group_selector(selector: str) -> list[str]:
    match = re.fullmatch(r"A(\d{2})-A(\d{2})", selector.strip())
    if not match:
        raise SystemExit(f"--group 只支持 A01-A05 形式，收到：{selector}")
    first, last = int(match.group(1)), int(match.group(2))
    if last < first:
        raise SystemExit(f"--group 范围倒置：{selector}")
    return [f"A{number:02d}" for number in range(first, last + 1)]


def parse_actions_selector(selector: str) -> list[str]:
    actions = []
    for item in selector.split(","):
        item = item.strip()
        if not ACTION_DIR_RE.match(item):
            raise SystemExit(f"--actions 只接受 A01,A02 形式，收到：{item}")
        actions.append(item)
    return sorted(set(actions))


def load_ledger(path: Path) -> dict:
    if not path.is_file():
        return {"files": {}, "groups": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        warn(f"ledger 损坏（{error}），按从未评审处理")
        return {"files": {}, "groups": {}}
    data.setdefault("files", {})
    data.setdefault("groups", {})
    return data


def save_ledger(path: Path, ledger: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=".review-ledger.",
        delete=False,
    ) as stream:
        json.dump(ledger, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
        temporary = Path(stream.name)
    temporary.replace(path)


def previous_open_findings(out_dir: Path, group: str) -> str | None:
    """从该组最近一次成功评审 artifact 提取『## 阻断项』段，作为上轮未关闭 findings。"""
    candidates = sorted(
        (
            path
            for path in out_dir.glob(f"kimi-{group.lower()}-*.md")
            if not path.name.endswith(".blocked.md")
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return None
    text = candidates[0].read_text(encoding="utf-8", errors="replace")
    section = re.search(
        r"^##[ \t]+阻断项[ \t]*\r?\n([\s\S]*?)(?=^##[ \t]|\Z)",
        text,
        re.MULTILINE,
    )
    if not section:
        return None
    body = section.group(1).strip()
    if not body or body in ("- 无。", "- 无"):
        return None
    return f"（摘自 {candidates[0].name}）\n{body}"


def build_prompt(
    concept: str,
    group: str,
    digest: str,
    hashes: dict[str, str],
    contents: dict[str, str],
    changed: list[str],
    prev_findings: str | None,
    full_mode: bool,
) -> str:
    identities = "\n".join(
        f"- `{path}`：`{value}`" for path, value in hashes.items()
    )
    materials = "\n\n".join(
        f"===== BEGIN {path} =====\n{text}\n===== END {path} ====="
        for path, text in contents.items()
    )
    if full_mode:
        mode_block = "本轮为全量重审（--full），所有输入文件均视为评审对象。"
    else:
        changed_list = "\n".join(f"- `{path}`" for path in changed) or "- 无"
        findings_block = prev_findings or "无（上轮无未关闭阻断项，或本轮为首次评审）。"
        mode_block = f"""本轮为 delta 增量评审。本轮变更文件清单（自上次评审后 hash 变化或从未评审）：
{changed_list}

上轮未关闭 findings（必须逐条核实是否已修复，并在『本轮变更裁决』中给出结论）：
{findings_block}

裁决纪律：只就本轮变更文件与上述既有 findings 作出裁决；不得推翻已冻结且本轮
未变更部分的既有结论；评审中新发现的、与本轮变更无关的非阻断问题只能写入
『Backlog』段，不得计入阻断项。"""
    return f"""你是 Bridge {concept} Action Design 的独立反方评审员。本次只审
{group}，输入 pack SHA-256 为 `{digest}`。

这是严格只读任务。禁止调用工具、修改、创建或删除文件；只能使用下面内嵌的
hash-bound 材料：
{identities}

{mode_block}

请逐 Action 对抗性检查：
1. trigger、输入、observer、state read/write 和输出是否构成唯一稳定边界；
2. P/N/F oracle 是否实现无关、可独立执行，是否会把 dependency、Job aggregate、
   系统服务、UI、build 或另一个 Action PASS 当成本 Action PASS；
3. Action 语义是否与 Concept 级 bridge contract / strategy 决策一致；
4. Action dependency 是否只依赖较小 ID 或明确 external gate，是否有循环；
5. 设计文档是否足以让实现者不再发明 architecture，同时没有虚构已存在代码；
6. 是否存在硬编码、跨代拼接、第二真源、默认成功、collect-only、partial receipt、
   NOT_STARTED 假 transaction 等可被恶意实现者利用的歧义；
7. evidence 输出是否足以让未参与实现的独立 agent 给
   PASS/FAIL/BLOCK/SPEC_GAP。

只输出中文 Markdown，严格使用：

# {concept} Action Design {group} 独立挑刺
## 结论
只能单独写：`建议批准`、`修改后批准`、`不建议批准`
## 本轮变更裁决
逐条列出本轮变更文件与上轮未关闭 findings 的裁决结果；全量重审时写 `- 全量重审。`
## 阻断项
逐项写 `[P0|P1]`、Action ID、精确文件/字段、冲突、最小修改；无则 `- 无。`
## 非阻断项
逐项写 `[P2]`；无则 `- 无。`
## Backlog
只写与本轮变更无关的新发现非阻断问题；无则 `- 无。`
## 逐 Action 闭环
每个 Action 单独说明独立边界、P/N/F 和 evidence 是否闭合。
## 跨 Action 风险
说明依赖、single writer、并发、恢复和 verdict 继承风险。
## 评审边界
明确这只是设计挑刺，不是实现、设备或 Action PASS。

以下是唯一允许使用的材料：

{materials}
"""


def invoke_kimi(
    review_command: Path,
    model: str | None,
    prompt: str,
    timeout: int,
    group: str,
) -> tuple[str, str]:
    """调用 kimi headless，返回 (review_text, transport)。失败抛 SystemExit。"""
    with tempfile.TemporaryDirectory(
        prefix=f"bridge-kimi-review-{group.lower()}-"
    ) as review_dir:
        review_dir_name = Path(review_dir).name
        command = [str(review_command)]
        if model:
            command.extend(["--model", model])
        command.extend(["--prompt", prompt, "--output-format", "text"])
        try:
            result = subprocess.run(
                command,
                cwd=review_dir,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise SystemExit(f"评审在 {timeout} 秒后超时") from error

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise SystemExit(f"评审失败 exit={result.returncode}: {detail[-500:]}")
    review = result.stdout.strip()
    transport = "wrapper_stdout"
    try:
        parse_verdict(review)
    except SystemExit as parse_error:
        recovered = recover_review_from_alex_wire(review_dir_name)
        if recovered is None:
            raise SystemExit(f"评审输出无法解析 verdict：{parse_error}") from parse_error
        review, wire_path = recovered
        transport = f"isolated_session_wire:{wire_path}"
        parse_verdict(review)
    return review, transport


def write_artifact(output: Path, metadata: dict, body: str) -> None:
    artifact = (
        "---\n"
        + yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False)
        + "---\n\n"
        + body.rstrip()
        + "\n"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=output.parent,
        prefix=".kimi-action-review.",
        delete=False,
    ) as stream:
        stream.write(artifact)
        temporary = Path(stream.name)
    temporary.replace(output)


def review_group(
    concept: str,
    group: str,
    inputs: list[Path],
    hashes: dict[str, str],
    changed: list[str],
    prev_findings: str | None,
    out_dir: Path,
    review_command: Path,
    model: str | None,
    timeout: int,
    full_mode: bool,
    force: bool,
    version: str,
) -> dict:
    """评审单个 Action 组。返回结果 dict（ok/blocked/reason/output/verdict）。"""
    digest = pack_digest(hashes)
    output = out_dir / f"kimi-{group.lower()}-{digest[:12]}.md"
    if output.exists() and output.stat().st_size > 200 and not force:
        return {"group": group, "ok": True, "skipped": True, "output": output}

    contents = {
        str(path): (ROOT / path).read_text(encoding="utf-8") for path in inputs
    }
    prompt = build_prompt(
        concept, group, digest, hashes, contents, changed, prev_findings, full_mode
    )

    attempts = [(prompt, timeout, "full_pack")]
    # 降级重试：缩小到仅本轮变更文件（全量模式下去掉共享文档），600s。
    if full_mode:
        shrunk_keys = [
            path for path in contents if path.startswith(f"docs/spec/atoms/{concept}/")
        ]
    else:
        shrunk_keys = [path for path in changed if path in contents]
    if shrunk_keys and len(shrunk_keys) < len(contents):
        shrunk_contents = {key: contents[key] for key in shrunk_keys}
        shrunk_prompt = build_prompt(
            concept, group, digest, hashes, shrunk_contents,
            changed, prev_findings, full_mode,
        )
        attempts.append((shrunk_prompt, RETRY_TIMEOUT, "changed_files_only"))

    errors = []
    review = None
    transport = None
    used_attempt = None
    for attempt_prompt, attempt_timeout, attempt_label in attempts:
        try:
            review, transport = invoke_kimi(
                review_command, model, attempt_prompt, attempt_timeout, group
            )
            used_attempt = attempt_label
            break
        except SystemExit as error:
            errors.append(f"{attempt_label}: {error}")
            continue

    if review is None:
        reason = "；".join(errors)
        blocked_output = out_dir / f"kimi-{group.lower()}-{digest[:12]}.blocked.md"
        metadata = {
            "review_type": "action_design_adversarial_review",
            "concept": concept,
            "group": group,
            "reviewed_pack_sha256": digest,
            "reviewer": "kimi_cli_headless",
            "verdict": "BLOCKED_NO_ARTIFACT",
            "failure_reason": reason,
            "attempts": errors,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "allowed_input_sha256": hashes,
        }
        body = (
            f"# {concept} Action Design {group} 评审 BLOCKED_NO_ARTIFACT\n\n"
            f"评审工具未能产出有效评审，本记录用于消除『无产物的等待』。\n\n"
            f"- 输入 pack SHA-256：`{digest}`\n"
            f"- 失败原因：{reason}\n\n"
            "本组输入 hash 未写入 ledger，下次运行会自动重试本组。\n"
        )
        write_artifact(blocked_output, metadata, body)
        return {
            "group": group, "ok": False, "reason": reason,
            "output": blocked_output, "digest": digest,
        }

    after = {str(path): sha256(ROOT / path) for path in inputs}
    if after != hashes:
        return {
            "group": group, "ok": False,
            "reason": "评审期间输入文件变化，拒绝保存失配结果",
            "output": None, "digest": digest,
        }

    verdict = parse_verdict(review)
    metadata = {
        "review_type": "action_design_adversarial_review",
        "concept": concept,
        "group": group,
        "reviewed_pack_sha256": digest,
        "review_mode": "full" if full_mode else "delta",
        "review_attempt": used_attempt,
        "changed_inputs": changed,
        "reviewer": "kimi_cli_headless",
        "reviewer_model": model or "_kimi.alex default (k3)",
        "review_command": str(review_command),
        "reviewer_version": version,
        "review_transport": transport,
        "verdict": verdict,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "allowed_input_sha256": hashes,
    }
    write_artifact(output, metadata, review)
    return {
        "group": group, "ok": True, "skipped": False, "output": output,
        "verdict": verdict, "digest": digest,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--concept", required=True, help="FnXX，如 Fn01")
    parser.add_argument("--actions", default=None, help="逗号分隔子集，如 A01,A02")
    parser.add_argument("--group", default=None, help="单个连续范围组，如 A01-A05")
    parser.add_argument("--out", type=Path, default=None, help="评审输出目录")
    parser.add_argument("--full", action="store_true", help="关闭 delta，全量重审")
    parser.add_argument("--jobs", type=int, default=1, help="并行评审的组数")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--group-size", type=int, default=GROUP_SIZE)
    parser.add_argument(
        "--review-command", type=Path, default=DEFAULT_REVIEW_COMMAND
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--force", action="store_true", help="忽略已有 artifact")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划，不调用 kimi")
    args = parser.parse_args()

    concept = args.concept
    if not re.fullmatch(r"Fn\d{2}", concept):
        raise SystemExit(f"--concept 必须是 FnXX 形式，收到：{concept}")
    if args.actions and args.group:
        raise SystemExit("--actions 与 --group 互斥")
    if args.jobs < 1:
        raise SystemExit("--jobs 必须 >= 1")

    out_dir = args.out or (
        ROOT / "evidence" / "concepts" / concept / "action-design-reviews"
    )
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    ledger_path = out_dir / LEDGER_NAME

    discovered = discover_actions(concept)
    if args.group:
        wanted = expand_group_selector(args.group)
        missing = [a for a in wanted if a not in discovered]
        for action in missing:
            warn(f"--group 指定的 {action} 不存在于 docs/spec/atoms/{concept}，跳过")
        selected = [a for a in wanted if a in discovered]
        if not selected:
            raise SystemExit("--group 指定的 Action 全部不存在")
        groups = [(args.group.strip(), selected)]
    elif args.actions:
        wanted = parse_actions_selector(args.actions)
        missing = [a for a in wanted if a not in discovered]
        for action in missing:
            warn(f"--actions 指定的 {action} 不存在于 docs/spec/atoms/{concept}，跳过")
        selected = [a for a in wanted if a in discovered]
        if not selected:
            raise SystemExit("--actions 指定的 Action 全部不存在")
        groups = group_actions(selected, args.group_size)
    else:
        groups = group_actions(discovered, args.group_size)

    shared_inputs = collect_shared_inputs(concept)

    ledger = load_ledger(ledger_path)
    ledger_files: dict = ledger["files"]

    # 预计算每组的输入、hash 与变更清单。
    plans = []
    for name, actions in groups:
        inputs = list(shared_inputs)
        for action in actions:
            inputs.extend(collect_action_inputs(concept, action))
        hashes = {str(path): sha256(ROOT / path) for path in inputs}
        changed = [
            str(path)
            for path in inputs
            if ledger_files.get(str(path)) != hashes[str(path)]
        ]
        plans.append(
            {"name": name, "actions": actions, "inputs": inputs,
             "hashes": hashes, "changed": changed}
        )

    if args.full:
        pending = plans
    else:
        pending = [plan for plan in plans if plan["changed"]]

    if args.dry_run:
        print(f"concept={concept} out={out_dir.relative_to(ROOT)}")
        print(f"mode={'full' if args.full else 'delta'} jobs={args.jobs} "
              f"ledger={ledger_path.relative_to(ROOT)}")
        for plan in plans:
            digest = pack_digest(plan["hashes"])
            output = out_dir / f"kimi-{plan['name'].lower()}-{digest[:12]}.md"
            if not args.full and not plan["changed"]:
                print(f"[SKIP] {plan['name']}：输入无变化（{len(plan['inputs'])} 个文件）")
                continue
            print(f"[REVIEW] {plan['name']}（{', '.join(plan['actions'])}）")
            print(f"  输出: {output.relative_to(ROOT)}")
            print(f"  输入 {len(plan['inputs'])} 个文件，变更 {len(plan['changed'])} 个：")
            for path in plan["changed"]:
                print(f"    - {path}")
        if not pending:
            print("NO-OP：所有组输入均无变化。")
        return 0

    if not pending:
        print(f"NO-OP：{concept} 共 {len(plans)} 个组，输入自上次评审后均无变化。")
        return 0

    review_command = args.review_command.expanduser().resolve()
    if not review_command.is_file():
        raise SystemExit(f"找不到 Kimi review command: {review_command}")
    version_result = subprocess.run(
        [str(review_command), "--version"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    version = (version_result.stdout or version_result.stderr).strip()

    def run_plan(plan: dict) -> dict:
        prev = None if args.full else previous_open_findings(out_dir, plan["name"])
        return review_group(
            concept=concept,
            group=plan["name"],
            inputs=plan["inputs"],
            hashes=plan["hashes"],
            changed=plan["changed"],
            prev_findings=prev,
            out_dir=out_dir,
            review_command=review_command,
            model=args.model,
            timeout=args.timeout,
            full_mode=args.full,
            force=args.force,
            version=version,
        )

    results = []
    if args.jobs == 1 or len(pending) == 1:
        for plan in pending:
            results.append(run_plan(plan))
    else:
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            for result in pool.map(run_plan, pending):
                results.append(result)

    # 只在主线程更新 ledger：成功组写入其输入 hash；失败组不写，下次自动重试。
    now = datetime.now(timezone.utc).isoformat()
    blocked = []
    plan_by_name = {plan["name"]: plan for plan in pending}
    for result in results:
        group = result["group"]
        if result["ok"]:
            plan = plan_by_name[group]
            for path, digest_value in plan["hashes"].items():
                ledger_files[path] = digest_value
            ledger["groups"][group] = {
                "digest": result.get("digest") or pack_digest(plan["hashes"]),
                "artifact": str(result["output"].relative_to(ROOT)),
                "verdict": result.get("verdict", "cached"),
                "reviewed_at": now,
            }
            status = "SKIP(已有 artifact)" if result.get("skipped") else result["verdict"]
            print(f"[OK] {group}: {status} -> {result['output'].relative_to(ROOT)}")
        else:
            blocked.append(result)
            print(f"[BLOCKED] {group}: {result['reason']}", file=sys.stderr)
            if result.get("output"):
                print(f"  记录: {result['output'].relative_to(ROOT)}", file=sys.stderr)

    ledger["concept"] = concept
    ledger["updated_at"] = now
    save_ledger(ledger_path, ledger)

    if blocked:
        print(f"{len(blocked)} 个组评审失败（BLOCKED_NO_ARTIFACT）", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
