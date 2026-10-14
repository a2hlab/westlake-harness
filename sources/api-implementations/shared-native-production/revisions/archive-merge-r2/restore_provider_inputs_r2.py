#!/usr/bin/env python3
"""Exact locked-archive merge revision; the original frozen restorer is unchanged."""
import argparse
import json
from pathlib import Path
import stat
import sys

from audit_archives import SOURCE, compare, inventory
from acquire import sha256, verify
from restore_provider_inputs import restore


def verify_external_overlap(primary, secondary):
    if secondary.keys() - primary.keys():
        raise ValueError("UNDECLARED_NEW_EXTERNAL_TARGETS")
    rows = compare(primary, secondary)
    if any(row["decision"] == "REJECT_DIFFERENT" for row in rows):
        raise ValueError("DIFFERENT_EXTERNAL_BYTES_OR_METADATA")
    return rows


def verify_restored_duplicate(destination, record):
    target = destination / record["target"]
    metadata = record["metadata"]
    if target.is_symlink():
        raise ValueError("RESTORED_DUPLICATE_SYMLINK")
    if metadata["type"] == "5":
        if not target.is_dir():
            raise ValueError("RESTORED_DUPLICATE_NOT_DIRECTORY")
        return
    if metadata["type"] != "0" or not target.is_file():
        raise ValueError("RESTORED_DUPLICATE_NOT_REGULAR_FILE")
    verify(target, record["sha256"])
    if target.stat().st_size != metadata["size"] or stat.S_IMODE(target.stat().st_mode) != metadata["mode"]:
        raise ValueError("RESTORED_DUPLICATE_SIZE_MODE_CHANGED")


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
    receipt = {"revision": "archive-merge-r2", "inputs_sha256": entries["FZ002_GENERATION"]["sha256"], "external_sha256": entries["FZ002_PLATFORM_LINK"]["sha256"], "generation_path": str(args.out.resolve()), "build_executed": False, "whole_generation_complete": False}
    try:
        primary, primary_summary = inventory(args.inputs, "b68-generation", args.out / "generation-inventory.jsonl")
        secondary, secondary_summary = inventory(args.external, "platform-link", args.out / "external-inventory.jsonl")
        duplicates = verify_external_overlap(primary, secondary)
        receipt["generation_inventory"] = primary_summary
        receipt["external_inventory"] = secondary_summary
        receipt["generation_members"] = restore(args.inputs, args.out, "b68-generation")
        for record in secondary.values():
            verify_restored_duplicate(args.out, record)
        receipt["duplicate_members_verified"] = len(duplicates)
        receipt["external_files_overwritten"] = 0
        receipt["external_new_targets"] = 0
        receipt["unprovided_not_consumed_by_provider"] = ["v1-tests/include", "v1-tests/src"]
        receipt["status"] = "RESTORED_NOT_BUILT"
        exit_code = 0
    except (OSError, ValueError) as error:
        receipt["status"] = "REJECT_PARTIAL_RETAINED"
        receipt["error"] = str(error)
        exit_code = 2
    receipt["exit_code"] = exit_code
    (args.out / "restore-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
