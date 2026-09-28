#!/usr/bin/env python3
"""独立核验批处理入口：扫描 READY_FOR_VERIFY 队列，批量拉起独立核验 agent。

队列来源：src/atoms 下各 Action 的 STATUS.yaml 的 code.status，
值为 READY_FOR_VERIFY / READY_FOR_INDEPENDENT_VERIFY 即入队（pyyaml 防御性解析；
同时兼容 src/atoms/FnXX/AYY/ 与 src/atoms/FnXX.AYY/ 两种目录布局）。

每个入队 Action 拉起一个独立的 _kimi.alex headless 会话（每个 Action 一个
独立 session，保证核验者与实现者上下文隔离），按 br-action-verify 工作流执行
host 侧核验，证据写入
var/evidence/atoms/<FnXX>/<AYY>/runs/<UTC 时间戳>-independent-host/。
kimi 调用方式（wrapper、--prompt/--output-format text、独立临时 cwd、
subprocess timeout、wire 恢复）照抄 src/tools/run_action_design_review.py。

幂等：若某 Action 的 runs/ 下已存在 verdict=PASS 且 implementation_sha256
与当前 IMPLEMENTATION.yaml 文件 SHA-256 一致的 manifest.json，跳过并标注
SKIP_ALREADY_VERIFIED。

超时/崩溃/无证据产物：为该 Action 写 BLOCKED_NO_ARTIFACT 记录并继续下一个，
任何单个失败不中断批次。

退出码：0 = 批次内无失败；2 = 存在执行失败（超时/崩溃/无 manifest/hash 漂移/
缺 handoff）或 verdict == FAIL。verdict 为 BLOCK / SPEC_GAP / SKIP 属于合法
核验结论，不算批次失败。
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


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VERIFY_COMMAND = Path("/Users/alexyang/.local/bin/_kimi.alex")
DEFAULT_TIMEOUT = 3600
DEFAULT_JOBS = 2
QUEUE_STATUSES = ("READY_FOR_VERIFY", "READY_FOR_INDEPENDENT_VERIFY")
VERIFICATION_CANDIDATES = ("verification.md", "veration.md", "ATOM_VALIDATION.md")
DESIGN_CANDIDATES = ("DESIGN_SPEC.md", "DESIGN.md")
VALID_VERDICTS = ("PASS", "FAIL", "BLOCK", "SPEC_GAP")
CONCEPT_RE = re.compile(r"^Fn\d{2}$")
FLAT_DIR_RE = re.compile(r"^(Fn\d{2})\.(A\d{2,})$")


def warn(message: str) -> None:
    print(f"WARNING: {message}", file=sys.stderr)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def run_timestamp(moment: datetime) -> str:
    return moment.strftime("%Y%m%dT%H%M%SZ")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def short(digest: str | None) -> str:
    return digest[:12] if digest else "-"


# ---------------------------------------------------------------- 队列扫描


def find_status_files() -> list[tuple[str, str, Path]]:
    """返回 (concept, action, STATUS.yaml 绝对路径)，兼容两种目录布局。"""
    base = ROOT / "src" / "atoms"
    found = []
    if not base.is_dir():
        return found
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        flat = FLAT_DIR_RE.match(child.name)
        if flat and (child / "STATUS.yaml").is_file():
            found.append((flat.group(1), flat.group(2), child / "STATUS.yaml"))
            continue
        if not CONCEPT_RE.match(child.name):
            continue
        for sub in sorted(child.iterdir()):
            if sub.is_dir() and (sub / "STATUS.yaml").is_file():
                found.append((child.name, sub.name, sub / "STATUS.yaml"))
    return found


def load_entry(concept: str, action: str, status_path: Path) -> dict | None:
    """解析一个 STATUS.yaml；code.status 不在队列状态内时返回 None。"""
    try:
        data = yaml.safe_load(status_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError) as error:
        warn(f"{status_path.relative_to(ROOT)} 解析失败（{error}），跳过")
        return None
    if not isinstance(data, dict):
        warn(f"{status_path.relative_to(ROOT)} 不是 mapping，跳过")
        return None
    code = data.get("code")
    code_status = code.get("status") if isinstance(code, dict) else None
    if code_status not in QUEUE_STATUSES:
        return None

    action_id = data.get("action_id")
    if not isinstance(action_id, str) or "." not in action_id:
        action_id = f"{concept}.{action}"
    verification = data.get("verification")
    review_status = (
        verification.get("review_status") if isinstance(verification, dict) else None
    )

    spec_dir = Path("docs/spec/atoms") / concept / action
    docs_dir = Path("docs/atoms") / concept / action
    evidence_dir = Path("var/evidence/atoms") / concept / action
    src_dir = status_path.parent.relative_to(ROOT)

    definition_file = spec_dir / "atom.yaml"
    verification_file = None
    for name in VERIFICATION_CANDIDATES:
        if (ROOT / spec_dir / name).is_file():
            verification_file = spec_dir / name
            break
    design_file = None
    for name in DESIGN_CANDIDATES:
        if (ROOT / spec_dir / name).is_file():
            design_file = spec_dir / name
            break
    implementation_file = src_dir / "IMPLEMENTATION.yaml"

    domains = [docs_dir, spec_dir, evidence_dir, src_dir]
    domain_count = sum(1 for relative in domains if (ROOT / relative).is_dir())

    entry = {
        "action_id": action_id,
        "concept": concept,
        "action": action,
        "code_status": code_status,
        "review_status": review_status if isinstance(review_status, str) else None,
        "src_dir": src_dir,
        "spec_dir": spec_dir,
        "docs_dir": docs_dir,
        "evidence_dir": evidence_dir,
        "runs_dir": evidence_dir / "runs",
        "domain_count": domain_count,
        "definition_file": definition_file if (ROOT / definition_file).is_file() else None,
        "verification_file": verification_file,
        "design_file": design_file,
        "implementation_file": (
            implementation_file if (ROOT / implementation_file).is_file() else None
        ),
    }
    entry["definition_sha256"] = (
        sha256(ROOT / entry["definition_file"]) if entry["definition_file"] else None
    )
    entry["verification_sha256"] = (
        sha256(ROOT / verification_file) if verification_file else None
    )
    entry["implementation_sha256"] = (
        sha256(ROOT / entry["implementation_file"])
        if entry["implementation_file"]
        else None
    )
    return entry


def scan_queue(concept_filter: str | None) -> list[dict]:
    queue = []
    for concept, action, status_path in find_status_files():
        if concept_filter and concept != concept_filter:
            continue
        entry = load_entry(concept, action, status_path)
        if entry is not None:
            queue.append(entry)
    queue.sort(key=lambda item: item["action_id"])
    return queue


# ---------------------------------------------------------------- 幂等检查


def already_verified(entry: dict) -> str | None:
    """存在绑定当前 implementation_sha256 的 PASS manifest 时返回其 run_id。"""
    current = entry["implementation_sha256"]
    if not current:
        return None
    runs_dir = ROOT / entry["runs_dir"]
    if not runs_dir.is_dir():
        return None
    for manifest in sorted(runs_dir.glob("*/manifest.json")):
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if (
            isinstance(data, dict)
            and data.get("verdict") == "PASS"
            and data.get("implementation_sha256") == current
        ):
            return manifest.parent.name
    return None


# ---------------------------------------------------------------- 核验 prompt


def build_prompt(entry: dict, run_id: str, validator_available: bool) -> str:
    aid = entry["action_id"]
    run_dir = ROOT / entry["runs_dir"] / run_id
    frozen_files = [
        ("definition", entry["definition_file"], entry["definition_sha256"]),
        ("verification oracle", entry["verification_file"], entry["verification_sha256"]),
        ("implementation handoff", entry["implementation_file"], entry["implementation_sha256"]),
    ]
    freeze_lines = []
    for label, relative, digest in frozen_files:
        if relative is None:
            freeze_lines.append(f"- {label}：文件缺失（这本身就是 SPEC_GAP 的候选原因）")
        else:
            freeze_lines.append(
                f"- {label}：`/opt/Bridge/{relative}`（参考 SHA-256 `{digest}`，必须自行复算核对）"
            )
    design_line = (
        f"- 设计文档：`/opt/Bridge/{entry['design_file']}`"
        if entry["design_file"]
        else "- 设计文档：缺失"
    )
    validator_line = (
        "11. 写完后运行 `python3 scripts/validate_evidence_run.py --root /opt/Bridge "
        f"--action-id {aid} --run-id {run_id}` 自检 manifest；不通过则修正后重跑。"
        if validator_available
        else "11. 写完后自行复核 manifest.json 字段与证据契约逐条对齐，且每个 evidence 文件真实存在且非空。"
    )
    return f"""你是 Bridge 项目（仓库根 /opt/Bridge，AOSP-on-OpenHarmony 适配层）的独立核验者。你不是实现者，也未参与 {aid} 的实现。你的任务是按照 br-action-verify 工作流，对 Action {aid} 做一次独立的 host 侧核验，并签发 PASS / FAIL / BLOCK / SPEC_GAP 之一。

