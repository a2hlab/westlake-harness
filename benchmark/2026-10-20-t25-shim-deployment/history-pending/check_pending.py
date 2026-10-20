#!/usr/bin/env python3
"""Offline pending-data checks; never imports Board or calls a device tool."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

P = Path(__file__).resolve().parent
def load(p):
    return json.loads(p.read_text())
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    donor = a.repo / "benchmark/2026-10-20-t23-shim-deployment"
    checks = []
    for row in load(P / "unchanged-pins.json"):
        assert sha(P / row["file"]) == row["sha256"]
        assert (P / row["file"]).read_bytes() == (a.repo / row["donor"]).read_bytes()
    checks.append("six donor files byte-identical including executor")
    params = load(P / "parameters.json")
    old = load(donor / "parameters.json")
    assert params["artifacts"][:5] == old["artifacts"][:5]
    assert params["artifacts"][-1]["after_sha256"] is None
    assert params["historical_identity_only"] == {}
    ad = load(P / "admission.template.json")
    for field in ("approved_by", "boot", "holder", "window_start", "parent_mnt",
                  "origin_apply_plan_sha256", "bridge_metadata", "shim_metadata"):
        assert ad[field] is None, field
    assert ad["host"] == {"pid": None, "birth": None, "uid": 20011300}
    for field, file in (("executor_sha256", "executor.py"),
                        ("parameters_sha256", "parameters.json"),
                        ("source_pins_sha256", "executor-source-pins.json"),
                        ("readonly_inputs_sha256", "readonly-inputs.json"),
                        ("bridge_candidate_sha256", "bridge-candidate.json"),
                        ("shim_candidate_sha256", "shim-candidate.json")):
        assert ad[field] == sha(P / file), field
    checks.append("five other artifacts unchanged; no fresh identity or approval inherited")
    candidate = load(P / "shim-candidate.json")
    assert candidate["after_sha256"] is None and candidate["after_bytes"] is None
    assert candidate["production_refs"] == [] and candidate["build_status"] == "UNAPPROVED"
    slots = load(P / "three-slot-admission.json")
    assert slots["candidate_sha256"] is None
    assert [(x["symbol"], x["player_slot"]) for x in slots["slots"]] == [
        ("ANativeWindow_setBuffersGeometry", "0x472048"),
        ("ANativeWindow_lock", "0x472490"),
        ("ANativeWindow_unlockAndPost", "0x472760")]
    assert all(x["candidate_export_offset"] is None and x["actual_slot_value"] is None
               and x["matched"] is False for x in slots["slots"])
    checks.append("three exact player slots required; candidate/live values unknown")
    for ref in load(P / "bridge-candidate.json")["production_refs"]:
        assert sha(a.repo / ref["path"]) == ref["sha256"]
    runs = []
    for mode in ("preflight", "apply", "rollback"):
        for execute in (False, True):
            argv = [sys.executable, str(P / "executor.py"), mode]
            if execute:
                argv += ["--execute", "--boot", "OFFLINE_SENTINEL", "--parent", "1",
                         "--birth", "1", "--hdc", "/NONEXISTENT_T25_NO_DEVICE",
                         "--holder", "OFFLINE_SENTINEL", "--out", str(a.out.resolve() / mode),
                         "--repo", str(a.repo.resolve()), "--inputs", str(a.out.resolve()),
                         "--admission", str(P / "admission.template.json"), "--start", "1"]
            r = subprocess.run(argv, capture_output=True, timeout=10)
            name = mode + ("-execute-sentinel" if execute else "-preview")
            (a.out / (name + ".argv.json")).write_text(json.dumps(argv, indent=2) + "\n")
            (a.out / (name + ".stdout")).write_bytes(r.stdout)
            (a.out / (name + ".stderr")).write_bytes(r.stderr)
            (a.out / (name + ".rc")).write_text(str(r.returncode) + "\n")
            if execute:
                assert r.returncode != 0 and b"shim candidate pin required" in r.stderr
            else:
                assert r.returncode == 0 and json.loads(r.stdout)["device_calls"] == 0
            runs.append({"name": name, "rc": r.returncode,
                         "expected": "pending shim rejected before Board import" if execute else "preview"})
    result = {"status": "PENDING_TEMPLATE_CHECKED_NOT_ADMISSION", "checks": checks,
              "runs": runs, "device_calls": 0, "transaction_tests_rerun": False}
    (a.out / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))

if __name__ == "__main__":
    main()
