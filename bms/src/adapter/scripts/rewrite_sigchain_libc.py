#!/usr/bin/env python3
"""Rewrite the one AOSP host-musl sigchain loader literal, then fail closed."""

from __future__ import annotations

import argparse
from pathlib import Path


OLD = '"libc_musl.so"'
NEW = '"libc.so"'


def verify_closed(text: str) -> None:
    if text.count(OLD) != 0 or text.count(NEW) < 1:
        raise SystemExit(
            f"sigchain libc oracle failed: libc_musl.so={text.count(OLD)} libc.so={text.count(NEW)}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-closed", action="store_true")
    args = parser.parse_args()
    text = args.source.read_text(encoding="utf-8")
    if args.verify_closed:
        if args.output is not None:
            raise SystemExit("--verify-closed does not accept --output")
        verify_closed(text)
        return
    if args.output is None:
        raise SystemExit("rewrite requires --output")
    if text.count(OLD) not in (0, 1):
        raise SystemExit(
            f"sigchain source oracle failed: libc_musl.so={text.count(OLD)} libc.so={text.count(NEW)}"
        )
    rewritten = text.replace(OLD, NEW)
    verify_closed(rewritten)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(rewritten, encoding="utf-8")
    temporary.replace(args.output)


if __name__ == "__main__":
    main()
