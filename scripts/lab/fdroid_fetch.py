"""Download the suggested F-Droid build of each candidate, preferring an arm64-v8a (or ABI-free) APK.

usage: fdroid_fetch.py <candidates.json> <out dir> <result.json>
candidates.json: {"<package>": "<stack label>", ...}. F-Droid often ships one APK per ABI under different
versionCodes of the same versionName; each is tried until one carries lib/arm64-v8a or no native code.
"""
import json, subprocess, sys, urllib.request, zipfile
from pathlib import Path

cands, out, result_path = json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2]), Path(sys.argv[3])
results = json.loads(result_path.read_text()) if result_path.exists() else {}

def abis(apk):
    with zipfile.ZipFile(apk) as z:
        return sorted({n.split("/")[1] for n in z.namelist() if n.startswith("lib/") and n.count("/") >= 2})

for pkg, stack in cands.items():
    if results.get(pkg, {}).get("status") == "ok":
        continue
    try:
        meta = json.load(urllib.request.urlopen(f"https://f-droid.org/api/v1/packages/{pkg}", timeout=60))
    except Exception as e:
        results[pkg] = {"status": f"not on F-Droid ({e.__class__.__name__})", "stack": stack}; print(pkg, results[pkg]["status"], flush=True); continue
    sugg = meta.get("suggestedVersionCode"); name = next((p["versionName"] for p in meta["packages"] if p["versionCode"] == sugg), None)
    tries = [p["versionCode"] for p in meta["packages"] if p["versionName"] == name] or [sugg]
    tries.sort(key=lambda vc: vc != sugg)
    status = "no arm64 build"
    for vc in tries:
        apk = out / f"{pkg}_{vc}.apk"
        if not apk.exists():
            r = subprocess.run(["curl", "-fsSL", "--retry", "5", "--retry-all-errors", "--max-time", "1800", "-o", str(apk),
                                f"https://f-droid.org/repo/{pkg}_{vc}.apk"])
            if r.returncode: apk.unlink(missing_ok=True); continue
        a = abis(apk)
        if not a or "arm64-v8a" in a:
            results[pkg] = {"status": "ok", "stack": stack, "file": str(apk), "version": name, "version_code": vc, "abis": a or ["none (pure JVM)"]}
            break
        apk.unlink()
    else:
        results[pkg] = {"status": status, "stack": stack}
    print(pkg, results[pkg]["status"], results[pkg].get("abis", ""), flush=True)
    result_path.write_text(json.dumps(results, indent=1) + "\n")
result_path.write_text(json.dumps(results, indent=1) + "\n")
