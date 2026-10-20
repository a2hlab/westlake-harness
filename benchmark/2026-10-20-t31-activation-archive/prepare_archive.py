#!/usr/bin/env python3
"""T30 archive pattern adapted to the complete closed T31 retained activation window allowlist; local only."""
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
    assert c["status"] == "CLOSED_CANDIDATE_RETAINED_ARCHIVAL_SEAL_PENDING" and c["elapsed_seconds"] > 0
    # Preserve an actual deadline overrun if present; archiving does not approve it.
    assert (close.parent / "unlock.rc").read_text().strip() == "0"
    assert (close.parent / "held-after.rc").read_text().strip() == "1"
    assert not (close.parent / "held-after.stdout").read_bytes().strip()
    assert a.out.is_absolute() and not str(a.out).startswith(("/tmp/", "/private/tmp/"))
    a.out.mkdir(parents=True, exist_ok=False)
    allow = {"directories": ["t31-5cd-window-01"], "files": sorted(p.name for p in a.base.glob("t31_*.py"))}
    allow["directories"] += sorted(p.name for p in a.base.glob("t31-fresh-readonly-*") if p.is_dir())
    assert len(allow["directories"]) >= 1
    selected = {}
    for name in allow["directories"]:
        base = a.base / name
        assert base.is_dir()
        for p in sorted(base.rglob("*")):
            if p.is_file():
                selected["ACTIVATION01/" + str(p.relative_to(a.base))] = p
    for name in allow["files"]:
        p = a.base / name
        assert p.is_file()
        selected["ACTIVATION01/" + name] = p
    inputs = a.base.parent / "t30-candidate-inputs"
    assert inputs.is_dir()
    for f in sorted(inputs.rglob("*")):
        if f.is_file(): selected["original-BASE20/t30-candidate-inputs/" + str(f.relative_to(inputs))] = f
    peer = a.base.parent.parent / "t31-activation-codex-review"
    assert peer.is_dir()
    for f in sorted(peer.rglob("*")):
        if f.is_file(): selected["peer-runtime/" + str(f.relative_to(peer))] = f
    workspaces = Path(__file__).resolve().parents[3]
    # Include the actual mainline execution sources plus the author's original
    # offline helper receipts; production itself has a separate complete archive.
    for producer, names, alias in [
        (workspaces / "westlake-harness/benchmark/2026-10-20-t31-demo-retain",
         ["helpers", "recovery", "evidence", "evidence-delivery", "activation-verified", "activation-prep"], "main-execution-tools"),
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
    selected["ACTIVATION01/t16-reviewed-snapshot-plan.json"] = a.base / "t16-reviewed-snapshot-plan.json"
    selected["task-spec/toutiao_t31_preview.rs"] = workspaces / "westlake-harness/tools/spec-checks/tests/toutiao_t31_preview.rs"
    for origin, alias in [(a.base.parent.parent / "t31-root-landing", "outer-source-freeze"),
                          (a.base.parent.parent / "t31-evidence-receive-01", "outer-evidence-receive")]:
        assert origin.is_dir(), origin
        for f in sorted(origin.rglob("*")):
            if f.is_file(): selected[alias + "/" + str(f.relative_to(origin))] = f
    decision = load(close.parent / "retain-decision.json")
    assert decision["retained"] is True and c["candidate_retained"] is True
    main = workspaces / "westlake-harness"
    for ref in decision["source_production_recovery_reuse_refs"]:
        assert ref["path"].startswith("$MAIN/")
        rel = ref["path"][6:]; src = main / rel
        assert sha(src) == ref["sha256"] and src.stat().st_size == ref["bytes"]
        selected["decision-source-refs/" + rel] = src
    for backup in decision["origin_backups"]["five_files"]:
        src = main / "benchmark/2026-10-20-t30-request-recovery/deployment/final-01/run5cd.before.reference.sh" if backup["path"].split("/")[-1].startswith("run.sh.") else workspaces / "westlake-inputs/seal-artifacts-20261012/sha256" / backup["sha256"]
        assert sha(src) == backup["sha256"]
        selected["original-before-source-bytes/" + backup["sha256"]] = src
    reused = load(main / "benchmark/2026-10-20-t31-demo-retain/activation-verified/reused-evidence.json")
    for ref in reused["refs"] + reused["frames"]:
        assert ref["path"].startswith("$HOME/")
        src = Path.home() / ref["path"][6:]
        assert sha(src) == ref["sha256"] and src.stat().st_size == ref["bytes"]
        selected["reused-evidence/" + ref["path"][6:]] = src
    selected["original-before-source-bytes/source-index.json"] = a.base.parent.parent / "t31-activation-archive/original-five-source-index.json"
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
    dirname = "t31-retained-activation-20261020"
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
              "scope": "complete retained activation window with signed decision and close, actual candidate inputs, origin backup guard evidence and exact local five-before source bytes, full execution/recovery/t4 sources, independent peer, referenced replay18frames and user statement; final archival seal excluded; production archives separate",
              "elapsed_seconds": c["elapsed_seconds"], "within_1800_seconds": c["elapsed_seconds"] < 1800}
    (a.out / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))

if __name__ == "__main__":
    main()
