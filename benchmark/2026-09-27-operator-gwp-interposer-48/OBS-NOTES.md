# libwestlake_gwp_shim (v4 OBSERVER) — in-musl-layer forensics at the a_crash (#48 path A)
date: 2026-09-27   pins the non-hook mallocng corruptor by dumping at the detection point (NOT by guarding)

## Why observer (the pivot)
Three user-allocation adjacency guards have now MISSED this corruptor:
- v1 canary-guard-ALL (rear+front redzones, periodic scan): **0 CORRUPTION** across a warm batch.
- v2 page-guard (LEFT-adjacent, ≤4096B): **0 FAULT** (size cap missed >4KB IO buffers).
- v3 page-guard (LEFT-adjacent, ALL sizes, cap 16384): **0 FAULT** across 12 rounds / 4 hits of
  0xd6e20, victims spread across bd_tracker / main / ChromiumNet0 / RenderThread / platform-io.

Verdict (outer loop, confirmed): the corrupted bytes are **shared musl group/meta**, not a
thread-local user chunk, and the victim thread at the a_crash is RANDOM (≠ the writer). A guard that
relocates blocks into a private pool even *changes* musl-group adjacency (Heisenberg) so it can never
be adjacent to the write. Therefore this build **STOPS guarding** and becomes a pure OBSERVER: it
lets the corruption happen on musl's native layout and, at the a_crash SIGSEGV (musl's own integrity
check, 100% hit), dumps IN-PROCESS the evidence DFX cannot (its /proc/self/mem is EACCES): faulting
PC→lib+off, ALL GP registers (the victim chunk/meta ptr is usually in a register at a_crash), and a
frame-pointer backtrace of the DETECTING thread (each saved LR resolved via dl_iterate_phdr) = the
free()/realloc call chain that tripped musl's check.

## Product
- out/libwestlake_gwp_obs.aarch64-ohos.so  (provenance name)
- out/libwestlake_gwp_shim.aarch64-ohos.so (SAME bytes, deploy name for same-name overlay swap over v3)
- **sha256 `7d1a815e15ec6ef0459a027c482915c6a20307f671ab5007b1c013ed1c2bb63a`** (first16 `7d1a815e15ec6ef0`;
  9032 B; ELF64 AArch64; SONAME libwestlake_gwp_shim.so). BiSheng clang --target=aarch64-linux-ohos -nostdlib.
- 8 malloc-family + sigaction GLOBAL DEFAULT; UND = dl_iterate_phdr/sigaction/dlopen/dlsym/dlerror/
  getenv/write/abort (NO __emutls, no libc SONAME).

## Three confirmations
1. **守护已停 (guarding stopped)**: malloc/free/calloc/realloc/posix_memalign/memalign/aligned_alloc/
   malloc_usable_size are thin PASS-THROUGHs to real_* (resolved via dlsym(RTLD_NEXT,...)). musl's
   native allocator/layout is untouched — no private pool, no mprotect, no relocation, no sampling.
   (self-test T1: 500 alloc+memset+free cycles → NORMAL_OK, no perturbation, no false crash.)
2. **寄存器 dump (register dump)**: SA_SIGINFO SIGSEGV handler reads pc (aarch64 ucontext pc@432),
   fault addr (siginfo si_addr@16), and dumps ALL GP registers x0..x30 + sp + pc from
   uc_mcontext.regs@176. It flags when PC ∈ the musl mallocng integrity a_crash region
   (off 0xd6e20 / 0xd5e1c / 0xd6a00..0xd6f00) — then the regs hold the victim chunk/meta ptr.
   (self-test x86_64 NREGS=23: x0..x22 + sp + pc all dumped, clean `xN=0x...` labels.)
3. **fp 链回溯 (fp-chain backtrace)**: from x29(fp)@408 it walks the frame-pointer chain — [fp]=saved
   fp, [fp+8]=saved LR — up to 32 frames, each LR resolved to lib+off via in-SEGV dl_iterate_phdr
   (walks each lib's PT_LOAD; LR−base = file offset; defeats the /proc-maps EACCES / DFX gap).
   Sanity: fp non-null & 16-aligned, saved_fp monotonic & frame <0x100000. A nested fault while
   walking a bad fp is caught (g_in_handler) → chains/aborts, never re-dumps.
   (self-test x86_64: fault PC→main+off, LRs resolved through main binary AND libc.so.6+off.)

Plus: sigaction is interposed so OUR handler stays ON TOP — any SIGSEGV registration re-installs ours
and records theirs as the chain target (out-crash42). After the dump we chain to out-crash42 (so it
still captures) or abort. (self-test: TEST installs its handler via sigaction → we dump FIRST → chain
→ TEST_CHAINED_HANDLER_RAN, exit 42.)

## env-free (DIGEST B-9: env doesn't reach the appspawn-x child)
No env needed. WGWP_SHIM optionally overrides the chain-load path; the dump is unconditional.

## Self-test (glibc x86_64; handler/backtrace/resolver logic arch-agnostic, aarch64 offsets by-spec)
  T1 normal (500 alloc/free): NORMAL_OK rc0 (pure pass-through, no perturbation).
  T2 crash (opaque null write via volatile target, defeats -O1 UB elision):
     handler dumped fault_addr=0x0, pc=main+0x11b4, regs x0..x22/sp/pc, fp-backtrace
     (main+0x11cf → main+0x125c → libc.so.6+0x2724a) → chained to TEST handler → exit 42.

## Board deploy (claude-2 — env-free, same-name overlay over v3)
Push out/libwestlake_gwp_shim.aarch64-ohos.so (sha 7d1a815e…) to
`/data/local/tmp/asx/lib/arm64-v8a/libwestlake_gwp_shim.so` (overwrites v3 page-guard at the same
path) via the single-slot channel `WESTLAKE_ANDROID_NATIVE_PRELOAD=.../libwestlake_gwp_shim.so`.
Gate: app child stderr shows `[WGWP-OBS] armed (observer: no guarding; ...)` + `shim chain-loaded`.
Then warm-reproduce the ~11-17s 0xd6e20 crash. At the a_crash the handler prints the
`==== SIGSEGV a_crash evidence ====` block: fault_addr / pc→lib+off (should say PC in musl a_crash
region) / regs x0..x30 / fp-backtrace of the detecting thread. Recv that stderr block +
crash-analysis.json + maps and hand to claude-3.

## What claude-3 does with the dump
- The fp-backtrace names the free()/realloc caller chain in ld-musl + the caller lib/offset that
  invoked into musl's allocator on the detecting thread.
- The registers (esp. x0/x1 near the a_crash) hold the victim group/meta pointer; cross-referencing
  the poisoned meta value against the caller lib pins the writing subsystem.
- Then: instruction patch / whole-lib hollow / dlopen-refuse of the corruptor, OR a permanent musl
  malloc round-up (treats the whole class) — with sha + assert + safety proof, back to board test.
