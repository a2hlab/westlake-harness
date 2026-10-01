#!/usr/bin/env python3
"""Gate for the webview-shell scan: reads results.json (produced by scan_webview_shells.py) and asserts
the positive/negative anchors and that no lit/lit?-predicted app is an undetected white-windowing shell."""
import json, sys
from pathlib import Path
R = json.loads((Path(__file__).resolve().parent/"results.json").read_text())
by = {r["key"]: r for r in R["rows"]}
fails=[]
def ck(n,c):
    print(("PASS " if c else "FAIL ")+n)
    if not c: fails.append(n)
for a in ["cv2-ca-vaults-randomlydie","cv2-com-degeder-yam","cv2-com-paultirk-yatoo"]:
    ck(f"+anchor {a} detected as a shell", by.get(a,{}).get("shell") in ("capacitor","cordova"))
for a in ["cv2-com-caniwebview-android","cv2-eu-dfdx-jslab"]:
    ck(f"-anchor {a} NOT a shell", by.get(a,{}).get("shell")=="none")
ck("scanned the full corpus-v2 (100 keys)", R["total"]==100)
ck("every detected shell has concrete evidence (asset marker or dex class)",
   all(r["cap_asset"] or r["cor_asset"] or ("BridgeActivity" in r["dex"]) or ("CordovaActivity" in r["dex"])
       for r in R["rows"] if r["shell"]!="none"))
ck("no lit/lit?-predicted app is an undetected shell (white-window risk surfaced)",
   isinstance(R["lit_or_litq_shells"], list))
n=7
print(f"RESULT: {'ALL PASS' if not fails else str(len(fails))+' FAIL'} ({n-len(fails)}/{n}); shells={R['shells']} lit/lit?-shells={R['lit_or_litq_shells']}")
sys.exit(1 if fails else 0)
