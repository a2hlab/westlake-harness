#!/usr/bin/env python3
"""Bind reviewed source to actual archived build bytes; no build or device call."""
from pathlib import Path
import hashlib
import json
import os

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    receipt = json.loads((HERE / "candidate.json").read_text())
    for name, digest in receipt["sources"].items():
        assert sha(HERE / name) == digest, name
    base = Path(os.environ.get("TTVIDEO_R8_ARCHIVE_ROOT", Path.home() / ".local/share/westlake/toutiao-resume-20261019"))
    build = base / "r8-build-outer-2329/build"
    raw = json.loads((build / "build-receipt.json").read_text())
    for row in raw["files"]:
        p = build / row["path"]
        assert p.stat().st_size == row["size"] and sha(p) == row["sha256"], row["path"]
    assert sha(build / "recipe.sh") == receipt["sources"]["build_candidate.sh"]
    assert sha(build / "src/ttplayer_log_mirror.c") == receipt["sources"]["ttplayer_log_mirror.c"]
    rc = {p.stem: int(p.read_text()) for p in (build / "raw").glob("*.rc")}
    assert len(rc) == 15 and all(value == 0 for value in rc.values())
    assert sha(build / "artifacts/libopensles_android_compat.so") == receipt["artifacts"]["libopensles_android_compat.so"]
    assert sha(base / "r8-derive-outer-2328/libttmplayer.so") == receipt["artifacts"]["libttmplayer.so"]
    unchanged = HERE.parent / "candidate-r3/deploy-inputs"
    assert sha(unchanged / "run.sh") == "79275cf9f9a72be72beb551b978ee5f2faaed84129980aa5c79d2f51acd040d5"
    assert sha(unchanged / "libmffmpeg.so") == "d2882303bf5dc34e297a404e4b57a214d9c30ddaf0f496eb2ef9f7dcac09c4b4"
    published = json.loads((HERE / "evidence/manifest.json").read_text())
    for row in published["files"]:
        assert sha(HERE / "evidence" / row["published_path"]) == row["published_sha256"]
    review = json.loads((HERE.parents[1] / "2026-10-19-toutiao-rea-methods/video-1919-r8-elf-review/final-review.json").read_text())
    assert review["verdict"] == "ACCEPT_OFFLINE_CANDIDATE_NOT_RUNTIME_ADMISSION"
    assert review["derive_sha256"] == receipt["sources"]["derive_ttmplayer_logmirror.py"]
    assert review["executed_recipe_sha256"] == receipt["sources"]["build_candidate.sh"]
    assert not review["blockers"]
    assert receipt["runtime_provider"] == "unknown" and receipt["playback"] != "passed"
    print(json.dumps({"scope": "OFFLINE_EVIDENCE_ONLY", "raw_files_checked": len(raw["files"]),
                      "successful_build_stages": len(rc), "published_records_checked": len(published["files"]),
                      "runtime_provider": "unknown", "playback": "not_passed"}))


if __name__ == "__main__":
    main()
