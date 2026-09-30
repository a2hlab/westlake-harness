"""Read the authorized 16+6 shard, retaining input failures and first-attempt evidence."""

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re

import intake


u6 = intake.u6
HERE = Path(__file__).resolve().parent
SEGMENTS = ["5cd/20261001T054910-73c67347/5cd1e3dd00000000000000000923012c",
            "5cd-resume/20261001T061216-7af5a7e8/5cd1e3dd00000000000000000923012c"]
INTEREST = re.compile(r"tagsoup|HtmlToSpanned|SSLSockets|canManageMedia|getContentUri|EXTERNAL_CONTENT|ColorMatrix|nativeOnScheduleLaunchApplication ENTRY|RESUME_ACTIVITY|createSession:|main_threw|JNI DETECTED|JNI FatalError|in call to GetLongField|\[T7")


def validate_segments(summaries, planned):
    keys = [row["key"] for summary in summaries for row in summary["records"]]
    if [len(summary["records"]) for summary in summaries] != [16, 6] or len(set(keys)) != 22 or set(keys) != set(planned):
        raise ValueError("need unique authorized 16+6 partition")
    if set(summaries[0]["not_run"]) != {row["key"] for row in summaries[1]["records"]} or summaries[1].get("not_run") or summaries[1].get("batch_error"):
        raise ValueError("resume does not close interrupted plan")
    if summaries[0].get("batch_error") != "target cleanup could not be verified; stop before next app":
        raise ValueError("unexpected interruption")


def analyze_folder(folder):
    record, events, pids, reports, disappeared, pins = u6.first_fatal.load_run(folder)
    shot = next((shot for shot in record.get("screenshots", []) if shot.get("captured") and shot.get("scheduled_seconds") == 20), None)
    cutoff = datetime.fromtimestamp(int(shot["remote_stat"].split()[1]), timezone(timedelta(hours=8))).strftime("%m-%d %H:%M:%S") + ".999" if shot else None
    start = datetime.fromtimestamp(record["clicked_at"], timezone(timedelta(hours=8))).strftime("%m-%d %H:%M:%S") + ".000" if record.get("clicked_at") else None
    bounded = [event for event in events if start and event["timestamp"] >= start]
    registry = u6.read(u6.benign.REGISTRY)
    fatal = u6.first_fatal.analyze(bounded, pids, reports, disappeared, registry, registry["context"], cutoff)
    witnesses = [event for event in u6.classify.scoped(bounded, pids, cutoff) if u6.classify.is_execution(event) and INTEREST.search(event["message"])] if cutoff else []
    if shot and u6.sha(folder / "t20.jpeg") != shot["sha256"]:
        raise ValueError("capture drift")
    return record, dict(record_sha256=pins["record_sha256"], hilog_sha256=pins["hilog_sha256"],
                        target_pids=sorted(pids), binding_lines=pins["binding_lines"],
                        log_complete=bool((record.get("diagnostics") or {}).get("complete") and pins["diagnostic_hash_verified"]),
                        interval=dict(start=start, cutoff=cutoff), termination=intake.compact_terminal(fatal),
                        native_frames=intake.scan_first_frame.compact((fatal.get("root") or {}).get("report", {}).get("frames", [])),
                        t20_sha256=shot["sha256"] if shot else None,
                        process_receipts={name: u6.sha(folder / name) for name in ["processes-t5.txt", "processes-t20.txt"] if (folder / name).is_file()},
                        witnesses=intake.scan_first_frame.compact(witnesses))


def collect(root, shard="5cd"):
    freeze = intake.verify_freeze()
    expected = u6.read(intake.FROZEN / "expected-run.json")
    predictions = {row["key"]: row for row in u6.read(intake.FROZEN / "PREDICTIONS.json")["rows"]}
    segments = SEGMENTS if shard == "5cd" else ["61b/20261001T060453-7a751269/61b0657200000000000000000324012c"]
    summaries = [u6.read(root / relative / "summary.json") for relative in segments]
    plan = u6.read(root / segments[0] / "plan.json")
    if shard == "5cd":
        validate_segments(summaries, [row["key"] for row in plan["apps"]])
    elif len(summaries[0]["records"]) != 22 or summaries[0].get("batch_error") or summaries[0].get("not_run") or {row["key"] for row in summaries[0]["records"]} != {row["key"] for row in plan["apps"]}:
        raise ValueError("61b is not a completed shard")
    attempts, audit, pins, rows = {}, [], {}, []
    for path in sorted(root.glob(shard + "*/*/*/summary.json")):
        summary = u6.read(path)
        audit.append(dict(source=str(path.relative_to(root)), sha256=u6.sha(path), records=len(summary.get("records", [])),
                          batch_error=summary.get("batch_error"), not_run=summary.get("not_run", [])))
    for path in sorted(root.glob(shard + "*/*/*/*/record.json")):
        record = u6.read(path)
        attempts.setdefault(record["key"], []).append(dict(record=str(path.relative_to(root)), clicked_at=record.get("clicked_at"), sha256=u6.sha(path)))
    for relative, summary in zip(segments, summaries):
        base = root / relative
        plan = u6.read(base / "plan.json")
        runtime, boot = u6.inventory(base / "runtime-fingerprint.txt"), u6.inventory(base / "boot-image-fingerprint.txt")
        for name in ["summary.json", "plan.json", "baseline.json", "facts.txt", "runtime-fingerprint.txt", "boot-image-fingerprint.txt"]:
            pins[str((base / name).relative_to(root))] = u6.sha(base / name)
        for original in summary["records"]:
            key = original["key"]
            record, row = analyze_folder(base / key)
            if record != original or record["serial"] != plan["serial"]:
                raise ValueError("record differs from summary or board")
            path = str((base / key / "record.json").relative_to(root))
            first = intake.first_attempt(path, attempts[key])
            issues = intake.identity_issues(record, runtime, boot, expected, predictions[key], plan["tool"])
            if not first or record.get("clicked_at", 0) <= datetime.fromisoformat(freeze["frozen_at"]).timestamp():
                issues.append("no-first-post-freeze-execution")
            if not row["t20_sha256"] and (key != "fd-seal" or record["status"] != "app_failed" or record.get("clicked")):
                raise ValueError("unexpected missing screenshot")
            row.update(key=key, record=path, prediction=predictions[key], first_attempt=first, attempts=attempts[key],
                       identity_verified=not issues, issues=issues, observed_input=u6.app_identity(record),
                       runtime_count=len(runtime), boot_count=len(boot), tool=plan["tool"],
                       status=record["status"], input_error=record.get("error"),
                       t20_path=str((base / key / "t20.jpeg").relative_to(root)) if row["t20_sha256"] else None)
            rows.append(row)
    return dict(status="signed-shard-intake-not-full-U7", prediction_sha256=intake.CSV_SHA, source_pins=pins,
                aborted_run_audit=audit, first_fatal_sha256=u6.sha(intake.ROOT / "scripts/lab/first_fatal.py"),
                noise_registry_sha256=u6.sha(u6.benign.REGISTRY), frozen_pins_checked=len(freeze["files"]),
                selected_keys=len(rows), missing_keys=sorted(set(predictions) - {row["key"] for row in rows}), rows=sorted(rows, key=lambda row: row["key"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=intake.ROOT.parent / "westlake-harness-wiki/benchmark/2026-10-01-u7-sweep")
    parser.add_argument("--shard", choices=["5cd", "61b"], default="5cd")
    args = parser.parse_args()
    print(u6.encoded(collect(args.root.resolve(), args.shard)), end="")


if __name__ == "__main__":
    main()
