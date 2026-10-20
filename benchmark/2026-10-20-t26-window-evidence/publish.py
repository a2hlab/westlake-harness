#!/usr/bin/env python3
"""Publish a closed T26 window from local evidence only; never calls devices."""
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
    ap.add_argument("--after-supplement", default="restored-supplement")
    a = ap.parse_args()
    w = a.base / "t26-5cd-window-01"
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
    assert identity_text.rstrip().endswith("T26_SHELL_COMPLETE")
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
                 "restore-comparison.json", "restoration-comparison.json", "visual-review.json", "interim-visual-review.json"):
        if (w / name).is_file():
            copy(w / name, "receipts/" + name.replace("/", "--"))
    for stem in ("apply-exec", "rollback-exec", "unlock", "held-after-unlock",
                 "restored-supplement", "restored-supplement-02", identity.stem):
        for ext in ("argv.json", "stdout", "stderr", "rc"):
            src = w / (stem + "." + ext)
            if src.is_file():
                copy(src, "receipts/" + stem + "." + ext + (".txt" if ext == "stderr" else ""))
    before = a.base / "t26-readonly-01"
    before_boot = load(before / "before-snapshot/snapshot.json")["boot_id"]
    comparison = compare(before / "before-snapshot/snapshot.json", w / "restored-snapshot/snapshot.json",
                         before / "before-supplement", w / a.after_supplement, before_boot, c["restored_boot"])
    dump("independent-restoration-comparison.json", comparison)
    assert comparison["status"] == "EQUAL", "do not report restoration from close alone"
    review = load(HERE / "peer-review-inputs.json")
    assert review["boot"] == load(w / "candidate-log-13338/result.json")["boot"]
    logs = {}
    for pid, expected in ((7603, "c55c8ee75d062332d583aedf4d227f6263cfcdb3fb7e019c225cf06a6eddb7de"),
                          (13338, "c1a519a981d15c60f6cc31f93a5f180f7f52e4f9fa94d162073f98040134d537")):
        logdir = w / ("candidate-log-" + str(pid))
        lr = load(logdir / "result.json")
        data = (logdir / "selected.raw").read_bytes()
        assert sha(logdir / "selected.raw") == lr["sha256"] == expected
        assert len(data) == lr["source_end"] and lr["immutability_not_proven"] is True
        copy(logdir / "result.json", "log-" + str(pid) + "-receipt.json")
        excerpts = []
        offset = 0
        for line in data.splitlines(keepends=True):
            if any(t in line for t in (b"[WL-R25-", b"[WL-R20-", b"[WL-R23-", b"[WL-T27]",
                                      b"Invalid GrBackendTexture", b"Fatal signal")):
                assert len(line) < 2000 and b"http://" not in line and b"https://" not in line
                excerpts.append({"source_offset": offset, "length": len(line),
                                 "sha256": hashlib.sha256(line).hexdigest(), "text": line.decode()})
            offset += len(line)
        texts = [r["text"] for r in excerpts]
        counts = {tag: sum(tag in x for x in texts) for tag in
                  ("WL-R25-GEOMETRY", "WL-T27", " p=3 ", " p=4 ", "print-cap=256", "Invalid GrBackendTexture", "Fatal signal")}
        logs[str(pid)] = {"source_sha256": expected, "source_bytes": len(data), "counts": counts,
                         "immutability_not_proven": True, "rows": excerpts}
        dump("technical-excerpts-" + str(pid) + ".json", logs[str(pid)])
    assert logs["13338"]["counts"]["WL-R25-GEOMETRY"] == 7
    assert logs["13338"]["counts"][" p=3 "] == logs["13338"]["counts"][" p=4 "] == 3
    assert logs["13338"]["counts"]["print-cap=256"] == 1
    for image in review["images"]:
        assert sha(w / image["source"]) == image["sha256"]
        copy(w / image["source"], image["public_path"])
        shot = (w / image["source"]).with_name("screenshot.json")
        if shot.is_file():
            copy(shot, "image-receipts/" + Path(image["public_path"]).stem + ".json")
    for name in ("candidate-icon", "candidate-icon-reentry", "cycle02-icon-reentry"):
        copy(w / name / "record.json", name + "-record.json")
    for name in ("candidate-icon-reentry", "cycle02-icon-reentry"):
        q = load(w / name / "quick/result.json")
        assert q["pid"] == 13338 and q["birth"] == 19234 and q["boot"] == review["boot"]
        copy(w / name / "quick/result.json", name + "-identity.json")
    for name in ("cycle-observation-01", "cycle-observation-02", "cycle-resume-01", "cycle-resume-02"):
        copy(w / name / "result.json", name + ".json")
    copy(w / "restored-icon/after-icon.jpeg", "images/restored-ui.jpeg")
    copy(w / "restored-icon/record.json", "restored-icon-record.json")
    review["status"] = "CLOSED_TWO_CYCLES_VISUALLY_OBSERVED_SCOPED"
    review["audio"] = c["audio"]
    review["restored_ui"] = "HOST_ONLY_INDEPENDENTLY_VIEWED"
    review["limitations"][-1] = "Audio follows this window human/close receipt only; restored runtime does not establish UI recovery"
    dump("image-review.json", review)
    run = subprocess.run([sys.executable, str(a.repo / "scripts/lab/run_facts.py"), str(w)], capture_output=True, timeout=30)
    assert run.returncode == 0
    (out / "facts.txt").write_bytes(run.stdout)
    (out / "facts.stderr.txt").write_bytes(run.stderr)
    dump("facts-receipt.json", {"rc": run.returncode, "helper_sha256": sha(a.repo / "scripts/lab/run_facts.py"),
                               "record_schema_only": True, "explicitly_indexed_candidate_images": len(review["images"]),
                               "no_synthetic_records": True})
    dump("results.json", {"status": c["status"], "elapsed_seconds": c["elapsed"], "close": c,
                          "independent_restoration": comparison["status"],
                          "selected_logs": {pid: {k: v for k, v in item.items() if k != "rows"} for pid, item in logs.items()},
                          "first_child": "RGBX2 -> OH11 import -> actual Mali create NULL -> fatal; retained failure",
                          "candidate_feed": "VISIBLE_AFTER_NORMAL_ICON_REENTRY",
                          "video": review["video"], "audio": c["audio"],
                          "cycle2": "same child13338/b19234 foreground via desktop icon; not cold restart",
                          "archive_remote": "PENDING", "author_device_calls": 0})
    helpers = sorted(a.base.glob("t26_*.py")) + [a.base / "t26-helpers-prepared.json"]
    assert all(p.is_file() for p in helpers)
    dump("raw-archive-allowlist.json", {"directories": ["t26-5cd-window-01", "t26-readonly-01", "t26-readonly-02", "t26-candidate-inputs"],
                                      "files": [p.name for p in helpers],
                                      "scope": "whole closed raw window, all readonly snapshots, actual candidate inputs and outer helper source"})
    dump("source-index.json", refs)
    print(json.dumps({"status": "CLOSED_LOCAL_EVIDENCE_PUBLISHED", "video": review["video"],
                      "restoration": comparison["status"], "author_device_calls": 0}))

if __name__ == "__main__":
    main()
