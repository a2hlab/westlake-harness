#!/usr/bin/env python3
"""#46: neutralize libnpth.so's "dump pthread" routine for musl.

The routine at vaddr 0x17930 walks Bionic's thread list from pthread_self()
with `x = *x` until NULL. On OH musl, offset 0 of struct pthread is `self`,
so the walk never ends and the npth dumper thread spins at 100% forever.
Replace its first instruction (stp x29, x30, [sp, #-96]!) with `ret`.
Callers (0x193a0, 0x19ac0, 0x28d10) ignore the return value.

Only the pinned Toutiao 13.9.0 libnpth.so is accepted.
"""
import hashlib
import sys

PINNED = "10641147b4c2a551e48162fa07f08776642147abc443d014756b909b6236076f"
OFFSET = 0x17930  # PT_LOAD[0] maps file offset 0 at vaddr 0
EXPECT = bytes.fromhex("fd7bbaa9")  # stp x29, x30, [sp, #-96]!
RET = bytes.fromhex("c0035fd6")     # ret

src, dst = sys.argv[1], sys.argv[2]
data = bytearray(open(src, "rb").read())
digest = hashlib.sha256(data).hexdigest()
if digest != PINNED:
    sys.exit(f"refusing: {src} sha256 {digest} is not the pinned libnpth.so")
if data[OFFSET:OFFSET + 4] != EXPECT:
    sys.exit(f"refusing: bytes at {OFFSET:#x} are {data[OFFSET:OFFSET + 4].hex()}")
data[OFFSET:OFFSET + 4] = RET
open(dst, "wb").write(data)
print(hashlib.sha256(data).hexdigest(), dst)