先阅读 /opt/Bridge/.agents/skills/br-action-verify/SKILL.md 与其 references/evidence-contract.md，严格遵循证据契约。正典 manifest 样本（先精读，字段必须严格对齐）：/opt/Bridge/evidence/atoms/Fn01/A01/runs/20260728T001302Z-independent-linux/manifest.json。

纪律（逐条必须遵守）：
1. 冻结输入：读取下列文件，用 shasum -a 256 实际计算每个文件的 SHA-256 并与参考值核对；不一致说明 hash drift，停止执行并签发 FAIL（notes 写明 drift），不得继续核验：
{chr(10).join(freeze_lines)}
{design_line}
2. oracle（verification 文件中的正/负/失败用例）不明、缺失或不可独立执行 → verdict SPEC_GAP，写明缺失的 oracle，不得硬跑。
3. 在 host 范围内如实独立执行正向、负向、失败用例。不得参考或信任实现者的自测结论；可以复用实现者公开的测试 harness（如 IMPLEMENTATION.yaml 中的 test_commands / build_commands），但必须由你亲自执行、亲自观察结果并保存原始输出。设备（OpenHarmony target / D600）相关用例在本机无法执行时，相关部分标 BLOCK 并在 blocked_by/notes 写清缺的设备前提，不得伪造执行结果。
4. 你只允许写入你的 run 目录 {run_dir}。禁止修改任何产品源码、spec、docs、既有 evidence、STATUS.yaml 或其他 Action 的文件。
5. run_id 固定为 {run_id}，证据目录固定为 {run_dir}，结构：
   - manifest.json：字段严格对齐正典样本（schema_version/action_id/run_id/verdict/verifier/implementer/definition_sha256/verification_sha256/implementation_sha256/build_identity/environment/started_at/finished_at/positive_cases/negative_cases/failure_cases/blocked_by/notes）；每个 case 的 evidence 用相对 run 目录的 raw/... 路径，且文件必须真实存在且非空。
   - VERDICT.md：中文 verdict 说明（结论、身份、已证明、范围限制）。
   - commands.txt：编号列出你实际执行过的全部命令。
   - raw/：全部原始日志与输出。
