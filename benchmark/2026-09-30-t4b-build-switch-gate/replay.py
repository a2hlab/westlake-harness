#!/usr/bin/env python3
"""Replay actual local evidence; never synthesize a historical build receipt."""
import argparse
import csv
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location("t4b_gate", ROOT / "knowledge/toolchains/art-r155/t4b_build_switch_gate.py")
sys.path.insert(0, str(ROOT / "knowledge/toolchains/art-r155"))
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspaces", type=Path, default=Path(os.environ.get("WORKSPACES", ROOT.parent)))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--include-t5b", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    base = args.workspaces / "westlake-generation-v3c-candidate/payload/android"
    native = base / "lib64/libart.so"
    cases = {
        "v3c": (base / "framework/arm64/boot.oat", None,
                 "25d92cf7df9c86ca4bbc81c1e2f44a5c6c64798506247239e07a30f651b9e78c", "pass", 3),
        "t5": (args.workspaces / "_hw248-t5/arm64/boot.oat", HERE / "evidence/T3-BUILD.md",
               "08837079ac97bbec25a804fc1916e5973911b8dd58733a57f8e5f52d5c9da6c9", "fail", 2),
    }
    if args.include_t5b:
        cases["t5b"] = (args.workspaces / "_hw248-t5b/arm64/boot.oat",
                        HERE / "evidence/T3b-BUILD-final-snapshot.md",
                        "90f827190482b849f71bceb9ab3d2482c8b42adf70b8b084af887728cb43f248", "pass", 3)
    summary = dict(generated_at=datetime.now(timezone.utc).isoformat(), cases={},
                   board_commands=0, t5b="included" if args.include_t5b else "not_requested",
                   scope="Actual artifact controls; no synthetic historical BUILD.md")
    exceptions = []
    for name, (image, build, expected_sha, expected_consistency, expected_exit) in cases.items():
        if gate.sha(native.read_bytes()) != gate.LIBART_SHA or gate.sha(image.read_bytes()) != expected_sha:
            raise ValueError(f"{name}: replay artifact identity differs")
        report = gate.check(native, image, build)
        report["source_paths"] = dict(libart=str(native.relative_to(args.workspaces)),
                                      oat=str(image.relative_to(args.workspaces)),
                                      build=str(build.relative_to(HERE)) if build else None)
        if report["consistency"] != expected_consistency or report["exit_code"] != expected_exit:
            raise ValueError(f"{name}: unexpected result {report['verdict']}")
        (args.out / (name + ".json")).write_text(json.dumps(report, indent=2) + "\n")
        summary["cases"][name] = {key: report[key] for key in
                                   ["consistency", "verdict", "exit_code", "deploy_allowed", "inputs"]}
        summary["cases"][name].update(mismatches=len(report["mismatches"]),
                                      exceptions=len(report["exceptions"]))
        exceptions.extend(dict(case=name, **row) for row in report["exceptions"])
    (args.out / "results.json").write_text(json.dumps(summary, indent=2) + "\n")
    with (args.out / "exceptions.csv").open("w") as output:
        writer = csv.DictWriter(output, fieldnames=["case", "field", "evidence", "review"])
        writer.writeheader()
        writer.writerows(exceptions)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
