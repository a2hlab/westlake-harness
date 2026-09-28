#!/usr/bin/env python3
"""Replace one exact NUL-terminated ELF string without changing file size."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("elf", type=Path)
    parser.add_argument("old")
    parser.add_argument("new")
    args = parser.parse_args()

    if len(args.old) != len(args.new) or args.old == args.new:
        raise SystemExit("old/new must be distinct and have equal byte length")
    old = args.old.encode("ascii") + b"\0"
    new = args.new.encode("ascii") + b"\0"
    data = args.elf.read_bytes()
    count = data.count(old)
    if count < 1:
        raise SystemExit(f"symbol string not found: {args.old}")
    args.elf.write_bytes(data.replace(old, new))
    print(f"mutated={args.elf.name} occurrences={count}")


if __name__ == "__main__":
    main()
