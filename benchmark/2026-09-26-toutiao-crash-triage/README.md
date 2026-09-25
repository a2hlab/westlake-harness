# Toutiao crash triage (#46/#48): eight signatures, four fixes, three root-caused

Every saved Toutiao run on the OH boards crashes. #46 triaged the existing evidence offline, with no board time: 19+ #38 runs on board 5ea34a45 (`ability38/*`) and the #42 runs on board 5cd1e3dd (`aot42/*`). Each class below gets a root-cause hypothesis, its evidence, a fix and a verification method. They are ordered by the outer loop's priority: first what blocks "tap a feed item, read the article", then what burns CPU.

| # | Signature | Root cause | Fix | R2 |
|---|---|---|---|---|
| 1 | RenderThread SIGSEGV@0, `libwebviewchromium.so` vaddr `0x1e006f0` (cppcrash `+0x3e026f0` / `+0x26016f0`) | shim `dlopen()` opens `libGLESv2.so` before its §734 GLES translation → NDK facade → GrContext NULL → Chromium 109 flushes NULL in `~SkiaOutputSurfaceImplOnGpu` | **built**: westlake `fix/webview-gles-order-46` `87fb17b`, shim `ecc7b12c…` | symbolization verified; cause partially; fix unverified |
| 2 | `npth-dumper-thr` spins at one full core (≈45% of process samples) | libnpth's "dump pthread" routine (`0x17930`) walks Bionic's thread list `x = *x`; musl `struct pthread` offset 0 is `self` | **built**: one-instruction patch, `libnpth.so` `8b8d559c…` | verified (static + outer-loop live sample); patch unverified |
| 3 | `work_thread` SIGABRT, empty backtrace | a **forked child**, not the app: Umeng ZID's root probe (`libumeng-spy.so` `getNativeID`) forked from Umeng's `work_thread` HandlerThread | none needed for the app; abort site inside the child needs one experiment | partially |
| 4 | `TicketGuardNetw` SIGSEGV@0x28 (#42 verify-r2b) | a default-namespace **second copy** of the tt BoringSSL pair binds `HMAC_Init_ex` to OH's OpenSSL 3 (load-order lookup); `HMAC_CTX_init` (absent from OpenSSL 3) stays in `libttcrypto` — mismatched HMAC_CTX | **config, no rebuild**: Fix A targets `+cjtfccsm +delta` (run `22c1d3df`) for NativeLoader paths, Fix B `LD_PRELOAD libttcrypto` (run `33b4ab08`) for the native-dlopen video path | split + 10 unroutable dependants verified; LD_PRELOAD viability verified; effect unverified |
| 5 | `PatchUpdateMana` → shadowhook → `calloc` → `__libc_malloc_impl+1332` writes NULL (#42 prerun) | heap already corrupt; the corrupter is unknown | experiment | unverified |
| 6 | post-WebView-fix SIGTRAP/TRAP_BRKPT on `ThreadPoolForeg` (first article with a video) | hollow MediaCodec from `native_setup` + unregistered `getOwnCodecInfo` → `UnsatisfiedLinkError` (an Error) → Chromium FATAL `jni_android.cc(315)` + `brk` | **built**: westlake `fix/mediacodec-unsupported-46` `ddb2f48`, bridge `d4fae8e5…` | cause verified; fix unverified |
| 7 | SIGTRAP/`brk` on `Chrome_InProcRe` (in-process renderer), engine `0x37cfec8` | Blink PartitionAlloc (blink/blink_style) recommit `mprotect(PROT_RW)` fails after the renderer's memory climbs unbounded (~200 MiB/min, RSS 0.86→2.06 GiB over three videos) — in-process because `--single-process` (#20) means the renderer never exits to return it | **no build; run-env + route**: raise the board's mapping/commit ceiling before launch (mitigation), multiprocess renderer (root, needs child-service spawn) | handler + growth verified; exhausted resource (mapping-count vs commit) partially; mitigation unverified |
| 8 | main-thread NPE → `ActivityThread.main` returns → `_exit(1)`, ~100–126 s (#48, non-signal) | metasec's `System.load` of its rewritten private copy `/data/data/<pkg>/app_lib/libmetasec_ml.so` gets errno13 (EACCES on an executable mapping of an app-private file) on the shared `platform-back-handler` godzilla thread; the uncaught `UnsatisfiedLinkError` kills that thread; ~100 s later `X.DEv` builds a Handler on `getBackgroundHandlerThread().getLooper()` = null | **config/loader, not a rebuild here**: reuse the loaded asx copy for the app_lib load (T1, needs core-runtime change + board check); errno13 itself is OH SELinux/mount, not libc | chain verified; T1 effect + metasec self-check unverified; root fix not Bionic-only |

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

## 7. TicketGuard HMAC split: make the app's BoringSSL pair exist once, in the Android namespace

Evidence: [evidence/tt-namespace.txt](evidence/tt-namespace.txt). This refines §4.

- **Two copies (verified).** One process (`wv46-articles-3` maps) maps **two** images each of `libttboringssl.so`, `libttcrypto.so` and `libsscronet.so`, and one `libcrypto_openssl.z.so`.
  - `libsscronet.so` is an Android-ABI target: `System.loadLibrary` routes it into the isolated `westlake_android_app` namespace (`dlopen_ns`, inheriting only libc/libdl/libm/libz/liblog), and its DT_NEEDED pair loads there.
  - Non-target libraries that also need the pair load with plain `dlopen(RTLD_LOCAL)` in the default namespace, and their DT_NEEDED pair loads a second time there. #42 verify-r2b loaded `libdelta.so` this way.
  - `WESTLAKE_ANDROID_NATIVE_TARGETS` routes only `System.loadLibrary` calls. It cannot move a DT_NEEDED dependency of a default-namespace library.
- **Why only the default copy splits (verified from OH source).** OH 6.1.0.31 musl `do_relocs` resolves every import by walking the global DSO chain **in load order**. Each DSO it visits is either global (exe, preload, ldso) or a dependency of an earlier dlopen that `check_sym_accessible()` says is visible from the relocating DSO's namespace (`dynlink.c` 614–631, 735–760, 1070–1086).
  - For the default copy, `libcrypto_openssl.z.so` (default namespace, loaded earlier) is visible and first. `HMAC_Init_ex`, `HMAC_Update` and `HMAC_Final` bind to OpenSSL 3. `HMAC_CTX_init` and `HMAC_CTX_cleanup` exist only in `libttcrypto.so`.
  - For the namespace copy, OpenSSL 3 is not visible and everything binds to `libttcrypto.so`. Cronet's TLS, which runs on that copy, works; the feed loads.
  - A BoringSSL-layout `HMAC_CTX` handed to OpenSSL 3 reads `i_ctx` = NULL and faults at `+0x28`, exactly the crash.
  - The caller is identified by elimination (**partially**). Only a default-namespace copy can reach OpenSSL 3's `HMAC_Init_ex`, and `libttboringssl.so` is the only APK importer of it.
- **Why the first target attempt did not hold (verified).** `four46-fresh2` deployed a 4-target run.sh (`libttcrypto`, `libttboringssl`, `libdelta`, `liblynxsecurity`); the pair was **1 image at consent** but the outer loop saw 2 again once videos played. Adding a library name to `WESTLAKE_ANDROID_NATIVE_TARGETS` only routes it if it arrives through NativeLoader (`System.loadLibrary`); it does nothing for a library a native `dlopen` pulls in. `scripts/tt_cover.py` crosses the 15 direct DT_NEEDED dependants of the pair with the 63 libraries this run actually took through NativeLoader:
  - **4 have a NativeLoader root** — `libcjtfccsm`, `libdelta`, `liblynxsecurity`, `libsscronet` — so a target moves them into the namespace.
  - **10 have no NativeLoader root** — `libbdvideouploader`, `libmffmpeg`, `libropaencrypt`, `libtt_cnpa_sdk`, `libttmverify`, `libttmverifylite`, `libvcn`, `libvcnverify`, `libvcnverifylite`, `libxbnlog` — reachable only by a native `dlopen` (the video path: `ttmplayer`/`vcn`/`mffmpeg`), which no target can route. This is why the second image reappeared during video playback, and it is a hard limit of the target mechanism, not a missing name.
- **Fix A — complete the routable set (no rebuild, necessary but not sufficient).** Add the two missing NativeLoader roots `libcjtfccsm` and `libdelta` (`libsscronet`, `liblynxsecurity` already targets). `scripts/apply_tt_targets.py` on the wv46 run.sh (`65530f5c…`) gives `~/a2hlab/ws/out-tt46b/run-targets.sh`, sha256 `22c1d3df6529210fde522436a08643afea4d1791ebb6275df952a8c986f32e0f`, 21 targets. This removes every NativeLoader-path second copy, but the 10 native-`dlopen` dependants can still create one during video playback.
- **Fix B — LD_PRELOAD the app's BoringSSL (no rebuild, closes the gap).** Every HMAC/EVP symbol is **unversioned** on all three sides (app `libttcrypto` exports, app `libttboringssl` imports, OH `libcrypto_openssl` exports; OH exports `HMAC_CTX_new` but not `HMAC_CTX_init`, which OpenSSL 3 removed). So one `libttcrypto.so` placed first in `LD_PRELOAD` — it self-contains HMAC + EVP with DT_NEEDED only libc/m/dl — makes **every** unversioned HMAC/EVP reference in the default namespace bind to BoringSSL, whichever way its consumer was loaded. The namespace copy is already all-BoringSSL, so it is unaffected. `scripts/apply_ld_preload.py` on Fix A's run.sh gives `~/a2hlab/ws/out-tt46b/run-combined.sh`, sha256 `33b4ab080b87ac7005e2495e1adbba4fd3407b53626138ae69846bfdebec312d` (both fixes together).
  - **Hijack risk is one library (verified scan).** A global BoringSSL could in principle re-bind an OH system library's HMAC. Of every OH `.z.so` in the app-process maps, only `libsqlite.z.so` imports HMAC unversioned; all others import none. So the only OH component whose HMAC would move to BoringSSL is SQLite, and only if Toutiao exercises SQLite's HMAC path. The existing `LD_PRELOAD` already carries two shims without harming OH libraries, so a global preload is an established shape here; this adds one entry and one narrow risk to check on the board.
- **What changes for the moved libraries (Fix A).** Non-APK deps resolve through the namespace search path: `libandroid`/`libjnigraphics` to the `webview-t-lib` copies (as the 19 current targets), `libstdc++` to `/data/local/tmp/asx`; only `libttmplayer` needs GL/audio, and `libGLESv2` already resolves to `/system/lib64/ndk/libGLESv2.so`. Recorded on the board below.
- **Verify on a board.** Apply Fix A first (cheap); if the pair is still 2 images during video, apply Fix B. On top of shim `ecc7b12c`, bridge `d4fae8e5`, patched `libnpth` `8b8d559c`:

  | Check | Expected |
  |---|---|
  | offset-0 r-xp images of `libttboringssl`, `libttcrypto`, `libsscronet` in `/proc/<pid>/maps`, sampled during a **video** article | 1 each |
  | `grep -c 'TicketGuardNetw' child.stderr` in a `Fatal signal` banner | 0 |
  | `[SOURCE-NATIVE-LOAD-FAIL]` for the added target names | 0 |
  | feed / Cronet TLS | loads |
  | Fix B only: SQLite-backed features (history, saved articles, login persistence) | work (SQLite HMAC not broken) |
  | article with a video, 5 min after the tap | alive |

  If Fix A alone leaves 2 images, that confirms the native-`dlopen` path and selects Fix B. The generic long-term follow-up is for the loader to route a library into the namespace whenever its DT_NEEDED closure intersects the target set, which would make Fix A sufficient on its own.

## 8. In-process renderer PartitionAlloc OOM (the fifth long-survival crash)

With the four fixes deployed, two of three video articles survived >120 s; the third crashed at ~99 s with a new signature. Evidence: [evidence/inproc-oom.txt](evidence/inproc-oom.txt).

- **Signature (verified).** `Fatal signal 5 (SIGTRAP)` on tid 6853 `Chrome_InProcRe` (Chromium's InProcessRendererThread). pc = `libwebviewchromium.so` file offset `0x37cfec8`, a `brk #0`. The instruction before it, at `0x37cfea4`, stores x0 (a pointer to the request size) into a global and calls the crash logger `Mqw5545M` — the same `IMMEDIATE_CRASH` shape as §6's mediacodec SIGTRAP, here the PartitionAlloc out-of-memory handler.
  - x1 = `0x9000` (36 KiB, the request), x2 = `3` = `PROT_READ|PROT_WRITE` (a recommit `mprotect`), x4 = `0x4000`.
  - x6/x7 decode to ASCII `blink,blink_styl…`: PartitionAlloc's partition tags `blink` and `blink_style`, i.e. this is the Blink allocator, not V8 or the disk cache.
  - So the renderer's Blink PartitionAlloc asked the kernel to commit another 36 KiB (`mprotect PROT_RW` on a page it had reserved `PROT_NONE`), the syscall failed, and PartitionAlloc's `CHECK` fired `brk`.
- **Unbounded growth (verified).** Across the three videos the process RSS climbs monotonically: video1 0.86→1.12 GiB (121 MiB/min), video2 1.08→1.58 (240), video3 1.63→2.06 (270), crash at ~2.06 GiB. VSZ is flat at 231 GiB — PartitionAlloc's one-time GigaCage reservation, not growth. Thread count is flat at ~400 (not a thread leak). The renderer's memory is not being returned between article navigations.
- **Why in-process matters (verified logic).** The fault thread is the in-process renderer. `--single-process` was forced by #20 because a sandboxed renderer process throws `child service doesn't exist` (still logged once here) and wedges the UI thread. With the renderer in the browser process, its Blink PartitionAlloc lives in the browser process's address space and is **never reclaimed by process exit** — in multiprocess Chromium, navigating away kills the renderer process and returns every one of its mappings and its RSS at once. In-process, each article's Blink objects, GPU transfer buffers and recommitted pages accumulate for the life of the app.
- **Which resource ran out (partially — needs one board experiment).** The recommit `mprotect(PROT_RW)` failed, but the run only sampled the address space at consent (5452 mappings). Two candidates, both driven by the same unbounded growth, and both consistent with the evidence:
  - **A. mapping count.** PartitionAlloc recommits many small ranges; each `mprotect` on a slice of a larger `PROT_NONE` reservation splits one VMA into three. OH's default `vm.max_map_count` is 65530. At ~200 MiB/min for ~350 s the count can climb from 5452 toward the ceiling, at which point `mprotect` returns `ENOMEM` with RSS still only ~2 GiB — matching a crash that early.
  - **B. physical / per-app commit.** RSS reaching a DAYU600 memcg or overcommit ceiling; the board's total memory was not in the device report. A self-inflicted `CHECK` (not an lmkd `SIGKILL`) means the `mprotect`/`mmap` syscall itself returned failure, which a hard memcg limit or strict overcommit produces.
  - Distinguish on the board: from launch, every 10 s read `wc -l /proc/<pid>/maps`, `VmRSS` and `VmSwap` from `/proc/<pid>/status`, and the app's `memory.current`/`memory.max` from its cgroup. Whichever curve hits its ceiling at ~99 s into video 3 is the bound. This is cheap and can run alongside the article taps.
- **Fixes / trade-offs.**
  - **Mitigation, no engine change (config).** If A, `board_setup.sh` raises `vm.max_map_count` (e.g. to 262144) before the app starts — the hdc shell is `su`/permissive, so `echo … > /proc/sys/vm/max_map_count` is applied per boot. If B, raise the app's memcg limit / `vm.overcommit_memory`. Either only defers the crash, but for a single-article read session it buys the survival the milestone needs. Verify by re-reading the same curve.
  - **Operator session.** The #45 watchdog already relaunches; folding "force-stop and rebuild the WebView every N articles" into it caps the accumulation without touching the engine.
  - **Root fix (route change, larger).** Restore the multiprocess renderer so navigating away returns its whole address space. That is blocked on `child service doesn't exist`: westlake must let the renderer spawn as a real sandboxed child (the #20 note). Until then in-process is unavoidable and the crash is only deferrable.
  - The engine is a fixed 109 prebuilt; its PartitionAlloc `CHECK` cannot be edited, so there is no single-object rebuild for this class — the lever is the run environment and the process model, which is why this section ships analysis + an experiment rather than a binary.
- **Verify on a board.** With the four fixes plus whichever mitigation A/B the experiment selects, open ≥5 video articles back to back and require: the mapping-count (A) or memcg (B) curve stays below its ceiling; no `Chrome_InProcRe` `Fatal signal 5`; RSS plateaus or the session completes; feed and non-video articles unaffected.

## 9. The sixth exit path (#48): metasec errno13 kills a shared thread, a later Handler reads its null Looper

With all five #46 fixes on the operator instance, articles render, but the process `_exit(1)`s (no signal) ~100–126 s in. Evidence: [evidence/metasec-exit-48.txt](evidence/metasec-exit-48.txt) (61b06572 `operator45/morning46/exit-6204.stderr`, and `exit-8881`).

The stack the outer loop quoted is **two independent events**, not one causal line. Separating them is the whole finding.

- **Event 1 — metasec errno13, non-fatal by itself (verified).** metasec loads its native library from two places: `/data/local/tmp/asx/lib/arm64-v8a/libmetasec_ml.so` (an executable location; #41 verified this copy loads) and `/data/data/com.ss.android.article.news/app_lib/libmetasec_ml.so` (the app-private dir). The app_lib load gets `failed to map library errno=13` (EACCES on an executable mapping of an app-private file). This throws `UnsatisfiedLinkError` on the **`platform-back-handler`** thread — godzilla's background `HandlerThread` (`X.AFG.<init>(I)` = `new HandlerThread("platform-back-handler", …)`), which `PlatformHandlerThread.getBackgroundHandlerThread()` returns. It appears **once** and is never retried; the thread's `NoQuitHandlerThread.run` has no catch, so the exception escapes and **the background thread dies**. metasec has been failing this way since consent; nothing crashes yet.
- **Event 2 — the actual exit, ~100 s later, on the main thread (verified).** A main-thread runnable (`X.DPb.run → X.DPS → X.DEv.n → X.DEv.<init>`) constructs `new Handler(PlatformHandlerThread.getBackgroundHandlerThread().getLooper())`. Bytecode `X.DEv.<init>` offsets 0x1f/0x23/0x27: `getBackgroundHandlerThread()` → `getLooper()` → `Handler.<init>(Looper)`. The background thread is dead, so `getLooper()` returns **null**, and `Handler.<init>` throws NPE (`Looper.mQueue` on null). It escapes `ActivityThread.main`, `Looper.loop` ends, `main` returns, and westlake's launcher `_exit(1)`s (`launchActivityThread returned unexpectedly`).
- **So X.DEv's null Looper is the *effect* (verified), not an independent bug.** metasec killed the shared background thread; the first component to later read that thread's Looper on the main thread hit null. "Only after a long read" = it takes that long for `X.DEv` (a bus-subscribed component) to be instantiated on the main thread.
- **Why westlake's existing errno13 retry did not save it (verified).** `OpenNativeLibrary` already retries `errno=13` via `FindPackagedCopy`, which reuses a same-name file on the ClassLoader search path **only when it is byte-identical (size + sha256)** to the app_lib copy. For metasec the retry never fired (0 `IDENTICAL-COPY` logs, exception still thrown): the app_lib copy is **not** identical to the asx/APK copy. A hardening SDK rewrites its private copy, so the sha256 guard — correct in general — cannot reuse it.
- **errno13 is OH policy, not libc (verified reasoning).** The refused path is under `/data/data/<pkg>/app_lib`, a `normal_hap` private directory; executable mapping there is denied by OH (SELinux `normal_hap` lacking `execute app_data_file`, or the dir mounted `noexec`). `/data/local/tmp/asx` is permissive, which is why the asx copy loads. This decision is in the kernel; swapping musl for Bionic does not change it. **The root fix is therefore not "Bionic-only".** Real Android's `untrusted_app` domain *does* allow executing from the app's data dir, so the full Android-runtime route (M3/M4) removes the errno13 by adopting that SELinux model — but that is the whole model, not the libc. In today's OH model, errno13 cannot be fixed inside the app; it can only be made non-fatal.
- **Treatments (do not change the SDK).**
  - **T1 — make the app_lib load non-fatal (short-circuits this exit).** Relax the errno13 retry for `libmetasec_ml.so` specifically: when the app_lib load fails EACCES, reuse the already-loaded asx image (`dlopen(asx, RTLD_NOLOAD)` handle) instead of requiring sha256 identity, so `System.load` returns non-null, no exception is thrown, and the background thread survives. This is a `link_stubs`/core-runtime change (rebuild + board check), not a run.sh edit. **Risk (the metasec pit):** the asx image is not the rewritten app_lib image, so if metasec self-checks the loaded path/inode it may reject it — but metasec's `DoLazyInit` already never runs on OH (#41), so the SDK is already inert; the only goal is to stop it killing the shared thread. Unverified until a board run.
  - **T2 — root the errno13 (out of app scope).** Allow executable mappings under app_lib (OH SELinux/mount). Weakens the OH security model; an operator/system decision, not a westlake change.
  - **T3/T4 — not viable.** The dead thread cannot be revived (an app thread whose `run` let an exception escape is gone; an `UncaughtExceptionHandler` runs *after* `run` ends), and re-entering `main` after its Looper died has no meaningful state.
- **Verify on a board (T1).** On top of the five fixes: `System.load(app_lib/libmetasec_ml.so)` returns non-null (no `platform-back-handler` `UnsatisfiedLinkError`); no `X.DEv` NPE; the process survives past 3 min on a video article; metasec-gated features (login/anti-fraud) are no worse than today (they are already inert). If metasec rejects the reused image, T1 is a dead end and the exit must be accepted until the Bionic/Android route lands.

## Rules this adds

- Compute a stripped library's vaddr from the absolute pc minus the base of its r-xp mapping at file offset 0. faultloggerd's rel-pc base varies by run.
- A `Fatal signal` banner whose thread is not in the app's task list is a child process. Check x20/x21 against the app pid before counting it as an app crash.
- In `webview_bionic_shim.c` `dlopen()`, every name translation must precede the `.z.so` probe, because the probe returns the plain name whenever it opens. This is the second instance of this bug.
- Never delete or refuse an app library whose `System.loadLibrary` is unguarded on the Application path. Patch or stub it.
- Separate the crash you see from the crash that killed you: an uncaught exception on a *shared* background thread has no visible effect until, much later, another component reads that thread's Looper/Handler and gets null. The banner names the second site; the cause is the earlier thread death.
- An in-process renderer never returns its memory: what a multiprocess Chromium reclaims by killing the renderer process accumulates for the app's lifetime, so any per-process ceiling (mapping count, memcg) is reached eventually. Sample the ceiling, don't guess which one.
- A library that must load in the Android namespace brings its whole reverse-dependency closure with it. Otherwise a default-namespace consumer loads a second copy, and OH musl's load-order lookup binds that copy's imports to whatever the default namespace loaded first.
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
| `evidence/metasec-exit-48.txt` | #48 sixth exit: metasec errno13 → dead background thread → X.DEv null Looper → _exit(1), with retry analysis |
| `evidence/inproc-oom.txt` | in-process renderer PartitionAlloc OOM: banner, register decode, handler disasm, RSS/VSZ/VMA curve |
| `evidence/tt-namespace.txt` | TicketGuard split: two images, OH musl lookup rule, closure, run.sh diff |
| `evidence/tt-rootfix.txt` | TicketGuard root fix: NativeLoader coverage, HMAC versioning, LD_PRELOAD hijack scan, both run.sh products |
| `evidence/sigtrap-mediacodec.txt` | post-fix SIGTRAP: stderr, banner, engine trap site, unregistered natives, westlake diff, rebuild hashes |
| `scripts/` | `build_shim.sh`, `patch_npth.py`, `build_bridge_mc.py`, `tt_closure.py`, `tt_cover.py`, `apply_tt_targets.py`, `apply_ld_preload.py`, `mem_curve.py`, `make_evidence.sh`, and the dexdump/objdump helpers `strs.py`, `callers.py`, `guard.py`, `webview-fnstr.py` |
| `results.json` | machine-readable summary |
