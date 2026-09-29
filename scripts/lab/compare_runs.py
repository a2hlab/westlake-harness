#!/usr/bin/env python3
"""List every variable that differs between two bms_batch.py runs before anyone names a cause.

    compare_runs.py <run-A> <run-B> [--keys k1,k2,...]

A run is a bms_batch run directory (<run>/<serial>/..., or the <serial> directory itself). The variables are
the board (serial), a reboot on the same board (baseline.json boot_id), and every path whose sha256 differs in
runtime-fingerprint.txt, including paths present in only one run; files in GROUPS count once. For each key it prints both facts.txt lines; without --keys it prints the keys whose t5/t20
liveness differs.

The last line is the attribution rule (FLAW-008): exactly one variable = a single-variable comparison;
more than one = any single-cause statement is a hypothesis and needs a discriminating run; zero variables
with a flipped key = repeat that key (nondeterminism) before blaming anything.
"""
import json
import pathlib
import re
import sys


# files that are only ever deployed together count as one variable
GROUPS = {
    "installer": {"/system/lib64/libbms.z.so", "/system/lib64/libapk_installer.so"},
}


def device_dir(run):
    run = pathlib.Path(run)
    if (run / "runtime-fingerprint.txt").is_file():
        return run
    subs = [d for d in run.iterdir() if d.is_dir() and re.search(r"0{7}", d.name)]
    if len(subs) != 1:
        sys.exit(f"compare_runs: {run}: expected one <serial> directory, found {len(subs)}")
    return subs[0]


def fingerprint(d):
    f = d / "runtime-fingerprint.txt"
    if not f.is_file():
        sys.exit(f"compare_runs: {f} missing (run predates the fingerprint; compare boards by hand)")
    out = {}
    for line in f.read_text().splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2 and re.fullmatch(r"[0-9a-f]{64}", parts[0]):
            out[parts[1].strip()] = parts[0]
    return out


def boot_id(d):
    try:
        return json.loads((d / "baseline.json").read_text()).get("boot_id")
    except (OSError, ValueError):
        return None


def keeps_app_data(d):
    """True when the run launched already-installed apps, so data left by an earlier crash carries over."""
    try:
        options = json.loads((d / "plan.json").read_text()).get("options", {})
    except (OSError, ValueError):
        return None
    return bool(options.get("launch_only")) or not options.get("reinstall", False)


def facts(d):
    f = d / "facts.txt"
    rows = {}
    if f.is_file():
        for line in f.read_text().splitlines():
            m = re.match(r"(\S+)\s+shots ", line)
            if m:
                rows[m.group(1)] = line.rstrip()
    return rows


def alive(line):
    m = re.search(r"alive t5=(\S+) t20=(\S+)", line or "")
    return m.groups() if m else None


def compare(a, b, keys=None):
    da, db = device_dir(a), device_dir(b)
    fa, fb = fingerprint(da), fingerprint(db)
    variables = []
    if da.name != db.name:
        variables.append(f"board {da.name[:8]} -> {db.name[:8]}")
    elif boot_id(da) and boot_id(db) and boot_id(da) != boot_id(db):
        variables.append(f"reboot {boot_id(da)[:8]} -> {boot_id(db)[:8]}")
    grouped = {}
    for path in sorted(set(fa) | set(fb)):
        if fa.get(path) != fb.get(path):
            change = f"{path} {(fa.get(path) or 'absent')[:8]} -> {(fb.get(path) or 'absent')[:8]}"
            group = next((g for g, members in GROUPS.items() if path in members), None)
            if group:
                grouped.setdefault(group, []).append(change)
            else:
                variables.append(change)
    for group, changes in grouped.items():
        variables.append(f"{group}: " + "; ".join(changes))
    carried = [name for name, d in (("A", da), ("B", db)) if keeps_app_data(d)]
    if carried:
        variables.append(f"app data carried over from earlier runs in {'/'.join(carried)} (no --reinstall)")
    ra, rb = facts(da), facts(db)
    if keys is None:
        keys = [k for k in sorted(set(ra) & set(rb), key=str.lower) if alive(ra[k]) != alive(rb[k])]
    lines = [f"variables: {len(variables)}"] + [f"  {v}" for v in variables]
    for k in keys:
        lines += [f"key {k}", f"  A {ra.get(k, '?')}", f"  B {rb.get(k, '?')}"]
    if len(variables) == 1:
        lines.append("verdict: single-variable comparison; a difference may be attributed to it")
    elif variables:
        lines.append(f"verdict: {len(variables)} variables differ; any single-cause attribution is a hypothesis "
                     "until a run that changes only that variable")
    else:
        lines.append("verdict: no variable differs; a flipped key is nondeterminism until it repeats (>=3 runs)")
    return lines


def main(argv):
    args, keys = [], None
    it = iter(argv)
    for x in it:
        if x == "--keys":
            keys = [k for k in next(it).split(",") if k]
        else:
            args.append(x)
    if len(args) != 2:
        sys.exit(__doc__)
    print("\n".join(compare(args[0], args[1], keys)))


if __name__ == "__main__":
    main(sys.argv[1:])
