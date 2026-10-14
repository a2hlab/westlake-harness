#!/usr/bin/env python3
"""Acquire or validate locked external archives; never silently substitute inputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(path, expected):
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f"SHA_MISMATCH {path.name} expected={expected} actual={actual}")
    return actual


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--receipt-dir", type=Path, required=True)
    args = parser.parse_args()
    lock = Path(__file__).with_name("dependencies.lock.json")
    entries = json.loads(lock.read_text())["archives"]
    entry = next((item for item in entries if item["id"] == args.id), None)
    if entry is None:
        parser.error("unknown dependency id")
    args.receipt_dir.mkdir(parents=True, exist_ok=False)
    receipt = {"id": args.id, "lock_sha256": sha256(lock), "expected_sha256": entry["sha256"], "fetch_requested": args.fetch}
    exit_code = 2
    try:
        if args.fetch:
            if args.archive.exists():
                raise ValueError("FETCH_REFUSE_EXISTING_ARCHIVE")
            host = os.environ["HW248_HOST"]
            home = os.environ["HW248_HOME"]
            if not home.startswith("/") or any(char in host + home for char in "\n\r"):
                raise ValueError("invalid remote locator")
            temporary = args.archive.with_name(args.archive.name + ".partial")
            if temporary.exists():
                raise ValueError("FETCH_REFUSE_EXISTING_PARTIAL")
            argv = ["scp", "-o", "BatchMode=yes", host + ":" + home.rstrip("/") + "/" + entry["relative_remote_path"], str(temporary)]
            receipt["argv"] = argv
            with (args.receipt_dir / "fetch.stdout").open("wb") as stdout, (args.receipt_dir / "fetch.stderr").open("wb") as stderr:
                result = subprocess.run(argv, stdout=stdout, stderr=stderr, check=False)
            receipt["fetch_exit_code"] = result.returncode
            if result.returncode:
                raise ValueError("FETCH_FAILED_PARTIAL_RETAINED")
            verify(temporary, entry["sha256"])
            os.link(temporary, args.archive)
            temporary.unlink()
        receipt["actual_sha256"] = verify(args.archive, entry["sha256"])
        receipt["bytes"] = args.archive.stat().st_size
        receipt["status"] = "LOCKED_ARCHIVE_VERIFIED_NOT_A_BUILD"
        exit_code = 0
    except (OSError, KeyError, ValueError) as error:
        receipt["status"] = "REJECT"
        receipt["error"] = str(error)
    receipt["exit_code"] = exit_code
    for path in args.receipt_dir.iterdir():
        if path.is_file():
            receipt.setdefault("raw", []).append({"path": path.name, "sha256": sha256(path)})
    (args.receipt_dir / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
