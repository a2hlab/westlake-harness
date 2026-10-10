#!/usr/bin/env python3
"""Minimal, read-only exporter for reboot_sim.py's eight-input manifest (cc-t3 #91).

reboot_sim.py --inputs expects a SHA-pinned manifest (schema_version 1, inputs = exactly
{plan, snapshot, inventory, autostart, closure, recipe, queries, policy}, plus raw_inputs covering
every snapshot item), NOT a snapshot directory. This exporter assembles that manifest from a read-only
snapshot dir + the deployment plan + the auxiliary input paths. It only HASHES and REFERENCES files; it
never fabricates content and never touches a board.

snapshot + plan are derivable here; the other six inputs (inventory/autostart/closure/recipe/queries/policy)
are supplied by path (they are separate evidence). Any not supplied are emitted with sha256=null and a
"MISSING" marker and listed on stderr, so an operator can tell exactly what is still needed (the commands.md
step then documents "reference step; skip + record if an input is missing").

Usage:
  reboot_sim_inputs.py --snapshot <dir-or-snapshot.json> --plan <plan.json> --out <inputs.json> \
     [--inventory P] [--autostart P] [--closure P] [--recipe P] [--queries P] [--policy P]
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

AUX = ("inventory", "autostart", "closure", "recipe", "queries", "policy")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def portable(path):
    """$WORKSPACES/$HOME-relative form for stable manifests (matches the known-answer sample style)."""
    s = str(Path(path).resolve())
    ws = os.environ.get("WORKSPACES") or str(Path.home() / "orca/workspaces")
    for var, base in (("$WORKSPACES", ws), ("$HOME", str(Path.home()))):
        base = str(Path(base).resolve())
        if s == base or s.startswith(base + "/"):
            return var + s[len(base):]
    return s


def ref(path):
    return {"path": portable(path), "sha256": digest(path)}


def build(snapshot_json, plan, aux_paths):
    snap_dir = snapshot_json.parent
    snap = json.loads(snapshot_json.read_text())
    inputs = {"snapshot": ref(snapshot_json), "plan": ref(plan)}
    missing = []
    for name in AUX:
        p = aux_paths.get(name)
        if p and Path(p).is_file():
            inputs[name] = ref(Path(p))
        else:
            inputs[name] = {"path": p or None, "sha256": None, "status": "MISSING"}
            missing.append(name)
    # raw_inputs: every snapshot item's raw (+ .stderr) pinned to the sha the snapshot already recorded.
    raw_inputs = {}
    for name, item in snap.get("items", {}).items():
        if item.get("raw"):
            raw_inputs[name] = {"path": portable(snap_dir / item["raw"]), "sha256": item.get("raw_sha256")}
        if item.get("stderr_raw"):
            raw_inputs[name + ".stderr"] = {"path": portable(snap_dir / item["stderr_raw"]),
                                            "sha256": item.get("stderr_sha256")}
    manifest = {"schema_version": 1, "inputs": inputs, "raw_inputs": raw_inputs}
    # advisory bindings (warn, do not fabricate): the plan must match the snapshot's recorded plan_sha256.
    warnings = []
    plan_canon = hashlib.sha256(json.dumps(json.loads(plan.read_text()), sort_keys=True,
                                           separators=(",", ":")).encode()).hexdigest()
    if snap.get("plan_sha256") and snap["plan_sha256"] != plan_canon:
        warnings.append("plan does not match snapshot.plan_sha256 (%s != %s)" % (plan_canon[:12], snap["plan_sha256"][:12]))
    return manifest, missing, warnings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snapshot", required=True, type=Path)
    ap.add_argument("--plan", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    for name in AUX:
        ap.add_argument("--" + name, type=str)
    a = ap.parse_args(argv)
    snapshot_json = a.snapshot / "snapshot.json" if a.snapshot.is_dir() else a.snapshot
    if not snapshot_json.is_file():
        print("REFUSE: snapshot.json not found: " + str(snapshot_json), file=sys.stderr)
        return 2
    if not a.plan.is_file():
        print("REFUSE: plan not found: " + str(a.plan), file=sys.stderr)
        return 2
    if a.out.exists():
        print("REFUSE: fresh --out required", file=sys.stderr)
        return 2
    manifest, missing, warnings = build(snapshot_json, a.plan, {n: getattr(a, n) for n in AUX})
    a.out.write_text(json.dumps(manifest, indent=2) + "\n")
    print("wrote " + str(a.out) + " (raw_inputs=" + str(len(manifest["raw_inputs"])) + ")")
    for w in warnings:
        print("WARN " + w, file=sys.stderr)
    if missing:
        print("MISSING aux inputs (supply or skip+record per commands.md): " + ", ".join(missing), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
