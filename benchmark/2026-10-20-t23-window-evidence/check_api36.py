#!/usr/bin/env python3
"""Check the additive row with the existing renderer in an isolated local copy."""
import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--main", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    main_root = args.main.resolve()
    canonical = main_root / "benchmark/2026-10-19-api-progress-update"
    original_sha = sha(canonical / "observations.json")
    original = json.loads((canonical / "observations.json").read_text())
    row = json.loads((HERE / "api36-proposal.json").read_text())
    assert len(original["rows"]) == 35
    assert row["id"] not in {r["id"] for r in original["rows"]}
    assert row["frozen"] is False
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    stage = out / "source-root"
    render_dir = stage / "benchmark/2026-10-19-api-progress-update"
    render_dir.mkdir(parents=True)
    shutil.copyfile(canonical / "render.py", render_dir / "render.py")
    count = 0
    for group in ("source", "build", "evidence"):
        for item in row[group]:
            rel = Path(item["path"])
            assert not rel.is_absolute() and ".." not in rel.parts
            source = ROOT / rel if rel.is_relative_to(HERE.relative_to(ROOT)) else main_root / rel
            assert source.is_file() and not source.is_symlink()
            assert sha(source) == item["sha256"], str(rel)
            dest = stage / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
            count += 1
    data = {k: v for k, v in original.items() if k != "rows"}
    data["rows"] = [row]
    (render_dir / "observations.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    argv = [sys.executable, str(render_dir / "render.py"), "--source-root", str(stage)]
    (out / "argv.json").write_text(json.dumps(argv, indent=2) + "\n")
    with (out / "stdout.txt").open("wb") as stdout, (out / "stderr.txt").open("wb") as stderr:
        result = subprocess.run(argv, stdout=stdout, stderr=stderr, check=False)
    (out / "rc").write_text(str(result.returncode) + "\n")
    assert result.returncode == 0
    with (render_dir / "observations.csv").open(encoding="utf-8-sig", newline="") as stream:
        csv_rows = list(csv.DictReader(stream))
    assert len(csv_rows) == 1
    for key, value in row.items():
        if isinstance(value, list):
            assert json.loads(csv_rows[0][key]) == value
        else:
            assert csv_rows[0][key] == str(value)
    assert sha(canonical / "observations.json") == original_sha
    receipt = {
        "status": "PASS_ROW_ONLY_RENDER",
        "proposal_sha256": sha(HERE / "api36-proposal.json"),
        "canonical_input_sha256": original_sha,
        "original_rows": 35,
        "original_rows_changed": 0,
        "historical_315_changed": False,
        "references_verified": count,
        "renderer_sha256": sha(canonical / "render.py"),
        "render_rc": result.returncode,
        "stdout_sha256": sha(out / "stdout.txt"),
        "stderr_sha256": sha(out / "stderr.txt"),
        "csv_all_fields_equal": True,
        "scope": "Only the new row was rendered; no canonical table was written.",
        "device_calls": 0,
    }
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
