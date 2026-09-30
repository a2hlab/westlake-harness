#!/usr/bin/env python3
"""Capture a real offline package check; never treats capture success as gate PASS."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/lab"))
from native_gate_common import Package, read_json, sha256
from native_predeploy import check_package


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--readelf", default="llvm-readelf")
    args = parser.parse_args()
    output = args.out.resolve()
    input_root = args.inputs.resolve().parent
    if output.exists() or output.is_relative_to(input_root):
        raise ValueError("capture requires a new output directory outside the input tree")
    result = check_package(args.package, args.inputs, readelf=args.readelf)
    if result["errors"] or "N2" not in result["gates"]:
        raise ValueError("capture has invalid inputs: " + str(result["errors"]))
    output.mkdir(parents=True)
    shutil.copytree(input_root, output / "inputs")
    shutil.copy2(args.package / "package.json", output / "candidate-package.json")
    save(output / "current-gate.json", result)
    package = Package(args.package)
    inputs = read_json(args.inputs)
    namespaces_path = input_root / inputs["namespaces"]["manifest"]["path"]
    namespaces = read_json(namespaces_path)
    evidence = []
    for entry in result["gates"]["N2"]["details"]["readelf_evidence"]:
        relative = "readelf/" + entry["sha256"] + ".txt"
        path = output / relative
        path.parent.mkdir(exist_ok=True)
        path.write_text(entry["stdout"])
        evidence.append(dict(path=relative, sha256=sha256(path), artifact_sha256=entry["sha256"],
                             package_path=entry["package_path"]))
    virtual = {name: {key: value for key, value in record.items() if key != "path"}
               for name, record in package.virtual_files().items()}
    sources = [dict(path=str(Path("inputs") / namespaces_path.parent.relative_to(input_root) / entry["path"]),
                    sha256=entry["sha256"]) for entry in namespaces["config_sources"]]
    findings = [{key: value for key, value in row.items() if key not in {"issue_id", "disposition", "exception"}}
                for row in result["gates"]["N2"]["findings"]]
    save(output / "needed-replay.json", dict(schema_version=1, package_manifest_sha256=package.sha256,
         domains=namespaces["domains"], virtual_files=virtual, config_sources=sources,
         readelf_evidence=evidence, findings=findings))
    executable = shutil.which(args.readelf)
    version = subprocess.run([args.readelf, "--version"], capture_output=True, text=True, check=True)
    save(output / "capture.json", dict(package=args.package.name, package_manifest_sha256=package.sha256,
         inputs_sha256=sha256(args.inputs), gate_exit=result["exit_code"], readelf_sha256=sha256(executable),
         readelf_version=version.stdout, code_sha256={str(path.relative_to(ROOT)): sha256(path)
            for path in sorted((ROOT / "scripts/lab").glob("native_*.py"))}))
    print(json.dumps(dict(captured=True, gate_status=result["status"], gate_exit=result["exit_code"])))


if __name__ == "__main__":
    main()
