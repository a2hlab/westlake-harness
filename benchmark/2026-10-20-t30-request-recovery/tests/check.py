#!/usr/bin/env python3
"""T30 acceptance checker — dispatches the REAL route replay + the REAL pthread pollution counter-example
against THIS tree's two derived TUs. No mirror implementation, no value-assertion stand-in: the derived
window_module.c / provider_adapter.c are compiled into the actual pair/geometry/R14/R15/R26/entry chain
(replay.py) and the actual r15_adapter (adapter_pollution.c); only OH/provider/owner/sink are doubles.
Invoked by tools/spec-checks/tests/toutiao_t30_recovery.rs. t1 contract revision 2271d5d1f.

The peer route replay + pollution landed in the main tree (89058228d7), so defaults are same-repo paths
under REPO_ROOT; explicit overrides stay (WL_T30_PEER_DIR, WL_T30_MAIN_REPO). Absent trees -> a clear
exit-2 setup error, never a false pass. Zero device, zero REA.

Receipts: every compile/run keeps its argv/stdout/stderr/rc under a PERSISTENT per-invocation run dir
(WL_T30_RECEIPTS, default $HOME/.local/share/westlake/t30-recovery-cc/selector/run-<ns>); nothing is
deleted, and the replay --out (fixture binary + results.json + its own compile/run logs) lives there too."""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
T30 = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(os.path.dirname(T30))          # benchmark/<t30>/.. -> repo root
# Defaults: the landed same-repo locations (89058228d7). Overrides for a pre-merge branch / relocated lab.
PEER_DIR = os.environ.get("WL_T30_PEER_DIR",
    os.path.join(REPO_ROOT, "benchmark", "2026-10-20-t30-recovery-peer"))
MAIN_REPO = os.environ.get("WL_T30_MAIN_REPO", REPO_ROOT)
SHIM = os.path.join(MAIN_REPO, "benchmark", "2026-10-20-t29-window-observation", "shim")
OBSERVER = os.path.join(MAIN_REPO, "benchmark", "2026-10-20-t27-buffer-observation")
RELEASE_FAIL_TEST = os.path.join(T30, "test", "test_recovery_release_fail.c")
WINDOW_MODULE = os.path.join(T30, "src", "window_module.c")
PROVIDER_ADAPTER = os.path.join(T30, "src", "provider_adapter.c")
REPLAY = os.path.join(PEER_DIR, "replay.py")
POLLUTION = os.path.join(PEER_DIR, "adapter_pollution.c")
RECEIPTS_ROOT = os.environ.get("WL_T30_RECEIPTS",
    os.path.join(os.path.expanduser("~"), ".local", "share", "westlake",
                 "t30-recovery-cc", "selector"))

# Real route cases that exercise the conservative/retained + cleanup-failure paths on the derived TUs.
RETAINED_CASES = ["request_failure", "request_positive_error", "map_failure",
                  "unmap_failure", "flush_failure", "abort_failure", "precheck_failure",
                  "owner_release_failure"]
# Real route cases that exercise the original success/format path (must be unchanged by the derived TUs).
REGRESSION_CASES = ["valid", "rgb", "unknown", "rgbx", "handle_failure",
                    "native_convert_failure", "layout_failure"]

_SEQ = [0]


def _run_dir():
    d = os.path.join(RECEIPTS_ROOT, f"run-{time.time_ns()}")
    os.makedirs(d, exist_ok=False)
    return d


def need(path, what):
    if not os.path.exists(path):
        print(f"T30 check: required {what} not found: {path}", file=sys.stderr)
        print("  set WL_T30_PEER_DIR / WL_T30_MAIN_REPO to the landed route replay + T29 shim; this "
              "acceptance reuses the real harness and does not substitute a mirror.", file=sys.stderr)
        sys.exit(2)


def rec(run, name, argv, **kw):
    _SEQ[0] += 1
    tag = f"{_SEQ[0]:02d}-{name}"          # unique per run; receipts never overwrite each other
    with open(os.path.join(run, tag + ".argv.json"), "w") as f:
        json.dump([str(x) for x in argv], f)
    r = subprocess.run([str(x) for x in argv], capture_output=True, text=True, **kw)
    for ext, data in (("stdout", r.stdout), ("stderr", r.stderr)):
        with open(os.path.join(run, tag + "." + ext), "w") as f:
            f.write(data or "")
    with open(os.path.join(run, tag + ".rc"), "w") as f:
        f.write(str(r.returncode) + "\n")
    return r


def run_replay(run, expect, overrides):
    outdir = os.path.join(run, "replay-" + expect)    # persistent: fixture + results.json + logs kept
    argv = ["python3", REPLAY, "--repo", MAIN_REPO, "--expect", expect, "--out", outdir]
    if overrides:
        argv += ["--window-module", WINDOW_MODULE, "--provider-adapter", PROVIDER_ADAPTER]
    r = rec(run, "replay-" + expect, argv)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-1200:])
        return None, outdir
    return json.load(open(os.path.join(outdir, "results.json"))), outdir


def build_pollution(run):
    binp = os.path.join(run, "pollution")
    r = rec(run, "pollution-build",
            ["clang", "-std=c11", "-Wall", "-Wextra", "-Werror", "-Wno-misleading-indentation",
             "-pthread", "-D_GNU_SOURCE=1", "-I", SHIM, "-I", os.path.join(SHIM, "derived"),
             POLLUTION, PROVIDER_ADAPTER, "-o", binp])
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
        sys.exit(1)
    return binp


