#!/usr/bin/env python3
"""Emit only the reviewed C/D v11 IPC/operator hunks used by L02.A01.

The historical base_bundle_installer hunk predates the rev-5 typed-plan and
journal contract. The enum hunk targets an API-24 oracle rather than the exact
OH 6.1.0.31 source. Both are therefore rejected here and supplied by separate
rev-5 patches. No source outside the canonical adapter is read.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


EXCLUDED_TARGETS = {
    "foundation/bundlemanager/bundle_framework/services/bundlemgr/"
    "include/bundle_framework_services_ipc_interface_code.h",
    "foundation/bundlemanager/bundle_framework/services/bundlemgr/"
    "src/base_bundle_installer.cpp",
}


def target_for_section(lines: list[str]) -> str:
    for line in lines:
        if line.startswith("+++ v11/"):
            return line.split("\t", 1)[0][len("+++ v11/") :]
    raise ValueError("diff section has no v11 target")


def split_sections(text: str) -> list[list[str]]:
    sections: list[list[str]] = []
    current: list[str] = []
    for line in text.splitlines(keepends=True):
        if line.startswith("diff -ruN "):
            if current:
                sections.append(current)
            current = [line]
        else:
            if not current:
                raise ValueError("content before first diff section")
            current.append(line)
    if current:
        sections.append(current)
    return sections


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("patch", type=Path)
    args = parser.parse_args()

    sections = split_sections(args.patch.read_text(encoding="utf-8"))
    included = []
    excluded = []
    for section in sections:
        target = target_for_section(section)
        if target in EXCLUDED_TARGETS:
            excluded.append(target)
        else:
            included.append(section)

    if set(excluded) != EXCLUDED_TARGETS:
        raise ValueError(f"excluded target mismatch: {excluded!r}")
    if len(included) != 14:
        raise ValueError(f"expected 14 reviewed sections, got {len(included)}")

    for section in included:
        sys.stdout.writelines(section)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
