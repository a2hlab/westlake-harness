#!/usr/bin/env python3
"""Fail-closed recurring D600 APK/Unity refresh and HumanTodo scanner."""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path("/opt/Bridge")
REPORT_ROOT = ROOT / "var/evidence/reports/demo-refresh"
CANONICAL = REPORT_ROOT / "CANONICAL.md"
UNITY_REPORT = REPORT_ROOT / "UNITY_INVENTORY.md"
TODO_REPORT = REPORT_ROOT / "HUMAN_TODO_CURRENT.md"
CRASH_LEDGER = REPORT_ROOT / "CRASH_FINGERPRINTS.jsonl"
LOCK = REPORT_ROOT / ".refresh.lock"
HDC = Path("/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc")
AAPT = Path("/Users/alexyang/Library/Android/sdk/build-tools/36.1.0/aapt")
NOTIFY_HANDLE = os.environ.get("BRIDGE_DEMO_NOTIFY_HANDLE", "")
RELEASE_ROOT = ROOT / "var/evidence/device-leases/demo-refresh"

FIXTURES = [
    ("OpenCalc", ROOT / "var/evidence/fixtures/github-apks/OpenCalc.v3.2.1.apk"),
    ("Gallery", ROOT / "var/evidence/fixtures/github-apks/gallery-396-foss-release.apk"),
    ("NewPipe", ROOT / "var/evidence/fixtures/github-apks/NewPipe_v0.29.0.apk"),
]


def utcnow() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run(argv: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)


def hdc(serial: str, shell: str, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return run([str(HDC), "-t", serial, "shell", shell], timeout=timeout)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, path)


def notify(subject: str, body: str) -> None:
    if not NOTIFY_HANDLE or not shutil.which("orca"):
        return
    run([
        "orca", "orchestration", "send", "--to", NOTIFY_HANDLE,
        "--type", "status", "--subject", subject, "--body", body,
    ], timeout=20)


def required_inputs() -> dict:
    paths = [
        ROOT / "AGENTS.md",
        ROOT / "docs/agent-entry.md",
        ROOT / "docs/spec/project.yaml",
        ROOT / "worker/lanes.yaml",
    ]
    for path in paths:
        path.read_bytes()
    return {
        "project": yaml.safe_load(paths[2].read_text()),
        "lanes": yaml.safe_load(paths[3].read_text()),
    }


def unity_inventory() -> list[dict]:
    manifest = yaml.safe_load((ROOT / "docs/spec/unity-goal-ladder.yaml").read_text())
    canonical_root = Path(manifest["import_policy"]["canonical_root"])
    rows: list[dict] = []
    for goal in manifest["goals"]:
        artifacts = goal.get("artifacts", [])
        if not artifacts:
            rows.append({
                "id": goal["id"], "name": goal["name"], "path": "",
                "state": goal.get("import_state", "UNKNOWN"), "hash": "", "actual": "",
            })
        for artifact in artifacts:
            path = canonical_root / artifact["path"]
            actual = sha256(path) if path.is_file() else ""
            rows.append({
                "id": artifact["id"], "name": goal["name"], "path": str(path),
                "state": "AVAILABLE_HASH_MATCH" if actual == artifact["sha256"] else (
                    "MISSING" if not actual else "HASH_MISMATCH"
                ),
                "hash": artifact["sha256"], "actual": actual,
                "device_state": goal.get("device_state", "UNKNOWN"),
            })
    return rows


def device_rows(lanes: dict) -> list[dict]:
    lane_by_prefix = {item["serial_prefix"].lower(): item for item in lanes["device_allocation"]}
    online = []
    if HDC.is_file():
        result = run([str(HDC), "list", "targets"], timeout=20)
        online = re.findall(r"[0-9a-f]{32}", result.stdout.lower())
    rows = []
    for prefix, item in lane_by_prefix.items():
        serial = next((value for value in online if value.startswith(prefix)), "")
        release = RELEASE_ROOT / f"{serial}.release" if serial else Path("/nonexistent")
        released = serial and release.is_file() and release.read_text().strip() == "RELEASED"
        rows.append({
            "fn": re.search(r"fn(\d+)", item["lane"]).group(1),
            "lane": item["lane"], "serial": serial or f"{prefix}…",
            "online": bool(serial), "released": bool(released),
        })
    return sorted(rows, key=lambda row: int(row["fn"]))


def apk_identity(path: Path) -> tuple[str, str]:
    if not AAPT.is_file():
        return "", ""
    output = run([str(AAPT), "dump", "badging", str(path)], timeout=30).stdout
    package = re.search(r"package: name='([^']+)'", output)
    activity = re.search(r"launchable-activity: name='([^']+)'", output)
    return package.group(1) if package else "", activity.group(1) if activity else ""


