# libwestlake_gwp_shim (v4b OBSERVER) — in-musl-layer forensics at the a_crash (#48 path A)
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

## v4b LOAD FIX (why the first v4 failed on-board, and what actually fixed it)
The first v4 (sha 7d1a815e) FAILED TO LOAD on the board: no `[WGWP-OBS] armed`, 0 chain-load, app
crashed ~2s at pc=0x0 (the shim never got chain-loaded → app missing its bionic-compat shim).

Root-cause investigation (evidence, not theory):
- The UND set was already CLEAN (llvm-nm -u: only abort/dl_iterate_phdr/dlerror/dlopen/dlsym/getenv/
  write — all standard, all also used by the loadable v2/v3). Not a symbol-closure problem.
- **BIND_NOW is NOT the cause**: rebuilding v3 from src reproduces its exact deployed sha
  (345b032c5eb2d45d) and readelf -d shows v3 ALSO has `FLAGS BIND_NOW` + `FLAGS_1 NOW` + zero
  DT_NEEDED — yet v3 loads fine. So eager binding / missing DT_NEEDED were red herrings.
- **The sole structural difference**: the first v4 EXPORTED and interposed `sigaction` (to keep our
  handler "on top"), and installed our handler via a `dlsym(RTLD_NEXT,"sigaction")` function pointer.
  Defining the libc symbol `sigaction` in a zero-DT_NEEDED preload that the OH runtime *dlopen()s* is
  what broke loading. v3 (proven loadable) instead CALLS libc `sigaction` DIRECTLY (a normal UND the
  loader resolves via JUMP_SLOT) and chains to whatever SIGSEGV handler was installed BEFORE us
  (out-crash42, the runtime recorder, present from process start).

**v4b mirrors v3's exact symbol profile**: NO exported/interposed sigaction (sigaction is back as a
plain UND, called directly), handler installed via a direct sigaction() call, chain-to-previous. Only
the handler body (enhanced dump) and the removed guard machinery differ from v3. Additionally built
with `-Wl,-z,lazy -Wl,-z,norelro` so FLAGS has NO BIND_NOW (per outer-loop request; lazy also defers
dl_iterate_phdr/dlopen resolution to call time, strictly safer for a zero-DT_NEEDED preload).

Trade-off vs the interposing v4: we chain to the handler installed BEFORE our constructor. This is
correct as long as out-crash42 is installed before the app's NATIVE_PRELOAD dlopen (it is — it's the
always-on runtime recorder). If a board run shows out-crash42 capture but NO `[WGWP-OBS]` block, then
something installed a non-chaining SIGSEGV handler AFTER us and shadowed our dump — I'd add a minimal
re-assert then. Expected case: our dump runs, then out-crash42 captures.

## Product
- out/libwestlake_gwp_obs.aarch64-ohos.so  (provenance name)
- out/libwestlake_gwp_shim.aarch64-ohos.so (SAME bytes, deploy name for same-name overlay over v3/v4)
- **sha256 `a6c84d72b8518f0edff2cc50b6d6fd31600dcdf309f9b49f34ed92cee9b231a2`** (first16 `a6c84d72b8518f0e`;
  9840 B; ELF64 AArch64; SONAME libwestlake_gwp_shim.so). BiSheng clang --target=aarch64-linux-ohos
  -nostdlib -Wl,-z,lazy -Wl,-z,norelro. **Supersedes the unloadable 7d1a815e.**
- FLAGS: NO BIND_NOW, NO RELRO (lazy). 8 malloc-family GLOBAL DEFAULT, NO exported sigaction.
  UND = dl_iterate_phdr/sigaction/dlopen/dlsym/dlerror/getenv/write/abort (NO __emutls, no libc SONAME).

## Three confirmations
1. **守护已停 (guarding stopped)**: malloc/free/calloc/realloc/posix_memalign/memalign/aligned_alloc/
   malloc_usable_size are thin PASS-THROUGHs to real_* (resolved via dlsym(RTLD_NEXT,...)). musl's
   native allocator/layout is untouched — no private pool, no mprotect, no relocation, no sampling.
   (self-test T-NORMAL: 500 alloc+memset+free cycles → NORMAL_OK, no perturbation, no false crash.)
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

Handler install: direct sigaction() (v3-proven, loader-resolved UND); g_oldsa receives the previous
handler (out-crash42), which seg_handler chains to after the dump (or aborts / re-raises if none).

## env-free (DIGEST B-9: env doesn't reach the appspawn-x child)
No env needed. WGWP_SHIM optionally overrides the chain-load path; the dump is unconditional.

## Self-test (glibc x86_64; handler/backtrace/resolver logic arch-agnostic, aarch64 offsets by-spec)
  T-DLOPEN (mimics the board NATIVE_PRELOAD path): host installs its own SIGSEGV handler, then
     dlopen(observer, RTLD_NOW|RTLD_GLOBAL) → LOADS OK, constructor prints "armed" + "shim
     chain-loaded"; then an opaque null write (volatile target, defeats -O1 UB elision) →
     handler dumped fault_addr=0x0, pc=main+off, regs x0..x22/sp/pc, fp-backtrace
     (main → main → libc.so.6+0x2724a) → chained to the HOST handler → exit 42.
     (RTLD_NOW = eager load; proves the zero-DT_NEEDED preload resolves + arms under the board's path.)
  T-NORMAL (LD_PRELOAD, 500 alloc/free): NORMAL_OK (pure pass-through, no perturbation).

## Board deploy (claude-2 — env-free, same-name overlay over v3/v4)
Push out/libwestlake_gwp_shim.aarch64-ohos.so (sha a6c84d72…) to
`/data/local/tmp/asx/lib/arm64-v8a/libwestlake_gwp_shim.so` via the single-slot channel
`WESTLAKE_ANDROID_NATIVE_PRELOAD=.../libwestlake_gwp_shim.so`.
Gate: verify the .so maps r-xp AND app child stderr shows `[WGWP-OBS] armed (observer: no guarding;
...)` + `shim chain-loaded` BEFORE running forensic rounds. Then warm-reproduce the ~11-17s 0xd6e20
crash. At the a_crash the handler prints the `==== SIGSEGV a_crash evidence ====` block: fault_addr /
pc→lib+off (should say PC in musl a_crash region) / regs x0..x30 / fp-backtrace of the detecting
thread. Recv that stderr block + crash-analysis.json + maps and hand to claude-3.

## What claude-3 does with the dump
- The fp-backtrace names the free()/realloc caller chain in ld-musl + the caller lib/offset that
  invoked into musl's allocator on the detecting thread.
- The registers (esp. x0/x1 near the a_crash) hold the victim group/meta pointer; cross-referencing
  the poisoned meta value against the caller lib pins the writing subsystem.
- Then: instruction patch / whole-lib hollow / dlopen-refuse of the corruptor, OR a permanent musl
  malloc round-up (treats the whole class) — with sha + assert + safety proof, back to board test.
