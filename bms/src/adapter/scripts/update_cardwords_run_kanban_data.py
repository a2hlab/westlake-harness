#!/usr/bin/env python3
"""Append one CardWords staircase run to representative atom-local raw facts.

The 14 project staircase floors do not have a one-to-one identity with the
global atom library.  This producer therefore uses one acceptance-aligned
canonical atom per project floor.  It never writes dashboard/UI fields and it
never treats a later floor that was not reached as an implementation failure.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path("/opt/21.Game/02.unity.cardwords")
ADAPTER_ROOT = PROJECT_ROOT / "adapter"
LOCAL_ATOM_ROOT = ADAPTER_ROOT / "research/atoms"
CANONICAL_ATOM_ROOT = Path(
    "/opt/15.WestLake/03new_Requirement/02.AtomFunctionGit/atoms"
)

FLOOR_ATOMS = {
    "L01": "L01.A01",  # public baseline / device evidence commands
    "L02": "L02.A03",  # APK manifest parse
    "L03": "L02.A02",  # installed package query result-state
    "L04": "L03.A03",  # AppSpawnX socket and client addressing
    "L05": "L04.A01",  # Activity create
    "L06": "L03.A12",  # APK native SO load
    "L07": "L03.A11",  # JNI native-symbol resolution
    "L08": "L03.A14",  # Bionic/Musl libc boundary
    "L09": "L05.A03",  # window session add
    "L10": "L05.A01",  # first frame visible
    "L11": "L06.A01",  # input click dispatch
    "L12": "L11.A09",  # media/image decoder compatibility
    "L13": "L13.A01",  # process alive after launch
    "L14": "L14.A10",  # manual/test launch is not production
}


class NoAliasSafeDumper(yaml.SafeDumper):
    """Safe YAML dumper that never emits protocol-forbidden anchors/aliases."""

    def ignore_aliases(self, data: Any) -> bool:
        return True


def fail(message: str) -> "NoReturn":
    raise SystemExit(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def find_canonical(atom_id: str) -> tuple[Path, dict[str, Any], str]:
    floor, _ = atom_id.split(".", 1)
    matches: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted((CANONICAL_ATOM_ROOT / floor).glob("A*/atom.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("atom_id") == atom_id:
            matches.append((path, data))
    if len(matches) != 1:
        fail(f"expected one canonical definition for {atom_id}, found {len(matches)}")
    path, data = matches[0]
    return path, data, sha256_file(path)


def criterion_identity(canonical: dict[str, Any], index: int) -> tuple[str, str]:
    acceptance = canonical.get("acceptance")
    if not isinstance(acceptance, list) or index >= len(acceptance):
        fail(f"missing acceptance/{index} for {canonical.get('atom_id')}")
    return f"/acceptance/{index}", canonical_json_sha256(acceptance[index])


def read_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        fail(f"raw fact file does not start with frontmatter: {path}")
    end = text.find("\n---", 4)
    if end < 0:
        fail(f"raw fact file has no closing frontmatter: {path}")
    data = yaml.safe_load(text[4:end])
    if not isinstance(data, dict):
        fail(f"raw fact frontmatter is not a mapping: {path}")
    return data


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def render_frontmatter(data: dict[str, Any]) -> str:
    body = yaml.dump(
        data,
        Dumper=NoAliasSafeDumper,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=120,
    )
    return f"---\n{body}---\n"


def evidence(
    run_dir: Path, filename: str, kind: str, summary: str
) -> dict[str, str]:
    path = run_dir / filename
    if not path.is_file() or path.is_symlink():
        fail(f"missing or unsafe evidence: {path}")
    return {
        "kind": kind,
        "path": str(path.relative_to(PROJECT_ROOT)),
        "sha256": sha256_file(path),
        "summary": summary,
    }


def fact_base(atom_id: str, canonical: dict[str, Any], index: int) -> dict[str, str]:
    criterion_ref, criterion_sha256 = criterion_identity(canonical, index)
    return {
        "criterion_ref": criterion_ref,
        "criterion_sha256": criterion_sha256,
    }


def main() -> int:
    if len(sys.argv) != 2:
        fail(f"usage: {Path(sys.argv[0]).name} RUN_DIR")
    run_dir = Path(sys.argv[1]).resolve()
    try:
        run_dir.relative_to(ADAPTER_ROOT / "research/runs")
    except ValueError:
        fail(f"run directory escapes canonical adapter run root: {run_dir}")
    run_data_path = run_dir / "RUN_DATA.json"
    run = json.loads(run_data_path.read_text(encoding="utf-8"))
    if run.get("schema") != "westlake.cardwords.staircase-run.v1":
        fail("unsupported RUN_DATA schema")
    if run.get("scope") != str(PROJECT_ROOT):
        fail("RUN_DATA scope is not the 02 project")

    run_id = str(run["run_id"])
    fact_suffix = re.sub(r"[^a-z0-9.-]+", "-", run_id.lower()).strip("-.")
    observed_at = str(run["host_ended_at"])
    if re.fullmatch(r".*[+-][0-9]{4}", observed_at):
        observed_at = observed_at[:-2] + ":" + observed_at[-2:]
    source_revision = str(run["source_revision"])
    package_sha256 = str(run["canonical_apk_sha256"])
    device_serial = str(run["device_serial"])
    boot_id = str(run["boot_id"])
    cold_start = str(run["cold_start"])
    build_generation = f"{run['generation']}@{boot_id}"
    launch = run["launch"]

    device_context = {
        "mode": "canonical_device",
        "source_revision": source_revision,
        "build_generation": build_generation,
        "package_sha256": package_sha256,
        "device_serial": device_serial,
        "boot_id": boot_id,
        "cold_start": cold_start,
        "command": str(launch["command"]),
        "exit_code": int(launch["exit_code"]),
        "started_at": str(run["host_started_at"]),
        "ended_at": observed_at,
    }
    for key in ("started_at",):
        value = device_context[key]
        if re.fullmatch(r".*[+-][0-9]{4}", value):
            device_context[key] = value[:-2] + ":" + value[-2:]
    artifact_context = {
        "mode": "artifact_readback",
        "source_revision": source_revision,
        "subject_artifact_sha256": package_sha256,
        "package_sha256": package_sha256,
        "command": "pinned apkanalyzer manifest print + apksigner verify + unzip entry inventory",
        "exit_code": 0,
        "started_at": device_context["started_at"],
        "ended_at": observed_at,
    }

    run_receipt = evidence(
        run_dir,
        "RUN_DATA.json",
        "device_receipt",
        "同一 run_id 的 L01-L14 实际执行记录、首个失败层、设备/boot/APK 身份与后续未触达边界。",
    )
    hilog_receipt = evidence(
        run_dir,
        "hilog_window.txt",
        "log",
        "从启动前 monotonic anchor 起截取的原始 hilog 窗口，含 AppMS 路由、AppSpawnX socket ENOENT 与 pid=0。",
    )
    manifest_receipt = evidence(
        run_dir,
        "apk_manifest.xml",
        "manifest",
        "固定 apkanalyzer 从 canonical APK 解码的 AndroidManifest.xml，包含原 package 与 UnityPlayerActivity。",
    )
    package_receipt = evidence(
        run_dir,
        "package_dump.json",
        "device_receipt",
        "D600-A BMS 对已安装原始包的 package、codePath、ABI、nativeLibraryPath 与 main component 回读。",
    )
    screen_receipt = evidence(
        run_dir,
        "screen.jpeg",
        "screenshot",
        "启动观察窗后的设备截图；没有存活 CardWords PID，不能作为游戏首帧证据。",
    )

    floor_records = {item["floor_id"]: item for item in run["floor_records"]}
    planned: dict[str, dict[str, list[dict[str, Any]]]] = {
        atom_id: {"proven": [], "not_proven": [], "failed": [], "next_evidence": []}
        for atom_id in FLOOR_ATOMS.values()
    }
    canonical_cache: dict[str, tuple[Path, dict[str, Any], str]] = {
        atom_id: find_canonical(atom_id) for atom_id in FLOOR_ATOMS.values()
    }

    def add_proven(
        atom_id: str,
        index: int,
        fact_id: str,
        statement: str,
        context: dict[str, Any],
        receipts: list[dict[str, str]],
        level: str = "device_verified",
    ) -> None:
        canonical = canonical_cache[atom_id][1]
        planned[atom_id]["proven"].append(
            {
                "fact_id": fact_id,
                "route_id": "A",
                **fact_base(atom_id, canonical, index),
                "statement": statement,
                "observed_at": observed_at,
                "declared_evidence_level": level,
                "context": context,
                "evidence": receipts,
            }
        )

    def add_not_proven(
        atom_id: str,
        index: int,
        fact_id: str,
        statement: str,
        reason: str,
        missing_evidence: list[str],
        receipts: list[dict[str, str]] | None = None,
    ) -> None:
        canonical = canonical_cache[atom_id][1]
        planned[atom_id]["not_proven"].append(
            {
                "fact_id": fact_id,
                "route_id": "A",
                **fact_base(atom_id, canonical, index),
                "statement": statement,
                "observed_at": observed_at,
                "reason": reason,
                "missing_evidence": missing_evidence,
                "context": device_context,
                "evidence": receipts or [run_receipt],
            }
        )

    def add_failed(
        atom_id: str,
        index: int,
        fact_id: str,
        statement: str,
        expected: str,
        observed: str,
        receipts: list[dict[str, str]],
    ) -> None:
        canonical = canonical_cache[atom_id][1]
        planned[atom_id]["failed"].append(
            {
                "fact_id": fact_id,
                "route_id": "A",
                **fact_base(atom_id, canonical, index),
                "statement": statement,
                "expected": expected,
                "observed": observed,
                "observed_at": observed_at,
                "declared_evidence_level": "device_verified",
                "context": device_context,
                "evidence": receipts,
            }
        )

    # L01: the run proves target/commands, while current adapter version/deploy
    # artifacts remain deliberately not proven on this adapter-free boot.
    add_proven(
        "L01.A01",
        2,
        f"p-{fact_suffix}-l01a01-device-command-record",
        "本次原始 CardWords 运行记录了 D600-A serial、boot_id、canonical APK hash、精确 aa 启动命令、返回码和证据文件哈希。",
        device_context,
        [run_receipt],
    )
    add_not_proven(
        "L01.A01",
        0,
        f"np-{fact_suffix}-l01a01-public-version",
        "本次 current-boot baseline 不能证明可发布的 adapter public version 已命名。",
        "设备七个固定 adapter/runtime 路径均缺失，run generation 只是现场身份标签，不是发布版本。",
        ["带版本号、source manifest 与 build generation 的可部署 adapter 发行凭据"],
    )
    add_not_proven(
        "L01.A01",
        1,
        f"np-{fact_suffix}-l01a01-build-deploy-scope",
        "本次运行列出了固定路径缺失，但不能证明 build artifacts 与部署范围已闭合。",
        "当前 boot 没有同代 adapter payload/provider manifest，也未执行部署。",
        ["同代 ARM64 artifact manifest、provider closure 与 scoped deploy receipt"],
    )

    # L02: exact static APK manifest inspection.
    for index, statement in (
        (0, "固定 apkanalyzer 从 canonical APK AndroidManifest.xml 提取出 package com.CardWordsStudio.CardWords。"),
        (1, "同一 manifest 输出枚举出主 Activity com.unity3d.player.UnityPlayerActivity 及其 MAIN/LAUNCHER 声明。"),
    ):
        add_proven(
            "L02.A03",
            index,
            f"p-{fact_suffix}-l02a03-manifest-{index}",
            statement,
            artifact_context,
            [manifest_receipt],
            "artifact_verified",
        )

    # L03: this is an existing installed result-state query, not an install transaction.
    for index, statement in (
        (0, "D600-A BMS 查询返回 canonical CardWords package identity、version 与 arm64-v8a code path。"),
        (1, "D600-A BMS 查询返回主组件 com.unity3d.player.UnityPlayerActivity 和 nativeLibraryPath。"),
    ):
        add_proven(
            "L02.A02",
            index,
            f"p-{fact_suffix}-l02a02-package-query-{index}",
            statement,
            device_context,
            [package_receipt, run_receipt],
        )

    # L04: explicit production socket failure.
    add_failed(
        "L03.A03",
        0,
        f"f-{fact_suffix}-l03a03-socket-absent",
        "本次真实启动到达 Android appspawn 路由，但 AppSpawnX service socket 不存在。",
        "production AppSpawnX service name 与 /dev/unix/socket/AppSpawnX endpoint 已配置并可连接。",
        "APPSPAWN_CLIENT 四次报告 Failed to connect /dev/unix/socket/AppSpawnX error: 2。",
        [run_receipt, hilog_receipt],
    )
    add_failed(
        "L03.A03",
        1,
        f"f-{fact_suffix}-l03a03-client-address",
        "Spawn client 已选择 Android app spawner，但没有取得 child pid。",
        "spawn client 将 canonical package 请求送达 Android app spawner 并返回非零 child pid。",
        "AppMS 最终记录 spawn new app fail、errCode 0d000010、pid:0 与 PROCESS_START_FAILED。",
        [run_receipt, hilog_receipt],
    )

    blocked_reason = "同一次运行在 L04 因 AppSpawnX socket ENOENT、pid=0 停止；该原子功能未执行。"
    blocked_specs = {
        "L04.A01": [
            (0, "本次运行不能证明 Activity onCreate 已发生。", "CardWords child 的 onCreate 原始日志"),
            (1, "本次运行不能证明 setContentView 可无 fatal crash 执行。", "Activity child 的 setContentView 与存活证据"),
        ],
        "L03.A12": [
            (0, "本次运行没有到达 APK native library path。", "同代 child 的 System.loadLibrary、maps 与 exact-hash DSO readback"),
            (1, "本次运行没有执行真实 dlopen，因此不能评价依赖/ABI/symbol 诊断。", "受控真实 dlopen 正负例及可区分错误"),
        ],
        "L03.A11": [
            (0, "本次运行没有到达 Java-to-native symbol resolution。", "UnityPlayer JNI symbol 命中与调用证据"),
            (1, "本次运行未产生 UnsatisfiedLinkError 或 dlsym 结果。", "真实缺 symbol 负例与对应 replacement atom"),
        ],
        "L03.A14": [
            (0, "本次运行没有 app-scoped libc/libm/libdl bridge observation。", "CardWords child 的边界符号清单与 provider trace"),
            (1, "本次运行不能证明 ABI 不兼容已被 guard。", "同代 child 的跨 ABI 正负例与 guard 诊断"),
        ],
        "L05.A03": [
            (0, "本次运行没有到达 Android window token/layout 到 OH surface target。", "Activity/window/session/render trace 与截图前置"),
            (1, "本次运行没有执行 invalid-window-token controlled probe。", "invalid token 的 Android-compatible failure trace"),
        ],
        "L05.A01": [
            (0, "本次运行没有 CardWords 首帧；截图仅记录当时设备屏幕。", "onResume、window/render trace 与含预期游戏内容的截图"),
            (1, "本次运行没有 launch-to-first-frame timestamp。", "同一 device/build baseline 的首帧时间戳与截图对"),
        ],
        "L06.A01": [
            (0, "本次运行没有可点击的 CardWords UI，未执行 click listener。", "首帧后真实点击及 listener 运行证据"),
            (1, "本次运行没有 app click action log。", "输入命令、dispatch/ACK 与 app 状态变化日志"),
        ],
        "L11.A09": [
            (0, "本次运行没有到达 ImageDecoder native calls。", "CardWords 所需 image decode 调用与 symbol/provider trace"),
            (1, "本次运行没有执行 unsupported decode negative。", "不支持特性的显式失败而非 fake success"),
        ],
    }
    for atom_id, items in blocked_specs.items():
        floor_id = next(key for key, value in FLOOR_ATOMS.items() if value == atom_id)
        if floor_records[floor_id]["observation"] != "not_reached_in_this_run":
            fail(f"refusing generic not-reached facts for reached floor {floor_id}")
        for index, statement, missing in items:
            receipts = [run_receipt]
            if atom_id == "L05.A01":
                receipts = [run_receipt, screen_receipt]
            add_not_proven(
                atom_id,
                index,
                f"np-{fact_suffix}-{atom_id.lower().replace('.', '')}-{index}",
                statement,
                blocked_reason,
                [missing],
                receipts,
            )

    # L13 gets a real E2E failure, not merely a later-floor placeholder.
    add_failed(
        "L13.A01",
        0,
        f"f-{fact_suffix}-l13a01-no-pid",
        "aa 接受启动请求后，配置的 8 秒观察窗结束时 CardWords pid 仍为空。",
        "canonical package pid 在整个配置观察窗内保持存在。",
        "AppSpawnX socket ENOENT 导致 child pid=0；8 秒后 pidof 仍为空。",
        [run_receipt, hilog_receipt],
    )
    add_not_proven(
        "L13.A01",
        1,
        f"np-{fact_suffix}-l13a01-crash-loop",
        "本次没有 child，不能证明应用无 fatal crash 或 restart loop。",
        "启动在进程出生前失败；absence of crash 不能替代运行稳定性。",
        ["存活 child 的五分钟 crash/restart 观察与视频"],
    )

    # L14: the run capsule explicitly labels this manual request and rejects
    # aa request success as production capability.
    for index, statement in (
        (0, "运行凭据将 aa 手工启动请求、AppMS 路由和缺失的 production AppSpawnX socket 分开记录。"),
        (1, "aa 返回 start ability successfully 只作为 request acknowledgement；pid=0 时没有被计作 production app launch。"),
    ):
        add_proven(
            "L14.A10",
            index,
            f"p-{fact_suffix}-l14a10-launch-label-{index}",
            statement,
            device_context,
            [run_receipt, hilog_receipt],
        )

    changed: list[str] = []
    for atom_id, additions in planned.items():
        canonical_path, canonical, canonical_sha256 = canonical_cache[atom_id]
        floor, atom = atom_id.split(".", 1)
        atom_dir = LOCAL_ATOM_ROOT / floor / atom
        atom_dir.mkdir(parents=True, exist_ok=True)
        local_spec_path = atom_dir / "atom.yaml"
        if not local_spec_path.exists():
            local_spec = {
                "schema_version": 1,
                "atom_id": atom_id,
                "title": canonical.get("title", atom_id),
                "canonical_root": f"research/atoms/{floor}/{atom}",
                "upstream_spec": str(canonical_path),
                "material_policy": "run facts, failures, evidence, and acceptance remain in this directory",
            }
            atomic_write(
                local_spec_path,
                yaml.dump(
                    local_spec,
                    Dumper=NoAliasSafeDumper,
                    allow_unicode=True,
                    sort_keys=False,
                    width=120,
                ),
            )

        raw_path = atom_dir / "KANBAN_DATA.md"
        if raw_path.exists():
            data = read_frontmatter(raw_path)
            if data.get("atom_id") != atom_id:
                fail(f"atom id mismatch in {raw_path}")
            if data.get("canonical_atom_sha256") != canonical_sha256:
                fail(f"canonical hash mismatch in {raw_path}")
        else:
            data = {
                "schema_version": 1,
                "producer": "game-codex",
                "atom_id": atom_id,
                "canonical_atom_sha256": canonical_sha256,
                "updated_at": observed_at,
                "activities": [],
                "proven": [],
                "not_proven": [],
                "failed": [],
                "next_evidence": [],
            }

        known_ids = {
            fact["fact_id"]
            for category in ("proven", "not_proven", "failed", "next_evidence")
            for fact in data.get(category, [])
        }
        appended = False
        for category in ("proven", "not_proven", "failed", "next_evidence"):
            data.setdefault(category, [])
            for fact in additions[category]:
                if fact["fact_id"] in known_ids:
                    continue
                data[category].append(fact)
                known_ids.add(fact["fact_id"])
                appended = True
        data.setdefault("activities", [])
        if appended:
            data["updated_at"] = observed_at
            changed.append(atom_id)
        # Always render through the no-alias dumper.  This also repairs output
        # produced by older versions of this script without changing facts.
        atomic_write(raw_path, render_frontmatter(data))

    print(
        "CARDWORDS_RUN_KANBAN_DATA_UPDATED "
        f"run_id={run_id} changed={','.join(changed) if changed else 'none'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
