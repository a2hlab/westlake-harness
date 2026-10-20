#!/usr/bin/env python3
"""T30 archive pattern adapted to the complete closed T31 original window allowlist; local only."""
import argparse
import hashlib
import json
import os
import shlex
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()
def load(p):
    return json.loads(p.read_text())
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--remote-root", default=os.environ.get("HW248_ARTIFACT_ROOT"), required=False)
    a = ap.parse_args()
    close = a.base / "t31-5cd-window-01/close.json"
    c = load(close)
    assert c["status"] == "CLOSED_RESTORED_NOT_SEALED" and c["elapsed_seconds"] > 0
    # Preserve an actual deadline overrun if present; archiving does not approve it.
    assert (close.parent / "unlock.rc").read_text().strip() == "0"
    assert (close.parent / "held-after.rc").read_text().strip() == "1"
    assert not (close.parent / "held-after.stdout").read_bytes().strip()
    assert a.out.is_absolute() and not str(a.out).startswith(("/tmp/", "/private/tmp/"))
    a.out.mkdir(parents=True, exist_ok=False)
    allow = {"directories": ["t31-5cd-window-01", "t30-candidate-inputs"], "files": sorted(p.name for p in a.base.glob("t31_*.py"))}
    allow["directories"] += sorted(p.name for p in a.base.glob("t31-fresh-readonly-*") if p.is_dir())
    assert len(allow["directories"]) >= 3
    selected = {}
    for name in allow["directories"]:
        base = a.base / name
        assert base.is_dir()
        for p in sorted(base.rglob("*")):
            if p.is_file():
                selected["BASE20/" + str(p.relative_to(a.base))] = p
    for name in allow["files"]:
        p = a.base / name
        assert p.is_file()
        selected["BASE20/" + name] = p
    workspaces = Path(__file__).resolve().parents[3]
    # Include the actual mainline execution sources plus the author's original
    # offline helper receipts; production itself has a separate complete archive.
    for producer, names, alias in [
        (workspaces / "westlake-harness/benchmark/2026-10-20-t31-demo-retain",
         ["helpers", "recovery", "evidence", "evidence-delivery"], "main-execution-tools"),
        (workspaces / "westlake-harness-t4/benchmark/2026-10-20-t31-demo-retain",
         [".private"], "helper-original-receipts"),
    ]:
        for name in names:
            origin = producer / name
            assert origin.is_dir()
            for p in sorted(origin.rglob("*")):
                if p.is_file() and "__pycache__" not in p.parts:
                    selected[alias + "/" + name + "/" + str(p.relative_to(origin))] = p
    origin = workspaces / "westlake-harness/benchmark/2026-10-20-t31-demo-retain"
    for f in sorted(origin.iterdir()):
        if f.is_file(): selected["main-execution-tools/" + f.name] = f
    for origin, alias in [(workspaces / "westlake-harness/specs/toutiao-t31-demo-retain", "task-spec"),
                          (workspaces / "westlake-harness/benchmark/2026-10-20-t30-request-recovery/deployment/final-01", "original-deployment-data"),
                          ]:
        assert origin.is_dir(), origin
        for f in sorted(origin.rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts: selected[alias + "/" + str(f.relative_to(origin))] = f
    selected["BASE20/t16-reviewed-snapshot-plan.json"] = a.base / "t16-reviewed-snapshot-plan.json"
    selected["task-spec/toutiao_t31_preview.rs"] = workspaces / "westlake-harness/tools/spec-checks/tests/toutiao_t31_preview.rs"
    for origin, alias in [(a.base.parent / "t31-root-landing", "outer-source-freeze"),
                          (a.base.parent / "t31-evidence-receive-01", "outer-evidence-receive")]:
        assert origin.is_dir(), origin
        for f in sorted(origin.rglob("*")):
            if f.is_file(): selected[alias + "/" + str(f.relative_to(origin))] = f
    selected["review-source/prepare_archive.py"] = Path(__file__).resolve()
    members = [{"path": n, "bytes": p.stat().st_size, "sha256": sha(p)} for n, p in sorted(selected.items())]
    (a.out / "members.json").write_text(json.dumps({"files": members}, indent=2) + "\n")
    selected["archive/members.json"] = a.out / "members.json"
    pins = {r["path"]: r for r in members}
    pins["archive/members.json"] = {"bytes": (a.out / "members.json").stat().st_size, "sha256": sha(a.out / "members.json")}
    a.out.chmod(0o700)
    archive = a.out / "window.tar.gz"
    with tarfile.open(archive, "w:gz") as t:
        for name, p in sorted(selected.items()):
            t.add(p.resolve(), arcname=name, recursive=False)
    archive.chmod(0o600)
    with tarfile.open(archive, "r:gz") as t:
        entries = t.getmembers()
        assert len(entries) == len(selected) and {m.name for m in entries} == set(selected)
        for m in entries:
            assert m.isfile() and m.size == pins[m.name]["bytes"]
            assert hashlib.sha256(t.extractfile(m).read()).hexdigest() == pins[m.name]["sha256"]
    assert all(sha(p) == pins[n]["sha256"] for n, p in selected.items()), "input changed while archiving"
    assert a.remote_root and a.remote_root.startswith("/")
    dirname = "t31-window-20261020"
    rd = a.remote_root.rstrip("/") + "/" + dirname
    remote = rd + "/window.tar.gz"
    commands = [
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "hw248",
         "set -eu; umask 077; test ! -e " + shlex.quote(rd) + "; test ! -L " + shlex.quote(rd) + "; mkdir -m 700 " + shlex.quote(rd)],
        ["scp", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", str(archive), "hw248:" + remote],
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "hw248",
         "set -eu; test ! -L " + shlex.quote(remote) + "; chmod 600 " + shlex.quote(remote) +
         "; sha256sum " + shlex.quote(remote) + "; stat -c %s " + shlex.quote(remote)],
    ]
    (a.out / "remote-commands.private.json").write_text(json.dumps(commands, indent=2) + "\n")
    result = {"status": "LOCAL_MEMBERS_VERIFIED_REMOTE_PENDING", "archive_sha256": sha(archive),
              "bytes": archive.stat().st_size, "member_count": len(selected),
              "local_member_sha_verified": True, "source_after_archive_sha_verified": True,
              "remote": "HW248_ARTIFACT_ROOT/" + dirname + "/window.tar.gz",
              "remote_verified": False, "device_calls": 0,
              "scope": "complete original T31 closed window, own before/restored snapshots, actual candidate inputs, frozen execution/helper/recovery/spec sources and offline evidence including failures; replay02 excluded; T30 production archive is separate",
              "elapsed_seconds": c["elapsed_seconds"], "within_1800_seconds": c["elapsed_seconds"] < 1800}
    (a.out / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))

if __name__ == "__main__":
    main()
