#!/usr/bin/env python3
"""#69-2: manifest static classification for the 20 deduped apps (#63 13 ∪ #65 14).

Per APK (aapt2 badging + xmltree + unzip listing):
  <application android:name>, Flutter (libflutter.so in lib/),
  launch-activity theme resolved to AppCompat/Material via resources.arsc? —
  we record the raw theme reference plus a resolved string when aapt2 can,
  provider count (E: provider under application), targetSdk, launchable
  activity. Output results.json + README.md.
"""
import json, subprocess, re, zipfile, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
APKS = HERE / "apks"
AAPT = str(Path.home() / "Library/Android/sdk/build-tools/34.0.0/aapt2")

def sh(*args):
    p = subprocess.run(list(args), capture_output=True, text=True, timeout=120)
    return p.stdout + p.stderr

def classify(apk_path):
    apk = str(apk_path)
    d = {"apk": apk_path.name}
    bad = sh(AAPT, "dump", "badging", apk)
    m = re.search(r"package: name='([^']+)'", bad)
    d["package"] = m.group(1) if m else None
    m = re.search(r"targetSdkVersion:'(\d+)'", bad)
    d["target_sdk"] = int(m.group(1)) if m else None
    m = re.search(r"sdkVersion:'(\d+)'", bad)
    d["min_sdk"] = int(m.group(1)) if m else None
    m = re.search(r"launchable-activity: name='([^']+)'", bad)
    d["launch_activity"] = m.group(1) if m else None
    # Flutter?
    try:
        with zipfile.ZipFile(apk) as z:
            libs = [n for n in z.namelist() if n.startswith("lib/") and n.endswith(".so")]
        d["flutter"] = any(n.endswith("libflutter.so") for n in libs)
        d["native_libs"] = sorted({os.path.dirname(n).split("/")[-1] for n in libs})
    except Exception as e:
        d["flutter"] = None
        d["native_libs_error"] = repr(e)[:80]
    # manifest tree
    tree = sh(AAPT, "dump", "xmltree", apk, "--file", "AndroidManifest.xml")
    # application tag attributes (block runs to the next TOP-LEVEL element:
    # 4-space-indented "E: ..." — children are deeper, so the old 6-space
    # lookahead never fired and every app fell back to "(default)")
    app_block = re.search(r"E: application \(line=\d+\)(.*?)(?=\n    E: |\Z)", tree, re.S)
    name = theme = None
    if app_block:
        blk = app_block.group(1)
        m = re.search(r'android:name\(0x[0-9a-f]+\)="([^"]+)"', blk)
        if m: name = m.group(1)
        m = re.search(r"android:theme\(0x[0-9a-f]+\)=([^ \n]+)", blk)
        if m: theme = m.group(1)
    d["application_name"] = name or "(default Application)"
    d["application_theme_ref"] = theme
    # AppCompat / Material proxy: scan classes.dex strings
    try:
        with zipfile.ZipFile(apk) as z:
            dex = b"".join(z.read(n) for n in z.namelist() if n.endswith(".dex"))
        d["uses_appcompat"] = b"androidx/appcompat" in dex
        d["uses_material"] = b"com/google/android/material" in dex
    except Exception:
        d["uses_appcompat"] = d["uses_material"] = None
    # providers under application
    provs = re.findall(r"E: provider \(line=(\d+)\)", tree)
    d["provider_count"] = len(provs)
    # launch activity theme: xmltree activity with android.intent.category.LAUNCHER is
    # hard to attribute textually; record themes of all activities matching launch name
    if d["launch_activity"]:
        esc = re.escape(d["launch_activity"])
        m = re.search(r"E: activity \(line=\d+\).*?" + esc + r".*?android:theme\(0x[0-9a-f]+\)=([^ \n]+)", tree, re.S)
        d["launch_theme_ref"] = m.group(1) if m else None
    # services / receivers quick counts (context)
    d["service_count"] = len(re.findall(r"E: service \(line=\d+\)", tree))
    d["receiver_count"] = len(re.findall(r"E: receiver \(line=\d+\)", tree))
    return d

def main():
    keys = json.load(open(HERE / "keys-27.json"))
    rows = []
    for line in open(HERE / "apk-paths.txt"):
        p = line.strip()
        if not p: continue
        key = p.split("/")[0]
        f = APKS / p
        if not f.is_file():
            rows.append({"key": key, "error": "apk missing"})
            continue
        try:
            d = classify(f)
            d["key"] = key
            rows.append(d)
        except Exception as e:
            rows.append({"key": key, "error": repr(e)[:120]})
    json.dump({"source": {"p63_white13": keys["from_p63"], "p65_b8": keys["from_p65"],
                          "deduped": keys["keys"]},
               "apps": rows}, open(HERE / "results.json", "w"), indent=1, ensure_ascii=False)
    for r in rows:
        print("%-18s %s" % (r.get("key"), r.get("error") or
              "name=%-42s flutter=%-5s providers=%-2d tSdk=%s" % (
                  (r.get("application_name") or "(default)")[:42], r.get("flutter"),
                  r.get("provider_count"), r.get("target_sdk"))))

if __name__ == "__main__":
    main()
