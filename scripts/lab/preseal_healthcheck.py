#!/usr/bin/env python3
"""preseal_healthcheck.py <serial> — one-shot READ-ONLY pre-seal health check.

Burns down tonight's three hypothesis classes BEFORE the sealing window, all
via read-only board queries + static grep over the staged payload source:
  (1) real SELinux state: /proc/cmdline androidboot.selinux + getenforce
      (never trust the "v2=Enforcing" memory model);
  (2) mount flags: nosuid/noexec on the target binds (appspawn-x, data) in
      PID 1 mountinfo;
  (3) init trigger chain: every `param:` job condition X in staged *.cfg must
      have a staged script that sets X (grep the payload source); nobody sets
      it => "trigger chain broken";
  (4) entrypoint readiness: appspawn-x non-empty, label appspawn_exec,
      319/56 U13 recover targets present;
  (5) cold-boot reproducibility posture: mode matches the plan selinux_mode
      and no manual setenforce is required.

Output: --out JSON (default stdout) + one line "WINDOW-OK" or
"WINDOW-BLOCKED: <surviving assumptions>".
Exit 0 iff WINDOW-OK.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_paths  # noqa: E402

STAGED_PAYLOAD = (Path(__file__).resolve().parents[2] /
                  "benchmark/2026-10-10-u13-autostart/payload")
APPSPAWN = "/system/bin/appspawn-x"
U13_TABLE = STAGED_PAYLOAD.parent / "payload/u13-recover-table.json"


def shell(hdc, serial, cmd, timeout=60):
    r = subprocess.run([hdc, "-t", serial, "shell", cmd],
                       capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("serial")
    ap.add_argument("--hdc", default="/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc")
    ap.add_argument("--payload", type=Path, default=STAGED_PAYLOAD)
    ap.add_argument("--plan-selinux-mode", default="permissive",
                    choices=("enforcing", "permissive"))
    ap.add_argument("--offline", action="store_true",
                    help="static-only: (3) trigger chain + payload posture, no board queries")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()

    findings, blocked = [], []

    def check(cid, ok, detail, blocking=True):
        findings.append({"id": cid, "ok": bool(ok), "detail": detail})
        if not ok and blocking:
            blocked.append(cid)

    # ---- (3) static: init trigger chain (works offline) ----
    chain = {}
    cfgs = sorted((a.payload / "init").glob("*.cfg")) if (a.payload / "init").is_dir() else []
    conditions, setters = [], {}
    for cfg in cfgs:
        try:
            doc = json.loads(cfg.read_text())
        except json.JSONDecodeError:
            check(f"cfg-parse:{cfg.name}", False, "invalid JSON", blocking=True)
            continue
        for job in doc.get("jobs", []):
            name = str(job.get("name", ""))
            m = re.match(r"^param:(.+)$", name)
            if m:
                cond = str(job.get("condition", ""))
                cm = re.match(r"^([^=<>!]+)=(.+)$", cond)
                param = cm.group(1).strip() if cm else cond
                conditions.append({"cfg": cfg.name, "job": name, "condition": cond, "param": param})
    script_bodies = []
    for sh in sorted((a.payload / "scripts").glob("*.sh")) if (a.payload / "scripts").is_dir() else []:
        body = sh.read_text(errors="replace")
        script_bodies.append((sh.name, body))
    for c in conditions:
        p = re.escape(c["param"])
        setter = None
        for n, b in script_bodies:
            if re.search(rf"param\s+set\s+{p}\b", b):
                setter = n; break
            # indirect via a shell variable: VAR=<param> ... param set "$VAR" true/false
            vm = re.search(rf"^(\w+)={p}\s*$", b, re.M)
            if vm and re.search(r'param\s+set\s+"\$' + vm.group(1), b):
                setter = f"{n}(via {vm.group(1)})"; break
        c["setter"] = setter
        if not setter:
            check(f"trigger-chain:{c['param']}", False,
                  f"{c['cfg']} job {c['job']} waits on {c['param']} but no staged script sets it")
        else:
            check(f"trigger-chain:{c['param']}", True, f"set by {setter}")
    chain = {"conditions": conditions}

    # ---- payload posture (static): 319/56 targets present ----
    table = None
    if U13_TABLE.is_file():
        try:
            table = json.loads(U13_TABLE.read_text())
            targets = table.get("targets") or table.get("layers") or []
            n = len(targets) if isinstance(targets, list) else len(table)
            check("u13-table-present", n in (319, 56), f"u13-recover-table entries={n} (expect 319 or 56)")
        except Exception as e:
            check("u13-table-present", False, f"parse error {e}")

    if a.offline:
        report = {"schema": "preseal-healthcheck/v1", "serial": a.serial, "mode": "offline",
                  "checks": findings, "trigger_chain": chain}
        verdict(report, a.out)
        return

    # ---- (1) real SELinux state ----
    rc, out = shell(a.hdc, a.serial, "cat /proc/cmdline")
    m = re.search(r"androidboot\.selinux=(\w+)", out)
    cmdline_mode = m.group(1) if m else None
    rc2, out2 = shell(a.hdc, a.serial, "getenforce")
    enforce = out2.strip()
    check("selinux-cmdline", cmdline_mode is not None,
          f"androidboot.selinux={cmdline_mode} (missing => kernel default, cannot assume permissive)")
    plan_expect = {"enforcing": "Enforcing", "permissive": "Permissive"}[a.plan_selinux_mode]
    check("selinux-mode-matches-plan", enforce == plan_expect,
          f"getenforce={enforce} plan expects {plan_expect}")

    # ---- (2) mount flags on target binds (PID 1 view) ----
    rc, mi = shell(a.hdc, a.serial, "cat /proc/1/mountinfo")
    bad_flags = []
    for line in mi.splitlines():
        fields = line.split()
        if len(fields) < 6:
            continue
        mp = fields[4]
        opts = fields[5]
        for probe in (APPSPAWN, "/data"):
            if mp == probe or mp.startswith(probe.rstrip("/") + "/"):
                for flag in ("nosuid", "noexec"):
                    if flag in opts.split(","):
                        bad_flags.append({"mount": mp, "flag": flag})
    check("mount-flags", not bad_flags, f"nosuid/noexec on target binds: {bad_flags or 'none'}")

    # ---- (4) entrypoint readiness ----
    rc, st = shell(a.hdc, a.serial, f"stat -c '%s' {APPSPAWN}")
    size = st.strip()
    check("appspawn-nonempty", size.isdigit() and int(size) > 0, f"appspawn-x size={size!r}")
    rc, lab = shell(a.hdc, a.serial, f"stat -c '%C' {APPSPAWN}")
    label = lab.strip()
    check("appspawn-label", label == "u:object_r:appspawn_exec:s0", f"label={label!r}")

    # ---- (5) cold-boot posture (mode already checked; no manual setenforce) ----
    check("coldboot-no-manual-setenforce", a.plan_selinux_mode != "permissive" or cmdline_mode == "permissive",
          "plan=permissive relies on cmdline permissive; if cmdline=enforcing the recover-v3 opt-in sets it AFTER "
          "READY (14s window) — seal driver must keep the receipt-ready barrier")

    report = {"schema": "preseal-healthcheck/v1", "serial": a.serial, "mode": "live",
              "selinux": {"cmdline": cmdline_mode, "getenforce": enforce},
              "mounts": {"bad_flags": bad_flags},
              "checks": findings, "trigger_chain": chain}
    verdict(report, a.out)


def verdict(report, out):
    blocked = [c["id"] for c in report["checks"] if not c["ok"]]
    line = ("WINDOW-OK" if not blocked else "WINDOW-BLOCKED: " + ", ".join(blocked))
    report["window"] = line
    if out:
        out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
        print(line)
    else:
        print(json.dumps(report, indent=1, ensure_ascii=False))
        print(line)
    sys.exit(0 if not blocked else 1)


if __name__ == "__main__":
    main()
