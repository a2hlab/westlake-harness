#!/usr/bin/env python3
"""Pure local rollback admission. No subprocess/device capability."""
import argparse
import json
import time
from pathlib import Path
from rollback_core import fill, read_script, require, sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="mode", required=True)
    r = sub.add_parser("read-script")
    r.add_argument("--parent", required=True, type=int)
    r.add_argument("--host", required=True, type=int)
    f = sub.add_parser("fill")
    for key in ("repo", "context", "apply-plan", "apply-admission",
                "held-stdout", "held-stderr", "held-rc",
                "read-stdout", "read-stderr", "read-rc", "out"):
        f.add_argument("--" + key, required=True, type=Path)
    a = p.parse_args()
    if a.mode == "read-script":
        print(read_script(a.parent, a.host), end="")
        return
    c = json.loads(a.context.read_text())
    plan = json.loads(a.apply_plan.read_text())
    original = json.loads(a.apply_admission.read_text())
    require(sha(a.apply_admission) == plan["admission_sha256"], "original admission SHA")
    require(a.held_rc.read_text().strip() == a.read_rc.read_text().strip() == "0", "host rc")
    require(not a.held_stderr.read_bytes() and not a.read_stderr.read_bytes(), "stderr")
    require(a.read_stdout.stat().st_mtime >= a.apply_plan.stat().st_mtime,
            "fresh read predates apply plan")
    require(a.held_stdout.stat().st_mtime >= c["start"], "held predates window")
    ad, ids, budget = fill(a.repo, c, a.held_stdout.read_text(),
                          a.read_stdout.read_text(), time.time(), plan)
    for key in ("executor_sha256", "parameters_sha256", "source_pins_sha256",
                "readonly_inputs_sha256", "bridge_candidate_sha256",
                "shim_candidate_sha256", "three_slot_requirements_sha256",
                "bridge_binding_requirements_sha256", "providers", "cfg_sha256"):
        require(ad[key] == original[key], "original source/admission pin drift: " + key)
    ad["origin_apply_plan_sha256"] = sha(a.apply_plan)
    ad["recovery_no_parent"] = False
    a.out.mkdir(parents=True, exist_ok=False)
    for name, value in (
        ("admission.json", ad), ("budget.json", budget),
        ("identity.json", dict(boot=ad["boot"], parent=ids["P"][0], parent_birth=ids["P"][2],
                               host=ids["H"][0], host_birth=ids["H"][2])),
        ("inputs.json", {str(getattr(a, key)): sha(getattr(a, key)) for key in
                        ("context", "apply_plan", "apply_admission", "held_stdout",
                         "held_stderr", "held_rc", "read_stdout", "read_stderr", "read_rc")})):
        (a.out / name).write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps(dict(status="LOCAL_ONLY_ROLLBACK_EXECUTOR_STILL_REQUIRED",
                          device_calls=0, out=str(a.out), **budget)))


if __name__ == "__main__":
    main()
