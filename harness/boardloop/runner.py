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
#: The source-closure flow never runs the cfg that creates the CHILD_LOG directory; the child
#: walks child_main.cpp's candidates and lands on <runtime>/private-tmp/ instead. The legacy
#: path stays as a candidate for boards still on the old layout.
CHILD_LOG_PRIVATE_TMP = "{runtime}/private-tmp/adapter_child_{pid}.stderr"
FAULTLOG_GLOB = "/data/log/faultlog/temp/cppcrash-{pid}-*"
TAP_CHANNEL = "/data/local/tmp/noice_tap.{pid}"

#: Screen/board keep-alive around each app (outer loop, verified on the real board): the
#: default 30 s screen timeout locks the panel over the app, and OH backgrounds the host
#: (org.westlake.imehost), zeroing the app's child windows and blackening captures.
HOST_PACKAGE = "org.westlake.imehost"
HOST_ABILITY = "EntryAbility"
WAKE_COMMANDS = ["power-shell wakeup",
                 "power-shell timeout -o 86400000"]  # 2147483647 is silently discarded
UNLOCK_SWIPE = "uinput -T -m 600 1500 600 400 300"  # swipe up: dismiss the lock screen
FOREGROUND_COMMAND = f"aa start -b {HOST_PACKAGE} -a {HOST_ABILITY}"


def child_log_candidates(child_pid: int | None, runtime: str | None) -> list[str]:
    """Where the child's stderr can live, most likely first for this board's layout."""
    if child_pid is None:
        return []
    candidates = []
    if runtime:
        candidates.append(CHILD_LOG_PRIVATE_TMP.format(runtime=runtime, pid=child_pid))
    candidates.append(CHILD_LOG.format(pid=child_pid))
    return candidates


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


def extra_args(app: dict[str, Any]) -> list[str]:
    """Per-app probe arguments from the corpus entry ('extra_args': ["--flag", "value", …]).

    Some apps only run under flags the probe must carry -- toutiao needs its NDK-side
    DSOs routed through the isolated Android ABI namespace
    (--android-native-target libvision_core.so --android-native-target libc++_shared.so).
    Keeping this in the corpus entry keeps the launcher generic and the need per-app
    visible next to the app it belongs to.
    """
    args: list[str] = []
    for flag in app.get("extra_args", []):
        if not isinstance(flag, str):
            raise ValueError(f"extra_args entries must be strings, got {flag!r}")
        args.append(flag)
    return args


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
        *extra_args(app),
    ]


def view_tree_from_log(lines: list[str]) -> list[str]:
    """Widget lines out of a tap-channel view-tree dump: geometry-bearing rows only.

    Both dump eras are accepted: the old one tags rows '[N/OH_InputBridge] VT <widget>'
    (ttwalk.sh matched on 'OH_InputBridge. VT'), the current one drops the tag and starts
    the row with 'VT ' itself ('VT     LinearLayout id=e5c rect=[…]'). What matters for the
    §10 P4a oracle is unchanged: a laid-out widget carries rect=[x,y WxH] with W,H > 0.
    """
    widgets = []
    for line in lines:
        text = line
        if "OH_InputBridge" in text and " VT" in text:
            text = text.split(" VT", 1)[1]
        elif text.lstrip().startswith("VT"):
            pass  # current era: the row itself starts with 'VT '
        # bare widget rows (already-stripped fixtures) pass through unchanged
        if "rect=[" in text:
            widgets.append(text.strip())
    return widgets


