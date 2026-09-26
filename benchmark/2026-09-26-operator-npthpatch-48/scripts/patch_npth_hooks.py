#!/usr/bin/env python3
"""#48 warm-corruptor fallback: neuter libnpth's two inline-hook installs.

Root cause (evidence/warm-corruptor-npth-48.txt): libnpth is the warm heap
corruptor, but — corrected by disassembly — it does NOT hook the malloc family.
Its ONLY two hook-install calls in JNI_OnLoad target:
  - 0x1ffb4  bytehook_hook_partial   -> "setpriority"
  - 0x24a34  shadowhook_hook_sym_name-> a table of libart.so ART GC / thread
             internals (FinishGC, WaitForGcToCompleteLocked, GarbageCollector::Run,
             ScopedPause, AllocThreadId, InternTable::WaitUntilAccessible,
             ThreadFlipBegin/End). The rodata "malloc"/"free" strings are log
             messages ("calloc parameters", " FREE SWAPPED"), not hook targets.
The corruption is via these inline hooks on hot ART functions (shadowhook
trampoline management on musl), not a malloc hook.

This patch replaces each `bl <hook-install>` with `mov x0, #1`, i.e. a fake
non-null success stub: npth believes every hook installed, JNI_OnLoad takes its
success path and returns success (npth stays LOADED — no _exit(1) risk, its
signal-based crash catching is untouched), but NO inline hook is actually
installed, so nothing rewrites ART's hot functions and the mallocng corruption
vector is gone.

Safety: JNI_OnLoad returns -6 if a hook install returns NULL, so we must fake
SUCCESS (not NULL) to keep npth loaded. The site-1 stub is not dereferenced
(0x1866c only reads a global flag). The site-2 stubs are stored for unhook only,
which runs in error/exit paths; shadowhook_unhook validates the stub and returns
an error for the fake one without dereferencing it.

Applies on top of the class-3 patched libnpth (8b8d559c). Not deployed here.

usage: patch_npth_hooks.py <in libnpth.so (8b8d559c)> <out libnpth.so>
"""
import sys, hashlib

PATCHES = [
    # (file offset == vaddr for .text; addr==off verified), expect `bl`, -> mov x0,#1
    (0x1ffb4, bytes.fromhex("8f290094"), "bytehook_hook_partial(setpriority)"),
    (0x24a34, bytes.fromhex("0b170094"), "shadowhook_hook_sym_name(libart GC/thread table)"),
]
MOV_X0_1 = bytes.fromhex("2000 80d2".replace(" ", ""))  # d2800020 LE = mov x0,#1

def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    data = bytearray(open(sys.argv[1], "rb").read())
    for off, expect, what in PATCHES:
        got = bytes(data[off:off + 4])
        if got != expect:
            sys.exit("offset 0x%x: expected %s (bl) but found %s — wrong base?"
                     % (off, expect.hex(), got.hex()))
        data[off:off + 4] = MOV_X0_1
        print("  patched 0x%08x  %s  bl -> mov x0,#1" % (off, what))
    open(sys.argv[2], "wb").write(data)
    print("sha256:", hashlib.sha256(data).hexdigest())
    print("wrote", sys.argv[2])

if __name__ == "__main__":
    main()
