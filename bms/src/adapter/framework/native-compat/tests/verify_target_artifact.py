#!/usr/bin/env python3
"""Fail-closed structural verifier for the audit-only target DSO."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys


EXPECTED_EXPORTS = {
    "WLNC_GetAbiVersion",
    "WLNC_ReasonString",
    "WLNC_AfterForkChildReset",
    "WLNC_ProcessInitPreverified",
    "WLNC_PrepareCurrentThread",
    "WLNC_AuthorizeLoad",
    "WLNC_Revoke",
    "WLNC_GetAuditSnapshot",
}


def under(path: pathlib.Path, root: pathlib.Path) -> pathlib.Path:
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise RuntimeError(f"path escapes project root: {resolved}") from error
    return resolved


def digest(path: pathlib.Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def tool(tool_path: pathlib.Path, *arguments: str) -> str:
    completed = subprocess.run(
        [str(tool_path), *arguments],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--library", required=True)
    parser.add_argument("--second-library", required=True)
    parser.add_argument("--readelf", required=True)
    parser.add_argument("--objdump", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    root = pathlib.Path(args.project_root).resolve(strict=True)
    library = under(pathlib.Path(args.library), root)
    second = under(pathlib.Path(args.second_library), root)
    readelf = under(pathlib.Path(args.readelf), root)
    objdump = under(pathlib.Path(args.objdump), root)
    report = pathlib.Path(args.report).resolve()
    try:
        report.relative_to(root)
    except ValueError as error:
        raise RuntimeError(f"report escapes project root: {report}") from error

    module = under(root / "adapter/framework/native-compat", root)
    product_sources = [
        under(module / "include/westlake_native_compat.h", root),
        under(module / "src/native_compat_internal.h", root),
        under(module / "src/process_state.c", root),
        under(module / "tests/abi_layout_asserts.c", root),
        under(module / "westlake_native_compat.map", root),
    ]
    source_text = "\n".join(path.read_text(encoding="utf-8")
                              for path in product_sources)
    forbidden_source = {
        "constructor_attribute": r"__attribute__\s*\(\(\s*constructor\b",
        "c_thread_local": r"\b_Thread_local\b",
        "gnu_thread_local": r"\b__thread\b",
        "cpp_thread_local": r"\bthread_local\b",
        "tpidr_el0": r"\btpidr_el0\b",
        "inline_asm": r"\b(__asm__|asm)\s*\(",
        "dynamic_loader": r"\b(dlopen|dlsym|dlvsym)\s*\(",
    }
    source_hits = {
        name: bool(re.search(pattern, source_text, flags=re.IGNORECASE))
        for name, pattern in forbidden_source.items()
    }
    require(not any(source_hits.values()),
            f"forbidden source primitive found: {source_hits}")

    first_sha = digest(library)
    second_sha = digest(second)
    require(first_sha == second_sha,
            "two target builds are not byte-identical")

    headers = tool(readelf, "-W", "-h", str(library))
    programs = tool(readelf, "-W", "-l", str(library))
    dynamic = tool(readelf, "-W", "-d", str(library))
    sections = tool(readelf, "-W", "-S", str(library))
    symbols = tool(readelf, "-W", "-s", str(library))
    relocations = tool(readelf, "-W", "-r", str(library))
    versions = tool(readelf, "-W", "--version-info", str(library))
    notes = tool(readelf, "-W", "-n", str(library))
    disassembly = tool(objdump, "-d", str(library))

    require("Machine:                           AArch64" in headers,
            "artifact is not AArch64")
    require("Type:                              DYN" in headers,
            "artifact is not a shared object")
    require(not re.search(r"^\s*TLS\s", programs, re.MULTILINE),
            "PT_TLS is forbidden")
    require(".tdata" not in sections and ".tbss" not in sections,
            "TLS section is forbidden")
    require(".init_array" not in sections and ".preinit_array" not in sections,
            "constructor array is forbidden")
    require(not re.search(r"\((INIT|INIT_ARRAY|PREINIT_ARRAY)\)", dynamic),
            "dynamic initializer is forbidden")
    require("(NEEDED)" not in dynamic, "unexpected runtime dependency")
    require("(RPATH)" not in dynamic and "(RUNPATH)" not in dynamic,
            "runtime search path is forbidden")
    require("(TEXTREL)" not in dynamic, "text relocation is forbidden")
    require("Library soname: [libwestlake_native_compat.so]" in dynamic,
            "wrong SONAME")
    require("WLNC_1.0" in versions, "missing WLNC_1.0 symbol version")
    require("Build ID:" in notes, "missing deterministic build ID")

    exports: set[str] = set()
    undefined: list[str] = []
    owner_rows: list[str] = []
    in_dynsym = False
    for line in symbols.splitlines():
        if line.startswith("Symbol table '.dynsym'"):
            in_dynsym = True
            continue
        if line.startswith("Symbol table '") and ".dynsym" not in line:
            in_dynsym = False
        if "g_wlnc_owner" in line:
            owner_rows.append(line)
        if not in_dynsym:
            continue
        match = re.search(r"\b(WLNC_[A-Za-z0-9_]+)(?:@@WLNC_1\.0)?$", line)
        if match and " GLOBAL " in line and " DEFAULT " in line:
            exports.add(match.group(1))
        if " UND " in line:
            fields = line.split()
            if fields and fields[-1] != "UND" and not fields[-1].isdigit():
                undefined.append(fields[-1])
    require(exports == EXPECTED_EXPORTS,
            f"export set mismatch: got={sorted(exports)}")
    require(not undefined, f"undefined dynamic symbols: {undefined}")
    require(len(owner_rows) == 1 and " OBJECT " in owner_rows[0]
            and " LOCAL " in owner_rows[0],
            f"single local owner not proven: {owner_rows}")
    require("WLNC_Test" not in symbols, "test hook leaked into target DSO")

    lowered = disassembly.lower()
    require("tpidr_el0" not in lowered, "TPIDR_EL0 access is forbidden")
    require(not re.search(r"\b(mrs|msr)\b", lowered),
            "system-register instruction is forbidden")
    require("__stack_chk_guard" not in symbols and
            "__stack_chk_fail" not in symbols,
            "pre-guard audit core must not consume stack-guard ABI")
    require(not re.search(r"(TLS|TLSDESC|TPREL|DTPREL)", relocations,
                          flags=re.IGNORECASE),
            "TLS relocation is forbidden")

    payload = {
        "status": "build_pass",
        "classification": "audit_only_control_plane",
        "device_verified": False,
        "load_authority": False,
        "real_guard_publisher": False,
        "real_signature_or_certificate_verifier": False,
        "target": "aarch64-linux-ohos",
        "sha256": first_sha,
        "deterministic_build_count": 2,
        "checks": {
            "all_inputs_project_local": True,
            "aarch64_elf_dso": True,
            "exact_versioned_c_exports": sorted(exports),
            "single_local_state_owner": True,
            "pt_tls_absent": True,
            "tls_sections_absent": True,
            "constructors_absent": True,
            "runtime_dependencies_absent": True,
            "rpath_runpath_textrel_absent": True,
            "tpidr_or_system_register_access_absent": True,
            "stack_guard_consumer_absent": True,
            "tls_relocations_absent": True,
            "source_forbidden_primitive_hits": source_hits,
        },
        "not_proven": [
            "target-device runtime behavior",
            "real Bionic stack-guard publication",
            "certificate authenticity or issuer trust",
            "Unity guest-load authorization",
            "production appspawn-x integration",
        ],
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print(f"PASS target verifier sha256={first_sha}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
