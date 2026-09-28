#!/usr/bin/env python3
"""Run hash-bound, read-only Kimi challenge reviews for Fn03 Action designs."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

from run_kimi_concept_approval_review import parse_verdict, recover_review_from_alex_wire


ROOT = Path(__file__).resolve().parents[1]
REVIEW_COMMAND = Path("/Users/alexyang/.local/bin/_kimi.alex")
GROUPS = {"A01-A05": range(1, 6), "A06-A10": range(6, 11)}
SHARED = (
    Path("docs/concepts/Fn03/BRIDGE_CONTRACT.md"),
    Path("docs/spec/concepts/Fn03/bridge-contract.yaml"),
    Path("docs/concepts/Fn03/STRATEGY_DECISION.md"),
    Path("docs/concepts/Fn03/CONCEPT_DESIGN.md"),
    Path("docs/spec/concepts/Fn03/action-map.yaml"),
    Path("docs/spec/concepts/Fn03/lifecycle-mapping-v1.yaml"),
    Path("docs/spec/concepts/Fn03/timeout-policy-v1.yaml"),
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs(group: str) -> list[Path]:
    result = list(SHARED)
    for number in GROUPS[group]:
        root = Path(f"docs/spec/atoms/Fn03/A{number:02d}")
        result += [root / "atom.yaml", root / "DESIGN_SPEC.md", root / "verification.md"]
    return result


def prompt(group: str, digest: str, hashes: dict[str, str], contents: dict[str, str]) -> str:
    identities = "\n".join(f"- `{path}`: `{value}`" for path, value in hashes.items())
    materials = "\n\n".join(
        f"===== BEGIN {path} =====\n{text}\n===== END {path} ====="
        for path, text in contents.items()
    )
    return f"""你是 Bridge Fn03 Action Design 的独立反方评审员。本次只审 {group}，
输入 pack SHA-256 为 `{digest}`。这是严格只读任务，禁止调用工具或修改文件，只能
使用下面内嵌的 hash-bound 材料：

{identities}

背景：owner 已裁决 R1 为主方案；R2 只是未来升级方案，不是 backup/fallback。
R1 必须保持边界 reducer、native owner/generation-bound opaque capability 和未修改的
AOSP ClientTransaction/ActivityThread 主链。
项目固定规则：`capability_bits` 只是 Cr/Qy/Up/Dl/Ex/Ps/Cc/Is 的 one-hot 类型位，
不是 capability 唯一编号；同为 Ex 的 A02/A03/A04/A06/A07/A10 使用同一
`0000-1000` 是正确分类，唯一身份由 Action ID 与 capability_name 提供。

请逐 Action 对抗性检查：
1. trigger、observer、state read/write、输出是否形成唯一可独立核验边界；
2. positive/negative/failure oracle 是否实现无关且不会继承相邻 Action、UI、build；
3. token、owner、process_epoch、generation、transition_id 是否端到端闭合；
4. callback、mapping、ACK、first-frame receipt 的所有权与依赖是否无循环；
5. 是否允许裸地址、Java/native 双真源、timeout 假成功、默认状态、重复 ACK；
6. A10 是否只消费 Fn04 typed first-content-present receipt，而不自产渲染事实；
7. evidence 是否足够让独立 agent 给 PASS/FAIL/BLOCK/SPEC_GAP。

只输出中文 Markdown，严格使用：

# Fn03 Action Design {group} 独立挑刺
## 结论
只能单独写：`建议批准`、`修改后批准`、`不建议批准`
## 阻断项
逐项写 `[P0|P1]`、Action ID、精确文件/字段、冲突、最小修改；无则 `- 无。`
## 非阻断项
逐项写 `[P2]`；无则 `- 无。`
## 逐 Action 闭环
每个 Action 单独说明独立边界、P/N/F 和 evidence 是否闭合。
## 跨 Action 风险
说明依赖、状态所有权、并发、恢复和 verdict 继承风险。
## 评审边界
明确这只是设计挑刺，不是实现、设备或 Action PASS。

以下是唯一允许使用的材料：

{materials}
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", choices=GROUPS, required=True)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not REVIEW_COMMAND.is_file():
        raise SystemExit(f"missing review command: {REVIEW_COMMAND}")
    selected = inputs(args.group)
    missing = [str(path) for path in selected if not (ROOT / path).is_file()]
    if missing:
        raise SystemExit("missing review inputs: " + ", ".join(missing))

    hashes = {str(path): sha(ROOT / path) for path in selected}
    digest = hashlib.sha256(
        json.dumps(hashes, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    output = (
        ROOT
        / "var/evidence/concepts/Fn03/action-design-reviews"
        / f"kimi-{args.group.lower()}-{digest[:12]}.md"
    )
    if output.exists() and output.stat().st_size > 200 and not args.force:
        print(output.relative_to(ROOT))
        return 0
    contents = {str(path): (ROOT / path).read_text(encoding="utf-8") for path in selected}
    version_result = subprocess.run(
        [str(REVIEW_COMMAND), "--version"], text=True, capture_output=True, check=False
    )
    version = (version_result.stdout or version_result.stderr).strip()

    with tempfile.TemporaryDirectory(prefix=f"bridge-kimi-fn03-{args.group.lower()}-") as cwd:
        cwd_name = Path(cwd).name
        try:
            result = subprocess.run(
                [
                    str(REVIEW_COMMAND),
                    "--prompt",
                    prompt(args.group, digest, hashes, contents),
                    "--output-format",
                    "text",
                ],
                cwd=cwd,
                text=True,
                capture_output=True,
                timeout=args.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise SystemExit(f"Kimi review timeout after {args.timeout}s") from error
    if result.returncode != 0:
        raise SystemExit((result.stderr or result.stdout)[-1200:])
    review = result.stdout.strip()
    transport = "wrapper_stdout"
    try:
        verdict = parse_verdict(review)
    except SystemExit:
        recovered = recover_review_from_alex_wire(cwd_name)
        if recovered is None:
            raise
        review, wire = recovered
        verdict = parse_verdict(review)
        transport = f"isolated_session_wire:{wire}"

    if {str(path): sha(ROOT / path) for path in selected} != hashes:
        raise SystemExit("review inputs changed during review")
    metadata = {
        "review_type": "fn03_action_design_adversarial_review",
        "group": args.group,
        "reviewed_pack_sha256": digest,
        "reviewer": "kimi_cli_headless",
        "reviewer_model": "_kimi.alex default",
        "review_command": str(REVIEW_COMMAND),
        "reviewer_version": version,
        "review_transport": transport,
        "verdict": verdict,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "allowed_input_sha256": hashes,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "---\n"
        + yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False)
        + "---\n\n"
        + review.rstrip()
        + "\n",
        encoding="utf-8",
    )
    print(output.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
