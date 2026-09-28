#!/usr/bin/env python3
"""Fail-closed ELF audit for the frozen appspawn-x generation.

This verifies only build/static claims.  It deliberately does not label the
artifacts device_verified and does not claim that Bionic TLS slot 5 semantics
exist. The live source now additionally requires that any refreshed generation
carry an admitted main-owned prepare entry point in appspawn-x itself; compat
must still contain no TP-relative writer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

EXPECTED_MAIN_PREPARE_SYMBOLS = (
    "westlake_native_compat_prepare_main_thread",
    "WestLakeNativeCompatPrepareMainThread",
)


class GateError(RuntimeError):
    pass


def run(tool: str, *args: str) -> str:
    proc = subprocess.run(
        [tool, *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if proc.returncode != 0:
        raise GateError(
            f"tool failed ({proc.returncode}): {tool} {' '.join(args)}\n{proc.stderr}"
        )
    return proc.stdout


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateError(message)


def build_id(readelf: str, path: pathlib.Path) -> str:
    match = re.search(r"Build ID:\s*([0-9a-fA-F]+)", run(readelf, "-nW", str(path)))
    require(match is not None, f"missing Build-ID: {path}")
    return match.group(1).lower()


def dynamic(readelf: str, path: pathlib.Path) -> tuple[list[str], str | None, str]:
    output = run(readelf, "-dW", str(path))
    needed = re.findall(r"\(NEEDED\).*?\[([^]]+)\]", output)
    sonames = re.findall(r"\(SONAME\).*?\[([^]]+)\]", output)
    require(len(sonames) <= 1, f"multiple SONAME entries: {path}")
    return needed, sonames[0] if sonames else None, output


def header(readelf: str, path: pathlib.Path) -> str:
    output = run(readelf, "-hW", str(path))
    require(re.search(r"Machine:\s*AArch64", output) is not None, f"not AArch64: {path}")
    return output


def assert_no_unsafe_dynamic_tags(dynamic_output: str, path: pathlib.Path) -> None:
    for tag in ("RPATH", "RUNPATH", "TEXTREL"):
        require(f"({tag})" not in dynamic_output, f"forbidden {tag}: {path}")


def assert_same_build_id(readelf: str, stripped: pathlib.Path, sidecar: pathlib.Path) -> str:
    stripped_id = build_id(readelf, stripped)
    sidecar_id = build_id(readelf, sidecar)
    require(stripped_id == sidecar_id, f"Build-ID sidecar mismatch: {stripped} vs {sidecar}")
    require(len(stripped_id) == 40, f"Build-ID is not sha1: {stripped}")
    return stripped_id


def elf_candidates(root: pathlib.Path) -> list[pathlib.Path]:
    result: list[pathlib.Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name.endswith(".unstripped"):
            continue
        if "sp" in path.parts:
            continue
        try:
            with path.open("rb") as stream:
                if stream.read(4) == b"\x7fELF":
                    result.append(path)
        except OSError:
            pass
    return result


def provider_map(
    readelf: str, roots: list[pathlib.Path]
) -> dict[str, list[pathlib.Path]]:
    providers: dict[str, list[pathlib.Path]] = {}
    seen: set[pathlib.Path] = set()
    for root in roots:
        for path in elf_candidates(root):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            try:
                _, soname, _ = dynamic(readelf, path)
            except GateError:
                continue
            # A few current AOSP adapter outputs intentionally carry no
            # DT_SONAME.  In that case the loader identity is the filename
            # recorded by the consumer's DT_NEEDED entry.
            provider_name = soname if soname else path.name
            providers.setdefault(provider_name, []).append(path)
    return providers


def verify_direct_needed(
    needed: list[str], providers: dict[str, list[pathlib.Path]], consumer: pathlib.Path
) -> None:
    for name in needed:
        matches = providers.get(name, [])
        require(matches, f"unresolved direct DT_NEEDED {name}: {consumer}")
        # Multiple identical frozen files are still ambiguous load providers.
        unique_hashes = {
            hashlib.sha256(path.read_bytes()).hexdigest() for path in matches
        }
        require(
            len(unique_hashes) == 1,
            f"ambiguous non-identical providers for {name}: {matches}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", required=True, type=pathlib.Path)
    parser.add_argument("--inputs", required=True, type=pathlib.Path)
    parser.add_argument("--readelf", required=True)
    parser.add_argument("--objdump", required=True)
    parser.add_argument("--expected-wrapper-build-id", required=True)
    args = parser.parse_args()

    artifacts = args.artifacts.resolve()
    inputs = args.inputs.resolve()
    require(artifacts.is_dir(), f"missing artifacts directory: {artifacts}")
    require(inputs.is_dir(), f"missing inputs directory: {inputs}")

    frozen_cfg = inputs / "config/appspawn_x.cfg"
    artifact_cfg = artifacts / "appspawn_x.cfg"
    require(frozen_cfg.is_file() and artifact_cfg.is_file(),
            "same-generation appspawn_x.cfg is missing")
    require(frozen_cfg.read_bytes() == artifact_cfg.read_bytes(),
            "deployed appspawn_x.cfg differs from frozen input")
    config = json.loads(frozen_cfg.read_text(encoding="utf-8"))
    services = [service for service in config.get("services", [])
                if service.get("name") == "appspawn-x"]
    require(len(services) == 1, "expected one appspawn-x init service")
    service = services[0]
    require(service.get("path") ==
            ["/system/bin/appspawn-x", "--socket-name", "AppSpawnX"],
            "appspawn-x must use init-owned direct exec")
    require(service.get("secon") == "u:r:appspawn:s0",
            "appspawn-x parent SELinux domain mismatch")
    environment = {item.get("name"): item.get("value")
                   for item in service.get("env", [])
                   if isinstance(item, dict) and item.get("name")}
    require(environment.get("APPSPAWNX_FAST_DEV") == "0",
            "FAST_DEV must be disabled in production cfg")
    require(environment.get("APPSPAWNX_CHECK_JNI") == "0",
            "CheckJNI must be disabled in production cfg")
    require(environment.get("APPSPAWNX_NO_JIT") == "1",
            "qualifying cold starts must disable ART JIT")
    library_path = environment.get("LD_LIBRARY_PATH", "").split(":")
    expected_library_path = [
        "/system/android/lib64",
        "/system/lib64/chipset-sdk-sp",
        "/system/lib64",
        "/system/lib64/platformsdk",
        "/system/lib64/chipset-sdk",
        "/system/lib64/ndk",
    ]
    require(library_path == expected_library_path,
            f"production cfg LD_LIBRARY_PATH mismatch: {library_path}")
    require(not any(path.startswith("/system/android/lib") and path != "/system/android/lib64"
                    for path in library_path),
            "32-bit Android library paths must not remain in production cfg")
    require(not any(path.startswith("/system/lib/") or path == "/system/lib"
                    for path in library_path),
            "32-bit OH library paths must not remain in production cfg")
    commands = [command for job in config.get("jobs", [])
                for command in job.get("cmds", [])]
    require(any("dalvik-cache/arm64" in command for command in commands),
            "ARM64 dalvik-cache setup is missing")

    wrapper = artifacts / "libwestlake_hap_domain_wrapper.so"
    wrapper_sidecar = artifacts / "libwestlake_hap_domain_wrapper.so.unstripped"
    compat = artifacts / "libbionic_compat.so"
    compat_sidecar = artifacts / "libbionic_compat.so.unstripped"
    appspawn = artifacts / "appspawn-x"
    appspawn_sidecar = artifacts / "appspawn-x.unstripped"
    for path in (wrapper, wrapper_sidecar, compat, compat_sidecar, appspawn, appspawn_sidecar):
        require(path.is_file(), f"missing artifact: {path}")
        header(args.readelf, path)

    # Wrapper: pure C ABI outside, exact stock HapContext call inside.
    wrapper_id = assert_same_build_id(args.readelf, wrapper, wrapper_sidecar)
    require(
        wrapper_id == args.expected_wrapper_build_id,
        f"wrapper Build-ID does not match pin: {wrapper_id}",
    )
    wrapper_needed, wrapper_soname, wrapper_dynamic = dynamic(args.readelf, wrapper)
    require(
        wrapper_soname == "libwestlake_hap_domain_wrapper.so",
        f"wrong wrapper SONAME: {wrapper_soname}",
    )
    require(
        wrapper_needed == ["libhap_restorecon.z.so", "libc++.so"],
        f"unexpected wrapper DT_NEEDED order/set: {wrapper_needed}",
    )
    assert_no_unsafe_dynamic_tags(wrapper_dynamic, wrapper)
    wrapper_symbols = run(args.readelf, "-sW", str(wrapper_sidecar))
    require(
        re.search(
            r"FUNC\s+GLOBAL\s+DEFAULT\s+\S+\s+WestLakeHapDomainSetContext$",
            wrapper_symbols,
            re.MULTILINE,
        )
        is not None,
        "wrapper C ABI export missing or not globally defined",
    )
    require(
        "HapDomainSetcontext" in wrapper_symbols,
        "wrapper does not retain the stock HapContext::HapDomainSetcontext import",
    )
    wrapper_source = (
        inputs / "sources/hap_domain_wrapper/westlake_hap_domain_wrapper.cpp"
    ).read_text(encoding="utf-8")
    require(
        "return context.HapDomainSetcontext(info);" in wrapper_source,
        "wrapper source does not call stock HapContext specialization",
    )
    require('"/proc' not in wrapper_source and "attr/current" not in wrapper_source,
            "direct procattr bypass detected in wrapper source")

    # Compat: admitted six-source producer, no old global brokers and no TPIDR
    # access. android_reset_stack_guards may update musl's global canary; that
    # is explicitly not evidence of Bionic slot-5 semantics.
    compat_id = assert_same_build_id(args.readelf, compat, compat_sidecar)
    compat_needed, compat_soname, compat_dynamic = dynamic(args.readelf, compat)
    require(compat_soname == "libbionic_compat.so", f"wrong compat SONAME: {compat_soname}")
    assert_no_unsafe_dynamic_tags(compat_dynamic, compat)
    compat_symbols = run(args.readelf, "-sW", str(compat_sidecar))
    forbidden_compat_symbols = (
        "g_bionic_tls_guard",
        "bionic_tls_get_guard",
        "bionic_tls_abi_init_main_thread",
        "bionic_tls_thread_trampoline",
        "pthread_create",
        # The real AOSP libziparchive DSO is the sole typed owner.  Compat is
        # forbidden from satisfying either the C++ ABI or an accidental C ABI.
        "_Z15ErrorCodeStringi",
        "ErrorCodeString",
    )
    for symbol in forbidden_compat_symbols:
        require(symbol not in compat_symbols, f"forbidden compat broker/writer linked: {symbol}")
    disassembly = run(args.objdump, "-d", "--no-show-raw-insn", str(compat_sidecar))
    require("tpidr_el0" not in disassembly.lower(), "compat contains a TPIDR_EL0 access")
    for forbidden_source in (
        "bionic_tls_abi.c",
        "unity_pthread_box.c",
        "unity_signal_box.c",
        "minizip.cpp",
    ):
        require(
            not (inputs / "sources/bionic_compat/src" / forbidden_source).exists(),
            f"forbidden compat source entered frozen closure: {forbidden_source}",
        )

    # Main ELF: exact PIE/TLS ownership contract, final/sidecar identity, and
    # deterministic startup dependency order.
    appspawn_id = assert_same_build_id(args.readelf, appspawn, appspawn_sidecar)
    app_header = header(args.readelf, appspawn)
    require(re.search(r"Type:\s+DYN \(Shared object file\)", app_header) is not None,
            "appspawn-x is not an ELF PIE (ET_DYN)")
    phdrs = run(args.readelf, "-lW", str(appspawn))
    require(
        "[Requesting program interpreter: /lib/ld-musl-aarch64.so.1]" in phdrs,
        "wrong appspawn-x program interpreter",
    )
    tls_lines = [line for line in phdrs.splitlines() if re.match(r"\s*TLS\s", line)]
    require(len(tls_lines) == 1, f"expected one PT_TLS, got: {tls_lines}")
    tls_fields = tls_lines[0].split()
    require(len(tls_fields) >= 8, f"unparseable PT_TLS: {tls_lines[0]}")
    require(int(tls_fields[4], 16) == 48,
            f"PT_TLS filesz must be 48: {tls_lines[0]}")
    require(int(tls_fields[5], 16) == 48, f"PT_TLS memsz must be 48: {tls_lines[0]}")
    require(int(tls_fields[-1], 16) == 16, f"PT_TLS align must be 16: {tls_lines[0]}")

    sidecar_symbols = run(args.readelf, "-sW", str(appspawn_sidecar))
    prefix_lines = [
        line for line in sidecar_symbols.splitlines()
        if line.rstrip().endswith("westlake_bionic_tls_slots_2_7_reservation")
    ]
    require(len(prefix_lines) == 1, f"missing/duplicate TLS prefix symbol: {prefix_lines}")
    prefix_fields = prefix_lines[0].split()
    require(int(prefix_fields[2]) == 48, f"TLS prefix symbol size is not 48: {prefix_lines[0]}")
    require(prefix_fields[3] == "TLS", f"TLS prefix symbol type is wrong: {prefix_lines[0]}")
    require(int(prefix_fields[1], 16) == 0, f"TLS prefix symbol must begin at module offset 0")
    admitted_prepare_lines = [
        line for line in sidecar_symbols.splitlines()
        if any(line.rstrip().endswith(symbol) for symbol in EXPECTED_MAIN_PREPARE_SYMBOLS)
    ]
    require(
        len(admitted_prepare_lines) == 1,
        f"missing/duplicate admitted main prepare symbol: {admitted_prepare_lines}",
    )
    admitted_prepare_fields = admitted_prepare_lines[0].split()
    require(
        admitted_prepare_fields[3] == "FUNC"
        and admitted_prepare_fields[4] == "GLOBAL",
        f"admitted prepare symbol must be global function: {admitted_prepare_lines[0]}",
    )

    app_needed, app_soname, app_dynamic = dynamic(args.readelf, appspawn)
    require(app_soname is None, "PIE unexpectedly carries a SONAME")
    expected_app_needed = [
        "libwestlake_thread_guard_registry.so",
        "libc.so",
        "libhilog.so",
        "libipc_single.z.so",
        "libsamgr_proxy.z.so",
        "libbegetutil.z.so",
        "libselinux.z.so",
        "libhap_restorecon.z.so",
        "libtokensetproc_shared.z.so",
        "libnativehelper.so",
        "liblog.so",
        "libbionic_compat.so",
        "libart.so",
        "libc++.so",
    ]
    require(
        app_needed == expected_app_needed,
        f"unexpected appspawn-x DT_NEEDED order/set: {app_needed}",
    )
    require(
        "libwestlake_hap_domain_wrapper.so" not in app_needed,
        "wrapper must remain a fail-closed absolute-path dlopen, not startup NEEDED",
    )
    assert_no_unsafe_dynamic_tags(app_dynamic, appspawn)
    child_source = (inputs / "sources/appspawn/src/child_main.cpp").read_text(encoding="utf-8")
    require(
        f'"{wrapper_id}"' in child_source,
        "appspawn child source does not pin the wrapper Build-ID",
    )
    require(
        '"/system/lib64/libwestlake_hap_domain_wrapper.so"' in child_source,
        "appspawn child source does not pin the production wrapper path",
    )
    require(
        "westlake_native_compat_prepare_main_thread" not in child_source,
        "legacy appspawn child source must not own the admitted main prepare entry",
    )
    main_prepare_header = (inputs / "sources/appspawn/src/native_compat_prepare.h").read_text(encoding="utf-8")
    main_prepare_source = (inputs / "sources/appspawn/src/native_compat_prepare.cpp").read_text(encoding="utf-8")
    template_source = (
        inputs / "sources/native_compat/thread_template_publisher.c"
    ).read_text(encoding="utf-8")
    main_prepare_owner = (
        inputs / "sources/appspawn/src/native_compat_prepare_owner_aarch64.S"
    ).read_text(encoding="utf-8")
    require(
        "int westlake_native_compat_prepare_main_thread(" in main_prepare_header
        and "const WlncProcessIdentityV1 *identity);" in main_prepare_header,
        "main prepare header does not declare the receipt-bound C ABI symbol",
    )
    require(
        "getrandom(&guard, sizeof(guard), 0)" in main_prepare_source,
        "main prepare source does not require OS CSPRNG",
    )
    require(
        "__stack_chk_guard" not in main_prepare_source,
        "main prepare source must not write musl global __stack_chk_guard",
    )
    require(
        "0x00000aff0a0d0000UL" not in main_prepare_source,
        "main prepare source must not contain the fixed canary fallback",
    )
    require(
        "WLTP_PublishMainThreadTemplate" in main_prepare_source and
        "getauxval(AT_PHDR)" in template_source and
        "WLTP_MUTANT" not in main_prepare_source,
        "MAIN does not use the exact main-image template publisher",
    )
    require(
        "westlake_bionic_tls_slots_2_7_reservation" in main_prepare_owner
        and "#:tprel_hi12:westlake_bionic_tls_slots_2_7_reservation" in main_prepare_owner
        and "#:tprel_lo12_nc:westlake_bionic_tls_slots_2_7_reservation" in main_prepare_owner,
        "main prepare owner accessor does not use TLSLE relocation ownership",
    )

    providers = provider_map(
        args.readelf,
        [
            inputs / "sysroot/lib",
            inputs / "libraries",
            artifacts,
        ],
    )
    verify_direct_needed(wrapper_needed, providers, wrapper)
    verify_direct_needed(compat_needed, providers, compat)
    verify_direct_needed(app_needed, providers, appspawn)

    print(f"PASS wrapper_build_id={wrapper_id}")
    print(f"PASS compat_build_id={compat_id} no_tpidr_writer=true")
    print(f"PASS appspawn_build_id={appspawn_id} pt_tls=0x30/0x30/align0x10")
    print("PASS production_config=arm64,init_owned,diagnostics_off")
    print("NOT_PROVEN bionic_slot5_guard_semantics")
    print("NOT_PROVEN first_frame_stub_call_closure")
    print("NOT_PROVEN device_verified")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
