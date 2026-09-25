# Toutiao crash triage (#46): six signatures, three fixes built

Every saved Toutiao run on the OH boards crashes. #46 triaged the existing evidence offline, with no board time: 19+ #38 runs on board 5ea34a45 (`ability38/*`) and the #42 runs on board 5cd1e3dd (`aot42/*`). Each class below gets a root-cause hypothesis, its evidence, a fix and a verification method. They are ordered by the outer loop's priority: first what blocks "tap a feed item, read the article", then what burns CPU.

| # | Signature | Root cause | Fix | R2 |
|---|---|---|---|---|
| 1 | RenderThread SIGSEGV@0, `libwebviewchromium.so` vaddr `0x1e006f0` (cppcrash `+0x3e026f0` / `+0x26016f0`) | shim `dlopen()` opens `libGLESv2.so` before its §734 GLES translation → NDK facade → GrContext NULL → Chromium 109 flushes NULL in `~SkiaOutputSurfaceImplOnGpu` | **built**: westlake `fix/webview-gles-order-46` `87fb17b`, shim `ecc7b12c…` | symbolization verified; cause partially; fix unverified |
| 2 | `npth-dumper-thr` spins at one full core (≈45% of process samples) | libnpth's "dump pthread" routine (`0x17930`) walks Bionic's thread list `x = *x`; musl `struct pthread` offset 0 is `self` | **built**: one-instruction patch, `libnpth.so` `8b8d559c…` | verified (static + outer-loop live sample); patch unverified |
| 3 | `work_thread` SIGABRT, empty backtrace | a **forked child**, not the app: Umeng ZID's root probe (`libumeng-spy.so` `getNativeID`) forked from Umeng's `work_thread` HandlerThread | none needed for the app; abort site inside the child needs one experiment | partially |
| 4 | `TicketGuardNetw` SIGSEGV@0x28 (#42 verify-r2b) | `libttboringssl.so` (BoringSSL ABI) calls `HMAC_Init_ex`, which resolved to OH's OpenSSL 3 `libcrypto_openssl.z.so`; its `HMAC_CTX_init` came from `libttcrypto.so` | experiment: load the tt crypto pair as Android-ABI targets | partially |
| 5 | `PatchUpdateMana` → shadowhook → `calloc` → `__libc_malloc_impl+1332` writes NULL (#42 prerun) | heap already corrupt; the corrupter is unknown | experiment | unverified |
| 6 | post-WebView-fix SIGTRAP/TRAP_BRKPT on `ThreadPoolForeg` (first article with a video) | hollow MediaCodec from `native_setup` + unregistered `getOwnCodecInfo` → `UnsatisfiedLinkError` (an Error) → Chromium FATAL `jni_android.cc(315)` + `brk` | **built**: westlake `fix/mediacodec-unsupported-46` `ddb2f48`, bridge `d4fae8e5…` | cause verified; fix unverified |

What was wrong before #46:
- The memory rule "cppcrash rel-pc minus 0x2002000 = `libwebviewchromium` vaddr" held only for cold-a4. The rel-pc base differs per run: verify-1 needed `0x801000`. Compute vaddr from the absolute pc minus the r-xp mapping at file offset 0.
- "work_thread SIGABRT in every run" was counted as an app crash. It is a child process, `pid == tid == 13890` (x20/x21) against app pid 10823, and the app keeps logging afterwards.
- The npth loop sits in a stripped function at `0x17930`. The name "JNI_OnLoad+0x79f0" is only objdump's nearest symbol, because the library has no symbols past `JNI_OnLoad`.

## 1. WebView RenderThread SIGSEGV — the only measured blocker on the article page

Full symbolization and chain: [evidence/webview-renderthread.md](evidence/webview-renderthread.md). Raw material: [evidence/webview-renderthread-raw.txt](evidence/webview-renderthread-raw.txt).

- **Symbolization (verified).** Both cppcrashes resolve to vaddr `0x1e006f0`: `GrDirectContext::flush`, first load `ldr x8,[x0]` with x0 = NULL. The frames above it are `~SkiaOutputSurfaceImplOnGpu` ← `SkiaOutputSurfaceImplOnGpu::Create` (`Initialize()` failed) ← `TaskQueueWebView::ScheduleOnVizAndBlock` ← `DrawFn_DrawGL` ← plat_support `draw_gl` ← hwui `GLFunctorDrawable::onDraw`. Engine sha256 `27c34ff4…` on the board, identical to `out-sp20/webview-candidate`. The 22 Chromium frames differ between the two runs by a constant `0x1801000`.
- **Frequency (verified).** The four-line GL-failure signature appears in 12 runs, and every one of them opened `NewDetailActivity`. 13 runs opened it in total; the 13th, trace-1, ends before the first frame. The process dies 10–153 stderr lines after the signature. See [evidence/crash-run-map.txt](evidence/crash-run-map.txt). The four lines:
  - `InitializeGL failure max_vertex_attribs : 0`
  - `nullptr GL version string`
  - `Failed to initialize extensions`
  - `GrGLInterface creation failed`

  So the first article frame always crashes. The same signature accounts for **5 of the 9 #42 formal signal-11 deaths**: base r1–r3 and speed r2–r3, all after the item tap.
- **Cause.**
  - `framework/webview-shim/webview_bionic_shim.c` `dlopen()` runs its `.z.so` probe before the §734 block. The probe `real_dlopen("libGLESv2.so")` succeeds from `/system/lib64/ndk` and returns.
  - The translation to `/system/lib64/platformsdk/libGLESv3.so` is therefore dead code:
    - `GLES library translated` appears in 0 of 50 child.stderr files;
    - `ndk/libGLESv2.so` is in the maps;
    - in the deployed binary (= `ae6ac828`, reproduced byte for byte), the `.so` suffix test branches into the probe (`0x5650 → 0x56fc`) ahead of `strcmp(…,"libGLESv2.so")` (`0x5660`). See [evidence/webview-shim-fix.txt](evidence/webview-shim-fix.txt).
  - The §734 comment records that the facade leaves `glGetString` NULL on OH. That matches the signature, but was not re-measured here (**partially**).
- **Existing switches do not avoid it.**
  - `--single-process` (#20) and `--disable-features=AndroidSurfaceControl` (#10/#17 default) were both active in the crashing runs (cold-a4 child.stderr L1668–1669).
  - `WESTLAKE_WEBVIEW_GPU_MODE=in-process` only swaps the AndroidSurfaceControl switch for `--in-process-gpu`. The DrawGL functor still builds its context on RenderThread through the same `libGLESv2.so`, and #10 already saw that mode reintroduce the SurfaceControl SIGTRAP.
  - `software` (`--disable-gpu-compositing`) does not remove the functor's GL context. It is untested.
- **Fix (built, not on a board).**
  - Change: move the §734 block ahead of the probe. The "library resolved" block was moved for the identical reason and the file's comment says so.
  - Source: westlake branch `fix/webview-gles-order-46` @ `87fb17b` (worktree `~/a2hlab/ws/westlake-wv46`, base 22b9453; the file is byte-identical in 22b9453, ability38 and out-sp20).
  - Build: `scripts/build_shim.sh` → `~/a2hlab/ws/out-wv46/patched/libwebview_bionic_shim.so`, sha256 `ecc7b12c3591c979f3d9aece5bb1d414acc04d01d2c500a88364525082f9df9f`. Exports and DT_NEEDED are unchanged. The same script on unchanged source reproduces the deployed `ae6ac828` exactly.
  - Deploy: overlay the file onto the candidate's `webview-t-lib/` by hand, because the packager drops shim fixes.
- **Verify on a board.** Open an article at least 3 times; each run must satisfy:

  | Check | Expected |
  |---|---|
  | `grep -c 'GLES library translated libGLESv2.so -> /system/lib64/platformsdk/libGLESv3.so' child.stderr` | 1 |
  | `grep -c 'GrGLInterface creation failed' child.stderr` | 0 |
  | `grep -c 'InitializeGL failure' child.stderr` | 0 |
  | `grep -c 'ndk/libGLESv2.so' /proc/<pid>/maps` | 0 |
  | process 60 s after the tap | alive, no RenderThread cppcrash |
  | after-15s screenshot | article body |

  If GrContext still fails with platformsdk GLES, the next step is software draw. That is an experiment, not an existing switch.

## 2. npth-dumper-thr spin

The outer loop confirmed the loop live: 61b06572, pid 29135, 100% of samples at `0x179c0–0x179c8`. Supporting disassembly: [evidence/npth-disassembly.txt](evidence/npth-disassembly.txt).

- **Loop (verified).** The routine at `0x17930` does:
  - `x21 = pthread_self(); do { x22 = x21; x21 = *x21; } while (x21);` to reach the list tail;
  - then it walks `[x19+8]`.

  Bionic's `pthread_internal_t` is `{next@0, prev@8, tid@16}`. OH 6.1 musl's `struct pthread` (aarch64, `TLS_ABOVE_TP`) is `{self@0, prev@8, next@16, sysinfo@24, tid@32}`, read from the exact 6.1.0.31 tree on hw248. `*self == self`, so the first loop never ends. musl's list is also circular, so the second loop would not end either.
- **Who reaches it.** Its three callers are:
  - the native crash dump sequence and a second dump sequence (`dump fds` → `dump pthread`);
  - the native-info dump dispatcher (`0x28bfc`). There, one-shot latches run each item once, and item `+32` is dump pthread, followed by `PriorityMonitor`/`anr/priority_jstack.txt`.

  So the spin starts on npth's first crash or ANR dump, not at load. In cpu-detail-1 the dumper thread was created at uptime ≈78450.9 s, inside an 8 s main-thread stall (TOUCH21 queue gap 78447.6→78455.7 s). That is consistent with npth's ANR watchdog; the trigger is a hypothesis.
- **Nothing else in npth walks the list (verified).** The other `pthread_self()` users are:
  - `0x12694` and `0x1584c`: only `pthread_setname_np`;
  - `0x176d0`: a bounded probe that scans `pthread_self()+16` up to the page end for stack and altstack fields, and stores −1 if it finds nothing.

  No other `libnpth_*.so` dereferences `pthread_self()` at offset 0.
- **Is libnpth needed?** Not for the product; it is ByteDance's crash reporter. **Deleting or refusing it is unsafe (static)**: `System.loadLibrary("npth")` in `X.BEd.<init>` propagates through `Npth.init` to `ArticleApplication.attachBaseContext` / `delayInitAfterAgreement`. Every catch on that path is a `monitor-exit; throw` handler, so an `UnsatisfiedLinkError` would abort application start. No library has `DT_NEEDED libnpth.so`; others need only `libnpth_dl/bt/unw*`. See [evidence/dex-and-load-chains.txt](evidence/dex-and-load-chains.txt). Do not add it to the shim's refused list.
- **Options.**
  - **(A) Built:** `scripts/patch_npth.py` replaces `0x17930` `stp x29,x30,[sp,#-96]!` with `ret`.
    - The callers ignore the return value (`0x193a4`/`0x19ac4` reload x0; `0x28d14` does not read it). Dump pthread becomes empty and everything else in npth is unchanged.
    - The script is gated on input sha256 `10641147…` and the original bytes.
    - Output `~/a2hlab/ws/out-npth46/libnpth.so`, sha256 `8b8d559c50130a997b5fbf3383e8ebf6291ebe54ab2b5ed5fbc8e1ac73fe36af`, 4 bytes differ.
  - **(B)** A `JNI_OnLoad`-only stub keeps `isSoLoaded` false, but 15 native call sites, one each in 15 methods, are not guarded by it in their own method (ANR profiler, `NativeResourceMonitor`). This needs an experiment.
- **Verify on a board.** Stage the patched `libnpth.so`, first checking with `sha256sum` that the staged original is `10641147…`. Then:
  - after 60 s, `/proc/<pid>/task/*/stat` for `npth-dumper-thr`, if the thread exists, shows state S/D and utime growth < 1 s per 10 s;
  - in hiperf, `npth-dumper-thr` < 1%;
  - consent, feed and item tap do not regress.

## 3. work_thread SIGABRT — Umeng's forked root probe

Evidence: [evidence/umeng-spy-disassembly.txt](evidence/umeng-spy-disassembly.txt), [evidence/dex-and-load-chains.txt](evidence/dex-and-load-chains.txt).

- **It is a separate process (verified).**
  - The banner registers come from npth's handler re-raising with `rt_tgsigqueueinfo(getpid(), gettid(), SIGABRT, info)`, `x8 = 240`. x20 and x21 hold getpid() and gettid(), both 13890; the app is 10823.
  - The banner itself is ART's `HandleUnexpectedSignalCommon` (`Cmdline: <unset>`, `Fault message:`), which ran after npth's handler.
  - x23 is the handler's `TPIDR_EL0`. It lies in a 32 MB anonymous stack mapping, so the forking thread was a Java thread.
  - The original signal was SIGABRT with `SI_TKILL`, i.e. `abort()`/`raise`, because npth re-queues the siginfo verbatim.
- **Which child (partially).**
  - The only literal `"work_thread"` in the APK is `com.umeng.mc.e`'s HandlerThread.
  - Its handler runs `com.umeng.mc.f.a` → `f.b` → `com.umeng.umzid.Spy.a` → `Spy.getNativeID(SDK_INT >= 29)`.
  - `libumeng-spy.so` does:
    - `pipe`;
    - `signal(SIGCHLD, handler)` when the argument is true; the handler loops `waitpid(-1, …, WNOHANG)` and so reaps **every** child in the process;
    - `fork`;
    - parent: `select` with a 1 s timeout;
    - child: `access()` on 8 `su` paths, `stat` of `/data/data`, `/data/`, `/data/app`, reads `/proc/sys/kernel/random/boot_id`, three `popen("getprop …")` (no `getprop` on OH), `write` to the pipe, `sleep(2)`, `_exit(0)`.
  - npth's own fork path (`nativeDumpHprof`: `ScopedGCCriticalSection` + `ScopedSuspendAll` + `fork` + child `art::hprof::DumpHeap`, reached from `com.bytedance.memory` HeapDumper when `runStrategy == 2`) is the other forker in the APK. It is less likely: it needs a heap-threshold trigger, while the SIGABRT happens exactly once in every run.
- **Impact.** The app process survives; the child dies. It is not user-visible, but the process-wide SIGCHLD reaper can steal other children's exit status.
- **Open (experiment).** The abort site inside the child. Cheapest way to pin it: an `abort()` interposer in the already-preloaded shim that writes `__builtin_return_address(0)`, the thread name and the pid to fd 2 before aborting. That yields the caller DSO+offset in one run.

## 4. TicketGuardNetw SIGSEGV@0x28

Evidence: [evidence/ticketguard-hmac.txt](evidence/ticketguard-hmac.txt).

- **Symbolization (partially).** pc and lr fall in `/system/lib64/chipset-sdk-sp/libcrypto_openssl.z.so`. hw248's OH 6.1.0.31 build has the identical PT_LOAD layout (file offsets, vaddrs and segment sizes). The hash was not compared with the board. The frames are:
  - pc `0x21e524`: `evp_md_init_internal`, `ldr x9,[x0,#0x28]` with x0 = NULL;
  - `EVP_DigestInit_ex`;
  - lr `0x247e74`: `HMAC_Init_ex` at `hmac.c:79` (`EVP_DigestInit_ex(ctx->i_ctx, …)`); the digest is `sha256_md`.
- **Mechanism (partially).**
  - `libttboringssl.so` imports `HMAC_CTX_init`, `HMAC_CTX_cleanup`, `HMAC_Init_ex`, `HMAC_Update` and `HMAC_Final`, and has `DT_NEEDED libttcrypto.so`, ByteDance's BoringSSL, which defines all of them.
  - OH OpenSSL 3 exports `HMAC_Init_ex` but not `HMAC_CTX_init` or `HMAC_CTX_cleanup`. With `libcrypto_openssl.z.so` already in the global scope, the calls split between two ABIs.
  - BoringSSL's embedded `HMAC_CTX`, zeroed by its `HMAC_CTX_init`, is read by OpenSSL 3 as `{md, md_ctx*, i_ctx*, o_ctx*}`, giving `i_ctx` = NULL and a fault at `+0x28`.
  - The caller is inferred: it is the only APK library importing `HMAC_Init_ex`, and the banner has no backtrace.
- **Fix (experiment).** Add `libttcrypto.so:libttboringssl.so` to `WESTLAKE_ANDROID_NATIVE_TARGETS`, plus their other importers `libdelta.so` and `liblynxsecurity.so`. First confirm with `probes/runtime-resolve` which file answers `HMAC_Init_ex` for `libttboringssl.so`. The assertion is that `libttcrypto.so` answers.

## 5. PatchUpdateMana → shadowhook → calloc

The #42 speed-1/2 preruns (105 s / 88 s) crashed in `calloc(0xc20)` from `libshadowhook.so`: `__libc_malloc_impl+1332` writes address 0 (esr `0x92000047`, WnR). That is a symptom of prior heap corruption, and the offline evidence does not say who corrupted the heap. It needs the crash census's full stacks or an allocator-debug run. **unverified**.

Unattributed: #42 verify-r1, verify-r3 and speed-r1 died before the item tap with no banner and no cppcrash. verify-r3 carries only the child SIGABRT. These are left to the crash census.

## 6. After the WebView fix: SIGTRAP on the first article with a video

codex-2 put shim `ecc7b12c` on 5ea34a45 (`ability38/wv46-articles-*`). Two article bodies rendered and every §1 assertion passed. About 54 s after the second article resumed, the child died with `Fatal signal 5 (SIGTRAP), code 1 (TRAP_BRKPT)` on tid 20753 `ThreadPoolForeg`, and parent logged `child 18719 killed by signal 5`. Evidence: [evidence/sigtrap-mediacodec.txt](evidence/sigtrap-mediacodec.txt).

- **Cause (verified).**
  - Tid 20753 first logs `No implementation found for … MediaCodec.getOwnCodecInfo()`, then `java.lang.UnsatisfiedLinkError` under `MediaCodec.getCodecInfo` ← `org.chromium.media.MediaCodecUtil` ← `MediaCodecBridgeBuilder.createVideoDecoder`, then `[FATAL:jni_android.cc(315)] Please include Java exception stack in crash report`.
  - The banner is that same tid. x7, x12 and x13 still hold the formatted message text (`ni_andro`, `in crash`, ` report\n`).
  - In the deployed engine `27c34ff4…`, the only `brk #0` whose page offset (`0xcd4`) and LR distance match is vaddr `0xe3ccd4`. It is Chromium's `IMMEDIATE_CRASH` (`brk #0; hlt #0`) at the end of the stderr-writing FATAL path.
  - 4 video-decoder attempts in the run hit the same Error.
  - **Unrelated to TicketGuard/HMAC**: different thread, signal and library.
- **Why the Error reaches native.**
  - `framework/core/jni/oh_mediacodec_shim.cpp` bridges only OH audio decoders, and its `native_setup` never fails. For a type OH cannot create it logs `CreateByMime failed` and hands Java a codec with nothing behind it.
  - Chromium's `createDecoder` therefore "succeeds" and calls `getCodecInfo()`, whose native `getOwnCodecInfo` the shim never registered. 32 of AOSP 14's 50 `MediaCodec` natives are unregistered.
  - `UnsatisfiedLinkError` is an `Error`, not an `Exception`, so Chromium's `catch (Exception)` misses it.
- **Fix (built).** westlake branch `fix/mediacodec-unsupported-46` @ `ddb2f48` (worktree `~/a2hlab/ws/westlake-mc46`, base 22b9453; the file is identical in ability38).
  - `native_setup` throws what AOSP throws: `IllegalArgumentException("Failed to initialize <type>, error 0xfffffffe (NAME_NOT_FOUND)")` when OH has no codec for the type, `IOException` when the OH codec library is unavailable. Chromium catches both and plays no video; the article is untouched.
  - `getOwnCodecInfo` is registered on its own, returning null. AOSP's `getCodecInfo()` then asks `MediaCodecList`, which the shim implements.
  - The succeeding `audio/mpeg` path is unchanged.
  - `scripts/build_bridge_mc.py` reuses the exact compile flags and link line of `out-ability38/native-stack`, the build of the deployed bridge. The untouched object and the untouched relink reproduce `06c0e052` and `e4ab5de6` byte for byte.
  - Output `~/a2hlab/ws/out-mc46/patched/liboh_adapter_bridge.so`, sha256 `d4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b`. Exports, imports and DT_NEEDED are unchanged.
- **Verify on a board.** Replace `liboh_adapter_bridge.so` in the stage, keeping shim `ecc7b12c`. Open ≥3 articles, including one with a video, and require:

  | Check | Expected |
  |---|---|
  | `grep -c 'getOwnCodecInfo()' child.stderr` | 0 |
  | `grep -c 'FATAL:jni_android.cc(315)' child.stderr` | 0 |
  | `grep -c '^Fatal signal 5' child.stderr` | 0 |
  | `grep -c 'Failed to initialize video/' child.stderr` | ≥ 1 (Chromium's "Failed to create MediaCodec" log carries the exception) |
  | the video article | body still shown |
  | process 120 s after the tap | alive |
  | noice (MP3 through `audio/mpeg`) | still plays |

  Residual risk: a type OH can create, e.g. AAC audio, will reach more of the 31 still-unregistered natives. If one is called, the same FATAL follows. Registering the rest with AOSP-equivalent `IllegalStateException` bodies is the follow-up.

## Rules this adds

- Compute a stripped library's vaddr from the absolute pc minus the base of its r-xp mapping at file offset 0. faultloggerd's rel-pc base varies by run.
- A `Fatal signal` banner whose thread is not in the app's task list is a child process. Check x20/x21 against the app pid before counting it as an app crash.
- In `webview_bionic_shim.c` `dlopen()`, every name translation must precede the `.z.so` probe, because the probe returns the plain name whenever it opens. This is the second instance of this bug.
- Never delete or refuse an app library whose `System.loadLibrary` is unguarded on the Application path. Patch or stub it.
- A framework native that the runtime does not implement must fail the way AOSP fails, with the Exception type AOSP throws, or not exist on a reachable path. A hollow success defers the failure to an unregistered native, and `UnsatisfiedLinkError` escapes every `catch (Exception)`. In Chromium that means FATAL + `brk`.
- The npth fix is to leave musl's `pthread_self()` alone and neutralise the one Bionic-layout walk. No Android-ABI library can be given a Bionic `pthread_internal_t`.

## Layout

| Path | Contents |
|---|---|
| `evidence/webview-renderthread.md`, `-raw.txt` | WebView symbolization, frame table, frequency, fix, R2 |
| `evidence/webview-shim-fix.txt` | westlake diff, hashes, dlopen control flow before/after |
| `evidence/npth-disassembly.txt` | loop, callers, dispatcher, bounded probe, fork heap-dump path, re-raise, child signal reset |
| `evidence/umeng-spy-disassembly.txt` | `getNativeID` annotated, child probes |
| `evidence/dex-and-load-chains.txt` | dex call chains (heap dump, Umeng, `loadLibrary("npth")`), `isSoLoaded` guard scan, DT_NEEDED |
| `evidence/ticketguard-hmac.txt` | banner, maps, OH OpenSSL symbolization, export comparison |
| `evidence/crash-run-map.txt` | per-run signatures, #38 and #42 |
| `evidence/sigtrap-mediacodec.txt` | post-fix SIGTRAP: stderr, banner, engine trap site, unregistered natives, westlake diff, rebuild hashes |
| `scripts/` | `build_shim.sh`, `patch_npth.py`, `build_bridge_mc.py`, `make_evidence.sh`, and the dexdump/objdump helpers `strs.py`, `callers.py`, `guard.py`, `webview-fnstr.py` |
| `results.json` | machine-readable summary |
