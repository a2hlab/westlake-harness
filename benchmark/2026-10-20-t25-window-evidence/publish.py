#!/usr/bin/env python3
"""Publish a closed T25 window from local evidence only; never calls devices."""
import argparse
import hashlib
import json
import subprocess
import sys
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
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    w = a.base / "t25-5cd-window-01"
    if not a.write:
        print(json.dumps({"device_calls": 0, "close_exists": (w / "close.json").is_file(),
                          "status": "PREVIEW_ONLY"}))
        return
    c = load(w / "close.json")
    assert c["unlocked"] is True and c["status"].startswith("CLOSED_")
    assert c["serial"] == "5cd1e3dd00000000000000000923012c"
    assert 0 < c["elapsed"] < 1800 and abs(c["closed_at"] - c["start"] - c["elapsed"]) < .01
    assert (w / "unlock.rc").read_text().strip() == "0"
    assert (w / "held-after-unlock.rc").read_text().strip() == "1"
    assert not (w / "held-after-unlock.stdout").read_bytes().strip()
    assert (w / "apply-exec.rc").read_text().strip() == "0"
    assert (w / "rollback-exec.rc").read_text().strip() == "0"
    rb = load(w / "rollback/result.json")
    assert rb["origin_apply_plan_sha256"] == sha(w / "apply/plan.json")
    identity = w / c["identity_raw"]
    assert sha(identity) == c["identity_sha256"]
    identity_text = identity.read_text()
    for key in ("before_sha", "bridge_before_sha", "media_before_sha", "player_before_sha", "shim_before_sha"):
        assert identity_text.count(rb[key] + "  ") == 2, key
    assert "COMPAT_ABSENT" in identity_text
    assert "Timeout=10000ms  OverrideTimeout=10000ms" in identity_text
    assert "errNum is:106!" in identity_text
    assert identity_text.rstrip().endswith("T25_SHELL_COMPLETE")
    assert identity.with_suffix(".rc").read_text().strip() == "0"
    out = HERE / "final"
    out.mkdir(exist_ok=False)
    refs = []
    def clean(text):
        return text.replace(str(a.base.resolve()), "BASE20").replace(str(a.repo.resolve()), "$MAIN").replace(str(Path.home()), "$HOME")
    def dump(name, value):
        p = out / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(clean(json.dumps(value, indent=2, ensure_ascii=False)) + "\n")
    def copy(src, name):
        p = out / name
        p.parent.mkdir(parents=True, exist_ok=True)
        data = src.read_bytes()
        p.write_bytes(data if src.suffix == ".jpeg" else clean(data.decode()).encode())
        refs.append({"path": "BASE20/" + str(src.relative_to(a.base)),
                     "sha256": sha(src), "bytes": len(data), "public_path": name,
                     "public_sha256": sha(p), "byte_exact": data == p.read_bytes()})
    for name in ("close.json", "close-preunlock.json", "context.json", "admission.json",
                 "rollback-admission.json", "apply/plan.json", "apply/result.json",
                 "rollback/plan.json", "rollback/result.json", "candidate-boot.json",
                 "restored-boot.json", "playback-review.json", "human-audio-receipt.json",
                 "restore-comparison.json"):
        if (w / name).is_file():
            copy(w / name, "receipts/" + name.replace("/", "--"))
    for stem in ("apply-exec", "rollback-exec", "unlock", "held-after-unlock",
                 "restored-supplement", "restored-supplement-02", identity.stem):
        for ext in ("argv.json", "stdout", "stderr", "rc"):
            src = w / (stem + "." + ext)
            if src.is_file():
                copy(src, "receipts/" + stem + "." + ext + (".txt" if ext == "stderr" else ""))
    before = a.base / "t25-readonly-01"
    before_boot = load(before / "before-snapshot/snapshot.json")["boot_id"]
    comparison = compare(before / "before-snapshot/snapshot.json", w / "restored-snapshot/snapshot.json",
                         before / "before-supplement", w / "restored-supplement-02", before_boot, c["restored_boot"])
    dump("independent-restoration-comparison.json", comparison)
    assert comparison["status"] == "EQUAL", "do not report restoration from close alone"
    logdir = w / "candidate-log-7777"
    lr = load(logdir / "result.json")
    data = (logdir / "selected.raw").read_bytes()
    assert sha(logdir / "selected.raw") == lr["sha256"]
    assert len(data) == lr["source_end"] and lr["immutability_not_proven"] is True
    copy(logdir / "result.json", "candidate-log-receipt.json")
    excerpts = []
    offset = 0
    for line in data.splitlines(keepends=True):
        selected = any(t in line for t in (b"[WL-R25-", b"[WL-R20-", b"[WL-R23-",
                                           b"Invalid GrBackendTexture", b"Fatal signal 6 (SIGABRT)"))
        if selected:
            assert len(line) < 1500 and b"http://" not in line and b"https://" not in line
            excerpts.append({"source_offset": offset, "length": len(line),
                             "sha256": hashlib.sha256(line).hexdigest(), "text": line.decode()})
        offset += len(line)
    dump("technical-excerpts.json", {"source_sha256": lr["sha256"], "source_bytes": len(data),
                                    "immutability_not_proven": True, "rows": excerpts})
    texts = [r["text"] for r in excerpts]
    geometry = [x for x in texts if "[WL-R25-GEOMETRY]" in x]
    locks = [x for x in texts if "[WL-R20-PAIR]" in x and "op=lock " in x]
    unlocks = [x for x in texts if "[WL-R20-PAIR]" in x and "op=unlock " in x]
    assert len(geometry) == 4 and all("wh=576x1024 fmt=842094169" in x and "result=0" in x for x in geometry)
    assert len(locks) == len(unlocks) == 3
    assert all("rc=0" in x for x in locks + unlocks)
    shots = []
    names = ["capture-1792470720036057000", "capture-1792470803792776000",
             "capture-1792470808838965000", "capture-1792470813842123000",
             "capture-1792470823841190000"]
    for i, name in enumerate(names):
        src = w / name / "screen.jpeg"
        dest = "images/candidate-feed.jpeg" if i == 0 else "images/cycle-" + str(i) + ".jpeg"
        copy(src, dest)
        shots.append({"path": dest, "sha256": sha(src)})
    copy(w / "cycle-observation-01/result.json", "cycle-result.json")
    copy(w / "restored-icon/after-icon.jpeg", "images/restored-host.jpeg")
    copy(w / "restored-icon/record.json", "restored-icon-record.json")
    copy(w / "candidate-icon/record.json", "candidate-icon-record.json")
    dump("image-review.json", {"reviewer": "Codex video_plan; actual images read",
                              "candidate_feed": "VISIBLE", "cycle": "HOST_ONLY; first three identical, final status icon differs",
                              "restored_ui": "HOST_ONLY_NOT_FEED",
                              "video": "NOT_PASSED", "images": shots})
    run = subprocess.run([sys.executable, str(a.repo / "scripts/lab/run_facts.py"), str(w)], capture_output=True, timeout=30)
    assert run.returncode == 0
    (out / "facts.txt").write_bytes(run.stdout)
    (out / "facts.stderr.txt").write_bytes(run.stderr)
    dump("facts-receipt.json", {"rc": run.returncode, "helper_sha256": sha(a.repo / "scripts/lab/run_facts.py"),
                               "record_schema_only": True, "explicitly_indexed_candidate_images": 5,
                               "no_synthetic_records": True})
    dump("results.json", {"status": c["status"], "elapsed_seconds": c["elapsed"],
                          "close": c, "independent_restoration": comparison["status"],
                          "geometry_success_records": len(geometry), "lock_success_records": len(locks),
                          "unlock_flush_success_records": len(unlocks),
                          "next_observed_failure": "R23 create failed then Invalid GrBackendTexture 576x1024 and SIGABRT",
                          "cause_of_create_failure": "UNKNOWN", "candidate_feed": "VISIBLE",
                          "video": "NOT_PASSED", "T25_audio": c["audio"],
                          "T23_audio": "prior user-confirmed audible; unchanged",
                          "live_three_slot_evidence": "candidate in-process gate log; no independent external slot receipt in this package",
                          "archive_remote": "PENDING", "author_device_calls": 0})
    helpers = sorted(a.base.glob("t25_*.py")) + [a.base / "t25-helpers-prepared.json"]
    assert all(p.is_file() for p in helpers)
    dump("raw-archive-allowlist.json", {"directories": ["t25-5cd-window-01", "t25-readonly-01", "t25-candidate-inputs"],
                                      "files": [p.name for p in helpers],
                                      "scope": "whole closed raw window, all readonly snapshots, actual candidate inputs and outer helper source"})
    dump("source-index.json", refs)
    print(json.dumps({"status": "CLOSED_LOCAL_EVIDENCE_PUBLISHED", "video": "NOT_PASSED",
                      "restoration": comparison["status"], "author_device_calls": 0}))

if __name__ == "__main__":
    main()
