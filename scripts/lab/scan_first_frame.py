#!/usr/bin/env python3
"""Read-only PID-scoped graphics observations, not proof of frame presentation."""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re

import first_fatal


TOKENS = {"present": "present", "vsync": "vsync", "finish_drawing": "finishdrawing", "notify_drawing": "notifydrawingcompleted"}
GRAPHICS = re.compile(r"Gfx|Render|Surface|Window|RS|EGL|Buffer", re.I)
PRESENT = re.compile(r"^(?:\[stderr\] )?(?:\[[^]]+\] )?(?:present(?:Frame|Buffer)?|PresentDisplay|RSMainThread::DoComposition)\b.*(?:rc=|result=|success|failed|ENTRY|completed)", re.I)
FINISH = re.compile(r"^(?:\[stderr\] )?(?:\[[^]]+\] )?(?:WindowSessionAdapter\.)?finishDrawing(?:\(|:|\s).*?(?:ENTRY|completed|called|rc=|result=|window=)")
NOTIFY = re.compile(r"^(?:\[stderr\] )?(?:\[[^]]+\] )?(?:native)?Notify(?:Surface)?DrawingCompleted(?:\(|:|\s).*?(?:ENTRY|completed|called|rc=|result=|window=)", re.I)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stamp(epoch, upper=False):
    return datetime.fromtimestamp(float(epoch), timezone(timedelta(hours=8))).strftime("%m-%d %H:%M:%S") + (".999" if upper else ".000")


def semantic(event):
    if not first_fatal.classify.is_execution(event):
        return []
    message, tag = event["message"], event["tag"]
    result = []
    if tag.endswith("/OH_DER_VSync"):
        if re.match(r"^scheduleVsync RequestFrame rc=0\b", message):
            result.append("vsync_request_ok")
        if re.match(r"^scheduleVsync RequestFrame rc=-?[1-9]\d*\b", message):
            result.append("vsync_request_failed")
        if message.startswith("onOhVsync ENTRY "):
            result.append("vsync_callback")
    if GRAPHICS.search(tag):
        if PRESENT.search(message):
            result.append("present_event")
            if re.search(r"failed|(?:rc|result)=-?[1-9]\d*\b", message, re.I):
                result.append("present_failed")
        if FINISH.search(message):
            result.append("finish_drawing")
        if NOTIFY.search(message):
            result.append("notify_drawing")
    return result


def count_events(events, pids, start, cutoff):
    if not pids or not start or not cutoff or start > cutoff:
        raise ValueError("verified PIDs and valid launch/capture interval required")
    names = ["vsync_request_ok", "vsync_request_failed", "vsync_callback", "present_event", "present_failed", "finish_drawing", "notify_drawing"]
    counts = {name: 0 for name in names}
    examples = {name: [] for name in names}
    buckets = {name: [] for name in TOKENS}
    whole = {name: 0 for name in TOKENS}
    scoped = {name: 0 for name in TOKENS}
    nonexecution = {name: 0 for name in TOKENS}
    per_pid = {str(pid): dict(counts) for pid in sorted(pids)}
    request_times = []
    for event in events:
        for name, token in TOKENS.items():
            if token in event["message"].lower():
                whole[name] += 1
        if event["pid"] not in pids or not start <= event["timestamp"] <= cutoff:
            continue
        for name, token in TOKENS.items():
            if token in event["message"].lower():
                scoped[name] += 1
                if not first_fatal.classify.is_execution(event):
                    nonexecution[name] += 1
                if len(buckets[name]) < 3:
                    buckets[name].append(event)
        for name in semantic(event):
            counts[name] += 1
            per_pid[str(event["pid"])][name] += 1
            if len(examples[name]) < 3:
                examples[name].append(event)
            if name == "vsync_request_ok":
                request_times.append(event["timestamp"])
    return dict(counts=counts, per_pid=per_pid, examples=examples, raw_substring_whole_log=whole,
                raw_substring_app_interval=scoped, nonexecution_substrings=nonexecution,
                raw_examples=buckets, request_first=min(request_times) if request_times else None,
                request_last=max(request_times) if request_times else None,
                present_observability="explicit-marker-observed" if counts["present_event"] else "unknown-no-explicit-marker",
                finish_observability="explicit-marker-observed" if counts["finish_drawing"] else "unknown-no-explicit-marker",
                present_vsync_ratio=None if not counts["present_event"] else counts["present_event"] / max(1, counts["vsync_request_ok"]))


