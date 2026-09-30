#!/usr/bin/env python3
"""Replay hash-bound native sources and DEX initialization slices, entirely offline."""
import argparse
import hashlib
import json
from pathlib import Path

from rules_native_initialization import Source, jni_order_walls, namespace_walls


def read_input(root, entry):
    path = (root / entry["path"]).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("input escapes manifest directory")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
        raise ValueError("input SHA mismatch: " + entry["path"])
    return raw


def scan(manifest_path):
    manifest = json.loads(manifest_path.read_text())
    if manifest["schema_version"] != 1:
        raise ValueError("unsupported replay schema")
    root = manifest_path.parent
    sources = {name: Source(name, read_input(root, entry).decode(), entry.get("first_line", 1))
               for name, entry in manifest["sources"].items()}
    rows = []
    for profile in manifest["profiles"]:
        if profile["rule"] == "namespace":
            result = namespace_walls(sources[profile["source"]])
        elif profile["rule"] == "jni-order":
            dex = json.loads(read_input(root, manifest["dex"]))
            selected = {name: sources[name] for name in profile["sources"]}
            result = jni_order_walls(selected, profile["entry_source"], profile["entry_function"], dex["classes"])
        else:
            raise ValueError("unknown rule")
        rows.append(dict(profile=profile["name"], identity=profile["identity"], **result))
    return dict(schema_version=1, prospective=False, device_access=False,
                scope="bounded static initialization risks; no finding does not prove runtime success",
                manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(), profiles=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = scan(args.manifest)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps(dict(status="unknown-invalid-input", error=str(error))))
        return 3
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
