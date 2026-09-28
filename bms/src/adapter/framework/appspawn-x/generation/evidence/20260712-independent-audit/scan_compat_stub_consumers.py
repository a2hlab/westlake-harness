#!/usr/bin/env python3
"""Scan static undefined references to the admitted compat stubs/partials.

Absence of a direct undefined symbol is *not* interpreted as first-frame
non-use.  Every group that imports dlsym/dlopen (or lacks a complete frozen
recursive closure) is reported as dynamically unresolved / NOT_PROVEN.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import struct
import sys

from independent_audit import AuditError, Elf64, require, sha256


SYMBOLS = {
    # system_properties.cpp
    "__system_property_foreach": ("stub_success", "system_properties.cpp", 104),
    "add_sysprop_change_callback": ("partial_registration_never_dispatched", "system_properties.cpp", 117),
    # malloc_compat.cpp
    "android_mallopt": ("mixed_fake_success_or_unsupported", "malloc_compat.cpp", 9),
    "android_mallopt_get_caller_info": ("stub_empty_result", "malloc_compat.cpp", 28),
    # fdsan_stubs.cpp
    "android_fdsan_get_error_level": ("default_disabled", "fdsan_stubs.cpp", 8),
    "android_fdsan_set_error_level": ("no_op_default_disabled", "fdsan_stubs.cpp", 12),
    "android_fdsan_exchange_owner_tag": ("no_op", "fdsan_stubs.cpp", 18),
    "android_fdsan_get_owner_tag": ("default_zero", "fdsan_stubs.cpp", 24),
    "android_fdsan_close_with_tag": ("partial_ignores_tag", "fdsan_stubs.cpp", 29),
    # misc_compat.cpp
    "android_reset_stack_guards": ("partial_fixed_canary_fallback", "misc_compat.cpp", 16),
    "android_set_abort_message": ("partial_process_global_buffer_stderr", "misc_compat.cpp", 35),
    "android_get_abort_message": ("partial_process_global_buffer", "misc_compat.cpp", 43),
    "_Z15ErrorCodeStringi": ("handwritten_default_mapping", "misc_compat.cpp", 49),
    "android_dlwarning": ("no_op", "misc_compat.cpp", 73),
    # liblog_android_supplement.cpp
    "__android_log_security": ("default_zero", "liblog_android_supplement.cpp", 33),
    "android_logger_list_alloc": ("fake_handle", "liblog_android_supplement.cpp", 49),
    "android_logger_list_alloc_time": ("fake_handle", "liblog_android_supplement.cpp", 58),
    "android_logger_open": ("fake_handle", "liblog_android_supplement.cpp", 74),
    "android_logger_list_read": ("default_eof", "liblog_android_supplement.cpp", 82),
    "android_logger_get_log_size": ("default_zero", "liblog_android_supplement.cpp", 87),
    "android_logger_set_log_size": ("fake_success", "liblog_android_supplement.cpp", 88),
    "android_logger_get_log_readable_size": ("default_zero", "liblog_android_supplement.cpp", 89),
    "android_logger_get_log_version": ("fixed_default_four", "liblog_android_supplement.cpp", 90),
    "android_logger_clear": ("fake_success", "liblog_android_supplement.cpp", 92),
    "create_android_logger": ("fake_event_context", "liblog_android_supplement.cpp", 104),
    "android_log_destroy": ("partial_fake_context_destroy", "liblog_android_supplement.cpp", 111),
    "android_log_write_int32": ("fake_success_drops_event", "liblog_android_supplement.cpp", 121),
    "android_log_write_int64": ("fake_success_drops_event", "liblog_android_supplement.cpp", 122),
    "android_log_write_float32": ("fake_success_drops_event", "liblog_android_supplement.cpp", 123),
    "android_log_write_string8": ("fake_success_drops_event", "liblog_android_supplement.cpp", 124),
    "android_log_write_string8_len": ("fake_success_drops_event", "liblog_android_supplement.cpp", 125),
    "android_log_write_list_begin": ("fake_success_drops_event", "liblog_android_supplement.cpp", 126),
    "android_log_write_list_end": ("fake_success_drops_event", "liblog_android_supplement.cpp", 127),
    "android_log_write_list": ("fake_success_drops_event", "liblog_android_supplement.cpp", 128),
    "android_log_read_next": ("default_end", "liblog_android_supplement.cpp", 131),
    "android_log_parser_read_next": ("default_end", "liblog_android_supplement.cpp", 132),
    # sync_builtins.c
    "adler32_combine": ("incorrect_simplified_result", "sync_builtins.c", 68),
}


def elf_files(roots: list[pathlib.Path]) -> list[pathlib.Path]:
    result: dict[pathlib.Path, pathlib.Path] = {}
    for root in roots:
        candidates = [root] if root.is_file() else root.rglob("*")
        for path in candidates:
            if not path.is_file() or path.is_symlink():
                continue
            try:
                if path.read_bytes()[:4] != b"\x7fELF":
                    continue
            except OSError:
                continue
            result[path.resolve()] = path
    return sorted(result.values(), key=lambda item: str(item))


def scan_group(name: str, roots: list[pathlib.Path], complete: bool) -> dict[str, object]:
    files = elf_files(roots)
    consumers: dict[str, list[str]] = {symbol: [] for symbol in SYMBOLS}
    dynamic_resolvers: dict[str, list[str]] = {
        "dlsym": [], "dlvsym": [], "dlopen": [], "android_dlopen_ext": []
    }
    errors: list[str] = []
    inventory = []
    for path in files:
        try:
            elf = Elf64(path)
            undefined = {
                symbol_name.split("@", 1)[0]
                for symbol_name, _, _, shndx, _, _ in elf.symbols()
                if shndx == Elf64.SHN_UNDEF and symbol_name
            }
        except (AuditError, OSError, struct.error) as error:  # type: ignore[name-defined]
            errors.append(f"{path}: {error}")
            continue
        relative = str(path)
        inventory.append({"path": relative, "sha256": sha256(path)})
        for symbol in SYMBOLS:
            if symbol in undefined:
                consumers[symbol].append(relative)
        for resolver in dynamic_resolvers:
            if resolver in undefined:
                dynamic_resolvers[resolver].append(relative)
    direct = {
        symbol: paths for symbol, paths in consumers.items() if paths
    }
    return {
        "name": name,
        "complete_recursive_closure_claimed": complete,
        "elf_count": len(files),
        "inventory": inventory,
        "direct_undefined_stub_refs": direct,
        "direct_ref_count": sum(len(paths) for paths in direct.values()),
        "dynamic_resolver_imports": {
            symbol: paths for symbol, paths in dynamic_resolvers.items() if paths
        },
        "dynamic_symbol_use": "NOT_PROVEN" if any(dynamic_resolvers.values()) else
                              "NO_DIRECT_RESOLVER_IMPORT_OBSERVED_NOT_A_NONUSE_PROOF",
        "first_frame_non_use": "NOT_PROVEN",
        "parse_errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--initial-root", action="append", type=pathlib.Path, default=[])
    parser.add_argument("--initial-complete", action="store_true")
    parser.add_argument("--app-candidate-root", action="append", type=pathlib.Path, default=[])
    parser.add_argument("--guest-root", action="append", type=pathlib.Path, default=[])
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    try:
        for root in args.initial_root + args.app_candidate_root + args.guest_root:
            require(root.exists(), f"missing scan root: {root}")
            require(pathlib.Path("/opt/21.Game/02.unity.cardwords").resolve() in
                    [root.resolve(), *root.resolve().parents],
                    f"scan input escaped project: {root}")
        result = {
            "schema": "westlake-compat-stub-consumer-scan-v1",
            "interpretation": (
                "Direct undefined references only. A miss is never first-frame non-use proof; "
                "dlsym/dlopen and an incomplete recursive closure remain NOT_PROVEN."
            ),
            "stub_symbol_catalog": [
                {"symbol": symbol, "classification": fields[0],
                 "source": fields[1], "line": fields[2]}
                for symbol, fields in SYMBOLS.items()
            ],
            "groups": [
                scan_group("final_initial_closure", args.initial_root, args.initial_complete),
                scan_group("current_app_runtime_candidate_not_final", args.app_candidate_root, False),
                scan_group("canonical_cardwords_guest_roots_not_recursive_closure", args.guest_root, False),
            ],
        }
        if args.summary:
            for group in result["groups"]:
                print(
                    f"GROUP {group['name']} elf_count={group['elf_count']} "
                    f"complete={str(group['complete_recursive_closure_claimed']).lower()} "
                    f"direct_refs={group['direct_ref_count']} "
                    f"dynamic={group['dynamic_symbol_use']} "
                    f"parse_errors={len(group['parse_errors'])}"
                )
                for symbol, paths in group["direct_undefined_stub_refs"].items():
                    print(f"DIRECT {group['name']} {symbol} <- {','.join(paths)}")
                resolver_count = sum(
                    len(paths) for paths in group["dynamic_resolver_imports"].values()
                )
                print(f"NOT_PROVEN {group['name']} dynamic_resolver_import_count={resolver_count}")
                print(f"NOT_PROVEN {group['name']} first_frame_non_use")
        else:
            print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except AuditError as error:
        print(f"FAILED {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
