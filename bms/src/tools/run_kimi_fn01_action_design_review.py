#!/usr/bin/env python3
"""用隔离的 _kimi.alex 对 Fn01 Action 设计分组执行 hash-bound 只读挑刺。"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

from run_kimi_concept_approval_review import (
    parse_verdict,
    recover_review_from_alex_wire,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REVIEW_COMMAND = Path("/Users/alexyang/.local/bin/_kimi.alex")
GROUPS = {
    "A01-A05": range(1, 6),
    "A06-A10": range(6, 11),
    "A11-A15": range(11, 16),
    "A16-A19": range(16, 20),
}
SHARED_INPUTS = (
    Path("docs/concepts/Fn01/BRIDGE_CONTRACT.md"),
    Path("docs/spec/concepts/Fn01/bridge-contract.yaml"),
    Path("docs/concepts/Fn01/STRATEGY_DECISION.md"),
    Path("docs/concepts/Fn01/CONCEPT_DESIGN.md"),
    Path("docs/concepts/Fn01/MULTI_APK_DESIGN_SPEC.md"),
    Path("docs/concepts/Fn01/ANDROID_MODEL.md"),
    Path("docs/concepts/Fn01/OPENHARMONY_MODEL.md"),
    Path("docs/spec/concepts/Fn01/action-map.yaml"),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def group_inputs(group: str) -> tuple[Path, ...]:
    paths = list(SHARED_INPUTS)
    for number in GROUPS[group]:
        action = f"A{number:02d}"
        root = Path("docs/spec/atoms/Fn01") / action
        paths.extend(
            (
                root / "atom.yaml",
                root / "DESIGN_SPEC.md",
                root / "verification.md",
            )
        )
    return tuple(paths)


def pack_digest(hashes: dict[str, str]) -> str:
    canonical = json.dumps(
        hashes, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def build_prompt(
    group: str,
    digest: str,
    hashes: dict[str, str],
    contents: dict[str, str],
) -> str:
    identities = "\n".join(
        f"- `{path}`：`{value}`" for path, value in hashes.items()
    )
    materials = "\n\n".join(
        f"===== BEGIN {path} =====\n{text}\n===== END {path} ====="
        for path, text in contents.items()
    )
    return f"""你是 Bridge Fn01 Action Design 的独立反方评审员。本次只审
{group}，输入 pack SHA-256 为 `{digest}`。

这是严格只读任务。禁止调用工具、修改、创建或删除文件；只能使用下面内嵌的
hash-bound 材料：
{identities}

背景：Fn01 Concept 已接受，R2 是 primary、R3 是 backup。产品必须支持通用多
APK 安装/管理，不得使用历史 packageName、Activity、签名、APK 数量、corpus
或设备路径硬编码。A01-A13 保持稳定 ID；A14-A19 只给真正可独立触发、观察并
产生独立 verdict 的 update、uninstall、stable list、durable Job、reconcile、
same-package concurrency。

请逐 Action 对抗性检查：
1. trigger、输入、observer、state read/write 和输出是否构成唯一稳定边界；
2. P/N/F oracle 是否实现无关、可独立执行，是否会把 dependency、Job aggregate、
   BMS、UI、build 或另一个 Action PASS 当成本 Action PASS；
3. R2 single writer、generation/digest、P5、restart、tombstone、retirement、
   snapshot、CAS 与 member receipt 语义是否和 Contract 一致；
4. Action dependency 是否只依赖较小 ID 或明确 external gate，是否有循环；
5. DESIGN_SPEC 是否足以让实现者不再发明 architecture，同时没有虚构已存在代码；
6. 是否存在硬编码、跨代拼接、第二真源、默认成功、collect-only、partial receipt、
   NOT_STARTED 假 transaction 等可被恶意实现者利用的歧义；
7. evidence 输出是否足以让未参与实现的独立 agent 给
   PASS/FAIL/BLOCK/SPEC_GAP。

