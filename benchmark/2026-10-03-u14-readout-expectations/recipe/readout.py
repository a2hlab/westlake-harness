#!/usr/bin/env python3
"""U14 readout: auto-extract each mover's first-fatal / dialog z-order from a U14 window run dir and
compare it to expectations.csv -> a match / moved-past / unchanged / moved-elsewhere table.

    readout.py <window-run-dir> [--expectations expectations.csv] [--json out.json]
               [--repo /path/to/westlake-harness] [--key KEY ...] [--quiet]

Why this shape (DIGEST-762 lesson): the first-fatal is NOT a naive grep. Tokens like "ICU",
"eglCreateWindowSurface", "Impeller", "UnsatisfiedLinkError" appear ~12x in EVERY run as benign log
lines, so a count would false-positive. We anchor the first-fatal to scripts/lab/first_fatal.py
(proper terminal selection + root-cause chain), corroborate the native wall with
scripts/lab/dlopen_failures.py --near-fatal, the bind outcome with scripts/lab/bind_status.py, and
only then test the *specific* pre-fix / post-fix symbol markers from expectations.csv. The M5 dialog
movers are a different axis: they do not terminate (terminal stays null) and the signal is the
dialog-vs-activity z-order (createSession androidType + UpdateZOrderInner, DIGEST 690/714/721), not a
first-fatal location.

Two axes (expectations.csv column `axis`):
  * first-fatal (10 keys: Flutter A x4, C x2, D x2, I toutiao, J fd-plus): has the fix moved the
    first fatal past the pre-fix wall to the expected next wall?
  * zorder     (14 keys: 13 M5 watchlist + dddmodel2, cluster G): is the onCreate dialog now
    z-ordered ABOVE the activity (and the app still alive)?

Verdicts:
  first-fatal: unchanged (pre-fix wall still the fatal) | match (post-fix marker present, pre-fix
               gone) | moved-past (pre-fix gone, cluster's next wall is app-specific/unknown so no
               positive marker -- success for C/D/I) | alive-no-fatal | moved-elsewhere (died at an
               unexpected place) | no-run
  zorder:      match (dialog_z > activity_z, alive) | unchanged (dialog_z < activity_z) |
               regression-fatal (app died) | no-data | no-run

Self-test: run against a U13 stage-A window dir (pre-every-U14-fix). The known answer is that every
mover is still at its pre-fix state -> all first-fatal movers `unchanged`, all z-order movers
`unchanged`. Any other verdict on U13 is an extractor bug.
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def repo_root(explicit):
    if explicit:
        return Path(explicit).resolve()
    # recipe/ lives at <repo>/benchmark/<topic>/recipe/readout.py
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / "scripts" / "lab" / "first_fatal.py").exists():
            return p
    # worktree sibling fallback: the wiki worktree reuses the master scripts/lab
    for sib in ("westlake-harness",):
        cand = here.parents[4] / sib if len(here.parents) > 4 else None
        if cand and (cand / "scripts" / "lab" / "first_fatal.py").exists():
            return cand
    raise SystemExit("could not locate scripts/lab; pass --repo")


def norm(path, ws):
    s = str(path)
    return s.replace(ws, "$WORKSPACES") if ws and s.startswith(ws) else s


# ---- run-dir discovery -------------------------------------------------------
def index_runs(window_root):
    """key (from record.json) -> [run dirs] that have both record.json and hilog.txt."""
    idx = {}
    for rj in Path(window_root).rglob("record.json"):
        d = rj.parent
        if not (d / "hilog.txt").exists():
            continue
        try:
            key = json.loads(rj.read_text()).get("key")
        except Exception:
            continue
        if key:
            idx.setdefault(key, []).append(d)
    return idx


# ---- extractors (reuse scripts/lab) -----------------------------------------
def first_fatal(repo, run):
    try:
        out = subprocess.run([sys.executable, str(repo / "scripts/lab/first_fatal.py"), str(run)],
                             capture_output=True, text=True, timeout=120)
        return json.loads(out.stdout) if out.stdout.strip() else None
    except Exception:
        return None


def terminal_sig(ff):
    """(kind, short root symbol) from a first_fatal result."""
    if not ff:
        return (None, "")
    t = ff.get("terminal")
    kind = t.get("kind") if t else None
    root = ff.get("root")
    sym = ""
    if isinstance(root, dict):
        ev = root.get("event") or {}
        sym = (ev.get("message") or "")[:200]
    return (kind, sym)


def near_fatal_libs(bind_mod, dlopen_mod, run):
    rows = dlopen_mod.scan([run], near_fatal_seconds=3)
    return sorted({r["lib"] if "lib" in r else r.get("key", "") for r in rows if r.get("near_fatal_keys")}) \
        if rows and isinstance(rows[0], dict) and "near_fatal_keys" in rows[0] else []


def bind_status_for(bind_mod, run, key):
    for r in bind_mod.scan([run]):
        if r["key"] == key or r["key"] == Path(run).name:
            return r["key_status"]
    # bind_status keys by hilog.parent.name; the leaf dir is the bare key in runner output
    rows = bind_mod.scan([run])
    return rows[0]["key_status"] if rows else "unknown"


# ---- M5 z-order axis (createSession androidType + UpdateZOrderInner) ---------
_CS = re.compile(r"createSession: bundle=(\S+) ability=\S+ name=\S+, androidType=(\d+) -> ohType=\d+")
_OK = re.compile(r"createSession: success, sessionId=(\d+)")
_ZO = re.compile(r"UpdateZOrderInner: id: (\d+), zOrder: \d+ -> (\d+)")
_LINE = re.compile(r"^\S+\s+\S+\s+(\d+)\s+(\d+)\s+\w\s+\S+\s+(.*)$")


def zorder(run, pkg):
    order, pending = [], {}
    try:
        fh = open(Path(run) / "hilog.txt", errors="replace")
    except OSError:
        return [], []
    with fh:
        for line in fh:
            if "createSession" not in line and "UpdateZOrderInner" not in line:
                continue
            m = _LINE.match(line)
            if not m:
                continue
            tid, msg = m.group(2), m.group(3)
            c = _CS.search(msg)
            if c and pkg in c.group(1):
                pending[tid] = int(c.group(2))
                continue
            o = _OK.search(msg)
            if o and tid in pending:
                order.append({"session": int(o.group(1)), "androidType": pending.pop(tid), "zOrder": None})
                continue
            z = _ZO.search(msg)
            if z:
                for s in order:
                    if s["session"] == int(z.group(1)):
                        s["zOrder"] = int(z.group(2))
    dz = [s["zOrder"] for s in order if s["androidType"] == 2 and s["zOrder"] is not None]
    az = [s["zOrder"] for s in order if s["androidType"] == 1 and s["zOrder"] is not None]
    return dz, az


# ---- classification ----------------------------------------------------------
def hit(marker, text):
    return bool(marker) and re.search(marker, text) is not None


def classify_first_fatal(exp, ff, hilog_text):
    kind, sym = terminal_sig(ff)
    pre = hit(exp["prefix_marker"], hilog_text)
    post = hit(exp["postfix_marker"], hilog_text)
    optional = exp["postfix_optional"] == "yes"
    if pre and not post:
        verdict = "unchanged"
    elif post and not pre:
        verdict = "match"
    elif post and pre:
        verdict = "mixed(both-markers)"
    else:  # neither marker
        if optional:
            verdict = "moved-past" if kind else "alive-no-fatal"
        else:
            verdict = "alive-no-fatal" if kind is None else "moved-elsewhere"
    return verdict, dict(terminal_kind=kind, root=sym[:160], prefix_hit=pre, postfix_hit=post)


def classify_zorder(ff, dz, az):
    kind, _ = terminal_sig(ff)
    if not dz or not az:
        return ("no-data", dict(terminal_kind=kind, dialog_z=dz, activity_z=az))
    d, a = max(dz), max(az)
    obs = dict(terminal_kind=kind, dialog_z=dz, activity_z=az)
    if kind is not None:
        return ("regression-fatal", obs)
    if d > a:
        return ("match", obs)
    if d < a:
        return ("unchanged", obs)
    return ("equal-zorder", obs)


# ---- main --------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("window", type=Path, help="U14 (or U13 self-test) window run dir to scan")
    ap.add_argument("--expectations", type=Path,
                    default=Path(__file__).resolve().parent.parent / "expectations.csv")
    ap.add_argument("--repo", default=None)
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--key", action="append", default=None, help="only these mover keys")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    repo = repo_root(a.repo)
    sys.path.insert(0, str(repo / "scripts" / "lab"))
    import bind_status as bind_mod          # noqa: E402
    import dlopen_failures as dlopen_mod    # noqa: E402

    ws = os.environ.get("WORKSPACES") or str(Path(repo).resolve().parent)

    exps = list(csv.DictReader(open(a.expectations)))
    if a.key:
        exps = [e for e in exps if e["key"] in set(a.key)]
    idx = index_runs(a.window)

    results = []
    for e in exps:
        key = e["key"]
        runs = idx.get(key, [])
        if not runs:
            results.append(dict(key=key, axis=e["axis"], cluster=e["cluster"], board=e["board"],
                                verdict="no-run", runs=0, observed={}, expectation=e))
            continue
        run = runs[0]  # first run; runs>1 reported in `runs`
        ff = first_fatal(repo, run)
        try:
            hilog = (run / "hilog.txt").read_text(errors="replace")
        except OSError:
            hilog = ""
        if e["axis"] == "zorder":
            try:
                pkg = json.loads((run / "record.json").read_text())["package"]
            except Exception:
                pkg = ""
            dz, az = zorder(run, pkg)
            verdict, obs = classify_zorder(ff, dz, az)
        else:
            verdict, obs = classify_first_fatal(e, ff, hilog)
            obs["near_fatal_libs"] = near_fatal_libs(bind_mod, dlopen_mod, run)
            obs["bind_status"] = bind_status_for(bind_mod, run, key)
        results.append(dict(key=key, axis=e["axis"], cluster=e["cluster"], board=e["board"],
                            verdict=verdict, runs=len(runs), run=norm(run, ws),
                            observed=obs, expectation=e))

    # ---- print table ----
    if not a.quiet:
        w = max((len(r["key"]) for r in results), default=10)
        print(f"{'KEY':<{w}}  {'AXIS':<11} {'CL':<2} {'VERDICT':<17} OBSERVED")
        print("-" * (w + 50))
        for r in results:
            o = r["observed"]
            if r["axis"] == "zorder":
                od = f"dialog_z={o.get('dialog_z')} activity_z={o.get('activity_z')} term={o.get('terminal_kind')}"
            else:
                od = (f"term={o.get('terminal_kind')} pre={o.get('prefix_hit')} post={o.get('postfix_hit')} "
                      f"bind={o.get('bind_status')} nearfatal={o.get('near_fatal_libs')}")
            if r["verdict"] == "no-run":
                od = "(no run dir for this key in the window)"
            print(f"{r['key']:<{w}}  {r['axis']:<11} {r['cluster']:<2} {r['verdict']:<17} {od}")
        from collections import Counter
        print("\nverdict counts:", dict(Counter(r["verdict"] for r in results)))

    if a.json:
        a.json.write_text(json.dumps(results, indent=1, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
