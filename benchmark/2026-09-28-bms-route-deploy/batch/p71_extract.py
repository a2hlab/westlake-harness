#!/usr/bin/env python3
"""#71: per-app markers from the r8b rerun hilog (b4-71-white14).

For each key dir: [B43-BIND] providers populated count, [B8-R8B]
manifest-fallback presence, first fatal exception line (or alive),
ScheduleLaunchAbility arrival. Compares against #69 predictions.
"""
import json, glob, os, re, sys
from pathlib import Path

RUN_ROOT = sorted(glob.glob("/home/zhaoyue/a2hlab/board/b4-71-white14/2026*"))[-1]

PRED_69 = {
    "fd-binaryeye": "manifest-only", "fd-catima": "manifest-only", "noice": "manifest-only",
    "fd-mobile": "manifest-only", "ooniprobe": "manifest-only", "fd-k9": "manifest-only(Koin)",
    "fd-android": "manifest-only(Koin)", "opencamera": "manifest-only-or-AppCompat",
    "fd-etar": "manifest+armeabi-ns", "burgerking": "AppCompat+armeabi-ns",
    "fd-fluffychat": "flutter-domain", "fd-immich": "flutter-domain",
    "fd-kitchenowl": "flutter-domain", "fd-libre": "flutter-domain",
    "fd-saber": "flutter-domain", "localsend": "flutter-domain",
    "fd-minetest": "AppCompat", "fd-stk": "anomalous-manifest", "mindustry": "anomalous-manifest",
}
SIX_FOCUS = ["fd-mobile", "fd-stk", "localsend", "mindustry", "noice", "fd-binaryeye"]

def markers(hpath):
    if not os.path.isfile(hpath):
        return {}
    txt = open(hpath, errors="replace").read()
    lines = [ln for ln in txt.splitlines() if "HDC_LOG" not in ln]
    out = {}
    prov = [ln.strip() for ln in lines if "providers populated" in ln]
    out["providers_populated_lines"] = [l[:200] for l in prov[:3]]
    m = re.search(r"providers populated: (\d+)", prov[0]) if prov else None
    out["providers_count"] = int(m.group(1)) if m else None
    fb = [ln.strip()[:200] for ln in lines if "manifest-fallback" in ln or "B8-R8B" in ln]
    out["manifest_fallback"] = fb[:3]
    sla = [ln.strip()[:180] for ln in lines if "ScheduleLaunchAbility" in ln or "B47-SLA" in ln]
    out["sla_arrived"] = bool(sla)
    out["sla_line"] = sla[0] if sla else None
    fatal = None
    for ln in lines:
        if re.search(r"FATAL EXCEPTION|UnsatisfiedLinkError|ClassNotFoundException|"
                     r"NullPointerException|IllegalStateException|RuntimeException|"
                     r"exit with code|Fatal signal|ART Crash|abort", ln):
            fatal = ln.strip()[:240]; break
    out["first_fatal"] = fatal
    return out

def main(outpath):
    apps = {}
    for d in sorted(glob.glob(RUN_ROOT + "/*/record.json")) + sorted(glob.glob(RUN_ROOT + "/*/*/record.json")):
        r = json.load(open(d))
        k = r.get("key")
        hl = os.path.join(os.path.dirname(d), "hilog.txt")
        rec = {
            "key": k, "status": r.get("status"), "clicked": r.get("clicked"),
            "shots": len(r.get("screenshots") or []),
            "shots_captured": sum(1 for s in (r.get("screenshots") or []) if s.get("local")),
        }
        rec.update(markers(hl))
        rec["pred69"] = PRED_69.get(k)
        rec["focus6"] = k in SIX_FOCUS
        apps[k] = rec
    doc = {"run": RUN_ROOT, "apps": apps}
    json.dump(doc, open(outpath, "w"), indent=1, ensure_ascii=False)
    for k, v in apps.items():
        star = "*" if v["focus6"] else " "
        print("%s %-18s prov=%-4s fb=%-4s sla=%-5s fatal=%s" % (
            star, k, v.get("providers_count"), bool(v.get("manifest_fallback")),
            v.get("sla_arrived"), (v.get("first_fatal") or "ALIVE?")[:110]))
    print("---providers detail---")
    for k, v in apps.items():
        for l in v.get("providers_populated_lines") or []:
            print("%-18s %s" % (k, l[:160]))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/p71.json")
