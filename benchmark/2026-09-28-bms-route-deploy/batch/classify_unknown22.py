#!/usr/bin/env python3
"""#48: classify the 22 unknown keys — first fatal line per app from hilog +
new faultlogger files. Merge into b4-final (v3).
"""
import json, os, re, collections, sys

RUN = "/home/zhaoyue/a2hlab/board/b4-48-unknown22-61b-20260929T1015"
FAULTS = "/home/zhaoyue/a2hlab/board/b4-48-faultlog/new"
KEYS = ['termux', 'ooniprobe', 'opencamera', 'fd-android', 'fd-etar', 'fd-feeder',
        'fd-fluffychat', 'fd-im-vector-app', 'fd-immich', 'fd-k9', 'fd-kitchenowl',
        'fd-libre', 'fd-minetest', 'fd-saber', 'fd-shatteredpixeldungeon', 'fd-tusky',
        'fd-tutanota', 'fd-wifianalyzer', 'fd-stk', 'burgerking', 'ppsspp', 'mindustry']

def first_fatal(hpath):
    """First meaningful fatal line in a per-app hilog dump."""
    if not os.path.isfile(hpath):
        return None, None
    pats = [
        ("java-fatal", re.compile(r"FATAL EXCEPTION|AndroidRuntime.*(died|Exception)")),
        ("unsatisfied-link", re.compile(r"UnsatisfiedLinkError[^\n]{0,140}")),
        ("class-not-found", re.compile(r"ClassNotFoundException[^\n]{0,140}")),
        ("b6-activity-attach", re.compile(r"ContextWrapper\.getApplicationInfo|ContextImpl\.getTheme|handleConfigurationChanged")),
        ("getsharedprefs-crash", re.compile(r"getSharedPreferences.*(SIGSEGV|crash|Fault)")),
        ("fdsan", re.compile(r"fdsan_error|attempted to close file descriptor")),
    ]
    try:
        lines = open(hpath, errors="replace").read().splitlines()
    except OSError:
        return None, None
    for ln in lines:
        # constant noise: hdc echoes, sigchain, kickdog, hook registration INFO
        if ("HDC_LOG" in ln or "MUSL-SIGCHAIN" in ln or "appspawn_kickdog" in ln
                or "OH_RegHook" in ln):
            continue
        for bucket, rx in pats:
            m = rx.search(ln)
            if m:
                return bucket, ln.strip()[:240]
    return None, None

def main(out_path):
    trials = {t["key"]: t for t in json.load(open(os.path.join(RUN, "results.json")))["trials"]}
    # map faultlogger files to keys by uid
    faultmap = {}
    uid2key = {str(t["uid"]): t["key"] for t in trials.values() if t.get("uid")}
    for fn in sorted(os.listdir(FAULTS)):
        p = os.path.join(FAULTS, fn)
        txt = open(p, errors="replace").read()
        uid = re.search(r"^Uid:(\d+)", txt, re.M)
        frame = re.search(r"^#00 .*$", txt, re.M)
        key = uid2key.get(uid.group(1)) if uid else None
        if not key:
            continue
        f = frame.group(0)[:240] if frame else ""
        if "fdsan_error" in f:
            b = "fdsan"
        elif "getSharedPreferences" in f:
            b = "b6-family-context"  # ContextImpl during attach-phase init
        elif "handleConfigurationChanged" in f or "getTheme" in f or "getApplicationInfo" in f:
            b = "b6-activity-attach"
        else:
            b = "other-native"
        # keep the FIRST crash file per key (earliest by name sort = oldest ms)
        faultmap.setdefault(key, {"file": fn, "first_blocker": b, "evidence": f})

    out = {}
    for k in KEYS:
        t = trials[k]
        alive = bool(t.get("pids_at_15s"))
        hl_bucket, hl_line = first_fatal(os.path.join(RUN, k, "hilog.txt"))
        fl = faultmap.get(k)
        if alive:
            out[k] = {"pids_at_15s": t["pids_at_15s"], "first_blocker": None,
                      "category": "alive-at-sample",
                      "evidence": "alive at t+15; no fatal line; faultlog: %s" % (fl["file"] if fl else "none")}
        elif fl:
            out[k] = {"pids_at_15s": [], "first_blocker": fl["first_blocker"],
                      "category": "exited-early", "evidence": fl["evidence"],
                      "faultlog_file": fl["file"]}
        elif hl_bucket:
            out[k] = {"pids_at_15s": [], "first_blocker": hl_bucket,
                      "category": "exited-early", "evidence": hl_line,
                      "source": "hilog"}
        elif hl_bucket:
            out[k] = {"pids_at_15s": [], "first_blocker": hl_bucket,
                      "category": "exited-early", "evidence": hl_line,
                      "source": "hilog"}
        else:
            # dead with NO crash file: derive the exit chain from hilog —
            # appspawn_service.c:118 "<pkg> with pid N exit with code:1" (clean self-exit)
            ev = None
            hpath = os.path.join(RUN, k, "hilog.txt")
            if os.path.isfile(hpath):
                pkg = t.get("package", "")
                for ln in open(hpath, errors="replace"):
                    if "HDC_LOG" in ln or "MUSL-SIGCHAIN" in ln or "appspawn_kickdog" in ln:
                        continue
                    if "appspawn_service.c:118]" in ln and pkg in ln and "exit with code" in ln:
                        ev = ln.strip()[:240]; break
            if ev:
                out[k] = {"pids_at_15s": [], "first_blocker": "clean-exit-1",
                          "category": "exited-early", "evidence": ev, "source": "hilog"}
            else:
                out[k] = {"pids_at_15s": [], "first_blocker": "unknown",
                          "category": "exited-early",
                          "evidence": "no faultlogger file; no fatal hilog line; no exit-with-code line"}
    hist = dict(collections.Counter(v["first_blocker"] for v in out.values()))
    res = {"run": RUN, "keys": out, "histogram": hist}
    json.dump(res, open(out_path, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(hist, indent=1))
    for k, v in out.items():
        print(f"{k:24s} {str(v['first_blocker']):26s} {str(v['pids_at_15s'] or ''):8s} {str(v.get('faultlog_file') or v.get('source',''))[:22]}")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/c48.json")
