#!/usr/bin/env python3
"""#83 auto-triage: fatal point -> class -> Westlake segment -> fix-batch coverage.

Input: a bms_batch run directory (the one containing <key>/ subdirs with
record.json + hilog.txt), or a direct path list. Reuses p75_fatal.py logic
(last uncaught fatal before exit) and the westlake-map-78.json knowledge
base. Output: per-app rows + segment ranking, JSON to stdout or --out.
"""
import json, os, re, sys, glob
from pathlib import Path

MAP = Path(__file__).resolve().parents[2] / "2026-09-29-wikipedia-diff" / "westlake-map-78.json"

# classification rules: (class_name, regex on the fatal line, westlake segment key)
RULES = [
    ("flutter-domain",     r"path is outside app domain",
                           "native-lib-path domain (PackageInfoBuilder L205-242 + mapAbi L309-313 + spawn_server L194-195)"),
    ("dlopen-ns",          r"dlopen_ns failed",
                           "native-lib-path domain (PackageInfoBuilder L205-242 + spawn_server L194-195)"),
    ("theme-appcompat",    r"You need to use a Theme\.AppCompat|Attribute not found",
                           "theme pair (#81 five-step; r13 resolveActivityTheme)"),
    ("jobscheduler",       r"WorkManager is not initialized|JobScheduler",
                           "JobScheduler stub (AppSpawnXInit L2058-2110; r13 carries)"),
    ("bindService",        r"bindService\(\) failed",
                           "bindService bridge (ActivityManagerAdapter L355-375)"),
    ("velocitytracker",    r"VelocityTracker\.native",
                           "VelocityTracker runtime registration (android_view_VelocityTracker.cpp)"),
    ("window-type",        r"InvalidDisplayException|window type .* is not valid",
                           "addToDisplay bridge (WindowSessionAdapter L593-660)"),
    ("notification-npe",   r"INotificationManager",
                           "notification (no Westlake adapter; r13 stubs)"),
    ("appclass-missing",   r"KoinApplication has not been started|Unable to make application|ClassNotFound.*App",
                           "manifest appClassName application (AppSchedulerBridge L1568-1571)"),
    ("prefs-npe",          r"SharedPreferences\.getString.*null|getSharedPreferences",
                           "route-A-only gap (B6-family ContextImpl prefs; investigate null source)"),
    ("viewmodel",          r"Cannot create an instance of class|ViewModelProvider",
                           "route-A-only (ViewModel factory chain; needs stack)"),
    ("clinit-failure",     r"ExceptionInInitializerError|<clinit>",
                           "route-A-only (<clinit> initializer threw — NOT multidex; root is the initializer's own exception)"),
    ("multidex",           r"NoClassDefFoundError.*AppConfig|Didn't find class",
                           "route-A-only (multi-dex/classloader order; needs stack)"),
    ("musl-reloc",         r"symbol not found\. dso=/data/app|Error loading shared library[^:]*: \(needed by /data/app",
                           "musl/bionic symbol compat (#84: app-owned .so only)"),
    ("musl-system-noise",  r"MUSL-LDSO.*(?:libmmi_knuckle|security_component|libartbased|libhwui)",
                           "system-lib loader noise (not an app wall)"),
    ("provider-startup",   r"Unable to get provider androidx\.startup|InitializationProvider",
                           "provider chain (PackageManagerAdapter L1123-1133; B8 item 1)"),
]
# fix-batch coverage (best-effort from board notes 2026-09-29)
FIX_BATCH = {
    "theme pair (#81 five-step; r13 resolveActivityTheme)": "r13",
    "JobScheduler stub (AppSpawnXInit L2058-2110; r13 carries)": "r13",
    "notification (no Westlake adapter; r13 stubs)": "r13",
    "bindService bridge (ActivityManagerAdapter L355-375)": "r15 (assigned)",
    "VelocityTracker runtime registration (android_view_VelocityTracker.cpp)": "r15 (assigned)",
    "addToDisplay bridge (WindowSessionAdapter L593-660)": "r15 (assigned)",
    "native-lib-path domain (PackageInfoBuilder L205-242 + mapAbi L309-313 + spawn_server L194-195)": "r15 (proposed)",
    "native-lib-path domain (PackageInfoBuilder L205-242 + spawn_server L194-195)": "r15 (proposed)",
    "manifest appClassName application (AppSchedulerBridge L1568-1571)": "check r13/r14",
    "provider chain (PackageManagerAdapter L1123-1133; B8 item 1)": "B8 item 1 (r8b+)",
}

NOISE = re.compile(r"VTLEN|IFACE-BITS|IFACE-IF|IFACE-RAW|VTBLDIAG|class_linker|OH_RegHook|EARLY-TF|COROUTINE-FIX|WL-THEME-SYNC")

def ts_of(line):
    m = re.match(r"\S+ (\d\d:\d\d:\d\d\.\d\d\d)", line)
    return m.group(1) if m else None

