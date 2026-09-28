"""Check downloaded APKs (and split files) against app-inputs.lock.json by SHA-256."""
import hashlib, json, sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
lock = json.loads((root / "app-inputs.lock.json").read_text())["applications"]
have = {}
for path in (root / "apks").rglob("*.apk"):
    have.setdefault(hashlib.sha256(path.read_bytes()).hexdigest(), []).append(path.relative_to(root))
for key, entry in lock.items():
    parts = [("base", entry["sha256"])] + [(s["name"], s["sha256"]) for s in entry.get("splits", [])]
    found = [(name, have.get(sha)) for name, sha in parts]
    ok = all(p for _, p in found)
    detail = ", ".join(f"{n}={'ok' if p else 'MISSING'}" for n, p in found)
    print(f"{'OK  ' if ok else '--  '}{key:28s} {entry.get('version_name','')[:22]:22s} {detail}")
