#!/usr/bin/env python3
"""用隔离的 _kimi.alex 对 Fn01 受信包管理服务拓扑做 hash-bound 只读挑刺。"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from run_kimi_concept_approval_review import (
    parse_verdict,
    recover_review_from_alex_wire,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REVIEW_COMMAND = Path("/Users/alexyang/.local/bin/_kimi.alex")
INPUTS = (
    Path("docs/concepts/Fn01/PACKAGE_MANAGEMENT_SERVICE_TOPOLOGY_PROPOSAL.md"),
    Path("docs/concepts/Fn01/BRIDGE_CONTRACT.md"),
    Path("docs/concepts/Fn01/STRATEGY_DECISION.md"),
    Path("docs/concepts/Fn01/MULTI_APK_DESIGN_SPEC.md"),
    Path("src/adapter/framework/package-manager/package_info/src/package_info_runtime_v1.cpp"),
    Path("src/adapter/framework/package-manager/package_transaction/src/package_transaction_v1.cpp"),
    Path("src/adapter/framework/package-manager/jni/package_info_jni.cpp"),
    Path("src/adapter/framework/core/java/ServiceInterceptor.java"),
    Path("src/adapter/framework/appspawn-x/java/com/android/internal/os/AppSpawnXInit.java"),
    Path("var/evidence/atoms/Fn01/A04/runs/20260728T012642Z-d600-runtime-baseline/raw/61b0657200000000000000000324012c-identity.txt"),
    Path("var/evidence/atoms/Fn01/A04/runs/20260728T012642Z-d600-runtime-baseline/raw/654b3a6b00000000000000000824012c-identity.txt"),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pack_digest(hashes: dict[str, str]) -> str:
    encoded = json.dumps(
        hashes, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_prompt(digest: str, hashes: dict[str, str], contents: dict[str, str]) -> str:
    identities = "\n".join(f"- `{p}`：`{v}`" for p, v in hashes.items())
    materials = "\n\n".join(
        f"===== BEGIN {path} =====\n{text}\n===== END {path} ====="
        for path, text in contents.items()
    )
    return f"""你是 Bridge Fn01 R2 生产拓扑的独立反方架构评审员。
输入 pack SHA-256 为 `{digest}`。

这是严格只读任务。禁止调用工具或修改文件，只能使用下面 hash-bound 材料：
{identities}

请集中挑刺一个问题：Bridge PackageStore/PackageManagementService 应由哪个受信
进程拥有，Android 应用进程内的 PackageManagerAdapter 应如何调用。不得把 host
fixture、静态 build 或旧 D600 artifact 当成产品接线证据。

必须检查：
1. 提案的“app 进程内 adapter”事实是否真的推出独立受信边界，是否遗漏已有
   OH/AOSP 系统服务承载点；
2. T1/T2/T3 是否真是结构不同的路线，T4 拒绝理由是否充分；
3. T1 的 peer identity、user/visibility、启动顺序、SELinux、BMS 权限、
   death/restart、事务恢复是否有致命缺口；
4. T2 是否可能在不形成双权威的条件下更合理，所需资格证据是什么；
5. 推荐 primary/backup 是否与已接受 R2/R3、AonB 边界、single writer、
   generation/digest/publication fence 一致；
6. owner gate 应冻结哪些内容，哪些应留给实现设计；
7. 给出可执行的最小设备/源码审计实验，能在写大量代码前证伪 T1 或 T2。

只输出中文 Markdown，严格使用：

# Fn01 受信包管理服务拓扑独立挑刺
## 结论
只能单独写：`建议批准`、`修改后批准`、`不建议批准`
## 阻断项
逐项写 `[P0|P1]`、精确材料位置、冲突、最小修改；无则 `- 无。`
## 路线比较
逐一裁判 T1–T4。
## 必须先做的证伪实验
给出动作、观察值和 route switch 条件。
## Owner 应冻结的最小裁决
明确 primary、backup、reject、rollback triggers。
## 评审边界
声明这只是拓扑设计挑刺，不是实现、设备或 Action PASS。

以下是唯一允许使用的材料：

{materials}
"""


def extract_review_from_wire(wire: Path, digest: str) -> str:
    raw = wire.read_text(encoding="utf-8")
    if digest not in raw:
        raise SystemExit("指定 wire 不包含当前评审 pack digest")
    parts: list[str] = []
    for line in raw.splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        event = record.get("event", {})
        part = event.get("part", {})
        if (
            record.get("type") == "context.append_loop_event"
            and event.get("type") == "content.part"
            and part.get("type") == "text"
        ):
            parts.append(str(part.get("text", "")))
    review = "".join(parts).strip()
    parse_verdict(review)
    return review


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-command", type=Path, default=DEFAULT_REVIEW_COMMAND)
    parser.add_argument("--model", default=None)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--recover-wire",
        type=Path,
        help="从已完成且包含当前 pack digest 的 _kimi.alex wire 恢复评审",
    )
    args = parser.parse_args()

    review_command = args.review_command.expanduser().resolve()
    if not review_command.is_file():
        raise SystemExit(f"找不到 Kimi review command: {review_command}")
    missing = [str(path) for path in INPUTS if not (ROOT / path).is_file()]
    if missing:
        raise SystemExit("缺少评审输入：" + ", ".join(missing))

    hashes = {str(path): sha256(ROOT / path) for path in INPUTS}
    digest = pack_digest(hashes)
    contents = {
        str(path): (ROOT / path).read_text(encoding="utf-8") for path in INPUTS
    }
    output = (
        ROOT
        / "var/evidence/concepts/Fn01/topology-reviews"
        / f"kimi-package-service-topology-{digest[:12]}.md"
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
    if args.recover_wire is not None:
        wire = args.recover_wire.expanduser().resolve()
        if not wire.is_file():
            raise SystemExit(f"找不到 Kimi wire: {wire}")
        review = extract_review_from_wire(wire, digest)
        transport = f"isolated_session_wire:{wire}"
        verdict = parse_verdict(review)
    else:
        with tempfile.TemporaryDirectory(
            prefix="bridge-kimi-fn01-service-topology-"
        ) as review_dir:
            review_dir_name = Path(review_dir).name
            command = [str(review_command)]
            if args.model:
                command.extend(["--model", args.model])
            command.extend(
                [
                    "--prompt",
                    build_prompt(digest, hashes, contents),
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
                    f"Kimi 拓扑评审在 {args.timeout} 秒后超时"
                ) from error

        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise SystemExit(
                f"Kimi 拓扑评审失败 exit={result.returncode}: {detail[-1000:]}"
            )
        review = result.stdout.strip()
        transport = "wrapper_stdout"
        try:
            verdict = parse_verdict(review)
        except SystemExit as parse_error:
            recovered = None
            # _kimi.alex may return before the durable wire has flushed its
            # final text event. Give it a bounded flush window.
            for _ in range(60):
                recovered = recover_review_from_alex_wire(review_dir_name)
                if recovered is not None:
                    break
                time.sleep(0.5)
            if recovered is None:
                raise parse_error
            review, wire_path = recovered
            transport = f"isolated_session_wire:{wire_path}"
            verdict = parse_verdict(review)

    if {str(path): sha256(ROOT / path) for path in INPUTS} != hashes:
        raise SystemExit("Kimi 评审期间输入变化，拒绝保存失配结果")

    metadata = {
        "review_type": "fn01_trusted_package_service_topology",
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
        prefix=".kimi-topology-review.",
        delete=False,
    ) as stream:
        stream.write(artifact)
        temporary = Path(stream.name)
    temporary.replace(output)
    print(output.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
