#!/usr/bin/env python3
"""Binary/source gate for the Route-A WLTG product integration."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


WLTG_EXPORTS = {
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

PTHREAD_BRIDGE_EXPORTS = {
    "WLPB_GetAbiVersion",
    "WLPB_InstallHostOps",
    "pthread_create",
    "pthread_exit",
    "pthread_attr_init",
    "pthread_attr_destroy",
    "pthread_attr_setdetachstate",
    "pthread_attr_setstacksize",
    "pthread_attr_getstack",
    "pthread_getattr_np",
}

APP_NATIVE_LOADER_EXPORTS = {
    "ANL_InstallRuntimeGate",
    "ANL_CreateDomain",
    "ANL_Dlopen",
    "ANL_Dlsym",
    "ANL_Dlclose",
    "ANL_Dlerror",
    "ANL_GetNamespaceName",
    "ANL_ReleaseDomainHandle",
}

ART_PALETTE_EXPORTS = {
    "PaletteSchedSetPriority",
    "PaletteSchedGetPriority",
    "PaletteWriteCrashThreadStacks",
    "PaletteTraceEnabled",
    "PaletteTraceBegin",
    "PaletteTraceEnd",
    "PaletteTraceIntegerValue",
    "PaletteAshmemCreateRegion",
    "PaletteAshmemSetProtRegion",
    "PaletteCreateOdrefreshStagingDirectory",
    "PaletteShouldReportDex2oatCompilation",
    "PaletteNotifyStartDex2oatCompilation",
    "PaletteNotifyEndDex2oatCompilation",
    "PaletteNotifyDexFileLoaded",
    "PaletteNotifyOatFileLoaded",
    "PaletteShouldReportJniInvocations",
    "PaletteNotifyBeginJniInvocation",
    "PaletteNotifyEndJniInvocation",
    "PaletteReportLockContention",
    "PaletteSetTaskProfiles",
}

HOST_NATIVE_COMPAT_CALLBACKS = {
    "westlake_native_compat_prepare_parent_runtime",
    "westlake_native_compat_verify_parent_preload_thread_ready",
    "westlake_native_compat_prepare_main_thread",
    "westlake_native_compat_verify_current_thread_ready",
    "westlake_native_compat_get_audit_snapshot",
    "westlake_native_compat_get_pthread_bridge_ops",
}

COMPAT_V12_DROP_IN_EXPORTS = {
    "_init", "_fini", "__android_log_security", "__memcmp16",
    "__sync_synchronize", "__sync_val_compare_and_swap_1",
    "__system_property_find", "__system_property_foreach",
    "__system_property_get", "__system_property_read",
    "__system_property_read_callback", "__system_property_set",
    "add_sysprop_change_callback", "adler32", "adler32_combine",
    "android_dlwarning", "android_fdsan_close_with_tag",
    "android_fdsan_exchange_owner_tag", "android_fdsan_get_error_level",
    "android_fdsan_get_owner_tag", "android_fdsan_set_error_level",
    "android_get_abort_message", "android_log_destroy",
    "android_log_parser_read_next", "android_log_read_next",
    "android_log_write_float32", "android_log_write_int32",
    "android_log_write_int64", "android_log_write_list",
    "android_log_write_list_begin", "android_log_write_list_end",
    "android_log_write_string8", "android_log_write_string8_len",
    "android_logger_clear", "android_logger_get_log_readable_size",
    "android_logger_get_log_size", "android_logger_get_log_version",
    "android_logger_list_alloc", "android_logger_list_alloc_time",
    "android_logger_list_free", "android_logger_list_read",
    "android_logger_open", "android_logger_set_log_size", "android_mallopt",
    "android_mallopt_get_caller_info", "android_reset_stack_guards",
    "android_set_abort_message", "create_android_logger",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def legacy_parent_art_target_disabled(
        build_gn: str, parent_main: str) -> bool:
    return ('ohos_executable("appspawn-x")' not in build_gn and
            '":appspawn-x"' not in build_gn and
            'group("appspawn_x_legacy_parent_art_disabled")' in build_gn and
            "WESTLAKE_LEGACY_PARENT_ART_TEST_ONLY" in parent_main and
            '#error "Route A forbids the legacy parent-ART appspawn-x main' in
            parent_main)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(tool: Path, *arguments: str) -> str:
    return subprocess.run(
        [str(tool), *arguments], check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout


def needed(dynamic: str) -> list[str]:
    return re.findall(r"Shared library: \[([^]]+)\]", dynamic)


def dyn_exports(symbols: str) -> set[str]:
    result: set[str] = set()
    in_dynamic = False
    for line in symbols.splitlines():
        if line.startswith("Symbol table '.dynsym'"):
            in_dynamic = True
            continue
        if line.startswith("Symbol table '") and ".dynsym" not in line:
            in_dynamic = False
        if not in_dynamic or " GLOBAL " not in line or " DEFAULT " not in line:
            continue
        fields = line.split()
        if len(fields) >= 8 and " UND " not in f" {line} ":
            result.add(fields[-1].split("@", 1)[0])
    return result


def dyn_imports(symbols: str) -> set[str]:
    result: set[str] = set()
    in_dynamic = False
    for line in symbols.splitlines():
        if line.startswith("Symbol table '.dynsym'"):
            in_dynamic = True
            continue
        if line.startswith("Symbol table '") and ".dynsym" not in line:
            in_dynamic = False
        if not in_dynamic or " UND " not in f" {line} ":
            continue
        fields = line.split()
        if len(fields) >= 8:
            result.add(fields[-1].split("@", 1)[0])
    return result


def sha_manifest(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split(maxsplit=1)
        require(len(fields) == 2 and
                re.fullmatch(r"[0-9a-f]{64}", fields[0]) is not None,
                f"invalid provider manifest line: {line}")
        name = Path(fields[1]).name
        require(name not in result, f"duplicate provider manifest member: {name}")
        result[name] = fields[0]
    return result


def function_body(disassembly: str, name_fragment: str) -> str:
    lines = disassembly.splitlines()
    start = None
    for index, line in enumerate(lines):
        if name_fragment in line and re.search(r"<.*>:$", line.strip()):
            start = index + 1
            break
    if start is None:
        return ""
    body: list[str] = []
    for line in lines[start:]:
        if re.search(r"^[0-9a-f]+ <.*>:$", line.strip()):
            break
        if line.strip():
            body.append(line)
    return "\n".join(body)


def ordered(body: str, names: list[str]) -> bool:
    cursor = 0
    for name in names:
        found = body.find(name, cursor)
        if found < 0:
            return False
        cursor = found + len(name)
    return True


def provider_free_parent_topology(host_needed: list[str],
                                  plugin_needed: list[str],
                                  plugin_imports: set[str]) -> bool:
    provider = "libwestlake_android_runtime_provider.so"
    return (provider not in host_needed and provider not in plugin_needed and
            not any(name.startswith("WLAR_") for name in plugin_imports))


def specialized_child_binary_edges(
        provider_symbols: str, legacy_body: str, prepare_bundle_body: str,
        capture_audit_body: str, commit_audit_body: str,
        construct_body: str, vm_body: str, jni_body: str,
        sequence_body: str) -> bool:
    return (
        "WLAR_ServerPreload" not in provider_symbols and
        "WLAR_ZygotePreFork" not in provider_symbols and
        "WLAR_ZygotePostForkParent" not in provider_symbols and
        "mov\tw0, #-3007" in legacy_body and
        "ret" in legacy_body and
        "ANL_InstallRuntimeGate" in construct_body and
        "AppSpawnXRuntime::startVm" in vm_body and
        "AppSpawnXRuntime::preload" in jni_body and
        sequence_body.count("blr") >= 4 and
        "wlar_child_sequence::Run" in prepare_bundle_body and
        ordered(capture_audit_body, [
            "WLAR_HostServicesPrepareMain",
            "WLAR_HostServicesGetAuditSnapshot",
        ]) and
        ordered(commit_audit_body, [
            "WLAR_HostServicesMarkChildConsumed",
            "WLAR_LoaderPhaseMarkChildReady",
        ]))


def strip_c_comments(source: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", source, flags=re.DOTALL)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--second-host", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--second-provider", required=True)
    parser.add_argument("--plugin", required=True)
    parser.add_argument("--second-plugin", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--second-registry", required=True)
    parser.add_argument("--pthread-bridge", required=True)
    parser.add_argument("--second-pthread-bridge", required=True)
    parser.add_argument("--compat", required=True)
    parser.add_argument("--second-compat", required=True)
    parser.add_argument("--app-native-loader", required=True)
    parser.add_argument("--second-app-native-loader", required=True)
    parser.add_argument("--native-loader", required=True)
    parser.add_argument("--second-native-loader", required=True)
    parser.add_argument("--provider-set-manifest", required=True)
    parser.add_argument("--art-palette", required=True)
    parser.add_argument("--second-art-palette", required=True)
    parser.add_argument("--owner-object", required=True)
    parser.add_argument("--readelf", required=True)
    parser.add_argument("--objdump", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    root = Path(args.project_root).resolve(strict=True)
    paths = {
        name: Path(getattr(args, name)).resolve(strict=True)
        for name in (
            "host", "second_host", "provider", "second_provider",
            "plugin", "second_plugin",
            "registry", "second_registry", "pthread_bridge",
            "second_pthread_bridge", "compat", "second_compat",
            "app_native_loader", "second_app_native_loader", "owner_object",
            "native_loader", "second_native_loader",
            "provider_set_manifest", "art_palette", "second_art_palette",
            "readelf", "objdump",
        )
    }
    for path in paths.values():
        path.relative_to(root)

    legacy_build = (root / "adapter/framework/appspawn-x/BUILD.gn").read_text()
    legacy_main = (root / "adapter/framework/appspawn-x/src/main.cpp").read_text()
    require(legacy_parent_art_target_disabled(legacy_build, legacy_main),
            "competing installable legacy parent-ART topology is admitted")
    require(not legacy_parent_art_target_disabled(
                legacy_build.replace(
                    'group("appspawn_x_legacy_parent_art_disabled")',
                    'ohos_executable("appspawn-x")', 1),
                legacy_main),
            "legacy parent-ART target-admission mutant survived")
    require(not legacy_parent_art_target_disabled(
                legacy_build,
                legacy_main.replace(
                    "WESTLAKE_LEGACY_PARENT_ART_TEST_ONLY", "mutated", 1)),
            "legacy parent-ART main-admission mutant survived")

    require(digest(paths["host"]) == digest(paths["second_host"]),
            "stock host is not deterministic")
    require(digest(paths["registry"]) == digest(paths["second_registry"]),
            "registry is not deterministic")
    require(digest(paths["pthread_bridge"]) ==
            digest(paths["second_pthread_bridge"]),
            "pthread bridge is not deterministic")
    require(digest(paths["compat"]) == digest(paths["second_compat"]),
            "compat is not deterministic")
    require(digest(paths["provider"]) == digest(paths["second_provider"]),
            "runtime provider is not deterministic")
    require(digest(paths["plugin"]) == digest(paths["second_plugin"]),
            "child plugin is not deterministic")
    require(digest(paths["app_native_loader"]) ==
            digest(paths["second_app_native_loader"]),
            "app native loader is not deterministic")
    require(digest(paths["native_loader"]) ==
            digest(paths["second_native_loader"]),
            "native loader is not deterministic")
    require(digest(paths["art_palette"]) ==
            digest(paths["second_art_palette"]),
            "ART Palette provider is not deterministic")

    provider_manifest = sha_manifest(paths["provider_set_manifest"])
    provider_directory = paths["provider_set_manifest"].parent / "providers"
    provider_files = {
        path.name: path for path in provider_directory.glob("*.so")
    }
    require(len(provider_manifest) == 26 and
            set(provider_manifest) == set(provider_files),
            "provider-set manifest is not the exact 26-DSO deployment set")
    for name, expected_sha in provider_manifest.items():
        require(digest(provider_files[name]) == expected_sha,
                f"provider-set member hash drift: {name}")
    require(provider_manifest.get("libwestlake_thread_guard_registry.so") ==
            digest(paths["registry"]) and
            provider_manifest.get("libbionic_compat.so") ==
            digest(paths["compat"]) and
            provider_manifest.get("libwestlake_bionic_pthread_bridge.so") ==
            digest(paths["pthread_bridge"]) and
            provider_manifest.get("libapp_native_loader.so") ==
            digest(paths["app_native_loader"]) and
            provider_manifest.get("libnativeloader.so") ==
            digest(paths["native_loader"]) and
            provider_manifest.get("libartpalette-system.so") ==
            digest(paths["art_palette"]),
            "product compatibility artifacts are not the deployment-set bytes")

    host_dynamic = run(paths["readelf"], "-Wd", str(paths["host"]))
    host_symbols = run(paths["readelf"], "-Ws", str(paths["host"]))
    host_disassembly = run(
        paths["objdump"], "-d", "--demangle", str(paths["host"])
    )
    host_needed = needed(host_dynamic)
    require(host_needed.count("libwestlake_thread_guard_registry.so") == 1,
            "stock host must own exactly one direct registry edge")
    require(host_needed.count("libwestlake_android_runtime_provider.so") == 0,
            "stock host must defer provider/ART constructors until plugin load")
    require("libwestlake_bionic_pthread_bridge.so" not in host_needed,
            "namespace-only pthread bridge leaked into host DT_NEEDED")
    plugin_dynamic = run(paths["readelf"], "-Wd", str(paths["plugin"]))
    plugin_symbols = run(paths["readelf"], "-Ws", str(paths["plugin"]))
    plugin_needed = needed(plugin_dynamic)
    plugin_imports = dyn_imports(plugin_symbols)
    require(provider_free_parent_topology(
                host_needed, plugin_needed, plugin_imports),
            "inert child plugin retained provider DT_NEEDED/import")
    require(not provider_free_parent_topology(
                host_needed + ["libwestlake_android_runtime_provider.so"],
                plugin_needed, plugin_imports) and
            not provider_free_parent_topology(
                host_needed,
                plugin_needed + ["libwestlake_android_runtime_provider.so"],
                plugin_imports) and
            not provider_free_parent_topology(
                host_needed, plugin_needed,
                plugin_imports | {"WLAR_EnterAndroidAfterStockSpecialization"}),
            "provider-free parent/plugin topology mutant survived")
    host_exports = dyn_exports(host_symbols)
    require(not (HOST_NATIVE_COMPAT_CALLBACKS & host_exports) and
            all(callback in host_symbols
                for callback in HOST_NATIVE_COMPAT_CALLBACKS),
            "stock host callbacks escaped or disappeared from typed-table boundary")

    prepare_body = function_body(
        host_disassembly, "WestLakeNativeCompatPrepareMainThread"
    )
    require(prepare_body, "native compatibility MAIN function missing")
    require(ordered(prepare_body, [
        "WLTG_AfterForkChildReset",
        "WLTG_ProcessArm",
        "WLTG_IssueThreadTicket",
        "WLTG_PrepareCurrentThread",
        "WLTG_VerifyCurrentThreadReady",
    ]), "MAIN WLTG reset/arm/ticket/write/verify order drifted")

    provider_dynamic = run(paths["readelf"], "-Wd", str(paths["provider"]))
    provider_symbols = run(paths["readelf"], "-Ws", str(paths["provider"]))
    provider_disassembly = run(
        paths["objdump"], "-d", "--demangle", str(paths["provider"])
    )
    provider_needed = needed(provider_dynamic)
    require(provider_needed.count("libapp_native_loader.so") == 1,
            "runtime provider must own exactly one v13 app-loader edge")
    require(provider_needed.count("libwestlake_thread_guard_registry.so") == 1,
            "runtime provider must own the central JNI admission registry edge")
    require(" ANL_InstallRuntimeGate" in provider_symbols and
            not any(callback in provider_symbols
                    for callback in HOST_NATIVE_COMPAT_CALLBACKS),
            "runtime provider lost loader gate or regained direct MAIN imports")
    prepare_callback_body = function_body(
        provider_disassembly, "WLAR_HostServicesPrepareMain")
    audit_callback_body = function_body(
        provider_disassembly, "WLAR_HostServicesGetAuditSnapshot")
    legacy_body = function_body(
        provider_disassembly, "WLAR_EnterAndroidAfterStockSpecialization"
    )
    prepare_bundle_body = function_body(
        provider_disassembly, "WLAR_PrepareA02PrerequisiteBundleV2")
    capture_audit_body = function_body(
        provider_disassembly, "(anonymous namespace)::CaptureAuditSnapshot")
    commit_audit_body = function_body(
        provider_disassembly, "(anonymous namespace)::CommitAuditSnapshot")
    construct_body = function_body(
        provider_disassembly, "(anonymous namespace)::Constructors")
    vm_body = function_body(
        provider_disassembly, "(anonymous namespace)::Vm")
    jni_body = function_body(
        provider_disassembly, "(anonymous namespace)::Jni")
    sequence_body = function_body(provider_disassembly,
                                  "wlar_child_sequence::Run")
    require(specialized_child_binary_edges(
                provider_symbols, legacy_body, prepare_bundle_body,
                capture_audit_body, commit_audit_body, construct_body,
                vm_body, jni_body, sequence_body),
            "specialized-child A06 prerequisite binary seam drifted")
    for original, replacement in (
        ("#-3007", "#-3006"),
        ("ANL_InstallRuntimeGate", "mutated_loader_gate"),
        ("AppSpawnXRuntime::startVm", "mutated_vm"),
        ("AppSpawnXRuntime::preload", "mutated_jni"),
        ("WLAR_HostServicesPrepareMain", "mutated_prepare_main"),
        ("WLAR_HostServicesGetAuditSnapshot", "mutated_audit_snapshot"),
        ("WLAR_HostServicesMarkChildConsumed", "mutated_child_consumed"),
        ("WLAR_LoaderPhaseMarkChildReady", "mutated_child_ready"),
        ("blr", "mutated_indirect_call"),
        ("wlar_child_sequence::Run", "mutated_sequence"),
    ):
        require(not specialized_child_binary_edges(
                    provider_symbols,
                    legacy_body.replace(original, replacement),
                    prepare_bundle_body.replace(original, replacement),
                    capture_audit_body.replace(original, replacement),
                    commit_audit_body.replace(original, replacement),
                    construct_body.replace(original, replacement),
                    vm_body.replace(original, replacement),
                    jni_body.replace(original, replacement),
                    sequence_body.replace(original, replacement)),
                f"specialized-child binary mutant survived: {original}")
    require(not specialized_child_binary_edges(
                provider_symbols + "\nWLAR_ServerPreload", legacy_body,
                prepare_bundle_body, capture_audit_body, commit_audit_body,
                construct_body, vm_body, jni_body, sequence_body),
            "parent provider-entry mutant survived")
    require("blr" in prepare_callback_body and
            "blr" in audit_callback_body,
            "provider host-service callbacks are not typed-table indirect calls")

    app_loader_dynamic = run(
        paths["readelf"], "-Wd", str(paths["app_native_loader"])
    )
    app_loader_symbols = run(
        paths["readelf"], "-Ws", str(paths["app_native_loader"])
    )
    app_loader_disassembly = run(
        paths["objdump"], "-d", str(paths["app_native_loader"])
    )
    require("Library soname: [libapp_native_loader.so]" in app_loader_dynamic,
            "app native loader SONAME drift")
    require("BIND_NOW" in app_loader_dynamic and
            "(RPATH)" not in app_loader_dynamic and
            "(RUNPATH)" not in app_loader_dynamic and
            "(TEXTREL)" not in app_loader_dynamic,
            "app native loader binding policy drift")
    require(dyn_exports(app_loader_symbols) == APP_NATIVE_LOADER_EXPORTS,
            "app native loader exact export contract drifted")
    app_loader_dlopen_body = function_body(
        app_loader_disassembly, "ANL_Dlopen"
    )
    require(app_loader_dlopen_body and
            "blr" in app_loader_dlopen_body and
            "dlopen_ns@plt" not in app_loader_dlopen_body,
            "ANL_Dlopen lost READY callback-before-loader structure")
    app_loader_dlclose_body = function_body(
        app_loader_disassembly, "ANL_Dlclose"
    )
    require(app_loader_dlclose_body and ordered(app_loader_dlclose_body, [
        "blr", "dlclose@plt"
    ]), "ANL_Dlclose lost READY callback-before-destructor structure")
    app_loader_create_body = function_body(
        app_loader_disassembly, "ANL_CreateDomain"
    )
    require(app_loader_create_body and
            "blr" in app_loader_create_body and
            "dlns_create2@plt" not in app_loader_create_body and
            "dlopen_ns@plt" not in app_loader_create_body and
            "dlsym@plt" not in app_loader_create_body,
            "ANL_CreateDomain lost default-owner namespace callback")
    stock_namespace_create_body = function_body(
        host_disassembly, "StockCreateConfiguredNamespaces"
    )
    stock_namespace_open_body = function_body(
        host_disassembly, "StockOpenNamespace"
    )
    require(stock_namespace_create_body and
            stock_namespace_create_body.count("dlns_create2@plt") >= 2 and
            "dlopen_ns@plt" in stock_namespace_create_body and
            "dlsym@plt" in stock_namespace_create_body and
            "blr" in stock_namespace_create_body and
            "dlns_inherit@plt" in stock_namespace_create_body and
            stock_namespace_open_body and
            "dlopen_ns@plt" in stock_namespace_open_body,
            "stock host lost namespace/bootstrap ownership")

    palette_dynamic = run(paths["readelf"], "-Wd", str(paths["art_palette"]))
    palette_symbols = run(paths["readelf"], "-Ws", str(paths["art_palette"]))
    palette_disassembly = run(
        paths["objdump"], "-d", str(paths["art_palette"])
    )
    require("Library soname: [libartpalette-system.so]" in palette_dynamic,
            "ART Palette SONAME drift")
    require(set(needed(palette_dynamic)) == {"libc.so", "liblog.so"} and
            "BIND_NOW" in palette_dynamic and
            "(RPATH)" not in palette_dynamic and
            "(RUNPATH)" not in palette_dynamic and
            "(TEXTREL)" not in palette_dynamic,
            "ART Palette dependency/binding policy drift")
    require(dyn_exports(palette_symbols) == ART_PALETTE_EXPORTS,
            "ART Palette exact export contract drifted")
    require(" UND setpriority" in palette_symbols and
            " UND getpriority" in palette_symbols,
            "ART Palette lost real Musl scheduler imports")
    require("setpriority" in function_body(
                palette_disassembly, "PaletteSchedSetPriority") and
            "getpriority" in function_body(
                palette_disassembly, "PaletteSchedGetPriority"),
            "ART Palette scheduler boundary became fake")

    registry_headers = run(paths["readelf"], "-Wh", str(paths["registry"]))
    registry_programs = run(paths["readelf"], "-Wl", str(paths["registry"]))
    registry_dynamic = run(paths["readelf"], "-Wd", str(paths["registry"]))
    registry_symbols = run(paths["readelf"], "-Ws", str(paths["registry"]))
    registry_relocs = run(paths["readelf"], "-Wr", str(paths["registry"]))
    registry_disassembly = run(paths["objdump"], "-d", str(paths["registry"]))
    require("Machine:                           AArch64" in registry_headers,
            "registry is not AArch64")
    require("Library soname: [libwestlake_thread_guard_registry.so]" in
            registry_dynamic, "registry SONAME drift")
    require("(NEEDED)" not in registry_dynamic,
            "registry unexpectedly owns a runtime dependency")
    require(not re.search(r"^\s*TLS\s", registry_programs, re.MULTILINE),
            "registry PT_TLS forbidden")
    require(not re.search(r"TLS|TLSDESC|TPREL|DTPREL", registry_relocs,
                          re.IGNORECASE), "registry TLS relocation forbidden")
    require("tpidr_el0" not in registry_disassembly.lower(),
            "registry DSO reads TP directly")
    require(WLTG_EXPORTS <= dyn_exports(registry_symbols),
            "registry export contract incomplete")

    pthread_bridge_headers = run(
        paths["readelf"], "-Wh", str(paths["pthread_bridge"])
    )
    pthread_bridge_programs = run(
        paths["readelf"], "-Wl", str(paths["pthread_bridge"])
    )
    pthread_bridge_dynamic = run(
        paths["readelf"], "-Wd", str(paths["pthread_bridge"])
    )
    pthread_bridge_symbols = run(
        paths["readelf"], "-Ws", str(paths["pthread_bridge"])
    )
    pthread_bridge_relocs = run(
        paths["readelf"], "-Wr", str(paths["pthread_bridge"])
    )
    pthread_bridge_disassembly = run(
        paths["objdump"], "-d", str(paths["pthread_bridge"])
    )
    require("Machine:                           AArch64" in
            pthread_bridge_headers,
            "pthread bridge is not AArch64")
    require("Library soname: [libwestlake_bionic_pthread_bridge.so]" in
            pthread_bridge_dynamic,
            "pthread bridge SONAME drift")
    require("BIND_NOW" in pthread_bridge_dynamic and
            "(NEEDED)" not in pthread_bridge_dynamic and
            "(RPATH)" not in pthread_bridge_dynamic and
            "(RUNPATH)" not in pthread_bridge_dynamic and
            "(TEXTREL)" not in pthread_bridge_dynamic,
            "pthread bridge dependency/binding policy drift")
    require(re.search(r"\((?:INIT|FINI|INIT_ARRAY|FINI_ARRAY)\)",
                      pthread_bridge_dynamic) is None,
            "pthread bridge constructor/destructor dynamic tag forbidden")
    require(not re.search(r"^\s*TLS\s", pthread_bridge_programs,
                          re.MULTILINE),
            "pthread bridge PT_TLS forbidden")
    require(not re.search(r"TLS|TLSDESC|TPREL|DTPREL",
                          pthread_bridge_relocs, re.IGNORECASE),
            "pthread bridge TLS relocation forbidden")
    require("tpidr_el0" not in pthread_bridge_disassembly.lower(),
            "pthread bridge reads TP directly")
    pthread_bridge_exports = dyn_exports(pthread_bridge_symbols) - {
        "LIBC", "WESTLAKE_WLPB_1",
    }
    require(pthread_bridge_exports == PTHREAD_BRIDGE_EXPORTS,
            "pthread bridge exact export contract drifted: "
            f"{sorted(pthread_bridge_exports)}")
    require(not dyn_imports(pthread_bridge_symbols),
            "freestanding pthread bridge has dynamic imports")
    pthread_bridge_start = function_body(
        pthread_bridge_disassembly, "start_trampoline"
    )
    pthread_bridge_create = function_body(
        pthread_bridge_disassembly, "pthread_create"
    )
    pthread_bridge_install = function_body(
        pthread_bridge_disassembly, "WLPB_InstallHostOps"
    )
    require(pthread_bridge_start and "blr" in pthread_bridge_start and
            pthread_bridge_create and "blr" in pthread_bridge_create and
            pthread_bridge_install and "ret" in pthread_bridge_install,
            "pthread bridge contains a missing/trivial core body")

    compat_dynamic = run(paths["readelf"], "-Wd", str(paths["compat"]))
    compat_symbols = run(paths["readelf"], "-Ws", str(paths["compat"]))
    compat_disassembly = run(paths["objdump"], "-d", str(paths["compat"]))
    require("Library soname: [libbionic_compat.so]" in compat_dynamic,
            "compat SONAME drift")
    require(dyn_exports(compat_symbols) == COMPAT_V12_DROP_IN_EXPORTS,
            "safe compatibility DSO is not a v12 ABI drop-in")
    require("__stack_chk_guard" not in compat_symbols,
            "compat mutates or imports Musl global stack guard")
    require("bionic_tls_abi_init_main_thread" not in compat_symbols and
            "tpidr_el0" not in compat_disassembly.lower(),
            "legacy constructor/direct-TP guard owner survived")
    require("pthread_create" not in dyn_exports(compat_symbols),
            "global compat pthread provider survived")
    reset_body = function_body(compat_disassembly,
                               "android_reset_stack_guards")
    require(reset_body and "_exit" in reset_body and
            "open" not in reset_body and "read" not in reset_body,
            "unsupported legacy reset is not deterministic fail-closed")

    owner_relocs = run(paths["readelf"], "-Wr", str(paths["owner_object"]))
    owner_disassembly = run(paths["objdump"], "-d", str(paths["owner_object"]))
    require(owner_relocs.count(
                "westlake_bionic_tls_slots_2_7_reservation") == 2 and
            "TLSLE_ADD_TPREL_HI12" in owner_relocs and
            "TLSLE_ADD_TPREL_LO12_NC" in owner_relocs,
            "MAIN owner lost TLS-symbol relocations")
    require(owner_disassembly.lower().count("tpidr_el0") == 1,
            "MAIN owner must be the only one-step TP resolver")

    native_source = (
        root / "adapter/framework/appspawn-x/src/native_compat_prepare.cpp"
    ).read_text(encoding="utf-8")
    stock_host_source = (
        root / "adapter/framework/appspawn-x/security_specialization/"
        "stock_child_plugin/src/westlake_stock_host_main.c"
    ).read_text(encoding="utf-8")
    misc_source = (
        root / "adapter/framework/appspawn-x/bionic_compat/src/misc_compat.cpp"
    ).read_text(encoding="utf-8")
    app_loader_source = (
        root / "adapter/framework/app-native-loader/src/app_native_loader.c"
    ).read_text(encoding="utf-8")
    misc_code = strip_c_comments(misc_source)
    require("getrandom(&guard, sizeof(guard), 0)" in native_source and
            "guard &= " not in native_source and
            "__stack_chk_guard" not in native_source,
            "product issuer contains a second/masked/Musl guard")
    require("kAuditCapacity" not in native_source and
            "audit_accepted_count" in native_source,
            "product audit sink has a finite event cap")
    require("westlake_native_compat_get_audit_snapshot" in native_source and
            "registry.audit_drop_count != UINT64_C(0)" in native_source and
            "accepted_before != accepted_after" in native_source,
            "reproducible non-torn audit digest snapshot is absent")
    require(all(
        f"services.{field} =\n        {callback};" in stock_host_source
        for field, callback in (
            ("prepare_parent_runtime",
             "westlake_native_compat_prepare_parent_runtime"),
            ("verify_parent_preload_thread_ready",
             "westlake_native_compat_verify_parent_preload_thread_ready"),
            ("prepare_main_thread",
             "westlake_native_compat_prepare_main_thread"),
            ("verify_current_thread_ready",
             "westlake_native_compat_verify_current_thread_ready"),
            ("get_audit_snapshot",
             "westlake_native_compat_get_audit_snapshot"),
            ("get_pthread_bridge_ops",
             "westlake_native_compat_get_pthread_bridge_ops"),
        )
    ), "stock host typed-table callback binding drifted")
    require(re.search(r"MarkFailed\(\);\s*MarkFailed\(\);",
                      native_source) is None,
            "duplicate failure transition survived merge")
    require("0x00000aff0a0d0000" not in misc_code and
            "__stack_chk_guard" not in misc_code,
            "legacy fixed/global guard source survived")
    create_source = stock_host_source[
        stock_host_source.index(
            "static WLASC_NOINLINE int StockCreateConfiguredNamespaces("):
        stock_host_source.index(
            "static WLASC_NOINLINE void *StockOpenNamespace(")
    ]
    require(ordered(create_source, [
        "dlns_create2(bridge_namespace",
        "dlopen_ns(",
        "dlsym(",
        "install(pthread_bridge_ops)",
        "dlns_create2(app_namespace",
        "dlns_inherit(app_namespace, bridge_namespace",
    ]) and
        "namespace_host_ops.create_configured_namespaces(" in
            app_loader_source and
        "namespace_host_ops.open_namespace(" in app_loader_source,
        "default-owner pthread bridge/app namespace order drifted")

    report = Path(args.report).resolve()
    report.relative_to(root)
    payload = {
        "status": "pass_main_and_loader_product_integration",
        "wltg_canonical_bionic_process_guard_equals_all_admitted_slot5": False,
        "musl_global_guard_untouched": True,
        "main_binary_call_order_proven": True,
        "single_registry_startup_owner": True,
        "exact_provider_set_identity_bound": True,
        "real_art_palette_product_integrated": True,
        "unbounded_compressed_audit_sink": True,
        "audit_sink_is_complete_event_log": False,
        "audit_acceptance_counters_lossless": True,
        "audit_snapshot_digest_exported": True,
        "namespace_pthread_bridge_product_integrated": True,
        "central_jni_attach_product_integrated": True,
        "guest_loader_ready_gate_product_integrated": True,
        "guest_dlclose_destructor_ready_gate_product_integrated": True,
        "product_activation": False,
        "device_verified": False,
        "sha256": {
            "host": digest(paths["host"]),
            "provider": digest(paths["provider"]),
            "registry": digest(paths["registry"]),
            "pthread_bridge": digest(paths["pthread_bridge"]),
            "compat": digest(paths["compat"]),
            "app_native_loader": digest(paths["app_native_loader"]),
            "native_loader": digest(paths["native_loader"]),
            "provider_set_manifest": digest(paths["provider_set_manifest"]),
            "art_palette": digest(paths["art_palette"]),
        },
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print("PASS Route-A MAIN WLTG + loader READY product integration; remaining boundaries fail closed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
