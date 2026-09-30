"""Pin record-aligned baseline apps into the manifest's app-inputs.lock.json (same entry format as the corpus100 pins).

usage: pin_aligned.py <manifest> <key>=<apk-or-xapk>[::<reference>] ...
An XAPK is unpacked to <inputs>/apks/xapk-extracted/<key>/ and pinned as base + splits by their own hashes, so
prepare_app.py can be fed the inner files directly. Package, version and launch activity come from aapt2.
Runs inside VM a2hlab. Existing keys are refused rather than overwritten.
"""
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import lab_paths

AAPT2 = Path.home() / "a2hlab/ws/toolchains/android-build-tools35/android-15/aapt2"
INPUTS = lab_paths.inputs()


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def badging(apk):
    text = subprocess.run([str(AAPT2), "dump", "badging", str(apk)], capture_output=True, text=True).stdout
    field = lambda pattern: (re.search(pattern, text) or [None, None])[1]
    return {"package": field(r"package: name='([^']+)'"), "version_name": field(r"versionName='([^']*)'"),
            "version_code": int(field(r"versionCode='(\d+)'")), "launch_activity": field(r"launchable-activity: name='([^']+)'")}


def native_abis(paths):
    abis = set()
    for path in paths:
        with zipfile.ZipFile(path) as z:
            abis.update(n.split("/")[1] for n in z.namelist() if n.startswith("lib/") and n.endswith(".so"))
    return abis


def main():
    manifest = Path(sys.argv[1])
    lock_path = manifest / "app-inputs.lock.json"
    lock = json.loads(lock_path.read_text())
    for spec in sys.argv[2:]:
        key, rest = spec.split("=", 1)
        source, _, reference = rest.partition("::")
        source = Path(source)
        if key in lock["applications"]:
            raise SystemExit(f"{key}: already pinned")
        if source.suffix == ".xapk":
            root = INPUTS / "apks/xapk-extracted" / key
            root.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(source) as z:
                inner = [n for n in z.namelist() if n.endswith(".apk")]
                z.extractall(root, inner)
            files = [root / n for n in inner]
            info = next(badging(f) for f in files if not Path(f).name.startswith("config.")
                        and Path(f).name != "google_assets.apk")
            base = next(f for f in files if badging(f)["launch_activity"] or f.stem == info["package"])
            splits = [f for f in files if f != base]
        else:
            base, splits, info = source, [], badging(source)
        abis = native_abis([base, *splits])
        entry = {"kind": "original-apk-with-splits" if splits else "original-apk", "package": info["package"],
                 "version_name": info["version_name"], "version_code": info["version_code"], "abi": "arm64-v8a",
                 "bytes": base.stat().st_size, "sha256": sha(base), "delivery": "baseline alignment (record-matched build)",
                 "reference": reference or str(source.name), "rebuild": False, "modify_or_resign": False,
                 "launch_activity": info["launch_activity"]}
        if splits:
            entry["splits"] = [{"name": s.name, "bytes": s.stat().st_size, "sha256": sha(s)} for s in splits]
        if not abis:
            entry["pure_java"] = True
        elif "arm64-v8a" not in abis:
            raise SystemExit(f"{key}: no arm64-v8a code ({sorted(abis)})")
        lock["applications"][key] = entry
        print(key, json.dumps({k: entry[k] for k in ("package", "version_name", "version_code", "launch_activity")}),
              "splits:", [s.name for s in splits], "abis:", sorted(abis) or "none (pure JVM)")
    lock_path.write_text(json.dumps(lock, indent=1) + "\n")


if __name__ == "__main__":
    main()
