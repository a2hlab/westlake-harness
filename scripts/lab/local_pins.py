"""Rewrite app-inputs.lock.json for inputs this workstation supplies differently, recording each change.

Only three kinds of substitution are made, each kept under "local_substitution" with the original values:
  * probes re-built from westlake-harness and signed with this machine's debug keystore;
  * a density split from the same XAPK (same build, same developer certificate) as a base that matches the pin;
  * a whole base+split pair from another build of the same version when the pinned pair is not downloadable.
"""
import hashlib
import json
import sys
from pathlib import Path

lock_path, inputs = Path(sys.argv[1]), Path(sys.argv[2])
lock = json.loads(lock_path.read_text())
apps = lock["applications"]


def ident(path):
    data = path.read_bytes()
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def record(entry, reason, original):
    entry["local_substitution"] = {"reason": reason, "original": original}


probes = inputs / "apks/probes"
for key in [k for k, v in apps.items() if k.endswith("-probe")]:
    entry = apps[key]
    path = probes / f"{key}.apk"
    original = {"sha256": entry["sha256"], "bytes": entry["bytes"]}
    entry.update(ident(path))
    record(entry, "re-built from westlake-harness probes/ and signed with this workstation's debug keystore", original)

pure = inputs / "apks/apkpure"
for key, folder, old, new in [
    ("mcdonalds", "com.mcdonalds.app@26.31.1@arm64-v8a", "split_config.xxxhdpi.apk", "config.xxhdpi.apk"),
    ("burgerking", "com.emn8.mobilem8.nativeapp.bk@7.82.0@arm64-v8a", "config.xxhdpi.apk", "config.hdpi.apk"),
]:
    entry = apps[key]
    splits = entry["splits"]
    index = next(i for i, s in enumerate(splits) if s["name"] == old)
    original = dict(splits[index])
    splits[index] = {"name": new, **ident(pure / folder / new)}
    record(entry, f"{old} not downloadable; {new} is from the same XAPK as the pinned base, same developer certificate", original)
# prepare_app.py matches splits by file name: the other pinned splits keep APKPure's names.
for key, folder in [("mcdonalds", "com.mcdonalds.app@26.31.1@arm64-v8a")]:
    for split in apps[key]["splits"]:
        if split["name"].startswith("split_config."):
            split["name"] = split["name"].removeprefix("split_")

entry = apps["subwaysurfers"]
pair = pure / "subway-variants/v2"
original = {"sha256": entry["sha256"], "bytes": entry["bytes"], "splits": entry["splits"]}
entry.update(ident(pair / "com.kiloo.subwaysurf.apk"))
entry["splits"] = [{"name": "config.arm64_v8a.apk", **ident(pair / "config.arm64_v8a.apk")}]
record(entry, "APKPure serves the pinned base only with an armeabi-v7a split; base and arm64 split taken together "
              "from APKPure's other 3.69.1 XAPK (same versionCode 95769, same developer certificate) so IL2CPP "
              "metadata and libil2cpp.so come from one build", original)

lock_path.write_text(json.dumps(lock, indent=1, ensure_ascii=False) + "\n")
print("rewrote", sum("local_substitution" in v for v in apps.values()), "entries")
