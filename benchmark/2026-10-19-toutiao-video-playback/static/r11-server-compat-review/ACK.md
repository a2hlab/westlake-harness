# ACK video-2020-r11-server-compat-review

No already-verified OH replacement was found. Failure is before breakpoint setup:
server GetMaxU64 size assertion, then no stop reply. The specific register/regset
and whether size is zero or >8 remain unknown; no SVE or stepover cause claimed.

Single retained alternative: local NDK r23b static AArch64 lldb-server,
SHA 13c0b4bfcb0b8b83cd9d73df2be0ebffcb1cc5fea2eb420cb7b2f5629254a06a.
It is unstripped, has Linux/AArch64 register and hardware-breakpoint implementations,
and no ELF interpreter/DT_NEEDED. This is a candidate for separate tool validation,
not a verified fix or admission. Frozen R11 server pin must not be bypassed.
Two other local OH15 objects have no evidence of a fix; do not retry by SHA alone.
No device call, build or observer modification. Exact paths/hashes are in results.