def record_crashes(text: str, cycle_id: str, subject: str) -> list[str]:
    lines = [
        line for line in text.splitlines()
        if re.search(
            r"FATAL EXCEPTION|Fatal signal|SIG(?:ABRT|SEGV)|Process .* died|"
            r"uncaught exception|app(?:lication)? crash",
            line,
            re.I,
        )
    ]
    if not lines:
        return []
    normalized = "\n".join(re.sub(r"\b(?:pid|tid)[=: ]+\d+\b|\b0x[0-9a-f]+\b", "<id>", line, flags=re.I)
                           for line in lines[:40])
    fingerprint = hashlib.sha256(normalized.encode()).hexdigest()
    existing = set()
    if CRASH_LEDGER.is_file():
        for line in CRASH_LEDGER.read_text(errors="replace").splitlines():
            try:
                existing.add(json.loads(line)["fingerprint"])
            except (ValueError, KeyError):
                pass
    if fingerprint not in existing:
        CRASH_LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with CRASH_LEDGER.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({
                "recorded_at": utcnow(), "cycle": cycle_id, "subject": subject,
                "fingerprint": fingerprint, "summary": lines[:8],
            }, ensure_ascii=False) + "\n")
        notify("Bridge D600 crash", f"{subject}: {fingerprint[:12]} — {lines[0][:180]}")
    return [fingerprint]


def safe_matrix(serial: str, apk_name: str, apk: Path, cycle_dir: Path) -> dict:
    """Run only with an explicit owner release file; never changes system policy."""
    package, activity = apk_identity(apk)
    stem = re.sub(r"[^A-Za-z0-9_.-]", "_", apk_name)
    raw = cycle_dir / serial[:8] / stem
    raw.mkdir(parents=True, exist_ok=True)
    remote = f"/data/local/tmp/bridge-demo-refresh-{os.getpid()}-{apk.name}"
    pre = hdc(serial, (
        "cat /proc/sys/kernel/random/boot_id; "
        "param get const.product.software.version; param get const.ohos.fullname; "
        "getenforce; "
        f"bm dump -n {package} 2>&1"
    )).stdout
    (raw / "preflight.txt").write_text(pre)
    if "bundleName" in pre or package in pre:
        return {"status": "NOT_PASS", "first_bad": "PREEXISTING_PACKAGE_REFUSED",
                "next": "owner supplies a clean, generation-frozen device window", "evidence": str(raw)}
    sent = run([str(HDC), "-t", serial, "file", "send", str(apk), remote], timeout=180)
    install = hdc(serial, f"sha256sum {remote}; bm install -p {remote}", timeout=180)
    combined = sent.stdout + install.stdout
    (raw / "install.txt").write_text(combined)
    if "successfully" not in install.stdout.lower():
        logs = hdc(serial, "hilog -x 2>&1", timeout=60).stdout
        (raw / "hilog.txt").write_text(logs)
        record_crashes(logs, cycle_dir.name, f"{apk_name} on {serial[:8]}")
        hdc(serial, f"rm -f {remote}")
        wall = "INSTALL_TERMINAL_ERROR"
        if "libapk_installer.so failed" in logs:
            wall = "FN01.A01_ENTRY_LIBAPK_INSTALLER_MISSING"
        return {"status": "NOT_PASS", "first_bad": wall,
                "next": "freeze matching target generation and repeat identical APK", "evidence": str(raw)}
    after = hdc(serial, (
        f"bm dump -n {package} 2>&1; "
        f"aa start -a {activity} -b {package} 2>&1; sleep 12; "
        f"ps -ef | grep -F {package}; "
        "hidumper -s WindowManagerService -a -a 2>&1; "
        "hilog -x 2>&1"
    ), timeout=120).stdout
    (raw / "after.txt").write_text(after)
    record_crashes(after, cycle_dir.name, f"{apk_name} on {serial[:8]}")
    # Package was absent before this run, so cleanup is scoped to this run.
    hdc(serial, f"aa force-stop -b {package} 2>&1; bm uninstall -n {package} 2>&1; rm -f {remote}", timeout=90)
    first_bad = "FIRST_FRAME_NOT_PROVEN"
    status = "NOT_PASS"
    if activity and package in after and "ActivityThread" in after:
        first_bad = "WINDOW_FIRST_FRAME_ORACLE_NOT_PROVEN"
    return {"status": status, "first_bad": first_bad,
            "next": "capture timestamp-bound screenshot/pixels and interaction/recovery oracle", "evidence": str(raw)}


