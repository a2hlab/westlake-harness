#!/usr/bin/env python3
"""Fail-closed AArch64 structural gate for the thread guard registry."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass


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
    versions: str
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
        versions=tool(readelf, "-W", "--version-info", str(path)),
        notes=tool(readelf, "-W", "-n", str(path)),
        disassembly=tool(objdump, "-d", str(path)),
    )


def function_body(disassembly: str, symbol: str) -> str:
    lines = disassembly.splitlines()
    marker = re.compile(rf"^[0-9a-f]+ <{re.escape(symbol)}>:$")
    start: int | None = None
    for index, line in enumerate(lines):
        if marker.match(line.strip()):
            start = index + 1
            break
    if start is None:
        return ""
    result: list[str] = []
    next_symbol = re.compile(r"^[0-9a-f]+ <[^>]+>:$")
    for line in lines[start:]:
        if next_symbol.match(line.strip()):
            break
        if line.strip():
            result.append(line)
    return "\n".join(result)


def exports_and_undefined(symbols: str) -> tuple[set[str], list[str]]:
    exports: set[str] = set()
    undefined: list[str] = []
    in_dynsym = False
    for line in symbols.splitlines():
        if line.startswith("Symbol table '.dynsym'"):
            in_dynsym = True
            continue
        if line.startswith("Symbol table '") and ".dynsym" not in line:
            in_dynsym = False
        if not in_dynsym:
            continue
        match = re.search(r"\b(WLTG_[A-Za-z0-9_]+)(?:@@WLTG_1\.0)?$", line)
        if match and " GLOBAL " in line and " DEFAULT " in line:
            exports.add(match.group(1))
        if " UND " in line:
            fields = line.split()
            if fields and fields[-1] != "UND" and not fields[-1].isdigit():
                undefined.append(fields[-1])
    return exports, undefined


def registry_errors(view: ElfView) -> list[str]:
    errors: list[str] = []
    exports, undefined = exports_and_undefined(view.symbols)
    if "Machine:                           AArch64" not in view.headers:
        errors.append("NOT_AARCH64")
    if "Type:                              DYN" not in view.headers:
        errors.append("NOT_DSO")
    if re.search(r"^\s*TLS\s", view.programs, re.MULTILINE):
        errors.append("PT_TLS_FORBIDDEN")
    if re.search(r"\.(?:tdata|tbss)\b", view.sections):
        errors.append("TLS_SECTION_FORBIDDEN")
    if re.search(r"\.(?:preinit_array|init_array)\b", view.sections) or re.search(
        r"\((?:PREINIT_ARRAY|INIT_ARRAY|INIT)\)", view.dynamic
    ):
        errors.append("CONSTRUCTOR_FORBIDDEN")
    if "(NEEDED)" in view.dynamic:
        errors.append("RUNTIME_DEPENDENCY_FORBIDDEN")
    if "(RPATH)" in view.dynamic or "(RUNPATH)" in view.dynamic:
        errors.append("SEARCH_PATH_FORBIDDEN")
    if "(TEXTREL)" in view.dynamic:
        errors.append("TEXTREL_FORBIDDEN")
    if "Library soname: [libwestlake_thread_guard_registry.so]" not in view.dynamic:
        errors.append("SONAME_MISMATCH")
    if "WLTG_1.0" not in view.versions:
        errors.append("SYMBOL_VERSION_MISSING")
    if "Build ID:" not in view.notes:
        errors.append("BUILD_ID_MISSING")
    if exports != EXPECTED_EXPORTS:
        errors.append(f"EXPORT_SET_MISMATCH:{sorted(exports)}")
    if undefined:
        errors.append(f"UNDEFINED_SYMBOLS:{undefined}")
    lowered = view.disassembly.lower()
    if "tpidr_el0" in lowered or re.search(r"\b(?:mrs|msr)\b", lowered):
        errors.append("TP_OR_SYSTEM_REGISTER_FORBIDDEN")
    if re.search(r"TLS|TLSDESC|TPREL|DTPREL", view.relocations,
                 flags=re.IGNORECASE):
        errors.append("TLS_RELOCATION_FORBIDDEN")
    if "westlake_bionic_tls_slots_2_7_reservation" in view.symbols:
        errors.append("RESERVATION_REFERENCE_FORBIDDEN")
    if "__stack_chk_guard" in view.symbols or "__stack_chk_fail" in view.symbols:
        errors.append("MUSL_GLOBAL_GUARD_FORBIDDEN")
    if re.search(r"\bpthread_(?:create|exit|key_create)\b", view.symbols):
        errors.append("PTHREAD_INTERPOSITION_FORBIDDEN")
    if re.search(r"\b(?:dlopen|dlsym|dlvsym|sigaction|signal)\b", view.symbols):
        errors.append("GLOBAL_BROKER_FORBIDDEN")
    if "WLTG_MUTANT" in view.symbols:
        errors.append("MUTATION_HOOK_LEAKED")
    owner_rows = [line for line in view.symbols.splitlines()
                  if line.rstrip().endswith("g_wltg_owner")]
    if not (len(owner_rows) == 1 and " OBJECT " in owner_rows[0]
            and " LOCAL " in owner_rows[0]):
        errors.append(f"SINGLE_LOCAL_OWNER_NOT_PROVEN:{owner_rows}")
    store = function_body(view.disassembly, "WLTG_StoreGuardAndReadback")
    if not store:
        errors.append("GUARD_STORE_MISSING")
    else:
        stores = [line for line in store.splitlines()
                  if re.search(r"\b(?:str|stur|stp|stxr|stlr)\b", line.lower())]
        if len(stores) != 1 or not re.search(
            r"\bstr\s+x1,\s*\[x0\]", stores[0].lower()
        ):
            errors.append("GUARD_STORE_SHAPE_MISMATCH")
        if not re.search(r"\bldr\s+x0,\s*\[x0\]", store.lower()):
            errors.append("GUARD_READBACK_MISSING")
    return errors


def strip_comments(text: str) -> str:
    kept: list[str] = []
    for line in text.splitlines():
        line = line.split("//", 1)[0]
        line = line.split("#", 1)[0]
        kept.append(line)
    return "\n".join(kept)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--library", required=True)
    parser.add_argument("--second-library", required=True)
    parser.add_argument("--owner-object", required=True)
    parser.add_argument("--hardcoded-owner-object", required=True)
    parser.add_argument("--tls-mutant", required=True)
    parser.add_argument("--constructor-mutant", required=True)
    parser.add_argument("--readelf", required=True)
    parser.add_argument("--objdump", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    root = pathlib.Path(args.project_root).resolve(strict=True)
    paths = {
        name: under(pathlib.Path(getattr(args, name)), root)
        for name in (
            "library", "second_library", "owner_object",
            "hardcoded_owner_object", "tls_mutant", "constructor_mutant",
            "readelf", "objdump",
        )
    }
    report = pathlib.Path(args.report).resolve()
    try:
        report.relative_to(root)
    except ValueError as error:
        raise RuntimeError(f"report escapes project root: {report}") from error

    module = under(
        root / "adapter/framework/native-compat/thread-guard-registry", root
    )
    product_sources = [
        under(module / "include/westlake_thread_guard_registry.h", root),
        under(module / "src/thread_guard_registry_internal.h", root),
        under(module / "src/thread_guard_registry.c", root),
        under(module / "src/guard_store_aarch64.S", root),
        under(module / "westlake_thread_guard_registry.map", root),
    ]
    source_text = "\n".join(path.read_text(encoding="utf-8")
                              for path in product_sources)
    registry_source = product_sources[2].read_text(encoding="utf-8")
    forbidden_source = {
        "constructor": r"__attribute__\s*\(\(\s*constructor\b",
        "thread_local": r"\b(?:_Thread_local|__thread|thread_local)\b",
        "tpidr": r"\btpidr_el0\b",
        "dynamic_loader": r"\b(?:dlopen|dlsym|dlvsym)\s*\(",
        "pthread_interposer": r"\bpthread_create\s*\(",
        "signal_interposer": r"\b(?:signal|sigaction)\s*\(",
        "musl_global_guard": r"\b__stack_chk_guard\b",
        "package_allowlist": r"\b(?:package_name|bundle_name|app_name)\b",
        "environment_enable": r"\b(?:getenv|secure_getenv)\s*\(",
    }
    source_hits = {
        name: bool(re.search(pattern, source_text, flags=re.IGNORECASE))
        for name, pattern in forbidden_source.items()
    }
    require(not any(source_hits.values()),
            f"forbidden product source primitive: {source_hits}")
    arm_start = registry_source.find("WltgResult WLTG_ProcessArm(")
    arm_end = registry_source.find("WltgResult WLTG_IssueThreadTicket(",
                                   arm_start)
    prepare_start = registry_source.find(
        "WltgResult WLTG_PrepareCurrentThread("
    )
    prepare_end = registry_source.find(
        "WltgResult WLTG_VerifyCurrentThreadReady(", prepare_start
    )
    require(arm_start >= 0 and arm_end > arm_start and
            prepare_start >= 0 and prepare_end > prepare_start,
            "process guard functions not bounded")
    arm_source = registry_source[arm_start:arm_end]
    prepare_source = registry_source[prepare_start:prepare_end]
    require("WltgGetCsprngGuard(platform_ops" in arm_source and
            "&g_wltg_owner.process_guard, process_guard" in arm_source,
            "canonical process guard is not generated/stored during arm")
    require("&g_wltg_owner.process_guard" in prepare_source and
            "WLTG_StoreGuardAndReadback" in prepare_source and
            "WLTG_REASON_PROCESS_GUARD_MISMATCH" in prepare_source,
            "thread prepare does not copy and recheck the process guard")

    require(digest(paths["library"]) == digest(paths["second_library"]),
            "target builds are not byte-identical")
    good_view = inspect(paths["library"], paths["readelf"], paths["objdump"])
    good_errors = registry_errors(good_view)
    require(not good_errors, f"valid registry rejected: {good_errors}")

    tls_errors = registry_errors(
        inspect(paths["tls_mutant"], paths["readelf"], paths["objdump"])
    )
    constructor_errors = registry_errors(
        inspect(paths["constructor_mutant"], paths["readelf"],
                paths["objdump"])
    )
    require("PT_TLS_FORBIDDEN" in tls_errors,
            f"target PT_TLS mutant survived: {tls_errors}")
    require("CONSTRUCTOR_FORBIDDEN" in constructor_errors,
            f"target constructor mutant survived: {constructor_errors}")

    owner_relocations = tool(paths["readelf"], "-W", "-r",
                             str(paths["owner_object"]))
    owner_disassembly = tool(paths["objdump"], "-d",
                             str(paths["owner_object"]))
    owner_rows = [line for line in owner_relocations.splitlines()
                  if "westlake_bionic_tls_slots_2_7_reservation" in line]
    require(len(owner_rows) == 2 and
            any("TLSLE_ADD_TPREL_HI12" in row for row in owner_rows) and
            any("TLSLE_ADD_TPREL_LO12_NC" in row for row in owner_rows),
            f"symbol-bound MAIN owner relocation missing: {owner_rows}")
    owner_body = function_body(owner_disassembly,
                               "WLTG_TestMainReservationBase")
    require("tpidr_el0" in owner_body.lower(),
            "target owner does not resolve current TP")
    require(not re.search(r"\badd\s+x0,\s*x0,\s*#(?:0x28|40)\b",
                          owner_body.lower()),
            "target owner hardcodes TP+0x28")

    hard_relocations = tool(paths["readelf"], "-W", "-r",
                            str(paths["hardcoded_owner_object"]))
    hard_disassembly = tool(paths["objdump"], "-d",
                            str(paths["hardcoded_owner_object"]))
    hard_body = function_body(hard_disassembly,
                              "WLTG_TestMainReservationBase")
    require("westlake_bionic_tls_slots_2_7_reservation" not in hard_relocations
            and re.search(r"\badd\s+x0,\s*x0,\s*#(?:0x28|40)\b",
                          hard_body.lower()) is not None,
            "hardcoded TP owner mutant was not distinguished")

    activation_files = [
        under(root / "adapter/framework/appspawn-x/BUILD.gn", root),
        under(root / "adapter/framework/appspawn-x/generation/build_generation.sh", root),
        under(root / "adapter/framework/appspawn-x/generation/container_build.sh", root),
        under(root / "adapter/framework/appspawn-x/src/child_main.cpp", root),
        under(root / "adapter/framework/app-native-loader/src/app_native_loader.c", root),
        under(root / "adapter/framework/app-native-loader/include/app_native_loader.h", root),
    ]
    activation_text = "\n".join(
        strip_comments(path.read_text(encoding="utf-8"))
        for path in activation_files
    )
    activation_markers = [
        "libwestlake_thread_guard_registry.so",
        "WLTG_AfterForkChildReset",
        "WLTG_ProcessArm",
        "WLTG_PrepareCurrentThread",
        "WLTG_VerifyCurrentThreadReady",
    ]
    activation_hits = [marker for marker in activation_markers
                       if marker in activation_text]
    require(not activation_hits,
            f"unproved product activation reached build/call graph: {activation_hits}")

    first_sha = digest(paths["library"])
    payload = {
        "status": "build_pass",
        "classification": "real_impl_mechanism_not_product_activated",
        "target": "aarch64-linux-ohos",
        "sha256": first_sha,
        "deterministic_build_count": 2,
        "device_verified": False,
        "target_executed": False,
        "product_activation": False,
        "checks": {
            "all_build_inputs_project_local": True,
            "exact_versioned_exports": sorted(EXPECTED_EXPORTS),
            "single_local_process_registry": True,
            "pt_tls_absent": True,
            "constructors_absent": True,
            "runtime_dependencies_absent": True,
            "tpidr_access_absent_from_registry_dso": True,
            "pthread_or_signal_interposition_absent": True,
            "global_musl_guard_access_absent": True,
            "process_guard_copy_semantics": True,
            "symbol_bound_main_owner_object": True,
            "guard_store_readback_shape": "one str x1,[x0] plus ldr x0,[x0]",
            "target_mutants_killed": [
                "backend_pt_tls", "backend_constructor", "hardcoded_tp_owner"
            ],
            "source_forbidden_primitive_hits": source_hits,
            "product_activation_markers": activation_hits,
        },
        "not_proven": [
            "appspawn-x post-setcon/pre-ART call-site order in a same-generation binary",
            "namespace-scoped typed Bionic pthread bridge and real Musl trampoline",
            "central adapter JNI-attach admission call site",
            "thread-exit/destructor completion boundary",
            "target-device multi-thread execution",
            "CardWords Unity load or first frame",
        ],
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print(f"PASS target registry verifier sha256={first_sha}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
