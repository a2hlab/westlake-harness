#!/usr/bin/env python3
"""Manifest-driven D600 APK lifecycle evidence harness.

Each selected APK is an independent install/query/launch/screenshot/uninstall
unit.  The harness deliberately has no embedded device serial, package name,
activity, APK hash, or product path.  Those facts must arrive in a reviewed run
manifest with source provenance.

This is an execution tool, not an independent verifier and not a product PASS
issuer.  It preserves raw facts for a verifier to assess.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[3]
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{5,127}$")
PACKAGE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+$")
COMPONENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.$]*$")


class HarnessError(RuntimeError):
    pass


@dataclass(frozen=True)
class App:
    name: str
    apk: Path
    source_root: Path
    package: str
    activity: str | None
    module: str
    sha256: str | None = None


@dataclass(frozen=True)
class BmsIdentity:
    bundle_name: str
    bundle_type: int | None
    code_path: str
    cpu_abi: str
    launcher_activities: list[str]
    all_activities: list[str]
    selected_activity: str
    selected_module: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def native_libs(path: Path) -> list[str]:
    try:
        with zipfile.ZipFile(path) as archive:
            return sorted(
                name for name in archive.namelist()
                if name.startswith("lib/") and name.endswith(".so")
            )
    except zipfile.BadZipFile as error:
        raise HarnessError(f"invalid APK zip: {path}") from error


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", value)


def resolve_repo_path(value: str, label: str) -> Path:
    path = (ROOT / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as error:
        raise HarnessError(f"{label} must be inside the Bridge repository: {value}") from error
    return path


def load_manifest(path: Path) -> list[App]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise HarnessError(f"cannot read manifest: {error}") from error
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise HarnessError("manifest must be a mapping with schema_version: 1")
    items = data.get("apps")
    if not isinstance(items, list) or not items:
        raise HarnessError("manifest apps must be a non-empty list")
    result: list[App] = []
    packages: set[str] = set()
    for index, raw in enumerate(items):
        if not isinstance(raw, dict):
            raise HarnessError(f"apps[{index}] must be a mapping")
        missing = {"name", "apk", "source_root", "package", "module"} - set(raw)
        if missing:
            raise HarnessError(f"apps[{index}] missing {sorted(missing)}")
        package = str(raw["package"])
        activity = str(raw["activity"]) if raw.get("activity") is not None else None
        module = str(raw["module"])
        if not PACKAGE_RE.fullmatch(package):
            raise HarnessError(f"apps[{index}] has invalid package: {package}")
        if activity is not None and not COMPONENT_RE.fullmatch(activity):
            raise HarnessError(f"apps[{index}] has invalid activity: {activity}")
        if not COMPONENT_RE.fullmatch(module):
            raise HarnessError(f"apps[{index}] has invalid module: {module}")
        if package in packages:
            raise HarnessError(f"duplicate package in independent queue: {package}")
        packages.add(package)
        apk = resolve_repo_path(str(raw["apk"]), f"apps[{index}].apk")
        source_root = resolve_repo_path(str(raw["source_root"]), f"apps[{index}].source_root")
        if not apk.is_file() or apk.suffix.lower() != ".apk":
            raise HarnessError(f"apps[{index}] APK is missing or not an APK: {apk}")
        if not source_root.is_dir():
            raise HarnessError(f"apps[{index}] source_root is missing: {source_root}")
        expected_sha = raw.get("sha256")
        if expected_sha is not None:
            expected_sha = str(expected_sha).lower()
            if not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
                raise HarnessError(f"apps[{index}] sha256 must be 64 lowercase hex")
            actual_sha = sha256(apk)
            if actual_sha != expected_sha:
                raise HarnessError(f"apps[{index}] APK sha256 {actual_sha} != expected {expected_sha}")
        result.append(App(str(raw["name"]), apk, source_root, package, activity, module, expected_sha))
    return result


class D600:
    def __init__(self, hdc: str, serial: str, evidence: Path) -> None:
        self.hdc = hdc
        self.serial = serial
        self.evidence = evidence

    def run(self, name: str, *args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
        result = subprocess.run([self.hdc, "-t", self.serial, *args], text=True, capture_output=True, check=False)
        target = self.evidence / "raw" / f"{safe_name(name)}.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            f"argv: {json.dumps([self.hdc, '-t', self.serial, *args])}\n"
            f"returncode: {result.returncode}\n--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}",
            encoding="utf-8",
        )
        if check and result.returncode != 0:
            raise HarnessError(f"D600 command failed: {name}; see {target}")
        return result

    def shell(self, name: str, command: str, check: bool = False) -> subprocess.CompletedProcess[str]:
        return self.run(name, "shell", command, check=check)


def exact_package_seen(text: str, package: str) -> bool:
    return re.search(rf"(?<![A-Za-z0-9_.]){re.escape(package)}(?![A-Za-z0-9_.])", text) is not None


def bundle_tool_success(result: subprocess.CompletedProcess[str], operation: str) -> bool:
    """Interpret the Bundle Manager's terminal receipt, not HDC's transport RC.

    `hdc shell` can return zero after the remote `bm` tool printed a failed
    operation.  The only positive receipt accepted here is the tool's exact
    success sentence (with the current D600's optional "bundle" noun); BMS
    registration remains a separate, stronger gate immediately afterwards.
    """
    receipt = re.compile(
        rf"^\s*{re.escape(operation)}(?:\s+bundle)?\s+successfully\.\s*$",
        re.IGNORECASE | re.MULTILINE,
    )
    return result.returncode == 0 and receipt.search(result.stdout) is not None


def ability_tool_success(result: subprocess.CompletedProcess[str]) -> bool:
    """Reject an ability-manager failure even when HDC reports transport success."""
    output = result.stdout + result.stderr
    return result.returncode == 0 and re.search(
        r"(?:^|\n)\s*error:|failed to start ability", output, re.IGNORECASE
    ) is None


def extract_bms_json(text: str, package: str) -> dict[str, Any]:
    """Extract the BundleInfo JSON body from `bm dump -n`.

    The tool prints `<package>:` followed by a JSON object.  Treat malformed,
    missing, or package-mismatched output as absent metadata; callers must not
    fall back to test-manifest facts.
    """
    match = re.search(rf"(?m)^\s*{re.escape(package)}\s*:\s*$", text)
    if match is None:
        raise HarnessError(f"BMS dump does not contain exact package header: {package}")
    start = text.find("{", match.end())
    if start < 0:
        raise HarnessError(f"BMS dump has no JSON body for package: {package}")
    try:
        value, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError as error:
        raise HarnessError(f"BMS dump JSON parse failed for package: {package}") from error
    if not isinstance(value, dict):
        raise HarnessError(f"BMS dump JSON body is not an object for package: {package}")
    return value


def _skill_has_launcher_marker(skill: dict[str, Any]) -> bool:
    actions = skill.get("actions")
    entities = skill.get("entities")
    if not isinstance(actions, list) or not isinstance(entities, list):
        return False
    action_set = {str(item) for item in actions}
    entity_set = {str(item) for item in entities}
    return (
        "android.intent.action.MAIN" in action_set
        or "ohos.want.action.home" in action_set
    ) and (
        "android.intent.category.LAUNCHER" in entity_set
        or "entity.system.home" in entity_set
    )


def _ability_is_launcher(ability: dict[str, Any]) -> bool:
    if ability.get("isLauncherAbility") is True:
        return True
    skills = ability.get("skills")
    return isinstance(skills, list) and any(
        isinstance(skill, dict) and _skill_has_launcher_marker(skill)
        for skill in skills
    )


def derive_bms_identity(
    bms: dict[str, Any], package: str, expected_activity: str | None
) -> BmsIdentity:
    name = bms.get("name")
    app_info = bms.get("applicationInfo")
    app_bundle = app_info.get("bundleName") if isinstance(app_info, dict) else None
    if name != package and app_bundle != package:
        raise HarnessError(
            f"BMS identity mismatch: name={name!r} applicationInfo.bundleName={app_bundle!r}"
        )

    hap_modules = bms.get("hapModuleInfos")
    if not isinstance(hap_modules, list):
        raise HarnessError("BMS identity has no hapModuleInfos array")

    all_activities: list[tuple[str, str, bool]] = []
    for module in hap_modules:
        if not isinstance(module, dict):
            continue
        module_name = str(module.get("moduleName") or "entry")
        abilities = module.get("abilityInfos")
        if not isinstance(abilities, list):
            continue
        for ability in abilities:
            if not isinstance(ability, dict):
                continue
            ability_name = ability.get("name")
            ability_bundle = ability.get("bundleName")
            if not isinstance(ability_name, str) or ability_name == "":
                continue
            if ability_bundle not in (None, "", package):
                continue
            enabled = ability.get("enabled", True)
            if enabled is False:
                continue
            ability_module = str(ability.get("moduleName") or module_name)
            all_activities.append((ability_name, ability_module, _ability_is_launcher(ability)))

    if not all_activities:
        raise HarnessError("BMS identity has no enabled abilityInfos")

    launcher = [item for item in all_activities if item[2]]
    if not launcher:
        raise HarnessError("BMS identity has no enabled launcher ability")

    selected = (
        next((item for item in launcher if item[0] == expected_activity), None)
        if expected_activity is not None else launcher[0]
    )
    if selected is None:
        raise HarnessError(
            "manifest-selected activity is not an enabled BMS launcher: "
            f"{expected_activity}; bms_launchers={[item[0] for item in launcher]}"
        )
    return BmsIdentity(
        bundle_name=package,
        bundle_type=bms.get("applicationInfo", {}).get("bundleType")
        if isinstance(bms.get("applicationInfo"), dict) else None,
        code_path=str(app_info.get("codePath") or "") if isinstance(app_info, dict) else "",
        cpu_abi=str(app_info.get("cpuAbi") or bms.get("cpuAbi") or "")
        if isinstance(app_info, dict) else str(bms.get("cpuAbi") or ""),
        launcher_activities=[item[0] for item in launcher],
        all_activities=[item[0] for item in all_activities],
        selected_activity=selected[0],
        selected_module=selected[1],
    )


def device_preflight(device: D600, expected_selinux: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for key, command in {
        "version": "param get const.product.software.version",
        "selinux": "getenforce",
        "boot_id": "cat /proc/sys/kernel/random/boot_id",
        "appspawn_pid": "pidof appspawn-x || true",
        "package_artifact_sha256": (
            "sha256sum /system/lib64/libbms.z.so "
            "/system/lib64/libapk_installer.so /system/bin/installd 2>&1"
        ),
        "bms_apk_transaction_markers": (
            "strings /system/lib64/libbms.z.so 2>/dev/null | "
            "grep -E 'APK install requires exactly one APK|"
            "adapter APK list install|adapter APK install' || true"
        ),
    }.items():
        values[key] = device.shell(f"preflight-{key}", command).stdout.strip()
    if not values["version"]:
        raise HarnessError("D600 preflight failed: version absent")
    if expected_selinux != "any" and values["selinux"] != expected_selinux:
        raise HarnessError(
            f"D600 preflight failed: SELinux is {values['selinux']}, expected {expected_selinux}"
        )
    return values


def poll_pid(device: D600, prefix: str, package: str, attempts: int = 30) -> str:
    for attempt in range(1, attempts + 1):
        result = device.shell(f"{prefix}-pid-poll-{attempt:02d}", f"pidof {package} || true")
        pid = result.stdout.strip()
        if pid:
            return pid
        hilog = device.shell(
            f"{prefix}-pid-hilog-poll-{attempt:02d}",
            "hilog -x | grep 'AppSpawnClientSendMsg' | tail -20",
        )
        matches = re.findall(r"result:0x0 pid:(\d+)", hilog.stdout + hilog.stderr)
        for candidate in reversed(matches):
            ps = device.shell(
                f"{prefix}-pid-ps-verify-{attempt:02d}-{candidate}",
                "ps -A -o PID,PPID,UID,NAME,CMDLINE",
            )
            for line in ps.stdout.splitlines():
                columns = line.split(None, 4)
                if len(columns) >= 1 and columns[0] == candidate and package in line:
                    return candidate
            legacy_ps = device.shell(
                f"{prefix}-pid-ps-legacy-verify-{attempt:02d}-{candidate}",
                "ps -ef",
            )
            for line in legacy_ps.stdout.splitlines():
                columns = line.split()
                if len(columns) >= 2 and columns[1] == candidate and package in line:
                    return candidate
    return ""


def capture_launch_window(device: D600, prefix: str, package: str, activity: str) -> None:
    """Preserve the launch boundary before later PID polling adds HDC noise."""
    grep_pattern = (
        "StartAbility|StartUIAbility|ScheduleLaunch|AppSpawn|APPSPAWN|"
        "Parsed spawn request|Spawn request|ROUTE-A|WLTG|Central JNI|"
        "CK_BEFORE|CK_AFTER|J_initChild|ActivityThread|AndroidRuntime|"
        f"{package}|{activity}|com.ohos.settings"
    )
    device.shell(
        f"{prefix}-launch-window-hilog",
        f"hilog -x | grep -E '{grep_pattern}' | tail -n 800",
    )
    device.shell(
        f"{prefix}-launch-window-appspawn-files",
        "ls -l /data/service/el1/public/appspawnx 2>&1; "
        "grep -R -n 'Parsed spawn request\\|Spawn request\\|ROUTE-A\\|WLTG\\|Central JNI\\|CK_BEFORE\\|CK_AFTER\\|J_initChild\\|ActivityThread' "
        "/data/service/el1/public/appspawnx 2>/dev/null | tail -n 200",
    )
    device.shell(
        f"{prefix}-launch-window-ps",
        f"ps -A -o PID,PPID,UID,NAME,CMDLINE | grep -E 'appspawn-x|{package}|com.ohos.settings' || true",
    )


def app_lifecycle(device: D600, app: App, index: int, require_launch: bool = True) -> dict[str, Any]:
    """Execute one independent APK lifecycle and always close owned state.

    This is one member of an outer fail-fast queue, not a multi-package BMS
    transaction. Once this harness has verified that it installed an app, its
    ownership obligation is to attempt normal Bundle Manager removal and
    residue observation even when launch or capture fails.
    """
    prefix = f"{index:02d}-{safe_name(app.name)}"
    libs = native_libs(app.apk)
    result: dict[str, Any] = {
        "app": asdict(app),
        "apk_sha256": sha256(app.apk),
        "host_native_libs": libs,
        "requires_bionic_runtime_bridge": bool(libs),
        "steps": {},
        "verdict": "FAIL",
    }
    remote = f"/data/local/tmp/bridge-{safe_name(device.evidence.name)}-{index}.apk"
    pre = device.shell(f"{prefix}-pre-bms", f"bm dump -n {app.package}")
    result["steps"]["pre_bms_exact_package"] = exact_package_seen(pre.stdout + pre.stderr, app.package)
    if result["steps"]["pre_bms_exact_package"]:
        result["verdict"] = "BLOCK_PREEXISTING_PACKAGE"
        return result

    installed = False
    launch_rc: int | None = None
    launch_tool_success = False
    pid = ""
    screenshot_received = False
    remote_snapshot = f"/data/local/tmp/bridge-{safe_name(device.evidence.name)}-{index}.jpeg"
    try:
        send = device.run(f"{prefix}-send", "file", "send", str(app.apk), remote)
        result["steps"]["file_send_rc"] = send.returncode
        if send.returncode != 0:
            result["verdict"] = "FAIL_ARTIFACT_TRANSFER"
            return result
        remote_hash = device.shell(f"{prefix}-remote-sha", f"sha256sum {remote}")
        result["steps"]["remote_sha_matches"] = sha256(app.apk) in remote_hash.stdout
        if not result["steps"]["remote_sha_matches"]:
            result["verdict"] = "FAIL_ARTIFACT_INTEGRITY"
            return result
        install = device.shell(f"{prefix}-install", f"bm install -p {remote}")
        result["steps"]["install_rc"] = install.returncode
        result["steps"]["install_tool_success"] = bundle_tool_success(install, "install")
        after_install = device.shell(f"{prefix}-after-install-bms", f"bm dump -n {app.package}")
        installed = exact_package_seen(after_install.stdout + after_install.stderr, app.package)
        result["steps"]["installed_bms_exact_package"] = installed
        after_install_text = after_install.stdout + after_install.stderr
        result["steps"]["manifest_expected_activity"] = app.activity
        result["steps"]["after_install_bms_contains_expected_activity"] = (
            exact_package_seen(after_install_text, app.activity)
            if app.activity is not None else None
        )
        result["steps"]["after_install_bms_excerpt"] = after_install_text[:4096]
        bms_identity: BmsIdentity | None = None
        if installed:
            try:
                bms_identity = derive_bms_identity(
                    extract_bms_json(after_install_text, app.package),
                    app.package,
                    app.activity,
                )
                result["steps"]["bms_identity"] = asdict(bms_identity)
                result["steps"]["yaml_activity_registered_in_bms"] = (
                    app.activity in bms_identity.all_activities
                    if app.activity is not None else None
                )
                result["steps"]["yaml_activity_is_bms_launcher"] = (
                    app.activity in bms_identity.launcher_activities
                    if app.activity is not None else None
                )
            except HarnessError as error:
                result["steps"]["bms_identity_error"] = str(error)
        if (
            not result["steps"]["install_tool_success"]
            or not installed
            or bms_identity is None
        ):
            result["verdict"] = "FAIL_INSTALL_OR_QUERY"
            return result

        if not require_launch:
            result["steps"]["launch_skipped"] = True
        else:
            device.shell(f"{prefix}-force-stop-before", f"aa force-stop {app.package}")
            device.shell(f"{prefix}-hilog-clear-before-launch", "hilog -r")
            launch = device.shell(
                f"{prefix}-launch",
                "aa start "
                f"-a {bms_identity.selected_activity} "
                f"-b {bms_identity.bundle_name} "
                f"-m {bms_identity.selected_module} -W",
            )
            launch_rc = launch.returncode
            result["steps"]["launch_rc"] = launch_rc
            launch_tool_success = ability_tool_success(launch)
            result["steps"]["launch_tool_success"] = launch_tool_success
            if launch_tool_success:
                capture_launch_window(device, prefix, app.package, bms_identity.selected_activity)
                pid = poll_pid(device, prefix, app.package)
                result["steps"]["pid_after_launch"] = pid
                device.shell(f"{prefix}-ps-after-launch", f"ps -A -o PID,PPID,UID,NAME,CMDLINE | grep -E 'appspawn-x|{app.package}' || true")
                device.shell(f"{prefix}-hilog-after-launch", "hilog -x | tail -n 500")
                snapshot = device.shell(f"{prefix}-snapshot", f"snapshot_display -f {remote_snapshot}")
                local_snapshot = device.evidence / "screens" / f"{prefix}.jpeg"
                local_snapshot.parent.mkdir(parents=True, exist_ok=True)
                receive = device.run(f"{prefix}-snapshot-recv", "file", "recv", remote_snapshot, str(local_snapshot))
                result["steps"]["screenshot_rc"] = snapshot.returncode
                screenshot_received = (
                    receive.returncode == 0
                    and local_snapshot.is_file()
                    and local_snapshot.stat().st_size > 0
                )
            result["steps"]["screenshot_received"] = screenshot_received
    except Exception as error:
        result["steps"]["execution_error"] = str(error)
        result["verdict"] = "HARNESS_ERROR"
    finally:
        # Only remove an app when this invocation positively established that
        # it installed it.  A pre-existing app is never silently destroyed.
        device.shell(f"{prefix}-stage-cleanup", f"rm -f {remote}")
        device.shell(f"{prefix}-snapshot-cleanup", f"rm -f {remote_snapshot}")
        if installed:
            uninstall = device.shell(f"{prefix}-uninstall", f"bm uninstall -n {app.package}")
            result["steps"]["uninstall_rc"] = uninstall.returncode
            result["steps"]["uninstall_tool_success"] = bundle_tool_success(uninstall, "uninstall")
            after_remove = device.shell(f"{prefix}-after-uninstall-bms", f"bm dump -n {app.package}")
            result["steps"]["uninstalled_bms_absent"] = not exact_package_seen(after_remove.stdout + after_remove.stderr, app.package)
            residue = device.shell(
                f"{prefix}-residue",
                f"for p in /data/app/el1/bundle/public/{app.package} /data/storage/el2/base/haps/{app.package} /data/app/el2/0/base/{app.package} /data/app/el2/100/base/{app.package}; do test -e \"$p\" && echo PRESENT:$p || echo ABSENT:$p; done",
            )
            result["steps"]["residue_absent"] = "PRESENT:" not in residue.stdout

    if installed:
        cleanup_ok = (
            result["steps"].get("uninstall_rc") == 0
            and result["steps"].get("uninstall_tool_success") is True
            and result["steps"].get("uninstalled_bms_absent") is True
            and result["steps"].get("residue_absent") is True
        )
        if not require_launch and cleanup_ok:
            result["verdict"] = "PASS_PACKAGE_LIFECYCLE"
        elif all((launch_rc == 0, launch_tool_success, bool(pid), screenshot_received, cleanup_ok)):
            result["verdict"] = "PASS_CAPTURE_READY"
        elif result["verdict"] != "HARNESS_ERROR":
            result["verdict"] = "FAIL_LAUNCH_SCREENSHOT_OR_UNINSTALL"
    return result


def run_fail_fast_queue(
    apps: list[App],
    execute: Any,
    expected_verdict: str,
) -> tuple[list[dict[str, Any]], str | None, list[str]]:
    """Run independent package lifecycles and stop at the first non-pass.

    The returned package names make partial-prefix and unattempted membership
    explicit. The queue never converts member results into an atomic batch
    claim.
    """
    outcomes: list[dict[str, Any]] = []
    stopped_at: str | None = None
    for index, app in enumerate(apps, start=1):
        try:
            outcome = execute(app, index)
        except Exception as error:
            outcome = {
                "app": asdict(app),
                "verdict": "HARNESS_ERROR",
                "error": str(error),
            }
        outcomes.append(outcome)
        if outcome.get("verdict") != expected_verdict:
            stopped_at = app.package
            return outcomes, stopped_at, [member.package for member in apps[index:]]
    return outcomes, stopped_at, []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--apply", action="store_true", help="perform install/launch/uninstall; otherwise only validate input")
    parser.add_argument(
        "--mode",
        choices=["package", "capture"],
        default="capture",
        help="package validates install/query/uninstall; capture also requires launch and screenshot",
    )
    parser.add_argument("--hdc", default=shutil.which("hdc") or "hdc")
    parser.add_argument(
        "--expected-selinux",
        choices=["Enforcing", "Permissive", "any"],
        default="Enforcing",
        help="expected device SELinux state recorded during preflight",
    )
    args = parser.parse_args()
    if not RUN_ID_RE.fullmatch(args.run_id):
        raise HarnessError("run-id must be 6+ safe filename characters")
    apps = load_manifest(args.manifest)
    if not args.apply:
        print(json.dumps({"validated": [asdict(app) for app in apps]}, indent=2, default=str))
        return 0
    evidence = ROOT / "evidence" / "runs" / args.run_id
    if evidence.exists():
        raise HarnessError(f"run evidence directory already exists: {evidence}")
    evidence.mkdir(parents=True)
    shutil.copy2(args.manifest, evidence / "manifest.executed.yaml")
    device = D600(args.hdc, args.serial, evidence)
    summary: dict[str, Any] = {
        "run_id": args.run_id,
        "started_at": utc_now(),
        "serial": args.serial,
        "preflight": device_preflight(device, args.expected_selinux),
        "apps": [],
    }
    expected = "PASS_CAPTURE_READY" if args.mode == "capture" else "PASS_PACKAGE_LIFECYCLE"
    outcomes, stopped_at, unattempted = run_fail_fast_queue(
        apps,
        lambda app, index: app_lifecycle(
            device, app, index, require_launch=args.mode == "capture"
        ),
        expected,
    )
    summary["apps"] = outcomes
    summary["queue_policy"] = "fail_fast_single_package_transactions"
    summary["stopped_at_package"] = stopped_at
    summary["unattempted_packages"] = unattempted
    summary["finished_at"] = utc_now()
    (evidence / "SUMMARY.json").write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, default=str))
    return 0 if stopped_at is None and len(outcomes) == len(apps) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except HarnessError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
