#!/usr/bin/env python3
"""Fail closed if the frozen AOSP Bionic process-guard contract drifts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


MODULE = Path(__file__).resolve().parent.parent
FROZEN = MODULE / "var/evidence/references/aosp-bionic-stack-guard"
OUT = MODULE / "out/aosp-guard-semantics.json"


def read(relative: str) -> str:
    path = FROZEN / relative
    if not path.is_file():
        raise SystemExit(f"missing frozen AOSP source: {relative}")
    return path.read_text(encoding="utf-8")


def require(text: str, needle: str, claim: str) -> None:
    if needle not in text:
        raise SystemExit(f"AOSP guard semantic gate failed: {claim}")


main_thread = read("libc/bionic/__libc_init_main_thread.cpp")
pthread_create = read("libc/bionic/pthread_create.cpp")
tls_defines = read("libc/platform/bionic/tls_defines.h")
test_source = read("tests/stack_protector_test.cpp")
zygote = read("frameworks/base/core/jni/com_android_internal_os_Zygote.cpp")
arc4random = read("libc/bionic/bionic_arc4random.cpp")

require(
    main_thread,
    "__libc_safe_arc4random_buf(&__stack_chk_guard, sizeof(__stack_chk_guard));",
    "post-fork reset must generate the canonical global guard from Bionic CSPRNG",
)
require(
    main_thread,
    "__init_tcb_stack_guard(__get_bionic_tcb());",
    "post-fork reset must copy the canonical guard to the main TCB",
)
require(
    main_thread,
    "not possible to return from any existing\n// stack frame with stack protector enabled",
    "guard reset must retain the protected-frame safety warning",
)
require(
    pthread_create,
    "tcb->tls_slot(TLS_SLOT_STACK_GUARD) = reinterpret_cast<void*>(__stack_chk_guard);",
    "thread initialization must copy, not regenerate, the process guard",
)
require(
    pthread_create,
    "__init_tcb_stack_guard(tcb);",
    "new pthread allocation must initialize its guard slot",
)
require(
    tls_defines,
    "#define TLS_SLOT_STACK_GUARD      5",
    "AArch64 Bionic stack guard must remain TLS slot 5",
)
require(
    test_source,
    "ASSERT_EQ(__stack_chk_guard, reinterpret_cast<uintptr_t>(guard));",
    "Bionic test must require TLS/global equality",
)
require(
    test_source,
    "TEST(stack_protector, same_guard_per_thread)",
    "Bionic test must cover cross-thread guard semantics",
)
require(
    test_source,
    "ASSERT_EQ(1U, checker.guards.size());",
    "Bionic test must require exactly one guard across all threads",
)
require(
    zygote,
    "android_reset_stack_guards();",
    "zygote child fork path must reset the process guard",
)
require(
    arc4random,
    "arc4random_buf(buf, n);",
    "normal Bionic guard entropy must fill the requested bytes without masking",
)
require(
    arc4random,
    "memcpy(buf, reinterpret_cast<char*>(getauxval(AT_RANDOM))",
    "Bionic early-init fallback must be kernel AT_RANDOM, never a fixed value",
)

files = {}
for path in sorted(FROZEN.rglob("*")):
    if path.is_file():
        files[str(path.relative_to(FROZEN))] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()

result = {
    "status": "pass",
    "frozen_aosp_semantics": {
        "guard_cardinality_per_process": 1,
        "entropy_events_per_process_epoch": 1,
        "main_thread": "canonical global copied to TLS slot 5",
        "new_threads": "same canonical global copied to TLS slot 5",
        "tls_slot": 5,
        "global_tls_equality_required": True,
        "guard_low_byte_forced_zero": False,
        "fixed_entropy_fallback_allowed": False,
        "early_init_entropy_fallback": "kernel AT_RANDOM bytes",
        "reset_inside_stack_protected_frame_allowed": False,
    },
    "implementation_consequence": (
        "registry owns one verified OS-CSPRNG process guard and the publisher "
        "copies that exact value into every admitted thread reservation"
    ),
    "source_sha256": files,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("PASS frozen AOSP Bionic guard semantics: one process guard copied to every thread")
