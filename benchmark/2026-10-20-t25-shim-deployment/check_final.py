#!/usr/bin/env python3
"""Check only T25 data and pre-Board refusals; no transaction or device replay."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

P = Path(__file__).resolve().parent
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):
    return json.loads(p.read_text())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-root", type=Path, action="append", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    sources = []
    def resolve(path, expected):
        assert not Path(path).is_absolute() and ".." not in Path(path).parts
        hits = [(i, root / path) for i, root in enumerate(a.source_root)
                if (root / path).is_file() and sha(root / path) == expected]
        assert hits, "missing exact source: " + path
        index, file = hits[0]
        sources.append({"path": path, "sha256": expected, "source_root_index": index})
        return file
    for row in load(P / "unchanged-pins.json"):
        assert sha(P / row["file"]) == row["sha256"]
        assert (P / row["file"]).read_bytes() == resolve(row["donor"], row["sha256"]).read_bytes()
    pending = load(P / "history-pending/parameters.json")
    params = load(P / "parameters.json")
    assert params["artifacts"][:5] == pending["artifacts"][:5]
    ad = load(P / "admission.template.json")
    for field in ("approved_by", "boot", "holder", "window_start", "parent_mnt",
                  "origin_apply_plan_sha256", "bridge_metadata", "shim_metadata",
                  "fresh_three_slot_receipt_sha256"):
        assert ad[field] is None, field
    assert ad["host"] == {"pid": None, "birth": None, "uid": 20011300}
    for field, file in (("executor_sha256", "executor.py"),
                        ("parameters_sha256", "parameters.json"),
                        ("source_pins_sha256", "executor-source-pins.json"),
                        ("readonly_inputs_sha256", "readonly-inputs.json"),
                        ("bridge_candidate_sha256", "bridge-candidate.json"),
                        ("shim_candidate_sha256", "shim-candidate.json"),
                        ("three_slot_requirements_sha256", "three-slot-admission.json")):
        assert ad[field] == sha(P / file), field
    candidate = load(P / "shim-candidate.json")
    inspection = load(P / "candidate-inspection.json")
    assert {"sha256": candidate["after_sha256"], "bytes": candidate["after_bytes"]} == inspection["candidate"]
    assert candidate["build_status"] == "PRODUCTION_BUILD_VERIFIED"
    assert candidate["after_sha256"] == params["artifacts"][-1]["after_sha256"]
    slots = load(P / "three-slot-admission.json")
    assert slots["candidate_sha256"] == candidate["after_sha256"]
    assert [(x["symbol"], x["player_slot"], x["candidate_export_offset"]) for x in slots["slots"]] == [
        ("ANativeWindow_setBuffersGeometry", "0x472048", "0xd7e4"),
        ("ANativeWindow_lock", "0x472490", "0x6c28"),
        ("ANativeWindow_unlockAndPost", "0x472760", "0x6c3c")]
    assert all(x["actual_slot_value"] is None and x["matched"] is False for x in slots["slots"])
    view = a.out / "receipt-view"
    for record in (load(P / "bridge-candidate.json"), candidate):
        assert record["production_refs"]
        for ref in record["production_refs"]:
            src = resolve(ref["path"], ref["sha256"])
            dest = view / ref["path"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src.read_bytes())
    index_ref = next(x for x in candidate["production_refs"]
                     if x["path"].endswith("/evidence/public-source-index.json"))
    index = load(resolve(index_ref["path"], index_ref["sha256"]))
    for row in index:
        resolve("benchmark/2026-10-20-t25-geometry/" + row["public_path"], row["public_sha256"])
    runs = []
    for mode in ("preflight", "apply", "rollback"):
        for execute in (False, True):
            argv = [sys.executable, str(P / "executor.py"), mode]
            if execute:
                argv += ["--execute", "--boot", "OFFLINE_SENTINEL", "--parent", "1",
                         "--birth", "1", "--hdc", "/NONEXISTENT_T25_NO_DEVICE",
                         "--holder", "OFFLINE_SENTINEL", "--out", str(a.out.resolve() / mode),
                         "--repo", str(view.resolve()), "--inputs", str(a.out.resolve()),
                         "--admission", str(P / "admission.template.json"), "--start", "1"]
            r = subprocess.run(argv, capture_output=True, timeout=10)
            name = mode + ("-execute-sentinel" if execute else "-preview")
            (a.out / (name + ".argv.json")).write_text(json.dumps(argv, indent=2) + "\n")
            (a.out / (name + ".stdout")).write_bytes(r.stdout)
            (a.out / (name + ".stderr")).write_bytes(r.stderr)
            (a.out / (name + ".rc")).write_text(str(r.returncode) + "\n")
            if execute:
                assert r.returncode != 0 and b"TypeError" in r.stderr and b"shim_metadata" in r.stderr
            else:
                assert r.returncode == 0 and json.loads(r.stdout)["device_calls"] == 0
            runs.append({"name": name, "rc": r.returncode,
                         "expected": "null fresh shim metadata rejected before Board import" if execute else "preview"})
    result = {"status": "STATIC_DATA_VERIFIED_NOT_ADMISSION", "sources": sources,
              "runs": runs, "device_calls": 0, "transaction_tests_rerun": False,
              "public_evidence_files_verified": len(index),
              "live_three_slots": "UNKNOWN", "approved_by": None}
    (a.out / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))

if __name__ == "__main__":
    main()
