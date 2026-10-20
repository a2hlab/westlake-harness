#!/usr/bin/env python3
"""Narrow recipe/ELF checks; no compiler or device invocation."""
import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path

import build
import jni_tables


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bridge", type=Path, required=True)
    ap.add_argument("--symbols", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    passed = []
    def refuses(name, fn):
        try:
            fn()
        except ValueError:
            passed.append(name)
            return
        raise AssertionError(name + " accepted")
    refuses("empty_abi", lambda: build.compare_abi("", ""))
    sample = ("  1: 0000000000001000 16 FUNC GLOBAL DEFAULT 1 exported@@LIBC\n"
              "  0x1 (NEEDED) Shared library: [libc.so]\n")
    build.compare_abi(sample, sample, 1)
    passed.append("nonempty_exact_abi")
    refuses("wrong_export_version", lambda: build.compare_abi(sample, sample.replace("@@LIBC", "@@OTHER")))
    refuses("missing_dependency", lambda: build.compare_abi(sample, sample.splitlines()[0]))
    refuses("wrong_export_count", lambda: build.compare_abi(sample, sample, 78))
    tables = jni_tables.inspect(a.bridge.read_bytes(), a.symbols.read_text())
    assert build.sha(a.bridge) == build.BASE_BRIDGE
    assert [len(v["entries"]) for v in tables.values()] == [12, 4]
    jni_tables.compare(tables, tables)
    passed.append("actual_dca_12_plus_4_jni")
    changed = copy.deepcopy(tables)
    next(iter(changed.values()))["entries"][0]["signature"] = "()WRONG"
    refuses("jni_signature_drift", lambda: jni_tables.compare(tables, changed))
    pending = a.out/"pending.json"
    pending.write_text(json.dumps({"status": "DRAFT"})+"\n")
    argv = [sys.executable, str(Path(__file__).with_name("build.py"))]
    for arg in ("repo", "sdk", "bridge-inputs", "bridge-base", "shim-base", "consumer"):
        argv += ["--"+arg, str(a.out/"not-an-input")]
    target = a.out/"must-not-exist"
    argv += ["--consumer-pins", str(pending), "--out", str(target), "--execute"]
    (a.out/"pending.argv.json").write_text(json.dumps(argv, indent=2)+"\n")
    with (a.out/"pending.stdout").open("wb") as o, (a.out/"pending.stderr").open("wb") as e:
        rc = subprocess.run(argv, stdout=o, stderr=e).returncode
    (a.out/"pending.rc").write_text(str(rc)+"\n")
    assert rc != 0 and not target.exists()
    assert "consumer not final" in (a.out/"pending.stderr").read_text()
    passed.append("pending_consumer_refused_before_output_or_compile")
    result = {"status": "PREPARATION_CHECKS_PASS_NOT_PRODUCTION",
              "cases": passed, "bridge_sha256": build.sha(a.bridge),
              "compiler_calls": 0, "device_calls": 0}
    (a.out/"result.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
