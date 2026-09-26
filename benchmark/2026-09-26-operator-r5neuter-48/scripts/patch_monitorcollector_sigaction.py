#!/usr/bin/env python3
# #48 r5: neuter libmonitorcollector-lib.so sigaction calls that overrun musl's 152B old buffer.
# Baseline = patched f3918bdc42b60a19edc3b80c4bd1c1cadc972eba286e5f1b1447505a6bff1793 (313744B).
# monitorcollector embeds xhook (xh_core_refresh/clear) which installs a SIGSEGV handler via
# sigaction with a non-null `old` (Bionic-sized); musl writes 152B struct sigaction -> OOB (r5).
# Same method as npth 7639af00: replace `bl sigaction@plt` with `mov x0,#0` (fake success;
# sigaction returns 0). vaddr==file-offset in .text.
#   0x1d214  install: sigaction(SIGSEGV, act, old=static 0x4d428)  -> r5 OOB  -> mov x0,#0
#   0x1df78  xh_core_clear restore sigaction                       -> mov x0,#0
# The 3rd site 0x1d318 is a `b`-tail-call INSIDE the SIGSEGV handler; unreachable once the
# install (0x1d214) is faked (handler never installed) -> intentionally left as-is.
import sys
p=sys.argv[1]; d=bytearray(open(p,'rb').read())
MOV0=bytes.fromhex('000080d2')
for off in (0x1d214,0x1df78): d[off:off+4]=MOV0
open(p,'wb').write(d); print("patched",p)
