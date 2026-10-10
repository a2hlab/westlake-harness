#!/usr/bin/env python3
"""Read-only pre-window checklist gate (RUNBOOK bd1d5baa30). Fail-closed: any FAIL -> non-zero exit.

Automates the '开窗前检查表': before a board window, verify the board matches the signed baseline's
conditions so a run is not silently compared across mismatched SELinux modes, dirty boots, missing keys,
or a different launch path. Pure read-only (getenforce/uptime/ps/bm dump); it never writes the board.

Usage:
  window_preflight.py <serial> --keys k1,k2,... --control <key> --baseline <signoff-or-run-dir>
                      --manifest <batch-manifest.json> [--launch icon-tap] [--hdc hdc]

Checks (each PASS/FAIL):
  selinux-mode   getenforce == the SELinux mode recorded by the baseline (baseline has none -> FAIL 'baseline mode unknown')
  clean-boot     uptime below threshold AND none of the keys'/control's packages already started since boot (WMS conflict risk)
  manifest+bms   every key and the control is in the batch manifest AND BMS-queryable (bm dump -a)
  launch-method  the intended launch method equals the baseline's recorded launch method
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def dev(hdc, serial, cmd, timeout=40):
    out = subprocess.run(hdc.split() + ["-t", serial, "shell", cmd],
                         capture_output=True, text=True, timeout=timeout)
    return out.stdout.replace("\r", "")


# ---- baseline readers (a baseline is a dir; it must record its own SELinux mode + launch method) ----
def baseline_selinux_mode(baseline):
    """Return 'Enforcing'/'Permissive' from the baseline dir, or None if it is not recorded."""
    snap = baseline / "snapshot.json"
    if snap.is_file():
        d = read_json(snap)
        if d.get("selinux_mode") in ("Enforcing", "Permissive"):
            return d["selinux_mode"]
        enf = d.get("selinux_enforce")
        if enf in ("1", 1, "Enforcing"):
            return "Enforcing"
        if enf in ("0", 0, "Permissive"):
            return "Permissive"
    receipt = baseline / "receipt.env"
    if receipt.is_file():
        for line in receipt.read_text().splitlines():
            if line.startswith("selinux_mode="):
                v = line.split("=", 1)[1].strip()
                if v in ("Enforcing", "Permissive"):
                    return v
    mode = baseline / "selinux_mode.json"
    if mode.is_file():
        v = read_json(mode).get("selinux_mode")
        if v in ("Enforcing", "Permissive"):
            return v
    return None


def baseline_launch_method(baseline):
    for candidate in ("run-facts.json", "record.json", "snapshot.json", "run.json"):
        p = baseline / candidate
        if p.is_file():
            v = read_json(p).get("launch_method")
            if isinstance(v, str) and v:
                return v
    return None


def manifest_packages(manifest):
    d = read_json(manifest)
    apps = d.get("apps", d if isinstance(d, list) else [])
    return {a["key"]: a.get("package") for a in apps if isinstance(a, dict) and a.get("key")}


def run(args):
    checks = []

    def add(name, ok, detail):
        checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    keys = [k for k in args.keys.split(",") if k]
    pkgmap = manifest_packages(Path(args.manifest))

    # 1. SELinux mode matches the baseline's recorded mode
    base_mode = baseline_selinux_mode(Path(args.baseline))
    if base_mode is None:
        add("selinux-mode", False, "baseline mode unknown (baseline records no selinux_mode/selinux_enforce)")
    else:
        live = dev(args.hdc, args.serial, "getenforce").strip()
        add("selinux-mode", live == base_mode, "getenforce=%s baseline=%s" % (live or "?", base_mode))

    # 2. clean boot + no target package already started (WMS conflict risk)
    up = dev(args.hdc, args.serial, "cut -d. -f1 /proc/uptime").strip()
    up_ok = up.isdigit() and int(up) <= args.max_uptime
    running = dev(args.hdc, args.serial, "ps -A -o NAME")
    already = sorted({k for k in keys + [args.control]
                      if pkgmap.get(k) and re.search(r"(?m)^" + re.escape(pkgmap[k][:15]), running)})
    add("clean-boot", up_ok and not already,
        "uptime=%ss (<=%s: %s); already-started(WMS risk)=%s" % (up or "?", args.max_uptime, up_ok, already or "none"))

    # 3. all keys + control in manifest AND BMS-queryable
    want = keys + [args.control]
    missing_manifest = [k for k in want if k not in pkgmap]
    bm = dev(args.hdc, args.serial, "bm dump -a")
    not_bms = [k for k in want if pkgmap.get(k) and pkgmap[k] not in bm]
    add("manifest+bms", not missing_manifest and not not_bms,
        "missing_from_manifest=%s not_bms_queryable=%s" % (missing_manifest or "none", not_bms or "none"))

    # 4. launch method matches the baseline's recorded method
    base_launch = baseline_launch_method(Path(args.baseline))
    if base_launch is None:
        add("launch-method", False, "baseline launch method unknown")
    else:
        add("launch-method", args.launch == base_launch, "intended=%s baseline=%s" % (args.launch, base_launch))

    for c in checks:
        print("%-14s %s  %s" % (c["check"], c["status"], c["detail"]))
    failed = [c["check"] for c in checks if c["status"] == "FAIL"]
    print("PREFLIGHT " + ("PASS" if not failed else "FAIL: " + ",".join(failed)))
    return 0 if not failed else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("serial")
    ap.add_argument("--keys", required=True)
    ap.add_argument("--control", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--launch", default="icon-tap")
    ap.add_argument("--hdc", default="hdc")
    ap.add_argument("--max-uptime", type=int, default=600)
    return run(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
