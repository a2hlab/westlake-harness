#!/usr/bin/env python3
"""Compile and exercise the production reader; preserve each actual invocation."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def run(argv, out, name, timeout):
    part = out / name
    part.mkdir()
    record = {"argv": list(map(str, argv)), "cwd": str(ROOT), "start": stamp()}
    (part / "command.json").write_text(json.dumps(record, indent=2) + "\n")
    start = time.monotonic()
    with (part / "stdout").open("wb") as stdout, (part / "stderr").open("wb") as stderr:
        try:
            result = subprocess.run(argv, cwd=ROOT, stdout=stdout, stderr=stderr, timeout=timeout)
            rc = result.returncode
        except subprocess.TimeoutExpired:
            rc = 124
            record["timeout"] = True
        except OSError as error:
            rc = 127
            stderr.write(str(error).encode())
    record.update(end=stamp(), elapsed_seconds=time.monotonic()-start, rc=rc,
                  stdout_sha256=sha(part/"stdout"), stderr_sha256=sha(part/"stderr"))
    (part / "receipt.json").write_text(json.dumps(record, indent=2) + "\n")
    if rc:
        raise RuntimeError(f"{name} rc={rc}; preserved at {part}")
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    out = args.out or ROOT / ".private" / ("run-" + uuid.uuid4().hex)
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    lock = json.loads((ROOT / "dependency-lock.json").read_text())
    if sha(ROOT / lock["vendored"]) != lock["sha256"]:
        raise RuntimeError("JSON dependency SHA mismatch")
    compiler = shutil.which(os.environ.get("CXX", "clang++"))
    if not compiler:
        raise RuntimeError("CXX/clang++ unavailable; no download or fallback")
    sources = [ROOT / "host_window_record_reader.cpp", ROOT / "tests/reader_test.cpp"]
    inputs = sources + [ROOT / "host_window_record_reader.h", ROOT / lock["vendored"],
                        ROOT / "dependency-lock.json", ROOT / "run_tests.py"]
    pins = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    (out / "inputs.json").write_text(json.dumps(pins, indent=2) + "\n")
    run([compiler, "--version"], out, "compiler-version", 10)
    compile_record = run([compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-pedantic",
                          "-I", str(ROOT), *map(str, sources), "-o", str(out / "reader-test")],
                         out, "compile", 120)
    test_record = run([str(out / "reader-test"), str(out / "fixtures")], out, "test", 10)
    if pins != {str(p.relative_to(ROOT)): sha(p) for p in inputs}:
        raise RuntimeError("source changed while running")
    counts = json.loads((out / "test/stdout").read_text().splitlines()[-1])
    result = {"status": "offline_tests_passed", "counts": counts,
              "compile_rc": compile_record["rc"], "test_rc": test_record["rc"],
              "inputs": pins, "compiler_sha256": sha(Path(compiler)),
              "executable_sha256": sha(out / "reader-test"),
              "device_operations": 0, "runtime_bridge_builds": 0}
    (out / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"out": str(out), **result}))


if __name__ == "__main__":
    main()