6. verifier 写 "kimi_independent_verify_batch"；implementer 从 IMPLEMENTATION.yaml 的 implementer 字段如实读取；两者必须不同，否则 PASS 无效。
7. manifest 中的 definition_sha256 / verification_sha256 / implementation_sha256 必须等于你实测的三个文件 SHA-256；verdict 与 implementation_sha256 绑定。
8. environment 如实写你实际使用的 host 环境（如 macOS/arm64 本机，或你实际使用的容器镜像身份）；build_identity 从 IMPLEMENTATION.yaml（source_commit、build_receipts）如实概括。
9. scope 明确 host-only：notes 必须写明本 verdict 只覆盖 host 侧语义，不外推 OpenHarmony target/device。
{validator_line}

最后，在回复末尾单独一行输出最终结论，格式严格为：VERDICT: <PASS|FAIL|BLOCK|SPEC_GAP>
"""


# ---------------------------------------------------------------- kimi 调用与恢复


def recover_output_from_alex_wire(work_dir_name: str) -> str | None:
    """wrapper session 仍在但 stdout 为空时，从隔离 session 的 wire.jsonl 恢复最终文本。"""
    sessions = Path.home() / ".kimi-code-alex" / "sessions"
    candidates = sorted(
        sessions.glob(f"wd_{work_dir_name}_*/session_*/agents/main/wire.jsonl"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for wire in candidates:
        parts: list[str] = []
        try:
            lines = wire.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
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
            return recovered
    return None


def extract_verdict(text: str) -> str | None:
    found = re.findall(r"^VERDICT:[ \t]*(PASS|FAIL|BLOCK|SPEC_GAP)\b", text, re.MULTILINE)
    return found[-1] if found else None


def read_manifest_verdict(run_dir: Path) -> str | None:
    manifest = run_dir / "manifest.json"
    if not manifest.is_file():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    verdict = data.get("verdict") if isinstance(data, dict) else None
    return verdict if verdict in VALID_VERDICTS else None


def write_blocked_record(entry: dict, run_id: str, reason: str, started: datetime) -> Path:
    """核验 agent 未产出有效证据时，消除『无产物的等待』。"""
    run_dir = ROOT / entry["runs_dir"] / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    output = run_dir / "BLOCKED_NO_ARTIFACT.md"
    metadata = {
        "record_type": "independent_verify_batch_blocked",
        "action_id": entry["action_id"],
        "run_id": run_id,
        "verdict": "BLOCKED_NO_ARTIFACT",
        "verifier": "run_independent_verify_batch.py",
        "implementation_sha256": entry["implementation_sha256"],
        "failure_reason": reason,
        "started_at": started.isoformat(),
        "recorded_at": utc_now().isoformat(),
    }
    body = (
        f"# {entry['action_id']} 独立核验 BLOCKED_NO_ARTIFACT\n\n"
        "独立核验 agent 未能产出有效证据（manifest.json 缺失或不可解析），"
        "本记录用于消除『无产物的等待』。\n\n"
        f"- run_id：`{run_id}`\n"
        f"- implementation_sha256：`{entry['implementation_sha256']}`\n"
        f"- 失败原因：{reason}\n\n"
        "本记录不是 PASS/FAIL/BLOCK/SPEC_GAP verdict；该 Action 仍需重新独立核验。\n"
    )
    artifact = (
        "---\n"
        + yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False)
        + "---\n\n"
        + body
    )
    output.write_text(artifact, encoding="utf-8")
    return output


# ---------------------------------------------------------------- 单个 Action 核验


def verify_one(
    entry: dict,
    verify_command: Path,
    model: str | None,
    timeout: int,
    validator_available: bool,
) -> dict:
    aid = entry["action_id"]
    started = utc_now()
    result = {
        "action_id": aid,
        "started_at": started.isoformat(),
        "ok": False,
        "verdict": None,
        "skipped": False,
        "reason": None,
        "run_dir": None,
        "transport": None,
    }

    skip_run = already_verified(entry)
    if skip_run is not None:
        result.update(
            ok=True,
            skipped=True,
            verdict="SKIP_ALREADY_VERIFIED",
            reason=f"已存在绑定当前 implementation_sha256 的 PASS manifest（runs/{skip_run}）",
            run_dir=str(entry["runs_dir"] / skip_run),
        )
        return result

    if entry["implementation_file"] is None:
        result["reason"] = "缺少 IMPLEMENTATION.yaml，无法绑定 implementation hash"
        return result

    run_id = f"{run_timestamp(started)}-independent-host"
    run_dir = ROOT / entry["runs_dir"] / run_id
    result["run_dir"] = str(entry["runs_dir"] / run_id)
    prompt = build_prompt(entry, run_id, validator_available)

    safe_name = aid.lower().replace(".", "-")
    output_text = ""
    transport = "wrapper_stdout"
    failure = None
    with tempfile.TemporaryDirectory(
        prefix=f"bridge-kimi-verify-{safe_name}-"
    ) as work_dir:
        work_dir_name = Path(work_dir).name
        command = [str(verify_command)]
        if model:
            command.extend(["--model", model])
        # --prompt 与 --yolo/--auto 互斥；headless -p 模式本身即按
        # auto permission policy 处理工具调用（官方文档确认），无需额外 flag。
        command.extend(["--prompt", prompt, "--output-format", "text"])
        try:
            completed = subprocess.run(
                command,
                cwd=work_dir,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
            output_text = (completed.stdout or "").strip()
            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout or "").strip()
                failure = f"kimi exit={completed.returncode}: {detail[-500:]}"
        except subprocess.TimeoutExpired:
            failure = f"核验在 {timeout} 秒后超时"
        except OSError as error:
            failure = f"kimi 调用失败：{error}"

        if not output_text:
            recovered = recover_output_from_alex_wire(work_dir_name)
            if recovered:
                output_text = recovered
                transport = "isolated_session_wire"

    result["transport"] = transport

    # 输入 hash 漂移检查：核验期间冻结文件被改动则拒绝采信。
    drift = []
    for key in ("definition_file", "verification_file", "implementation_file"):
        relative = entry[key]
        if relative is None:
            continue
        current = sha256(ROOT / relative)
        if current != entry[f"{key.replace('_file', '_sha256')}"]:
            drift.append(str(relative))
    if drift:
        failure = (failure + "；" if failure else "") + "核验期间冻结文件变化：" + ", ".join(drift)

    verdict = read_manifest_verdict(run_dir)
    if verdict is None and failure is None:
        text_verdict = extract_verdict(output_text)
        failure = (
            f"agent 报告 VERDICT: {text_verdict} 但未写出有效 manifest.json"
            if text_verdict
            else "agent 未写出有效 manifest.json，输出中也无 VERDICT 行"
        )

    if verdict is not None and failure is None:
        result.update(ok=True, verdict=verdict)
        return result

    record = write_blocked_record(entry, run_id, failure or "未知失败", started)
    result["reason"] = failure
    result["blocked_record"] = str(record.relative_to(ROOT))
    if verdict is not None:
        # 有 manifest 但伴随 drift：verdict 只作参考，仍判失败。
        result["verdict"] = verdict
    return result


# ---------------------------------------------------------------- 报告


def write_batch_report(batch_id: str, queue: list[dict], results: list[dict]) -> Path:
    report = ROOT / "evidence" / "runs" / f"verify-batch-{batch_id}.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    failures = [
        r for r in results if not r["ok"] or (r["verdict"] == "FAIL" and not r["skipped"])
    ]
    lines = [
        f"# 独立核验批处理报告 {batch_id}",
        "",
        f"- 生成时间：{utc_now().isoformat()}",
        f"- 队列大小：{len(queue)}（code.status ∈ READY_FOR_VERIFY / READY_FOR_INDEPENDENT_VERIFY）",
        f"- 执行结果：{len(results) - len(failures)} 个完成，{len(failures)} 个失败",
        "- 退出码语义：0 = 无失败；2 = 存在执行失败（超时/崩溃/无 manifest/hash 漂移/缺 handoff）或 verdict == FAIL；BLOCK / SPEC_GAP / SKIP_ALREADY_VERIFIED 为合法结论，不算失败。",
        "",
        "## 逐 Action 结果",
        "",
        "| Action | 结果 | 耗时 | 证据路径 | 说明 |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        verdict = r["verdict"] or ("SKIP_ALREADY_VERIFIED" if r["skipped"] else "BLOCKED_NO_ARTIFACT")
        duration = "-"
        if r.get("finished_at") and r.get("started_at"):
            start = datetime.fromisoformat(r["started_at"])
            finish = datetime.fromisoformat(r["finished_at"])
            duration = f"{(finish - start).total_seconds():.0f}s"
        evidence = r.get("run_dir") or "-"
        note = r.get("reason") or ""
        if r.get("transport") and r["transport"] != "wrapper_stdout":
            note = (note + "；" if note else "") + f"transport={r['transport']}"
        lines.append(f"| {r['action_id']} | {verdict} | {duration} | {evidence} | {note} |")
    lines += ["", "## 失败原因汇总", ""]
    if failures:
        for r in failures:
            reason = r.get("reason") or "verdict == FAIL（详见其 run 目录证据）"
            lines.append(f"- {r['action_id']}：{reason}")
    else:
        lines.append("- 无。")
    lines += [
        "",
        "## 边界说明",
        "",
        "- 本批次只触发并汇总独立核验；每个 verdict 由独立核验 agent 签发并与其 run 目录证据绑定，本报告不构成 verdict 本身。",
        "- host 侧 verdict 不外推 OpenHarmony target/device。",
        "",
    ]
    report.write_text("\n".join(lines), encoding="utf-8")
    return report


def print_queue(queue: list[dict], planned: dict[str, str]) -> None:
    print(f"核验队列（{len(queue)} 个 Action）：")
    header = f"{'ACTION':<12} {'STATUS':<32} {'IMPL':<14} {'VERIF':<14} {'四域':<5} 计划"
    print(header)
    print("-" * len(header))
    for entry in queue:
        print(
            f"{entry['action_id']:<12} {entry['code_status']:<32} "
            f"{short(entry['implementation_sha256']):<14} "
            f"{short(entry['verification_sha256']):<14} "
            f"{entry['domain_count']}/4  {planned[entry['action_id']]}"
        )
        if entry["review_status"]:
            print(f"{'':<12} review_status={entry['review_status']}")


# ---------------------------------------------------------------- main


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--concept", default=None, help="可选 FnXX 过滤，如 Fn01")
    parser.add_argument("--jobs", type=int, default=DEFAULT_JOBS, help="并发核验数")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="单个核验超时秒数")
    parser.add_argument("--model", default=None, help="可选模型 alias；_kimi.alex 默认无需传入")
    parser.add_argument(
        "--verify-command", type=Path, default=DEFAULT_VERIFY_COMMAND,
        help="Kimi wrapper；默认使用隔离的 _kimi.alex",
    )
    parser.add_argument("--dry-run", action="store_true", help="只打印队列与计划，不拉起 agent")
    args = parser.parse_args()

    if args.concept and not CONCEPT_RE.match(args.concept):
        raise SystemExit(f"--concept 必须是 FnXX 形式，收到：{args.concept}")
    if args.jobs < 1:
        raise SystemExit("--jobs 必须 >= 1")

    queue = scan_queue(args.concept)
    if not queue:
        print("NO-OP：队列为空（没有 code.status 为 READY_FOR_VERIFY / "
              "READY_FOR_INDEPENDENT_VERIFY 的 Action）。")
        return 0

    batch_id = run_timestamp(utc_now())
    planned = {}
    for entry in queue:
        skip_run = already_verified(entry)
        if skip_run is not None:
            planned[entry["action_id"]] = (
                f"SKIP_ALREADY_VERIFIED（runs/{skip_run} 已绑定当前 impl hash 的 PASS）"
            )
        elif entry["implementation_file"] is None:
            planned[entry["action_id"]] = "NOT_EXECUTABLE（缺少 IMPLEMENTATION.yaml）"
        else:
            planned[entry["action_id"]] = (
                f"VERIFY -> {entry['runs_dir']}/<UTC 时间戳>-independent-host"
            )
    print_queue(queue, planned)

    if args.dry_run:
        print("\nDRY-RUN：不拉起任何核验 agent。")
        return 0

    verify_command = args.verify_command.expanduser().resolve()
    if not verify_command.is_file():
        raise SystemExit(f"找不到 Kimi verify command: {verify_command}")

    validator_available = (ROOT / "scripts" / "validate_evidence_run.py").is_file()
    if not validator_available:
        warn("scripts/validate_evidence_run.py 不存在，核验 agent 将自行复核 manifest")

    def run_entry(entry: dict) -> dict:
        result = verify_one(
            entry, verify_command, args.model, args.timeout, validator_available
        )
        result["finished_at"] = utc_now().isoformat()
        return result

    print(f"\n开始批量核验（jobs={args.jobs}, timeout={args.timeout}s, batch={batch_id}）")
    results = []
    if args.jobs == 1 or len(queue) == 1:
        for entry in queue:
            results.append(run_entry(entry))
    else:
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            for result in pool.map(run_entry, queue):
                results.append(result)

    failures = []
    for r in results:
        verdict = r["verdict"] or ("SKIP_ALREADY_VERIFIED" if r["skipped"] else "BLOCKED_NO_ARTIFACT")
        if r["ok"]:
            print(f"[OK] {r['action_id']}: {verdict} -> {r.get('run_dir')}")
        else:
            failures.append(r)
            print(f"[FAILED] {r['action_id']}: {r['reason']}", file=sys.stderr)
            if r.get("blocked_record"):
                print(f"  记录: {r['blocked_record']}", file=sys.stderr)
        if r["verdict"] == "FAIL" and r["ok"]:
            failures.append(r)

    report = write_batch_report(batch_id, queue, results)
    print(f"\n批报告: {report.relative_to(ROOT)}")
    print(f"汇总：队列 {len(queue)}，完成 {len(results) - len(failures)}，失败 {len(failures)}")
    if failures:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
