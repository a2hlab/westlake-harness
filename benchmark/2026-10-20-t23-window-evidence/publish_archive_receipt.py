#!/usr/bin/env python3
"""Append verified outer upload evidence; never rewrite the original pending receipt."""
import argparse
import hashlib
import json
import re
from pathlib import Path
HERE = Path(__file__).resolve().parent

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def clean(text):
    text = text.replace(str(HERE), "$LANE/benchmark/2026-10-20-t23-window-evidence")
    text = text.replace(str(Path.home()), "$HOME")
    text = re.sub(r"/home/[^/ \n\"']+", "HW248_ARTIFACT_ROOT", text)
    text = re.sub(r"[a-zA-Z0-9_.-]+@(?=(?:[0-9]{1,3}\.){3}[0-9]{1,3})", "", text)
    return re.sub(r"(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])", "HW248_HOST", text)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    src = HERE / ".private/upload-01"
    original = HERE / "archive/pending.json"
    before = sha(original)
    pending = json.loads(original.read_text())
    receipt = json.loads((src / "receipt.json").read_text())
    assert receipt["status"] == "REMOTE_VERIFIED" and receipt["remote_verified"] is True
    assert receipt["archive_sha256"] == pending["archive_sha256"]
    assert receipt["bytes"] == pending["bytes"]
    assert len(receipt["commands"]) == 3
    for i, command in enumerate(receipt["commands"]):
        assert command["index"] == i and command["rc"] == 0
        assert (src / f"{i}.rc").read_text().strip() == "0"
        for item in command["files"]:
            p = src / item["name"]
            assert sha(p) == item["sha256"] and p.stat().st_size == item["bytes"]
    remote = (src / "2.stdout").read_text().splitlines()
    assert remote[0].split()[0] == pending["archive_sha256"]
    assert remote[-1].strip() == str(pending["bytes"])
    out = HERE / "outer-success"
    if a.write:
        out.mkdir(exist_ok=False)
        refs = []
        for p in sorted(src.iterdir()):
            if not p.is_file():
                continue
            name = p.name + ".txt" if p.suffix == ".stderr" else p.name
            q = out / name
            q.write_text(clean(p.read_text()))
            refs.append({"private_alias": ".private/upload-01/" + p.name,
                         "sha256": sha(p), "bytes": p.stat().st_size,
                         "public_path": name, "public_sha256": sha(q)})
        (out / "source-index.json").write_text(json.dumps(refs, indent=2) + "\n")
        (out / "verification.json").write_text(json.dumps({
            "status": "REMOTE_VERIFIED", "executor": "outer(codex)",
            "archive_sha256": receipt["archive_sha256"], "bytes": receipt["bytes"],
            "member_count": pending["member_count"], "command_rcs": [0, 0, 0],
            "remote_sha_size_match": True, "original_pending_sha256": before,
            "archive_repacked": False, "prior_pending_preserved": True,
            "raw_argv_index": "source-index.json", "remote_git_push_claimed": False
        }, indent=2) + "\n")
    assert sha(original) == before
    print(json.dumps({"status": "REMOTE_VERIFIED", "write": a.write,
                      "original_pending_preserved": True}))

if __name__ == "__main__":
    main()
