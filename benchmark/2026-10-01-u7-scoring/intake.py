"""Read-only completed-shard intake for the unchanged U7 freeze."""

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FROZEN = HERE.parent / "2026-10-01-u7-prospective/v1"
sys.path.insert(0, str(HERE.parent / "2026-10-01-u6-scoring"))
sys.path.insert(0, str(ROOT / "scripts/lab"))
import score as u6
import scan_first_frame


CSV_SHA = "fa92c5b964fed2976ba66d82fb703672241435a294c8d9286a7c9192ebab9007"
RUNNER_SHA = "71cd7ecd93248deae1d4e385237c7794b260634e584162b7f3d2af3d58bcfd9a"
BATCH_SHA = "456dfc6f9cb637a82c357823ebe4395c9d9c16dea7b3ebed93c6580efefe6418"


def verify_freeze():
    if u6.sha(FROZEN / "PREDICTIONS.csv") != CSV_SHA:
        raise ValueError("U7 CSV changed")
    frozen = u6.read(FROZEN / "FREEZE.json")
    for name, digest in frozen["files"].items():
        if u6.sha(ROOT / name) != digest:
            raise ValueError("U7 frozen dependency changed: " + name)
    return frozen


def identity_issues(record, runtime, boot, expected, prediction, tool):
    issues = []
    tests = [(runtime == expected["runtime_files"], "runtime-mismatch"),
             (boot == expected["boot_files"], "boot-mismatch"),
             (u6.app_identity(record) == expected["apps"][record["key"]], "app-input-mismatch"),
             (record.get("input_sha256") == prediction["metadata_sha256"], "metadata-mismatch"),
             (u6.installed_identity(record, u6.app_identity(record)), "install-or-assembly-unverified"),
             (tool.get("bms_batch_sha256") == BATCH_SHA, "batch-tool-mismatch"),
             (tool.get("manifest_sha256") == RUNNER_SHA, "runner-manifest-mismatch")]
    for accepted, reason in tests:
        if not accepted:
            issues.append(reason)
    return issues


def first_attempt(selected, attempts):
    timed = [row for row in attempts if row["clicked_at"]]
    if not timed:
        return False
    first = min(timed, key=lambda row: (row["clicked_at"], row["record"]))
    if first["record"] != selected:
        raise ValueError("selected a later timed retry: " + selected)
    return True


def compact_terminal(result):
    result = scan_first_frame.compact(result)
    for field in ["context", "noise_context"]:
        entries = result.pop(field, [])
        result[field + "_sha256"] = u6.seal(entries)
        result[field + "_count"] = len(entries)
    return result


