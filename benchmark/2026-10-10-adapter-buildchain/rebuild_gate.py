#!/usr/bin/env python3
"""Offline fail-closed input/reproduction audit. Never builds, deploys or edits a binary.

--preflight refuses missing source/patch/tool/link inputs before a build can start.
--require-reproduced additionally requires two independently logged clean builds.
--compare compares supplied files; a mismatch returns 2 and writes a difference report.
Registry status is evidence, never authority to weaken an existing deployment gate.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

REPO = Path(__file__).resolve().parents[2]
REQUIRED = ("source_snapshot", "patch_series", "build_script", "toolchain", "sysroot", "link_flags")
SHA = re.compile(r"[0-9a-f]{64}\Z")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def expand(path, root=REPO):
    if "$WORKSPACES" in path and not os.environ.get("WORKSPACES"):
        path = path.replace("$WORKSPACES", str(root.parent))
    path = os.path.expandvars(os.path.expanduser(path))
    if "$" in path:
        raise ValueError("unresolved location: " + path)
    p = Path(path)
    return p if p.is_absolute() else root / p


def check_pin(pin, root):
    if pin.get("state") != "complete":
        return "not complete: " + pin.get("state", "missing")
    if not SHA.fullmatch(pin.get("sha256", "")):
        return "missing full SHA256"
    try:
        path = expand(pin["path"], root)
        if not path.is_file() or digest(path) != pin["sha256"]:
            return "missing or changed input: " + pin["path"]
    except (OSError, ValueError, KeyError) as exc:
        return str(exc)
    return None


def audit(row, root=REPO, require_reproduced=False):
    errors = []
    if not SHA.fullmatch(row.get("sha256", "")):
        errors.append("target: missing full SHA256")
    if not row.get("provenance"):
        errors.append("target: missing provenance")
    for name in REQUIRED:
        reason = check_pin(row.get("inputs", {}).get(name, {}), root)
        if reason:
            errors.append(name + ": " + reason)
    for evidence in row.get("evidence", []):
        if not (root / evidence).is_file():
            errors.append("missing evidence: " + evidence)
    if not row.get("evidence"):
        errors.append("missing evidence list")
    if require_reproduced:
        runs = row.get("last_reproduction", {}).get("runs", [])
        if row.get("last_reproduction", {}).get("status") != "reproduced" or len(runs) != 2:
            errors.append("two clean byte-identical builds not recorded")
        else:
            if runs[0].get("clean_dir") == runs[1].get("clean_dir"):
                errors.append("builds reused the same clean directory")
            for i, run in enumerate(runs):
                if run.get("rc") != 0 or run.get("tee_rc") != 0 or run.get("clean") is not True:
                    errors.append(f"run {i + 1}: clean build/log failed")
                artifact = dict(run.get("artifact", {}), state="complete")
                if artifact.get("sha256") != row.get("sha256"):
                    errors.append(f"run {i + 1}: target SHA mismatch")
                for name, pin in (("artifact", artifact), ("raw_log", dict(run.get("raw_log", {}), state="complete"))):
                    reason = check_pin(pin, root)
                    if reason:
                        errors.append(f"run {i + 1} {name}: {reason}")
    return errors


def elf_metadata(path, readelf):
    def read(*args):
        return subprocess.check_output([readelf, *args, str(path)], text=True)
    syms = read("-sW")
    dyn = read("-dW")
    return {
        "translation_units": [s.split()[-1] for s in syms.splitlines() if " FILE " in s],
        "defined_dynamic_symbols": [s.split()[-1] for s in read("--dyn-syms", "-W").splitlines()
                                    if len(s.split()) >= 8 and s.split()[6] != "UND" and s.split()[0].endswith(":")],
        "build_id": re.findall(r"Build ID: (\w+)", read("-n")),
        "needed_order": re.findall(r"\(NEEDED\).*?\[(.*?)\]", dyn),
        "compiler_comment": read("-p", ".comment"),
        "compile_options": "unknown unless original compile argv/receipt is supplied",
        "link_order": "DT_NEEDED order only; exact object/library argv is unknown",
    }


def compare(target, runs, readelf=None):
    want = digest(target)
    rows = [{"path": str(p), "sha256": digest(p), "equals_target": digest(p) == want} for p in runs]
    out = {"target_sha256": want, "runs": rows, "byte_identical": all(r["equals_target"] for r in rows),
           "new_patched_artifact_created": False}
    if not out["byte_identical"] and readelf:
        out["target_metadata"] = elf_metadata(target, readelf)
        out["run_metadata"] = [elf_metadata(p, readelf) for p in runs]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--table", type=Path, default=REPO / "knowledge/gates/rebuildable-artifacts.json")
    ap.add_argument("--artifact")
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--require-reproduced", action="store_true")
    ap.add_argument("--compare", nargs=3, metavar=("TARGET", "R1", "R2"), type=Path)
    ap.add_argument("--readelf")
    ap.add_argument("--report", type=Path)
    args = ap.parse_args(argv)
    try:
        if args.compare:
            result = compare(args.compare[0], args.compare[1:], args.readelf)
            rc = 0 if result["byte_identical"] else 2
        else:
            table = json.loads(args.table.read_text())
            if table.get("schema") != 1 or not isinstance(table.get("artifacts"), list):
                raise ValueError("invalid rebuildability table")
            rows = table["artifacts"]
            if args.artifact:
                rows = [r for r in rows if r["id"] == args.artifact]
            if not rows:
                raise ValueError("artifact absent from table")
            result = {"mode": "require-reproduced" if args.require_reproduced else "preflight", "artifacts": []}
            for row in rows:
                errors = audit(row, require_reproduced=args.require_reproduced)
                result["artifacts"].append({"id": row["id"], "sha256": row["sha256"],
                                            "verdict": "LOCKED" if errors else "PASS", "errors": errors})
            rc = 2 if any(r["errors"] for r in result["artifacts"]) else 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        result, rc = {"verdict": "REJECT", "error": str(exc)}, 2
    if args.report:
        args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