def cleanup_commands(hdc: str, serial: str, package: str | None,
                     child_pid: int | None, parent_pid: int | None) -> list[list[str]]:
    """Commands that end the app's on-board processes, child before parent.

    probe_source_app.py spawns parent (`nohup … appspawn-x`, device-report `parent`) and the
    child (`host_spawn`, report `child`) and never ends either — every app leaves both resident
    on the board, accumulating across a corpus run. Pids from the report are the reliable
    handles: the child's comm is only set late in Java init (westlake child_main.cpp
    PR_SET_NAME truncates to 15 chars; AppSpawnXInit setArgV0 later still), so an early-stuck
    or early-crashed app is invisible to `pidof <package>`. pidof remains as the fallback for
    reports that are missing or unparseable. These are board writes, executed only in real
    (non-dry-run) runs after a launch — which itself requires board authorization.
    """
    commands = []
    if child_pid:
        commands.append([hdc, "-t", serial, "shell", f"kill -9 {child_pid} 2>/dev/null"])
    if parent_pid:
        commands.append([hdc, "-t", serial, "shell", f"kill -9 {parent_pid} 2>/dev/null"])
    if package:
        commands.append([hdc, "-t", serial, "shell",
                         f"kill -9 $(pidof {package}) 2>/dev/null"])
    return commands


def report_pids(report_path: Path) -> tuple[int | None, int | None]:
    """(child, parent) pids out of device-report.json; (None, None) when absent or bad."""
    try:
        report = json.loads(report_path.read_text())
        return report.get("child"), report.get("parent")
    except (OSError, json.JSONDecodeError):
        return None, None


def run_cleanup(args: argparse.Namespace, app: dict[str, Any], serial: str,
                child_pid: int | None, parent_pid: int | None) -> list[dict[str, Any]]:
    """Run (or in dry-run, only list) the cleanup commands; each entry records the exit code."""
    executed = []
    for command in cleanup_commands(args.hdc, serial, app.get("package"),
                                    child_pid, parent_pid):
        entry: dict[str, Any] = {"command": " ".join(command)}
        if not args.dry_run:
            done = subprocess.run(command, stdin=subprocess.DEVNULL,
                                  capture_output=True, text=True, timeout=30)
            entry["rc"] = done.returncode
        executed.append(entry)
    return executed


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
        record["cleanup"] = run_cleanup(args, app, serial, None, None)
        return {**record, "verdict": "dry-run"}

    report_path = out / "device-report.json"
    try:
        # Keep the panel lit and the host in front before the launch: the default 30 s
        # screen timeout locks over the app, and OH backgrounds the host, zeroing the app's
        # child windows (outer-loop evidence from the 11-app real-board baseline).
        device = _Device(args.hdc, serial)
        for wake in (*WAKE_COMMANDS, UNLOCK_SWIPE):
            device.shell(wake)
        try:
            proc = subprocess.run(command, cwd=args.manifest, capture_output=True, text=True,
                                  timeout=args.launch_timeout)
        except subprocess.TimeoutExpired as error:
            tail = lambda s: (s or "").strip()[-300:]
            record.update(verdict="launch-timeout",
                          detail={"stdout_tail": tail(error.stdout),
                                  "stderr_tail": tail(error.stderr)})
            return record
        if proc.returncode != 0 or not report_path.exists():
            # Mutate `record` itself (not a {**record} copy): the finally writes cleanup
            # into it, and a copied dict would drop that field from the returned record.
            record.update(verdict="launch-failed",
                          detail=(proc.stdout + proc.stderr).strip()[-300:])
            return record

        # Bring the host back to the foreground after the launch, before collecting
        # evidence — a backgrounded host makes the app's windows 0×0 and captures black.
        device.shell(FOREGROUND_COMMAND)
        report = json.loads(report_path.read_text())
        child = report.get("child")
        child_log = ""
        for candidate in child_log_candidates(child, report.get("runtime")):
            child_log = device.shell(f"cat {candidate} 2>/dev/null")
            if child_log.strip():
                record["child_log_path"] = candidate
                break
        # View tree over the tap channel ('v' dump), then RenderService visible nodes — the
        # two independent §10 oracles; a screenshot is deliberately not among them.
        device.shell(f"echo v > {TAP_CHANNEL.format(pid=child)}")
        time.sleep(args.vt_wait)
        if record.get("child_log_path"):
            refreshed = device.shell(f"cat {record['child_log_path']} 2>/dev/null")
            if refreshed.strip():
                child_log = refreshed
        view_tree = view_tree_from_log(child_log.splitlines())
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
    except Exception as error:
        # An exception mid-collection must not escape to the worker: the finally below
        # still runs cleanup first, and the returned record carries that cleanup — the
        # worker-built fallback record never would (#7 leftover, carried into #9).
        record.update(verdict="runner-error",
                      detail=f"{type(error).__name__}: {error}")
        return record
    finally:
        # Every exit — done, launch-failed, launch-timeout, or an exception mid-collection —
        # cleans up AFTER evidence collection. The report is re-read here (not threaded
        # through the try body) so a timeout still finds the pids save() wrote along the way;
        # a missing/unparseable report falls back to pidof alone.
        child_pid, parent_pid = report_pids(report_path)
        record["cleanup"] = run_cleanup(args, app, serial, child_pid, parent_pid)


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
        # One app's failure must never kill the worker: a dead thread silently drops the
        # rest of this board's queue and shortens the SUMMARY. Every app gets a record.
        try:
            record = run_app(args, app_key, app, serial, run_dir, run_id)
        except Exception as error:  # TimeoutExpired is already handled inside run_app
            record = {"app": app_key, "package": app.get("package"), "run_id": run_id,
                      "serial": serial, "verdict": "runner-error",
                      "detail": f"{type(error).__name__}: {error}"}
        with lock:
            results.append(record)
            (run_dir / f"{app_key}.json").write_text(json.dumps(record, indent=1) + "\n")


