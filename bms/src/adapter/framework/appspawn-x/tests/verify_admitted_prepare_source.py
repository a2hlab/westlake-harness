#!/usr/bin/env python3
"""Static source/verifier sync gate for the admitted main prepare skeleton."""

from __future__ import annotations

import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[4]
APP = ROOT / "adapter/framework/appspawn-x"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    legacy_child = (APP / "src/child_main.cpp").read_text(encoding="utf-8")
    header = (APP / "src/native_compat_prepare.h").read_text(encoding="utf-8")
    source = (APP / "src/native_compat_prepare.cpp").read_text(encoding="utf-8")
    plugin = APP / "security_specialization/stock_child_plugin"
    provider = (plugin / "src/westlake_android_runtime_provider.cpp").read_text(
        encoding="utf-8"
    )
    route_build = (plugin / "build_route_a_generation_in_container.sh").read_text(
        encoding="utf-8"
    )
    template = (
        ROOT / "adapter/framework/native-compat/thread-template-publisher/"
        "src/thread_template_publisher.c"
    ).read_text(encoding="utf-8")
    owner = (APP / "src/native_compat_prepare_owner_aarch64.S").read_text(encoding="utf-8")
    require('#include "native_compat_prepare.h"' not in legacy_child and
            "westlake_native_compat_prepare_main_thread" not in legacy_child,
            "legacy security-owning child path regained MAIN prepare ownership")
    legacy_entry = legacy_child[legacy_child.index("void ChildMain::run("):]
    require(legacy_entry.index("_exit(125);") <
            legacy_entry.index("applyAccessToken(msg)"),
            "legacy child path is not compile-safe fail-closed")

    require(
        "int westlake_native_compat_prepare_main_thread(" in header and
        "const WlncProcessIdentityV1 *identity);" in header,
        "header missing receipt-bound MAIN prepare C ABI declaration",
    )
    entry = provider[provider.index(
        "int WLAR_EnterAndroidAfterStockSpecialization("):]
    ordered = [
        "RequestValid(request, stockReceipt)",
        "WLAR_HostServicesBeginChild(&gHostServicesRegistry)",
        "WLAR_HostServicesPrepareMain(",
        "WLAR_HostServicesGetAuditSnapshot(",
        "WLAR_HostServicesMarkChildConsumed(",
        "ChildMain::runAfterStockSpecialization",
    ]
    positions = [entry.index(token) for token in ordered]
    require(positions == sorted(positions),
            f"Route-A MAIN admission order drift: {list(zip(ordered, positions))}")
    for identity_field in (
        "identity.abi_version = WLNC_ABI_VERSION",
        "identity.struct_size = sizeof(identity)",
        "identity.runtime_generation = request->runtime_generation",
        "identity.child_stage_tail_reached",
        "identity.security_owner_stock_appspawn",
        "FillGenerationSha(identity.runtime_provider_sha256)",
    ):
        require(identity_field in entry,
                f"Route-A process identity lost field: {identity_field}")

    require("getrandom(&guard, sizeof(guard), 0)" in source, "source missing OS CSPRNG call")
    require("__stack_chk_guard" not in source, "source must not write musl global guard")
    require("0x00000aff0a0d0000UL" not in source, "source must not contain fixed canary fallback")
    require(
        "WLTP_PublishMainThreadTemplate" in source and
        "getauxval(AT_PHDR)" in template and
        "PT_GNU_RELRO" in template,
        "source missing exact main-image template publication",
    )
    require(
        "#:tprel_hi12:westlake_bionic_tls_slots_2_7_reservation" in owner
        and "#:tprel_lo12_nc:westlake_bionic_tls_slots_2_7_reservation" in owner,
        "owner accessor must use TLSLE relocations",
    )

    for token in (
        "native_compat_prepare.cpp",
        "native_compat_prepare_owner_aarch64.S",
        "thread_template_publisher.c",
        "host_runtime_services.c",
        "westlake_android_runtime_provider.cpp",
    ):
        require(token in route_build, f"Route-A build missing {token}")

    print("PASS receipt-bound Route-A admitted_prepare source/verifier sync")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
