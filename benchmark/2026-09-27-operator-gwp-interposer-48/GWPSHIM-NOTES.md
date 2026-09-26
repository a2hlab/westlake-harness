# libwestlake_gwp_shim — LEFT-adjacent page-guard + shim + in-SEGV PC resolver (#48)
date: 2026-09-27   hunts the non-hook mallocng HEADER/underflow writer

## Why LEFT-adjacent
Diagnosis: the corruption is a p-4 / front-zone (chunk header) clobber — the rear-zone canary stayed
silent across runs, and musl a_crashes at 0xd6e20 in its OWN metadata check (si_addr=0 = its own null
write, victim thread random != writer). So the write is BEFORE the user pointer. A page-guard must be
LEFT-adjacent: guarded blocks are [ GUARD page (PROT_NONE) ][ data pages, user = PAGE-aligned start ],
so a write to user-K (K<=PAGE), e.g. p-4, lands in the guard page and FAULTS AT THE WRITE.

## Product
- out/libwestlake_gwp_shim.aarch64-ohos.so  sha256 139d0ece7f5212fa9786f14ae5757f38b273276b36f3a5eb585ae2a40e59a9af (11856 B; ELF64 AArch64; SONAME libwestlake_gwp_shim.so)
    8 malloc-family GLOBAL DEFAULT; UND = mmap/mprotect/munmap/dlsym/dlopen/dlerror/dl_iterate_phdr/
    sigaction/getenv/atoi/atol/memcpy/memset/write/abort (no __emutls, no libc SONAME).

## Three confirmations
1. LEFT-adjacent guard: user is PAGE-aligned with a PROT_NONE guard page immediately BEFORE ->
   underflow write (p-4) faults AT the write. (self-test: fault_addr=p-4, in the guard.)
2. in-SEGV dl_iterate_phdr: SA_SIGINFO SIGSEGV handler reads the fault PC (aarch64 ucontext pc@432;
   fault addr from siginfo si_addr@16) and resolves PC -> lib name + file offset IN-PROCESS via
   dl_iterate_phdr (walks each lib's PT_LOAD; PC-base = file offset). Defeats the /proc-maps EACCES /
   DFX gap — no maps needed. Also logs the guarded block's victim buffer/size + alloc-site RA. Then
   CHAINS to the previous SIGSEGV handler (out-crash42) so it still captures; aborts if none.
   (self-test x86_64: writer_pc resolved to the faulting binary + offset.)
3. chain-load shim: constructor arms the guard first (malloc interception live), then
   dlopen(WGWP_SHIM or default /data/local/tmp/asx/webview-t-lib/libwebview_bionic_shim.so,
   RTLD_GLOBAL|RTLD_NOW). On failure: LOG (path+dlerror), do NOT abort.

## env-free (DIGEST B-9: env doesn't reach the appspawn-x child)
All defaults hardcoded: WGWP_SAMPLE=1 (guard EVERY allocation), WGWP_CAP=4096 live guarded regions
(recycled by munmap — a write to a recycled region still faults as an unmapped access, so recycling
does not lose detection), WGWP_MAXSZ=page. Report is unconditional (no log gate). Env still overrides
if it ever reaches the process.

## Self-test (glibc x86_64; guard/resolver logic arch-agnostic, aarch64 pc-offset by-spec)
  T1 normal (1500 allocs) : NORMAL_OK rc0; chain-load OK (default missing -> graceful, WGWP_SHIM=libm -> loaded)
  T2 underflow (write p-4): LEFT-guard FAULT -> handler logged fault_addr=p-4, writer_pc, dl_iterate_phdr
     resolved writer_lib+off, victim_buffer/size, alloc_site -> abort rc134.

## Board deploy (claude-2 / codex-2 — env-free)
  WESTLAKE_ANDROID_NATIVE_PRELOAD=/data/local/tmp/asx/lib/arm64-v8a/libwestlake_gwp_shim.so
Gate: app child stderr shows "[WGWP-GUARD] armed" + "[WGWP-GUARD] shim chain-loaded". Warm reproduce
the ~17s crash. On the corrupting write the LEFT guard faults and the handler prints
"[WGWP-GUARD] FAULT ... writer_pc=... writer_lib=<lib> writer_off=0x... victim_buffer/size alloc_site".
writer_lib+writer_off = the CORRUPTOR (hand claude-3 that line + crash-analysis). Memory: guard-all is
~2 pages/guarded alloc capped at 4096 (~32MB steady). If OOM before 17s, rebuild with a smaller CAP.
