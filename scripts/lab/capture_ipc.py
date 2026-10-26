#!/usr/bin/env python3
"""Record every binder call an app makes from cold start, on a real Android reference.

    capture_ipc.py --transport adb:<serial>        --package <pkg> --out <dir> [--settle 20]
    capture_ipc.py --transport tcp:127.0.0.1:25599 --package <pkg> --out <dir>

Force-stops the app, starts `am trace-ipc`, cold-starts the app's launcher activity with `am start -W`,
waits --settle seconds, stops tracing into a dump on the device and copies it to <dir>/ipc-trace.txt with
<dir>/capture.json (device build, app version, launch time). Feed the dump to
`westlake-apk-gap ipc-observe`.

Transports: `adb:<serial>` for a phone; `tcp:<host>:<port>` for a raw shell listening on a socket, which is
how the Husk LineageOS 23 / Android 16 guest exposes its shell (guest port 5599, forwarded to the host).
Both run the same `/system/bin/sh` commands as the shell user; nothing on the device needs root.
"""
from __future__ import annotations

import argparse
import json
import shlex
import socket
import subprocess
import sys
import time
from pathlib import Path

END = "__WESTLAKE_IPC_END__"


class Shell:
    def __init__(self, transport: str, timeout: float) -> None:
        kind, _, rest = transport.partition(":")
        if kind not in {"adb", "tcp"} or not rest:
            sys.exit(f"--transport must be adb:<serial> or tcp:<host>:<port>, not {transport!r}")
        self.kind, self.target, self.timeout = kind, rest, timeout

    def run(self, command: str, timeout: float | None = None) -> str:
        timeout = timeout or self.timeout
        if self.kind == "adb":
            done = subprocess.run(["adb", "-s", self.target, "shell", command], capture_output=True,
                                  text=True, errors="replace", timeout=timeout)
            return done.stdout
        host, _, port = self.target.rpartition(":")
        with socket.create_connection((host, int(port)), timeout=timeout) as conn:
            conn.sendall(f"{command}\necho {END}\n".encode())
            out, start = b"", time.time()
            while END.encode() not in out and time.time() - start < timeout:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                out += chunk
        return out.decode(errors="replace").replace(END, "").rstrip("\n") + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--transport", required=True, help="adb:<serial> or tcp:<host>:<port>")
    ap.add_argument("--package", required=True)
    ap.add_argument("--activity", help="component to start; default: the package's launcher activity")
    ap.add_argument("--settle", type=float, default=20, help="seconds to keep tracing after am start returns")
    ap.add_argument("--timeout", type=float, default=600, help="per-command timeout; emulated devices are slow")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    sh = Shell(args.transport, args.timeout)
    pkg = shlex.quote(args.package)
    activity = args.activity or sh.run(
        f"cmd package resolve-activity --brief -c android.intent.category.LAUNCHER {pkg} | tail -1").strip()
    if "/" not in activity:
        sys.exit(f"no launcher activity for {args.package}: {activity!r}")
    dump = f"/data/local/tmp/ipc-{args.package}.txt"

    sh.run(f"am force-stop {pkg}; rm -f {dump}")
    sh.run("am trace-ipc start")
    started = time.time()
    launch = sh.run(f"am start -W -n {shlex.quote(activity)}")
    time.sleep(args.settle)
    sh.run(f"am trace-ipc stop --dump-file {dump}")
    elapsed = time.time() - started
    text = sh.run(f"cat {dump}")
    if "Traces for process:" not in text:
        sys.exit(f"no trace-ipc dump came back from {dump}")

    def prop(name: str) -> str:
        return sh.run(f"getprop {name}").strip()

    version = sh.run(f"dumpsys package {pkg} | grep -m2 -E 'versionName|versionCode'")
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "ipc-trace.txt").write_text(text)
    record = {
        "package": args.package,
        "activity": activity,
        "transport": args.transport.split(":", 1)[0],
        "device": {
            "fingerprint": prop("ro.build.fingerprint"),
            "release": prop("ro.build.version.release"),
            "sdk": prop("ro.build.version.sdk"),
            "abi": prop("ro.product.cpu.abi"),
        },
        "app_version": " ".join(version.split()),
        "am_start": {k: v.strip() for k, _, v in
                     (line.partition(":") for line in launch.splitlines() if ":" in line)},
        "settle_seconds": args.settle,
        "traced_seconds": round(elapsed, 1),
        "processes_in_dump": text.count("Traces for process:"),
    }
    (args.out / "capture.json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"{args.package}: {record['processes_in_dump']} processes in dump, "
          f"TotalTime {record['am_start'].get('TotalTime', '?')} ms -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
