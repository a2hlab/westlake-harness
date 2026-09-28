#!/usr/bin/env python3
"""Entry #12 aggregator: join startup-reach outputs with 09-27 sweep labels,
attribute each outer-loop candidate API to a startup stage per app, and rank
candidates by startup_blocked desc / startup_lit asc.

Runs ON THE VM (pure stdlib json; reads VM-local scans + reach outputs).
Writes results.json directly into the Mac worktree via the OrbStack share.

Stage codes: 0=process start, 1=first activity, 2=next screens, 3=later,
255=not reached statically. "startup-reachable" = stage in {0, 1}.
"""
import json
import sys
from pathlib import Path

SCANS = Path("/home/zhaoyue/a2hlab/static/scans")
REACH = Path("/home/zhaoyue/a2hlab/static/reach-20260928")
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else
           "/Users/zhaoyue/orca/workspaces/westlake-harness-lev/benchmark/2026-09-28-api-leverage/results.json")

# ---- 09-27 sweep labels (README 收官总表: 66 launches, 13 distinct LIT) ----
LIT = {
    "wikipedia", "termux", "ooniprobe", "antennapod", "aegis", "fd-AppManager",
    "fd-auxio", "fd-com-amaze-filemanager", "fd-com-kunzisoft-keepass-libre",
    "fd-droidify", "fd-fitness", "fd-netguard", "fd-noice",
}
# swept keys = keys.fdroid.txt (66); blocked = swept minus LIT (dupes noice/burgerking noted)
SWEPT = {
    "toutiao", "mcdonalds", "burgerking", "subwaysurfers", "firefox", "vlc",
    "wikipedia", "localsend", "ppsspp", "mindustry", "termux", "ooniprobe",
    "anki", "antennapod", "newpipe", "aegis", "markor", "opencamera",
    "fd-AppManager", "fd-android", "fd-api", "fd-app", "fd-auxio",
    "fd-binaryeye", "fd-breezyweather", "fd-calendar", "fd-catima", "fd-client",
    "fd-com-amaze-filemanager", "fd-com-kunzisoft-keepass-libre", "fd-droidify",
    "fd-etar", "fd-feeder", "fd-fennec_fdroid", "fd-filemanager", "fd-fitness",
    "fd-fluffychat", "fd-gallery", "fd-im-vector-app", "fd-immich", "fd-k9",
    "fd-kitchenowl", "fd-libre", "fd-libretube", "fd-meet", "fd-minetest",
    "fd-mobile", "fd-mpv", "fd-musicplayer", "fd-netguard", "fd-noice",
    "fd-notes", "fd-organicmaps", "fd-plus", "fd-reader", "fd-saber", "fd-seal",
    "fd-shatteredpixeldungeon", "fd-stk", "fd-tasks", "fd-tusky", "fd-tutanota",
    "fd-uhabits", "fd-wifianalyzer", "x", "noice",
}
# noice == fd-noice (same app); burgerking = mislabeled McDonald's APK.
DUPES = {"noice": "fd-noice", "burgerking": "mcdonalds"}

# ---- candidate definitions (from entry #12 body) ----
JAVA_METHOD_CANDIDATES = {
    "pm:resolveService": ("Landroid/content/pm/PackageManager;", "resolveService"),
    "pm:getInstallerPackageName": ("Landroid/content/pm/PackageManager;", "getInstallerPackageName"),
    "pm:getInstallSourceInfo": ("Landroid/content/pm/PackageManager;", "getInstallSourceInfo"),
    "pm:getNameForUid": ("Landroid/content/pm/PackageManager;", "getNameForUid"),
    "view:dispatchDraw": (None, "dispatchDraw"),
    "view:onWindowSystemUiVisibilityChanged": (None, "onWindowSystemUiVisibilityChanged"),
    "activity:onWindowFocusChanged": (None, "onWindowFocusChanged"),
    "netcb:onAvailable": ("Landroid/net/ConnectivityManager$NetworkCallback;", "onAvailable"),
    "netcb:onCapabilitiesChanged": ("Landroid/net/ConnectivityManager$NetworkCallback;", "onCapabilitiesChanged"),
}
SERVICE_CANDIDATES = ["download", "account", "bluetooth", "sensor", "camera"]
WINDOW_EXT_PREFIX = "androidx.window.extensions"
NATIVE_PREFIXES = ["ANativeWindow_", "AMediaCodec", "AMediaFormat", "ASensor", "AHardwareBuffer"]

STAGE_NAMES = {0: "process start", 1: "first activity", 2: "next screens",
               3: "later", 255: "not reached statically"}


def stage_of_platform(platform_stage, owner_cls, method):
    """Min stage over platform nodes whose method name matches (and class matches if given)."""
    best = None
    for key, stage in platform_stage.items():
        if "->" not in key:
            continue
        cls, sig = key.split("->", 1)
        name = sig.split("(")[0]
        if name != method:
            continue
        if owner_cls is not None and cls != owner_cls:
            continue
        if owner_cls is None and not (cls.startswith("Landroid/view/") or cls.startswith("Landroid/app/")
                                      or cls.startswith("Landroid/net/")):
            # dispatchDraw/onWindowFocusChanged etc. counted on framework classes
            if method in ("dispatchDraw", "onWindowSystemUiVisibilityChanged", "onWindowFocusChanged"):
                if not cls.startswith("Landroid/"):
                    continue
        best = stage if best is None else min(best, stage)
    return best


