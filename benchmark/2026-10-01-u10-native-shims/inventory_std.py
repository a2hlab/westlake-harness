import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import zipfile


HERE = Path(__file__).resolve().parent


def digest(filename):
    return hashlib.sha256(Path(filename).read_bytes()).hexdigest()


def inventory(workspaces):
    native = workspaces / "westlake-generation-u9-j10g-238ffc14/native"
    root = native / "payload/android/lib64"
    policy = json.loads((HERE / "native-loader/overlay/policy/native_bridge_policy.v1.json").read_text())
    copies = []
    for relative in ["libstdc++.so", "westlake_native/libstdc++.so"]:
        board_path = "/system/android/lib64/" + relative
        copies.append({"board_path": board_path, "sha256": digest(root / relative),
                       "bridge_soname_search_candidate": str(PurePosixPath(board_path).parent) in policy["bridge_search_paths"]})
    if [row["bridge_soname_search_candidate"] for row in copies] != [True, False]:
        raise ValueError("bridge roots do not select the root copy exclusively")
    previous = json.loads((HERE.parents[1] / "benchmark/2026-10-01-u7-prospective/v1/apps-u7.json").read_text())["apps"]
    newer = json.loads((workspaces / "westlake-harness-t4/benchmark/2026-10-01-corpus-v2-inputs/apps-v2.json").read_text())["apps"]
    rows = []
    for application in previous + newer:
        key = application["key"]
        expected = application["apk_sha256"]
        candidates = [Path(application["apk"])] if "apk" in application else list((Path.home() / "a2hlab/app-inputs" / key).glob("*.apk"))
        matches = [filename for filename in candidates if filename.is_file() and digest(filename) == expected]
        if not matches:
            rows.append({"key": key, "apk_sha256": expected, "status": "input_identity_missing", "bundled_std": None})
            continue
        with zipfile.ZipFile(matches[0]) as archive:
            members = [name for name in archive.namelist() if name.startswith("lib/arm64-v8a/") and name.endswith("/libstdc++.so")]
            rows.append({"key": key, "apk_sha256": expected, "status": "scanned", "bundled_std": members})
    return {"schema": "u10-libstd-policy-resolution-v1", "copies": copies,
            "bridge_search_paths": policy["bridge_search_paths"], "bridge_permitted_paths": policy["bridge_permitted_paths"],
            "resolution": "SONAME lookup uses direct search roots, not recursive subdirectories; target dlns scope acceptance pending",
            "key_count": len(rows), "scanned_keys": sum(row["status"] == "scanned" for row in rows),
            "unknown_keys": [row["key"] for row in rows if row["status"] != "scanned"],
            "bundled_std_keys": [row["key"] for row in rows if row["bundled_std"]], "apps": rows,
            "limits": "Single pinned APK per key only; external/split sidecars and runtime loading are not covered by bundled member count"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspaces", type=Path, default=os.environ.get("WORKSPACES"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = inventory(args.workspaces)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({field: result[field] for field in ["key_count", "scanned_keys", "unknown_keys", "bundled_std_keys"]}))


if __name__ == "__main__":
    main()
