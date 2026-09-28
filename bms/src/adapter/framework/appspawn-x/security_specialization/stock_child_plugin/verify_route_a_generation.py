#!/usr/bin/env python3
"""Final ELF and adapter-edge gate for the Route A generation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


PLUGIN_ROOT = Path(__file__).resolve().parent
FROZEN_PROVIDER_ROOT = Path(os.environ.get(
    "WESTLAKE_ROUTE_A_BASE_PROVIDER_ROOT",
    PLUGIN_ROOT / "frozen/runtime_provider/provider-v12",
)).resolve()
R45_DYNAMIC_ROOTS = PLUGIN_ROOT.parents[3] / "frozen/r45-dynamic-roots"
BASE_PROVIDER_MANIFEST_SHA256 = (
    "3177745fafb7b4cc9f49c1c535a11de0c79bbec51b4a7cee6f42ee2386425752"
)
BASE_INPUT_MANIFEST_SHA256 = (
    "84ddec0e2dbbc249d6f7ef912663b015356500272f1ce9647302dd936b319ef1"
)
BASE_INDEPENDENT_AUDIT_SHA256 = (
    "597d1b367c8ab399e2edb9d564e92ea550d57fffdf2198a2122bc791c5fad13f"
)
CERTIFIED_EXTERNAL_NEEDED = {
    "libbegetutil.z.so",
    "libc++.so",
    "libc.so",
    "libhilog.so",
    "libshared_libz.z.so",
}

WLAR_EXPORTS = {
    "WLAR_GetRuntimeIdentity",
    "WLAR_InstallHostRuntimeServices",
    "WLAR_EnterAndroidAfterStockSpecialization",
    # The admitted-prepare entry point.  It is listed in the provider version
    # script (westlake_android_runtime_provider.map), defined with
    # visibility("default") in westlake_android_runtime_provider.cpp, and
    # already known to verify_route_a_source.py, so it is part of the provider
    # ABI surface by construction; this set had simply not been updated with
    # it and the exact-match compare below reported the artifact as drifted.
    "WLAR_PrepareA02PrerequisiteBundleV2",
}
HOST_NATIVE_COMPAT_EXPORTS = {
    "westlake_native_compat_prepare_parent_runtime",
    "westlake_native_compat_verify_parent_preload_thread_ready",
    "westlake_native_compat_prepare_main_thread",
    "westlake_native_compat_verify_current_thread_ready",
    "westlake_native_compat_get_audit_snapshot",
}
PLUGIN_STOCK_IMPORTS = {
    "AddAppSpawnHook",
    "AddServerStageHook",
    "CheckAppSpawnMsgFlag",
    "GetAppSpawnMsgInfo",
    "RegChildLooper",
}
HOST_REQUIRED_EXPORTS = PLUGIN_STOCK_IMPORTS
PLUGIN_EXPORTS = {
    "WLASC_GetContractV1",
    "WLASC_InstallStockHostServicesV1",
}
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
HOST_WLTG_IMPORTS = {
    "WLTG_AfterForkChildReset",
    "WLTG_ProcessArm",
    "WLTG_IssueThreadTicket",
    "WLTG_PrepareCurrentThread",
    "WLTG_VerifyCurrentThreadReady",
    "WLTG_Revoke",
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
NATIVE_LOADER_EXPORTS = {
    "InitializeNativeLoader",
    "ResetNativeLoader",
    "CreateClassLoaderNamespace",
    "OpenNativeLibrary",
    "CloseNativeLibrary",
    "NativeLoaderFreeErrorMessage",
    "WLNL_InstallSealedOpenV1",
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
FORBIDDEN_SECURITY_SYMBOLS = re.compile(
    r"(?:applySandbox|applySELinux|applyDac|applyAccessToken|"
    r"SetSelfTokenID|HapDomain|setprocattr|(?:^|@)(?:mount|umount2|unshare|"
    r"chroot|pivot_root|setcon|setexeccon|setresuid|setresgid|setgroups)(?:@|$))"
)


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def exact_symbol_set(actual: set[str], expected: set[str]) -> bool:
    return actual == expected


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def run(tool: Path, *arguments: str) -> str:
    result = subprocess.run(
        [str(tool), *arguments], check=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True
    )
    return result.stdout


def require_arm64_elf(readelf: Path, path: Path, label: str) -> None:
    header = run(readelf, "-Wh", str(path))
    dynamic = run(readelf, "-Wd", str(path))
    require(re.search(r"^\s*Class:\s+ELF64\s*$", header, re.MULTILINE)
            is not None, f"{label} is not ELF64")
    require(re.search(r"^\s*Data:.*little endian\s*$", header, re.MULTILINE)
            is not None, f"{label} is not little-endian ELF")
    require(re.search(r"^\s*Machine:\s+AArch64\s*$", header, re.MULTILINE)
            is not None, f"{label} is not AArch64")
    require(re.search(r"^\s*Type:\s+DYN\b", header, re.MULTILINE)
            is not None, f"{label} is not a PIE/DSO")
    require("(RPATH)" not in dynamic and "(RUNPATH)" not in dynamic and
            "(TEXTREL)" not in dynamic,
            f"{label} has load-path injection or text relocation")


def env_contract(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        require(separator == "=" and key and value,
                f"invalid environment contract line: {raw_line}")
        require(key not in values, f"duplicate environment contract key: {key}")
        values[key] = value
    return values


def symbol_name(line: str) -> str | None:
    fields = line.split()
    if len(fields) < 8 or not fields[0].rstrip(":").isdigit():
        return None
    return fields[-1].split("@", 1)[0]


def dynamic_symbols(text: str, *, undefined: bool) -> set[str]:
    symbols: set[str] = set()
    in_dynamic = False
    for line in text.splitlines():
        if line.startswith("Symbol table '.dynsym'"):
            in_dynamic = True
            continue
        if line.startswith("Symbol table '") and ".dynsym" not in line:
            in_dynamic = False
        if not in_dynamic:
            continue
        name = symbol_name(line)
        if name is None:
            continue
        is_undefined = " UND " in f" {line} "
        if is_undefined == undefined:
            if undefined or (" GLOBAL " in f" {line} " and
                             " DEFAULT " in f" {line} "):
                symbols.add(name)
    return symbols


def needed(text: str) -> list[str]:
    return re.findall(r"\(NEEDED\).*?\[([^]]+)\]", text)


def build_id(text: str) -> str:
    match = re.search(r"Build ID:\s*([0-9a-f]+)", text)
    require(match is not None, "ELF Build-ID absent")
    value = match.group(1)
    require(len(value) == 40, f"Build-ID is not SHA1-sized: {value}")
    return value


def sha_manifest(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text().splitlines():
        fields = line.split(maxsplit=1)
        require(len(fields) == 2 and re.fullmatch(r"[0-9a-f]{64}", fields[0])
                is not None, f"invalid SHA manifest line: {line}")
        name = Path(fields[1].strip()).name
        require(name not in entries, f"duplicate SHA manifest member: {name}")
        entries[name] = fields[0]
    return entries


def provider_closure(
        roots: list[str], providers: dict[str, dict[str, object]]) -> set[str]:
    result: set[str] = set()
    pending = list(roots)
    while pending:
        name = pending.pop()
        if name in result or name not in providers:
            continue
        result.add(name)
        pending.extend(str(item) for item in providers[name]["needed"])
    return result


def function_body(disassembly: str, symbol: str) -> str:
    label = re.search(
        rf"^[0-9a-f]+ <{re.escape(symbol)}(?:@@?[^>]*)?>:\s*$",
        disassembly,
        re.MULTILINE,
    )
    require(label is not None, f"disassembly function absent: {symbol}")
    following = re.search(
        r"^[0-9a-f]+ <[^>]+>:\s*$",
        disassembly[label.end():],
        re.MULTILINE,
    )
    end = len(disassembly) if following is None else label.end() + following.start()
    return disassembly[label.start():end]


def function_body_containing(disassembly: str, symbol_fragment: str) -> str:
    labels = [
        match for match in re.finditer(
            r"^[0-9a-f]+ <([^>]+)>:\s*$", disassembly, re.MULTILINE
        )
        if symbol_fragment in match.group(1)
    ]
    require(len(labels) == 1,
            f"disassembly function fragment is not unique: {symbol_fragment}")
    label = labels[0]
    following = re.search(
        r"^[0-9a-f]+ <[^>]+>:\s*$",
        disassembly[label.end():],
        re.MULTILINE,
    )
    end = len(disassembly) if following is None else label.end() + following.start()
    return disassembly[label.start():end]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--second-host", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--second-provider", required=True)
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
    parser.add_argument("--plugin", required=True)
    parser.add_argument("--second-plugin", required=True)
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--readelf", required=True)
    parser.add_argument("--objdump", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    host = Path(args.host).resolve(strict=True)
    second_host = Path(args.second_host).resolve(strict=True)
    provider = Path(args.provider).resolve(strict=True)
    second_provider = Path(args.second_provider).resolve(strict=True)
    registry = Path(args.registry).resolve(strict=True)
    second_registry = Path(args.second_registry).resolve(strict=True)
    pthread_bridge = Path(args.pthread_bridge).resolve(strict=True)
    second_pthread_bridge = Path(
        args.second_pthread_bridge).resolve(strict=True)
    compat = Path(args.compat).resolve(strict=True)
    second_compat = Path(args.second_compat).resolve(strict=True)
    app_native_loader = Path(args.app_native_loader).resolve(strict=True)
    second_app_native_loader = Path(
        args.second_app_native_loader).resolve(strict=True)
    native_loader = Path(args.native_loader).resolve(strict=True)
    second_native_loader = Path(
        args.second_native_loader).resolve(strict=True)
    provider_set_manifest = Path(
        args.provider_set_manifest).resolve(strict=True)
    art_palette = Path(args.art_palette).resolve(strict=True)
    second_art_palette = Path(args.second_art_palette).resolve(strict=True)
    plugin = Path(args.plugin).resolve(strict=True)
    second_plugin = Path(args.second_plugin).resolve(strict=True)
    inputs = Path(args.inputs).resolve(strict=True)
    readelf = Path(args.readelf).resolve(strict=True)
    objdump = Path(args.objdump).resolve(strict=True)
    report = Path(args.report).resolve()

    require(digest(host) == digest(second_host),
            "stock host builds are not byte-identical")
    require(digest(provider) == digest(second_provider),
            "runtime provider builds are not byte-identical")
    require(digest(registry) == digest(second_registry),
            "thread-guard registry builds are not byte-identical")
    require(digest(pthread_bridge) == digest(second_pthread_bridge),
            "pthread bridge builds are not byte-identical")
    require(digest(compat) == digest(second_compat),
            "safe Bionic compatibility builds are not byte-identical")
    require(digest(app_native_loader) == digest(second_app_native_loader),
            "app native loader builds are not byte-identical")
    require(digest(native_loader) == digest(second_native_loader),
            "native loader builds are not byte-identical")
    require(digest(art_palette) == digest(second_art_palette),
            "ART Palette builds are not byte-identical")
    require(digest(plugin) == digest(second_plugin),
            "child plugin builds are not byte-identical")

    host_header = run(readelf, "-Wh", str(host))
    host_programs = run(readelf, "-Wl", str(host))
    host_dynamic = run(readelf, "-Wd", str(host))
    host_symbols = run(readelf, "-Ws", str(host))
    host_notes = run(readelf, "-Wn", str(host))

    provider_header = run(readelf, "-Wh", str(provider))
    provider_programs = run(readelf, "-Wl", str(provider))
    provider_dynamic = run(readelf, "-Wd", str(provider))
    provider_symbols = run(readelf, "-Ws", str(provider))
    provider_notes = run(readelf, "-Wn", str(provider))
    provider_disassembly = run(objdump, "-dr", str(provider))

    registry_header = run(readelf, "-Wh", str(registry))
    registry_programs = run(readelf, "-Wl", str(registry))
    registry_dynamic = run(readelf, "-Wd", str(registry))
    registry_symbols = run(readelf, "-Ws", str(registry))
    registry_notes = run(readelf, "-Wn", str(registry))

    pthread_bridge_header = run(readelf, "-Wh", str(pthread_bridge))
    pthread_bridge_programs = run(readelf, "-Wl", str(pthread_bridge))
    pthread_bridge_dynamic = run(readelf, "-Wd", str(pthread_bridge))
    pthread_bridge_symbols = run(readelf, "-Ws", str(pthread_bridge))
    pthread_bridge_relocs = run(readelf, "-Wr", str(pthread_bridge))
    pthread_bridge_notes = run(readelf, "-Wn", str(pthread_bridge))
    pthread_bridge_disassembly = run(objdump, "-dr", str(pthread_bridge))

    compat_header = run(readelf, "-Wh", str(compat))
    compat_programs = run(readelf, "-Wl", str(compat))
    compat_dynamic = run(readelf, "-Wd", str(compat))
    compat_symbols = run(readelf, "-Ws", str(compat))
    compat_notes = run(readelf, "-Wn", str(compat))
    compat_disassembly = run(objdump, "-dr", str(compat))

    app_loader_header = run(readelf, "-Wh", str(app_native_loader))
    app_loader_dynamic = run(readelf, "-Wd", str(app_native_loader))
    app_loader_symbols = run(readelf, "-Ws", str(app_native_loader))
    app_loader_notes = run(readelf, "-Wn", str(app_native_loader))
    app_loader_disassembly = run(objdump, "-dr", str(app_native_loader))

    native_loader_header = run(readelf, "-Wh", str(native_loader))
    native_loader_dynamic = run(readelf, "-Wd", str(native_loader))
    native_loader_symbols = run(readelf, "-Ws", str(native_loader))
    native_loader_notes = run(readelf, "-Wn", str(native_loader))
    native_loader_disassembly = run(objdump, "-dr", str(native_loader))

    palette_header = run(readelf, "-Wh", str(art_palette))
    palette_dynamic = run(readelf, "-Wd", str(art_palette))
    palette_symbols = run(readelf, "-Ws", str(art_palette))
    palette_notes = run(readelf, "-Wn", str(art_palette))
    palette_disassembly = run(objdump, "-dr", str(art_palette))

    plugin_dynamic = run(readelf, "-Wd", str(plugin))
    plugin_header = run(readelf, "-Wh", str(plugin))
    plugin_symbols = run(readelf, "-Ws", str(plugin))
    plugin_notes = run(readelf, "-Wn", str(plugin))

    require("Machine:                           AArch64" in host_header and
            "Type:                              DYN" in host_header,
            "stock host is not an AArch64 PIE")
    require("PIE" in host_dynamic and "BIND_NOW" in host_dynamic,
            "stock host must be NOW-bound PIE")
    require("[Requesting program interpreter: /lib/ld-musl-aarch64.so.1]" in
            host_programs,
            "stock host is not bound to the AArch64 Musl interpreter")
    require("Library soname: [appspawn-x]" in host_dynamic,
            "stock host SONAME mismatch")
    require("(RPATH)" not in host_dynamic and "(RUNPATH)" not in host_dynamic and
            "(TEXTREL)" not in host_dynamic,
            "stock host has load-path injection or text relocation")
    require(re.search(r"^\s*TLS\s+.*0x000030\s+R\s+0x10$",
                      host_programs, re.MULTILINE) is not None,
            "main-ELF 48-byte TLS reservation is absent")
    host_exports = dynamic_symbols(host_symbols, undefined=False)
    host_imports = dynamic_symbols(host_symbols, undefined=True)
    require(HOST_REQUIRED_EXPORTS <= host_exports,
            f"stock host export edge missing: {HOST_REQUIRED_EXPORTS - host_exports}")
    require(not (HOST_NATIVE_COMPAT_EXPORTS & host_exports),
            "MAIN runtime callbacks escaped the typed-table boundary")

    require("Machine:                           AArch64" in provider_header and
            "Type:                              DYN" in provider_header,
            "runtime provider is not an AArch64 DSO")
    require("Library soname: [libwestlake_android_runtime_provider.so]" in
            provider_dynamic, "runtime provider SONAME mismatch")
    require("BIND_NOW" in provider_dynamic and
            "(RPATH)" not in provider_dynamic and
            "(RUNPATH)" not in provider_dynamic and
            "(TEXTREL)" not in provider_dynamic,
            "runtime provider binding policy mismatch")
    require(re.search(r"^\s*TLS\s", provider_programs, re.MULTILINE) is None,
            "runtime provider must not own PT_TLS")
    provider_exports = dynamic_symbols(provider_symbols, undefined=False)
    require(exact_symbol_set(provider_exports, WLAR_EXPORTS),
            f"runtime provider export drift: {sorted(provider_exports)}")
    for removed_export in WLAR_EXPORTS:
        require(not exact_symbol_set(provider_exports - {removed_export},
                                     WLAR_EXPORTS),
                f"runtime provider removal mutant survived: {removed_export}")
    require(not exact_symbol_set(
                provider_exports | {"WLAR_UnapprovedExportMutant"},
                WLAR_EXPORTS),
            "runtime provider extra-export mutant survived")
    provider_imports = dynamic_symbols(provider_symbols, undefined=True)
    require(not (HOST_NATIVE_COMPAT_EXPORTS & provider_imports),
            "strict provider retained a direct MAIN-ELF undefined edge")
    require(not FORBIDDEN_SECURITY_SYMBOLS.search(provider_symbols),
            "runtime provider contains duplicate security operation")
    require("svc" not in provider_disassembly.lower(),
            "runtime provider contains a direct syscall instruction")

    require("Machine:                           AArch64" in registry_header and
            "Type:                              DYN" in registry_header,
            "thread-guard registry is not an AArch64 DSO")
    require("Library soname: [libwestlake_thread_guard_registry.so]" in
            registry_dynamic, "thread-guard registry SONAME mismatch")
    require("BIND_NOW" in registry_dynamic and
            "(RPATH)" not in registry_dynamic and
            "(RUNPATH)" not in registry_dynamic and
            "(TEXTREL)" not in registry_dynamic,
            "thread-guard registry binding policy mismatch")
    require(re.search(r"^\s*TLS\s", registry_programs, re.MULTILINE) is None,
            "thread-guard registry must not own PT_TLS")
    registry_exports = dynamic_symbols(registry_symbols, undefined=False)
    registry_imports = dynamic_symbols(registry_symbols, undefined=True)
    require(WLTG_EXPORTS <= registry_exports,
            f"thread-guard registry export edge missing: "
            f"{WLTG_EXPORTS - registry_exports}")
    require(not registry_imports,
            f"freestanding thread-guard registry has imports: "
            f"{sorted(registry_imports)}")
    require(not needed(registry_dynamic),
            "freestanding thread-guard registry unexpectedly has DT_NEEDED")

    require("Machine:                           AArch64" in
            pthread_bridge_header and
            "Type:                              DYN" in
            pthread_bridge_header,
            "pthread bridge is not an AArch64 DSO")
    require("Library soname: [libwestlake_bionic_pthread_bridge.so]" in
            pthread_bridge_dynamic,
            "pthread bridge SONAME mismatch")
    require("BIND_NOW" in pthread_bridge_dynamic and
            "(RPATH)" not in pthread_bridge_dynamic and
            "(RUNPATH)" not in pthread_bridge_dynamic and
            "(TEXTREL)" not in pthread_bridge_dynamic,
            "pthread bridge binding policy mismatch")
    require(not needed(pthread_bridge_dynamic),
            "freestanding pthread bridge unexpectedly has DT_NEEDED")
    require(re.search(r"\((?:INIT|FINI|INIT_ARRAY|FINI_ARRAY)\)",
                      pthread_bridge_dynamic) is None,
            "pthread bridge constructor/destructor dynamic tag forbidden")
    require(re.search(r"^\s*TLS\s", pthread_bridge_programs,
                      re.MULTILINE) is None,
            "pthread bridge must not own PT_TLS")
    require(not re.search(r"TLS|TLSDESC|TPREL|DTPREL",
                          pthread_bridge_relocs, re.IGNORECASE),
            "pthread bridge contains TLS relocations")
    require("tpidr_el0" not in pthread_bridge_disassembly.lower(),
            "pthread bridge reads TP directly")
    pthread_bridge_exports = dynamic_symbols(
        pthread_bridge_symbols, undefined=False
    ) - {"LIBC", "WESTLAKE_WLPB_1"}
    pthread_bridge_imports = dynamic_symbols(
        pthread_bridge_symbols, undefined=True
    )
    require(pthread_bridge_exports == PTHREAD_BRIDGE_EXPORTS,
            "pthread bridge export drift: "
            f"{sorted(pthread_bridge_exports)}")
    require(not pthread_bridge_imports,
            "pthread bridge has dynamic imports: "
            f"{sorted(pthread_bridge_imports)}")
    pthread_bridge_start = function_body(
        pthread_bridge_disassembly, "start_trampoline"
    )
    pthread_bridge_create = function_body(
        pthread_bridge_disassembly, "pthread_create"
    )
    pthread_bridge_install = function_body(
        pthread_bridge_disassembly, "WLPB_InstallHostOps"
    )
    require("blr" in pthread_bridge_start and
            "blr" in pthread_bridge_create and
            "ret" in pthread_bridge_install,
            "pthread bridge contains a missing/trivial core body")

    require("Machine:                           AArch64" in compat_header and
            "Type:                              DYN" in compat_header,
            "safe Bionic compatibility library is not an AArch64 DSO")
    require("Library soname: [libbionic_compat.so]" in compat_dynamic,
            "safe Bionic compatibility SONAME mismatch")
    require("BIND_NOW" in compat_dynamic and
            "(RPATH)" not in compat_dynamic and
            "(RUNPATH)" not in compat_dynamic and
            "(TEXTREL)" not in compat_dynamic,
            "safe Bionic compatibility binding policy mismatch")
    require(re.search(r"^\s*TLS\s", compat_programs, re.MULTILINE) is None,
            "safe Bionic compatibility library must not own PT_TLS")
    compat_exports = dynamic_symbols(compat_symbols, undefined=False)
    require("android_reset_stack_guards" in compat_exports,
            "safe Bionic compatibility reset trap missing")
    require("__stack_chk_guard" not in compat_symbols and
            "g_bionic_tls_guard" not in compat_symbols and
            "bionic_tls_establish_current_thread" not in compat_symbols,
            "safe Bionic compatibility library retained a competing guard owner")
    reset_body = function_body(compat_disassembly, "android_reset_stack_guards")
    require("_exit@plt" in reset_body and "\tret" not in reset_body,
            "android_reset_stack_guards must terminate, never return/fallback")

    require("Machine:                           AArch64" in app_loader_header and
            "Type:                              DYN" in app_loader_header,
            "app native loader is not an AArch64 DSO")
    require("Library soname: [libapp_native_loader.so]" in app_loader_dynamic,
            "app native loader SONAME mismatch")
    require("BIND_NOW" in app_loader_dynamic and
            "(RPATH)" not in app_loader_dynamic and
            "(RUNPATH)" not in app_loader_dynamic and
            "(TEXTREL)" not in app_loader_dynamic,
            "app native loader binding policy mismatch")
    app_loader_exports = dynamic_symbols(app_loader_symbols, undefined=False)
    require(app_loader_exports == APP_NATIVE_LOADER_EXPORTS,
            f"app native loader export drift: {sorted(app_loader_exports)}")
    app_loader_dlopen_body = function_body(app_loader_disassembly, "ANL_Dlopen")
    require("blr" in app_loader_dlopen_body and
            "dlopen_ns@plt" not in app_loader_dlopen_body,
            "ANL_Dlopen lost default-owner callback structure")
    app_loader_dlclose_body = function_body(
        app_loader_disassembly, "ANL_Dlclose")
    require("dlclose@plt" in app_loader_dlclose_body and
            ("blr" in app_loader_dlclose_body or
             "verify_runtime_ready" in app_loader_dlclose_body),
            "ANL_Dlclose lost READY callback-before-destructor structure")
    app_loader_create_body = function_body(
        app_loader_disassembly, "ANL_CreateDomain"
    )
    require("blr" in app_loader_create_body and
            "dlns_create2@plt" not in app_loader_create_body and
            "dlopen_ns@plt" not in app_loader_create_body and
            "dlsym@plt" not in app_loader_create_body and
            "dlns_create2" in host_imports and
            "dlopen_ns" in host_imports,
            "namespace ownership did not move intact to stock host")

    require("Machine:                           AArch64" in native_loader_header and
            "Type:                              DYN" in native_loader_header,
            "native loader is not an AArch64 DSO")
    require("Library soname: [libnativeloader.so]" in native_loader_dynamic,
            "native loader SONAME mismatch")
    require("BIND_NOW" in native_loader_dynamic and
            "(RPATH)" not in native_loader_dynamic and
            "(RUNPATH)" not in native_loader_dynamic and
            "(TEXTREL)" not in native_loader_dynamic,
            "native loader binding policy mismatch")
    native_loader_exports = dynamic_symbols(
        native_loader_symbols, undefined=False)
    require(native_loader_exports == NATIVE_LOADER_EXPORTS,
            f"native loader export drift: {sorted(native_loader_exports)}")
    require("dlopen@plt" not in native_loader_disassembly and
            "dlopen_ns@plt" not in native_loader_disassembly and
            "blr" in native_loader_disassembly,
            "native loader retained a direct dlopen fallback or lost its sealed callback")

    require("Machine:                           AArch64" in palette_header and
            "Type:                              DYN" in palette_header,
            "ART Palette provider is not an AArch64 DSO")
    require("Library soname: [libartpalette-system.so]" in palette_dynamic,
            "ART Palette SONAME mismatch")
    require(set(needed(palette_dynamic)) == {"libc.so", "liblog.so"} and
            "BIND_NOW" in palette_dynamic and
            "(RPATH)" not in palette_dynamic and
            "(RUNPATH)" not in palette_dynamic and
            "(TEXTREL)" not in palette_dynamic,
            "ART Palette dependency/binding policy mismatch")
    palette_exports = dynamic_symbols(palette_symbols, undefined=False)
    require(palette_exports == ART_PALETTE_EXPORTS,
            f"ART Palette export drift: {sorted(palette_exports)}")
    require(" UND setpriority" in palette_symbols and
            " UND getpriority" in palette_symbols and
            "setpriority@plt" in function_body(
                palette_disassembly, "PaletteSchedSetPriority") and
            "getpriority@plt" in function_body(
                palette_disassembly, "PaletteSchedGetPriority"),
            "ART Palette scheduler boundary became a host fake")

    plugin_imports = dynamic_symbols(plugin_symbols, undefined=True)
    plugin_exports = dynamic_symbols(plugin_symbols, undefined=False)
    require(plugin_exports == PLUGIN_EXPORTS,
            f"child plugin export drift: {sorted(plugin_exports)}")
    require(not (plugin_imports & WLAR_EXPORTS) and
            not (PLUGIN_STOCK_IMPORTS & plugin_imports) and
            not (HOST_NATIVE_COMPAT_EXPORTS & plugin_imports),
            "child plugin retained runtime-provider, MAIN, or stock ABI imports")
    require("BIND_NOW" in plugin_dynamic,
            "child plugin is not load-time fail-closed")
    require("Class:                             ELF64" in plugin_header and
            "Machine:                           AArch64" in plugin_header and
            "Type:                              DYN" in plugin_header,
            "child plugin is not an ELF64 AArch64 DSO")

    host_needed = needed(host_dynamic)
    provider_needed = needed(provider_dynamic)
    plugin_needed = needed(plugin_dynamic)
    compat_needed = needed(compat_dynamic)
    require("appspawn-x" not in provider_needed,
            "provider retained the OH-Musl-incompatible circular MAIN NEEDED")
    require("libwestlake_bionic_pthread_bridge.so" not in host_needed,
            "namespace-only pthread bridge leaked into host DT_NEEDED")
    require("libwestlake_android_runtime_provider.so" not in plugin_needed and
            "libwestlake_android_runtime_provider.so" not in host_needed and
            "libwestlake_thread_guard_registry.so" in host_needed,
            "parent/plugin retained provider DT_NEEDED or host lost registry edge")
    require("libbionic_compat.so" in provider_needed,
            "runtime provider lost same-generation safe compatibility DT_NEEDED")
    require("libapp_native_loader.so" in provider_needed and
            "ANL_InstallRuntimeGate" in provider_imports,
            "runtime provider lost same-generation pre-guest loader gate edge")
    require(provider_needed.count(
                "libwestlake_thread_guard_registry.so") == 1,
            "runtime provider lost the central JNI admission registry edge")
    require(HOST_WLTG_IMPORTS <= host_imports and
            HOST_WLTG_IMPORTS <= registry_exports,
            "stock host -> WLTG symbol edge is incomplete")
    require(not (plugin_imports & HOST_NATIVE_COMPAT_EXPORTS),
            "plugin retained undefined MAIN callback imports")

    base_manifest_path = FROZEN_PROVIDER_ROOT / "base-providers.sha256"
    repro_manifest_path = FROZEN_PROVIDER_ROOT / "base-providers-repro.sha256"
    input_manifest_path = FROZEN_PROVIDER_ROOT / "base-inputs.sha256"
    base_verification_path = FROZEN_PROVIDER_ROOT / "base-verification.json"
    independent_audit_path = FROZEN_PROVIDER_ROOT / "independent-audit.json"
    require(base_manifest_path.read_bytes() == repro_manifest_path.read_bytes(),
            "frozen provider manifests are not byte-identical")
    base_manifest = sha_manifest(base_manifest_path)
    base_verification = json.loads(base_verification_path.read_text())
    dynamic_atomic_base = FROZEN_PROVIDER_ROOT.name != "provider-v12"
    if dynamic_atomic_base:
        require(input_manifest_path.is_file() and
                base_verification.get("atomic_libart_tuple") is True and
                base_verification.get("runtime_start_zero_array_transport", "").startswith("stack-address/") and
                base_verification["byte_deterministic_runs"] == 2 and
                base_verification["broad_art_runtime_stub_absent"] is True and
                base_verification["product_activation"] is False,
                "atomic provider certificate policy drift")
    else:
        require(digest(base_manifest_path) == BASE_PROVIDER_MANIFEST_SHA256 and
                digest(repro_manifest_path) == BASE_PROVIDER_MANIFEST_SHA256,
                "frozen v12 provider/repro manifests are not the certified pair")
        require(digest(input_manifest_path) == BASE_INPUT_MANIFEST_SHA256,
                "frozen v12 source/tool input manifest drift")
        require(digest(independent_audit_path) == BASE_INDEPENDENT_AUDIT_SHA256,
                "frozen v12 independent audit drift")
        independent_audit = json.loads(independent_audit_path.read_text())
        require(independent_audit["dual_build"]["all_provider_bytes_identical"]
                is True and
                independent_audit["broad_art_runtime_stub"]["file_count"] == 0 and
                independent_audit["product_activation"] is False,
                "frozen v12 independent audit policy drift")
    base_providers = base_verification["providers"]
    certificate_runtime_members = set(base_providers) - ({"libart-compiler.so"} if dynamic_atomic_base else set())
    require(set(base_manifest) == certificate_runtime_members,
            "frozen provider manifest/certificate membership drift")
    for name, expected_sha in base_manifest.items():
        require(base_providers[name]["sha256"] == expected_sha,
                f"base certificate hash drift: {name}")

    old_compat_sha = base_manifest["libbionic_compat.so"]
    frozen_provider_files = {
        path.name: path
        for path in (FROZEN_PROVIDER_ROOT / "providers").glob("*.so")
    }
    expected_frozen_names = set(base_manifest) - {"libbionic_compat.so"}
    require(set(frozen_provider_files) == expected_frozen_names,
            "frozen provider set must contain exactly the non-compat runtime DSOs")
    for name, path in frozen_provider_files.items():
        require(digest(path) == base_manifest[name],
                f"frozen provider DSO drift: {name}")
    require(digest(compat) != old_compat_sha,
            "Route A reused the guard-conflicting v12 compatibility DSO")
    require(digest(app_native_loader) != base_manifest["libapp_native_loader.so"],
            "Route A reused the v12 app loader without the READY gate")
    require(digest(native_loader) != base_manifest["libnativeloader.so"],
            "Route A reused the frozen native loader without the sealed callback")
    require(digest(art_palette) != base_manifest["libartpalette-system.so"],
            "Route A reused the v12 host-fake ART Palette provider")

    final_provider_manifest = sha_manifest(provider_set_manifest)
    final_provider_directory = provider_set_manifest.parent / "providers"
    final_provider_files = {
        path.name: path for path in final_provider_directory.glob("*.so")
    }
    expected_final_provider_names = set(base_manifest) | {
        "libwestlake_thread_guard_registry.so",
        "libwestlake_bionic_pthread_bridge.so",
        "libshared_libz.z.so",
    }
    require(set(final_provider_manifest) == expected_final_provider_names and
            set(final_provider_files) == expected_final_provider_names and
            len(final_provider_manifest) == len(base_manifest) + 3,
            "final same-generation provider-set membership drift")
    for name, expected_sha in final_provider_manifest.items():
        require(digest(final_provider_files[name]) == expected_sha,
                f"final provider-set manifest mismatch: {name}")

    identity = env_contract(PLUGIN_ROOT / "r45_adapter_identity.env")
    dynamic_root_contract = {
        "liboh_adapter_bridge.so": (
            "WLAR_ADAPTER_BRIDGE_SHA256_HEX",
            "WLAR_ADAPTER_BRIDGE_BUILD_ID_HEX",
        ),
        "liboh_android_runtime.so": (
            "WLAR_ANDROID_RUNTIME_SHA256_HEX",
            "WLAR_ANDROID_RUNTIME_BUILD_ID_HEX",
        ),
    }
    dynamic_root_files: dict[str, Path] = {}
    for name, (sha_key, build_id_key) in dynamic_root_contract.items():
        path = (R45_DYNAMIC_ROOTS / name).resolve(strict=True)
        require(digest(path) == identity.get(sha_key),
                f"R45 dynamic-root SHA mismatch: {name}")
        notes = run(readelf, "-Wn", str(path))
        require(build_id(notes) == identity.get(build_id_key),
                f"R45 dynamic-root Build-ID mismatch: {name}")
        dynamic_root_files[name] = path

    adapter_bridge_dynamic = run(
        readelf, "-Wd", str(dynamic_root_files["liboh_adapter_bridge.so"])
    )
    adapter_bridge_symbols = run(
        readelf, "--dyn-syms", "-W",
        str(dynamic_root_files["liboh_adapter_bridge.so"]),
    )
    adapter_bridge_needed = needed(adapter_bridge_dynamic)
    adapter_bridge_imports = dynamic_symbols(
        adapter_bridge_symbols, undefined=True
    )
    require("libskia_canvaskit.z.so" in adapter_bridge_needed,
            "adapter bridge lost direct Skia DT_NEEDED edge")
    require("_ZN12SkPngDecoder5IsPngEPKvm" in adapter_bridge_imports,
            "adapter bridge SkPngDecoder::IsPng import drift")

    arm64_deployment_artifacts = {
        "appspawn-x-stock": host,
        "libwestlake_android_child.z.so": plugin,
        "libwestlake_android_runtime_provider.so": provider,
    }
    arm64_deployment_artifacts.update({
        f"providers/{name}": path
        for name, path in final_provider_files.items()
    })
    arm64_deployment_artifacts.update({
        f"dynamic-roots/{name}": path
        for name, path in dynamic_root_files.items()
    })
    for label, path in arm64_deployment_artifacts.items():
        require_arm64_elf(readelf, path, label)

    for key in ("WLAR_ADAPTER_BRIDGE_PATH", "WLAR_ANDROID_RUNTIME_PATH"):
        require(identity.get(key, "").startswith("/system/android/lib64/") and
                "/../" not in identity[key],
                f"R45 64-bit deployment path drift: {key}")
    stock_host_source = (
        PLUGIN_ROOT / "src/westlake_stock_host_main.c"
    ).read_text(encoding="utf-8")
    require("/system/lib64/appspawn/libwestlake_android_child.z.so" in
            stock_host_source,
            "R45 child plugin is not pinned to the 64-bit appspawn directory")
    require("stock_long_proc_name[APP_LEN_PROC_NAME]" in stock_host_source and
            "StartSpawnService(&start_argument, sizeof(stock_long_proc_name)" in
            stock_host_source and
            "argument_span" not in stock_host_source,
            "stock host still depends on init argv span for long proc name")
    route_build = (
        PLUGIN_ROOT / "build_route_a_generation_in_container.sh"
    ).read_text(encoding="utf-8")
    target_build = (
        PLUGIN_ROOT / "build_target_in_container.sh"
    ).read_text(encoding="utf-8")
    require("TARGET=aarch64-linux-ohos" in route_build and
            "--target=aarch64-linux-ohos" in target_build and
            "aarch64-linux-ohos" in route_build,
            "R45 build target is not pinned to aarch64-linux-ohos")
    require(final_provider_manifest["libbionic_compat.so"] == digest(compat) and
            final_provider_manifest[
                "libwestlake_bionic_pthread_bridge.so"] ==
            digest(pthread_bridge) and
            final_provider_manifest["libapp_native_loader.so"] ==
            digest(app_native_loader) and
            final_provider_manifest["libnativeloader.so"] ==
            digest(native_loader) and
            final_provider_manifest["libwestlake_thread_guard_registry.so"] ==
            digest(registry) and
            final_provider_manifest["libartpalette-system.so"] ==
            digest(art_palette),
            "rebuilt same-generation provider identity mismatch")
    for name in set(base_manifest) - {
        "libbionic_compat.so", "libapp_native_loader.so",
        "libartpalette-system.so", "libnativeloader.so",
    }:
        require(final_provider_manifest[name] == base_manifest[name],
                f"unchanged base provider byte drift: {name}")
    require("libart_runtime_stubs.so" not in final_provider_manifest,
            "broad ART runtime stub entered final provider-set manifest")

    initial_provider_closure = provider_closure(provider_needed, base_providers)
    expected_initial_closure = (
        set(base_manifest) - {"libartpalette-system.so"}
    )
    require(initial_provider_closure == expected_initial_closure,
            "runtime provider recursive DSO closure drift: "
            f"missing={sorted(expected_initial_closure - initial_provider_closure)} "
            f"extra={sorted(initial_provider_closure - expected_initial_closure)}")
    all_base_needed = {
        str(dependency)
        for metadata in base_providers.values()
        for dependency in metadata["needed"]
    }
    require("libart_runtime_stubs.so" not in provider_needed and
            "libart_runtime_stubs.so" not in all_base_needed and
            "libart_runtime_stubs.so" not in frozen_provider_files,
            "broad ART runtime stub entered the final provider closure")
    external_provider_needed = all_base_needed - set(base_providers)
    certified_external_needed = CERTIFIED_EXTERNAL_NEEDED
    require(external_provider_needed == certified_external_needed,
            "external provider dependency closure drift")
    for external_name in certified_external_needed - {"libc.so"}:
        require(any(PLUGIN_ROOT.glob(f"frozen/**/{external_name}")),
                f"external provider dependency is not project-local: "
                f"{external_name}")

    # Adapter-owned closure, independent of normal libc/OH/AOSP DT_NEEDED:
    # parent and plugin are provider-free. The specialized child validates and
    # explicitly maps the sealed provider closure with local visibility.
    unresolved_adapter_edges = (
        (WLAR_EXPORTS - provider_exports) |
        (HOST_REQUIRED_EXPORTS - host_exports) |
        (HOST_WLTG_IMPORTS - registry_exports) |
        ({"ANL_InstallRuntimeGate"} - app_loader_exports)
    )
    require(not unresolved_adapter_edges,
            f"unresolved adapter edges: {sorted(unresolved_adapter_edges)}")

    legacy_child_entry = function_body(
        provider_disassembly, "WLAR_EnterAndroidAfterStockSpecialization")
    child_entry = function_body(
        provider_disassembly, "WLAR_PrepareA02PrerequisiteBundleV2")
    capture_audit = function_body(
        provider_disassembly,
        "_ZN12_GLOBAL__N_120CaptureAuditSnapshotEPvPN19wlar_child_sequence"
        "21LosslessAuditSnapshotE")
    commit_audit = function_body(
        provider_disassembly,
        "_ZN12_GLOBAL__N_119CommitAuditSnapshotEPv")
    constructors = function_body(
        provider_disassembly, "_ZN12_GLOBAL__N_112ConstructorsEPv")
    create_vm = function_body(
        provider_disassembly, "_ZN12_GLOBAL__N_12VmEPv")
    complete_jni = function_body(
        provider_disassembly, "_ZN12_GLOBAL__N_13JniEPv")
    prepare_callback = function_body(
        provider_disassembly, "WLAR_HostServicesPrepareMain")
    audit_callback = function_body(
        provider_disassembly, "WLAR_HostServicesGetAuditSnapshot")
    prepare_main_offset = capture_audit.find("WLAR_HostServicesPrepareMain")
    audit_snapshot_offset = capture_audit.find(
        "WLAR_HostServicesGetAuditSnapshot")
    mark_consumed_offset = commit_audit.find(
        "WLAR_HostServicesMarkChildConsumed")
    loader_ready_offset = commit_audit.find("WLAR_LoaderPhaseMarkChildReady")
    sequence_offset = child_entry.find("wlar_child_sequence3Run")
    call_edges = {
        "parent_provider_entries_absent":
            "WLAR_ServerPreload" not in provider_symbols and
            "WLAR_ZygotePreFork" not in provider_symbols and
            "WLAR_ZygotePostForkParent" not in provider_symbols,
        "legacy_child_entry_fail_closed":
            "mov\tw0, #-3007" in legacy_child_entry and
            "ret" in legacy_child_entry,
        "specialized_child_constructor_helper":
            "ANL_InstallRuntimeGate@plt" in constructors,
        "specialized_child_vm_helper":
            "AppSpawnXRuntime7startVmEv" in create_vm,
        "specialized_child_jni_helper":
            "AppSpawnXRuntime7preloadEv" in complete_jni,
        "specialized_child_sequence_entry":
            sequence_offset >= 0,
        "host_callback_prepare_and_audit_indirect":
            "blr" in prepare_callback and "blr" in audit_callback,
        "prepare_before_audit_snapshot":
            prepare_main_offset >= 0 and audit_snapshot_offset >= 0 and
            prepare_main_offset < audit_snapshot_offset,
        "receipt_consumed_before_loader_ready":
            mark_consumed_offset >= 0 and loader_ready_offset >= 0 and
            mark_consumed_offset < loader_ready_offset,
    }
    require(all(call_edges.values()),
            f"binary call-order edge missing: {call_edges}")

    input_sha = digest(inputs)
    require(provider.read_bytes().count(bytes.fromhex(input_sha)) == 1,
            "provider does not contain exactly one frozen generation identity")
    plugin_sha = digest(plugin)
    plugin_build_id = build_id(plugin_notes)
    require(plugin_sha.encode("ascii") in host.read_bytes() and
            plugin_build_id.encode("ascii") in host.read_bytes(),
            "MAIN does not bind the exact plugin SHA/Build-ID")
    input_document = json.loads(inputs.read_text())
    require(input_document["provider_security_operations_mask"] == 0 and
            input_document["security_operation_owner"] ==
            "stock_OH_appspawn_only",
            "input closure security ownership drift")

    result = {
        "status": "PASS",
        "classification": "route_A_final_link_generation",
        "deterministic_builds": 2,
        "stock_host_final_link": True,
        "runtime_provider_symbols_implemented": True,
        "missing_runtime_provider_symbols": [],
        "unresolved_adapter_symbol_edges": [],
        "unresolved_transitive_provider_symbols": [],
        "strict_transitive_shlib_final_link": True,
        "board_architecture": "AArch64",
        "target_triple": "aarch64-linux-ohos",
        "elf_class": "ELF64",
        "little_endian": True,
        "arm64_deployment_elf_count": len(arm64_deployment_artifacts),
        "arm64_deployment_members": sorted(arm64_deployment_artifacts),
        "elf32_artifacts": [],
        "lib64_deployment_paths_verified": True,
        "aarch64_musl_interpreter_verified": True,
        "external_dynamic_roots_local_verified": True,
        "adapter_bridge_sha256": digest(
            dynamic_root_files["liboh_adapter_bridge.so"]),
        "adapter_bridge_build_id": identity[
            "WLAR_ADAPTER_BRIDGE_BUILD_ID_HEX"],
        "adapter_bridge_needed": adapter_bridge_needed,
        "adapter_bridge_skia_edge_verified": True,
        "android_runtime_sha256": digest(
            dynamic_root_files["liboh_android_runtime.so"]),
        "android_runtime_build_id": identity[
            "WLAR_ANDROID_RUNTIME_BUILD_ID_HEX"],
        "provider_repeats_security_specialization": False,
        "security_operation_owner": "stock_OH_appspawn_only",
        "stock_host_sha256": digest(host),
        "stock_host_build_id": build_id(host_notes),
        "runtime_provider_sha256": digest(provider),
        "runtime_provider_build_id": build_id(provider_notes),
        "thread_guard_registry_sha256": digest(registry),
        "thread_guard_registry_build_id": build_id(registry_notes),
        "pthread_bridge_sha256": digest(pthread_bridge),
        "pthread_bridge_build_id": build_id(pthread_bridge_notes),
        "safe_bionic_compat_sha256": digest(compat),
        "safe_bionic_compat_build_id": build_id(compat_notes),
        "app_native_loader_sha256": digest(app_native_loader),
        "app_native_loader_build_id": build_id(app_loader_notes),
        "native_loader_sha256": digest(native_loader),
        "native_loader_build_id": build_id(native_loader_notes),
        "art_palette_sha256": digest(art_palette),
        "art_palette_build_id": build_id(palette_notes),
        "child_plugin_sha256": digest(plugin),
        "child_plugin_build_id": plugin_build_id,
        "route_a_input_generation_sha256": input_sha,
        "runtime_provider_exports": sorted(provider_exports),
        "stock_host_required_exports": sorted(HOST_REQUIRED_EXPORTS),
        "stock_host_needed": host_needed,
        "child_plugin_needed": plugin_needed,
        "runtime_provider_needed": provider_needed,
        "thread_guard_registry_needed": needed(registry_dynamic),
        "pthread_bridge_needed": needed(pthread_bridge_dynamic),
        "safe_bionic_compat_needed": compat_needed,
        "same_generation_needed_edges": {
            "stock_host_to_runtime_provider":
                "libwestlake_android_runtime_provider.so" in host_needed,
            "child_plugin_to_runtime_provider":
                "libwestlake_android_runtime_provider.so" in plugin_needed,
            "stock_host_to_thread_guard_registry": True,
            "runtime_provider_to_safe_bionic_compat": True,
            "runtime_provider_to_app_native_loader": True,
            "runtime_provider_to_jni_admission_registry": True,
            "app_loader_namespace_to_pthread_bridge": True,
        },
        "frozen_provider_base_manifest_sha256":
            digest(base_manifest_path),
        "frozen_provider_input_manifest_sha256":
            digest(input_manifest_path),
        "frozen_provider_independent_audit_sha256":
            (None if dynamic_atomic_base else BASE_INDEPENDENT_AUDIT_SHA256),
        "frozen_provider_base_count": len(base_manifest),
        "frozen_provider_copied_non_compat_count": len(frozen_provider_files),
        "final_provider_set_manifest_sha256": digest(provider_set_manifest),
        "final_provider_set_count": len(final_provider_manifest),
        "unchanged_v12_provider_count": len(base_manifest) - 4,
        "rebuilt_provider_members": [
            "libapp_native_loader.so",
            "libartpalette-system.so",
            "libbionic_compat.so",
            "libnativeloader.so",
            "libwestlake_bionic_pthread_bridge.so",
            "libwestlake_thread_guard_registry.so",
        ],
        "initial_recursive_provider_closure":
            sorted(initial_provider_closure),
        "initial_recursive_provider_count": len(initial_provider_closure),
        "external_provider_needed": sorted(external_provider_needed),
        "initial_global_scope_excludes_libartpalette_system": True,
        "broad_art_runtime_stub_absent": True,
        "guard_conflicting_v12_compat_reused": False,
        "ungated_v12_app_native_loader_reused": False,
        "host_fake_v12_art_palette_reused": False,
        "real_art_palette_priority_provider_packaged": True,
        "namespace_pthread_bridge_product_integrated": True,
        "central_jni_attach_product_integrated": True,
        "binary_call_edges": call_edges,
        "main_elf_tls_reservation": True,
        "wltg_canonical_bionic_process_guard_equals_all_admitted_slot5":
            False,
        "receipt_bound_main_admission_integrated": True,
        "versioned_host_callback_table_installed_once": True,
        "runtime_provider_direct_main_undefined_edges": [],
        "lossless_audit_snapshot_checked_before_guest_entry": True,
        "pre_guest_loader_ready_gate_integrated": True,
        "guest_loader_open_close_ready_gates_integrated": True,
        "activation_blocker":
            "device activation and truly-cold startup evidence are absent",
        "stubbed_unused_features": [
            "OH prefork process cache",
            "OH trace emission",
            "DFX stack dump catcher",
        ],
        "product_activation": False,
        "device_verified": False,
        "unity_loaded": False,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
