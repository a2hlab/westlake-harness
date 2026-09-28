#!/usr/bin/env python3
"""Seal the unified Bionic/Musl regression into JSON and a human report."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
from pathlib import Path
from typing import Dict, List


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fail(message: str) -> None:
    raise SystemExit(f"FAIL regression report: {message}")


def require_local(path: Path, project: Path) -> Path:
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(project)
    except ValueError:
        fail(f"path escaped project: {path}")
    if path.is_symlink():
        fail(f"symlink input rejected: {path}")
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--results", required=True, type=Path)
    args = parser.parse_args()

    project = args.project_root.resolve(strict=True)
    run_dir = require_local(args.run_dir, project)
    results_path = require_local(args.results, project)
    with results_path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        expected_header = [
            "id", "stage", "evidence_level", "status", "exit_code",
            "command", "log", "note",
        ]
        if reader.fieldnames != expected_header:
            fail(f"unexpected results header: {reader.fieldnames}")
        rows: List[Dict[str, str]] = list(reader)

    expected_ids = [f"R{n:02d}" for n in range(1, 21)] + [f"P{n:02d}" for n in range(1, 8)]
    if [row["id"] for row in rows] != expected_ids:
        fail("gate set/order drifted")
    for row in rows:
        if row["status"] == "PASS":
            if row["exit_code"] != "0" or row["log"] == "-":
                fail(f"PASS without zero exit/log: {row['id']}")
            log = require_local(project / row["log"], project)
            row["log_sha256"] = sha256(log)
        elif row["status"] == "FAIL":
            if row["exit_code"] in {"0", "-"} or row["log"] == "-":
                fail(f"FAIL without nonzero exit/log: {row['id']}")
            log = require_local(project / row["log"], project)
            row["log_sha256"] = sha256(log)
        elif row["status"] == "NOT_PROVEN":
            if row["id"].startswith("R"):
                fail(f"executable regression gate silently became NOT_PROVEN: {row['id']}")
            row["log_sha256"] = None
        else:
            fail(f"unknown gate status: {row['status']}")

    failures = [row for row in rows if row["status"] == "FAIL"]
    executed = [row for row in rows if row["id"].startswith("R")]
    not_proven = [row for row in rows if row["status"] == "NOT_PROVEN"]
    host_status = "PASS" if not failures and all(row["status"] == "PASS" for row in executed) else "FAIL"

    contract_path = require_local(run_dir / "CONTRACT_INPUTS.json", project)
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("schema") != "westlake-bionic-musl-contract-snapshot-v1":
        fail("unexpected contract snapshot schema")

    aperture_report_path = require_local(
        project / "adapter/framework/native-compat/tests/aperture_writer_fixture/REPORT.md",
        project,
    )
    aperture_report = aperture_report_path.read_text(encoding="utf-8")
    aperture_device_verified = (
        "aperture fixture device-verified: true" in aperture_report
        and "Product device-verified: false" in aperture_report
    )
    if not aperture_device_verified:
        fail("frozen standalone aperture device receipt is missing or downgraded")

    stage_matrix = {
        "S1_install_and_admission": {
            "status": "PARTIAL_STATIC_PROVEN" if host_status == "PASS" else "FAIL",
            "proven": "frozen identity, exact guest CFG closure, registry contracts, install-plan and namespace host behavior",
            "not_proven": "signed admission certificate, sealed-FD same-byte product consumer and target execution",
        },
        "S2_appspawn_main_thread": {
            "status": "AUDIT_ONLY_BUILD_PASS" if host_status == "PASS" else "FAIL",
            "proven": "audit-only process/thread state machine, fail-closed certificate mechanics and deterministic rejection of the unsafe provider profile",
            "not_proven": "current product closure, real guard publication, prepare order and production child execution",
        },
        "S3_unity_created_threads": {
            "status": "NOT_PROVEN",
            "proven": "none at product boundary",
            "not_proven": "namespace pthread provider, trampoline READY and all thread entry closure",
        },
        "S4_oh_musl_callbacks": {
            "status": "NOT_PROVEN",
            "proven": "none at product boundary",
            "not_proven": "typed callback guard, signal conversion/owner and nested restoration",
        },
        "S5_actual_inline_access": {
            "status": "PARTIAL_STATIC_PROVEN" if host_status == "PASS" else "FAIL",
            "proven": "CardWords CFG unknown=0, exact TP+0x28 read class, TLS layout, adler32, canonical libziparchive ErrorCodeString ownership, disabled aperture fixture and its frozen standalone 5EAB5 receipt",
            "not_proven": "product guard writer/issuer/callsite, complete six-entry target coverage and production-init Enforcing run",
        },
    }

    result = {
        "schema": "westlake-bionic-musl-unified-regression-v1",
        "run_dir": str(run_dir.relative_to(project)),
        "host": platform.platform(),
        "device_used": False,
        "standalone_aperture_fixture_device_verified": aperture_device_verified,
        "standalone_aperture_fixture_reexecuted_by_runner": False,
        "standalone_aperture_fixture_report": str(aperture_report_path.relative_to(project)),
        "apk_modified": False,
        "art_or_bcp_modified_by_regression": False,
        "external_source_tree_read_by_runner": False,
        "executed_gate_count": len(executed),
        "host_static_regression_status": host_status,
        "product_five_stage_status": "NOT_PROVEN",
        "device_verified": False,
        "stages": stage_matrix,
        "gates": rows,
        "not_proven_count": len(not_proven),
        "results_tsv": str(results_path.relative_to(project)),
        "results_tsv_sha256": sha256(results_path),
        "contract_inputs": str(contract_path.relative_to(project)),
        "contract_inputs_sha256": sha256(contract_path),
        "contract_aggregate_sha256": contract["aggregate_sha256"],
        "contract_file_count": contract["file_count"],
    }
    json_path = run_dir / "RESULT.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    proven = [
        "02c verifier 的 28 个允许资产已冻结到 02；四个 Unity 动态共享库字节身份一致。",
        "旧扫描结果严格保留为 3 个 CFG unknown 的历史红灯；当前 CFG-closed 证据为 0 unknown，且两次重放字节一致。",
        "五阶段机器注册表闭合：18 个错误码、27 个负例、153 个双故障优先级组合、38 个零指标、24 个状态方程和 17 个 REJECT 子例。",
        "install-plan、APK verifier sealed-FD transport、namespace loader、native-loader registry、initial/provider-closure fail-closed oracle、TLS layout、native-compat audit core、adler32、AOSP abort-message、libziparchive ErrorCodeString 唯一所有权与 disabled aperture writer 的 host/ARM64 target 回归均执行。",
        "独立 aperture fixture 已有冻结的 5EAB5 + SELinux Enforcing 成功回执；本 runner 只验证本地合同，没有重跑设备，也不把 fixture 回执升级为 product device_verified。",
    ]
    not_proven_lines = [row["note"] for row in not_proven]
    failed_lines = [f"{row['id']}: {row['note']}" for row in failures] or ["本轮确定性 host/static gate 无失败。"]
    next_lines = [
        "等待 provider/writer/production-cfg 并发变更收口后，只刷新一次本地 frozen generation 并重建同代 appspawn-x/compat/wrapper。",
        "补齐 recursive initial closure 与 binary prepare-order 证书，要求 pre_prepare_slot5_access_count == 0。",
        "以已验证的 standalone ARM64 guard fixture 为机制底座，实现 product issuer/appspawn callsite、namespace pthread bridge 与 typed callback/signal owner。",
        "最后才允许 5EAB5 production-init + SELinux Enforcing truly-cold Unity 首帧验收。",
    ]

    def bullets(items: List[str]) -> str:
        return "\n".join(f"- {item}" for item in items)

    report = f"""# Bionic/Musl 五阶段合并与统一回归报告

