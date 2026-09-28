#!/usr/bin/env python3
"""Deterministic gate for WestLake/AonB handoff and review Markdown."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


TEMPLATE = """# WestLake Task Handoff

## Boundary
- Boundary:
- Android behavior:
- OpenHarmony mapping:
- Fix layer:

## Evidence target
- What this proves:
- What this does not prove:

## Environment
- Host:
- Device:
- Tool path:
- Artifact path:
- App:

## Status
- Label: build_pass | stub | real_impl | device_verified
- Why:

## Proven
-

## Not proven
-

## Failed
-

## Next evidence
- Command:
- Expected output:
- If it fails:

## Shim/stub/bypass inventory
- Item:
- Owner:
- Why it exists:
- Removal condition:
- Test coverage:
- App-specific or common:

## Memory/skill/CI/review updates
- Memory:
- Skill:
- CI:
- Review checklist:
"""


REQUIRED_SECTIONS = [
    "Boundary",
    "Evidence target",
    "Environment",
    "Status",
    "Proven",
    "Not proven",
    "Failed",
    "Next evidence",
    "Shim/stub/bypass inventory",
    "Memory/skill/CI/review updates",
]

REQUIRED_LABELS = [
    "Boundary",
    "Android behavior",
    "OpenHarmony mapping",
    "Fix layer",
    "What this proves",
    "What this does not prove",
    "Host",
    "Device",
    "Tool path",
    "Artifact path",
    "App",
    "Label",
    "Why",
    "Command",
    "Expected output",
    "If it fails",
    "Item",
    "Owner",
    "Removal condition",
    "Test coverage",
    "Memory",
    "Skill",
    "CI",
    "Review checklist",
]

STATUS_WORDS = {"build_pass", "stub", "real_impl", "device_verified"}
BOUNDARY_WORDS = {
    "ART",
    "JNI",
    "Binder",
    "Surface",
    "Rendering",
    "Input",
    "Permission",
    "Security",
    "Package",
    "Resource",
    "appspawn",
    "Bionic",
    "Musl",
    "Device",
    "Tooling",
}


def section_present(text: str, section: str) -> bool:
    pattern = rf"(?mi)^##+\s+{re.escape(section)}\b"
    return bool(re.search(pattern, text))


def nonempty_after_label(text: str, label: str) -> bool:
    pattern = rf"(?mi)^[ \t]*-[ \t]*{re.escape(label)}[ \t]*:[ \t]*(\S.*)$"
    return bool(re.search(pattern, text))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?")
    parser.add_argument("--template", action="store_true")
    args = parser.parse_args()

    if args.template:
        print(TEMPLATE)
        return 0
    if not args.path:
        parser.error("path is required unless --template is used")

    path = Path(args.path)
    text = path.read_text(encoding="utf-8", errors="ignore")
    failures: list[str] = []
    warnings: list[str] = []

    for section in REQUIRED_SECTIONS:
        if not section_present(text, section):
            failures.append(f"missing required section: {section}")

    for label in REQUIRED_LABELS:
        if not nonempty_after_label(text, label):
            failures.append(f"missing or empty required label: {label}")

    if not (STATUS_WORDS & set(re.findall(r"\b[a-z_]+\b", text))):
        failures.append("missing explicit status label: build_pass/stub/real_impl/device_verified")

    if not any(word.lower() in text.lower() for word in BOUNDARY_WORDS):
        failures.append("missing recognizable WestLake boundary word")

    risky = [
        (r"\b(progress|done|completed|works|基本完成|差不多|应该可以)\b", "ambiguous progress wording"),
        (r"\b(always granted|return true|return false|bypass permission|silent stub)\b", "possible silent bypass/stub"),
        (r"\bhost pass\b|\bQEMU pass\b", "host/QEMU pass must not imply device_verified"),
    ]
    for regex, message in risky:
        if re.search(regex, text, re.IGNORECASE):
            warnings.append(message)

    print(f"westlake_gate: {path}")
    if failures:
        print("FAIL")
        for item in failures:
            print(f"- {item}")
    else:
        print("PASS")
    if warnings:
        print("WARN")
        for item in warnings:
            print(f"- {item}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
