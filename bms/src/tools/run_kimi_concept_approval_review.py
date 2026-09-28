#!/usr/bin/env python3
"""为 Fn01 通用多包 Concept/Strategy/Design 人工审批生成 hash 绑定的 Kimi 只读评审。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("docs/concepts/Fn01/BRIDGE_CONTRACT.md")
ALLOWED_INPUTS = (
    TARGET,
    Path("docs/concepts/Fn01/CONCEPT_DOMAIN.md"),
    Path("docs/concepts/Fn01/APK_GENERALIZATION_BOUNDARY.md"),
    Path("docs/concepts/Fn01/MULTI_APK_LIFECYCLE_AUDIT.md"),
    Path("docs/concepts/Fn01/ROUTE_SPACE.md"),
    Path("docs/concepts/Fn01/STRATEGY.md"),
    Path("docs/concepts/Fn01/STRATEGY_DECISION.md"),
    Path("docs/concepts/Fn01/MULTI_APK_DESIGN_SPEC.md"),
    Path("docs/concepts/Fn01/C07/README.md"),
    Path("docs/spec/concepts/Fn01/bridge-contract.yaml"),
    Path("docs/spec/concept-graph.yaml"),
    Path("docs/workflows/FN01_MULTI_APK_LIFECYCLE.json"),
)
DEFAULT_MODEL = "kimi-code/k3"
DEFAULT_REVIEW_COMMAND = Path("/Users/alexyang/.local/bin/_kimi.alex")
START_MARKER = "<!-- approval-review:start -->"
END_MARKER = "<!-- approval-review:end -->"
EXCLUDED_ATTACHMENT = "评审附件内容不属于被审 Concept 语义。"
VERDICTS = ("建议批准", "修改后批准", "不建议批准")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def semantic_target_bytes() -> bytes:
    text = (ROOT / TARGET).read_text(encoding="utf-8")
    if text.count(START_MARKER) != 1 or text.count(END_MARKER) != 1:
        raise SystemExit("目标文档必须各包含一个审批评审起止标记")
    before, remainder = text.split(START_MARKER, 1)
    _, after = remainder.split(END_MARKER, 1)
    normalized = (
        before
        + START_MARKER
        + "\n"
        + EXCLUDED_ATTACHMENT
        + "\n"
        + END_MARKER
        + after
    )
    return normalized.encode("utf-8")


def compact_review_contents() -> dict[str, str]:
    """Build a bounded, source-derived review pack without losing Fn01 semantics."""
    graph = yaml.safe_load((ROOT / "docs/spec/concept-graph.yaml").read_text(encoding="utf-8"))
    relevant_edges = [
        edge
        for edge in graph.get("edges", [])
        if str(edge.get("from", "")).startswith("Fn01")
        or str(edge.get("to", "")).startswith("Fn01")
    ]
    endpoint_ids = {
        str(edge.get(endpoint))
        for edge in relevant_edges
        for endpoint in ("from", "to")
        if edge.get(endpoint)
    }
    relevant_nodes = [
        node
        for node in graph.get("nodes", [])
        if str(node.get("id", "")).startswith("Fn01")
        or str(node.get("id", "")) in endpoint_ids
    ]
    assessments = graph.get("direction_assessments", {})
    relevant_assessments = {
        concept_id: value
        for concept_id, value in assessments.items()
        if str(concept_id).startswith("Fn01")
    }
    graph_projection = {
        "source": "docs/spec/concept-graph.yaml",
        "source_sha256": file_sha256(ROOT / "docs/spec/concept-graph.yaml"),
        "schema_version": graph.get("schema_version"),
        "status": graph.get("status"),
        "nodes_touching_Fn01": relevant_nodes,
        "edges_touching_Fn01": relevant_edges,
        "Fn01_direction_assessments": relevant_assessments,
    }

    contents = {
        str(TARGET): semantic_target_bytes().decode("utf-8"),
        "docs/spec/concept-graph.yaml::Fn01-source-derived-projection": yaml.safe_dump(
            graph_projection, allow_unicode=True, sort_keys=False
        ),
    }
    for relative in ALLOWED_INPUTS:
        if relative in {TARGET, Path("docs/spec/concept-graph.yaml")}:
            continue
        contents[str(relative)] = (ROOT / relative).read_text(encoding="utf-8")
    return contents


def build_prompt(
    content_sha256: str,
    input_hashes: dict[str, str],
    input_contents: dict[str, str],
) -> str:
    allowed = "\n".join(
        f"- `{path}`（SHA-256: `{digest}`）"
        for path, digest in input_hashes.items()
    )
    materials = "\n\n".join(
        f"===== BEGIN {path} =====\n{content}\n===== END {path} ====="
        for path, content in input_contents.items()
    )
    return f"""你是 Bridge Fn01 通用多 APK 需求、Concept、Technology Strategy 与详细设计冻结前的独立反方评审员。

