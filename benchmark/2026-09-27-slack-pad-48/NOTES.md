# libwestlake_pad — global slack-padding malloc interposer (#48 mitigation)
date: 2026-09-27

## Why (statistical verdict, claude-2, 16 rounds)
The non-hook mallocng corruption is a WHOLE-HEAP RANDOM adjacent-block-header smash: 4× 0xd6e20 +
2× 0xd5e1c, victims spanning different subsystems each time (sscronet / ICU / Mali-GPU / hilog / ipc /
art). No single culprit subsystem → a targeted fix is impossible; mitigation must be at the ALLOCATOR
level. The exact writer is un-pinnable at the diagnostic ceiling (victim side varies; a write-time
guard perturbs the very adjacency it needs to observe). Global slack padding is the last concrete lever
that can eliminate the crash: give every allocation SLACK tail bytes so a BOUNDED overflow past the
user's n lands in that slack instead of smashing the NEXT musl chunk header.

## What it does (pure slack — deliberately minimal)
Interposes the full malloc family (malloc/calloc/realloc/posix_memalign/memalign/aligned_alloc/
malloc_usable_size/free). Each allocation requests **(n + SLACK)** from the REAL allocator and returns
the pointer UNCHANGED. The user sees n usable bytes; SLACK=64 extra tail bytes hide behind them.
- calloc: allocate total+SLACK, zero exactly the user's `total` bytes.
- realloc: real_realloc(p, n+SLACK) — preserves min(old,new) as usual.
- aligned_alloc: pad rounded up to a multiple of align (C11 requirement).
- Because the returned pointer IS a real allocation (never moved/tracked), free / realloc /
  malloc_usable_size work on real pointers with **NO bookkeeping**.

NO mprotect, NO guard pages, NO redzone/canary checks, NO eviction, NO private pool. Functionally
transparent — the app just gets a legitimately larger buffer. Feed-break risk is far lower than the
earlier guards (the r1 sscronet-detector guard broke the feed; pure slack does not change behavior).

## Build / properties
BiSheng clang --target=aarch64-linux-ohos -nostdlib -Wl,-z,lazy -Wl,-z,norelro. Header-minimal
(self-contained decls), no __thread (no __emutls). env-free: SLACK=64 hardcoded. Chain-loads the app's
bionic-compat shim (single-slot WESTLAKE_ANDROID_NATIVE_PRELOAD points at us; WGWP_SHIM overrides).
- out/libwestlake_pad.aarch64-ohos.so — **sha256 `4e80e2eb2b2c8c869220d6f7686c8ff29e82320d022ae7bf014e606ba72f176d`**
  (first16 `4e80e2eb2b2c8c86`, 6496 B, ELF64 AArch64, SONAME libwestlake_pad.so).
- 8 malloc-family symbols GLOBAL DEFAULT (interpose musl libc). UND = dlsym/dlopen/dlerror/getenv/
  write/memset only (NO sigaction, NO dl_iterate_phdr, NO __emutls). FLAGS: no BIND_NOW / no RELRO (lazy).
- VM stable copy: `~/a2hlab/ws/out-pad48/libwestlake_pad.so` (same bytes).

## Self-test (glibc x86_64; padding logic arch-agnostic)
All PASS. Baseline malloc(100) usable=104; with pad malloc(100) usable=**168** (=+64 SLACK).
- T1 malloc(100): usable 168; wrote 163 B into the "100-byte" buffer → lands in slack, no corruption.
- T2 calloc(10,4): zeroed, usable 104 (40+64).
- T3 realloc(50→200): content preserved, usable 264 (200+64).
- T4 posix_memalign(64,100): rc0, 64-aligned, usable 168.
- T5 memalign(128,100): 128-aligned, usable 168.
- T6 aligned_alloc(64,128): 64-aligned, usable 200 (padded up to align multiple).
- T7 churn 2000 alloc/free: no crash. Constructor: armed + shim chain-loaded.

## Deploy (outer loop / claude-2) + the decisive experiment
Swap the single-slot preload in run.sh (line ~37) from `libwestlake_gwp_shim.so` to
`libwestlake_pad.so` (push the .so to /data/local/tmp/asx/lib/arm64-v8a/ + verify sha `4e80e2eb…`).
Gate: app child stderr shows `[WGWP-PAD] armed` + `shim chain-loaded`. Then run ~15 rounds A/B vs the
no-pad baseline and measure: (1) feed still renders normally (expected — pure slack, no behavior change);
(2) crash rate down / eliminated. This is the decisive test of whether global padding neutralizes the
whole-heap smash. If crashes persist, enlarge SLACK (128/256) — the overrun may exceed 64 B.
