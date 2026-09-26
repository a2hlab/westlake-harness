# 2026-09-26 operator r1 guard (#48)
Null-vtable-detector guard for the r1 cronet crash (libsscronet +0x28a21c virtual call on an
unconstructed TTNet detector). NOP the 3-insn virtual-call sequence -> the null vtable is never
dereferenced; a non-essential telemetry detector dispatch is skipped (safe; see CHANGE-NOTES).
| Path | What |
|------|------|
| out/libsscronet.R1GUARD48.so | patched (gitignored binary, on-disk) |
| scripts/patch_sscronet_r1guard.py | reproducible patcher from the 38f0dd42 baseline |
| scripts/assert_r1guard.sh | 3 nops + epilogue + ELF checks (ALL PASS) |
| CHANGE-NOTES.md | shas, byte change, unconditional-skip rationale, telemetry-safety proof |
