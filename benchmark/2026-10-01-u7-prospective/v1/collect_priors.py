"""Capture labeled T7d component priors without calling them combined U7 results."""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--compose-review", type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("u7_first_fatal", ROOT / "scripts/lab/first_fatal.py")
    fatal = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fatal)
    base = args.wiki / "benchmark/2026-10-01-image-predeploy-gate"
    paths = [base / relative for relative in [
        "t7d-stub-spec/T7D-STUB-SPEC.md", "t7d-stub-spec/t7d-stub-edits.patch",
        "t7d-stub-spec/sources/tagsoup/Parser.java", "t7d-stub-spec/sources/tagsoup/AOSP-r1-tagsoup-SHA256SUMS.txt",
        "t7d-board-5cd/results.json", "t7d-board-5cd/facts.txt",
        "t7d-board-5cd/zzsv-20261001T045309/resident-before.sha256",
        "t7d-board-5cd/zzsv-20261001T045309/resident-after.sha256",
    ]]
    paths.append(args.compose_review)
    sources = []
    for path in paths:
        lines = path.read_text().splitlines()
        selected = [(number, text) for number, text in enumerate(lines, 1)
                    if path.name != "Parser.java" or "public " in text or "implements" in text or "extends DefaultHandler" in text]
        sources.append(dict(source=str(path.relative_to(args.wiki)) if path.is_relative_to(args.wiki) else "westlake-harness-t3/benchmark/2026-09-30-u4-sweep/COMPOSE-WALL.md",
                            sha256=sha(path), lines=[dict(line=number, text=text) for number, text in selected]))
    rows = []
    for path in sorted(args.run.glob("*/record.json")):
        folder = path.parent
        record, events, pids, reports, disappeared, pins = fatal.load_run(folder)
        shots = [shot for shot in record.get("screenshots", []) if shot.get("scheduled_seconds") == 20 and shot.get("captured")]
        cutoff = None
        if len(shots) == 1 and shots[0].get("remote_stat"):
            cutoff = datetime.fromtimestamp(int(shots[0]["remote_stat"].split()[1]), timezone(timedelta(hours=8))).strftime("%m-%d %H:%M:%S") + ".999"
        result = fatal.analyze(events, pids, reports, disappeared, None, None, cutoff)
        result.pop("context", None)
        result.pop("noise_context", None)
        full = fatal.analyze(events, pids, reports, disappeared, None, None, None)
        full.pop("context", None)
        full.pop("noise_context", None)
        rows.append(dict(key=record["key"], record_sha256=pins["record_sha256"], hilog_sha256=pins["hilog_sha256"],
                         package=record["package"], apk_sha256=record["apk_sha256"], target_pids=sorted(pids), cutoff=cutoff,
                         source=str(folder.relative_to(args.wiki)), termination=result,
                         full_log_termination_observation_only=full,
                         t20_sha256=shots[0]["sha256"] if len(shots) == 1 else None,
                         note="Component T7d + U5 J6 runtime, not combined U7 J7b; screenshots labeled by outer, not this script"))
    print(json.dumps(dict(component="T7d-only-on-U5", sources=sources, rows=rows,
                          outer_signoffs=["ACK80 04:51:02 three own-UI targets", "ACK80 04:57:15 ZigZag U5 3/3 T7d 3/3; T7d accepted", "ACK95 04:57:34 U7 composition", "ACK95 04:59:10 quarantine accepted"],
                          caveats=["Early t5 ZigZag black was superseded by outer-reviewed six t20 images", "Compose-specific root cause refuted by cc-t3; blank root remains unproven", "Missing API errors alone are not positive checkpoint proof"]), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
