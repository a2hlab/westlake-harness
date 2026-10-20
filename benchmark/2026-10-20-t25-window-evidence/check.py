#!/usr/bin/env python3
"""Read-only replay of local published receipts against original T25 evidence."""
import argparse
import hashlib
import json
from pathlib import Path
from compare_restore import compare

HERE = Path(__file__).resolve().parent
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):
    return json.loads(p.read_text())
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, required=True)
    a = ap.parse_args()
    final = HERE / "final"
    w = a.base / "t25-5cd-window-01"
    close = load(w / "close.json")
    assert load(final / "results.json")["close"] == close
    assert close["unlocked"] and close["elapsed"] < 1800
    assert (w / "unlock.rc").read_text().strip() == "0"
    assert (w / "held-after-unlock.rc").read_text().strip() == "1"
    assert not (w / "held-after-unlock.stdout").read_bytes().strip()
    refs = load(final / "source-index.json")
    for row in refs:
        source = a.base / row["path"].removeprefix("BASE20/")
        assert sha(source) == row["sha256"] and source.stat().st_size == row["bytes"]
        assert sha(final / row["public_path"]) == row["public_sha256"]
    before = a.base / "t25-readonly-01"
    boot = load(before / "before-snapshot/snapshot.json")["boot_id"]
    actual = compare(before / "before-snapshot/snapshot.json", w / "restored-snapshot/snapshot.json",
                     before / "before-supplement", w / "restored-supplement-02", boot, close["restored_boot"])
    assert actual == load(final / "independent-restoration-comparison.json") and actual["status"] == "EQUAL"
    data = (w / "candidate-log-7777/selected.raw").read_bytes()
    excerpts = load(final / "technical-excerpts.json")
    assert hashlib.sha256(data).hexdigest() == excerpts["source_sha256"]
    for row in excerpts["rows"]:
        raw = data[row["source_offset"]:row["source_offset"] + row["length"]]
        assert hashlib.sha256(raw).hexdigest() == row["sha256"] and raw.decode() == row["text"]
    remote = load(HERE / "remote-success/results.json")
    pending = load(HERE / "archive-preparation.json")
    assert remote["remote_verified"] and remote["status"] == "REMOTE_AND_ALL_MEMBERS_VERIFIED"
    assert remote["archive_sha256"] == pending["archive_sha256"] and remote["bytes"] == pending["bytes"]
    assert all(x["rc"] == 0 for x in remote["commands"])
    assert remote["directory_mode"] == "700" and remote["file_mode"] == "600"
    assert remote["verification"]["members"] == pending["member_count"]
    print(json.dumps({"status": "PASS_PUBLISHED_EVIDENCE", "source_receipts": len(refs),
                      "technical_excerpts": len(excerpts["rows"]), "restoration": "EQUAL",
                      "remote_members": pending["member_count"], "video": "NOT_PASSED",
                      "device_calls": 0, "new_remote_commands": 0}))

if __name__ == "__main__":
    main()
