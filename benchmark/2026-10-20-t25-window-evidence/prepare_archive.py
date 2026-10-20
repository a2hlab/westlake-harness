#!/usr/bin/env python3
"""T23 archive pattern adapted to the complete closed T25 allowlist; local only."""
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
    close = a.base / "t25-5cd-window-01/close.json"
    c = load(close)
    assert c["unlocked"] is True and c["status"].startswith("CLOSED_") and c["elapsed"] < 1800
    assert load(HERE / "final/results.json")["close"] == c
    assert (close.parent / "unlock.rc").read_text().strip() == "0"
    assert (close.parent / "held-after-unlock.rc").read_text().strip() == "1"
    assert not (close.parent / "held-after-unlock.stdout").read_bytes().strip()
    assert a.out.is_absolute() and not str(a.out).startswith(("/tmp/", "/private/tmp/"))
    a.out.mkdir(parents=True, exist_ok=False)
    allow = load(HERE / "final/raw-archive-allowlist.json")
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
    for p in sorted((HERE / "final").rglob("*")):
        if p.is_file():
            selected["final-public/" + str(p.relative_to(HERE / "final"))] = p
    for name in ("publish.py", "compare_restore.py", "prepare_archive.py", "reuse-boundary.json"):
        selected["review-source/" + name] = HERE / name
    for p in sorted((HERE / "egl-contract").rglob("*")):
        if p.is_file():
            selected["peer-public/" + str(p.relative_to(HERE / "egl-contract"))] = p
    peer_archive = Path.home() / ".local/share/westlake/t25-egl-contract-evidence.tar.gz"
    assert peer_archive.stat().st_size == 815751
    assert sha(peer_archive) == "4bf8b8d96d50213fb84d3e6f87bf8dde53ca4faf9fae20d5336d63ac23106edb"
    selected["peer-raw/t25-egl-contract-evidence.tar.gz"] = peer_archive
    peer_review = Path.home() / ".local/share/westlake/t25-codex-review/runtime-review-01.json"
    assert sha(peer_review) == load(HERE / "egl-contract/source-index.json")["runtime_review_original_sha256"]
    selected["peer-raw/runtime-review-01.json"] = peer_review
    members = [{"path": n, "bytes": p.stat().st_size, "sha256": sha(p)} for n, p in sorted(selected.items())]
    (a.out / "members.json").write_text(json.dumps({"files": members}, indent=2) + "\n")
    selected["archive/members.json"] = a.out / "members.json"
    pins = {r["path"]: r for r in members}
    pins["archive/members.json"] = {"bytes": (a.out / "members.json").stat().st_size, "sha256": sha(a.out / "members.json")}
    archive = a.out / "window.tar.gz"
    with tarfile.open(archive, "w:gz") as t:
        for name, p in sorted(selected.items()):
            t.add(p.resolve(), arcname=name, recursive=False)
    with tarfile.open(archive, "r:gz") as t:
        entries = t.getmembers()
        assert len(entries) == len(selected) and {m.name for m in entries} == set(selected)
        for m in entries:
            assert m.isfile() and m.size == pins[m.name]["bytes"]
            assert hashlib.sha256(t.extractfile(m).read()).hexdigest() == pins[m.name]["sha256"]
    assert all(sha(p) == pins[n]["sha256"] for n, p in selected.items()), "input changed while archiving"
    assert a.remote_root and a.remote_root.startswith("/")
    dirname = "toutiao-t25-geometry-window-20261020"
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
              "scope": "complete T25 closed window, readonly snapshots, actual candidate inputs, outer helper source and final public evidence"}
    (a.out / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))

if __name__ == "__main__":
    main()
