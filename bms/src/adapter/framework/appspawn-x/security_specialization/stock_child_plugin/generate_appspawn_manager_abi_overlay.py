#!/usr/bin/env python3
"""Generate a current-semantics header with only TagAppSpawnMgr rebound."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


CURRENT_HEADER_SHA256 = (
    "5455b2c27d2a0c63733b10fddf13e3cb7b724da766f498a5c737418f3127c7de"
)
TARGET_HEADER_SHA256 = (
    "b3619c81b3e91af8c079eb17a922ef8a573938259745e54726122ffa174143b6"
)
MANAGER_PATTERN = re.compile(
    r"typedef struct TagAppSpawnMgr \{.*?\n\} AppSpawnMgr;", re.DOTALL
)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def manager_block(text: str, label: str) -> str:
    matches = MANAGER_PATTERN.findall(text)
    require(len(matches) == 1, f"{label} manager declaration count: {len(matches)}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--current", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    require(digest(args.current) == CURRENT_HEADER_SHA256,
            "current security-v7 manager header identity drift")
    require(digest(args.target) == TARGET_HEADER_SHA256,
            "target OH 6.1.0.31 manager header identity drift")
    current_text = args.current.read_text()
    target_text = args.target.read_text()
    current_manager = manager_block(current_text, "current")
    target_manager = manager_block(target_text, "target")
    require("checkPointIdQueue" in current_manager and
            "spawningFdsQueue" in current_manager,
            "current checkpoint manager fields are not the expected cohort")
    require("checkPointIdQueue" not in target_manager and
            "spawningFdsQueue" not in target_manager,
            "target manager declaration unexpectedly carries newer queues")

    overlay_text = current_text.replace(current_manager, target_manager)
    require(overlay_text.count(target_manager) == 1,
            "manager-only replacement did not produce one target declaration")
    require(overlay_text.replace(target_manager, current_manager) == current_text,
            "overlay changed content outside TagAppSpawnMgr")
    require("uint64_t checkPointId;" in overlay_text,
            "current AppSpawningCtx checkpoint declaration was lost")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(overlay_text)
    report = {
        "schema": "westlake.appspawn-manager-abi-overlay.v1",
        "status": "PASS",
        "candidate": "P0-A06-ABI-D8-001",
        "variable": (
            "APPSPAWN_X_HOST_SOURCE_ABI_COHORT=exact_OpenHarmony-6.1.0.31"
        ),
        "current_header_sha256": CURRENT_HEADER_SHA256,
        "target_header_sha256": TARGET_HEADER_SHA256,
        "overlay_header_sha256": digest(args.output),
        "replacement_scope": "TagAppSpawnMgr_declaration_only",
        "current_non_manager_declarations_preserved": True,
        "current_app_spawning_ctx_checkpoint_preserved": True,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
