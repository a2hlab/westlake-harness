#!/usr/bin/env python3
"""Reuse canonical renderer in an isolated copy; preserve all 37 original objects."""
import argparse
import csv
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

P = Path(__file__).resolve().parent
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-root", type=Path, required=True)
    ap.add_argument("--proposal-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    m = a.source_root.resolve()
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    pre = json.loads((P / "preimage.json").read_text())
    c = m / pre["canonical"]
    def guard():
        for ref in pre["files"]:
            assert sha(m / ref["path"]) == ref["sha256"], ref["path"]
    guard()
    old = json.loads((c / "observations.json").read_text())
    assert len(old["rows"]) == 37 and old["historical_rows"] == 315
    row = json.loads((P / "proposal.json").read_text())
    assert "DRAFT" not in row["status"] and row["frozen"] is False
    assert "VIDEO_NOT_PASSED" in row["status"]
    new = json.loads(json.dumps(old))
    new["rows"].append(row)
    assert new["rows"][:37] == old["rows"] and len(new["rows"]) == 38
    view = out / "reference-view"
    unique = {}
    for observation in new["rows"]:
        for group in ("source", "build", "evidence"):
            for ref in observation[group]:
                relative = Path(ref["path"])
                assert not relative.is_absolute() and ".." not in relative.parts
                roots = [m] if observation is not new["rows"][-1] else [m, a.proposal_root]
                found = [root / relative for root in roots
                         if (root / relative).is_file() and sha(root / relative) == ref["sha256"]]
                assert found, ref["path"]
                dest = view / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists():
                    assert sha(dest) == ref["sha256"]
                else:
                    shutil.copyfile(found[0], dest)
                unique[str(relative)] = ref["sha256"]
    (out / "observations.json").write_text(json.dumps(new, ensure_ascii=False, indent=2) + "\n")
    shutil.copyfile(c / "render.py", out / "render.py")
    assert sha(out / "render.py") == sha(c / "render.py")
    argv = ["python3", str(out / "render.py"), "--source-root", str(view)]
    (out / "argv.json").write_text(json.dumps(argv, indent=2) + "\n")
    r = subprocess.run(argv, capture_output=True, timeout=60)
    for suffix, data in (("stdout", r.stdout), ("stderr", r.stderr), ("rc", (str(r.returncode) + "\n").encode())):
        (out / suffix).write_bytes(data)
    assert r.returncode == 0, r.stderr
    rows = list(csv.DictReader((out / "observations.csv").open(encoding="utf-8-sig")))
    assert len(rows) == 38
    for left, right in zip(rows, new["rows"]):
        for key, value in right.items():
            assert (json.loads(left[key]) if isinstance(value, list) else left[key]) == (value if isinstance(value, list) else str(value))
    assert (out / "index.html").read_text().count("<article>") == 38
    guard()
    result = {"status": "PASS_PROPOSAL_ONLY", "old37_objects_unchanged": True,
              "historical315_unchanged": True, "canonical_main_files_unchanged": True,
              "copied_renderer_sha256": sha(out / "render.py"), "rendered_rows": 38,
              "references_verified": json.loads((out / "results.json").read_text())["references_verified"],
              "unique_reference_files": len(unique), "csv_all_fields_equal": True,
              "html_cards": 38, "device_calls": 0, "OH_playback_pass_increment": 0,
              "frozen_API_count_increment": 0, "promotion_requires_outer": True}
    (out / "check-results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))

if __name__ == "__main__":
    main()
