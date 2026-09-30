"""Read local U5 evidence; print an offline replay payload to stdout."""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path

import classify
import benign


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCORE = REPO / "benchmark/2026-09-30-u4-sweep/J6N4-SCORING.json"
APP_TAGS = {"SubscriptionRepository", "Termux", "OMcore"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(path, root):
    return {"path": str(path.relative_to(root)), "sha256": digest(path)}


def collect(root):
    score = json.loads(SCORE.read_text())
    registry = json.loads(benign.REGISTRY.read_text())
    baseline = json.loads((root / "results.json").read_text())
    context = {"generation": "U5", "runtime_fingerprint": baseline["runtime_fingerprint"], "boot_image_fingerprint": baseline["boot_image_fingerprint"]}
    cohort = []
    evidence = []
    for row in score["rows"]:
        source = row["source"]
        record_path = root / source["record"]
        if digest(record_path) != source["record_sha256"]:
            raise ValueError("record changed: " + row["key"])
        record = json.loads(record_path.read_text())
        shots = [shot for shot in record.get("screenshots", []) if shot.get("scheduled_seconds") == 20]
        alive = shots[0].get("foreground", {}).get("observed_pids", []) if shots else []
        entry = dict(key=row["key"], visual=row["t20"], alive_pids=alive, record=source["record"], record_sha256=source["record_sha256"])
        entry["status"] = classify.eligibility(row["t20"], alive, False)
        cohort.append(entry)
        if not alive or (row["t20"] == "own-ui" and row["key"] not in {"aegis", "anki"}):
            continue
        if not shots or not source["target_pids"]:
            continue
        log_path = root / source["log"]
        if digest(log_path) != source["log_sha256"]:
            raise ValueError("hilog changed: " + row["key"])
        shot = shots[0]
        epoch = int(shot["remote_stat"].split()[1])
        cutoff = datetime.fromtimestamp(epoch, timezone(timedelta(hours=8))).strftime("%m-%d %H:%M:%S") + ".999"
        process_path = record_path.parent / "processes-t20.txt"
        uid = record["bms"]["uid"]
        process_rows = []
        for number, line in enumerate(process_path.read_text().splitlines(), 1):
            parts = line.split()
            if len(parts) >= 4 and parts[0].isdigit() and parts[2] == str(uid):
                process_rows.append(dict(line=number, pid=int(parts[0]), text=line))
        if not set(alive) <= {process["pid"] for process in process_rows}:
            raise ValueError("t20 PID/UID mismatch: " + row["key"])
        pids = set(map(int, source["target_pids"])) | {process["pid"] for process in process_rows}
        events = []
        for number, line in enumerate(log_path.read_text(errors="replace").splitlines(), 1):
            event = classify.parse(line, number)
            if event:
                events.append(event)
        app = classify.scoped(events, pids, cutoff)
        facts = classify.summarize(events, pids, cutoff, registry, context)
        entry["status"] = classify.eligibility(row["t20"], alive, facts["fatal"])
        facts["category"] = classify.category(facts)
        old_markers = [event for event in events if event["timestamp"] <= cutoff and classify.OLD_RENDER.search(event["message"])]
        foreign = [event for event in old_markers if event["pid"] not in pids]
        business = [event for event in app if event["tag"].rsplit("/", 1)[-1] in APP_TAGS]
        selected = {}
        for value in facts.values():
            if isinstance(value, list):
                for event in value:
                    if isinstance(event, dict) and "line" in event:
                        selected[event["line"]] = event
        for process in facts["processes"]:
            for field in ("java_main_last", "leader_last", "last_process_log"):
                if process[field]:
                    selected[process[field]["line"]] = process[field]
            if process["java_main"]:
                event = process["java_main"]["binding"]
                selected[event["line"]] = event
        for event in business[-3:]:
            selected[event["line"]] = event
        for event in app:
            if event["line"] in source["binding_lines"] or str(event["line"]) in facts["benign_noise"]:
                selected[event["line"]] = event
        screenshot = record_path.parent / "t20.jpeg"
        if digest(screenshot) != source["t20_sha256"]:
            raise ValueError("t20 changed: " + row["key"])
        evidence.append(dict(key=row["key"], package=record["package"], apk_sha256=record["apk_sha256"], context=context,
                             cutoff=cutoff, cutoff_source="t20 screenshot remote mtime (second precision), not hilog end",
                             pids=sorted(pids), live_pid_rows=process_rows, process_file=snapshot(process_path, root),
                             log=snapshot(log_path, root), screenshot=snapshot(screenshot, root),
                             old_render_count=len(old_markers), foreign_render_count=len(foreign),
                             foreign_render_examples=foreign[:3],
                             application_logger_last=business[-1] if business else None,
                             application_logger_policy="Only explicit SubscriptionRepository / Termux / OMcore tags; missing is unknown, not absence of app execution",
                             facts=facts, replay_events=sorted(selected.values(), key=lambda event: event["line"])))
    return dict(schema_version=1, source_root="WORKSPACES/westlake-harness-bms-deploy/benchmark/2026-10-01-u5-sweep",
                scoring_sha256=digest(SCORE), benign_registry_sha256=digest(benign.REGISTRY), cohort=cohort, evidence=evidence)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--u5-root", type=Path, default=Path(os.environ.get("WORKSPACES", REPO.parent)) / "westlake-harness-bms-deploy/benchmark/2026-10-01-u5-sweep")
    args = parser.parse_args()
    print(json.dumps(collect(args.u5_root), indent=2))
