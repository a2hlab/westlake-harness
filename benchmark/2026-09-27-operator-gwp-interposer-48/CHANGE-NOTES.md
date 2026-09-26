# GWP-ASan-lite page-guard malloc interposer — pin the non-hook mallocng writer (#48 path A)
date: 2026-09-27   (OFFLINE build + self-test done; NOT yet on board — awaiting coordination)

## Product
- out/libwestlake_gwp.aarch64-ohos.so   sha256 0b048804bddff7a212d0569e10189dacfa5cac095aac0e05ddae264a6f123506 (9640 B; ELF64 AArch64; SONAME libwestlake_gwp.so)
    exports GLOBAL DEFAULT: malloc free calloc realloc posix_memalign memalign aligned_alloc malloc_usable_size
    UND (resolved at runtime from process libc): mmap mprotect munmap dlsym getenv atoi atol memcpy memset write
    (NO __emutls_get_address / no libc SONAME needed — header-minimal, -nostdlib)
- src/westlake_gwp.c (header-minimal, self-contained decls -> builds against any OH sysroot)
- scripts/build_gwp.sh  (BiSheng clang: --target=aarch64-linux-ohos --sysroot=<OH native> -nostdlib)
- scripts/selftest.c    (normal / overflow / uaf harness)

## What it does
LD_PRELOAD interposes the libc malloc family. malloc is a LIBC symbol -> in OH musl LD_PRELOAD of
libc symbols is GLOBALLY effective (this is the dlopen/libc-level interposition that WORKS; it is
NOT the bytehook/shadowhook-export namespace blind spot that killed the hook/sigaction master-switch).
A SAMPLED subset of allocations is served from a private mmap whose page right AFTER the user bytes
is a PROT_NONE guard page, user data RIGHT-ALIGNED against it -> any overflow-past-end write hits the
guard and faults AT THE WRITING INSTRUCTION (crash PC == the corruptor, not the victim). free()
mprotects the block PROT_NONE (quarantine) so a use-after-free write also faults at the write. Live
guarded regions are capped (WGWP_CAP) and the oldest recycled -> bounded memory. Non-sampled allocs
pass through to real libc malloc. This turns "can't tell who wrote it from the victim's free" into
"the corrupting write itself faults with a resolvable PC".

## Self-test (glibc x86_64, same algorithm; guard logic is arch/libc-agnostic mmap/mprotect)
Built libwestlake_gwp.so + a harness under LD_PRELOAD:
  T1 normal  (WGWP_SAMPLE=1, guard all): NORMAL_OK, rc 0   -- malloc/free/calloc/realloc/posix_memalign all fine
  T2 overflow (guarded 100B, write past end): SIGSEGV rc 139  -- caught AT the write (guard page)
  T3 uaf      (guarded, freed, then write):   SIGSEGV rc 139  -- caught AT the write (quarantine)
  T4 sampled churn (SAMPLE=8, CAP=256, 2000 allocs): NORMAL_OK rc 0  -- sampling + recycle, no false crash
  T5 front-guard + overflow (WGWP_FRONT=1):   SIGSEGV rc 139
  control (no interposer, same overflow): NO_FAULT rc 0  -- confirms the interposer is what catches it.

## Board diagnostic plan (codex-2; DO NOT run yet — coordinate to avoid board contention)
1. Push out/libwestlake_gwp.aarch64-ohos.so to the board (app namespace dir, e.g.
   /data/local/tmp/asx/lib/arm64-v8a/ or a scratch path).
2. Add it FIRST in LD_PRELOAD in the westlake run.sh (before other preloads). malloc is libc-level so
   it interposes globally across the app + all monitor libs + cronet.
3. Config for the ~17s early non-hook crash (control-r2 class): start with
     WGWP_SAMPLE=1 WGWP_CAP=16384 WGWP_MAXSZ=512
   (guard every small allocation; small allocs are the likely metadata-overwrite victims; CAP bounds
   memory; MAXSZ limits to small size-classes to keep memory sane). If it OOMs before 17s, raise
   SAMPLE (2/4) or lower CAP/MAXSZ. If the crash is NOT caught (corruptor overflowed a non-guarded
   or large chunk), widen MAXSZ / lower SAMPLE, or drop MAXSZ entirely for a full run.
4. Reproduce the warm ~17s crash. WHEN the corruptor overflows a GUARDED chunk, the guard page faults
   AT the write -> out-crash42 records PC/LR/maps. The new fault PC now maps to the CORRUPTOR's
   lib+offset (resolve with readelf/objdump at that file offset), NOT platform-io-thr's free. That
   PC names the writer (lib + function/offset). A UAF instead faults in the quarantine.
5. Iterate SAMPLE/MAXSZ across a few runs until a guard-page fault is captured (the crash moves from
   0xd6e20 in ld-musl to an address INSIDE the corruptor lib -> that is the answer).

## Caveats (honest)
- Heisenbug risk: the guard allocator changes timing/memory layout; the intermittent race may shift
  or not reproduce -> may need several runs. If it stops reproducing entirely under the interposer,
  that itself is a signal (timing-sensitive corruptor).
- Coverage: catches overflow-past-a-tracked-allocation and use-after-free writes (the likely causes
  of a chunk-metadata-byte overwrite). It does NOT catch a wild write to an unrelated computed
  address, or underflow unless WGWP_FRONT=1. If nothing is caught after tuning, that narrows the
  class (not a simple overflow/UAF of a heap block).
- Memory: full guarding is ~2 pages/alloc; use WGWP_SAMPLE / WGWP_CAP / WGWP_MAXSZ to bound it.

## Status
Offline build + self-test complete. NOT deployed. Board run is codex-2's + must be coordinated
(codex-2 is deploying the delivery build; avoid board contention). This is path A (root-cause pin);
path B (works + fresh-restart) remains the pragmatic fallback if the writer is not caught.