def prepare(root, selection):
    frozen = verify_freeze()
    expected = u6.read(FROZEN / "expected-run.json")
    predictions = {row["key"]: row for row in u6.read(FROZEN / "PREDICTIONS.json")["rows"]}
    frozen_time = datetime.fromisoformat(frozen["frozen_at"]).timestamp()
    rows, audit, pins = [], [], {}
    registry = u6.read(u6.benign.REGISTRY)
    for shard, relative in selection["shards"].items():
        base = u6.within(root, relative)
        summary = u6.read(base / "summary.json")
        plan = u6.read(base / "plan.json")
        if summary.get("batch_error") or summary.get("not_run") or len(summary["records"]) != 22:
            raise ValueError("shard is not a completed 22-key run")
        if {row["key"] for row in summary["records"]} != {row["key"] for row in plan["apps"]}:
            raise ValueError("summary differs from planned shard")
        attempts = {}
        for path in sorted((root / shard).glob("*/*/summary.json")):
            previous = u6.read(path)
            audit.append(dict(source=str(path.relative_to(root)), sha256=u6.sha(path),
                              records=len(previous.get("records", [])), batch_error=previous.get("batch_error"),
                              not_run=previous.get("not_run", []), selected=path == base / "summary.json"))
        for path in sorted((root / shard).glob("*/*/*/record.json")):
            record = u6.read(path)
            attempts.setdefault(record["key"], []).append(dict(record=str(path.relative_to(root)),
                                                             clicked_at=record.get("clicked_at"), sha256=u6.sha(path)))
        runtime = u6.inventory(base / "runtime-fingerprint.txt")
        boot = u6.inventory(base / "boot-image-fingerprint.txt")
        for name in ["summary.json", "plan.json", "baseline.json", "facts.txt", "runtime-fingerprint.txt", "boot-image-fingerprint.txt"]:
            pins[str((base / name).relative_to(root))] = u6.sha(base / name)
        for original in sorted(summary["records"], key=lambda row: row["key"]):
            key = original["key"]
            folder = base / key
            record, events, pids, reports, disappeared, binding = u6.first_fatal.load_run(folder)
            if record != original or record["serial"] != plan["serial"]:
                raise ValueError("summary record or serial mismatch")
            record_relative = str((folder / "record.json").relative_to(root))
            first = first_attempt(record_relative, attempts[key])
            issues = identity_issues(record, runtime, boot, expected, predictions[key], plan["tool"])
            if not first or record.get("clicked_at", 0) <= frozen_time:
                issues.append("not-first-post-freeze-attempt")
            shots = [shot for shot in record.get("screenshots", []) if shot.get("captured") and shot.get("scheduled_seconds") == 20]
            if len(shots) != 1 or u6.sha(folder / "t20.jpeg") != shots[0]["sha256"]:
                raise ValueError("need one unchanged t20 capture")
            shot = shots[0]
            cutoff = datetime.fromtimestamp(int(shot["remote_stat"].split()[1]), timezone(timedelta(hours=8))).strftime("%m-%d %H:%M:%S") + ".999"
            start = datetime.fromtimestamp(record["clicked_at"], timezone(timedelta(hours=8))).strftime("%m-%d %H:%M:%S") + ".000"
            bounded = [event for event in events if event["timestamp"] >= start]
            termination = u6.first_fatal.analyze(bounded, pids, reports, disappeared, registry, registry["context"], cutoff)
            full = u6.first_fatal.analyze(bounded, pids, reports, disappeared, cutoff=None)
            complete = bool((record.get("diagnostics") or {}).get("complete") and binding["diagnostic_hash_verified"])
            readback = folder / "installed-apk.sha256"
            installed_apk_hash = readback.read_text().split()[0] if readback.is_file() and readback.read_text().split() else None
            rows.append(dict(key=key, shard=shard, record=record_relative, record_sha256=binding["record_sha256"],
                             hilog_sha256=binding["hilog_sha256"], target_pids=sorted(pids), binding_lines=binding["binding_lines"],
                             prediction=predictions[key], first_attempt=first, attempts=attempts[key],
                             identity_verified=not issues, issues=issues, metadata_sha256=record.get("input_sha256"),
                             observed_input=u6.app_identity(record), runtime_count=len(runtime), boot_count=len(boot),
                             tool=plan["tool"], log_complete=complete, interval=dict(start=start, cutoff=cutoff),
                             t20_sha256=shot["sha256"], t20_path=str((folder / "t20.jpeg").relative_to(root)),
                             t20_elapsed_seconds=shot.get("elapsed_seconds"), t20_foreground_confirmed=bool((shot.get("foreground") or {}).get("confirmed")),
                             termination=compact_terminal(termination), full_log_termination_observation_only=compact_terminal(full),
                             installation=dict(success_text=record["install"].get("success_text"), native_assembly_status=(record.get("native_assembly") or {}).get("status"),
                                               installed_apk_sha256=installed_apk_hash, readback_sha256=u6.sha(readback) if readback.is_file() else None),
                             process_receipts={name: u6.sha(folder / name) for name in ["processes-t5.txt", "processes-t20.txt"] if (folder / name).is_file()}))
    if len({row["key"] for row in rows}) != len(rows):
        raise ValueError("duplicate key across shards")
    return dict(status="prepared-not-outer-signed", prediction_sha256=CSV_SHA, selection=selection,
                selected_keys=len(rows), missing_keys=sorted(set(predictions) - {row["key"] for row in rows}),
                frozen_pins_checked=len(frozen["files"]), source_pins=pins, aborted_run_audit=audit,
                first_fatal_sha256=u6.sha(ROOT / "scripts/lab/first_fatal.py"), noise_registry_sha256=u6.sha(u6.benign.REGISTRY),
                noise_policy="historical registry used only to annotate nearby context; raw terminal and root selection unaffected",
                rows=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT.parent / "westlake-harness-wiki/benchmark/2026-10-01-u7-sweep")
    parser.add_argument("--selection", type=Path, default=HERE / "SELECTION.json")
    args = parser.parse_args()
    print(u6.encoded(prepare(args.root.resolve(), u6.read(args.selection))), end="")


if __name__ == "__main__":
    main()