这是严格只读任务。禁止调用工具、修改、创建或删除任何文件。完整源文件身份如下；提示末尾附有完整 Contract，以及从其余源文件确定性抽取的 Fn01 相关投影。只使用这些内嵌材料，不得访问其他路径，也不得访问用户禁止的历史材料：
{allowed}

被审主文档是 `{TARGET}`，其余文件是同一审批包。其中“独立评审附件”标记之间的内容不属于 Concept 语义，忽略该附件内容。脚本已计算 Contract 语义内容 SHA-256 为 `{content_sha256}`；每个输入文件 SHA-256 已列出。

用户最新方向是“不再参照历史上的硬编码；针对多 APK 安装/管理形成比较通用的方案”。评审目标是判断审批包是否足以交给 owner 冻结 Concept 和 Technology Strategy，并让 detailed design 随后冻结；不讨论具体实现 bug。请严格检查：
1. Concept 边界是否完整、路线无关，是否清楚区分语义唯一真源、物理承载和 host projection。
2. 是否真正删除 packageName、Activity、签名、APK 数量、设备路径、测试 corpus 等历史硬编码设计依赖；样例是否只作为测试数据。
3. install/query/list/restart/update/uninstall/reconcile 与 Job submit/get/cancel E2E 是否闭环；v1 base-only、primary-user、ordered-stop-on-failure 限制是否 typed fail closed。
4. MultiPackageJob 是否是独立 Concept，是否只编排 member 而不成为 package truth 第二写者；A committed/B failed/C not-started 能否分别给出独立事实。
5. 四组状态轴、P0-P6、uninstall tombstone publication、失败和重启恢复是否无冲突、无混代窗口。
6. canonicalDigest/projectionDigest 是否无环；journal recovery/terminal state 是否可直接持久表达。
7. R1-R6 是否是真实可区分路线，R2 recommended、R3 backup 的风险、证伪、reversibility 和 rollback 是否充分，是否提前推断 owner acceptance。
8. detailed design 的模块/API/locking/concurrency/persistence/security/error/observability/oracle 是否足够让实现者不再发明架构。
9. up/down/left/right、Fn01.C07、单真源文件职责、lifecycle 状态是否一致。
10. 现有 Action ID 是否未被重编号，新 Action 是否诚实保持待 route 接受后资格化。

只输出中文 Markdown，不写操作过程，不使用模糊赞美。必须严格使用以下结构：

# Fn01 通用多包冻结前独立评审
## 结论
只能单独写以下一个值：`建议批准`、`修改后批准`、`不建议批准`。只有当补充评审没有发现与 owner 已接受 Contract 不同的实质意见时，才写 `建议批准`。
## 阻断项
每项写 `[P0|P1]`、精确文件路径与标题/字段、冲突事实、为何阻断冻结、最小修改；没有则写 `- 无。`
## 非阻断项
每项写 `[P2]`、精确位置、改进理由；没有则写 `- 无。`
## 已验证的闭环
只列出经交叉核对成立的关键约束，不得因文件存在就判定成立。
## Owner 需要裁决的事项
只列 owner 必须接受/修改/拒绝的 Concept 与 Technology Strategy 内容。
## 评审边界
明确说明本结论只覆盖上述 hash 绑定的需求/Concept/Strategy/Design 候选，不是 Action、实现、设备或成熟度 PASS。

以下是唯一允许使用的评审材料：

