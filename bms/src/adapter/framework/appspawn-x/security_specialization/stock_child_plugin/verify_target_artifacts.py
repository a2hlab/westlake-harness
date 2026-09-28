#!/usr/bin/env python3
"""ELF gate for the route-A stock-host/plugin target ABI fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess


PLUGIN_EXPORTS = {
    "WLASC_GetContractV1",
    "WLASC_InstallStockHostServicesV1",
}
STOCK_PLUGIN_IMPORTS = {
    "AddAppSpawnHook",
    "AddServerStageHook",
    "CheckAppSpawnMsgFlag",
    "GetAppSpawnMsgInfo",
    "RegChildLooper",
}
FORBIDDEN_RUNTIME_PLUGIN_IMPORTS = {
    "WLAR_GetRuntimeIdentity",
    "WLAR_ServerPreload",
    "WLAR_InstallHostRuntimeServices",
    "WLAR_ZygotePreFork",
    "WLAR_ZygotePostForkParent",
    "WLAR_EnterAndroidAfterStockSpecialization",
}
APPROVED_LOCAL_LOADER_IMPORTS = {
    "__errno_location",
    "_exit",
    "close",
    "dlns_create2",
    "dlns_init",
    "dladdr",
    "dlerror",
    "dlopen",
    "dlsym",
    "fclose",
    "fgets",
    "fopen",
    "free",
    "fstat",
    "getpid",
    "getppid",
    # getrandom/strtoull come from westlake_generation_identity_ops.c (nonce
    # material and the decimal generation counter); sched_yield comes from the
    # child_hook_table_v1.c publication spin.  All three are linked into the
    # plugin by build_target_in_container.sh, so they belong to the libc-only
    # local-loader surface this set describes.
    "getrandom",
    "malloc",
    "memcmp",
    "memcpy",
    "memset",
    "open",
    "pread",
    "read",
    "realpath",
    "sched_yield",
    "snprintf",
    "sscanf",
    "strchr",
    "strcmp",
    "strlen",
    "strrchr",
    "strtoull",
    "write",
}
HOST_CALLBACK_IMPORTS = {
    "westlake_native_compat_prepare_parent_runtime",
    "westlake_native_compat_verify_parent_preload_thread_ready",
    "westlake_native_compat_prepare_main_thread",
    "westlake_native_compat_verify_current_thread_ready",
    "westlake_native_compat_get_audit_snapshot",
}
HOST_STOCK_IMPORTS = {
    "AppSpawnModuleMgrInstall",
    "InitCommonEnv",
    "StartSpawnService",
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


def tool(executable: pathlib.Path, *arguments: str) -> str:
    completed = subprocess.run(
        [str(executable), *arguments],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout


def symbol_name(line: str) -> str | None:
    fields = line.split()
    if len(fields) < 8 or not fields[0].rstrip(":").isdigit():
        return None
    return fields[-1].split("@", 1)[0]


def dynamic_symbols(symbols: str, undefined: bool) -> set[str]:
    result: set[str] = set()
    in_dynamic = False
    for line in symbols.splitlines():
        if line.startswith("Symbol table '.dynsym'"):
            in_dynamic = True
            continue
        if line.startswith("Symbol table '") and ".dynsym" not in line:
            in_dynamic = False
        if not in_dynamic:
            continue
        name = symbol_name(line)
        if not name:
            continue
        is_undefined = " UND " in f" {line} "
        if is_undefined == undefined:
            if undefined or (" GLOBAL " in f" {line} " and
                             " DEFAULT " in f" {line} "):
                result.add(name)
    result.discard("")
    return result


def all_undefined(symbols: str) -> set[str]:
    result: set[str] = set()
    for line in symbols.splitlines():
        if " UND " not in f" {line} ":
            continue
        name = symbol_name(line)
        if name:
            result.add(name)
    return result


def needed(dynamic: str) -> set[str]:
    return set(re.findall(r"\(NEEDED\).*?\[([^]]+)\]", dynamic))


def explicit_child_loader_source_fails_closed(plugin: str, loader: str,
                                              target_build: str,
                                              route_build: str) -> bool:
    required_plugin = (
        "WLASC_ReceiptConsume",
        "PublishChildHookTable(&request)",
        "WLSCPL_LoadSealedProvider(",
        "load_result.provider_handle, &child_services",
        'resolver(provider_handle,',
        '"WLAR_InstallHostRuntimeServices"',
        '"WLAR_EnterAndroidAfterStockSpecialization"',
    )
    required_loader = (
        "RTLD_NOW | RTLD_LOCAL",
        '"/proc/self/fd/%lld"',
        "dlopen(descriptor_path, flags)",
        "ComputeManifestDigest(request->manifest",
        "ops->mapped_identity_matches(",
        "WLSCPL_STATE_FAILED_AFTER_CONSTRUCTORS",
    )
    forbidden = (
        "RTLD_DEFAULT",
        "RTLD_NEXT",
        "RTLD_GLOBAL",
        "dlclose(",
    )
    if (not all(item in plugin for item in required_plugin) or
            not all(item in loader for item in required_loader) or
            any(item in plugin or item in loader for item in forbidden)):
        return False
    child = plugin[plugin.index("static int WestlakeRunAndroidChild("):
                   plugin.index("static int WestlakeServerPrepareInert(")]
    target_link = target_build[target_build.index("build_pass()"):
                               target_build.index("build_pass pass1")]
    host_link = route_build[route_build.index("build_stock_host()"):
                            route_build.index("build_stock_host pass1")]
    return (
        child.index("WLASC_ReceiptConsume") <
        child.index("PublishChildHookTable(&request)") <
        child.index("LoadSealedProviderAfterHooks(&request, &receipt)") and
        "-lwestlake_android_runtime_provider" not in target_link and
        "-lwestlake_android_runtime_provider" not in host_link)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--plugin", required=True)
    parser.add_argument("--second-plugin", required=True)
    parser.add_argument("--host-object", required=True)
    parser.add_argument("--second-host-object", required=True)
    parser.add_argument("--service-object", required=True)
    parser.add_argument("--second-service-object", required=True)
    parser.add_argument("--readelf", required=True)
    parser.add_argument("--objdump", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    root = pathlib.Path(args.project_root).resolve(strict=True)
    plugin = under(pathlib.Path(args.plugin), root)
    second_plugin = under(pathlib.Path(args.second_plugin), root)
    host = under(pathlib.Path(args.host_object), root)
    second_host = under(pathlib.Path(args.second_host_object), root)
    service = under(pathlib.Path(args.service_object), root)
    second_service = under(pathlib.Path(args.second_service_object), root)
    readelf = under(pathlib.Path(args.readelf), root)
    objdump = under(pathlib.Path(args.objdump), root)
    report = pathlib.Path(args.report).resolve()
    try:
        report.relative_to(root)
    except ValueError as error:
        raise RuntimeError(f"report escapes project root: {report}") from error
    plugin_root = root / (
        "adapter/framework/appspawn-x/security_specialization/stock_child_plugin"
    )
    plugin_source = (plugin_root / "src/westlake_android_child_plugin.c").read_text()
    loader_source = (plugin_root / "src/sealed_child_provider_loader.c").read_text()
    target_build = (plugin_root / "build_target_in_container.sh").read_text()
    route_build = (
        plugin_root / "build_route_a_generation_in_container.sh"
    ).read_text()

    require(digest(plugin) == digest(second_plugin),
            "plugin target builds are not byte-identical")
    require(digest(host) == digest(second_host),
            "stock-host entry objects are not byte-identical")
    require(digest(service) == digest(second_service),
            "patched stock service objects are not byte-identical")

    headers = tool(readelf, "-W", "-h", str(plugin))
    programs = tool(readelf, "-W", "-l", str(plugin))
    dynamic = tool(readelf, "-W", "-d", str(plugin))
    sections = tool(readelf, "-W", "-S", str(plugin))
    symbols = tool(readelf, "-W", "-s", str(plugin))
    relocations = tool(readelf, "-W", "-r", str(plugin))
    notes = tool(readelf, "-W", "-n", str(plugin))
    disassembly = tool(objdump, "-d", str(plugin))

    require("Machine:                           AArch64" in headers,
            "plugin is not AArch64")
    require("Type:                              DYN" in headers,
            "plugin is not a DSO")
    require("Library soname: [libwestlake_android_child.z.so]" in dynamic,
            "plugin SONAME mismatch")
    require("(BIND_NOW)" in dynamic or " NOW" in dynamic,
            "plugin must eagerly bind its local loader imports")
    require("Build ID:" in notes, "plugin build ID missing")
    require(not re.search(r"^\s*TLS\s", programs, re.MULTILINE),
            "plugin PT_TLS is forbidden")
    require(not re.search(r"\.tdata|\.tbss", sections),
            "plugin TLS section is forbidden")
    require(".init_array" not in sections and "(INIT_ARRAY)" not in dynamic,
            "plugin must be inert before MAIN installs typed services")
    require("(RPATH)" not in dynamic and "(RUNPATH)" not in dynamic,
            "plugin search path is forbidden")
    require("(TEXTREL)" not in dynamic, "plugin textrel is forbidden")
    require(dynamic_symbols(symbols, False) & PLUGIN_EXPORTS == PLUGIN_EXPORTS,
            "plugin contract export missing")
    wlasc_exports = {name for name in dynamic_symbols(symbols, False)
                     if name.startswith("WLASC_")}
    require(wlasc_exports == PLUGIN_EXPORTS,
            f"plugin export set mismatch: {wlasc_exports}")
    imports = dynamic_symbols(symbols, True)
    require(imports == APPROVED_LOCAL_LOADER_IMPORTS and
            not (imports & FORBIDDEN_RUNTIME_PLUGIN_IMPORTS) and
            not (imports & STOCK_PLUGIN_IMPORTS) and
            not (imports & HOST_CALLBACK_IMPORTS),
            f"plugin local-loader import set drift: {sorted(imports)}")
    require("libwestlake_android_runtime_provider.so" not in needed(dynamic),
            "plugin retained runtime-provider DT_NEEDED")
    require(explicit_child_loader_source_fails_closed(
                plugin_source, loader_source, target_build, route_build),
            "explicit specialized-child loader topology is not fail-closed")
    for mutant in (
        "WLASC_ReceiptConsume",
        "PublishChildHookTable(&request)",
        "WLSCPL_LoadSealedProvider(",
        "RTLD_NOW | RTLD_LOCAL",
        '"/proc/self/fd/%lld"',
        "ComputeManifestDigest(request->manifest",
        "ops->mapped_identity_matches(",
    ):
        # Replace every occurrence, not just the first.  The loader carries a
        # compile-time mutation switch (WLSCPL_MUTANT_SKIP_MAPPED_INODE_BIND),
        # so a construct such as ops->mapped_identity_matches( appears once in
        # the mutant branch and once in the real one.  Mutating only the first
        # left the real call site intact and the topology check kept reporting
        # fail-closed, which reads as "the mutant survived".
        require(not explicit_child_loader_source_fails_closed(
                    plugin_source.replace(mutant, "mutated"),
                    loader_source.replace(mutant, "mutated"),
                    target_build, route_build),
                f"explicit child-loader mutant survived: {mutant}")
    require(not re.search(r"TLS|TLSDESC|TPREL|DTPREL", relocations,
                          flags=re.IGNORECASE),
            "plugin TLS relocation forbidden")
    require("svc" not in disassembly.lower(),
            "plugin direct syscall instruction forbidden")
    require(not re.search(
        r"\b(?:mount|umount2|unshare|chroot|pivot_root|setcon|setexeccon|"
        r"SetSelfTokenID|setresuid|setresgid|setgroups)\b", symbols
    ), "plugin duplicates stock security operation")

    host_headers = tool(readelf, "-W", "-h", str(host))
    host_symbols = tool(readelf, "-W", "-s", str(host))
    host_relocations = tool(readelf, "-W", "-r", str(host))
    require("Machine:                           AArch64" in host_headers,
            "stock-host entry is not AArch64")
    require("Type:                              REL" in host_headers,
            "stock-host entry must remain a final-link input")
    require(re.search(r"\bmain$", host_symbols, re.MULTILINE) is not None,
            "stock-host entry does not define main")
    host_imports = all_undefined(host_symbols)
    require(HOST_STOCK_IMPORTS <= host_imports,
            f"stock-host core edge missing: {HOST_STOCK_IMPORTS - host_imports}")
    require("AppSpawnModuleMgrInstall" in host_relocations and
            "StartSpawnService" in host_relocations,
            "stock-host entry relocation edge missing")
    require(not re.search(
        r"\b(?:mount|umount2|unshare|chroot|pivot_root|setcon|setexeccon|"
        r"SetSelfTokenID|setresuid|setresgid|setgroups)\b", host_symbols
    ), "stock-host main duplicates stock security operation")

    service_headers = tool(readelf, "-W", "-h", str(service))
    service_symbols = tool(readelf, "-W", "-s", str(service))
    service_relocations = tool(readelf, "-W", "-r", str(service))
    require("Machine:                           AArch64" in service_headers and
            "Type:                              REL" in service_headers,
            "patched stock service is not an AArch64 final-link input")
    service_imports = all_undefined(service_symbols)
    require({"AppSpawnHookExecute", "AppSpawnProcessMsg"} <=
            service_imports,
            "patched service lost stock stage/fork edges")
    require("AppSpawnHookExecute" in service_relocations and
            "AppSpawnProcessMsg" in service_relocations,
            "patched service relocation edges missing")

    result = {
        "status": "PASS",
        "classification": "route_A_target_ABI_fixture",
        "product_activation": False,
        "device_verified": False,
        "deterministic_builds": 2,
        "plugin_sha256": digest(plugin),
        "stock_host_entry_sha256": digest(host),
        "patched_stock_service_sha256": digest(service),
        "plugin_exports": sorted(PLUGIN_EXPORTS),
        "stock_plugin_imports": sorted(STOCK_PLUGIN_IMPORTS),
        "stock_plugin_imports_eliminated": True,
        "host_callback_imports": [],
        "runtime_provider_imports": [],
        "runtime_provider_dt_needed": False,
        "approved_local_loader_imports": sorted(APPROVED_LOCAL_LOADER_IMPORTS),
        "stock_host_core_imports": sorted(HOST_STOCK_IMPORTS),
        "stock_host_final_link": False,
        "candidate_parent_prefork_fail_closed_source": True,
        "candidate_parent_prefork_service_target_compiled": True,
        "security_operation_owner": "stock_OH_appspawn_only",
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
