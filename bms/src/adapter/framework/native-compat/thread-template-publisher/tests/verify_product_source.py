#!/usr/bin/env python3
"""Source-order gate for the product main-template publication boundary."""

from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[5]
APP = ROOT / "adapter/framework/appspawn-x"
MODULE = ROOT / "adapter/framework/native-compat/thread-template-publisher"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    prepare = (APP / "src/native_compat_prepare.cpp").read_text()
    reservation = (
        APP / "tls_prefix/bionic_tls_prefix_reservation.cpp"
    ).read_text()
    publisher = (MODULE / "src/thread_template_publisher.c").read_text()
    build = (APP / "BUILD.gn").read_text()

    begin = prepare.index("int WestLakeNativeCompatPrepareMainThread(")
    end = prepare.index("\nint WestLakeNativeCompatVerifyCurrentThreadReady", begin)
    body = prepare[begin:end]
    ordered = [
        "WLTG_AfterForkChildReset",
        "WLTG_ProcessArm",
        "WLTG_IssueThreadTicket",
        "WLTG_PrepareCurrentThread",
        "WLTG_VerifyCurrentThreadReady",
        "WLTP_PublishMainThreadTemplate",
        "ProductState::READY",
    ]
    positions = [body.index(token) for token in ordered]
    require(positions == sorted(positions),
            f"MAIN publication order drift: {list(zip(ordered, positions))}")
    before_publish = body[:body.index("WLTP_PublishMainThreadTemplate")]
    for forbidden in ("pthread_create", "clone(", "fork(", "std::thread"):
        require(forbidden not in before_publish,
                f"thread creation before template publication: {forbidden}")
    failure = body[body.index("WLTP_PublishMainThreadTemplate"):]
    require("WLTG_Revoke" in failure and "MarkFailed" in failure and
            "_exit(126)" in failure,
            "template publication failure is not terminal in the caller")

    require(".tdata.westlake_bionic_tls_prefix" in reservation and
            "@progbits" in reservation and ".zero 48" in reservation and
            ".tbss.westlake_bionic_tls_prefix" not in reservation and
            ".byte" not in reservation,
            "product reservation is not an all-zero 48-byte .tdata image")
    require("getauxval(AT_PHDR)" in publisher and
            "PT_PHDR" in publisher and "PT_INTERP" in publisher and
            "PT_GNU_RELRO" in publisher,
            "publisher does not bind the exact main image")
    require("atomic_compare_exchange_strong_explicit" in publisher and
            "g_publish_state" in publisher and
            "static _Atomic uint32_t" in publisher,
            "publisher has no process-global exact-once CAS")
    require("(PF_R | PF_W | PF_X)) != (PF_R | PF_W)" in publisher,
            "publisher does not reject an executable containing LOAD")
    require("PROT_READ | PROT_WRITE" in publisher and
            "const int restore_protection = PROT_READ" in publisher,
            "RELRO writable/restore sequence is incomplete")
    for forbidden in ("pthread_create", "clone(", "fork(",
                      "__stack_chk_guard"):
        require(forbidden not in publisher,
                f"publisher crossed a forbidden boundary: {forbidden}")

    require(
        '"../native-compat/thread-template-publisher/src/thread_template_publisher.c"'
        in build and
        '"../native-compat/thread-template-publisher/include"' in build,
        "appspawn product graph does not compile the publisher",
    )
    print("PASS product source main->template single-thread order exact_once=CAS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