只输出中文 Markdown，严格使用：

# Fn01 Action Design {group} 独立挑刺
## 结论
只能单独写：`建议批准`、`修改后批准`、`不建议批准`
## 阻断项
逐项写 `[P0|P1]`、Action ID、精确文件/字段、冲突、最小修改；无则 `- 无。`
## 非阻断项
逐项写 `[P2]`；无则 `- 无。`
## 逐 Action 闭环
每个 Action 单独说明独立边界、P/N/F 和 evidence 是否闭合。
## 跨 Action 风险
说明依赖、single writer、并发、恢复和 verdict 继承风险。
## 评审边界
明确这只是设计挑刺，不是实现、设备或 Action PASS。

以下是唯一允许使用的材料：

{materials}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", choices=GROUPS, required=True)
    parser.add_argument(
        "--review-command", type=Path, default=DEFAULT_REVIEW_COMMAND
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    review_command = args.review_command.expanduser().resolve()
    if not review_command.is_file():
        raise SystemExit(f"找不到 Kimi review command: {review_command}")

    inputs = group_inputs(args.group)
    missing = [str(path) for path in inputs if not (ROOT / path).is_file()]
    if missing:
        raise SystemExit("缺少评审输入：" + ", ".join(missing))
    hashes = {str(path): sha256(ROOT / path) for path in inputs}
    digest = pack_digest(hashes)
    contents = {
        str(path): (ROOT / path).read_text(encoding="utf-8") for path in inputs
    }
    output = (
        ROOT
        / "var/evidence/concepts/Fn01/action-design-reviews"
        / f"kimi-{args.group.lower()}-{digest[:12]}.md"
    )
    if output.exists() and output.stat().st_size > 200 and not args.force:
        print(output.relative_to(ROOT))
        return 0

    version_result = subprocess.run(
        [str(review_command), "--version"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    version = (version_result.stdout or version_result.stderr).strip()
    with tempfile.TemporaryDirectory(
        prefix=f"bridge-kimi-fn01-{args.group.lower()}-"
    ) as review_dir:
        review_dir_name = Path(review_dir).name
        command = [str(review_command)]
        if args.model:
            command.extend(["--model", args.model])
        command.extend(
            [
                "--prompt",
                build_prompt(args.group, digest, hashes, contents),
                "--output-format",
                "text",
            ]
        )
        try:
            result = subprocess.run(
                command,
                cwd=review_dir,
                text=True,
                capture_output=True,
                timeout=args.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise SystemExit(
                f"Kimi {args.group} 评审在 {args.timeout} 秒后超时"
            ) from error

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise SystemExit(
            f"Kimi {args.group} 评审失败 exit={result.returncode}: {detail[-1000:]}"
        )
    review = result.stdout.strip()
    transport = "wrapper_stdout"
    try:
        verdict = parse_verdict(review)
    except SystemExit as parse_error:
        recovered = recover_review_from_alex_wire(review_dir_name)
        if recovered is None:
            raise parse_error
        review, wire_path = recovered
        transport = f"isolated_session_wire:{wire_path}"
        verdict = parse_verdict(review)

    after = {str(path): sha256(ROOT / path) for path in inputs}
    if after != hashes:
        raise SystemExit("Kimi 评审期间输入变化，拒绝保存失配结果")

    metadata = {
        "review_type": "fn01_action_design_adversarial_review",
        "group": args.group,
        "reviewed_pack_sha256": digest,
        "reviewer": "kimi_cli_headless",
        "reviewer_model": args.model or "_kimi.alex default (k3)",
        "review_command": str(review_command),
        "reviewer_version": version,
        "review_transport": transport,
        "verdict": verdict,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "allowed_input_sha256": hashes,
    }
    artifact = (
        "---\n"
        + yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False)
        + "---\n\n"
        + review.rstrip()
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
    print(output.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
