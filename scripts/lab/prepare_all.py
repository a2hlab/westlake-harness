"""Run the manifest's tools/prepare_app.py for every application in its app-inputs.lock.json.

Files are found by SHA-256 anywhere under <inputs>/apks (base and splits alike), so the lock is the
only source of truth for which file belongs to which entry. Output: <out>/<key>, one per application.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

manifest, inputs, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
apps = json.loads((manifest / "app-inputs.lock.json").read_text())["applications"]
by_hash = {}
for path in (inputs / "apks").rglob("*.apk"):
    by_hash.setdefault(hashlib.sha256(path.read_bytes()).hexdigest(), path)
ok = 0
for key, entry in apps.items():
    target = out / key
    if target.exists():
        print(f"SKIP {key}: {target} exists")
        continue
    base = by_hash.get(entry["sha256"])
    splits = [by_hash.get(s["sha256"]) for s in entry.get("splits", [])]
    if base is None or None in splits:
        print(f"MISSING {key}")
        continue
    cmd = [sys.executable, str(manifest / "tools/prepare_app.py"), "--apk", str(base), "--app", key, "--out", str(target)]
    for split in splits:
        cmd += ["--split", str(split)]
    done = subprocess.run(cmd, capture_output=True, text=True)
    last = (done.stdout.strip().splitlines() or [""])[-1] if done.returncode == 0 else (done.stderr.strip().splitlines() or [""])[-1]
    print(f"{'OK  ' if done.returncode == 0 else 'FAIL'} {key:28s} {last[:110]}")
    ok += done.returncode == 0
print(f"{ok}/{len(apps)} prepared")
