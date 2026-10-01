#!/usr/bin/env python3
"""Scan every corpus-v2 APK for WebView-shell signals (Capacitor / Cordova) and cross-reference the U9
predictions-v4.csv: a shell that "passes the wall" still white-windows on route-A (no Chromium renderer),
so a lit/lit? prediction on a shell is really alive-white-window. Signals per APK:
  - Capacitor: assets/capacitor.config.json | assets/public/index.html ; dex class BridgeActivity
  - Cordova:   assets/www/index.html | assets/www/cordova.js | assets/cordova.js ; dex class CordovaActivity
Evidence-first: one line per key. Paths resolve via scripts/lab/lab_paths.py (new-script convention)."""
import json, re, subprocess, sys, zipfile
from pathlib import Path
for _p in Path(__file__).resolve().parents:
    if (_p/"westlake-harness/scripts/lab/lab_paths.py").exists():
        sys.path.insert(0, str(_p/"westlake-harness/scripts/lab")); break
import lab_paths
WS = lab_paths.workspaces()
CORPUS = WS/"westlake-inputs/corpus-v2/app-inputs"
PRED = WS/"westlake-harness/benchmark/2026-10-01-u9-prediction/predictions-v4.csv"
HERE = Path(__file__).resolve().parent

CAP_ASSET = re.compile(r"assets/(capacitor\.config\.json|public/index\.html)$")
COR_ASSET = re.compile(r"assets/(www/index\.html|www/cordova\.js|cordova\.js)$")

def dex_classes(apk):
    """strings over the dex(es): did the app bundle a Capacitor BridgeActivity / Cordova CordovaActivity?"""
    hits = set()
    try:
        with zipfile.ZipFile(apk) as z:
            dexes = [n for n in z.namelist() if re.fullmatch(r"classes\d*\.dex", n)]
            for d in dexes:
                data = z.read(d)
                if b"BridgeActivity" in data: hits.add("BridgeActivity")
                if b"CordovaActivity" in data: hits.add("CordovaActivity")
                if b"capacitor" in data and b"Capacitor" in data: hits.add("capacitor-pkg")
    except Exception as e:
        hits.add(f"dexerr:{e}")
    return hits

def scan(apk):
    sig = {"cap_asset": [], "cor_asset": [], "dex": []}
    try:
        with zipfile.ZipFile(apk) as z:
            for n in z.namelist():
                if CAP_ASSET.search(n): sig["cap_asset"].append(n)
                elif COR_ASSET.search(n): sig["cor_asset"].append(n)
    except Exception as e:
        sig["err"] = str(e)
    sig["dex"] = sorted(dex_classes(apk))
    cap = bool(sig["cap_asset"]) or "BridgeActivity" in sig["dex"]
    cor = bool(sig["cor_asset"]) or "CordovaActivity" in sig["dex"]
    sig["shell"] = "capacitor" if cap else ("cordova" if cor else "none")
    return sig

def load_pred():
    pred = {}
    if PRED.exists():
        import csv
        for r in csv.DictReader(PRED.open()):
            pred[r["key"]] = (r.get("prediction",""), r.get("reason",""))
    return pred

def main():
    pred = load_pred()
    rows = []
    for d in sorted(CORPUS.iterdir()):
        if not d.is_dir(): continue
        apks = list(d.glob("*.apk"))
        if not apks: continue
        s = scan(apks[0])
        p, reason = pred.get(d.name, ("", ""))
        rows.append({"key": d.name, "shell": s["shell"], "prediction": p,
                     "cap_asset": s["cap_asset"], "cor_asset": s["cor_asset"], "dex": s["dex"], "reason": reason})
    shells = [r for r in rows if r["shell"] != "none"]
    lit_shells = [r for r in rows if r["shell"] != "none" and r["prediction"] in ("lit", "lit?")]
    out = {"schema":"webview-shell-scan-v1","total":len(rows),
           "shells":len(shells),"capacitor":sum(r["shell"]=="capacitor" for r in rows),
           "cordova":sum(r["shell"]=="cordova" for r in rows),
           "lit_or_litq_shells":[r["key"] for r in lit_shells], "rows": rows}
    (HERE/"results.json").write_text(json.dumps(out, indent=2))
    lines = [f'{r["key"]:42s} shell={r["shell"]:9s} pred={r["prediction"] or "-":18s} '
             f'cap={len(r["cap_asset"])} cor={len(r["cor_asset"])} dex={",".join(r["dex"]) or "-"}' for r in rows]
    (HERE/"per-key.txt").write_text("\n".join(lines)+"\n")
    print(f"scanned {len(rows)} keys; shells={len(shells)} (capacitor {out['capacitor']}, cordova {out['cordova']})")
    print(f"lit/lit?-predicted shells (white-window risk): {out['lit_or_litq_shells'] or 'none'}")
    for a in ["cv2-ca-vaults-randomlydie","cv2-com-degeder-yam","cv2-com-paultirk-yatoo"]:
        r=next((x for x in rows if x["key"]==a),None); print(f"  [+anchor] {a}: {r['shell'] if r else 'MISSING'}")
    for a in ["cv2-com-caniwebview-android","cv2-eu-dfdx-jslab"]:
        r=next((x for x in rows if x["key"]==a),None); print(f"  [-anchor] {a}: {r['shell'] if r else 'MISSING'}")

if __name__=="__main__": main()
