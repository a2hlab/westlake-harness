# r1 null-vtable-detector guard — libsscronet.so (#48)
date: 2026-09-27

## Product (on-disk, gitignored; from codex-2's exact board baseline)
- libsscronet.R1GUARD48.so   sha256 5ba487778a6a3be4a633b7ba5e90e0ff4e1bb6693d28c970f0e8025eb88fdb79
    baseline libsscronet.so   sha256 38f0dd424fabd2b92a08e0a6eb372bc464dd424b370aba23c88e39ba6374866f (4321504 B)
Board overlay path: /data/local/tmp/asx/lib/arm64-v8a/libsscronet.so (app namespace; overlay, not BCP).

## What changed (12 bytes, 3 instructions)
The r1 crash is a C++ virtual call on an UNCONSTRUCTED TTNet-detector object (vtable=null):
  0x28a20c ldr x0,[x20,#0x568]   ; detector object ptr (valid)
  0x28a218 ldr x8,[x0]           ; x8 = vtable = *x0  (== 0 when object unconstructed)
  0x28a21c ldr x8,[x8,#0x28]     ; CRASH: deref null vtable + 0x28
  0x28a220 blr x8                ; virtual dispatch
Patch: NOP the 3-insn virtual-call sequence (0x28a218/0x28a21c/0x28a220 -> d503201f). x0/x1/x2
setup (0x28a20c/0x28a210/0x28a214) is left as harmless dead code; execution falls through to the
function epilogue at 0x28a224 (add x0,sp,#0x200; destruct local std::string; stack-canary check;
restore; ret). No vtable is ever dereferenced -> the crash cannot occur.

## Why an UNCONDITIONAL skip (not a conditional cbz-vtable guard)
A conditional guard needs one extra instruction (cbz x8, skip); it does NOT fit the 6-slot window
without dropping a real call argument, and there is NO code cave for a detour (Chromium .text is
densely packed — no >=20-byte zero/NOP run; the .text->.plt gap is only 8 bytes). Since the
detector is confirmed NON-ESSENTIAL telemetry (below), an unconditional skip == "the guard with
vtable treated as always-null" and is safe, cave-free, and drops no arguments.

## Safety proof — skipping this detector call is safe (non-essential telemetry)
1. Return value UNUSED: the very next instruction (0x28a224 add x0,sp,#0x200) overwrites x0, so
   the virtual call's result is discarded. Only its side-effect (network-quality detection) is lost.
2. Detector = telemetry: rodata names the detector family ttnet_raw_detect / stress / exception /
   feedback / polling_detect — ByteDance TTNet network-QUALITY detection, not the article/network
   data path. #41/#49 established the monitor/telemetry infra is non-essential for feed+articles.
3. cronet ITSELF treats such a detector as skippable: the SIBLING virtual call 16 instructions
   earlier (0x28a1cc: ldr x8,[x20,#0x40]; ldr x0,[x8,#0x28]; cbz x0, 0x28a264; ...) has a null
   guard and, when the detector is null, jumps to 0x28a264 (mov w8,wzr; b back) and continues.
   So "skip a null/absent detector and continue" is cronet's own defensive pattern; this patch
   applies the same outcome to the [x20+0x568] path that (bug) lacked the guard.
4. Epilogue unaffected: the skipped call changes no callee-saved reg / sp; the canary check and
   restore at 0x28a224+ run normally. Stack balanced (nop != push; no blr).
5. Not a hook, not heap: this is cronet's own C++ object lifecycle (arm64 disasm proven);
   unrelated to the engine hollow (which stays) — r1 was unmasked by the heap fix.
RESIDUAL: this disables one TTNet quality-detector dispatch process-wide (telemetry only).
No effect on article fetch/render/network transport (sscronet/cronet core, ttboringssl unchanged).

## Verify
scripts/assert_r1guard.sh out/libsscronet.R1GUARD48.so -> ALL PASS (3 nops + epilogue intact + ELF valid).
Reproduce: scripts/patch_sscronet_r1guard.py on the 38f0dd42 baseline.
Not deployed (board is codex-2's); hand to codex-2 to overlay + merge-test with the hollow engines.
