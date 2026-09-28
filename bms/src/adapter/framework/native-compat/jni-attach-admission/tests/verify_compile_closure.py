#!/usr/bin/env python3
"""Fail closed when an active R45 adapter unit bypasses central JNI admission."""

from __future__ import annotations

import argparse
import pathlib
import re


RAW_JNI = re.compile(
    r"\b(?:AttachCurrentThread(?:AsDaemon)?|DetachCurrentThread)\s*\("
)

HISTORICAL_RAW_ATTACH_FILES = (
    "framework/appspawn-x/src/appspawnx_runtime.cpp",
    "framework/android-runtime/src/AndroidRuntime.cpp",
    "framework/android-runtime/src/android_view_DisplayEventReceiver.cpp",
    "framework/android-runtime/src/android_view_InputEventReceiver.cpp",
    "framework/activity/jni/app_scheduler_adapter.cpp",
    "framework/activity/jni/ability_scheduler_adapter.cpp",
    "framework/activity/jni/ability_connection_adapter.cpp",
    "framework/window/jni/window_callback_adapter.cpp",
    "framework/window/jni/session_stage_adapter.cpp",
    "framework/window/jni/window_manager_agent_adapter.cpp",
    "framework/core/jni/adapter_bridge.cpp",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def active_sources(adapter: pathlib.Path) -> list[pathlib.Path]:
    roots = (
        adapter / "framework/core/jni",
        adapter / "framework/activity/jni",
        adapter / "framework/window/jni",
        adapter / "framework/surface/jni",
        adapter / "framework/broadcast/jni",
        adapter / "framework/contentprovider/jni",
        adapter / "framework/android-runtime/src",
    )
    sources = {
        path
        for root in roots
        for suffix in ("*.c", "*.cc", "*.cpp")
        for path in root.glob(suffix)
        if "-untested-on-" not in path.name
    }
    sources.update(
        {
            adapter / "framework/appspawn-x/src/appspawnx_runtime.cpp",
            adapter / "framework/package-manager/jni/oh_bundle_mgr_client.cpp",
            adapter / "framework/package-manager/jni/apk_manifest_jni.cpp",
            adapter / "framework/package-manager/jni/apk_manifest_parser.cpp",
            adapter / "framework/package-manager/jni/axml_parser.cpp",
        }
    )
    return sorted(sources)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter-root", required=True)
    args = parser.parse_args()
    adapter = pathlib.Path(args.adapter_root).resolve(strict=True)

    wrapper_header = adapter / (
        "framework/native-compat/jni-attach-admission/include/"
        "westlake_jni_attach_admission.h"
    )
    wrapper_source = adapter / (
        "framework/native-compat/jni-attach-admission/src/"
        "jni_attach_admission.cpp"
    )
    require(wrapper_header.is_file(), "central JNI admission header missing")
    require(wrapper_source.is_file(), "central JNI admission source missing")

    sources = active_sources(adapter)
    missing = [str(path) for path in sources if not path.is_file()]
    require(not missing, f"active source inventory missing: {missing}")

    bypasses: list[str] = []
    for path in sources:
        for number, line in enumerate(
            path.read_text(encoding="utf-8-sig", errors="strict").splitlines(), 1
        ):
            if RAW_JNI.search(line):
                bypasses.append(
                    f"{path.relative_to(adapter)}:{number}:{line.strip()}"
                )
    require(not bypasses, "raw JNI attach/detach outside wrapper: " + "; ".join(bypasses))

    for relative in HISTORICAL_RAW_ATTACH_FILES:
        path = adapter / relative
        require(path.is_file(), f"historical attach source missing: {relative}")
        require("ScopedJniAttachment" in path.read_text(
            encoding="utf-8-sig", errors="strict"
        ) or relative.endswith("/AndroidRuntime.cpp"),
                f"central JNI route marker missing: {relative}")

    wrapper_text = wrapper_source.read_text(encoding="utf-8")
    require(len(RAW_JNI.findall(wrapper_text)) == 3,
            "central wrapper must own exactly Attach, AttachAsDaemon, Detach")
    for marker in (
        "WLTG_ADMISSION_ADAPTER_JNI_ATTACH",
        "WLTG_THREAD_ROLE_ADAPTER_JNI_ATTACH",
        "WLTG_IssueThreadTicket",
        "WLTG_PrepareCurrentThread",
        "WLTG_VerifyCurrentThreadReady",
        "WLTG_RetireCurrentThread",
    ):
        require(marker in wrapper_text, f"wrapper contract marker missing: {marker}")

    build_contracts = {
        "build/inner/compile_oh_android_runtime_arm64_stage2unity.sh": (
            "jni_attach_admission.cpp",
            "WLTG_REGISTRY",
            "libwestlake_thread_guard_registry.so",
        ),
        "build/inner/compile_oh_adapter_bridge_arm64.sh": (
            "jni_attach_admission.cpp",
            "WLTG_REGISTRY",
            "libwestlake_thread_guard_registry.so",
        ),
        "framework/appspawn-x/security_specialization/stock_child_plugin/"
        "build_route_a_generation_in_container.sh": (
            "jni_attach_admission.cpp",
            "jni_attach_admission.o",
            "-lwestlake_thread_guard_registry",
            "verify_compile_closure.py",
        ),
        "framework/appspawn-x/security_specialization/stock_child_plugin/"
        "generate_route_a_inputs.py": (
            "westlake_jni_attach_admission.h",
            "verify_compile_closure.py",
        ),
    }
    for relative, markers in build_contracts.items():
        text = (adapter / relative).read_text(encoding="utf-8")
        for marker in markers:
            require(marker in text,
                    f"build/input identity missing {marker}: {relative}")

    print(
        "PASS central JNI compile closure "
        f"active_sources={len(sources)} historical_raw_attach_sites=14 "
        "raw_attach_detach_outside_wrapper=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
