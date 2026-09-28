#!/usr/bin/env python3
"""Fail-closed validator for one Fn04 route-labelled runtime receipt.

This validator checks correlation and evidence shape only.  A valid receipt is
not a device PASS; an independent verifier still owns the Action verdict.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


ROUTE_RE = re.compile(r"^R[1-9][0-9]*[a-z]?$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
VERDICTS = {"PASS", "FAIL", "BLOCK", "SPEC_GAP"}
CONTENT_ORIGINS = {"APP_CONTENT", "STARTING_WINDOW", "PLACEHOLDER", "UNKNOWN"}
PRESENT_OUTCOMES = {"PRESENTED", "DROPPED", "FAILED", "NOT_REACHED"}
LIFECYCLE_ORDER = (
    "ADD_ACCEPTED",
    "RELAYOUT_READY",
    "SURFACE_READY",
    "REMOVE_REQUESTED",
    "CHILD_DESTROYED",
)


class ReceiptError(ValueError):
    """Receipt violates the frozen correlation contract."""


def require_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReceiptError(f"{field} must be an object")
    return value


def require_nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReceiptError(f"{field} must be a non-empty string")
    return value


def require_positive_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ReceiptError(f"{field} must be a positive integer")
    return value


def validate_receipt(data: dict[str, Any]) -> None:
    if data.get("schema_version") != "1.0":
        raise ReceiptError("schema_version must be 1.0")
    if data.get("concept_id") != "Fn04":
        raise ReceiptError("concept_id must be Fn04")

    route = require_nonempty(data.get("route"), "route")
    if not ROUTE_RE.fullmatch(route):
        raise ReceiptError("route must be a numeric family with optional lower-case variant")
    verdict = data.get("verdict")
    if verdict not in VERDICTS:
        raise ReceiptError(f"verdict must be one of {sorted(VERDICTS)}")

    generation = require_nonempty(data.get("generation_id"), "generation_id")
    build_sha = require_nonempty(data.get("build_manifest_sha256"), "build_manifest_sha256")
    if not HEX64_RE.fullmatch(build_sha):
        raise ReceiptError("build_manifest_sha256 must be 64 lower-case hex characters")

    window = require_mapping(data.get("window"), "window")
    require_nonempty(window.get("android_token"), "window.android_token")
    parent_id = require_positive_int(window.get("oh_parent_id"), "window.oh_parent_id")
    child_id = require_positive_int(window.get("oh_child_id"), "window.oh_child_id")
    if route == "R1b" and parent_id == child_id:
        raise ReceiptError("R1b parent and specific child identities must differ")
    if window.get("generation_id") != generation:
        raise ReceiptError("window generation does not match receipt generation")

    surface = require_mapping(data.get("surface"), "surface")
    require_positive_int(surface.get("unique_id"), "surface.unique_id")
    if surface.get("generation_id") != generation:
        raise ReceiptError("surface generation does not match receipt generation")

    lifecycle_events = data.get("lifecycle_events")
    if not isinstance(lifecycle_events, list):
        raise ReceiptError("lifecycle_events must be an array")
    lifecycle_names: list[str] = []
    last_seq = 0
    for index, raw_event in enumerate(lifecycle_events):
        event = require_mapping(raw_event, f"lifecycle_events[{index}]")
        seq = require_positive_int(event.get("seq"), f"lifecycle_events[{index}].seq")
        if seq <= last_seq:
            raise ReceiptError("lifecycle event seq must be strictly increasing")
        last_seq = seq
        name = require_nonempty(event.get("event"), f"lifecycle_events[{index}].event")
        if name not in LIFECYCLE_ORDER:
            raise ReceiptError(f"lifecycle_events[{index}].event is invalid")
        if event.get("generation_id") != generation:
            raise ReceiptError(f"lifecycle_events[{index}] generation mismatch")
        lifecycle_names.append(name)
    expected_prefix = list(LIFECYCLE_ORDER[: len(lifecycle_names)])
    if lifecycle_names != expected_prefix:
        raise ReceiptError("lifecycle events must follow add/relayout/surface/remove/destroy order")

    frames = data.get("frames")
    if not isinstance(frames, list):
        raise ReceiptError("frames must be an array")
    seen: set[int] = set()
    for index, raw_frame in enumerate(frames):
        frame = require_mapping(raw_frame, f"frames[{index}]")
        frame_id = require_positive_int(frame.get("frame_id"), f"frames[{index}].frame_id")
        if frame_id in seen:
            raise ReceiptError(f"duplicate frame_id: {frame_id}")
        seen.add(frame_id)
        if frame.get("generation_id") != generation:
            raise ReceiptError(f"frames[{index}] generation mismatch")
        if not isinstance(frame.get("buffer_queued"), bool):
            raise ReceiptError(f"frames[{index}].buffer_queued must be boolean")
        if not isinstance(frame.get("transaction_committed"), bool):
            raise ReceiptError(f"frames[{index}].transaction_committed must be boolean")
        if frame.get("present_outcome") not in PRESENT_OUTCOMES:
            raise ReceiptError(f"frames[{index}].present_outcome is invalid")
        if frame.get("content_origin") not in CONTENT_ORIGINS:
            raise ReceiptError(f"frames[{index}].content_origin is invalid")
        if frame.get("present_outcome") == "PRESENTED":
            if not frame["buffer_queued"] or not frame["transaction_committed"]:
                raise ReceiptError(
                    f"frames[{index}] PRESENTED requires queued buffer and committed transaction"
                )

    blocked_by = data.get("blocked_by", [])
    if not isinstance(blocked_by, list):
        raise ReceiptError("blocked_by must be an array")
    if verdict == "BLOCK" and not blocked_by:
        raise ReceiptError("BLOCK requires at least one explicit physical external gate")
    if verdict != "BLOCK" and blocked_by:
        raise ReceiptError("blocked_by is only valid for BLOCK")

    if verdict == "PASS":
        if lifecycle_names != list(LIFECYCLE_ORDER):
            raise ReceiptError("PASS requires complete add-to-destroy lifecycle")
        presented_app_frames = [
            frame
            for frame in frames
            if frame["present_outcome"] == "PRESENTED"
            and frame["content_origin"] == "APP_CONTENT"
        ]
        if not presented_app_frames:
            raise ReceiptError("PASS requires an APP_CONTENT PRESENTED frame")
        for case_group in ("positive_cases", "negative_cases", "failure_cases"):
            cases = data.get(case_group)
            if not isinstance(cases, list) or not cases:
                raise ReceiptError(f"PASS requires non-empty {case_group}")
            if any(case.get("result") != "PASS" for case in cases if isinstance(case, dict)):
                raise ReceiptError(f"all {case_group} must pass")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    data = json.loads(args.receipt.read_text(encoding="utf-8"))
    validate_receipt(require_mapping(data, "root"))
    print(f"VALID: {args.receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
