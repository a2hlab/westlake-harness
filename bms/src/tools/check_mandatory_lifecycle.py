#!/usr/bin/env python3
"""Validate a mandatory Bridge lifecycle state file.

This is a mechanical guard for execution order. It does not grant product PASS
or device verification; it only prevents later lifecycle stages from being
marked active/done before earlier stages are done.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ORDERED_STATUSES = {"pending", "active", "done", "blocked"}


def fail(message: str) -> None:
    raise SystemExit(f"FAIL mandatory lifecycle: {message}")


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")


def validate(data: dict, root: Path, require_complete: bool) -> None:
    if data.get("mandatory") is not True:
        fail("mandatory must be true")

    steps = data.get("steps")
    if not isinstance(steps, list) or len(steps) != 10:
        fail("steps must contain exactly 10 entries")

    expected = list(range(1, 11))
    actual = [step.get("step") for step in steps]
    if actual != expected:
        fail(f"step numbers must be exactly {expected}, got {actual}")

    active_steps = [step["step"] for step in steps if step.get("status") == "active"]
    if len(active_steps) > 1:
        fail(f"only one step may be active, got {active_steps}")

    allowed = set(data.get("allowed_statuses", [])) or ORDERED_STATUSES
    unknown = [
        (step["step"], step.get("status"))
        for step in steps
        if step.get("status") not in allowed or step.get("status") not in ORDERED_STATUSES
    ]
    if unknown:
        fail(f"unknown statuses: {unknown}")

    first_not_done = next((step["step"] for step in steps if step.get("status") != "done"), 11)
    for step in steps:
        status = step.get("status")
        number = step["step"]
        if number > first_not_done and status in {"active", "done"}:
            fail(f"step {number} is {status} before step {first_not_done} is done")
        if status == "done":
            artifacts = step.get("exit_artifacts", [])
            if not artifacts:
                fail(f"step {number} is done but has no exit_artifacts")
            missing = [artifact for artifact in artifacts if not (root / artifact).exists()]
            if missing:
                fail(f"step {number} missing exit_artifacts: {missing}")

    current_step = data.get("current_step")
    if active_steps and current_step != active_steps[0]:
        fail(f"current_step {current_step} does not match active step {active_steps[0]}")
    if not active_steps and first_not_done <= 10 and current_step != first_not_done:
        fail(f"current_step {current_step} should point to first unfinished step {first_not_done}")

    push_policy = data.get("push_policy", {})
    if push_policy.get("git_push_allowed_only_after_step") != 10:
        fail("git_push_allowed_only_after_step must be 10")
    if steps[-1].get("id") != "final_device_and_git_push":
        fail("step 10 must be final_device_and_git_push")

    if require_complete and first_not_done <= 10:
        fail(f"--require-complete set but step {first_not_done} is not done")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        nargs="?",
        default="docs/workflows/FN01_MULTI_APK_LIFECYCLE.json",
        help="mandatory lifecycle JSON path",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="repository root used to resolve exit_artifacts",
    )
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="fail unless all 10 steps are done; use before git push",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    path = (root / args.path).resolve() if not Path(args.path).is_absolute() else Path(args.path)
    validate(load(path), root, args.require_complete)
    print(f"PASS mandatory lifecycle: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
