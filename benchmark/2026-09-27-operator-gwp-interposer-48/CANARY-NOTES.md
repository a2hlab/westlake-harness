# Canary-guard-ALL variant — libwestlake_canary (#48 path A hedge)
date: 2026-09-27   companion to the page-guard libwestlake_gwp (0b048804)

## Product
- out/libwestlake_canary.aarch64-ohos.so  sha256 5e4fd1a4ef31a5b95ddf78c89851059a09fdf561c302e3fb351e6dce42dc17c0 (9656 B; ELF64 AArch64; SONAME libwestlake_canary.so)
    exports GLOBAL DEFAULT: malloc free calloc realloc posix_memalign memalign aligned_alloc malloc_usable_size
    UND (runtime): abort atoi atol dlsym getenv memcpy memset mmap write  (no __emutls, no libc SONAME)
- src/westlake_canary.c ; build with scripts/build_gwp.sh (swap SRC/OUT) or the same BiSheng invocation.

## Why (hedge vs page-guard)
page-guard (libwestlake_gwp) faults AT the corrupting write (PC == corruptor) but is per-PAGE ->
must SAMPLE, and its page churn perturbs timing (Heisenbug). canary-ALL uses BYTE-cost redzones ->
guards EVERY allocation, no sampling, low timing perturbation -> better for unattended long runs.
It detects overflow/underflow at free() and on a periodic scan, and reports the OVERFLOWED buffer +
its ALLOCATION SITE (which lib/function malloc'd it) + the clobbered canary bytes (the writer's data
signature). It does NOT give the corruptor's write PC (deferred detection) -> COMPLEMENTS page-guard.
Use both: page-guard names the writer when it fires; canary reliably names the victim buffer +
allocation subsystem + clobber pattern on long runs where page-guard's sample misses.

## Layout & detection
Per allocation (from the real allocator): [hdr: magic,size,alloc_site,front_canary][user bytes][rear redzone].
malloc returns base+sizeof(hdr); alloc_site = __builtin_return_address(0) (the malloc caller).
free(): recover hdr; verify front_canary (underflow) + rear redzone (overflow); on mismatch -> report
{buffer, size, alloc_site, which canary, clobber word} then abort (default) so out-crash42 captures.
Periodic scan (WGWP_SCAN=N): every N mallocs, walk a bounded live ring and verify all canaries ->
catches an overflow BEFORE its buffer is freed (closer in time to the write).
NOTE: this variant targets OVERFLOW + UNDERFLOW (contiguous redzone clobber) — the likely cause of a
"chunk metadata byte overwrite". Use-after-free WRITES are page-guard's domain (quarantine PROT_NONE).

## Self-test (glibc x86_64; canary/redzone logic is arch/libc-agnostic)
  T1 normal (3000 allocs + calloc/realloc): NORMAL_OK rc0, no false report
  T2 overflow (write into rear redzone) + free: CORRUPTION OVERFLOW(rear-redzone) report + abort rc134
     -> reported buffer, size=0x64, alloc_site, clobber=0x42ecececececec41 (shows the writer's bytes)
  T3 underflow (write before user) + free: CORRUPTION UNDERFLOW(front-canary) + abort rc134
  T4 overflow NOT freed, WGWP_SCAN=500: periodic scan catches it during churn + abort rc134
  T5 WGWP_ABORT=0: reports and CONTINUES (rc0)

## Env
  WGWP_REAR=bytes (default 16)   WGWP_SCAN=N (periodic scan every N mallocs; 0=off, check only at free)
  WGWP_ABORT=0/1 (default 1: abort on detection so out-crash42 captures)   WGWP_CAP=ring (default 65536)
  WGWP_LOG=1 (prints "[WGWP-CANARY] armed")

## Board use (claude-2 runs; DO NOT sample — guard ALL)
LD_PRELOAD it FIRST into the app (same env channel as libwebview_bionic_shim; run.sh export may not
survive appspawn-x — DIGEST B-9). Config for the ~17s crash:  WGWP_SCAN=2000 WGWP_ABORT=1 WGWP_LOG=1
(guard all + scan periodically). Gate: "[WGWP-CANARY] armed" in the APP CHILD stderr. Reproduce warm.
On CORRUPTION: the report's alloc_site (absolute) and the abort's crash-analysis+maps -> hand claude-3.
claude-3 resolves alloc_site - lib base (from maps) = file offset -> the lib/function that allocated
the overflowed buffer (the corrupting subsystem), + the clobber word = the writer's data signature.
