# Read package identity of each listed APK/XAPK without executing it: aapt2 dump badging (apk), manifest.json (xapk).
import json, os, subprocess, sys, zipfile
aapt2 = sys.argv[1]; lst = sys.argv[2]
for p in open(lst).read().split('\n'):
    if not p: continue
    rec = {"path": p}
    try:
        rec["size"] = os.path.getsize(p)
        if p.endswith('.xapk'):
            with zipfile.ZipFile(p) as z:
                m = json.loads(z.read('manifest.json'))
                rec.update(kind="xapk", package=m.get("package_name"), version_name=m.get("version_name"),
                           version_code=m.get("version_code"), members=[i.filename for i in z.infolist() if i.filename.endswith(('.apk','.obb'))])
        else:
            r = subprocess.run([aapt2, "dump", "badging", p], capture_output=True, text=True, timeout=30)
            line = next((l for l in r.stdout.splitlines() if l.startswith("package:")), None)
            rec.update(kind="apk", rc=r.returncode, package_line=line,
                       split=next((l for l in r.stdout.splitlines() if l.startswith("split:")), None))
            if line is None: rec["stderr_head"] = r.stderr[:200]
    except Exception as e:
        rec["error"] = repr(e)[:200]
    print(json.dumps(rec, ensure_ascii=False), flush=True)
