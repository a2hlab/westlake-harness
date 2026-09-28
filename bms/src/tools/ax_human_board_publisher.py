#!/usr/bin/env python3
"""Publish tiny read-only AX snapshots to a remote renderer and retrieve its HTML."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import signal
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def command_output(command: list[str], timeout: float = 8.0) -> str:
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_bundle(args: argparse.Namespace) -> dict[str, Any]:
    results_dir = Path(args.results).expanduser().resolve()
    results = {
        result.stem: str(result)
        for result in results_dir.glob("*.result")
        if result.is_file()
    }
    return {
        "schema_version": 1,
        "published_at": now(),
        "workflow": load_json(Path(args.workflow).expanduser().resolve()),
        "controller": load_json(Path(args.controller_state).expanduser().resolve()),
        "human_todo": Path(args.human_todo).expanduser().resolve().read_text(encoding="utf-8"),
        "orca_raw": command_output(["orca", "terminal", "list", "--json"]),
        "hdc_raw": command_output([args.hdc, "list", "targets", "-v"]),
        "results": results,
    }


def run(command: list[str], timeout: float = 15.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)


def publish_once(args: argparse.Namespace) -> dict[str, Any]:
    bundle = build_bundle(args)
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    remote = f"{args.user}@{args.host}"
    with tempfile.TemporaryDirectory(prefix="ax-human-board-publish-") as raw:
        temp_dir = Path(raw)
        local_bundle = temp_dir / "snapshot.json"
        local_bundle.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
        snapshot_bytes = local_bundle.stat().st_size
        remote_temp = f"{args.remote_root}/inbox/.snapshot.{os.getpid()}.json"
        copied = run(
            ["scp", "-P", str(args.port), "-q", str(local_bundle), f"{remote}:{remote_temp}"]
        )
        if copied.returncode:
            raise RuntimeError(f"snapshot upload failed: {copied.stderr.strip()}")
        promoted = run(
            [
                "ssh", "-p", str(args.port), remote,
                f"mv '{remote_temp}' '{args.remote_root}/inbox/snapshot.json'",
            ]
        )
        if promoted.returncode:
            raise RuntimeError(f"snapshot promotion failed: {promoted.stderr.strip()}")
        local_html = temp_dir / "HUMAN_BOARD.html"
        fetched = run(
            [
                "scp", "-P", str(args.port), "-q",
                f"{remote}:{args.remote_root}/output/HUMAN_BOARD.html",
                str(local_html),
            ]
        )
        fetched_html = fetched.returncode == 0 and local_html.is_file()
        if fetched_html:
            os.replace(local_html, output)
    return {
        "published_at": bundle["published_at"],
        "snapshot_bytes": snapshot_bytes,
        "remote": remote,
        "remote_root": args.remote_root,
        "html_fetched": fetched_html,
        "output": str(output),
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--workflow", required=True)
    value.add_argument("--controller-state", required=True)
    value.add_argument("--results", required=True)
    value.add_argument("--human-todo", required=True)
    value.add_argument("--output", required=True)
    value.add_argument("--host", required=True)
    value.add_argument("--port", type=int, required=True)
    value.add_argument("--user", required=True)
    value.add_argument("--remote-root", required=True)
    value.add_argument("--lock", required=True)
    value.add_argument(
        "--hdc",
        default="/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc",
    )
    sub = value.add_subparsers(dest="command", required=True)
    sub.add_parser("publish")
    watch = sub.add_parser("watch")
    watch.add_argument("--interval", type=float, default=20.0)
    return value


def main() -> int:
    args = parser().parse_args()
    lock_path = Path(args.lock).expanduser().resolve()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("publisher lock already held")
        lock.seek(0)
        lock.truncate()
        lock.write(str(os.getpid()))
        lock.flush()
        if args.command == "publish":
            print(json.dumps(publish_once(args), ensure_ascii=False, indent=2))
            return 0
        stop = False

        def request_stop(_signum: int, _frame: Any) -> None:
            nonlocal stop
            stop = True

        signal.signal(signal.SIGINT, request_stop)
        signal.signal(signal.SIGTERM, request_stop)
        while not stop:
            try:
                print(json.dumps(publish_once(args), ensure_ascii=False), flush=True)
            except Exception as exc:
                print(json.dumps({"published_at": now(), "error": str(exc)}, ensure_ascii=False), flush=True)
            deadline = time.monotonic() + max(args.interval, 1.0)
            while not stop and time.monotonic() < deadline:
                time.sleep(min(0.5, deadline - time.monotonic()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
