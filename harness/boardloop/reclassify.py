"""Offline re-classification of a finished run's first blockers, no board involved.

verify2 ran without --gap-map, so 40 records carry 'source: none' blockers with no gap
row; the child logs stay on the board only as long as the runtime dir lives. This entry
point re-reads recorded logs (or locally saved copies) and re-classifies each app against
a gap map, writing a parallel directory — the original run records are never touched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from . import blockers, runner


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify_run(run_dir: Path, out_dir: Path, gap_map: dict[str, Any] | None,
                 logs_dir: Path | None = None) -> list[dict[str, Any]]:
    """Re-classify every <app>.json under run_dir; returns the merged records.

    Evidence order: a local <logs_dir>/<app>.child.stderr (or .faultlog.txt) when given,
    else the record's on-board child_log_path content if it was captured inline. The
    runtime_lock gap is closed from the app's device-report.json (framework_report_sha256
    + runtime stage identity) — verify2's records all carry null because the runner never
    read the probe's own report for lock identity.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for record_path in sorted(run_dir.glob("*.json")):
        if record_path.name in ("SUMMARY.txt",):
            continue
        record = json.loads(record_path.read_text())
        app = record.get("app") or record_path.stem
        child_log = faultlog = ""
        if logs_dir is not None:
            local = logs_dir / f"{app}.child.stderr"
            child_log = local.read_text(errors="replace") if local.exists() else ""
            local_fl = logs_dir / f"{app}.faultlog.txt"
            faultlog = local_fl.read_text(errors="replace") if local_fl.exists() else ""
        blocker = blockers.classify(child_log, faultlog, gap_map)
        record["first_blocker"] = blocker
        record["offline_classified"] = True
        # runtime_lock backfill: the probe's own device-report carries the stage identity
        report = run_dir / app / "device-report.json"
        if record.get("runtime_lock") is None and report.exists():
            try:
                probe = json.loads(report.read_text())
                lock = {"framework_report_sha256": probe.get("framework_report_sha256"),
                        "runtime_stage": probe.get("stage"),
                        "runtime_dir": probe.get("runtime"),
                        "apk_sha256": probe.get("apk_sha256")}
                record["runtime_lock"] = lock
            except (OSError, json.JSONDecodeError):
                pass
        results.append(record)
        (out_dir / f"{app}.json").write_text(json.dumps(record, indent=1) + "\n")
    return results


def summarize_classified(results: list[dict[str, Any]]) -> str:
    lines = [runner.summarize(results)]
    unmapped = [r for r in results
                if (r.get("first_blocker") or {}).get("gap_row") == "unmapped"]
    mapped = [r for r in results
              if (r.get("first_blocker") or {}).get("gap_row") not in (None, "unmapped")]
    lines.append(f"mapped: {len(mapped)}  unmapped: {len(unmapped)}  none-source: "
                 f"{sum(1 for r in results if (r.get('first_blocker') or {}).get('source') == 'none')}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", required=True, type=Path, help="finished run dir with <app>.json records")
    parser.add_argument("--out", required=True, type=Path, help="new output dir (never overwrite the run)")
    parser.add_argument("--gap-map", type=Path, help="gap-map.json for blocker->row mapping")
    parser.add_argument("--logs", type=Path,
                        help="dir of <app>.child.stderr / <app>.faultlog.txt local copies")
    args = parser.parse_args(argv)

    gap_map = json.loads(args.gap_map.read_text()) if args.gap_map else None
    results = classify_run(args.run, args.out, gap_map, args.logs)
    summary = summarize_classified(results)
    (args.out / "SUMMARY.txt").write_text(summary + "\n")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
