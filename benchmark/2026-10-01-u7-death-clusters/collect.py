"""Replay U7 non-own-UI evidence without changing the accepted score."""

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCORES = ROOT / "benchmark/2026-10-01-u7-scoring"
sys.path.insert(0, str(SCORES))
import signed_intake


u6 = signed_intake.u6
MAIN = "[CM-BIGSTACK] ActivityThread on dedicated pthread"
DETAIL = re.compile(r"JNI DETECTED|JNI FatalError|GetLongField|libz\.so|__gnu_strerror_r|android_dlopen_ext|slCreateEngine|android_set_abort_message|ColorMatrix|MapInfoLayer|ATrace_beginSection|libmediandk|AccountManager|WebViewFactory|NoSuchMethodError|NoSuchFieldError")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def select(report):
    rows = [dict(row, shard=shard) for shard, body in report["shards"].items() for row in body["rows"]]
    if len(rows) != 66 or len({row["key"] for row in rows}) != 66 or sum(row["visual"] == "own-ui" for row in rows) != 34:
        raise ValueError("signed cohort must be 66 with 34 own UI")
    return sorted([row for row in rows if row["visual"] != "own-ui"], key=lambda row: row["key"])


def thread_observations(events, pids, start, cutoff):
    scoped = [event for event in events if event["pid"] in pids and (not cutoff or event["timestamp"] <= cutoff)]
    bindings = [event for event in scoped if MAIN in event["message"]]
    threads = {(event["pid"], event["tid"]) for event in bindings}
    executed = [event for event in scoped if (not start or event["timestamp"] >= start) and u6.classify.is_execution(event)]
    main = [event for event in executed if (event["pid"], event["tid"]) in threads]
    unique = [event for event in main if "[stderr]" not in event["message"]]
    tail = (unique or main)[-8:]
    gap = None
    if cutoff and tail:
        gap = (datetime.strptime("2026-" + cutoff, "%Y-%m-%d %H:%M:%S.%f") - datetime.strptime("2026-" + tail[-1]["timestamp"], "%Y-%m-%d %H:%M:%S.%f")).total_seconds()
    return dict(bindings=bindings, main_threads=[dict(pid=pid, tid=tid) for pid, tid in sorted(threads)],
                last_main_execution=tail, last_app_execution=executed[-4:], silence_before_capture_seconds=gap,
                state_at_t20="unknown-no-thread-stack-sample", inference="last logged action only; silence cannot distinguish Looper wait, blocked syscall, native rendering or unlogged execution")


def collect(run_root):
    score_path = SCORES / "formal-66/results.json"
    report = json.loads(score_path.read_text())
    stored = {}
    for path in [SCORES / "evidence/5ea-prepared.json", SCORES / "signed-44/5cd-prepared.json", SCORES / "formal-66/61b-prepared.json"]:
        stored.update({row["key"]: row for row in json.loads(path.read_text())["rows"]})
    rows = []
    for score in select(report):
        folder = (run_root / score["record"]).parent
        record, analyzed = signed_intake.analyze_folder(folder)
        expected = stored[score["key"]]
        for field in ["record_sha256", "hilog_sha256", "t20_sha256", "termination", "target_pids"]:
            if analyzed[field] != expected[field]:
                raise ValueError("scoring evidence drift: " + score["key"] + "/" + field)
        _, events, pids, reports, disappeared, _ = u6.first_fatal.load_run(folder)
        start, cutoff = analyzed["interval"]["start"], analyzed["interval"]["cutoff"]
        scoped = [event for event in events if event["pid"] in pids and cutoff and event["timestamp"] <= cutoff]
        registry = u6.read(u6.benign.REGISTRY)
        session_fatal = u6.first_fatal.analyze(events, pids, reports, disappeared, registry, registry["context"], cutoff) if pids else None
        supplemental = [event for event in scoped if u6.classify.is_execution(event) and DETAIL.search(event["message"])]
        root = (analyzed["termination"].get("root") or {}).get("event") or {}
        terminal = (analyzed["termination"].get("terminal") or {}).get("event") or {}
        causal = [event for event in scoped if terminal and event["pid"] == terminal["pid"] and event["tid"] == terminal["tid"] and min(root.get("line", terminal["line"]), terminal["line"]) - 3 <= event["line"] <= max(root.get("line", terminal["line"]), terminal["line"]) + 12]
        lines = (folder / "record.json").read_text().splitlines()
        errors = [dict(line=number, text=line.strip()) for number, line in enumerate(lines, 1) if '"error"' in line or '"status"' in line or '"clicked"' in line]
        rows.append(dict(key=score["key"], shard=score["shard"], signed_visual=score["visual"], observed_wall=score["observed_wall"],
                         record=score["record"], hilog=str(Path(score["record"]).with_name("hilog.txt")), authority=score["authority"],
                         evidence=analyzed, causal_excerpt=causal, supplemental_not_root=supplemental,
                         session_first_fatal=signed_intake.intake.compact_terminal(session_fatal) if session_fatal else None,
                         threads=thread_observations(events, pids, start, cutoff), input_error=record.get("error"), record_error_lines=errors))
    return dict(schema_version=1, signed_scores_sha256=sha(score_path), first_fatal_sha256=sha(ROOT / "scripts/lab/first_fatal.py"),
                run_root="WORKSPACES/westlake-harness-wiki/benchmark/2026-10-01-u7-sweep", keys=32, rows=rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, default=ROOT.parent / "westlake-harness-wiki/benchmark/2026-10-01-u7-sweep")
    args = parser.parse_args()
    print(json.dumps(collect(args.run_root), ensure_ascii=False, sort_keys=True, indent=2))
