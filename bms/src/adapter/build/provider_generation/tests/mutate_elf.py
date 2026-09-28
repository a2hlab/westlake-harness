#!/usr/bin/env python3
"""Flip one non-header byte in a copied ELF for the determinism negative."""

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("elf", type=Path)
    args = parser.parse_args()
    if args.elf.is_symlink() or not args.elf.is_file():
        raise ValueError("mutation target must be a regular non-symlink file")
    data = bytearray(args.elf.read_bytes())
    if len(data) < 4096 or data[:4] != b"\x7fELF":
        raise ValueError("mutation target is not a substantial ELF")
    offset = len(data) - 17
    data[offset] ^= 0x01
    args.elf.write_bytes(data)
    print(f"MUTATED {args.elf.name} offset={offset}")


if __name__ == "__main__":
    main()
