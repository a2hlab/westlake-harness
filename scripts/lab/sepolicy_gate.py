#!/usr/bin/env python3
"""Offline sepolicy gate for the SELinux label recipe (demo-baseline t2d).

Reads the pinned policy (path+SHA, never committed) and the real label recipe
knowledge/gates/selinux-label-recipe.json (cx-bms). Proves every label-recipe
entry with sesearch inside the OrbStack a2hlab VM (setools 4.4.4): for each
rule that requires a domain to use a labeled path, the corresponding allow
rule must exist. Fails closed when the tool is unreachable or the policy SHA
drifts. Writes the evidence snapshot to --evidence (default
knowledge/gates/sepolicy-evidence.json) and refuses to reuse stale evidence.

Usage: sepolicy_gate.py [--policy PATH] [--recipe PATH] [--evidence PATH]
Exit 0 = every entry proven; nonzero names entry+domain+missing permission.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_paths  # noqa: E402

POLICY_PIN_SHA = "7d23015f5e494b47044f3bfba7545789c20525aecb4c3b6b743aa77e97d764f0"
POLICY_REL = "westlake-inputs/sepolicy/oh-6.1.0.31/policy"
SCHEMA = "sepolicy-gate/v1"

# How each recipe rule is proven, by its context type and purpose. The recipe
# is cx-bms's knowledge/gates/selinux-label-recipe.json (master a799a713e7):
# rules[] each carry {id, match{exact|prefix|glob}, context "u:object_r:<type>:s0"}.
# appspawn is the domain that must use every labeled deployment path (the
# appspawn-x entrypoint and the mount view its app children inherit).
QUERIES = {
    # id -> (class, perms); domain is always appspawn
    "init-entry": ("file", ["entrypoint"]),
    "android-fonts": ("file", ["read", "open", "getattr"]),
    "seccomp-stock": ("file", ["read", "open", "getattr"]),
    "android-lib64": ("file", ["map", "read", "open", "execute"]),
    "route-libraries": ("file", ["map", "read", "open", "execute"]),
    "boot-art": ("file", ["map", "read", "open"]),
    "boot-oat": ("file", ["map", "read", "open", "execute"]),
    "boot-vdex": ("file", ["map", "read", "open"]),
    "jar": ("file", ["read", "open", "getattr"]),
    "json": ("file", ["read", "open", "getattr"]),
    "native-library": ("file", ["map", "read", "open", "execute"]),
}
# app-private (/data/app, data_app_el1_file) is the installer-domain concern,
# not an appspawn-path concern — out of this gate's scope, reported as skipped.
OUT_OF_SCOPE = {"app-private"}


def context_parts(ctx):
    # e.g. u:object_r:appspawn_exec:s0 -> appspawn_exec
    return ctx.split(":")[2] if ctx.count(":") >= 2 else ctx


def rule_queries(rule):
    """Yield (id, domain, label, class, perms) queries a recipe rule must satisfy."""
    rid = rule["id"]
    if rid in OUT_OF_SCOPE:
        return
    label = context_parts(rule["context"])
    if rid not in QUERIES:
        raise KeyError(f"recipe rule {rid} has no proof mapping — extend QUERIES")
    cls, perms = QUERIES[rid]
    yield rid, "appspawn", label, cls, perms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", type=Path, default=None)
    ap.add_argument("--recipe", type=Path, default=None)
    ap.add_argument("--evidence", type=Path, default=None)
    a = ap.parse_args()

    ws = lab_paths.workspaces()
    policy = a.policy or (ws / POLICY_REL)
    # The gate reads the master recipe in place (cx-bms owns it; never copied):
    # resolve the harness checkout that lab_paths points at, else this worktree.
    default_recipe = Path(__file__).resolve().parents[2] / "knowledge/gates/selinux-label-recipe.json"
    harness_recipe = ws / "westlake-harness/knowledge/gates/selinux-label-recipe.json"
    if not default_recipe.is_file() and harness_recipe.is_file():
        default_recipe = harness_recipe
    recipe = a.recipe or default_recipe
    evidence = a.evidence or (Path(__file__).resolve().parents[2] / "knowledge/gates/sepolicy-evidence.json")

    import subprocess

    # Fail-closed preconditions.
    if not policy.is_file():
        print(f"GATE-FAIL policy missing: {policy}", file=sys.stderr); return 2
    h = hashlib.sha256()
    with open(policy, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    actual = h.hexdigest()
    if actual != POLICY_PIN_SHA:
        print(f"GATE-FAIL policy sha drift: expected {POLICY_PIN_SHA[:16]} got {actual[:16]}", file=sys.stderr); return 2
    if not recipe.is_file():
        print(f"GATE-FAIL recipe missing: {recipe}", file=sys.stderr); return 2

    rec = json.loads(recipe.read_text())
    recipe_sha = hashlib.sha256(json.dumps(rec, sort_keys=True).encode()).hexdigest()

    def sesearch(args):
        cmd = ["orb", "-m", "a2hlab", "sesearch", *args, str(policy)]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            raise RuntimeError(f"sesearch unreachable: {e}")
        if r.returncode != 0:
            raise RuntimeError(f"sesearch failed rc={r.returncode}: {r.stderr.strip()[:200]}")
        return r.stdout

    try:
        proofs, failures, skipped = [], [], []
        for rule in rec["rules"]:
            if rule["id"] in OUT_OF_SCOPE:
                skipped.append(rule["id"])
                continue
            for rid, dom, label, cls, perms in rule_queries(rule):
                if dom is None:
                    skipped.append(rid); continue
                for perm in perms:
                    out = sesearch(["-A", "-s", dom, "-t", label, "-c", cls, "-p", perm])
                    lines = [l for l in out.splitlines() if l.startswith("allow") and f" {label}:" in l]
                    if lines:
                        proofs.append({"id": rid, "domain": dom, "label": label, "class": cls,
                                       "perm": perm, "rule": lines[0].strip()})
                    else:
                        failures.append(f"{rid}: domain={dom} label={label} class={cls} missing permission={perm}")
    except RuntimeError as e:
        print(f"GATE-FAIL {e}; no entry proven", file=sys.stderr); return 2

    policy_ref = f"$WORKSPACES/{POLICY_REL}"
    ev = {"schema": SCHEMA, "policy_path": policy_ref, "policy_sha256": POLICY_PIN_SHA,
          "recipe_source": "knowledge/gates/selinux-label-recipe.json (cx-bms, master a799a713e7)",
          "recipe_sha256": recipe_sha,
          "entries_proven": len(proofs), "skipped": skipped,
          "failures": failures, "proofs": proofs}
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(ev, indent=1, ensure_ascii=False) + "\n")

    for p in proofs:
        print(f"PROVEN {p['id']}: domain={p['domain']} label={p['label']} perm={p['perm']}\n       {p['rule']}")
    if skipped:
        print(f"SKIPPED (out of gate scope): {', '.join(skipped)}")
    if failures:
        for f in failures:
            print(f"GATE-FAIL {f}", file=sys.stderr)
        print(f"sepolicy-gate: {len(proofs)} proven, {len(failures)} FAILED", file=sys.stderr)
        return 1
    print(f"sepolicy-gate: all {len(proofs)} proofs pass (policy {POLICY_PIN_SHA[:16]}, recipe {recipe_sha[:16]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
