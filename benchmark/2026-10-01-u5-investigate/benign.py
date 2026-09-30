"""Mine contextual U5 baseline noise; preserve terminal fatal events."""

import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re

import classify


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
REGISTRY = REPO / "knowledge/gates/benign-log-signatures.json"
CONTEXT = {"generation": "U5", "runtime_fingerprint": "73ecf422dba2", "boot_image_fingerprint": "0876029078e2"}


def normalize(message):
    message = re.sub(r"\b0x[0-9a-fA-F]{8,}\b", "<address>", message)
    message = re.sub(r"@[0-9a-fA-F]{6,}\b", "@<address>", message)
    message = re.sub(r"\b[0-9a-fA-F]{12,16}\b", "<address>", message)
    message = re.sub(r"\b(?:pid|tid)[=: ]+\d+\b", "<thread-id>", message, flags=re.I)
    return message


def signature(event):
    return event["tag"] + "|" + event["level"] + "|" + normalize(event["message"])


def partition(events, registry, context):
    if context != registry["context"]:
        return list(events), []
    allowed = {entry["signature"]: entry["id"] for entry in registry["signatures"]
               if entry["distinct_app_count"] >= 3 and entry.get("enabled_for_triage")}
    kept, noise = [], []
    traces = {}
    for event in events:
        thread = (event["pid"], event["tid"], event["tag"])
        if classify.FATAL.search(event["message"]):
            traces.pop(thread, None)
            kept.append(event)
            continue
        matched = allowed.get(signature(event))
        message = event["message"].removeprefix("[stderr] ").strip()
        trace = traces.get(thread)
        continuation = re.fullmatch(r"(?:java\.lang\.ClassNotFoundException: kotlinx\.coroutines\.CoroutineStart|Caused by: java\.lang\.ClassNotFoundException: kotlinx\.coroutines\.CoroutineStart|at .+|\.\.\. \d+ more)", message)
        continued = False
        if not matched and trace and continuation and event["timestamp"][:14] == trace["second"]:
            matched = trace["signature_id"]
            continued = True
        elif not matched:
            traces.pop(thread, None)
        if matched:
            noise.append({"signature_id": matched, "event": event})
            if "[COROUTINE-FIX] primeCoroutineStart FAILED (non-fatal):" in event["message"]:
                traces[thread] = {"signature_id": matched, "second": event["timestamp"][:14]}
            elif not continued:
                traces.pop(thread, None)
        else:
            kept.append(event)
    return kept, noise


def mine(root):
    score_path = REPO / "benchmark/2026-09-30-u4-sweep/J6N4-SCORING.json"
    score = json.loads(score_path.read_text())
    groups = defaultdict(lambda: {"supports": {}, "examples": []})
    inputs = []
    for row in score["rows"]:
        if row["t20"] != "own-ui":
            continue
        source = row["source"]
        record_path = root / source["record"]
        log_path = root / source["log"]
        for path, expected in ((record_path, source["record_sha256"]), (log_path, source["log_sha256"])):
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError("source identity changed: " + row["key"])
        record = json.loads(record_path.read_text())
        shot = next(shot for shot in record["screenshots"] if shot.get("scheduled_seconds") == 20)
        image_path = record_path.parent / "t20.jpeg"
        if hashlib.sha256(image_path.read_bytes()).hexdigest() != source["t20_sha256"]:
            raise ValueError("reviewed image changed: " + row["key"])
        cutoff = datetime.fromtimestamp(int(shot["remote_stat"].split()[1]), timezone(timedelta(hours=8))).strftime("%m-%d %H:%M:%S") + ".999"
        pids = set(map(int, source["target_pids"]))
        inputs.append({"key": row["key"], "package": source["package"], "pids": sorted(pids),
                       "log": source["log"], "log_sha256": source["log_sha256"], "record_sha256": source["record_sha256"],
                       "t20_sha256": source["t20_sha256"], "cutoff": cutoff, "visual": "own-ui"})
        for number, line in enumerate(log_path.read_text(errors="replace").splitlines(), 1):
            event = classify.parse(line, number)
            if not event or event["pid"] not in pids or event["timestamp"] > cutoff or not classify.is_execution(event):
                continue
            if classify.FATAL.search(event["message"]):
                continue
            if event["level"] not in {"W", "E"} and not re.search(r"(?:Exception|Error):|Exception:|failed: java\.", event["message"]):
                continue
            key = signature(event)
            group = groups[key]
            if row["key"] not in group["supports"]:
                group["supports"][row["key"]] = {"package": source["package"], "count": 0, "first_line": number}
                group["examples"].append({"key": row["key"], "package": source["package"], "event": event})
            group["supports"][row["key"]]["count"] += 1
    candidates = []
    for key, group in groups.items():
        packages = {item["package"] for item in group["supports"].values()}
        if len(packages) >= 3:
            candidates.append({"signature": key, "distinct_app_count": len(packages),
                               "occurrence_count": sum(item["count"] for item in group["supports"].values()), **group})
    return {"context": CONTEXT, "inputs": inputs, "candidates": sorted(candidates, key=lambda item: (-item["distinct_app_count"], item["signature"]))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--u5-root", type=Path, default=Path(os.environ.get("WORKSPACES", REPO.parent)) / "westlake-harness-bms-deploy/benchmark/2026-10-01-u5-sweep")
    args = parser.parse_args()
    print(json.dumps(mine(args.u5_root), indent=2))