def current_known_result(name: str) -> dict:
    if name == "OpenCalc":
        receipt = ROOT / "var/evidence/journeys/20260728T203348Z-opencalc-5cd-demo/RUN_RECEIPT.md"
        if receipt.is_file():
            return {"status": "NOT_PASS", "first_bad": "Fn01.A01 entry: libapk_installer.so errno=2",
                    "next": "same APK on an owner-frozen generation containing the installer library",
                    "evidence": str(receipt.relative_to(ROOT))}
    return {"status": "NOT_PASS", "first_bad": "CURRENT_D600_RUN_NOT_AVAILABLE",
            "next": "obtain explicit owner release and run the safe matrix", "evidence": "none"}


def refresh() -> int:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        inputs = required_inputs()
        cycle_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        cycle_dir = REPORT_ROOT / "runs" / cycle_id
        cycle_dir.mkdir(parents=True, exist_ok=True)
        inventory = unity_inventory()
        devices = device_rows(inputs["lanes"])
        runnable = [row for row in devices if row["online"] and row["released"]]
        results = {name: current_known_result(name) for name, _ in FIXTURES}
        if runnable:
            device = runnable[0]
            for name, apk in FIXTURES:
                results[name] = safe_matrix(device["serial"], name, apk, cycle_dir)
            for row in inventory:
                if row["state"] != "AVAILABLE_HASH_MATCH":
                    continue
                if row["id"].startswith(("G9", "G10", "G11")):
                    continue
                results[row["id"]] = safe_matrix(device["serial"], row["id"], Path(row["path"]), cycle_dir)
        for row in inventory:
            if row["id"] not in results:
                gate = "ARM32_RUNTIME_GATE" if row["id"].startswith(("G9", "G10", "G11")) else (
                    "APK_BYTES_NOT_AVAILABLE" if row["state"] != "AVAILABLE_HASH_MATCH" else "NO_RELEASED_DEVICE"
                )
                results[row["id"]] = {"status": "NOT_PASS", "first_bad": gate,
                                      "next": "satisfy gate and run next simplest tier", "evidence": "inventory"}
        report = [
            "<!-- TEMPLATE-SIGNATURE: docs/templates/.template.mentors.md#error-incident -->",
            "# D600 Real APK Canonical Status", "",
            f"refreshed_at: `{utcnow()}`", "",
            "| APK/tier | D600 | First-bad boundary | Next agent experiment |",
            "|---|---|---|---|",
        ]
        order = [name for name, _ in FIXTURES] + [row["id"] for row in inventory]
        for key in order:
            value = results[key]
            report.append(f"| {key} | **{value['status']}** | {value['first_bad']} | {value['next']} |")
        atomic_write(CANONICAL, "\n".join(report) + "\n")
        inventory_text = [
            "<!-- TEMPLATE-SIGNATURE: docs/templates/.template.mentors.md#error-incident -->",
            "# Unity APK Inventory", "", f"refreshed_at: `{utcnow()}`", "",
            "| Tier | Product | APK identity | Manifest/device state |",
            "|---|---|---|---|",
        ]
        for row in inventory:
            identity = f"`{row['path']}` / `{row['hash']}`" if row["path"] else "none"
            inventory_text.append(f"| {row['id']} | {row['name']} | {identity} | {row['state']} / {row.get('device_state', 'NOT_RUN')} |")
        atomic_write(UNITY_REPORT, "\n".join(inventory_text) + "\n")
        (cycle_dir / "cycle.json").write_text(json.dumps({
            "cycle": cycle_id, "devices": devices, "results": results,
            "policy": "device execution requires explicit RELEASED marker per serial",
        }, ensure_ascii=False, indent=2) + "\n")
        summary = "; ".join(f"{key}={results[key]['status']}:{results[key]['first_bad']}" for key in order)
        notify("Bridge D600 demo refresh", summary[:3500])
    return 0


def scan_human_todo() -> int:
    required_inputs()
    path = ROOT / ".HumanTodoList.md"
    text = path.read_text()
    entries = re.split(r"(?=^- \[ \] \*\*)", text, flags=re.M)
    chosen = ""
    for entry in entries:
        if "READY_FOR_OWNER" not in entry:
            continue
        evidence = re.findall(r"`([^`]*var/evidence/[^`]*)`", entry)
        if evidence and not all((ROOT / item).exists() for item in evidence):
            continue
        chosen = entry.strip()
        break
    if not chosen:
        chosen = "No evidence-ready unchecked human item; agent work remains."
    output = (
        "<!-- TEMPLATE-SIGNATURE: docs/templates/.template.mentors.md#human-todolist -->\n"
        "# Current Human Todo\n\n"
        f"refreshed_at: `{utcnow()}`\n\n{chosen}\n"
    )
    atomic_write(TODO_REPORT, output)
    title = re.search(r"\*\*([^*]+)\*\*", chosen)
    notify("Bridge human todo", title.group(1) if title else chosen[:180])
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["refresh", "human-todo"])
    args = parser.parse_args()
    return refresh() if args.mode == "refresh" else scan_human_todo()


if __name__ == "__main__":
    raise SystemExit(main())
