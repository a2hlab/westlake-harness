#!/usr/bin/env python3
"""Validate evidence bindings only; never substitutes for strict human review."""
import hashlib
import json
import os
from pathlib import Path
import sys


def require(value, message):
    if not value:
        raise ValueError(message)


def validate(stage, path):
    data = json.loads(path.read_text())
    require(data.get("stage") == stage, "stage mismatch")
    require(data.get("status") == "ready_for_human_review", "not ready for human review")
    require(data.get("human_review_required") is True, "human review must remain required")
    require(data.get("evidence"), "missing evidence")
    bound = set()
    for item in data["evidence"]:
        relative = Path(item["path"])
        require(not relative.is_absolute() and ".." not in relative.parts, "invalid relative evidence path")
        p = (path.parent / relative).resolve()
        require(p.is_relative_to(path.parent.resolve()), "evidence escapes receipt root")
        require(hashlib.sha256(p.read_bytes()).hexdigest() == item["sha256"], "evidence SHA mismatch")
        bound.add(item["path"])
    require(set(data.get("required_evidence", [])) <= bound, "unbound required evidence")
    require(data.get("required_evidence"), "no required evidence")
    if stage == "static":
        require(set(data["routes"]) == {"network", "decode", "video_surface", "audio", "lifecycle"}, "five routes required")
        for name, route in data["routes"].items():
            require(route["state"] in {"confirmed", "unknown", "external_blocked"}, "invalid route state")
            require(route.get("evidence_refs") and set(route["evidence_refs"]) <= bound, "unbound route evidence")
        require(data.get("predictions") and data.get("source_search"), "missing prediction or ordered source search")
        require(data.get("historical_is_current") is False, "historical evidence cannot prove current deployment")
    else:
        identity = data["identity"]
        for key in ("serial", "boot_id", "apk_sha256", "runtime_manifest_sha256"):
            require(identity.get(key) not in (None, "", "unknown"), "missing current identity: " + key)
        if stage == "build":
            require(data["selected_change"]["first_blocker_state"] == "confirmed", "unconfirmed blocker")
            require(data["selected_change"].get("allowed_sources"), "unbound source list")
            for key in ("build_stdout", "build_stderr", "source_diff", "toolchain_manifest", "rollback_plan", "api_test_results"):
                require(data[key] in bound, "unbound build member: " + key)
            require(data.get("build_rc") == 0, "failed build")
            require(data.get("frozen_check_rc") == 0, "frozen check failed")
        elif stage == "playback":
            require(data.get("window_seconds", 0) >= 120 and data["window_seconds"] <= 1800, "invalid experiment window")
            require(len(data["cycles"]) >= 2, "two cycles required")
            for cycle in data["cycles"]:
                require(cycle["play_seconds"] >= 20 and cycle["pause_seconds"] >= 3 and cycle["resume_seconds"] >= 10, "short observation")
                require(len(cycle["ordered_frames"]) >= 7 and len(set(cycle["ordered_frames"])) == len(cycle["ordered_frames"]), "missing frame sequence")
                require(set(cycle["ordered_frames"]) <= bound, "unbound frames")
                require(cycle["audio_review"] in bound and cycle["content_roi_review"] in bound, "missing audio or content review")
            for key in ("facts", "api_delta", "icon_reentry_evidence", "rollback_receipt"):
                require(data[key] in bound, "missing publication evidence: " + key)
        else:
            raise ValueError("unknown stage")
    return data


if __name__ == "__main__":
    try:
        stage = sys.argv[1]
        raw = os.environ.get("TTVIDEO_RECEIPT_" + stage.upper())
        require(raw, "missing TTVIDEO_RECEIPT_" + stage.upper() + "; evidence is pending, not passed")
        validate(stage, Path(raw))
        print("receipt bindings valid; human acceptance remains pending")
    except (ValueError, KeyError, OSError, IndexError, TypeError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
