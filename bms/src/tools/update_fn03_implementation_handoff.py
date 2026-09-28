#!/usr/bin/env python3
"""Write hash-bound Fn03 developer-test receipts and implementation handoffs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "20260727-implementation-r1"
IMPLEMENTER = "Codex primary implementation agent"
DEVICE_SERIAL = "5cd1e3dd00000000000000000923012c"
DEVICE_BOOT_ID = "98f07cbf-9d7f-4097-854f-02378063b550"
SECOND_DEVICE_SERIAL = "61b0657200000000000000000324012c"
SECOND_DEVICE_BOOT_ID = "84dac0ab-a48b-4458-a57c-de364d6e97bb"

CHANGED_FILES = [
    "src/vendor/upstream/sources/oh61-v7-b2133b5b/framework/activity/core/fn03_lifecycle_core.h",
    "src/vendor/upstream/sources/oh61-v7-b2133b5b/framework/activity/core/fn03_lifecycle_core.cpp",
    "src/vendor/upstream/sources/oh61-v7-b2133b5b/framework/activity/jni/ability_scheduler_adapter.h",
    "src/vendor/upstream/sources/oh61-v7-b2133b5b/framework/activity/jni/ability_scheduler_adapter.cpp",
    "src/vendor/upstream/sources/oh61-v7-b2133b5b/framework/jni/BUILD.gn",
    "src/vendor/upstream/sources/oh61-v7-b2133b5b/build/inner/compile_oh_adapter_bridge_arm64.sh",
    "src/atoms/Fn03/tests/fn03_lifecycle_core_test.cpp",
    "src/atoms/Fn03/tests/run_host_tests.sh",
    "src/tools/update_fn03_implementation_handoff.py",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def action_title(action_id: str) -> str:
    fn_id, action = action_id.split(".")
    definition = yaml.safe_load(
        (ROOT / "spec" / "atoms" / fn_id / action / "atom.yaml").read_text(
            encoding="utf-8"
        )
    )
    return str(definition["title"])


def write_action(action_id: str) -> None:
    fn_id, action = action_id.split(".")
    spec_dir = ROOT / "spec" / "atoms" / fn_id / action
    src_dir = ROOT / "src" / "atoms" / fn_id / action
    run_dir = ROOT / "evidence" / "atoms" / fn_id / action / "runs" / RUN_ID
    title = action_title(action_id)

    deployment_path = run_dir / "application-device-deployment.json"
    deployment_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "kind": "IMPLEMENTER_APPLICATION_DEVICE_ATTEMPT",
                "action_id": action_id,
                "run_id": RUN_ID,
                "candidate_bridge_sha256": (
                    "5455d57e566f0a466988e7aa31c31c9177ed78c001b4d6a91fd4817ba5abf41c"
                ),
                "targets": [
                    {
                        "serial": "5eab586000000000000000001123012c",
                        "prior_bridge_sha256": (
                            "e7c9f3ffee3916c00e40ac29ba3efdc41a512273bf4b5eac5a7f540c2b6a8ae9"
                        ),
                        "backup_path": (
                            "/data/local/tmp/"
                            "liboh_adapter_bridge.e7c9f3ffee3916c0.backup.so"
                        ),
                        "candidate_copy_sha256_matched": True,
                        "result": "BLOCKED_DEVICE_RECONNECT",
                    },
                    {
                        "serial": "5583f5be00000000000000000323012c",
                        "prior_bridge_sha256": (
                            "90c79dc0dd83ff75ad3024d84641096cb0b712677265c6d446321ba5c4e35a7d"
                        ),
                        "backup_path": (
                            "/data/local/tmp/"
                            "liboh_adapter_bridge.90c79dc0.backup.so"
                        ),
                        "candidate_copy_sha256_matched": True,
                        "result": "BLOCKED_DEVICE_RECONNECT",
                    },
                    {
                        "serial": SECOND_DEVICE_SERIAL,
                        "boot_id_at_test": SECOND_DEVICE_BOOT_ID,
                        "prior_bridge_sha256": (
                            "e7c9f3ffee3916c00e40ac29ba3efdc41a512273bf4b5eac5a7f540c2b6a8ae9"
                        ),
                        "backup_path": (
                            "/data/local/tmp/"
                            "liboh_adapter_bridge.e7c9f3ff.61b.backup.so"
                        ),
                        "candidate_copy_sha256_matched": True,
                        "apk_install": "PASS",
                        "aa_start": "COMMAND_ACCEPTED",
                        "fn03_ingress_observed": False,
                        "blocking_fact": (
                            "appspawn-x repeatedly failed to dlopen libartbased.so "
                            "and terminated with SIGSEGV before Fn03 ingress"
                        ),
                        "restore_before_reboot": "PASS_PRIOR_SHA_MATCHED",
                        "post_reboot_fact": (
                            "/system/android/lib64 was absent, demonstrating that this "
                            "target did not retain a complete Android runtime closure"
                        ),
                        "result": "BLOCKED_APPSPAWN_RUNTIME_ARTIFACT_CLOSURE",
                    },
                ],
                "recovery_required": (
                    "When 5eab or 5583 reconnects, restore its target-specific backup "
                    "before any unrelated test unless the Fn03 application replay is "
                    "being resumed deliberately. The 61b target was restored to its "
                    "prior bridge SHA before reboot; its staged backup remains under "
                    "/data/local/tmp, while /system/android/lib64 is absent after reboot."
                ),
                "verdict": None,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    logs = {
        "host_unit_test": run_dir / "host-unit-test.log",
        "product_build": run_dir / "product-build.log",
        "device_core_test": run_dir / "device-core-test.log",
        "artifact_sha256": run_dir / "artifact-sha256.txt",
        "application_device_deployment": deployment_path,
        "second_device_core_test": (
            ROOT
            / "evidence"
            / "atoms"
            / "Fn03"
            / "A06"
            / "runs"
            / RUN_ID
            / "device-core-test-61b.log"
        ),
        "second_device_appspawn_log": (
            ROOT
            / "evidence"
            / "atoms"
            / "Fn03"
            / "A06"
            / "runs"
            / RUN_ID
            / "61b-appspawn-artifact-closure.log"
        ),
    }
    receipt = {
        "schema_version": "1.0",
        "kind": "ACTION_IMPLEMENTER_DEVELOPER_TEST_RECEIPT",
        "action_id": action_id,
        "action_title": title,
        "run_id": RUN_ID,
        "implementer": IMPLEMENTER,
        "scope": "shared Fn03 R1 native core plus A06 production ingress guard",
        "checks": {
            "host_unit": "PASS",
            "arm64_strict_product_build": "PASS",
            "aarch64_oh_device_core": "PASS",
            "aarch64_oh_device_core_second_target": "PASS",
            "application_lifecycle_device": (
                "BLOCKED_APPSPAWN_RUNTIME_ARTIFACT_CLOSURE"
            ),
        },
        "device": {
            "serial": DEVICE_SERIAL,
            "boot_id": DEVICE_BOOT_ID,
            "kernel": "Linux 5.15.180 aarch64 Toybox",
        },
        "second_device": {
            "serial": SECOND_DEVICE_SERIAL,
            "boot_id_at_core_test": SECOND_DEVICE_BOOT_ID,
            "core_test": "PASS_A01_A10",
            "application_test": "BLOCKED_BEFORE_FN03_INGRESS",
        },
        "artifact_sha256": {
            "device_test_binary": (
                "a31ad33746ba37e4fae5622a7da167c2a738d735d01f2b680ba73acc5c0c9530"
            ),
            "liboh_adapter_bridge.so": (
                "5455d57e566f0a466988e7aa31c31c9177ed78c001b4d6a91fd4817ba5abf41c"
            ),
        },
        "raw_files": {
            role: {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": digest(path),
            }
            for role, path in logs.items()
        },
        "limitations": [
            "This is implementer evidence and contains no independent Action verdict.",
            "The device run executes the exact native reducer test binary on OH aarch64; "
            "it is not a substitute for the frozen application-level P/N/F replay.",
            "Product deployment was attempted on 5eab and 5583 after preserving each "
            "device's prior bridge by SHA, but both targets left the HDC target list "
            "during appspawn-x restart and did not reconnect in the observation window.",
            "On 61b, the exact aarch64 core test passed A01-A10. The application launch "
            "was blocked before Fn03 ingress because appspawn-x could not load "
            "libartbased.so and repeatedly terminated with SIGSEGV. After restoring the "
            "prior bridge and rebooting, /system/android/lib64 was absent, confirming an "
            "incomplete or non-persistent runtime artifact closure on that target.",
            "Fn04.A02 has not emitted a hash-bound typed first-content-present receipt, "
            "so Fn03.A10 application-level completion remains externally blocked.",
        ],
    }
    receipt_path = run_dir / "developer-test-manifest.json"
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    handoff = {
        "schema_version": "1.0",
        "action_id": action_id,
        "title": title,
        "status": "IMPLEMENTATION_IN_PROGRESS",
        "implementer": IMPLEMENTER,
        "source_commit": "WORKTREE",
        "definition_sha256": digest(spec_dir / "atom.yaml"),
        "design_sha256": digest(spec_dir / "DESIGN_SPEC.md"),
        "verification_sha256": digest(spec_dir / "verification.md"),
        "changed_files": CHANGED_FILES,
        "build_commands": [
            "src/atoms/Fn03/tests/run_host_tests.sh",
            "bash src/adapter/scripts/build_oh61_v7_bridge_r8_arm64.sh",
            (
                "/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/"
                "native/llvm/bin/clang++ --target=aarch64-linux-ohos "
                "--sysroot=/Applications/DevEco-Studio.app/Contents/sdk/default/"
                "openharmony/native/sysroot -std=c++17 -Wall -Wextra -Werror "
                "-pthread <fn03 core and test sources>"
            ),
        ],
        "test_commands": [
            "src/atoms/Fn03/tests/run_host_tests.sh",
            (
                "hdc -t 5cd1e3dd00000000000000000923012c shell "
                "/data/local/tmp/fn03_lifecycle_core_test"
            ),
            (
                "hdc -t 61b0657200000000000000000324012c shell "
                "/data/local/tmp/fn03_lifecycle_core_test_aarch64"
            ),
        ],
        "build_receipts": [
            logs["host_unit_test"].relative_to(ROOT).as_posix(),
            logs["product_build"].relative_to(ROOT).as_posix(),
            logs["device_core_test"].relative_to(ROOT).as_posix(),
            deployment_path.relative_to(ROOT).as_posix(),
            receipt_path.relative_to(ROOT).as_posix(),
        ],
        "completed_developer_checks": [
            "host unit test A01-A10",
            "40/40 source arm64 compilation and strict shared-library link",
            "exact test-binary SHA replay on a connected OH aarch64 device",
            "exact test-binary SHA replay on second OH aarch64 target 61b",
        ],
        "blockers_to_ready_for_verify": [
            "Application-level cold lifecycle replay was not completed: 5eab and 5583 "
            "disconnected during appspawn-x restart, while 61b lacked a complete "
            "persistent /system/android runtime artifact closure and crashed before "
            "Fn03 ingress.",
            "Only A06 is connected to a live production ingress; A01-A05 and A07-A10 "
            "still need their existing Java/JNI paths narrowed onto the native core.",
            "A10 still requires the typed Fn04.A02 first-content-present producer receipt.",
        ],
        "notes": (
            "Do not change status to READY_FOR_VERIFY until all listed product paths "
            "consume the native R1 core and the application-level developer replay is "
            "recorded. This handoff deliberately declares no PASS verdict."
        ),
    }
    (src_dir / "IMPLEMENTATION.yaml").write_text(
        yaml.safe_dump(handoff, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def main() -> None:
    for number in range(1, 11):
        write_action(f"Fn03.A{number:02d}")


if __name__ == "__main__":
    main()
