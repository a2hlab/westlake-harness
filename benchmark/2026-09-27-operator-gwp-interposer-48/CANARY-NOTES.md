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

## UPDATE 2026-09-27: chain-load variant for the single-slot NATIVE_PRELOAD channel
The app's only early-preload channel is WESTLAKE_ANDROID_NATIVE_PRELOAD and it accepts EXACTLY ONE
.so path (a colon list is treated as one illegal filename and breaks the shim). That slot currently
holds libwebview_bionic_shim.so (app-required bionic-compat). To also get the canary into the child,
the canary now CHAIN-LOADS the shim itself: constructor(101) arms the canary, then
dlopen(shim, RTLD_GLOBAL|RTLD_NOW). Order is correct — canary loads first so its malloc-family
GLOBAL DEFAULT interception is live before the shim loads; the shim's mallocs go through canary.
So set the single slot to the canary:
  WESTLAKE_ANDROID_NATIVE_PRELOAD=/data/local/tmp/asx/lib/arm64-v8a/libwestlake_canary_shim.so
Shim path is env-overridable: WGWP_SHIM (default /data/local/tmp/asx/webview-t-lib/libwebview_bionic_shim.so).
On dlopen failure it LOGs ("[WGWP-CANARY] shim dlopen FAILED path=... dlerror=...") and does NOT abort
(a shim path problem must be loud, not a silent later crash).
RTLD constants (OH musl dlfcn.h): RTLD_NOW=0x2, RTLD_GLOBAL=0x100.

Product: out/libwestlake_canary_shim.aarch64-ohos.so  sha256 503a0ebb26a1fda1c2d16f9df4d580a21672b5c1e949c8020a7e769fc5fcf13c (ELF64 AArch64; malloc-family
GLOBAL DEFAULT; UND adds dlopen/dlerror; no __emutls). Supersedes the plain libwestlake_canary for
board use (single-slot preload). Self-test (glibc): default(missing) shim -> FAILED log + NORMAL_OK
rc0 (no abort); WGWP_SHIM=<real lib> -> "chain-loaded" log + NORMAL_OK rc0; overflow still -> abort rc134.

## Board use (updated) — claude-2
  WESTLAKE_ANDROID_NATIVE_PRELOAD=/data/local/tmp/asx/lib/arm64-v8a/libwestlake_canary_shim.so
  WGWP_SCAN=2000 WGWP_ABORT=1 WGWP_LOG=1
Gate: APP CHILD stderr shows "[WGWP-CANARY] armed" AND "[WGWP-CANARY] shim chain-loaded: ..." (if the
shim FAILED line appears instead, fix WGWP_SHIM before proceeding — the app needs the shim). Then warm
reproduce. On CORRUPTION: the report's alloc_site + the abort's crash-analysis+maps -> hand claude-3.

## UPDATE 2026-09-27 (b): periodic scan default-ON (env-free operation)
WGWP_SCAN (like WGWP_SHIM) does NOT reach the app child (DIGEST B-9), so relying on it to enable the
periodic scan would leave the child with scan OFF (free-time check only). Since canary takes over ALL
allocations, the original musl free-time crash no longer fires (everything is a canary chunk) and a
long-lived (never-freed) overflowed buffer would be missed without the scan. So the periodic scan is
now HARDCODED default-ON: src line 53 g_scan default 0 -> 4096 (scan the live ring every 4096
mallocs; WGWP_SCAN still overrides if it ever reaches). g_abort default 1 already correct.
=> libwestlake_canary_shim now needs NO env at all: chain-load shim (default path) + guard EVERY
   allocation + periodic scan (default 4096) + abort+report(alloc-site,clobber) on detection.
Rebuilt product: out/libwestlake_canary_shim.aarch64-ohos.so  sha256 a32b6feb6aae723f3c431248528291fbd82d9243cb43c3809968a8ff61ca1a53 (10344 B).
Self-test (glibc, NO env): un-freed overflow caught by default-on scan -> abort rc134; normal rc0;
overflow+free -> abort rc134. Supersedes 503a0ebb.
Board deploy (env-free): WESTLAKE_ANDROID_NATIVE_PRELOAD=/data/local/tmp/asx/lib/arm64-v8a/libwestlake_canary_shim.so
(WGWP_LOG optional for the armed/chain-loaded lines). Gate: app child shows "[WGWP-CANARY] armed"
+ "[WGWP-CANARY] shim chain-loaded" (both canary and shim mapped into the child).