{materials}
"""


def parse_verdict(review: str) -> str:
    review = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", review)
    section = re.search(
        r"^##[ \t]+结论[ \t]*\r?\n([\s\S]*?)(?=^##[ \t]|\Z)",
        review,
        re.MULTILINE,
    )
    if not section:
        raise SystemExit("Kimi 输出缺少合法且唯一的‘## 结论’值")
    found = {
        verdict
        for verdict in VERDICTS
        if re.search(rf"(?<![\w]){re.escape(verdict)}(?![\w])", section.group(1))
    }
    if len(found) != 1:
        raise SystemExit("Kimi 输出的‘## 结论’必须包含且只包含一个合法值")
    return found.pop()


def recover_review_from_alex_wire(
    review_dir_name: str,
) -> tuple[str, str] | None:
    """Recover the final text when the wrapper session is durable but stdout is empty."""
    sessions = Path.home() / ".kimi-code-alex" / "sessions"
    candidates = sorted(
        sessions.glob(
            f"wd_{review_dir_name}_*/session_*/agents/main/wire.jsonl"
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for wire in candidates:
        parts: list[str] = []
        for line in wire.read_text(encoding="utf-8").splitlines():
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
        recovered = "".join(parts).strip()
        if recovered:
            try:
                parse_verdict(recovered)
            except SystemExit:
                continue
            return recovered, str(wire)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--review-command",
        type=Path,
        default=DEFAULT_REVIEW_COMMAND,
        help="Kimi wrapper；默认使用隔离的 _kimi.alex",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="可选模型 alias；_kimi.alex 默认无需传入",
    )
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    review_command = args.review_command.expanduser().resolve()
    if not review_command.is_file():
        raise SystemExit(f"找不到 Kimi review command: {review_command}")

    missing = [str(path) for path in ALLOWED_INPUTS if not (ROOT / path).is_file()]
    if missing:
        raise SystemExit("缺少评审输入：" + ", ".join(missing))

    content_sha256 = sha256_bytes(semantic_target_bytes())
    input_hashes = {
        str(path): file_sha256(ROOT / path) for path in ALLOWED_INPUTS
    }
    input_contents = compact_review_contents()
    output = (
        ROOT
        / "var/evidence/concepts/Fn01/approval-reviews"
        / f"kimi-general-multipackage-freeze-{content_sha256[:12]}.md"
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
    kimi_version = (version_result.stdout or version_result.stderr).strip()
    with tempfile.TemporaryDirectory(prefix="bridge-kimi-review-") as review_dir:
        review_dir_name = Path(review_dir).name
        try:
            command = [str(review_command)]
            if args.model:
                command.extend(["--model", args.model])
            command.extend(
                [
                    "--prompt",
                    build_prompt(content_sha256, input_hashes, input_contents),
                    "--output-format",
                    "text",
                ]
            )
            result = subprocess.run(
                command,
                cwd=review_dir,
                text=True,
                capture_output=True,
                timeout=args.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise SystemExit(
                f"Kimi 评审在 {args.timeout} 秒后超时；未保存评审附件"
            ) from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise SystemExit(
            f"Kimi 评审失败，exit={result.returncode}: {detail[-1000:]}"
        )
    review = result.stdout.strip()
    review_transport = "wrapper_stdout"
    try:
        verdict = parse_verdict(review)
    except SystemExit as parse_error:
        recovered = recover_review_from_alex_wire(review_dir_name)
        if recovered is None:
            raise parse_error
        review, wire_path = recovered
        review_transport = f"isolated_session_wire:{wire_path}"
        verdict = parse_verdict(review)

    after_hashes = {
        str(path): file_sha256(ROOT / path) for path in ALLOWED_INPUTS
    }
    if after_hashes != input_hashes:
        raise SystemExit("Kimi 评审期间输入文件发生变化，拒绝保存失配评审")

    relative_output = output.relative_to(ROOT)
    metadata = {
        "review_type": "general_multipackage_concept_strategy_design_owner_review",
        "target_document": str(TARGET),
        "reviewed_content_sha256": content_sha256,
        "reviewer": "kimi_cli_headless",
        "reviewer_model": args.model or "_kimi.alex default (k3)",
        "review_command": str(review_command),
        "reviewer_version": kimi_version,
        "review_transport": review_transport,
        "review_artifact": str(relative_output),
        "verdict": verdict,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "allowed_input_sha256": input_hashes,
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
        prefix=".kimi-review.",
        delete=False,
    ) as stream:
        stream.write(artifact)
        temporary = Path(stream.name)
    temporary.replace(output)
    print(relative_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
