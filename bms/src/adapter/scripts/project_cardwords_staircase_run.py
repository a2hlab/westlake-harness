#!/usr/bin/env python3
"""Project one immutable CardWords launch capsule into L01-L14 raw run data.

The output is deliberately observational.  It records what the run executed,
where it first failed, and which later floors were not reached.  It does not
derive Kanban colors, acceptance, frontier priority, or cross-project status.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


FLOORS = (
    ("L01", "secretary", "主流程与公共基线"),
    ("L02", "package-inspect", "APK 包检查"),
    ("L03", "install-package", "原始 APK 安装"),
    ("L04", "appspawn-process-birth", "appspawn 进程出生"),
    ("L05", "activity-lifecycle", "Activity 生命周期"),
    ("L06", "native-library-load", "native 库装载"),
    ("L07", "jni-unityplayer-contract", "JNI / UnityPlayer 契约"),
    ("L08", "bionic-musl-runtime", "Bionic / Musl 运行时"),
    ("L09", "surface-anativewindow-egl", "Surface / ANativeWindow / EGL"),
    ("L10", "first-frame-visible", "真首帧可见"),
    ("L11", "input-dispatch", "输入分发"),
    ("L12", "audio-media-plugin", "音频 / 媒体 / 插件"),
    ("L13", "integration-review", "集成审查"),
    ("L14", "architecture-review", "架构审查"),
)

FIXED_ADAPTER_PATHS = (
    "/system/android/lib64/libart.so",
    "/system/android/lib64/libnativeloader.so",
    "/system/android/lib64/libapp_native_loader.so",
    "/system/android/lib64/libart_runtime_stubs.so",
    "/system/android/lib64/libbionic_compat.so",
    "/system/android/lib64/liboh_android_runtime.so",
    "/system/android/lib64/libsigchain.so",
)


def fail(message: str) -> "NoReturn":
    raise SystemExit(message)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        fail(f"missing run evidence: {path}")


def parse_env(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in read_text(path).splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key] = value
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evidence_meta(run_dir: Path, filename: str) -> dict[str, Any]:
    path = run_dir / filename
    if not path.is_file() or path.is_symlink():
        fail(f"invalid evidence file: {path}")
    data = path.read_bytes()
    return {
        "path": filename,
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "lines": data.count(b"\n"),
    }


def matching_events(hilog: str, patterns: tuple[str, ...]) -> list[dict[str, Any]]:
    compiled = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(hilog.splitlines(), start=1):
        if "HDC_LOG" in line:
            continue
        if not any(pattern.search(line) for pattern in compiled):
            continue
        monotonic_match = re.match(r"\s*([0-9]+[.][0-9]+)\s+", line)
        events.append(
            {
                "source": "hilog_window.txt",
                "line": line_number,
                "monotonic_seconds": (
                    float(monotonic_match.group(1)) if monotonic_match else None
                ),
                "text": line.strip(),
            }
        )
    return events


def floor_record(
    floor_id: str,
    slug: str,
    label: str,
    *,
    executed: bool,
    observation: str,
    facts: list[str],
    evidence: list[str],
    events: list[dict[str, Any]] | None = None,
    blocked_by: str | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "floor_id": floor_id,
        "slug": slug,
        "label": label,
        "executed": executed,
        "observation": observation,
        "facts": facts,
        "evidence": evidence,
        "events": events or [],
    }
    if blocked_by is not None:
        record["blocked_by"] = blocked_by
    return record


def main() -> int:
    if len(sys.argv) != 2:
        fail(f"usage: {Path(sys.argv[0]).name} RUN_DIR")
    run_dir = Path(sys.argv[1]).resolve()
    if not run_dir.is_dir():
        fail(f"run directory is not a directory: {run_dir}")

    identity = parse_env(run_dir / "run_identity.env")
    host_identity = parse_env(run_dir / "host_identity.env")
    preflight = read_text(run_dir / "device_preflight.txt")
    postflight = read_text(run_dir / "device_postflight.txt")
    package_dump = read_text(run_dir / "package_dump.json")
    apk_manifest = read_text(run_dir / "apk_manifest.xml")
    launch_text = read_text(run_dir / "launch.txt").strip()
    hilog = read_text(run_dir / "hilog_window.txt")
    app_pid = read_text(run_dir / "app_pid.txt").strip()

    required_identity = (
        "run_id",
        "host_started_at",
        "host_ended_at",
        "source_revision",
        "device_serial",
        "boot_id",
        "canonical_apk_sha256",
        "installed_apk_sha256",
        "launch_command",
        "launch_rc",
        "cold_start",
        "generation",
    )
    missing = [key for key in required_identity if key not in identity]
    if missing:
        fail(f"run_identity.env is missing keys: {', '.join(missing)}")
    if identity["canonical_apk_sha256"] != identity["installed_apk_sha256"]:
        fail("installed APK hash differs from canonical APK hash")

    boot_values = re.findall(r"^BOOT_ID=(\S+)", preflight + "\n" + postflight, re.MULTILINE)
    if len(boot_values) != 2 or len(set(boot_values)) != 1:
        fail(f"run is not enclosed by one boot identity: {boot_values}")

    absent_adapter_paths = [
        path for path in FIXED_ADAPTER_PATHS if f"ABSENT  {path}" in preflight
    ]
    package_fields: dict[str, str] = {}
    for field in (
        "bundleName",
        "codePath",
        "cpuAbi",
        "nativeLibraryPath",
        "mainElementName",
        "versionName",
    ):
        values = re.findall(rf'"{field}"\s*:\s*"([^"]*)"', package_dump)
        value = next((candidate for candidate in values if candidate), "")
        if value:
            package_fields[field] = value

    selinux_match = re.search(r"^SELINUX=(.*)$", preflight, re.MULTILINE)
    selinux = selinux_match.group(1).strip() if selinux_match else "unknown"

    process_events = matching_events(
        hilog,
        (
            r"StartProcess: routing to appspawn-x.*CardWordsStudio",
            r"Failed to connect /dev/unix/socket/AppSpawnX",
            r"AppSpawnClientSendMsg.*CardWordsStudio",
            r"spawn new app fail",
            r"PROCESS_START_FAILED",
        ),
    )
    activity_events = matching_events(
        hilog,
        (
            r"ActivityThread.*CardWordsStudio",
            r"bindApplication.*CardWordsStudio",
            r"LaunchActivity transaction.*CardWordsStudio",
            r"LoadLifecycle.*UnityPlayerActivity",
        ),
    )
    native_events = matching_events(
        hilog,
        (
            r"NativeLoader::load.*CardWordsStudio",
            r"OH_RegHook.*CardWordsStudio",
            r"libmain[.]so.*CardWordsStudio",
            r"libunity[.]so.*CardWordsStudio",
        ),
    )

    socket_failure = any(
        "Failed to connect /dev/unix/socket/AppSpawnX" in event["text"]
        for event in process_events
    )
    spawn_failure = any("spawn new app fail" in event["text"] for event in process_events)
    child_born = bool(activity_events or native_events or app_pid)
    if socket_failure and not child_born:
        first_failure_floor = "L04"
        run_result = "blocked_before_appspawn_child"
    elif not app_pid:
        first_failure_floor = "L04"
        run_result = "no_surviving_child_unknown_stage"
    else:
        first_failure_floor = None
        run_result = "child_survived_observation_window"

    l01_facts = [
        f"run_id={identity['run_id']}",
        f"source_revision={identity['source_revision']}",
        f"device={identity['device_serial']} boot_id={identity['boot_id']}",
        f"canonical APK SHA-256={identity['canonical_apk_sha256']}",
        f"cold_start={identity['cold_start']} generation={identity['generation']}",
    ]
    l02_facts = [
        "Pinned apkanalyzer parsed the package and UnityPlayer activity from the canonical APK AndroidManifest.xml.",
        "Installed base.apk bytes match the canonical APK SHA-256.",
        "BMS resolved the original package and launch component.",
        *(f"{key}={value}" for key, value in sorted(package_fields.items())),
    ]
    l03_facts = [
        "The package already existed before this run and was queryable through BMS.",
        "This run executed no install, uninstall, package rewrite, or signature transaction.",
        "Therefore it records installed result-state only, not a reproducible install transaction.",
    ]
    l04_facts = [
        f"aa returned rc={identity['launch_rc']} with output={launch_text!r}.",
        "AppMS routed the Android package to appspawn-x.",
        "No appspawn-x or CardWords PID existed after the observation window.",
    ]
    if socket_failure:
        l04_facts.append("AppSpawn client received ENOENT while connecting /dev/unix/socket/AppSpawnX.")
    if spawn_failure:
        l04_facts.append("AppMS recorded 'spawn new app fail' with pid 0.")

    floor_records = [
        floor_record(
            *FLOORS[0],
            executed=True,
            observation="actual_run_identity_recorded",
            facts=l01_facts,
            evidence=["run_identity.env", "host_identity.env", "device_preflight.txt"],
        ),
        floor_record(
            *FLOORS[1],
            executed=True,
            observation="actual_package_identity_recorded",
            facts=l02_facts,
            evidence=["apk_manifest.xml", "apk_signature.txt", "apk_entries.txt", "package_dump.json", "device_preflight.txt"],
        ),
        floor_record(
            *FLOORS[2],
            executed=True,
            observation="existing_install_result_state_only",
            facts=l03_facts,
            evidence=["package_dump.json", "commands.log", "app_pid_before.txt"],
        ),
        floor_record(
            *FLOORS[3],
            executed=True,
            observation="actual_failure",
            facts=l04_facts,
            evidence=["launch.txt", "launch.rc", "hilog_window.txt", "device_postflight.txt"],
            events=process_events,
        ),
    ]

    blocked_facts = {
        "L05": "No CardWords child reached ActivityThread, bindApplication, or Activity lifecycle dispatch.",
        "L06": "No CardWords child reached System.loadLibrary or the APK native-library path.",
        "L07": "No CardWords child reached UnityPlayer Java-to-JNI registration or calls.",
        "L08": "No CardWords child existed, so no app-scoped Bionic/Musl runtime observation was possible.",
        "L09": "No CardWords child reached app-owned Surface, ANativeWindow, EGL, or RenderService work.",
        "L10": "No CardWords process or app-owned surface existed; the captured screen is not evidence of a game frame.",
        "L11": "No game frame/focus target existed and this run injected no input event.",
        "L12": "No CardWords child reached Unity audio, media, or native plugin initialization.",
        "L13": "This was one bounded, not-cold failure run; replay, five-minute stability, input, and video were not executed.",
    }
    evidence_by_floor = {
        "L05": ["hilog_window.txt", "app_pid.txt"],
        "L06": ["hilog_window.txt", "app_maps.txt"],
        "L07": ["hilog_window.txt", "app_pid.txt"],
        "L08": ["hilog_window.txt", "app_pid.txt"],
        "L09": ["hilog_window.txt", "app_pid.txt"],
        "L10": ["screen.jpeg", "app_pid.txt"],
        "L11": ["commands.log", "app_pid.txt"],
        "L12": ["hilog_window.txt", "app_pid.txt"],
        "L13": ["run_identity.env", "commands.log", "app_pid.txt"],
    }
    for floor_id, slug, label in FLOORS[4:13]:
        floor_records.append(
            floor_record(
                floor_id,
                slug,
                label,
                executed=False,
                observation="not_reached_in_this_run",
                facts=[blocked_facts[floor_id]],
                evidence=evidence_by_floor[floor_id],
                blocked_by="L04",
            )
        )

    architecture_facts = [
        f"The original APK remained byte-identical at SHA-256 {identity['canonical_apk_sha256']}.",
        f"{len(absent_adapter_paths)} of {len(FIXED_ADAPTER_PATHS)} fixed adapter/runtime paths were absent.",
        f"The device reported SELinux {selinux}.",
        "The run performed no install, adapter deployment, system-library write, reboot, log clear, or package rewrite.",
        "The baseline is ineligible for product acceptance; the launch is retained only as actual current-generation failure evidence.",
    ]
    floor_records.append(
        floor_record(
            *FLOORS[13],
            executed=True,
            observation="actual_generation_gate_failure_recorded",
            facts=architecture_facts,
            evidence=["host_identity.env", "device_preflight.txt", "commands.log", "manifest.sha256"],
        )
    )

    evidence_names = (
        "host_identity.env",
        "apk_inspection.env",
        "apk_manifest.xml",
        "apk_signature.txt",
        "apk_entries.txt",
        "apk_native_entries.sha256",
        "run_identity.env",
        "commands.log",
        "targets.txt",
        "device_preflight.txt",
        "package_dump.json",
        "launch.txt",
        "launch.rc",
        "device_postflight.txt",
        "app_pid_before.txt",
        "app_pid.txt",
        "app_maps.txt",
        "app_status.txt",
        "hilog_window.txt",
        "screen.jpeg",
        "screenshot_capture.txt",
    )
    output = {
        "schema": "westlake.cardwords.staircase-run.v1",
        "producer": "game-codex",
        "run_id": identity["run_id"],
        "scope": "/opt/21.Game/02.unity.cardwords",
        "source_revision": identity["source_revision"],
        "device_serial": identity["device_serial"],
        "boot_id": identity["boot_id"],
        "host_started_at": identity["host_started_at"],
        "host_ended_at": identity["host_ended_at"],
        "generation": identity["generation"],
        "cold_start": identity["cold_start"],
        "canonical_apk_sha256": identity["canonical_apk_sha256"],
        "installed_apk_sha256": identity["installed_apk_sha256"],
        "launch": {
            "command": identity["launch_command"],
            "exit_code": int(identity["launch_rc"]),
            "stdout": launch_text,
            "surviving_app_pid": int(app_pid) if app_pid.isdigit() else None,
        },
        "run_result": run_result,
        "first_failure_floor": first_failure_floor,
        "fixed_adapter_paths_absent": absent_adapter_paths,
        "package_fields": package_fields,
        "floor_records": floor_records,
        "evidence_files": [evidence_meta(run_dir, name) for name in evidence_names],
        "limits": [
            "This run is not cold or truly-cold.",
            "It observes an adapter-free, SELinux-Permissive baseline and is not product acceptance evidence.",
            "A successful aa command only acknowledges the request; it does not prove child birth or Activity launch.",
            "Floors after L04 are explicit not-reached records, not inferred implementation failures.",
        ],
    }

    destination = run_dir / "RUN_DATA.json"
    destination.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    manifest_path = run_dir / "manifest.sha256"
    manifest_lines = []
    for path in sorted(run_dir.iterdir(), key=lambda candidate: candidate.name):
        if path == manifest_path or not path.is_file() or path.is_symlink():
            continue
        manifest_lines.append(f"{sha256_file(path)}  ./{path.name}\n")
    manifest_path.write_text("".join(manifest_lines), encoding="utf-8")
    print(
        f"CARDWORDS_RUN_DATA_WRITTEN run_id={identity['run_id']} "
        f"result={run_result} first_failure={first_failure_floor or 'none'} "
        f"sha256={sha256_file(destination)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
