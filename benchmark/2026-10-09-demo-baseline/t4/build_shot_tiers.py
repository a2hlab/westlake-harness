import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

from build_groups import HERE, MASTER, digest, expand, load, portable


PREFIX = re.compile(r"^(\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+(\d+)\s+(\d+)\s+[A-Z]\s+\S+:\s*(.*)$")
SPAWN = re.compile(r"SPAWN_RESULT ret=0 pid=(\d+)\b")
AMS = re.compile(r"spawned pname_([^,]+), pid_(\d+)\b")
CHILD = re.compile(r"entering Android child pid=(\d+)\s+uid=\d+\s+bundle=(\S+)")
LAUNCH = re.compile(r"nativeOnScheduleLaunchApplication ENTRY bundle=(\S+) process=(\S+) pid=(\d+)\b")
FRAME = "activityResumed (first-frame):"


def event(number, text, match):
    return {"line": number, "timestamp": match[1], "pid": int(match[2]), "text": text.rstrip("\r\n")}


def milliseconds(stamp):
    value = datetime.strptime("2026-" + stamp, "%Y-%m-%d %H:%M:%S.%f")
    delta = value - datetime(2026, 1, 1)
    return (delta.days * 86400 + delta.seconds) * 1000 + delta.microseconds // 1000


def timing(lines, package):
    births, identities, frames = [], [], []
    for number, text in enumerate(lines, 1):
        if not any(token in text for token in ("SPAWN_RESULT", "spawned pname_", "entering Android child", "nativeOnScheduleLaunchApplication ENTRY", FRAME)):
            continue
        prefix = PREFIX.match(text)
        if not prefix:
            continue
        row = event(number, text, prefix)
        message = prefix[4]
        spawn = SPAWN.search(message)
        ams = AMS.search(message)
        child = CHILD.search(message)
        launch = LAUNCH.search(message)
        if spawn:
            births.append({**row, "child_pid": int(spawn[1]), "kind": "APPSPAWN-SPAWN_RESULT"})
        if ams and ams[1] == package:
            identities.append({**row, "child_pid": int(ams[2]), "kind": "AppMS-spawned"})
        if child and child[2] == package and int(child[1]) == row["pid"]:
            identities.append({**row, "child_pid": int(child[1]), "kind": "ROUTE-A-bundle"})
        if launch and launch[1] == package and launch[2] == package and int(launch[3]) == row["pid"]:
            identities.append({**row, "child_pid": int(launch[3]), "kind": "B43-main-process"})
        if FRAME in message:
            frames.append(row)
    pids = sorted({row["child_pid"] for row in identities})
    episodes = []
    for pid in pids:
        bindings = [row for row in identities if row["child_pid"] == pid]
        starts = [row for row in births if row["child_pid"] == pid]
        if not starts:
            starts = [row for row in bindings if row["kind"] == "AppMS-spawned"]
        starts = list({(row["timestamp"], row["kind"]): row for row in starts}.values())
        starts.sort(key=lambda row: row["line"])
        if not starts:
            episodes.append({"pid": pid, "status": "unknown", "reason": "physical-child-start-missing", "identity": bindings[0]})
            continue
        for index, start in enumerate(starts):
            limit = starts[index + 1]["line"] if index + 1 < len(starts) else float("inf")
            candidates = [row for row in frames if row["pid"] == pid and start["line"] < row["line"] < limit]
            evidence = {"pid": pid, "start": start, "identity": bindings[0]}
            if not candidates:
                episodes.append({**evidence, "status": "unknown", "reason": "same-pid-first-frame-missing"})
                continue
            finish = candidates[0]
            elapsed = milliseconds(finish["timestamp"]) - milliseconds(start["timestamp"])
            if elapsed < 0:
                episodes.append({**evidence, "first_frame": finish, "status": "unknown", "reason": "clock-reversed"})
            else:
                episodes.append({**evidence, "first_frame": finish, "status": "known", "elapsed_ms": elapsed})
    known = [row["elapsed_ms"] for row in episodes if row["status"] == "known"]
    complete = bool(episodes) and all(row["status"] == "known" for row in episodes)
    return {"status": "known" if complete else "unknown", "reason": None if complete else "incomplete-main-process-timing",
            "max_elapsed_ms": max(known) if known else None, "episodes": episodes}


def choose_tier(runs, force_slow=False):
    known = [row["max_elapsed_ms"] for row in runs if row["status"] == "known"]
    maximum = max(known) if known else None
    unknown = sum(row["status"] != "known" for row in runs)
    fast = bool(runs) and unknown == 0 and maximum <= 4000 and not force_slow
    return {"screenshot_seconds": 10 if fast else 20, "historical_runs": len(runs),
            "known_runs": len(known), "unknown_runs": unknown, "max_first_frame_ms": maximum,
            "max_first_frame_seconds": maximum / 1000 if maximum is not None else None,
            "reason": "all-history-at-most-4s" if fast else "reserved-20s" if force_slow else
            "no-history-or-incomplete-timing" if not runs or unknown else "historical-maximum-over-4s"}


