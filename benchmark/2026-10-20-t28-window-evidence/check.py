#!/usr/bin/env python3
"""Read-only replay of local published receipts against original T28 evidence."""
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
    w = a.base / "t28-5cd-window-01"
    close = load(w / "close.json")
    assert load(final / "results.json")["close"] == close
    assert close["unlocked"] and close["elapsed"] < 1800
    assert (w / "unlock.rc").read_text().strip() == "0"
    assert (w / "held-after.rc").read_text().strip() == "1"
    assert not (w / "held-after.stdout").read_bytes().strip()
    refs = load(final / "source-index.json")
    for row in refs:
        source = (a.base / row["path"].removeprefix("BASE20/")) if row["path"].startswith("BASE20/") else (Path.home() / row["path"].removeprefix("$HOME/"))
        assert sha(source) == row["sha256"] and source.stat().st_size == row["bytes"]
        assert sha(final / row["public_path"]) == row["public_sha256"]
    before = a.base / "t26-5cd-window-01"
    boot = load(before / "restored-snapshot/snapshot.json")["boot_id"]
    actual = compare(before / "restored-snapshot/snapshot.json", w / "restored-snapshot/snapshot.json",
                     before / "restored-supplement", w / "restored-supplement", boot, close["restored_boot"])
    assert actual == load(final / "independent-restoration-comparison.json") and actual["status"] == "EQUAL"
    total = 0
    for selected in load(HERE / "peer-review-inputs.json")["logs"]:
        key = selected["directory"]
        data = (w / key / "selected.raw").read_bytes()
        excerpts = load(final / ("technical-excerpts-" + key + ".json"))
        assert hashlib.sha256(data).hexdigest() == excerpts["source_sha256"]
        for row in excerpts["rows"]:
            raw = data[row["source_offset"]:row["source_offset"] + row["length"]]
            assert hashlib.sha256(raw).hexdigest() == row["sha256"] and raw.decode() == row["text"]
        total += len(excerpts["rows"])
    print(json.dumps({"status": "PASS_PUBLISHED_LOCAL_EVIDENCE", "source_receipts": len(refs),
                      "technical_excerpts": total, "restoration": "EQUAL",
                      "remote_verification": "SEPARATE_PENDING_RECEIPT", "video": "TWO_DIFFERENT_CLIPS_SCOPED_WITH_BLACK_TRANSITION_NOT_SEALED",
                      "device_calls": 0, "new_remote_commands": 0}))

if __name__ == "__main__":
    main()
