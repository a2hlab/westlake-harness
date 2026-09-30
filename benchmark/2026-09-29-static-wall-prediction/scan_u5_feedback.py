"""Collect portable static facts or replay U5-feedback-v1 forecasts offline."""

import argparse
import concurrent.futures
import csv
import hashlib
import io
import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

from rules85 import elf_info
from rules_u5_feedback import SYMBOLS, aarch64_header, dex_family, predict
from scan_apps import HEADER, INSN

ROOT = Path(__file__).resolve().parents[2]
FROZEN = ROOT / "benchmark/2026-09-30-u4-sweep/J6N4-PREDICTIONS.csv"
FROZEN_SHA = "bae8fd74ffdcba3aa5ea05688fcc0c516169f0b0cfcc29d46249c7352fc6a26d"
VERSION = "u5-feedback-v1"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def library_fact(path, data):
    parsed = elf_info(data)
    return dict(path=path, sha256=digest(data), bytes=len(data), header=parsed["header"],
                needed=sorted(parsed["needed"]), symbol_status=parsed.get("symbol_status", "unknown"),
                imports=[row for row in parsed["imports"] if row["name"] in {pair[0] for pair in SYMBOLS.values()}])


def dex_facts(apk, dexdump):
    inventory, calls = [], []
    with zipfile.ZipFile(apk) as archive, tempfile.TemporaryDirectory(prefix="u5-dex-") as directory:
        for member in sorted(archive.namelist()):
            if not re.fullmatch(r"classes(?:[2-9]|[1-9][0-9]+)?\.dex", member):
                continue
            data = archive.read(member)
            sha = digest(data)
            inventory.append(dict(path=member, sha256=sha, bytes=len(data)))
            path = Path(directory) / member
            path.write_bytes(data)
            method = "unknown"
            retained = set()
            with tempfile.TemporaryFile() as errors:
                process = subprocess.Popen([str(dexdump), "-d", str(path)], stdout=subprocess.PIPE,
                                           stderr=errors, text=True, errors="replace")
                try:
                    for number, line in enumerate(process.stdout, 1):
                        header = HEADER.search(line)
                        if header:
                            method = header[1]
                        if not any(token in line for token in ("FlutterJNI", "hasVibrator", "getVibratorIds")):
                            continue
                        instruction = INSN.search(line)
                        if not instruction:
                            continue
                        family = dex_family(instruction[2])
                        if family and family not in retained:
                            retained.add(family)
                            calls.append(dict(dex=member, dex_sha256=sha, method=method,
                                              offset=instruction[1], line=number, instruction=instruction[2]))
                finally:
                    process.stdout.close()
                    process.wait()
                if process.returncode:
                    raise ValueError(f"dexdump failed for {member}: exit {process.returncode}")
    return inventory, calls


def collect_app(entry, input_root, dexdump):
    directory = input_root / entry["key"]
    metadata_path = directory / "app-input.json"
    metadata = json.loads(metadata_path.read_text())
    apks = [dict(path=str(path.relative_to(directory)), sha256=file_digest(path), bytes=path.stat().st_size)
            for path in sorted(directory.rglob("*.apk"))]
    selected = next((row for row in apks if row["sha256"] == metadata["apk_sha256"]), None)
    facts = dict(entry={field: entry[field] for field in ("key", "package", "apk_sha256")},
                 metadata_sha256=file_digest(metadata_path), metadata_apk_sha256=metadata["apk_sha256"],
                 metadata_package=metadata["application"]["package"],
                 apks=apks, selected_apk=selected, sidecars=[], libraries=[], dex=[], dex_calls=[], scan_errors=[])
    for path in sorted((directory / "lib/arm64-v8a").glob("*.so")):
        data = path.read_bytes()
        name = str(path.relative_to(directory))
        facts["sidecars"].append(dict(path=name, sha256=digest(data), bytes=len(data), header=aarch64_header(data)))
        if path.name in SYMBOLS or path.name.startswith("librealm"):
            facts["libraries"].append(library_fact(name, data))
    if selected:
        apk = directory / selected["path"]
        with zipfile.ZipFile(apk) as archive:
            for name in sorted(archive.namelist()):
                if name.startswith("lib/arm64-v8a/") and (Path(name).name in SYMBOLS or Path(name).name.startswith("librealm")):
                    facts["libraries"].append(library_fact(selected["path"] + "!" + name, archive.read(name)))
        try:
            facts["dex"], facts["dex_calls"] = dex_facts(apk, dexdump)
        except (ValueError, OSError, zipfile.BadZipFile) as error:
            facts["scan_errors"].append(str(error))
    else:
        facts["scan_errors"].append("No actual APK matches metadata pin")
    for library in facts["libraries"]:
        if library["header"] != "valid-ELF64-AArch64" or library["symbol_status"] != "parsed":
            facts["scan_errors"].append("Incomplete native facts: " + library["path"])
    print(f"collected {entry['key']}: {len(facts['dex'])} dex, {len(facts['dex_calls'])} calls", flush=True)
    return facts


