#!/usr/bin/env python3
"""Offline N1/N2 build and deployment preflight; exit 0/1/3 = pass/wall/invalid."""

import argparse
import json
from pathlib import Path
import subprocess

from native_gate_common import Package, apply_exceptions, load_inputs, read_json, sha256
import native_initialization_gate
import native_needed_gate


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXCEPTIONS = ROOT / "knowledge/gates/native-predeploy-exceptions.json"


def check_package(package_path, inputs_path, gate="all", exceptions=DEFAULT_EXCEPTIONS, readelf="llvm-readelf"):
    report = dict(schema_version=1, device_access=False, status="INVALID", exit_code=3, gates={}, errors=[])
    try:
        if gate not in {"N1", "N2", "all"}:
            raise ValueError("unknown gate")
        package = Package(package_path)
        inputs, root, inputs_sha = load_inputs(package, inputs_path)
        registry = read_json(exceptions)
        report.update(package_manifest_sha256=package.sha256, inputs_sha256=inputs_sha,
                      exceptions_sha256=sha256(exceptions))
        for selected in (["N1", "N2"] if gate == "all" else [gate]):
            try:
                if selected == "N1":
                    findings, details = native_initialization_gate.check(package, inputs, root)
                else:
                    findings, details = native_needed_gate.check(package, inputs, root, readelf)
                decision = apply_exceptions(selected, findings, package.sha256, inputs_sha, registry)
                report["gates"][selected] = dict(details=details, **decision)
            except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError, ImportError, subprocess.SubprocessError) as error:
                report["errors"].append(dict(gate=selected, error=str(error)))
        if not report["errors"]:
            rejected = sum(result["rejected"] for result in report["gates"].values())
            report.update(status="REJECT" if rejected else "PASS", exit_code=int(bool(rejected)))
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError, ImportError, subprocess.SubprocessError) as error:
        report["errors"].append(dict(gate="inputs", error=str(error)))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--gate", choices=["N1", "N2", "all"], default="all")
    parser.add_argument("--exceptions", type=Path, default=DEFAULT_EXCEPTIONS)
    parser.add_argument("--readelf", default="llvm-readelf")
    args = parser.parse_args(argv)
    report = check_package(args.package, args.inputs, args.gate, args.exceptions, args.readelf)
    print(json.dumps(report, indent=2))
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
