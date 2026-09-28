#!/usr/bin/env python3
"""Audit exact v11 consumers and interposition hazards of ART runtime stubs."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


def run(tool: Path, *args: str) -> str:
    result = subprocess.run(
        [str(tool), *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return result.stdout


def symbols(readelf: Path, elf: Path) -> tuple[set[str], set[str]]:
    defined: set[str] = set()
    undefined: set[str] = set()
    for line in run(readelf, "--dyn-syms", "--wide", str(elf)).splitlines():
        fields = line.split()
        if len(fields) < 8 or not fields[0].endswith(":"):
            continue
        name = fields[7].split("@", 1)[0]
        if not name:
            continue
        if fields[6] == "UND":
            undefined.add(name)
        elif fields[4] in {"GLOBAL", "WEAK"}:
            defined.add(name)
    return defined, undefined


def needed(readelf: Path, elf: Path) -> list[str]:
    dynamic = run(readelf, "--dynamic-table", str(elf))
    return re.findall(r"Shared library: \[([^]]+)\]", dynamic)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readelf", required=True, type=Path)
    parser.add_argument("--providers", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    stub = args.providers / "libart_runtime_stubs.so"
    stub_defined, _ = symbols(args.readelf, stub)
    consumers: dict[str, object] = {}
    for elf in sorted(args.providers.glob("*.so")):
        if elf == stub:
            continue
        _, undefined = symbols(args.readelf, elf)
        intersection = sorted(stub_defined & undefined)
        direct_edge = "libart_runtime_stubs.so" in needed(args.readelf, elf)
        if direct_edge or intersection:
            consumers[elf.name] = {
                "direct_needed": direct_edge,
                "undefined_symbols_also_defined_by_stub_dso": intersection,
            }

    dynamic = run(args.readelf, "--dynamic-table", str(stub))
    interposition = sorted(stub_defined & {
        "abort", "raise", "sigaction", "signal", "pthread_create",
        "android_reset_stack_guards",
    })
    result = {
        "schema": "westlake.art-runtime-stub-consumer-audit.v1",
        "status": "PRODUCT_REJECTED",
        "stub_defined_symbol_count": len(stub_defined),
        "direct_consumers": sorted(
            name for name, record in consumers.items() if record["direct_needed"]
        ),
        "consumers": consumers,
        "has_init_or_init_array": "(INIT)" in dynamic or "(INIT_ARRAY)" in dynamic,
        "global_interposition_definitions": interposition,
        "first_frame_non_use": "NOT_PROVEN",
        "product_activation": False,
        "reason": (
            "A directly loaded stub DSO has constructor/interposition behavior and a broad "
            "stub ABI. It must be removed from the product closure or replaced with exact "
            "real typed owners; direct-reference absence is not first-frame non-use proof."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "PASS stub_audit "
        f"defined={len(stub_defined)} direct_consumers={len(result['direct_consumers'])} "
        f"constructor={str(result['has_init_or_init_array']).lower()} "
        f"interposition={len(interposition)} product_activation=false"
    )


if __name__ == "__main__":
    main()
