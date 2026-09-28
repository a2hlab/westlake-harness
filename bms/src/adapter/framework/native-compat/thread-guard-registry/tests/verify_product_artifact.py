#!/usr/bin/env python3
"""Fail-closed binary gate for the product thread-guard registry DSO."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


EXPECTED_EXPORTS = {
    "WLTG_GetAbiVersion",
    "WLTG_ReasonString",
    "WLTG_AfterForkChildReset",
    "WLTG_ProcessArm",
    "WLTG_IssueThreadTicket",
    "WLTG_CancelThreadTicket",
    "WLTG_PrepareCurrentThread",
    "WLTG_VerifyCurrentThreadReady",
    "WLTG_RetireCurrentThread",
    "WLTG_Revoke",
    "WLTG_GetProcessSnapshot",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def run(tool: Path, *arguments: str) -> str:
    return subprocess.run(
        [str(tool), *arguments],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout


def dynamic_symbols(symbols: str) -> tuple[set[str], list[str]]:
    exports: set[str] = set()
    undefined: list[str] = []
    in_dynamic = False
    for line in symbols.splitlines():
        if line.startswith("Symbol table '.dynsym'"):
            in_dynamic = True
            continue
        if line.startswith("Symbol table '") and ".dynsym" not in line:
            in_dynamic = False
        if not in_dynamic:
            continue
        fields = line.split()
        if len(fields) < 8:
            continue
        symbol = fields[-1].split("@", 1)[0]
        if " UND " in f" {line} ":
            undefined.append(symbol)
        elif " GLOBAL " in line and " DEFAULT " in line and symbol.startswith("WLTG_"):
            exports.add(symbol)
    return exports, undefined


def inspect(path: Path, readelf: Path, objdump: Path) -> dict[str, str]:
    return {
        "header": run(readelf, "-W", "-h", str(path)),
        "programs": run(readelf, "-W", "-l", str(path)),
        "dynamic": run(readelf, "-W", "-d", str(path)),
        "sections": run(readelf, "-W", "-S", str(path)),
        "symbols": run(readelf, "-W", "-s", str(path)),
        "relocations": run(readelf, "-W", "-r", str(path)),
        "versions": run(readelf, "-W", "--version-info", str(path)),
        "notes": run(readelf, "-W", "-n", str(path)),
        "disassembly": run(objdump, "-d", str(path)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--library", required=True)
    parser.add_argument("--second-library", required=True)
    parser.add_argument("--readelf", required=True)
    parser.add_argument("--objdump", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    library = Path(args.library).resolve(strict=True)
    second = Path(args.second_library).resolve(strict=True)
    # LLVM's readelf frontend may be a multicall symlink to llvm-readobj.  Keep
    # the invoked basename so argv[0] selects readelf-compatible output.
    readelf = Path(args.readelf).absolute()
    objdump = Path(args.objdump).absolute()
    require(readelf.is_file(), f"readelf tool missing: {readelf}")
    require(objdump.is_file(), f"objdump tool missing: {objdump}")
    report = Path(args.report).absolute()

    first_sha = digest(library)
    require(first_sha == digest(second), "independent registry links are not byte-identical")
    view = inspect(library, readelf, objdump)
    exports, undefined = dynamic_symbols(view["symbols"])

    header_fields = {
        key.strip(): value.strip()
        for line in view["header"].splitlines()
        if ":" in line
        for key, value in (line.split(":", 1),)
    }
    require(header_fields.get("Machine") == "AArch64", "not AArch64")
    require(header_fields.get("Type", "").startswith("DYN "), "not a shared object")
    require("Library soname: [libwestlake_thread_guard_registry.so]" in view["dynamic"],
            "SONAME mismatch")
    require("(NEEDED)" not in view["dynamic"], "registry has a runtime dependency")
    require("(RPATH)" not in view["dynamic"] and "(RUNPATH)" not in view["dynamic"],
            "registry has an ambient search path")
    require("(TEXTREL)" not in view["dynamic"], "registry has text relocations")
    require(re.search(r"^\s*TLS\s", view["programs"], re.MULTILINE) is None,
            "registry owns a forbidden PT_TLS segment")
    require(re.search(r"\.(?:tdata|tbss|preinit_array|init_array)\b", view["sections"]) is None,
            "registry has TLS or constructor sections")
    require(exports == EXPECTED_EXPORTS, f"export set mismatch: {sorted(exports)}")
    require(not undefined, f"undefined dynamic symbols: {undefined}")
    require("WLTG_1.0" in view["versions"], "versioned export contract missing")
    build_ids = re.findall(r"Build ID:\s*([0-9a-fA-F]+)", view["notes"])
    require(len(build_ids) == 1 and re.fullmatch(r"[0-9a-fA-F]{40}", build_ids[0]) is not None,
            f"expected one SHA-1 Build-ID, got {build_ids}")

    forbidden = (
        r"\b(?:pthread_create|pthread_exit|dlopen|dlsym|dlvsym|sigaction|signal|"
        r"__stack_chk_guard|westlake_bionic_tls_slots_2_7_reservation)\b"
    )
    require(re.search(forbidden, view["symbols"]) is None, "forbidden owner/interposer symbol")
    require("tpidr_el0" not in view["disassembly"].lower(), "registry reads the thread pointer")
    require(re.search(r"TLS|TLSDESC|TPREL|DTPREL", view["relocations"], re.IGNORECASE) is None,
            "registry contains a TLS relocation")

    payload = {
        "build_id": build_ids[0].lower(),
        "checks": {
            "aarch64_dso": True,
            "deterministic_links": 2,
            "exact_versioned_exports": sorted(EXPECTED_EXPORTS),
            "no_constructors_or_tls": True,
            "no_runtime_dependencies": True,
            "no_thread_pointer_access": True,
            "no_undefined_symbols": True,
        },
        "sha256": first_sha,
        "status": "build_pass",
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PRODUCT_REGISTRY_PASS sha256={first_sha} build_id={build_ids[0].lower()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f"PRODUCT_REGISTRY_FAIL: {error}")
        raise SystemExit(1)
