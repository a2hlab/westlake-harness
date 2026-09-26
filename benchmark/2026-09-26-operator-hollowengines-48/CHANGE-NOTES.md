# Hollow hook-engines — libbytehook + libshadowhook (#48)
date: 2026-09-27   convergent fix for clamp r3/r4 residual mallocng corruption

## Products (binary-patched from codex-2's exact board baselines; on-disk in out/, gitignored)
- libbytehook.CLAMP48HOLLOW.so   sha256 fbb761a0f0d16342f9c63ff94af52b7d6377fda2def7c3f14950139907ea1baa  (63504 B)
    baseline libbytehook.so   sha256 238e7bc3e0c36247de86fe80453d596503ec0c45bc3ece578fc351d638506d61
- libshadowhook.CLAMP48HOLLOW.so sha256 34378f5c2e2f7f4b418a332018916d488fcbabdf68109836bc83b74bc6f53e3c  (77936 B)
    baseline libshadowhook.so sha256 88351a015be00254f961d5c559187513f8a657a40fb9d13f50b5d0733d7e9cbf
Board namespace path (codex-2 overlays): /data/local/tmp/asx/lib/arm64-v8a/{libbytehook,libshadowhook}.so
(also the runtime lib/arm64-v8a copy per manifest). BCP? No — these are app-namespace libs (overlay, not boot image).

## What changed (binary patch, NOT a from-scratch stub — keeps the real engine, no ULE)
Each engine's EXPORTED hook-install entry is overwritten at its first 8 bytes with
`mov x0,#1; ret` (return a fake non-null stub handle without installing anything); each
`unhook` entry with `mov x0,#0; ret` (success no-op). 9 functions, vaddr==file-offset in .text:
  libbytehook:   hook_single@0xdcd4, hook_partial@0xdce8, hook_all@0xdcfc  -> mov x0,#1;ret
                 unhook@0xdd10 -> mov x0,#0;ret
  libshadowhook: hook_func_addr@0xc5d4, hook_sym_addr@0xc764, hook_sym_name@0xc77c,
                 hook_sym_name_callback@0xc924 -> mov x0,#1;ret ; unhook@0xc938 -> mov x0,#0;ret
Bytes changed: bytehook 32 (4x8), shadowhook 40 (5x8). Exports/SONAME/NEEDED/ELF header
all unchanged (verified: dyn-sym FUNC set identical -> no UnsatisfiedLinkError). init NOT
patched (engine still initializes; it just installs nothing).

## Why this kills r3 AND r4 (and every residual hooker) — bypasses the namespace trap
The ~18-lib hook fleet installs inline hooks ONLY through these engine entry points. With
every install a fake-success no-op: no target prologue is rewritten, NO trampoline is
allocated -> the shadowhook/bytehook inline-hook MACHINERY (r4's corruptor, exercised by
hotfix's ClassLinker hook) never runs, AND no hook callback fires (r3's jato free-hook that
wrote Bionic metadata over musl chunks never runs). One patch, whole class. This is the
master-switch idea but applied to the ENGINE BINARY ITSELF, so it works regardless of OH-musl
namespace/SOURCE-NATIVE-LOAD (the loaded .so file is the patched one) — the exact reason the
LD_PRELOAD interposer master-switch (e692f8fd) failed does not apply here.

## Safety proof (per the standby-ACK design; the outer loop's key requirement)
1. Fake non-null handle (1): every caller checks the return for NON-NULL success and either
   stores it or ignores it. Verified caller pattern on the confirmed corruptors: hotfix-opt
   does `mov r4, r0` (STORE the stub, no deref); npth (prior) did `cbz w0` / store. None
   dereferences the handle as a pointer at install time -> handle=1 is safe.
2. unhook no-op returns 0 without touching the (fake) handle -> safe even if a lib later
   unhooks with handle=1 (the real unhook would deref it and crash; the patch prevents that).
3. get_prev_func / records / etc. are NOT patched but are reachable ONLY from inside a hook
   PROXY, which never fires (no hook installed) -> dead code -> never called with a fake handle.
4. The patch overwrites the FIRST instruction (was `str x30,[sp,#-0x10]!` on the thunks /
   `stp x29,x30,...` on shadowhook_unhook) so the push NEVER executes -> sp balanced, x30 =
   caller LR -> `ret` returns correctly. No stack imbalance, no PAC issue (xpaclri skipped).
RESIDUAL RISKS (watch in the crux experiment):
 (a) shadowhook_hook_sym_name_callback: patched to return fake stub WITHOUT invoking the async
     `hooked` callback. Fire-and-forget callers are fine; a caller that BLOCKS on the callback
     would hang (unlikely; no loaded corruptor uses it). If a hang appears, revisit.
 (b) NET/GFX observer hooks are also no-op'd (see classification). If any is load-bearing for
     article load/render, articles would fail — the crux experiment is the gate.

## OBSERVE vs FUNCTIONAL classification (all 22 engine-using libs; what each hooks)
All 22 are ByteDance APM/crash/monitor/hotfix/perf libs (observe-oriented; #41/#49: monitor
infra non-essential for feed/articles). The app's real network=sscronet/cronet+ttboringssl,
real graphics=hwui/skia — the monitors WATCH via hooks, they do not provide these.
 OBSERVE (safe to no-op; hooks heap/ART/thread/IO/dl for tracking):
   godzilla-lib, godzilla-memsponge(malloc), hotfix-opt(ClassLinker=hotpatch, non-load-bearing
   on a fresh no-patch app), hubble, io_perf, jarvis-binder, monitorcollector, npth(hollow),
   npth_fd_tracker, npth_ref_monitor, npth_repair, npth_tls_monitor, npth_vm_monitor(malloc),
   reparo, turbo, xdoctor, flash, jato(malloc/free — r3 corruptor).
 NET/GFX-touching (also no-op'd; WATCH in crux — believed observe, not transport/renderer):
   godzilla-sysopt(NET), jato(GFX), npth(NET, hollow), npth_fd_tracker(NET), sysoptimizer(NET/GFX),
   tunnel(GFX/NET). If articles fail to LOAD (network) or RENDER (graphics) under the hollow
   engines, these are the suspects to selectively restore (their hook targets, via a scoped
   engine pass-through) — but the corruption is the engine machinery, so restoring any hook
   re-risks corruption; prefer another route for that specific function if it proves load-bearing.

## Crux experiment (codex-2; resolves "is it the engine" + "any load-bearing hook")
Overlay both patched engines (namespace path above), warm 5x, feed + article (same 360s hard
nav). Expect: NO mallocng crash (0xd6e20/0xd5e1c gone) AND feed+articles still load+render.
- clean + articles work  -> engine hollow is THE fix; heap-corruption class closed; no hook was load-bearing.
- clean but articles break -> a NET/GFX hook was load-bearing; identify from the classification.
- still crashes -> corruptor is outside the engine hook path (non-hook writer); re-diagnose.
Assert before board: scripts/assert_hollow_engines.sh out/libbytehook.CLAMP48HOLLOW.so out/libshadowhook.CLAMP48HOLLOW.so (9/9 + structural PASS).
