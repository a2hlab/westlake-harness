#!/usr/bin/env python3
"""Read-only source/evidence audit for the registry's future product call sites."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def line_number(text: str, needle: str, start: int = 0) -> int:
    index = text.find(needle, start)
    require(index >= 0, f"missing source marker: {needle}")
    return text.count("\n", 0, index) + 1


def source_hits(root: pathlib.Path, relative_paths: list[str],
                pattern: re.Pattern[str]) -> list[dict[str, object]]:
    hits: list[dict[str, object]] = []
    for relative in relative_paths:
        path = root / relative
        require(path.is_file(), f"missing source: {relative}")
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line):
                hits.append({"path": relative, "line": number,
                             "text": line.strip()})
    return hits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    root = pathlib.Path(args.project_root).resolve(strict=True)
    report = pathlib.Path(args.report).resolve()
    try:
        report.relative_to(root)
    except ValueError as error:
        raise RuntimeError(f"report escapes project root: {report}") from error

    child_relative = "adapter/framework/appspawn-x/src/child_main.cpp"
    child = (root / child_relative).read_text(encoding="utf-8")
    run_start = child.find("[[noreturn]] void ChildMain::run")
    require(run_start >= 0, "ChildMain::run missing")
    setcon_line = line_number(child, "ret = applySELinux(msg);", run_start)
    post_child_line = line_number(
        child, "runtime->zygotePostForkChild()", run_start
    )
    post_common_line = line_number(
        child, "runtime->zygotePostForkCommon()", run_start
    )
    child_init_line = line_number(child, "runtime->onChildInit();", run_start)
    require(setcon_line < post_child_line < post_common_line < child_init_line,
            "child specialization order drifted")

    loader_relative = "adapter/framework/app-native-loader/src/app_native_loader.c"
    loader = (root / loader_relative).read_text(encoding="utf-8")
    dlopen_start = loader.find("void* ANL_Dlopen(")
    require(dlopen_start >= 0, "ANL_Dlopen missing")
    dlopen_end = loader.find("\n}\n", dlopen_start)
    require(dlopen_end >= 0, "ANL_Dlopen body not bounded")
    dlopen_body = loader[dlopen_start:dlopen_end]
    require("dlopen_ns(&domain->app" in dlopen_body,
            "ANL_Dlopen no longer uses the app namespace")
    loader_registry_gate = "WLTG_VerifyCurrentThreadReady" in dlopen_body

    ledger_relative = (
        "adapter/research/atoms/L03/A15/evidence/runs/"
        "20260712-s2-provider-closure-r1/reports/current/symbol-ledger.tsv"
    )
    ledger_path = root / ledger_relative
    require(ledger_path.is_file(), "provider closure ledger missing")
    pthread_rows = [
        line for line in ledger_path.read_text(encoding="utf-8").splitlines()
        if "\tpthread_create\t" in line and
        (line.startswith("libunity.so\t") or line.startswith("libil2cpp.so\t"))
    ]
    require(len(pthread_rows) == 2,
            f"unexpected Unity pthread_create ledger rows: {pthread_rows}")
    require(all("\treject\t" in row and
                "PTHREAD_OR_SEMAPHORE_OBJECT_CANNOT_CROSS_BIONIC_MUSL" in row
                for row in pthread_rows),
            "Unity pthread_create is no longer fail-closed in provider ledger")

    generation_verifier_relative = (
        "adapter/framework/appspawn-x/generation/verify_generation.py"
    )
    generation_verifier = (root / generation_verifier_relative).read_text(
        encoding="utf-8"
    )
    require('"pthread_create"' in generation_verifier and
            '"unity_pthread_box.c"' in generation_verifier and
            '"bionic_tls_abi.c"' in generation_verifier,
            "generation no longer rejects legacy global pthread/TLS brokers")

    reservation_relative = (
        "adapter/framework/appspawn-x/tls_prefix/"
        "bionic_tls_prefix_reservation.cpp"
    )
    reservation = (root / reservation_relative).read_text(encoding="utf-8")
    require(".zero 48" in reservation and
            "westlake_bionic_tls_slots_2_7_reservation" in reservation,
            "MAIN ELF reservation source contract missing")

    prepare_relative = (
        "adapter/framework/appspawn-x/src/native_compat_prepare.cpp"
    )
    misc_relative = (
        "adapter/framework/appspawn-x/bionic_compat/src/misc_compat.cpp"
    )
    legacy_tls_relative = (
        "adapter/framework/appspawn-x/bionic_compat/src/bionic_tls_abi.c"
    )
    prepare = (root / prepare_relative).read_text(encoding="utf-8")
    misc = (root / misc_relative).read_text(encoding="utf-8")
    legacy_tls = (root / legacy_tls_relative).read_text(encoding="utf-8")
    frozen_zygote_relative = (
        "adapter/framework/native-compat/thread-guard-registry/evidence/"
        "references/aosp-bionic-stack-guard/frameworks/base/core/jni/"
        "com_android_internal_os_Zygote.cpp"
    )
    frozen_hooks_relative = (
        "adapter/framework/native-compat/thread-guard-registry/evidence/"
        "references/aosp-bionic-stack-guard/art/runtime/native/"
        "dalvik_system_ZygoteHooks.cc"
    )
    frozen_zygote = (root / frozen_zygote_relative).read_text(encoding="utf-8")
    frozen_hooks = (root / frozen_hooks_relative).read_text(encoding="utf-8")
    native_fork_reset_present = "android_reset_stack_guards();" in frozen_zygote
    post_fork_hook_start = frozen_hooks.find(
        "static void ZygoteHooks_nativePostForkChild"
    )
    post_fork_hook_end = frozen_hooks.find(
        "static void ZygoteHooks_startZygoteNoThreadCreation",
        post_fork_hook_start
    )
    require(post_fork_hook_start >= 0 and post_fork_hook_end > post_fork_hook_start,
            "frozen ART post-fork hook body not bounded")
    hook_resets_guard = "android_reset_stack_guards" in frozen_hooks[
        post_fork_hook_start:post_fork_hook_end
    ]

    attach_sources = [
        "adapter/framework/appspawn-x/src/appspawnx_runtime.cpp",
        "adapter/framework/android-runtime/src/AndroidRuntime.cpp",
        "adapter/framework/android-runtime/src/android_view_DisplayEventReceiver.cpp",
        "adapter/framework/android-runtime/src/android_view_InputEventReceiver.cpp",
        "adapter/framework/activity/jni/app_scheduler_adapter.cpp",
        "adapter/framework/activity/jni/ability_scheduler_adapter.cpp",
        "adapter/framework/activity/jni/ability_connection_adapter.cpp",
        "adapter/framework/window/jni/window_callback_adapter.cpp",
        "adapter/framework/window/jni/session_stage_adapter.cpp",
        "adapter/framework/window/jni/window_manager_agent_adapter.cpp",
    ]
    attach_hits = source_hits(
        root, attach_sources,
        re.compile(r"\bAttachCurrentThread(?:AsDaemon)?\s*\("),
    )
    require(attach_hits, "no JNI attach boundary found")
    attach_guard_hits = [
        hit for hit in attach_hits
        if "WLTG_" in str(hit["text"])
    ]

    product_files = [
        "adapter/framework/appspawn-x/BUILD.gn",
        "adapter/framework/appspawn-x/generation/build_generation.sh",
        "adapter/framework/appspawn-x/generation/container_build.sh",
        child_relative,
        loader_relative,
    ]
    activation_hits = source_hits(
        root, product_files,
        re.compile(r"\bWLTG_(?:AfterForkChildReset|ProcessArm|PrepareCurrentThread|VerifyCurrentThreadReady)\b"),
    )

    payload = {
        "status": "pass_with_product_gaps",
        "source_order_candidate": {
            "path": child_relative,
            "setcon_call_line": setcon_line,
            "zygote_post_fork_child_line": post_child_line,
            "zygote_post_fork_common_line": post_common_line,
            "runtime_child_init_line": child_init_line,
            "candidate_window": "after applySELinux success, before zygotePostForkChild",
        },
        "app_native_loader": {
            "path": loader_relative,
            "uses_app_namespace_dlopen_ns": True,
            "current_thread_guard_gate_present": loader_registry_gate,
        },
        "unity_pthread_provider": {
            "ledger": ledger_relative,
            "rows": pthread_rows,
            "direct_musl_provider_admitted": False,
            "namespace_scoped_typed_bridge_present": False,
        },
        "jni_attach_boundaries": {
            "count": len(attach_hits),
            "hits": attach_hits,
            "guard_registry_calls_at_same_sites": attach_guard_hits,
            "centralized_admission_present": bool(attach_guard_hits),
        },
        "main_tls_reservation": {
            "path": reservation_relative,
            "source_contract_present": True,
            "reservation_is_not_guard_semantics": True,
        },
        "legacy_global_brokers": {
            "generation_verifier": generation_verifier_relative,
            "forbidden_by_generation": True,
        },
        "guard_owner_audit": {
            "standalone_registry_semantic":
                "one OS-CSPRNG process guard copied to every admitted thread",
            "route_a_prepare": {
                "path": prepare_relative,
                "generates_independent_guard": "GenerateGuard(&guard)" in prepare,
                "forces_low_byte_zero":
                    "guard &= ~static_cast<uint64_t>(0xff)" in prepare,
                "writes_musl_global": "__stack_chk_guard" in prepare,
                "registry_integrated": "WLTG_ProcessArm" in prepare,
            },
            "misc_compat": {
                "path": misc_relative,
                "writes_global_guard": "__stack_chk_guard = guard" in misc,
                "fixed_fallback_present": "0x00000aff0a0d0000" in misc,
                "fail_closed": "0x00000aff0a0d0000" not in misc,
            },
            "legacy_bionic_tls": {
                "path": legacy_tls_relative,
                "writes_global_guard": "__stack_chk_guard" in legacy_tls,
                "fixed_fallback_present":
                    "0x00000aff0a0d0000" in legacy_tls,
                "constructor_present": "__attribute__((constructor))" in legacy_tls,
                "direct_tp_present":
                    "bionic_tls_establish_current_thread" in legacy_tls,
            },
            "frozen_aosp_order": {
                "native_fork_child_resets_guard": native_fork_reset_present,
                "zygote_hooks_post_fork_child_resets_guard": hook_resets_guard,
                "westlake_external_appspawn_uses_native_fork_branch": False,
            },
            "global_tls_same_value_proven": False,
            "activation_blockers": [
                "multiple independent guard generators",
                "Route-A prepare masks the low byte unlike frozen AOSP",
                "fixed fallback in misc_compat and legacy bionic_tls_abi",
                "Musl-global guard mutation",
                "Bionic-global and per-thread slot equality not binary-proven",
            ],
        },
        "product_activation": {
            "present": bool(activation_hits),
            "hits": activation_hits,
            "same_generation_binary_proven": False,
        },
        "verdict": "MECHANISM_READY_CALL_GRAPH_NOT_PROVEN",
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print(
        "PASS boundary audit candidate_main_window=true "
        f"jni_attach_sites={len(attach_hits)} product_activation=false"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
