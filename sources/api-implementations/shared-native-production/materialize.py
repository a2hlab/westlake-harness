#!/usr/bin/env python3
"""Materialize exact preserved implementation bytes into a new build tree."""
import argparse
import base64
import hashlib
import json
from pathlib import Path


def materialize(family, destination):
    here = Path(__file__).resolve().parent
    rows = json.loads((here / "source-index.json").read_text())["files"]
    selected = [row for row in rows if row["path"].startswith(family.rstrip("/") + "/")]
    if not selected:
        raise ValueError("UNKNOWN_SOURCE_FAMILY")
    destination.mkdir(parents=True, exist_ok=False)
    receipt = []
    for row in selected:
        relative = Path(row["path"]).relative_to(family)
        if ".." in relative.parts or relative.is_absolute():
            raise ValueError("SOURCE_PATH_ESCAPE")
        value = (here / row["path"]).read_bytes()
        if hashlib.sha256(value).hexdigest() != row["sha256"]:
            raise ValueError("DELIVERED_SOURCE_CHANGED " + row["path"])
        if row.get("raw_source_path"):
            encoded = (here / row["raw_source_path"]).read_text().strip()
            raw = base64.b64decode(encoded, validate=True)
            if hashlib.sha256(raw).hexdigest() != row["raw_source_sha256"]:
                raise ValueError("RAW_SOURCE_CHANGED " + row["path"])
            if raw.replace(b"\r\n", b"\n") != value:
                raise ValueError("UNDECLARED_SOURCE_TRANSFORMATION " + row["path"])
            value = raw
        if hashlib.sha256(value).hexdigest() != row["origin_sha256"]:
            raise ValueError("ORIGINAL_SOURCE_BYTES_NOT_RESTORED " + row["path"])
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(value)
        receipt.append({"path": str(relative), "sha256": hashlib.sha256(value).hexdigest()})
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--family", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    rows = materialize(args.family, args.out)
    print(json.dumps({"materialized": len(rows), "files": rows}, indent=2))


if __name__ == "__main__":
    main()
