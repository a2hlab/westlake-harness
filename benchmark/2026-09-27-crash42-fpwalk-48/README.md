# 2026-09-27 crash42 in-handler FP-walk (#48 path A)
The non-hook mallocng corruptor's a_crash (0xd6e20 / 0xd5e1c free-path) is recorded ONLY by
crash42 — our preload SIGSEGV handler (v4b observer) lost the signal race to sigchain's trampoline
(`SigchainStartReassert`, re-asserted every 2 ms), so it never runs at the a_crash. crash42 is the
one handler that runs 100% and already dumps regs+pc/sp/fp/lr. It was MISSING only the free()/realloc
caller chain — and its existing FP walk was dead because it read the stack via `/proc/self/mem`
(EACCES on the board). This deliverable adds a **mem-independent, in-process FP walk** to crash42.

| Path | What |
|------|------|
| src/crash_snapshot.c | v2 AS-safe crash42 recorder (mem-independent RAW fp-walk; NO in-signal dl_iterate_phdr) |
| crash_snapshot.fpwalk48.diff | the exact source delta vs the deployed recorder (this is the only functional change) |
| (VOID) out/libsigchain.so | link-check artifact only — NOT deployable (see NOTES CORRECTION) |
| out/libart.so | v1 relinked libart (VOID — deadlocked on-board; VM out-crash42-fpwalk48/art/, sha b42e48f4) |
| out/libart.so (v2) | DEPLOYABLE v2 AS-safe relinked libart (gitignored; VM out-crash42-fpwalk48/art-v2/, sha 72068841) |
| scripts/symbolize_fpwalk.py | OFFLINE symbolizer: fp_frame_return[] + maps -> lib+ELF-offset |
| crash_snapshot.v2.diff | v2 AS-safe source delta (raw fp-walk, no dl_iterate_phdr) |
| NOTES.md | root cause, the fix, build, self-test (incl. mem-forced-fail), deploy, safety |

CORRECTION: the deployable container is a RELINKED libart.so (device sigchain is static in libart), NOT libsigchain.so. Original (now-superseded) note: recorder = `libsigchain.so` (VM `out-crash42/recorder/`, built by `out-crash42/fixture/scripts/build_vm.sh` from `crash_snapshot.c` + `sigchain_musl_diag.cc`). Small ~57 KB standalone lib — lightweight rebuild, not libart. New sha `32c11986e4a8723e…` (60464 B).
