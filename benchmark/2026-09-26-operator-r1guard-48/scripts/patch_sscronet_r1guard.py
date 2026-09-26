#!/usr/bin/env python3
# #48 r1 guard: skip the null-vtable TTNet-detector virtual call in libsscronet.so.
# Baseline sha256 38f0dd424fabd2b92a08e0a6eb372bc464dd424b370aba23c88e39ba6374866f.
# vaddr==file-offset in .text. NOP out the 3-insn virtual-call sequence at 0x28a218-0x28a220
# (ldr x8,[x0]; ldr x8,[x8,#0x28]; blr x8) so a null/unconstructed detector vtable is never
# dereferenced. Args (mov x1,x20; mov w2,w19) and the obj load (ldr x0,[x20,#0x568]) are left
# as harmless dead setup; execution falls through to the function epilogue at 0x28a224.
import sys
p=sys.argv[1]; d=bytearray(open(p,'rb').read())
NOP=bytes.fromhex('1f2003d5')
for off in (0x28a218,0x28a21c,0x28a220): d[off:off+4]=NOP
open(p,'wb').write(d); print("patched",p)
