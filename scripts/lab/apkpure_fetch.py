"""Fetch an arm64-capable build of each package from APKPure, trying every variant APKPure lists.

usage: apkpure_fetch.py <candidates.json> <out dir> <result.json>
candidates.json: {"<package>": {"stack": ..., "version": optional exact versionName}}
apkeep takes the first download link after the version string; when APKPure lists several variants of one
version (e.g. an armeabi-v7a and an arm64-v8a XAPK) that can silently be the wrong ABI. Here each variant of
the chosen version is downloaded in turn and kept only if it carries arm64-v8a code (or no native code).
"""
import base64, hashlib, json, re, subprocess, sys, urllib.parse, urllib.request, zipfile
from pathlib import Path

cands, out, result_path = json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2]), Path(sys.argv[3])
results = json.loads(result_path.read_text()) if result_path.exists() else {}
HEAD = {"x-cv": "3172501", "x-sv": "29", "x-abis": "arm64-v8a", "x-gp": "1"}
URL = re.compile(r"(X?APKJ)..(https?://download\.pureapk\.com/[-a-zA-Z0-9@:%._+~#=/?&]+)")

def variants(pkg):
    # curl, not urllib: APKPure refuses Python's default client identity
    cmd = ["curl", "-fsS", "--retry", "5", "--retry-all-errors", "--max-time", "90"]
    for k, v in HEAD.items(): cmd += ["-H", f"{k}: {v}"]
    body = subprocess.run(cmd + [f"https://api.pureapk.com/m/v3/cms/app_version?hl=en-US&package_name={pkg}"],
                          check=True, capture_output=True).stdout.decode("latin-1")
    found = []
    for kind, url in URL.findall(body):
        # parse the query by hand: parse_qs turns the '+' of standard base64 into a space
        raw = dict(kv.split("=", 1) for kv in urllib.parse.urlparse(url).query.split("&") if "=" in kv)
        c = urllib.parse.unquote(raw.get("c", "")).split("|")[-1]
        info = {}
        for decode in (base64.b64decode, base64.urlsafe_b64decode):
            try: info = dict(urllib.parse.parse_qsl(decode(c + "=" * (-len(c) % 4)).decode())); break
            except Exception: pass
        found.append({"kind": "xapk" if kind == "XAPKJ" else "apk", "url": url, "vn": info.get("vn"), "vc": info.get("vc"), "size": info.get("s")})
    return found

def arm64_ok(path, kind):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if kind == "xapk":
            splits = [n for n in names if n.endswith(".apk")]
            if any("arm64_v8a" in n for n in splits): return True, splits
            if any(("armeabi" in n or "x86" in n) for n in splits): return False, splits
            return True, splits  # no ABI split: code, if any, is in the base
        libs = {n.split("/")[1] for n in names if n.startswith("lib/") and n.count("/") >= 2}
        return (not libs or "arm64-v8a" in libs), sorted(libs)

for pkg, spec in cands.items():
    if results.get(pkg, {}).get("status") == "ok": continue
    try: vs = variants(pkg)
    except Exception as e:
        results[pkg] = {"status": f"lookup failed ({e.__class__.__name__})", **spec}; print(pkg, results[pkg]["status"], flush=True); continue
    # skip ChromeOS channel builds (versionName ...-CrOS): not the phone APK
    vs = [v for v in vs if v["vn"] and "cros" not in v["vn"].lower()]
    want = spec.get("version") or next((v["vn"] for v in vs), None)
    # a pinned version: only its variants; otherwise newest first, falling back to older builds when APKPure
    # lists no arm64 variant for the newest (e.g. Zoom's newest XAPK carries only config.armeabi_v7a)
    pick = [v for v in vs if v["vn"] == want] if spec.get("version") else vs[:5]
    results[pkg] = {"status": f"no arm64 variant in {len(pick)} tried (newest {want})" if pick else f"version {want} not listed", **spec}
    for i, v in enumerate(pick):
        want = v["vn"]
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", want)  # version names can hold '/' (Teams: "1416/1.0.0...")
        f = out / f"{pkg}@{safe}.v{i}.{v['kind']}"
        # download to a VM-local file first: retries that truncate a partial file fail on the shared Mac mount
        # (curl exit 23); resume with -C - across attempts, then move the finished file into place
        tmp = Path.home() / "a2hlab/tmp/apkpure" / f.name; tmp.parent.mkdir(parents=True, exist_ok=True)
        done = any(subprocess.run(["curl", "-fsSL", "-C", "-", "--retry", "5", "--retry-all-errors", "--max-time", "1800",
                                   "-o", str(tmp), v["url"]]).returncode == 0 for _ in range(6))
        if not done:
            tmp.unlink(missing_ok=True); continue
        import shutil; shutil.move(str(tmp), str(f))
        try: ok, detail = arm64_ok(f, v["kind"])
        except zipfile.BadZipFile: ok, detail = False, "bad zip"
        if ok:
            results[pkg] = {"status": "ok", **spec, "file": str(f), "version": want, "newest_listed": vs[0]["vn"] if vs else None, "version_code": v["vc"], "kind": v["kind"],
                            "sha256": hashlib.sha256(f.read_bytes()).hexdigest(), "bytes": f.stat().st_size, "contents": detail}
            break
        f.unlink()
    print(pkg, results[pkg]["status"], results[pkg].get("version", ""), flush=True)
    result_path.write_text(json.dumps(results, indent=1) + "\n")
result_path.write_text(json.dumps(results, indent=1) + "\n")