def collect(args):
    if file_digest(FROZEN) != FROZEN_SHA:
        raise ValueError("Frozen CSV changed")
    cohort = list(csv.DictReader(io.StringIO(FROZEN.read_text())))
    apps_data = args.apps.read_bytes()
    entries = {row["key"]: row for row in json.loads(apps_data)["apps"]}
    private = args.generation / "payload/android/lib64/westlake_flutter/libandroid.so"
    profile = dict(generation=args.generation.name,
                   package_sha256=file_digest(args.generation / "package.json"),
                   private_android=library_fact(str(private.relative_to(args.generation)), private.read_bytes()))
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures = [executor.submit(collect_app, entries[row["key"]], args.input_root, args.dexdump) for row in cohort]
        facts = [future.result() for future in futures]
    args.output.mkdir(parents=True, exist_ok=True)
    write_json(args.output / "static-facts.json", dict(version=VERSION, frozen_csv_sha256=FROZEN_SHA,
               apps_json_sha256=digest(apps_data), dexdump_sha256=file_digest(args.dexdump), profile=profile, apps=facts))


def forecast(document):
    if document["version"] != VERSION or document["frozen_csv_sha256"] != FROZEN_SHA or file_digest(FROZEN) != FROZEN_SHA:
        raise ValueError("Forecast version or frozen cohort identity mismatch")
    keys = [facts["entry"]["key"] for facts in document["apps"]]
    expected = {row["key"] for row in csv.DictReader(io.StringIO(FROZEN.read_text()))}
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError("Duplicate or missing cohort keys")
    return dict(version=VERSION, mode="retrospective-static-replay-not-held-out-evaluation",
                frozen_csv_sha256=FROZEN_SHA, profile=document["profile"],
                rows=[predict(facts, document["profile"]) for facts in document["apps"]])


def csv_text(report):
    output = io.StringIO(newline="")
    fields = ["key", "package", "expected_apk_sha256", "pin_status", "scanned_apk_sha256", "prediction", "input_categories", "risk_families", "first_wall", "t20"]
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in report["rows"]:
        writer.writerow({**{field: row[field] for field in fields if field in row},
                         "input_categories": ";".join(item["category"] for item in row["input_findings"]),
                         "risk_families": ";".join(item["family"] for item in row["app_wall_risks"])})
    return output.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    collect_parser = subparsers.add_parser("collect")
    collect_parser.add_argument("--apps", type=Path, required=True)
    collect_parser.add_argument("--input-root", type=Path, default=Path.home() / "a2hlab/app-inputs")
    collect_parser.add_argument("--generation", type=Path, required=True)
    collect_parser.add_argument("--dexdump", type=Path, default=Path.home() / "Library/Android/sdk/build-tools/37.0.0/dexdump")
    collect_parser.add_argument("--jobs", type=int, default=4)
    collect_parser.add_argument("--output", type=Path, required=True)
    replay = subparsers.add_parser("predict")
    replay.add_argument("--facts", type=Path, required=True)
    replay.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "collect":
        collect(args)
    else:
        report = forecast(json.loads(args.facts.read_text()))
        report["static_facts_sha256"] = file_digest(args.facts)
        args.output.mkdir(parents=True, exist_ok=True)
        write_json(args.output / "PREDICTIONS.json", report)
        (args.output / "PREDICTIONS.csv").write_text(csv_text(report))


if __name__ == "__main__":
    main()
