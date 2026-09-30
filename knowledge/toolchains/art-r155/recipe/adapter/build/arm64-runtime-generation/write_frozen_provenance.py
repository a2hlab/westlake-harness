#!/usr/bin/env python3
"""Write and verify an immutable frozen-input provenance manifest in one pass."""

import argparse
import csv
import hashlib
from pathlib import Path
import sys


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mappings", required=True, type=Path)
    parser.add_argument("--frozen", required=True, type=Path)
    parser.add_argument("--provenance", required=True, type=Path)
    parser.add_argument("--local-hashes", required=True, type=Path)
    args = parser.parse_args()

    rows = []
    with args.mappings.open(newline="", encoding="utf-8") as stream:
        for line_number, row in enumerate(csv.reader(stream, delimiter="\t"), 1):
            if len(row) != 4:
                raise SystemExit(f"invalid mapping row {line_number}: expected 4 fields")
            rows.append(row)
    rows.sort(key=lambda row: row[1])

    args.provenance.parent.mkdir(parents=True, exist_ok=True)
    local_hash_rows = []
    with args.provenance.open("w", newline="", encoding="utf-8") as receipt:
        writer = csv.writer(receipt, delimiter="\t", lineterminator="\n")
        writer.writerow(("kind", "local_path", "origin_path", "origin_sha256",
                         "local_sha256", "deployability"))
        for index, (kind, relative, origin, deployability) in enumerate(rows, 1):
            source = Path(origin)
            local = args.frozen / relative
            if not source.is_file() or not local.is_file():
                raise SystemExit(f"non-regular provenance input at row {index}: {relative}")
            origin_hash = sha256(source)
            local_hash = sha256(local)
            if origin_hash != local_hash:
                raise SystemExit(f"copy hash mismatch at row {index}: {relative}")
            writer.writerow((kind, relative, origin, origin_hash, local_hash, deployability))
            local_hash_rows.append((relative, local_hash))
            if index % 1000 == 0 or index == len(rows):
                print(f"FROZEN_PROVENANCE_PROGRESS verified={index}/{len(rows)}", file=sys.stderr)

    with args.local_hashes.open("w", encoding="utf-8") as manifest:
        for relative, digest in local_hash_rows:
            manifest.write(f"{digest}  {relative}\n")


if __name__ == "__main__":
    main()
