#!/usr/bin/env python3
"""patch_libjavacore_NAR_null_guard.py — binary-patch libjavacore.so to make
NativeAllocationRegistry_applyFreeFunction a no-op when freeFunction == 0.

Background:
    AOSP libcore's `NativeAllocationRegistry_applyFreeFunction(JNIEnv*, jclass,
    jlong freeFunction, jlong ptr)` does a raw `(*(FreeFunction)freeFunction)(ptr)`.
    When freeFunction is 0 (multiple adapter `nGetNativeFinalizer` stubs return 0,
    transitively reachable), the call dereferences null → SIGSEGV at pc=0
    inside `art_quick_generic_jni_trampoline`.

    The crash is deterministic at ~29s after process spawn (first GC cycle drains
    pending References, ReferenceQueueDaemon dispatches the Cleaner whose thunk
    is a `NativeAllocationRegistry$CleanerThunk` with `freeFunction=0`).

Fix (this script):
    Binary-patch the function so it just `bx lr` (return immediately), never
    calling the freeFunction. Native cleanups are skipped (memory leaks for
    the duration of the app), but the daemon survives.

    Original 8 bytes at function entry:
        e59d0000   ldr r0, [sp]    ; arg = ptr
        e12fff12   bx  r2          ; tail-call freeFunction
    Patched 8 bytes:
        e12fff1e   bx  lr           ; return
        e1a00000   mov r0, r0       ; nop padding

Long-term fix:
    Rebuild libjavacore.so from libcore source with explicit null check in
    NativeAllocationRegistry_applyFreeFunction. The AOSP build pipeline on this
    ECS is currently broken (Bazel JDK detection), so the source-side fix is
    deferred. See ohos_patches/libcore/luni/.../*.patch (TBD).

Idempotent: the new bytes don't match the original signature, so re-running is
a no-op.

Usage:
    python3 patch_libjavacore_NAR_null_guard.py /path/to/libjavacore.so
"""
import os
import struct
import sys

ORIGINAL = bytes([0x00, 0x00, 0x9d, 0xe5,  0x12, 0xff, 0x2f, 0xe1])
PATCHED  = bytes([0x1e, 0xff, 0x2f, 0xe1,  0x00, 0x00, 0xa0, 0xe1])


def main():
    if len(sys.argv) != 2:
        sys.exit(f"Usage: {sys.argv[0]} <path/to/libjavacore.so>")
    src = sys.argv[1]
    if not os.path.isfile(src):
        sys.exit(f"ERROR: not a file: {src}")

    with open(src, "rb") as f:
        data = bytearray(f.read())

    if PATCHED in data:
        print(f"[skip] {src} already patched")
        return

    if ORIGINAL not in data:
        sys.exit(
            f"ERROR: original signature not found in {src}. "
            f"Compiled libjavacore.so changed; update ORIGINAL bytes."
        )

    bak = src + ".pre_G2.14k"
    if not os.path.exists(bak):
        with open(bak, "wb") as f:
            f.write(bytes(data))
        print(f"[backup] {bak}")

    i = data.find(ORIGINAL)
    print(f"[patch] signature at file offset 0x{i:x}")
    data[i:i + 8] = PATCHED

    with open(src, "wb") as f:
        f.write(bytes(data))
    print(f"[patched] {src} — applyFreeFunction now `bx lr; nop` (G2.14k)")


if __name__ == "__main__":
    main()
