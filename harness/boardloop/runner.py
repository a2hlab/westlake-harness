"""Board-loop launcher: run a corpus through probe_source_app.py, one worker per board.

Each app is launched once per assigned board with a fresh run id; the record keeps the run id,
the runtime lock the launch was taken against, and the APK's sha256, so a later stage-ladder
verdict can always be traced to exact bits. Boards never collide: apps are dealt round-robin
over the board serials and each worker owns its serial for the whole run.

--dry-run prints the command list and touches no device.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

CHILD_LOG = "/data/service/el1/public/appspawnx/adapter_child_{pid}.stderr"
FAULTLOG_GLOB = "/data/log/faultlog/temp/cppcrash-{pid}-*"
TAP_CHANNEL = "/data/local/tmp/noice_tap.{pid}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepared_input(args: argparse.Namespace, app_key: str) -> Path:
    """The prepare_app.py output directory probe_source_app.py expects for this app.

    probe_source_app.py reads <app-input>/app-input.json (manifest tools/probe_source_app.py),
    so the raw APK/XAPK path from the corpus is never the right value: the prepared directory
    under --prepared-root is. A missing directory (or one without app-input.json) is reported
    rather than launching, since a launch against an unprepared input can only fail downstream.
    """
    prepared = Path(args.prepared_root) / app_key
    if not (prepared / "app-input.json").exists():
        raise FileNotFoundError(
            f"{app_key}: no prepared input at {prepared} (missing app-input.json); "
            f"run prepare_all.py {args.manifest} <inputs> {args.prepared_root} first")
    return prepared


def launch_command(args: argparse.Namespace, app_key: str, app: dict[str, Any],
                   serial: str, out: Path) -> list[str]:
    """The exact probe_source_app.py invocation for one app on one board."""
    return [
        sys.executable, str(args.manifest / "tools" / "probe_source_app.py"),
        "--workspace", str(args.workspace),
        "--westlake-source", str(args.westlake_source),
        "--framework-report", str(args.framework_report),
        "--app-input", str(prepared_input(args, app_key)),
        "--app", app_key,
        "--hdc", args.hdc,
        "--serial", serial,
        "--out", str(out),
    ]


def view_tree_from_log(lines: list[str]) -> list[str]:
    """Widget lines out of a tap-channel view-tree dump: geometry-bearing rows only."""
    return [line for line in lines if "rect=[" in line]


def run_app(args: argparse.Namespace, app_key: str, app: dict[str, Any],
            serial: str, run_dir: Path, run_id: str) -> dict[str, Any]:
    """Launch one app on one board and record the §10 evidence bundle."""
    from . import blockers, stages  # local import: keep --dry-run free of harness deps

    out = run_dir / app_key
    record: dict[str, Any] = {
        "app": app_key, "package": app.get("package"), "version": app.get("version"),
        "run_id": run_id, "serial": serial,
        "apk_sha256": sha256(Path(app["input"])),
        "runtime_lock": str(args.runtime_lock) if args.runtime_lock else None,
        "launched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    command = launch_command(args, app_key, app, serial, out)
    record["command"] = command
    if args.dry_run:
        return {**record, "verdict": "dry-run"}

    proc = subprocess.run(command, cwd=args.manifest, capture_output=True, text=True,
                          timeout=args.launch_timeout)
    report_path = out / "device-report.json"
    if proc.returncode != 0 or not report_path.exists():
        return {**record, "verdict": "launch-failed",
                "detail": (proc.stdout + proc.stderr).strip()[-300:]}

    report = json.loads(report_path.read_text())
    child = report.get("child")
    device = _Device(args.hdc, serial)
    child_log = device.shell(f"cat {CHILD_LOG.format(pid=child)} 2>/dev/null")
    # View tree over the tap channel ('v' dump), then RenderService visible nodes — the two
    # independent §10 oracles; a screenshot is deliberately not among them.
    device.shell(f"echo v > {TAP_CHANNEL.format(pid=child)}")
    time.sleep(args.vt_wait)
    view_tree = view_tree_from_log(
        device.shell(f"cat {CHILD_LOG.format(pid=child)} 2>/dev/null").splitlines())
    rs_raw = device.shell("hidumper -s RenderService -a RSTree 2>/dev/null")
    pkg = re_escape(app.get("package") or "")
    rs_visible = sum(1 for line in rs_raw.splitlines()
                     if pkg and pkg in line and "Visible: 1" in line) if pkg else None
    faultlog = device.shell(f"cat {FAULTLOG_GLOB.format(pid=child)} 2>/dev/null")

    gap_map = json.loads(args.gap_map.read_text()) if args.gap_map else None
    record["stages"] = stages.judge(child_log, view_tree, rs_visible)
    record["first_blocker"] = blockers.classify(child_log, faultlog, gap_map)
    record["verdict"] = "done"
    return record


def re_escape(text: str) -> str:
    return text  # substring match only; kept as a seam so escaping policy lives in one place


class _Device:
    """Read-only board access for evidence collection (writes stay inside probe_source_app)."""

    def __init__(self, hdc: str, serial: str):
        self.transport = [hdc, "-t", serial]

    def shell(self, command: str, timeout: int = 120) -> str:
        done = subprocess.run(self.transport + ["shell", command], stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=timeout)
        return done.stdout.replace("\r", "")


def _worker(args: argparse.Namespace, serial: str, jobs: "queue.Queue[tuple[str, dict]]",
            run_dir: Path, run_id: str, results: list[dict[str, Any]],
            lock: threading.Lock) -> None:
    while True:
        try:
            app_key, app = jobs.get_nowait()
        except queue.Empty:
            return
        record = run_app(args, app_key, app, serial, run_dir, run_id)
        with lock:
            results.append(record)
            (run_dir / f"{app_key}.json").write_text(json.dumps(record, indent=1) + "\n")


def summarize(results: list[dict[str, Any]]) -> str:
    head = "%-24s %-8s %-4s %-4s %-4s %-4s  %s" % (
        "app", "verdict", "P2", "P3", "P4a", "P4b", "first blocker")
    lines = [head, "-" * len(head)]
    for r in sorted(results, key=lambda r: r["app"]):
        st = r.get("stages", {})
        fb = r.get("first_blocker", {})
        blocker = fb.get("gap_row") or fb.get("identity") or r.get("verdict", "-")
        lines.append("%-24s %-8s %-4s %-4s %-4s %-4s  %s" % (
            r["app"], r.get("verdict", "-"), st.get("P2", "-"), st.get("P3", "-"),
            st.get("P4a", "-"), st.get("P4b", "-"), str(blocker)[:60]))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpus", required=True, type=Path, help="corpus JSON with an 'apps' map")
    parser.add_argument("--manifest", required=True, type=Path, help="launcher repo with tools/")
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--westlake-source", required=True, type=Path)
    parser.add_argument("--framework-report", required=True, type=Path,
                        help="per-board device-report.json from probe_framework_vm.py")
    parser.add_argument("--hdc", required=True)
    parser.add_argument("--prepared-root", required=True, type=Path,
                        help="prepare_all.py output root; each app launches with "
                             "<prepared-root>/<key> as --app-input")
    parser.add_argument("--serials", required=True, nargs="+",
                        help="one worker per board serial; apps are dealt round-robin")
    parser.add_argument("--runtime-lock", type=Path, help="runtime lock this run is taken against")
    parser.add_argument("--gap-map", type=Path, help="gap map JSON for blocker->row mapping")
    parser.add_argument("--runs", type=Path, default=Path("runs"), help="runs root directory")
    parser.add_argument("--run-id", help="defaults to UTC timestamp")
    parser.add_argument("--launch-timeout", type=int, default=1200)
    parser.add_argument("--vt-wait", type=float, default=8.0,
                        help="seconds to let the view-tree dump land after writing 'v'")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the command list; touch no device")
    args = parser.parse_args(argv)

    corpus = json.loads(args.corpus.read_text())["apps"]
    run_id = args.run_id or datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.runs / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    jobs: "queue.Queue[tuple[str, dict]]" = queue.Queue()
    for item in sorted(corpus.items()):
        jobs.put(item)

    if args.dry_run:
        serials = list(args.serials)
        for index, (app_key, app) in enumerate(sorted(corpus.items())):
            serial = serials[index % len(serials)]
            print(" ".join(launch_command(args, app_key, app, serial, run_dir / app_key)))
        print(f"# {len(corpus)} apps over {len(serials)} board(s), run id {run_id} (dry-run)")
        return 0

    results: list[dict[str, Any]] = []
    lock = threading.Lock()
    threads = [threading.Thread(target=_worker,
                                args=(args, serial, jobs, run_dir, run_id, results, lock),
                                daemon=True)
               for serial in args.serials]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    summary = summarize(results)
    (run_dir / "SUMMARY.txt").write_text(summary + "\n")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