def summarize(results: list[dict[str, Any]]) -> str:
    head = "%-24s %-14s %-4s %-4s %-4s %-4s  %s" % (
        "app", "verdict", "P2", "P3", "P4a", "P4b", "first blocker")
    lines = [head, "-" * len(head)]
    for r in sorted(results, key=lambda r: r["app"]):
        st = r.get("stages", {})
        fb = r.get("first_blocker", {})
        blocker = fb.get("gap_row") or fb.get("identity") or r.get("verdict", "-")
        lines.append("%-24s %-14s %-4s %-4s %-4s %-4s  %s" % (
            r["app"], r.get("verdict", "-"), st.get("P2", "-"), st.get("P3", "-"),
            st.get("P4a", "-"), st.get("P4b", "-"), str(blocker)[:60]))
    counts: dict[str, int] = {}
    for r in results:
        counts[r.get("verdict", "?")] = counts.get(r.get("verdict", "?"), 0) + 1
    tally = ", ".join(f"{verdict}={count}" for verdict, count in sorted(counts.items()))
    lines.append(f"total {len(results)}: {tally}")
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
    # Pre-flight: check every prepared input up front and list ALL misses before anything
    # launches — discovering a missing directory mid-run would strand one board's queue.
    missing = []
    for app_key in sorted(corpus):
        try:
            prepared_input(args, app_key)
        except FileNotFoundError as error:
            missing.append(str(error))
    if missing:
        for line in missing:
            print(line, file=sys.stderr)
        print(f"pre-flight failed: {len(missing)}/{len(corpus)} prepared inputs missing; "
              f"no app launched", file=sys.stderr)
        return 1

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
            # Wake/keep-alive before each app, foreground after the launch — printed so a
            # dry-run shows the full real-run sequence on the board.
            for wake in (*WAKE_COMMANDS, UNLOCK_SWIPE):
                print(f"# pre-launch: {args.hdc} -t {serial} shell {wake}")
            print(" ".join(launch_command(args, app_key, app, serial, run_dir / app_key)))
            print(f"# post-launch: {args.hdc} -t {serial} shell {FOREGROUND_COMMAND}")
            # Cleanup runs after every launch, timeout or not -- print it too,
            # so a dry-run shows everything a real run would do on the board.
            for command in cleanup_commands(args.hdc, serial, app.get("package"), None, None):
                print("# cleanup-after-run: " + " ".join(command))
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
