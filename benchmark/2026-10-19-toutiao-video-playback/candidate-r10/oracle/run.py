#!/usr/bin/env python3
"""Compile supplied mirror source(s) against mocks; never build/deploy a DSO."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

CASES = ["mixed", "filtered-n", "alias-n", "limit-4095", "limit-4096", "limit-4097",
         "concurrent", "long", "long-format", "errno-m", "positional", "write-error",
         "short-write", "null-tag", "filtered-n-after-cap", "alias-n-after-cap"]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, action="append", required=True)
    p.add_argument("--out", type=Path, required=True, help="Fresh output directory")
    p.add_argument("--cc", default="cc")
    p.add_argument("--include-dir", type=Path, action="append", default=[])
    a = p.parse_args()
    here = Path(__file__).resolve().parent
    repo = next(x for x in here.parents if (x / "AGENTS.md").is_file())
    sources = [s.resolve(strict=True) for s in a.source]
    cc = shutil.which(a.cc)
    if not cc:
        p.error("compiler not found")
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    relative = lambda x: os.path.relpath(x, repo)
    sha = lambda x: hashlib.sha256(Path(x).read_bytes()).hexdigest()
    commands = []

    def execute(label, argv):
        r = subprocess.run(argv, cwd=repo, capture_output=True, timeout=30)
        stdout, stderr = out / (label + ".stdout"), out / (label + ".stderr")
        stdout.write_bytes(r.stdout)
        stderr.write_bytes(r.stderr)
        row = dict(label=label, argv=[relative(Path(v)) if v.startswith("/") else v for v in argv], rc=r.returncode,
                   stdout_sha256=sha(stdout), stderr_sha256=sha(stderr))
        commands.append(row)
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        return r.returncode

    objects = []
    ok = True
    for i, source in enumerate(sources):
        obj = out / f"source-{i}.o"
        argv = [cc, "-std=c11", "-Wall", "-Wextra", "-pthread", "-O0", "-g",
                "-include", relative(here / "mock.h"),
                "-Dwrite=oracle_write", "-D__android_log_vprint=oracle_vprint"]
        for directory in a.include_dir:
            argv += ["-I", relative(directory.resolve())]
        argv += ["-c", relative(source), "-o", relative(obj)]
        if execute(f"compile-{i}", argv):
            ok = False
            break
        objects.append(relative(obj))
    executable = out / "oracle"
    if ok:
        ok = execute("link", [cc, "-std=c11", "-Wall", "-Wextra", "-pthread", "-O0", "-g",
                              relative(here / "oracle.c"), *objects,
                              "-o", relative(executable)]) == 0
    results = []
    if ok:
        # Separate processes reset candidate-private static state without test hooks.
        for case in CASES:
            rc = execute(case, [relative(executable), case])
            results.append({"case": case, "rc": rc})
    report = {
        "scope": "HOST_MOCK_BEHAVIOR_ONLY_NOT_PRODUCTION_ABI_OR_PROVIDER",
        "sources": [{"path": relative(s), "sha256": sha(s)} for s in sources],
        "compiler": {"path": relative(Path(cc)), "sha256": sha(cc)},
        "oracle": {name: sha(here / name) for name in ("oracle.c", "mock.h", "run.py")},
        "compile_link_pass": ok, "cases": results,
        "pass": ok and len(results) == len(CASES) and all(r["rc"] == 0 for r in results),
    }
    (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
