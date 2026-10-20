#!/usr/bin/env python3
"""T27 host-test dispatcher: builds the ONE real host test (test_observer.c) and runs it,
asserting rc 0 and the PASS line. It reuses the single existing C test (no per-scenario test).
Offline, no device. Invoked by the Rust selector tools/spec-checks/tests/toutiao_t27_buffer_observation.rs."""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PASS = "T27 OBSERVER TESTS: PASS"


def main() -> int:
    src = os.path.join(HERE, "test_observer.c")
    with tempfile.TemporaryDirectory() as d:
        binp = os.path.join(d, "test_observer")
        build = subprocess.run(
            ["cc", "-std=c11", "-Wall", "-Wextra", "-Wno-unused-parameter",
             "-I", HERE, src, "-o", binp, "-lpthread"],
            capture_output=True, text=True)
        if build.returncode != 0:
            sys.stderr.write(build.stderr)
            print("T27 build FAIL", file=sys.stderr)
            return 1
        run = subprocess.run([binp], capture_output=True, text=True)
        sys.stdout.write(run.stdout)
        sys.stderr.write(run.stderr)
        if run.returncode != 0 or PASS not in run.stdout:
            print("T27 run FAIL", file=sys.stderr)
            return 1
    print("T27 check OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
