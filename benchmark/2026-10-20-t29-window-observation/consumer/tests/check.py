#!/usr/bin/env python3
"""T29 consumer host-check (the part CC owns and can verify locally, offline, no device).

Two real checks:
  1. LOGGER: build test_observe29c.c and run all 14 modes (concurrency / sink dev-ino / one-write /
     reserved quotas / consumer ref-unref / invalid lane), asserting each prints its PASS line.
  2. PINS: the derived baseline (.orig copies) is byte-identical to the pinned originals.

The REAL consumer-METHOD comparison (phase/called/valid/ref-unref double rc / old->new correlation on
the actual nativeUpdateTexImage/attach/detach/nCreate/nDestroy bodies) runs in the independent base5
fixture (../westlake-harness-api-progress-peer/.../t29-consumer-test-peer/replay.py) against this
tree's derived sources; it is NOT re-implemented here. Invoked by the Rust selector
tools/spec-checks/tests/toutiao_t29_consumer.rs."""
import hashlib
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CONS = os.path.dirname(HERE)                       # .../consumer
LOGGER = os.path.join(CONS, "logger")
TEST = os.path.join(CONS, "test", "test_observe29c.c")
MODES = ["pipe", "fd2_rebind", "sink_drift", "epipe", "eintr", "short", "hot_new",
         "parallel", "reserve", "total", "epochs", "long", "refunref", "invalid_consumer"]
PINS = {
    os.path.join(CONS, "derived", ".orig", "oh_surface_texture_jni.cpp"):
        "c8d3bb700923c393c6e9aad43acf5004dba6d8a168ecfe829d66ec1c9c6f3f61",
    os.path.join(CONS, "derived", ".orig", "oh_texture_view_jni.cpp"):
        "7189e5c2b70af0aa5fff155ca1bb464305f958655e994737dce4ac1878a0558b",
}


def sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def check_pins() -> int:
    for path, want in PINS.items():
        if not os.path.exists(path):
            print(f"T29 PINS FAIL: missing {path}", file=sys.stderr)
            return 1
        got = sha256(path)
        if got != want:
            print(f"T29 PINS FAIL: {path} sha256={got} != pinned {want}", file=sys.stderr)
            return 1
    print("T29 pins OK (derived baseline == pinned originals)")
    return 0


def check_logger() -> int:
    with tempfile.TemporaryDirectory() as d:
        binp = os.path.join(d, "test_observe29c")
        build = subprocess.run(
            ["cc", "-std=c11", "-Wall", "-Wextra", "-Wno-unused-parameter",
             "-fvisibility=hidden", "-I", LOGGER, "-I", os.path.join(CONS, "test"),
             TEST, "-o", binp, "-lpthread"],
            capture_output=True, text=True)
        if build.returncode != 0:
            sys.stderr.write(build.stderr)
            print("T29 logger build FAIL", file=sys.stderr)
            return 1
        for m in MODES:
            # The sink-oriented modes require fd2 to START as a REGULAR FILE (the logger refuses a
            # pipe). Give each run a fresh regular file as stderr; read PASS from stdout (a pipe).
            errf = os.path.join(d, f"stderr_{m}.log")
            with open(errf, "wb") as eh:
                run = subprocess.run([binp, m], stdout=subprocess.PIPE, stderr=eh, text=True)
            if run.returncode != 0 or f"PASS observe29c {m}" not in (run.stdout or ""):
                sys.stderr.write(run.stdout or "")
                with open(errf, "r", errors="replace") as eh:
                    sys.stderr.write(eh.read()[-500:])
                print(f"T29 logger mode FAIL: {m}", file=sys.stderr)
                return 1
        print(f"T29 logger OK ({len(MODES)} modes PASS)")
    return 0


def main() -> int:
    rc = check_pins() or check_logger()
    if rc == 0:
        print("T29 consumer check OK")
    return rc


if __name__ == "__main__":
    sys.exit(main())