def main():
    apps = {}
    missing = []
    for scan_path in sorted(SCANS.glob("*.json")):
        key = scan_path.stem
        reach_path = REACH / f"{key}.reach.json"
        if not reach_path.exists():
            missing.append(key)
            continue
        label = "lit" if key in LIT else ("blocked" if key in SWEPT else "unswept")
        reach = json.loads(reach_path.read_text())
        scan = json.loads(scan_path.read_text())
        apps[key] = {"label": label, "reach": reach, "scan": scan}

    candidates = {}

    def note(cand, key, stage):
        if stage is None:
            return
        c = candidates.setdefault(cand, {"apps": {}})
        prev = c["apps"].get(key)
        if prev is None or stage < prev:
            c["apps"][key] = stage

    for key, app in apps.items():
        reach, scan = app["reach"], app["scan"]
        platform_stage, caller_stage, library_stage = (
            reach["platform_stage"], reach["caller_stage"], reach["library_stage"])
        inv = scan.get("inventory", {})

        # Java method candidates via platform_stage
        for cand, (cls, method) in JAVA_METHOD_CANDIDATES.items():
            note(cand, key, stage_of_platform(platform_stage, cls, method))

        # Service-name candidates: join scan service_requests call sites -> caller_stage
        for req in inv.get("service_requests", []):
            if not isinstance(req, dict) or req.get("service") not in SERVICE_CANDIDATES:
                continue
            ck = f"{req['owner']}->{req['method']}{req.get('descriptor','')}"
            stage = caller_stage.get(ck)
            if stage is not None:
                note(f"svc:{req['service']}", key, stage)

        # androidx.window.extensions probe sites -> caller_stage
        for site in inv.get("existence_probes", []):
            if not isinstance(site, dict):
                continue
            cn = site.get("class_name", "")
            if cn.startswith(WINDOW_EXT_PREFIX):
                ck = f"{site['owner']}->{site['method']}{site.get('descriptor','')}"
                stage = caller_stage.get(ck)
                if stage is not None:
                    note("probe:androidx.window.extensions", key, stage)

        # Native symbol candidates: importing library -> library_stage
        for imp in inv.get("native_imports", []):
            sym = imp.get("symbol", "")
            pref = next((p for p in NATIVE_PREFIXES if sym.startswith(p)), None)
            if pref is None:
                continue
            for lib in imp.get("importing_libraries", []):
                soname = lib.get("elf", "").rsplit("/", 1)[-1]
                stage = library_stage.get(soname)
                if stage is not None:
                    note(f"native:{pref}*", key, stage)

    # rank
    ranked = []
    for cand, c in candidates.items():
        per = c["apps"]
        sb = sum(1 for k, s in per.items() if apps[k]["label"] == "blocked" and s in (0, 1))
        sl = sum(1 for k, s in per.items() if apps[k]["label"] == "lit" and s in (0, 1))
        ranked.append({
            "candidate": cand,
            "startup_blocked": sb,
            "startup_lit": sl,
            "non_lethal_note": "also startup-reachable in LIT apps" if sl > 0 else "",
            "apps": {k: {"stage": s, "stage_name": STAGE_NAMES.get(s, str(s)),
                         "label": apps[k]["label"]} for k, s in sorted(per.items())},
        })
    ranked.sort(key=lambda r: (-r["startup_blocked"], r["startup_lit"], r["candidate"]))

    swept_scanned = [k for k in apps if k in SWEPT]
    out = {
        "task": "app-lighting #12 (oc-t0): startup-path reachability of high-leverage candidate APIs",
        "date": "2026-09-28",
        "method": {
            "tool": "harness/westlake_gap reach.analyse (startup-reach CLI), VM-local run",
            "stages": STAGE_NAMES,
            "startup_reachable": "stage in {process start, first activity}",
            "labels": "09-27 breadth sweep (66 launches, 13 distinct LIT); unswept apps (co-* commercial) excluded from ranking counts",
            "dupes": DUPES,
        },
        "coverage": {
            "scans_total": len(list(SCANS.glob('*.json'))),
            "reach_computed": len(apps),
            "reach_missing": missing,
            "swept_and_scanned": len(swept_scanned),
            "lit_in_set": sum(1 for k in swept_scanned if apps[k]["label"] == "lit"),
            "blocked_in_set": sum(1 for k in swept_scanned if apps[k]["label"] == "blocked"),
        },
        "candidates": ranked,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))
    print(f"wrote {OUT}: {len(ranked)} candidates, coverage reach={len(apps)} missing={len(missing)}")
    for r in ranked[:12]:
        print(f"  {r['candidate']:42s} blocked={r['startup_blocked']:2d} lit={r['startup_lit']:2d}")


if __name__ == "__main__":
    main()
