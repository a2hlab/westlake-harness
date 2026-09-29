#!/usr/bin/env python3
"""#75 offline: last UNCAUGHT fatal per early-death app from #73's 16M logs.

For each of the 12 early-death keys in b4-73-white14/20260929T155757-42aaa7c3:
  - exit line: appspawn_service.c:118 <pkg> with pid N exit with code:1
  - last uncaught exception BEFORE that timestamp+pid:
    FATAL EXCEPTION / Uncaught / J_invokeStaticMain_main_threw /
    "Unable to start activity" / AndroidRuntime E lines with a stack
  - first exception ([WL-THEME-SYNC] sync parse failed) recorded separately
  - theme-error flag: "You need to use a Theme.AppCompat" family
Output: benchmark/2026-09-29-manifest-classes/p73-fatal.json
"""
import json, os, re, sys
from pathlib import Path

RUN = "/home/zhaoyue/a2hlab/board/b4-73-white14/20260929T155757-42aaa7c3/61b0657200000000000000000324012c"
DEAD = ["ooniprobe", "fd-etar", "fd-fluffychat", "fd-immich", "fd-kitchenowl",
        "fd-minetest", "fd-mobile", "fd-stk", "localsend", "mindustry", "noice", "burgerking"]

def ts_of(line):
    m = re.match(r"(\d\d-\d\d) (\d\d:\d\d:\d\d\.\d\d\d)", line)
    return m.group(2) if m else None

def main(out_path):
    rows = {}
    for k in DEAD:
        hl = os.path.join(RUN, k, "hilog.txt")
        lines = [ln for ln in open(hl, errors="replace") if "HDC_LOG" not in ln]
        # child pid + exit timestamp
        pid = None; exit_ts = None; exit_line = None
        for ln in lines:
            m = re.search(r"appspawn_service\.c:118\]\S+ with pid (\d+) exit with code", ln)
            if m:
                pid = m.group(1); exit_ts = ts_of(ln); exit_line = ln.strip(); break
        if pid is None:
            # alternate form: '... with pid 26629 exit with code:1' (any phrasing)
            for ln in lines:
                m = re.search(r"with pid (\d+) exit with code", ln)
                if m:
                    pid = m.group(1); exit_ts = ts_of(ln); exit_line = ln.strip(); break
        # first exception: WL-THEME-SYNC
        first_ex = next((ln.strip()[:240] for ln in lines if "WL-THEME-SYNC" in ln), None)
        # last UNCAUGHT fatal before exit, in the child's own stderr/log lines
        fatal = None; fatal_line = None
        if pid:
            pat = re.compile(
                r"FATAL EXCEPTION|Uncaught|J_invokeStaticMain_main_threw|Unable to start activity"
                r"|AndroidRuntime.*Process:|java\.lang\.\w+Exception|java\.lang\.\w+Error"
                r"|IllegalArgumentException|IllegalStateException|Resources\$NotFoundException", re.I)
            for ln in lines:
                t = ts_of(ln)
                if not t or (exit_ts and t > exit_ts):
                    continue
                if re.search(r"\b%s\b" % pid, ln) and "WL-THEME-SYNC" not in ln and "EARLY-TF" not in ln and "COROUTINE-FIX" not in ln:
                    if pat.search(ln) and "OH_RegHook" not in ln and "hook" not in ln.lower():
                        fatal = ln.strip()[:240]; fatal_line = ln
        theme = bool(fatal and re.search(r"Theme\.AppCompat|theme.*AppCompat|You need to use a Theme", fatal, re.I))
        rows[k] = {"pid": pid, "exit_ts": exit_ts, "exit_line": (exit_line or "")[:200],
                   "first_exception": first_ex, "fatal": fatal, "fatal_theme_class": theme}
        print("%-16s pid=%-6s exit=%s theme=%-5s fatal=%s" % (
            k, pid, exit_ts, theme, (fatal or "NOT-FOUND")[:120]))
        if fatal:
            # print the 3 lines after the fatal marker for context (stack frames)
            if fatal_line is not None:
                i = lines.index(fatal_line)
                for ln in lines[i+1:i+4]:
                    if "AppSpawnXJava" in ln or "appspawn-x" in ln:
                        print("      >", ln.strip()[:150])
    doc = {"source_run": RUN, "apps": rows,
           "note": "fatal = last uncaught exception line before exit code:1 in the child pid stream, excluding WL-THEME-SYNC/EARLY-TF/COROUTINE-FIX known-nonfatal markers"}
    json.dump(doc, open(out_path, "w"), indent=1, ensure_ascii=False)
    n_theme = sum(1 for v in rows.values() if v["fatal_theme_class"])
    n_found = sum(1 for v in rows.values() if v["fatal"])
    print("fatal-found: %d/12, theme-class: %d/12" % (n_found, n_theme))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "p73-fatal.json")