def triage_run(run_dir):
    rows = []
    for d in sorted(p for p in Path(run_dir).iterdir() if (p / "record.json").is_file()):
        rec = json.load(open(d / "record.json"))
        k, uid = rec.get("key"), (rec.get("bms") or {}).get("uid")
        hl = d / "hilog.txt" if (d / "hilog.txt").is_file() else d / "hilog-excerpt.txt"
        first_ex = fatal = None; exit_ts = exit_line = pid = None
        alive = None
        if hl.is_file():
            lines = [ln for ln in open(hl, errors="replace") if "HDC_LOG" not in ln]
            first_ex = next((ln.strip()[:240] for ln in lines if "WL-THEME-SYNC" in ln), None)
            for ln in lines:
                m = re.search(r"with pid (\d+) exit with code", ln)
                if m: pid = m.group(1); exit_ts = ts_of(ln); exit_line = ln.strip()[:200]; break
            if pid is None:
                for ln in lines:
                    m = re.search(r"nativeOnScheduleLaunchApplication ENTRY.*pid=(\d+)", ln)
                    if m: pid = m.group(1); break
            def norm(ln):
                # strip an optional leading "NNNNN: " line-number prefix (#78 excerpts)
                return re.sub(r"^\s*\d+:\s*", "", ln)
            # RULE 1 (cc-wiki r16): if ensureBindApplication FAILED is present, the
            # root cause is the FIRST 'Caused by' under that marker (antennapod:
            # libconscrypt_jni.so __open_2 relocation) — NOT the last downstream
            # exception (a much later NPE from the half-bound app).
            bind_failed_at = next((i for i, l in enumerate(lines)
                                   if "ensureBindApplication FAILED" in l), None)
            if bind_failed_at is not None:
                for l in lines[bind_failed_at:bind_failed_at + 80]:
                    l2 = norm(l)
                    if "Caused by:" in l2:
                        fatal = l2.strip()[:240]
                        break
            for ln in (lines if fatal is None else []):
                l2 = norm(ln)
                t = ts_of(l2)
                if not t: continue
                if exit_ts and t > exit_ts: continue
                if pid and not re.search(r"\b%s\b" % pid, l2): continue
                if NOISE.search(l2): continue
                if "nativeParseManifestJson failed" in l2 or "providers populated" in l2: continue
                if re.search(r"UnsatisfiedLinkError|ClassNotFoundException|IllegalStateException|"
                             r"RuntimeException|NullPointerException|NoClassDefFoundError|"
                             r"InflateException|InvalidDisplayException|IllegalArgumentException|"
                             r"Fatal signal|MUSL-LDSO|relocating failed|main_threw|UNCAUGHT in thread|Unable to start activity|Unable to get provider", l2, re.I):
                    # keep the LAST (deepest) cause line: wrappers come first
                    fatal = l2.strip()[:240]
        # alive from processes files
        for tag in ("t20", "t5"):
            p = d / ("processes-%s.txt" % tag)
            if p.is_file():
                alive = any(f.split()[2] == str(uid) for f in open(p, errors="replace")
                            if len(f.split()) >= 3 and f.split()[2].isdigit())
                if alive: break
        cls = seg = None
        # RULE 3 (cc-wiki r16): a non-main-thread native crash shows as DFX
        # signo lines (not a Java fatal). Prefer the DFX signal line over any
        # nearby WARN, and surface the cppcrash top frame when present.
        dfx = next((ln.strip()[:200] for ln in lines
                    if re.search(r"DfxSignalHandler.*signo\(", ln)), None)
        cpp = None
        for cf in sorted(glob.glob(str(d) + "/cppcrash-*.txt")):
            try:
                reason = next(l.strip() for l in open(cf, errors="replace")
                              if l.startswith("Reason:"))
                top = next(l.strip()[:200] for l in open(cf, errors="replace")
                           if l.startswith("#00"))
                cpp = reason + " | " + top
                break
            except StopIteration:
                continue
        if dfx or cpp:
            row_native = {"dfx_signal": dfx, "cppcrash_top": cpp}
        else:
            row_native = None
        if fatal:
            for name, rx, segment in RULES:
                if re.search(rx, fatal):
                    cls, seg = name, segment; break
            if not cls:
                cls, seg = "unclassified", "(needs manual review)"
        else:
            cls, seg = ("alive-or-quiet", "-") if alive else ("no-fatal-found", "(check hilog coverage)")
        if row_native is not None:
            cls, seg = "native-signal-crash", "native crash (see cppcrash top frame; not a Java wall)"
        rows.append({"key": k, "uid": uid, "pid": pid, "alive": alive,
                     "first_exception": first_ex, "fatal": fatal,
                     "native": row_native,
                     "class": cls, "westlake_segment": seg,
                     "fix_batch": FIX_BATCH.get(seg, "not-yet"),
                     "exit_line": exit_line})
    return rows

def rank(rows):
    from collections import Counter
    c = Counter(r["westlake_segment"] for r in rows if r["class"] not in ("alive-or-quiet",) )
    return [{"segment": s, "apps": n} for s, n in c.most_common()]

def main():
    args = sys.argv[1:]
    out = None
    if args and args[0] == "--out":
        out = args[1]; args = args[2:]
    if not args:
        print("usage: auto_triage.py [--out FILE] <run-dir> [<run-dir>...]", file=sys.stderr); return 2
    doc = {"knowledge_base": str(MAP), "runs": {}}
    for run in args:
        rows = triage_run(run)
        doc["runs"][run] = {"rows": rows, "segment_ranking": rank(rows)}
    text = json.dumps(doc, indent=1, ensure_ascii=False)
    if out: open(out, "w").write(text)
    for run, r in doc["runs"].items():
        print("== %s" % run)
        for row in r["rows"]:
            print(" %-18s %-16s alive=%-5s %s" % (row["key"], row["class"], row["alive"], (row["fatal"] or "")[:90]))
        print(" ranking:", json.dumps(r["segment_ranking"], ensure_ascii=False)[:400])
    print("rows written", "to %s" % out if out else "(stdout only)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
