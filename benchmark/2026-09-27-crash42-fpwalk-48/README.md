# 2026-09-27 crash42 in-handler FP-walk (#48 path A)
The non-hook mallocng corruptor's a_crash (0xd6e20 / 0xd5e1c free-path) is recorded ONLY by
crash42 — our preload SIGSEGV handler (v4b observer) lost the signal race to sigchain's trampoline
(`SigchainStartReassert`, re-asserted every 2 ms), so it never runs at the a_crash. crash42 is the
one handler that runs 100% and already dumps regs+pc/sp/fp/lr. It was MISSING only the free()/realloc
caller chain — and its existing FP walk was dead because it read the stack via `/proc/self/mem`
(EACCES on the board). This deliverable adds a **mem-independent, in-process FP walk** to crash42.

| Path | What |
|------|------|
| src/crash_snapshot.c | patched crash42 recorder (mem-independent FP walk + dl_iterate_phdr symbolization) |
| crash_snapshot.fpwalk48.diff | the exact source delta vs the deployed recorder (this is the only functional change) |
| out/libsigchain.so | rebuilt recorder (gitignored; VM: ~/a2hlab/ws/out-crash42-fpwalk48/libsigchain.so) |
| NOTES.md | root cause, the fix, build, self-test (incl. mem-forced-fail), deploy, safety |

Deployed recorder = `libsigchain.so` (VM `out-crash42/recorder/`, built by `out-crash42/fixture/scripts/build_vm.sh` from `crash_snapshot.c` + `sigchain_musl_diag.cc`). Small ~57 KB standalone lib — lightweight rebuild, not libart. New sha `32c11986e4a8723e…` (60464 B).
