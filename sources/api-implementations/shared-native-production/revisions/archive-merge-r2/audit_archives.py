#!/usr/bin/env python3
"""Audit every target in the two locked archives before considering any merge."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import tarfile

SOURCE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SOURCE))
from acquire import sha256, verify
from restore_provider_inputs import mapped_name


def inventory(archive, component, output):
    targets = {}
    total = 0
    skipped = 0
    with tarfile.open(archive, "r:gz") as stream, output.open("x") as rows:
        for member in stream:
            total += 1
            if any(part.startswith("._") for part in Path(member.name).parts):
                skipped += 1
                continue
            target = mapped_name(member.name, component)
            if target == ".":
                skipped += 1
                continue
            if target in targets:
                raise ValueError("INTRA_ARCHIVE_DUPLICATE " + target)
            metadata = {"type": member.type.decode("ascii"), "mode": member.mode, "uid": member.uid, "gid": member.gid, "mtime": member.mtime, "size": member.size, "linkname": member.linkname}
            digest = None
            if member.isfile():
                value = hashlib.sha256()
                content = stream.extractfile(member)
                for block in iter(lambda: content.read(1024 * 1024), b""):
                    value.update(block)
                digest = value.hexdigest()
            record = {"target": target, "sha256": digest, "metadata": metadata}
            rows.write(json.dumps(record, sort_keys=True) + "\n")
            targets[target] = record
    return targets, {"tar_members": total, "ignored_metadata_and_root_members": skipped, "targets": len(targets), "inventory_sha256": sha256(output)}


def compare(primary, secondary):
    rows = []
    for target in sorted(primary.keys() & secondary.keys()):
        left, right = primary[target], secondary[target]
        byte_equal = left["sha256"] == right["sha256"]
        metadata_delta = {key: [left["metadata"][key], right["metadata"][key]] for key in left["metadata"] if left["metadata"][key] != right["metadata"][key]}
        is_directory = left["metadata"]["type"] == right["metadata"]["type"] == "5"
        decision = "RETAIN_EXISTING_DIRECTORY_NO_METADATA_CHANGE" if is_directory else "SKIP_EXACT_IDENTICAL" if byte_equal and not metadata_delta else "REJECT_DIFFERENT"
        rows.append({"target": target, "primary_sha256": left["sha256"], "secondary_sha256": right["sha256"], "byte_equal": byte_equal, "metadata_delta": metadata_delta, "directory": is_directory, "decision": decision})
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--external", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    lock = json.loads((SOURCE / "dependencies.lock.json").read_text())
    entries = {item["id"]: item for item in lock["archives"]}
    verify(args.inputs, entries["FZ002_GENERATION"]["sha256"])
    verify(args.external, entries["FZ002_PLATFORM_LINK"]["sha256"])
    args.out.mkdir(parents=True, exist_ok=False)
    primary, left_summary = inventory(args.inputs, "b68-generation", args.out / "generation.jsonl")
    secondary, right_summary = inventory(args.external, "platform-link", args.out / "external.jsonl")
    duplicates = compare(primary, secondary)
    conflicts = [row for row in duplicates if row["decision"] == "REJECT_DIFFERENT"]
    receipt = {"schema": "locked-archive-merge-audit/v1", "inputs_sha256": entries["FZ002_GENERATION"]["sha256"], "external_sha256": entries["FZ002_PLATFORM_LINK"]["sha256"], "generation": left_summary, "external": right_summary, "duplicates": duplicates, "duplicate_count": len(duplicates), "file_conflicts": len(conflicts), "merge_permitted": not conflicts, "extraction_or_build_executed": False, "exit_code": 0 if not conflicts else 2}
    (args.out / "audit.json").write_text(json.dumps(receipt, indent=2) + "\n")
    with (args.out / "duplicates.csv").open("x") as stream:
        writer = csv.writer(stream)
        writer.writerow(["target", "primary_sha256", "secondary_sha256", "metadata_delta", "decision"])
        writer.writerows([row["target"], row["primary_sha256"], row["secondary_sha256"], json.dumps(row["metadata_delta"], sort_keys=True), row["decision"]] for row in duplicates)
    print(json.dumps({"duplicate_count": len(duplicates), "file_conflicts": len(conflicts), "merge_permitted": not conflicts, "audit_sha256": sha256(args.out / "audit.json"), "exit_code": receipt["exit_code"]}, indent=2))
    return receipt["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