def scan_record(path, record):
    log = path.parent / "hilog.txt"
    base = {"record": portable(path), "record_sha256": digest(path), "serial": record.get("serial"),
            "hilog": portable(log)}
    if not log.is_file():
        return {**base, "status": "unknown", "reason": "hilog-missing", "max_elapsed_ms": None, "episodes": []}
    checksum = hashlib.sha256()
    def lines():
        with log.open("rb") as stream:
            for raw in stream:
                checksum.update(raw)
                yield raw.decode("utf-8", errors="backslashreplace")
    result = timing(lines(), record["package"])
    actual = checksum.hexdigest()
    diagnostics = record.get("diagnostics", {})
    if diagnostics.get("sha256") and diagnostics["sha256"] != actual:
        raise ValueError("pinned hilog changed: " + portable(log))
    if diagnostics.get("complete") is False:
        result.update(status="unknown", reason="capture-incomplete")
    return {**base, "hilog_sha256": actual, **result}


def generate(manifest_path):
    manifest = load(manifest_path)
    selected = [row for row in manifest["apps"] if row["install"]]
    aliases = {key: row for row in selected for key in row["signed_keys"]}
    runs = {row["key"]: [] for row in selected}
    paths = set()
    source13 = MASTER / "benchmark/2026-10-03-u13-stage-a-decision/selftest-u13-stage-a.json"
    source14 = MASTER / "benchmark/2026-10-08-u14-stage-a-decision-draft/record-selection.json"
    u13, u14 = load(source13), load(source14)
    paths.update(expand(row["record"]) for row in u13["runs"])
    paths.update(expand(value) for value in u14["selected"])
    for app in selected:
        for field in ("source_record", "selected_record"):
            binding = app["evidence"].get(field)
            if binding:
                path = expand(binding["path"])
                if digest(path) != binding["sha256"]:
                    raise ValueError("manifest source record changed: " + portable(path))
                paths.add(path)
    excluded = Counter()
    for path in sorted(paths):
        record = load(path)
        app = aliases.get(record.get("key"))
        if not app:
            excluded["not-selected-demo-key"] += 1
            continue
        if record.get("package") != app["package"]:
            raise ValueError("historical package mismatch: " + portable(path))
        if record.get("apk_sha256") != app["apk_sha256"]:
            excluded["different-or-missing-apk-identity"] += 1
            continue
        runs[app["key"]].append(scan_record(path, record))
    apps = [{"key": app["key"], "package": app["package"], "apk_sha256": app["apk_sha256"],
             **choose_tier(runs[app["key"]]), "runs": runs[app["key"]]}
            for app in sorted(selected, key=lambda row: row["key"])]
    counts = Counter(row["screenshot_seconds"] for row in apps)
    return {"schema": "demo-shot-tiers/v1", "execution_enabled": False,
            "policy": {"fast_max_ms": 4000, "fast_screenshot_seconds": 10, "slow_screenshot_seconds": 20,
                       "independent_of_stability_group": True, "unknown_is_slow": True,
                       "start": "main-package PID physical APPSPAWN result; exact-package AppMS spawned fallback",
                       "end": "first literal activityResumed (first-frame) on the same PID after birth",
                       "history_scope": "U13 candidate selection 219 + U14 union selection 348 + manifest reference/selected records; exact selected APK only",
                       "supersedes": "groups.json apps[].screenshot_seconds; group membership is unchanged"},
            "sources": [{"path": portable(path), "sha256": digest(path)} for path in (manifest_path, source13, source14)],
            "summary": {"selected_packages": len(apps), "t10": counts[10], "t20": counts[20],
                        "candidate_records": len(paths), "selected_history_runs": sum(len(value) for value in runs.values()),
                        "unknown_history_runs": sum(row["unknown_runs"] for row in apps), "excluded": dict(sorted(excluded.items()))},
            "apps": apps, "special_slots": [{"key": "toutiao", "package": "com.ss.android.article.news", **choose_tier([], True)},
                                             {"key": "BoatAttack", "package": None, **choose_tier([], True)}]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=HERE.parent / "demo-manifest.json")
    parser.add_argument("--out", type=Path, default=HERE / "shot-tiers.json")
    args = parser.parse_args()
    result = generate(args.manifest)
    for offset in range(0, len(result["apps"]), 64):
        chunk = result["apps"][offset:offset + 64]
        evidence = {row["key"]: row.pop("runs") for row in chunk}
        evidence_path = HERE / f"evidence/shot-history-{offset // 64}.json"
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        for row in chunk:
            row["history_evidence"] = {"path": portable(evidence_path), "sha256": digest(evidence_path), "pointer": "/" + row["key"]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": portable(args.out), "sha256": digest(args.out), **result["summary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
