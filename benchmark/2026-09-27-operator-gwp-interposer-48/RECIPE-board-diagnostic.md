# Board diagnostic recipe — pin the non-hook mallocng writer with the GWP interposer (#48)
# FOR codex-2 (board runner). claude-3 analyzes the captured guard-fault. Board 61b0657200000000000000000324012c.
# Product: out/libwestlake_gwp.aarch64-ohos.so  sha256 0b048804bddff7a212d0569e10189dacfa5cac095aac0e05ddae264a6f123506

## 0. Precondition
Speed (AOT/JIT) delivery (deploy/operator-speed-50) is deployed and passing. This diagnostic only
ADDS an LD_PRELOAD layer to the app; it changes no delivery binary. Remove the LD_PRELOAD to revert.

## 1. Push the interposer to the board (into the app arm64 lib dir = app namespace)
  SO=<repo>/westlake-harness-merged48/benchmark/2026-09-27-operator-gwp-interposer-48/out/libwestlake_gwp.aarch64-ohos.so
  hdc file send "$SO" /data/local/tmp/asx/lib/arm64-v8a/libwestlake_gwp.so
  hdc shell sha256sum /data/local/tmp/asx/lib/arm64-v8a/libwestlake_gwp.so   # expect 0b048804...

## 2. Inject into the APP process env  (CRITICAL: must reach the appspawn-x child)
Per DIGEST B-9, run.sh `export` does NOT survive the appspawn-x fork. Use the SAME app-env channel
that already preloads libwebview_bionic_shim into the app (the westlake launcher's app env / preload
list). Prepend the interposer to the app's LD_PRELOAD and add the WGWP vars:
  LD_PRELOAD=/data/local/tmp/asx/lib/arm64-v8a/libwestlake_gwp.so:<existing app preloads>
  WGWP_SAMPLE=1  WGWP_CAP=16384  WGWP_MAXSZ=512  WGWP_LOG=1
(libwestlake_gwp FIRST so its malloc wins. malloc is a libc symbol -> globally effective in OH musl.)

## 3. GATE — confirm the interposer actually loaded into the app child
Launch once; grep the APP CHILD stderr for:  [WGWP] armed
If ABSENT -> LD_PRELOAD did not reach the app child -> fix the env channel (do NOT proceed until the
armed line appears in the child, not the parent).

## 4. Reproduce the ~17s non-hook crash — guard-disabled warm, 5-8 rounds (Heisenbug)
No auto-relaunch watchdog (controlled test; DIGEST B-9). Per round, warm start, observe to ~40s
(the crash is ~17s), and for the crashing round capture ALL of:
  - crash-analysis.json (signal, thread, pc, lr, loaded_monitors)
  - the crash42 guard-fault event snapshot (.txt/.ucontext/.siginfo)
  - /proc/<child_pid>/maps  ->  hdc shell "cat /proc/<pid>/maps > /data/local/tmp/gwp-maps-rN.txt" ; hdc file recv   (NOT hdc recv on /proc — truncates to ~4KB)
Run 5-8 rounds because the guard allocator perturbs timing (the race may shift; expect it to fire in
a subset of rounds).

## 5. SUCCESS signal (how to know it worked)
The crash PC is NO LONGER ld-musl 0xd6e20 / 0xd5e1c (the victim free), but an address INSIDE an app
or monitor lib (or a PROT_NONE guard region) -> the guard page caught the corruptor's write. si_addr
will be in a guarded mmap region (high, page-aligned) and PC will be in the writer.

## 6. Tuning ladder (only if step 4 OOMs or MISSES)
  OOM before 17s          -> WGWP_SAMPLE=2 (or 4); or WGWP_CAP=8192; or WGWP_MAXSZ=256
  crash still at ld-musl   -> corruptor overflowed a NON-guarded / larger alloc:
     set 2: WGWP_SAMPLE=1 WGWP_MAXSZ=4096 WGWP_CAP=8192   (guard all sizes up to a page)
     set 3: WGWP_SAMPLE=2 WGWP_MAXSZ=4096 WGWP_CAP=8192   (halve memory if set 2 OOMs)
     set 4: add WGWP_FRONT=1  (catch underflow / write-before-buffer)
  If after set 4 x (5-8 rounds) nothing is caught -> the corruption is NOT a simple overflow/UAF of a
  tracked heap block (e.g., a wild write to a computed address) -> report; pivot to path B.

## 7. Hand back to claude-3
For the round where the PC moved off ld-musl: the guard-fault crash-analysis.json + the pulled maps.
claude-3 resolves: PC(absolute) - writer-lib map base (from maps) = file offset ->
readelf -s / llvm-objdump -d --start-address=<off> / addr2line -> the corruptor lib + function/offset,
then produces the fix (e.g., patch/neuter that lib's offending write, or hollow it).
