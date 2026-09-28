#!/usr/bin/env python3
"""Fail-closed ELF/instruction gate for the disabled PR-08A fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass


EXPECTED_BACKEND_EXPORTS = {
    "WLAF_PublishFixtureAperture",
    "WLAF_ReasonString",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


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


@dataclass(frozen=True)
class ElfView:
    headers: str
    programs: str
    dynamic: str
    sections: str
    symbols: str
    relocations: str
    notes: str
    disassembly: str


def inspect(path: pathlib.Path, readelf: pathlib.Path,
            objdump: pathlib.Path) -> ElfView:
    return ElfView(
        headers=tool(readelf, "-W", "-h", str(path)),
        programs=tool(readelf, "-W", "-l", str(path)),
        dynamic=tool(readelf, "-W", "-d", str(path)),
        sections=tool(readelf, "-W", "-S", str(path)),
        symbols=tool(readelf, "-W", "-s", str(path)),
        relocations=tool(readelf, "-W", "-r", str(path)),
        notes=tool(readelf, "-W", "-n", str(path)),
        disassembly=tool(objdump, "-d", str(path)),
    )


def function_body(disassembly: str, symbol: str) -> str:
    lines = disassembly.splitlines()
    marker = re.compile(rf"^[0-9a-f]+ <{re.escape(symbol)}>:$")
    start = None
    for index, line in enumerate(lines):
        if marker.match(line.strip()):
            start = index + 1
            break
    if start is None:
        return ""
    body: list[str] = []
    next_symbol = re.compile(r"^[0-9a-f]+ <[^>]+>:$")
    for line in lines[start:]:
        if next_symbol.match(line.strip()):
            break
        if line.strip():
            body.append(line)
    return "\n".join(body)


def dynamic_exports(symbols: str, prefix: str) -> set[str]:
    exports: set[str] = set()
    in_dynsym = False
    for line in symbols.splitlines():
        if line.startswith("Symbol table '.dynsym'"):
            in_dynsym = True
            continue
        if line.startswith("Symbol table '") and ".dynsym" not in line:
            in_dynsym = False
        if not in_dynsym or " GLOBAL " not in line or " DEFAULT " not in line:
            continue
        match = re.search(rf"\b({re.escape(prefix)}[A-Za-z0-9_]+)(?:@@[^ ]+)?$", line)
        if match:
            exports.add(match.group(1))
    return exports


def backend_errors(view: ElfView) -> list[str]:
    errors: list[str] = []
    if "Machine:                           AArch64" not in view.headers:
        errors.append("BACKEND_NOT_AARCH64")
    if "Type:                              DYN" not in view.headers:
        errors.append("BACKEND_NOT_DSO")
    if re.search(r"^\s*TLS\s", view.programs, re.MULTILINE):
        errors.append("BACKEND_PT_TLS_FORBIDDEN")
    if re.search(r"\.tdata|\.tbss", view.sections):
        errors.append("BACKEND_TLS_SECTION_FORBIDDEN")
    if re.search(r"\.preinit_array|\.init_array", view.sections) or re.search(
        r"\((?:PREINIT_ARRAY|INIT_ARRAY|INIT)\)", view.dynamic
    ):
        errors.append("BACKEND_CONSTRUCTOR_FORBIDDEN")
    if "(NEEDED)" in view.dynamic:
        errors.append("BACKEND_RUNTIME_DEPENDENCY_FORBIDDEN")
    if "(RPATH)" in view.dynamic or "(RUNPATH)" in view.dynamic:
        errors.append("BACKEND_SEARCH_PATH_FORBIDDEN")
    if "(TEXTREL)" in view.dynamic:
        errors.append("BACKEND_TEXTREL_FORBIDDEN")
    if "Library soname: [libwestlake_aperture_fixture_backend.so]" not in view.dynamic:
        errors.append("BACKEND_SONAME_MISMATCH")
    if "Build ID:" not in view.notes:
        errors.append("BACKEND_BUILD_ID_MISSING")
    if "tpidr_el0" in view.disassembly.lower() or re.search(
        r"\b(?:mrs|msr)\b", view.disassembly.lower()
    ):
        errors.append("BACKEND_TP_ACCESS_FORBIDDEN")
    if re.search(r"TLS|TLSDESC|TPREL|DTPREL", view.relocations,
                 flags=re.IGNORECASE):
        errors.append("BACKEND_TLS_RELOCATION_FORBIDDEN")
    if "__stack_chk_guard" in view.symbols:
        errors.append("MUSL_GLOBAL_STACK_GUARD_REFERENCE_FORBIDDEN")
    if "westlake_bionic_tls_slots_2_7_reservation" in view.symbols:
        errors.append("BACKEND_RESERVATION_SYMBOL_REFERENCE_FORBIDDEN")
    if dynamic_exports(view.symbols, "WLAF_") != EXPECTED_BACKEND_EXPORTS:
        errors.append("BACKEND_EXPORT_SET_MISMATCH")

    store = function_body(view.disassembly, "WLAF_StoreAndReadback")
    if not store:
        errors.append("UNIQUE_STORE_FUNCTION_MISSING")
    else:
        instructions = [
            line for line in store.splitlines()
            if re.search(r"\b(?:str|stur|stp|stxr|stlr)\b", line.lower())
        ]
        if len(instructions) != 1 or not re.search(
            r"\bstr\s+x1,\s*\[x0\]", instructions[0].lower()
        ):
            errors.append("UNIQUE_STORE_INSTRUCTION_MISMATCH")
        if not re.search(r"\bldr\s+x0,\s*\[x0\]", store.lower()):
            errors.append("READBACK_INSTRUCTION_MISSING")
    return errors


def main_errors(view: ElfView, owner_relocations: str,
                owner_source: str) -> list[str]:
    errors: list[str] = []
    if "Machine:                           AArch64" not in view.headers:
        errors.append("MAIN_NOT_AARCH64")
    if "Type:                              DYN" not in view.headers:
        errors.append("MAIN_NOT_PIE")
    if "Requesting program interpreter: /lib/ld-musl-aarch64.so.1" not in view.programs:
        errors.append("MAIN_INTERPRETER_MISMATCH")
    tls_rows = [line for line in view.programs.splitlines()
                if re.match(r"^\s*TLS\s", line)]
    if len(tls_rows) != 1:
        errors.append("MAIN_EXACT_PT_TLS_MISSING")
    else:
        tls_fields = tls_rows[0].split()
        try:
            tls_filesz = int(tls_fields[4], 16)
            tls_memsz = int(tls_fields[5], 16)
            tls_align = int(tls_fields[-1], 16)
        except (IndexError, ValueError):
            errors.append("MAIN_PT_TLS_LAYOUT_MISMATCH")
        else:
            if (tls_filesz, tls_memsz, tls_align) != (0, 0x30, 0x10):
                errors.append("MAIN_PT_TLS_LAYOUT_MISMATCH")
    reservation_rows = [
        line for line in view.symbols.splitlines()
        if line.rstrip().endswith("westlake_bionic_tls_slots_2_7_reservation")
    ]
    if not any(" 48 TLS " in line and " HIDDEN " in line
               for line in reservation_rows):
        errors.append("MAIN_RESERVATION_SYMBOL_MISMATCH")
    needed = re.findall(r"Shared library: \[([^]]+)\]", view.dynamic)
    if needed != ["libwestlake_aperture_fixture_backend.so"]:
        errors.append("MAIN_NEEDED_SET_MISMATCH")
    if "(RPATH)" in view.dynamic or "(RUNPATH)" in view.dynamic:
        errors.append("MAIN_SEARCH_PATH_FORBIDDEN")
    if re.search(r"lib(?:unity|il2cpp|main|_burst_generated)\.so",
                 view.dynamic + view.symbols, flags=re.IGNORECASE):
        errors.append("THIRD_PARTY_DSO_IN_FIXTURE_FORBIDDEN")

    owner_reloc_rows = [
        line for line in owner_relocations.splitlines()
        if "westlake_bionic_tls_slots_2_7_reservation" in line
    ]
    has_hi = any("TLSLE_ADD_TPREL_HI12" in line for line in owner_reloc_rows)
    has_lo = any("TLSLE_ADD_TPREL_LO12_NC" in line for line in owner_reloc_rows)
    if not (has_hi and has_lo and len(owner_reloc_rows) == 2):
        errors.append("OWNER_TLS_SYMBOL_RELOCATION_MISSING")
    if re.search(r"#\s*(?:0x28|40)\b", owner_source, flags=re.IGNORECASE):
        errors.append("OWNER_LITERAL_TP_OFFSET_FORBIDDEN")
    owner_body = function_body(view.disassembly, "WLAF_MainReservationBase")
    if "tpidr_el0" not in owner_body.lower():
        errors.append("OWNER_TP_BASE_READ_MISSING")
    if re.search(r"\badd\s+x0,\s*x0,\s*#0x28\b", owner_body.lower()):
        errors.append("OWNER_LITERAL_TP_OFFSET_FORBIDDEN")
    return errors


def strip_comments(text: str) -> str:
    kept: list[str] = []
    for line in text.splitlines():
        line = line.split("#", 1)[0]
        line = line.split("//", 1)[0]
        kept.append(line)
    return "\n".join(kept)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--backend", required=True)
    parser.add_argument("--second-backend", required=True)
    parser.add_argument("--main", required=True)
    parser.add_argument("--second-main", required=True)
    parser.add_argument("--owner-object", required=True)
    parser.add_argument("--core", required=True)
    parser.add_argument("--tls-mutant", required=True)
    parser.add_argument("--constructor-mutant", required=True)
    parser.add_argument("--hardcoded-owner-mutant", required=True)
    parser.add_argument("--hardcoded-owner-object", required=True)
    parser.add_argument("--readelf", required=True)
    parser.add_argument("--objdump", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    root = pathlib.Path(args.project_root).resolve(strict=True)
    paths = {
        name: under(pathlib.Path(getattr(args, name)), root)
        for name in (
            "backend", "second_backend", "main", "second_main",
            "owner_object", "core", "tls_mutant", "constructor_mutant",
            "hardcoded_owner_mutant", "hardcoded_owner_object", "readelf",
            "objdump",
        )
    }
    report = pathlib.Path(args.report).resolve()
    try:
        report.relative_to(root)
    except ValueError as error:
        raise RuntimeError(f"report escapes project root: {report}") from error

    fixture = under(
        root / "adapter/framework/native-compat/tests/aperture_writer_fixture",
        root,
    )
    owner_source_path = under(fixture / "target/reservation_owner_aarch64.S", root)
    backend_sources = [
        under(fixture / "include/wlnc_aperture_fixture.h", root),
        under(fixture / "src/aperture_writer.c", root),
    ]
    source_text = "\n".join(path.read_text(encoding="utf-8")
                            for path in backend_sources)
    forbidden_source = {
        "constructor": r"__attribute__\s*\(\(\s*constructor\b",
        "thread_local": r"\b(?:_Thread_local|__thread|thread_local)\b",
        "tpidr": r"\btpidr_el0\b",
        "dynamic_loader": r"\b(?:dlopen|dlsym|dlvsym)\s*\(",
        "package_allowlist": r"\b(?:package_name|bundle_name|app_name)\b",
        "environment_enable": r"\b(?:getenv|secure_getenv)\s*\(",
        "musl_global_guard": r"\b__stack_chk_guard\b",
    }
    source_hits = {
        name: bool(re.search(pattern, source_text, flags=re.IGNORECASE))
        for name, pattern in forbidden_source.items()
    }
    require(not any(source_hits.values()),
            f"forbidden backend source primitive: {source_hits}")

    require(digest(paths["backend"]) == digest(paths["second_backend"]),
            "backend builds are not byte-identical")
    require(digest(paths["main"]) == digest(paths["second_main"]),
            "main fixture builds are not byte-identical")

    backend_view = inspect(paths["backend"], paths["readelf"], paths["objdump"])
    main_view = inspect(paths["main"], paths["readelf"], paths["objdump"])
    owner_relocations = tool(paths["readelf"], "-W", "-r",
                             str(paths["owner_object"]))
    owner_source = owner_source_path.read_text(encoding="utf-8")
    good_backend_errors = backend_errors(backend_view)
    good_main_errors = main_errors(main_view, owner_relocations, owner_source)
    require(not good_backend_errors,
            f"valid backend rejected: {good_backend_errors}")
    require(not good_main_errors,
            f"valid main rejected: {good_main_errors}")

    tls_errors = backend_errors(
        inspect(paths["tls_mutant"], paths["readelf"], paths["objdump"])
    )
    constructor_errors = backend_errors(
        inspect(paths["constructor_mutant"], paths["readelf"], paths["objdump"])
    )
    hardcoded_relocations = tool(
        paths["readelf"], "-W", "-r", str(paths["hardcoded_owner_object"])
    )
    hardcoded_source = under(
        fixture / "target/mutants/hardcoded_owner_aarch64.S", root
    ).read_text(encoding="utf-8")
    hardcoded_errors = main_errors(
        inspect(paths["hardcoded_owner_mutant"], paths["readelf"],
                paths["objdump"]),
        hardcoded_relocations,
        hardcoded_source,
    )
    require("BACKEND_PT_TLS_FORBIDDEN" in tls_errors,
            f"PT_TLS mutant survived: {tls_errors}")
    require("BACKEND_CONSTRUCTOR_FORBIDDEN" in constructor_errors,
            f"constructor mutant survived: {constructor_errors}")
    require("OWNER_TLS_SYMBOL_RELOCATION_MISSING" in hardcoded_errors and
            "OWNER_LITERAL_TP_OFFSET_FORBIDDEN" in hardcoded_errors,
            f"hardcoded TP owner mutant survived: {hardcoded_errors}")

    core_view = inspect(paths["core"], paths["readelf"], paths["objdump"])
    require("libwestlake_aperture_fixture_backend.so" not in core_view.dynamic,
            "audit core gained a fixture backend dependency")
    require("WLAF_" not in core_view.symbols,
            "audit core gained a fixture permit/writer symbol")
    require("tpidr_el0" not in core_view.disassembly.lower(),
            "audit core gained TP access")

    product_files = [
        under(root / "adapter/framework/appspawn-x/BUILD.gn", root),
        under(root / "adapter/framework/appspawn-x/generation/build_generation.sh", root),
        under(root / "adapter/framework/appspawn-x/generation/container_build.sh", root),
        under(root / "adapter/build/inner/compile_appspawnx.sh", root),
    ]
    product_active_text = "\n".join(
        strip_comments(path.read_text(encoding="utf-8"))
        for path in product_files
    )
    forbidden_product_inputs = [
        "libwestlake_aperture_fixture_backend.so",
        "aperture_writer_fixture",
        "bionic_tls_abi.c",
        "unity_pthread_box.c",
        "unity_signal_box.c",
    ]
    product_hits = [
        item for item in forbidden_product_inputs if item in product_active_text
    ]
    require(not product_hits,
            f"fixture/legacy writer reached product build graph: {product_hits}")

    payload = {
        "status": "build_pass",
        "classification": "disabled_target_fixture",
        "device_verified": False,
        "target_executed": False,
        "product_activation": False,
        "product_load_authority": False,
        "real_release_signature_verified": False,
        "backend_sha256": digest(paths["backend"]),
        "main_fixture_sha256": digest(paths["main"]),
        "audit_core_sha256": digest(paths["core"]),
        "deterministic_build_count": 2,
        "checks": {
            "all_inputs_project_local": True,
            "backend_aarch64_dso": True,
            "backend_no_pt_tls": True,
            "backend_no_constructor": True,
            "backend_no_tpidr_access": True,
            "backend_no_musl_global_guard_reference": True,
            "backend_cannot_address_reservation_symbol": True,
            "unique_store_readback_primitive": True,
            "main_exact_existing_reservation": True,
            "main_exact_musl_interpreter": True,
            "owner_address_uses_linker_tls_symbol_relocations": True,
            "owner_literal_tp_offset_absent": True,
            "typed_fixture_permit_only": True,
            "audit_core_has_no_fixture_dependency_or_symbol": True,
            "legacy_writer_sources_excluded_from_product_graph": True,
            "fixture_sources_excluded_from_product_graph": True,
            "source_forbidden_primitive_hits": source_hits,
        },
        "negative_mutants": {
            "backend_pt_tls": sorted(tls_errors),
            "backend_constructor": sorted(constructor_errors),
            "hardcoded_tp_owner": sorted(hardcoded_errors),
            "killed": 3,
        },
        "not_proven": [
            "exact target runtime execution",
            "device CSPRNG syscall availability and policy",
            "all six guest-entry thread classes",
            "real certificate issuer trust or revocation",
            "production appspawn/native-loader integration",
            "Unity guest load or first frame",
        ],
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print("PASS aperture target ELF gate mutants_killed=3 "
          "product_activation=false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
