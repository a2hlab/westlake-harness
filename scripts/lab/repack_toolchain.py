"""Rebuild one toolchains/ LFS archive from its verified upstream tree with the manifest's packager.

usage: repack_toolchain.py <manifest> <index.json> <key> <extracted tree> <out archive>
The packager is deterministic (gzip mtime 0, PAX, sorted names, zeroed owners), so the result is
compared byte-for-byte with the LFS object the budget-limited repository would have served.
"""
import sys
from pathlib import Path

manifest, index_path, key, tree, out = sys.argv[1:6]
sys.path.insert(0, str(Path(manifest) / "tools"))
import json  # noqa: E402
from bootstrap_sdk import fingerprint  # noqa: E402
from package_toolchains import package  # noqa: E402

entry = json.loads(Path(index_path).read_text())["packages"][key]
actual = fingerprint(Path(tree))["sha256"]
print("ORIGINAL_TREE", actual, "ok" if actual == entry["original"]["tree_sha256"] else "MISMATCH " + entry["original"]["tree_sha256"])

def omit(name):
    if key != "ohos-sdk":
        return False
    return (Path(name).suffix.lower() in {".p12", ".pfx", ".jks", ".keystore", ".key", ".pem"}
            or name in {"toolchains/libselinux.so", "toolchains/libsepol.so", "toolchains/diff"})

record = package(Path(tree), Path(out), omit)
for field in ("sha256", "bytes", "tree_sha256", "file_count"):
    print(f"{field:12s} {'ok' if record[field] == entry[field] else 'MISMATCH'}  got={record[field]} want={entry[field]}")