def build_release_fail(run):
    # the real pair recovery + owner_release-failure counter-example: the derived two TUs + the real
    # pair/geometry/R20/R26 chain (shim), only OH/provider/owner are doubles.
    binp = os.path.join(run, "test_recovery_release_fail")
    r = rec(run, "release-fail-build",
            ["clang", "-std=c11", "-Wall", "-Wextra", "-Werror", "-Wno-misleading-indentation",
             "-pthread", "-D_GNU_SOURCE=1", "-DWL_T27_OBSERVER",
             "-I", SHIM, "-I", os.path.join(SHIM, "derived"), "-I", OBSERVER,
             RELEASE_FAIL_TEST, WINDOW_MODULE, PROVIDER_ADAPTER,
             os.path.join(SHIM, "derived", "entry.c"), os.path.join(SHIM, "rgbx.c"),
             os.path.join(SHIM, "observation.c"), os.path.join(SHIM, "observe29.c"),
             os.path.join(OBSERVER, "observer.c"), "-o", binp])
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
        sys.exit(1)
    return binp


def fixture_cases(run, outdir, cases):
    fixture = os.path.join(outdir, "fixture")
    need(fixture, "route fixture binary")
    for case in cases:
        r = rec(run, "case-" + case, [fixture, case])
        assert r.returncode == 0 and "PASS" in r.stdout, (case, r.returncode, r.stdout[-200:], r.stderr[-200:])


def check_request_recovery(run):
    res, _ = run_replay(run, "recovery", True)
    assert res and res["status"] == "CANDIDATE_REAL_ROUTE_RECOVERY_PASSED_HOST_ONLY", res
    f = res["facts"]
    assert f["first"] == -5 and f["second"] == 0 and f["request_calls"] == 2 and f["map_calls"] == 1, f
    assert f["first_report_retained"] == 0 and f["abort_calls"] == 0, f
    base, _ = run_replay(run, "baseline", False)
    assert base and base["status"] == "BASELINE_FAILURE_REPRODUCED_CANDIDATE_PENDING", base
    assert base["facts"]["second"] == -16 and base["facts"]["request_calls"] == 1, base
    binp = build_pollution(run)
    for op in ("flush", "abort"):
        r = rec(run, "pollution-" + op + "-retained", [binp, op, "retained"])
        assert r.returncode == 0, (op, r.returncode, r.stderr)
    print("T30 request_recovery OK (real-route recovery + baseline contrast + concurrent reservation retained)")


def check_retained(run):
    # (a) conservative + cleanup-failure retained on the real route through the derived TUs
    _, outdir = run_replay(run, "recovery", True)
    fixture_cases(run, outdir, RETAINED_CASES)
    # (b) concurrent pollution of the RESERVED record keeps the FAILED record (no wrongful clear)
    binp = build_pollution(run)
    for op in ("flush", "abort"):
        r = rec(run, "pollution-" + op + "-retained", [binp, op, "retained"])
        assert r.returncode == 0, (op, r.returncode, r.stderr)
        fact = json.loads(r.stdout.strip().splitlines()[-1])
        assert fact["after_record_rc"] == 0 and fact["second_rc"] == -16 and fact["lower_calls"] == 1, fact
    r = rec(run, "pollution-flush-cleared-negative", [binp, "flush", "cleared"])
    assert r.returncode != 0, "a concurrency-polluted record was wrongly cleared"
    # (c) recovery-path owner_release failure: real pair recovery (retained==0) + injected owner_release!=1
    #     -> -EPROTO, R14 recovered (report -ENOENT), owner ref left unbalanced (no fake balance/force-zero).
    rfbin = build_release_fail(run)
    r = rec(run, "recovery-release-fail", [rfbin, "recovery_release_fail"])
    assert r.returncode == 0 and "PASS" in r.stdout, (r.returncode, r.stdout[-200:], r.stderr[-300:])
    fact = json.loads(next(l for l in r.stdout.splitlines() if l.strip().startswith("{")))
    assert fact["request_calls"] == 1 and fact["release_delta"] == 1 and fact["refs"] == 3 and fact["report_rc"] == -2, fact
    print("T30 retained OK: " + str(len(RETAINED_CASES)) + " real conservative/cleanup-failure cases "
          "(incl. owner_release_failure -> -EPROTO on the real pair) + concurrent pollution keeps the FAILED "
          "record + recovery-path owner_release failure -> -EPROTO with R14 freed and the owner ref left "
          "unbalanced (no fake balance).")


def check_success_regression(run):
    _, outdir = run_replay(run, "recovery", True)
    fixture_cases(run, outdir, REGRESSION_CASES)
    print("T30 success_regression OK (" + str(len(REGRESSION_CASES)) +
          " original route success/reject cases PASS on the derived TUs)")


def main():
    if len(sys.argv) != 2:
        print("usage: check.py <request_recovery|retained|success_regression|runtime_evidence>", file=sys.stderr)
        return 2
    scenario = sys.argv[1]
    if scenario == "runtime_evidence":
        print("T30 runtime_evidence: HUMAN_PENDINGREVIEW — real-device before/after frames are "
              "outer-reviewed; no host test can substitute (zero device here).")
        return 3
    need(REPLAY, "route replay.py")
    need(POLLUTION, "adapter_pollution.c")
    need(SHIM, "T29 shim sources (real pair/R14/R15/R26)")
    run = _run_dir()
    print("T30 receipts: " + run, file=sys.stderr)
    if scenario == "request_recovery":
        check_request_recovery(run)
    elif scenario == "retained":
        check_retained(run)
    elif scenario == "success_regression":
        check_success_regression(run)
    else:
        print(f"unknown scenario: {scenario}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
