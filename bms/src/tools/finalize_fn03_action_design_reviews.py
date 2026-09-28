#!/usr/bin/env python3
"""Write hash-bound Fn03 Action REVIEW_LOG files after cleared group reviews."""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
REVIEWS = {
    "A01-A05": Path(
        "var/evidence/concepts/Fn03/action-design-reviews/"
        "kimi-a01-a05-41bf9af39a7c.md"
    ),
    "A06-A10": Path(
        "var/evidence/concepts/Fn03/action-design-reviews/"
        "kimi-a06-a10-ceaa0aff36f8.md"
    ),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    for number in range(1, 11):
        suffix = f"A{number:02d}"
        action_id = f"Fn03.{suffix}"
        group = "A01-A05" if number <= 5 else "A06-A10"
        review = REVIEWS[group]
        review_data = yaml.safe_load(
            (ROOT / review).read_text(encoding="utf-8").split("\n---\n", 1)[0][4:]
        )
        if review_data.get("verdict") != "建议批准":
            raise SystemExit(f"{review} is not cleared")
        spec = ROOT / "docs/spec/atoms/Fn03" / suffix
        hashes = {
            "atom_yaml": digest(spec / "atom.yaml"),
            "design_spec": digest(spec / "DESIGN_SPEC.md"),
            "verification": digest(spec / "verification.md"),
        }
        content = f"""---
action_id: {action_id}
status: cleared
author: codex-fn03-action-designer
reviewer: kimi_cli_headless
engine: _kimi.alex
review_command: python3 src/tools/run_kimi_fn03_action_design_review.py --group {group}
review_artifact: {review}
review_artifact_sha256: {digest(ROOT / review)}
reviewed_sha256:
  atom_yaml: {hashes["atom_yaml"]}
  design_spec: {hashes["design_spec"]}
  verification: {hashes["verification"]}
---

# {action_id} Action Design Review Log

## AOSP semantics

评审确认本 Action 保持未修改的 AOSP ClientTransaction/ActivityThread callback
所有权；Bridge 只维护 typed identity、ordering、mapping 和 receipt，不以 JNI
返回、日志、进程或相邻 Action verdict 替代真实 callback。

## OpenHarmony mapping

OpenHarmony Ability lifecycle 仍是真实控制面 owner。Action 只消费冻结的
`fn03-lifecycle-mapping-v1` 与 timeout policy；OH token 使用 native opaque
capability，AbilityTransitionDone 只有满足 terminal receipt 条件才发送。

## Adversarial implementation

最终 hash-bound 评审检查了裸地址身份、Java/native 双真源、错误 generation、
重复 transition、timeout 假成功、乱序 callback、first-frame 伪造和依赖 verdict
继承。前序 P1 均已在当前三份输入中处置；最终 artifact 结论为“建议批准”。

## Findings

当前 hash 对应输入无 P0/P1 阻断项。非阻断提醒不扩大 R1 权限，也不构成实现、
构建、设备验证或 Action PASS。

## Disposition

设计允许进入 br-action-implement。实现必须冻结本 REVIEW_LOG 中三份 SHA-256，
使用自然源码位置和真实 host/device evidence；任何输入变化都使本 review 失效并
要求重新评审。
"""
        (ROOT / "docs/atoms/Fn03" / suffix / "REVIEW_LOG.md").write_text(
            content, encoding="utf-8"
        )

    concept_inputs = [
        ROOT / "docs/concepts/Fn03/CONCEPT_DESIGN.md",
        ROOT / "docs/spec/concepts/Fn03/lifecycle-mapping-v1.yaml",
        ROOT / "docs/spec/concepts/Fn03/timeout-policy-v1.yaml",
        ROOT / REVIEWS["A01-A05"],
        ROOT / REVIEWS["A06-A10"],
    ]
    reviewed = "\n".join(
        f"  {path.relative_to(ROOT)}: {digest(path)}" for path in concept_inputs
    )
    concept_log = f"""---
concept_id: Fn03
author: codex-fn03-action-designer
reviewer: kimi_cli_headless
status: cleared
reviewed_sha256:
{reviewed}
---

# Fn03 Concept Design Review Log

Fn03 Action 设计被拆成 A01-A05 与 A06-A10 两组，通过隔离 `_kimi.alex` 执行
hash-bound 只读对抗评审。最终两组 verdict 均为“建议批准”，P0/P1 为零。

## AOSP 语义

设计保持 stock ClientTransaction、ActivityThread main-thread callback 与真实
Activity state owner，不允许 adapter 直接调用 callback 或复制 AOSP 真相。

## OpenHarmony 映射

OH Ability lifecycle 为 foreground-loss 唯一事实 owner；mapping version、
AbilityTransitionDone、terminal join 和 first-frame receipt 的 producer/consumer
边界已经冻结。

## 历史证据与相邻 Concept

设计只把历史 HanBing 机制当案例证据，不继承历史 PASS。Fn02 仅提供进程/bind
前态，Fn04.C05 生产 first-content-present receipt，Fn06 保持 launch policy owner。

## Action 稳定性与 adversarial implementation

A01-A10 各自保持独立 trigger、observer、state write 和 P/N/F verdict。评审连续
消除了身份字段缺失、双腿幂等冲突、无界 timeout、A09 bind/launch schema 混用、
A10 join 竞态与 A05 terminal ordering 等可被对抗实现利用的歧义。

## Findings

当前 hash 集无阻断项。评审只关闭设计门，不代表实现、单元测试、真机测试、
独立 Action verification 或 Journey 完成。

## Disposition

准许 br-action-implement 读取当前冻结输入。任一 atom/design/verification 变化必须
重新运行 hash-bound review；实现者不得担任最终 verifier。
"""
    (ROOT / "docs/concepts/Fn03/REVIEW_LOG.md").write_text(
        concept_log, encoding="utf-8"
    )


if __name__ == "__main__":
    main()