- Host/static regression: `{host_status}`
- Product five-stage status: `NOT_PROVEN`
- Device used: `false`
- Standalone aperture fixture device receipt: `true`（本 runner 未重跑；product=false）
- Executed gates: `{len(executed)}`
- 原始 APK / ART / BCP 修改: `false`

## Boundary

本轮只覆盖 Bionic/Musl 的安装认证、appspawn 主线程、namespace loader、线程状态机和内联访问静态/主机合同。全部输入来自 02 本地冻结副本；未读取 02c 或 16.12 作为运行输入，未操作设备。报告同时记录已冻结的 standalone aperture 真机回执，但该回执不是本 runner 产生，也不代表产品激活。

## Proven

{bullets(proven)}

## Not proven

{bullets(not_proven_lines)}

## Failed

{bullets(failed_lines)}

## Next evidence

{bullets(next_lines)}

## Evidence

- Machine result: `{json_path.relative_to(project)}`
- Gate ledger: `{results_path.relative_to(project)}`
- Frozen canonical contract: `{contract_path.relative_to(project)}` (`{contract['aggregate_sha256']}`)
- Per-gate logs: `{(run_dir / 'logs').relative_to(project)}/`

## Shim/stub/bypass inventory

本轮未新增 shim、stub 或 bypass。产品 native-compat core 仍是 audit-only；standalone fixture 虽有真实 writer 和真机回执，但 `product_activation=false`，不能冒充 Stage 2/5 产品实现。

## Memory / Skill / CI / Review updates

- Memory: 02c 历史 verifier 已冻结且由 SHA manifest 保护。
- CI: 单一入口为 `adapter/scripts/run_bionic_musl_regression.sh`。
- Review: 五阶段正本和机器注册表已纳入一致性回归；host PASS 不升级为 device_verified。
"""
    report_path = run_dir / "REPORT.md"
    report_path.write_text(report, encoding="utf-8")
    print(
        f"PASS report host_static={host_status} product=NOT_PROVEN "
        f"result={json_path.relative_to(project)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