def suspicion(observation):
    counts = observation["counts"]
    reasons = []
    if counts["vsync_request_ok"] >= 100:
        reasons.append(dict(rule="request-volume-100", points=20))
    if counts["vsync_request_ok"] >= 500:
        reasons.append(dict(rule="request-volume-500", points=20))
    if counts["vsync_request_ok"] >= 20 and counts["vsync_callback"] * 2 < counts["vsync_request_ok"]:
        reasons.append(dict(rule="observed-callback-deficit", points=20))
    if counts["present_failed"]:
        reasons.append(dict(rule="explicit-present-failure", points=40))
    return dict(score=sum(item["points"] for item in reasons), reasons=reasons,
                interpretation="heuristic prioritization, not probability or cause; unobserved present/finishDrawing contributes zero")


def eligibility(row, visual):
    if visual != "white":
        return "not-reviewed-white"
    if not row["coverage_ok"]:
        return "incomplete-evidence"
    if row["termination"]["status"] != "no-observed-termination":
        return "observed-termination"
    return "candidate-not-proven"


def compact(value):
    if isinstance(value, list):
        return [compact(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {}
    for name, item in value.items():
        if name == "text":
            continue
        if name == "chain":
            result["chain_lines"] = [event["line"] for event in item]
        elif name == "later_terminals":
            result["later_terminal_count"] = len(item)
        elif name == "frames":
            result[name] = compact(item[:3])
        elif name == "message" and len(item) > 500:
            result[name] = item[:500]
            result["message_truncated"] = True
            result["full_message_sha256"] = hashlib.sha256(item.encode()).hexdigest()
        else:
            result[name] = compact(item)
    return result


def extract(folder):
    record, events, pids, reports, disappeared, pins = first_fatal.load_run(folder)
    shots = [shot for shot in record.get("screenshots", []) if shot.get("captured") and shot.get("scheduled_seconds") == 20]
    shot = shots[0] if len(shots) == 1 else None
    cutoff = stamp(shot["remote_stat"].split()[1], True) if shot and shot.get("remote_stat") else None
    start = stamp(record["clicked_at"]) if record.get("clicked_at") else None
    coverage = bool(pids and start and cutoff and (record.get("diagnostics") or {}).get("complete") and pins["diagnostic_hash_verified"])
    termination = first_fatal.analyze(events, pids, reports, disappeared, cutoff=cutoff)
    full = first_fatal.analyze(events, pids, reports, disappeared)
    for result in [termination, full]:
        result.pop("context", None)
        result.pop("noise_context", None)
    image_path = folder / "t20.jpeg"
    image_hash = sha(image_path) if image_path.is_file() else None
    if shot and image_hash != shot.get("sha256"):
        raise ValueError("capture bytes differ: " + record["key"])
    observation = count_events(events, pids, start, cutoff) if pids and start and cutoff else None
    return compact(dict(key=record["key"], package=record["package"], record_sha256=pins["record_sha256"],
                hilog_sha256=pins["hilog_sha256"], t20_sha256=image_hash, target_pids=sorted(pids),
                binding_lines=pins["binding_lines"], interval=dict(start=start, cutoff=cutoff), coverage_ok=coverage,
                screenshots_foreground_confirmed=bool(shot and (shot.get("foreground") or {}).get("confirmed")),
                observation=observation, suspicion=suspicion(observation) if observation else None,
                termination=termination, full_log_termination_observation_only=full,
                process_receipts={name: sha(folder / name) for name in ["processes-t5.txt", "processes-t20.txt"] if (folder / name).is_file()}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    print(json.dumps(extract(args.run), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
