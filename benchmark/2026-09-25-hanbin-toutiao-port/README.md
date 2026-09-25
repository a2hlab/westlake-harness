# Toutiao on hanbin_adapter: what it reached, how, and what westlake can take

hanbin_adapter (`~/workspace/hanbin_adapter`) is another Android-on-OpenHarmony adapter that has Toutiao running. Board entry #35 asks four things:
- how far Toutiao really gets there;
- how it gets past `libmetasec_ml.so` and the musl thread layout;
- which pieces westlake can port;
- how its WebView, Cronet and image handling compare with our #17, #20 and #30.

This is a read-only study. hanbin is not a git repository; its newest Toutiao record is dated 2026-09-18. No board was used. Every claim below cites a file and line, and the key lines are quoted verbatim in `hanbin-evidence.txt`.

## The frame: why most of it does not port as is

| | hanbin | westlake |
|---|---|---|
| board | DAYU200 (RK3568), **32-bit** userspace, `/system/lib` | DAYU600, arm64 |
| OS | OpenHarmony 7.0.0.18, **self-built image** | **stock** OH 6.1.0.31; 47 system libraries hash-gated |
| Toutiao | **17.6.0**, `lib/armeabi-v7a` only (153 libs), sha256 `f4bd11fb…` | **13.9.0**, `lib/arm64-v8a` only (138 libs), sha256 `a1112a0c…` |
| libc in the app process | **real Bionic** libc and linker from `/system/android`, since 2026-08-03 ("方向二（Bionic）＝进程内单 libc", `app_fwk_bionic_design_v2.html:238`) | OH musl, plus a per-library Android-ABI namespace with a Bionic shim |
| deployment | installed into the system: its own zygote init service, 14 overwritten OH `.z.so` plus `file_contexts` and `system-sandbox.json` (`deploy/deploy_all_init.sh:66-76`), SELinux patches | everything under `/data/local/tmp`, launched from our host HAP |

The two code bases share an ancestor. Of westlake's 610-line `framework/package-manager/jni/apk_installer.cpp`, 597 lines appear verbatim in hanbin's current 1602-line file. westlake descends from hanbin's musl-era design, which hanbin has since retired. That is why hanbin's retired documents describe, one by one, the walls we are hitting now.

## What it settles

- **Toutiao really works on hanbin**, from 2026-08-14 on. The debug report records, with user sign-off, that the feed shows images and refreshes, tabs switch, articles open and videos play. What the traces prove on their own stops at "feed list drawn". The frequently cited "实测可用 2026-07-22" (`debug.md:35`) only checks that the `aa start` command is accepted. On 07-27 the process was in fact dead (`debug.md:61`).
- **hanbin never made metasec work on musl.**
  - What it did was stop using musl in the app process.
  - Its own ledger of the musl era ends with "当日七个假设全部证伪" and "后者的成因至今未定" (`libc_adaptation_directions.html:1156, 1252`).
  - In the Bionic era, metasec no longer appears in its reports at all.
- **"824" is not a TLS offset and not a fix.** It appears twice in hanbin, both times as an arm32 musl measurement (`libc_adaptation_directions.html` A.6.1):
  - `hi − tcb = 824`: the distance from the top of a musl thread-stack mapping to the thread descriptor, measured 3/3.
    - `debug.md:124`'s "900 vs 824, off by 76" is the same table's `tcb − pthread_t = 76`. The first measurement took `pthread_t` instead of the descriptor.
  - The metasec fault address = the library's load base − 824. Across five ASLR runs the difference is exactly 824, e.g. base `0xbf800000`, fault `0xbf7ffcc8`.
    - It is the start of a downward scan that follows a read of `/proc/self/maps` (A.6, lines 982 and 1154).
    - The hypothesis that the scan starts at a thread descriptor was falsified.
  - On our arm64 board codex measured TP − `pthread_self` = 392 (#23). No 824-based constant carries over, and nothing in hanbin uses 824 to repair metasec. It is a different crash from our #23.
- **Our #23 crash is a statically linked Bionic `vfork()`, and the dependency is narrow.**
  - In our arm64 metasec, exactly **two** instructions reach TLS slot 1 (`TLS_SLOT_THREAD_ID`, TP+8):
    - the vfork stub at 0x2043b8, which zeroes `cached_pid_` at +20;
    - a check at 0x10edc4 that compares slot 1 with `pthread_self()`.
  - Another 1456 instructions read the stack-protector canary at slot 5 (TP+0x28). See `metasec-tls-census.txt`.
  - hanbin's 32-bit metasec contains the same vfork stub (0x1bc064: slot 1 at TP+4, `cached_pid_` at +12).
- **hanbin once covered exactly that pattern, on arm32 only.**
  - It rebuilt OH musl so that `tp[1] = descriptor`, and reordered musl's `struct pthread` into Bionic field order (`musl_pthread_bionic_layout_design.html:366`).
  - The fix needed a modified system musl, and it did not rescue Toutiao.
  - hanbin's lesson: the next layers are the geometry of `/proc/self/maps`, and **shadowhook/xhook, which need the Bionic linker's `soinfo` and "永远无法初始化" on musl** (`libc_adaptation_directions.html:1237`).
  - Our APK uses shadowhook too: `libshadowhook.so` loads on the OH board (`sensor-online-1/child.stderr:17253`), and Android's logcat shows `shadowhook_tag: linker: call_ctors`, as recorded in #26.
- **Four of our Toutiao fixes are independently confirmed.**
  - hanbin hit the same ByteDance `TokenUtils` recursion as our #11 (report:1142).
  - It hit the same Chromium font-root crash (PI-59), which westlake already handles (`wl_fastlibc.cpp:376-380`).
  - It hit the same `std::__ndk1` class as #30 while still on musl, and fixed it the way #30 plans to.
  - It turns WebView multi-process off, like our #20, but at the Java level instead of on the command line.

## 1. How far Toutiao gets on hanbin (acceptance 1)

| Level | Reached | Evidence |
|---|---|---|
| L0 installed | yes | `apk_installation_design_v2.html:702` |
| L1 process starts | yes | all five traces; e.g. 09-14 fork at +27.66 s (`trace/README.txt:11`) |
| L2 Application + Activity | yes | 09-14 trace L62012 `makeApplication`, L167127 `performCreate MainActivity`, L409363 `performResume` |
| L3 first frame on screen | yes | 09-14 L699432 first `eglSwapBuffers`, L700296 `frameCommit success=1` |
| L4 feed chrome | yes | 09-14 L521052 `RV OnBindView` (11 items bound) |
| L5 real feed content over the network | yes (user sign-off) | report:993 "头条 feed 出图、可刷新；进程 19 条 ESTABLISHED 长连接稳定". The traces are consistent (network threads active, 80 `decodeBitmap` slices in the app process in the 09-14 run) but cannot prove what was on screen |
| L6 interactive | yes (sign-offs only) | tabs report:1052; article detail report:1487 "用户肉眼确认：详情页正常显示内容"; video report:3153. **No trace contains a touch** |
| L7 stable ≥5 min | one claim | report:1048 "清数据冷启后进程稳定存活 12 分钟以上" (08-18), never re-measured; traces cover at most 81 s |
| L8 performance-tuned | in progress | first pixel 14.0 s after spawn; OH Photos takes 2.8 s. Open complaints are slow launch, slow article open and janky scrolling (`app_performance_analysis_report.html:175`). Average CPU is 131% (:182). The 17.9 s main thread splits into 28% running, 39% page faults, 29% locks and GC (:184) |

The 2026-09-14/16/18 cold-start traces were captured to measure performance fixes:

| trace | first frame callback | first pixel | frames drawn | covers |
|---|---|---|---|---|
| 09-14 baseline | +14.7 s | +20.8 s | 27 | 64 s |
| 09-16 package-query cache (PI-70) | +12.6 s | +26.0 s | 11 | 81 s |
| 09-18 madvise, warm (PI-73) | +11.2 s | +15.2 s | 16 | 74 s |
| 09-18 madvise, after reboot | +16.7 s | not reached (trace cut) | 0 | 23 s |
| 09-18 speed-profile dexopt (PI-77) | +10.1 s | +14.0 s | 15 | 34 s |

Offsets are from the app process's first trace line, recomputed for 09-14: first `Choreographer#doFrame` at +14.65 s, first `eglSwapBuffers` at +20.8 s. In all of the traces the home screen stays static after launch.

hanbin's own figures use other markers:
- "home screen visible 17.9 s" (`trace/README.txt:12`) is a window-visibility time;
- "首帧 11.2→10.1 s" is the frame callback, not the first pixel.

Problems still open as of 09-18 (report):
- a plugin-framework thread block (PI-30);
- a WebView native crash (PI-35);
- a deferred detail-page window race (PI-42);
- the detail page rendering in only about one of three attempts (as of 08-24).

The path to "works" (report:802, 859, 993):
1. Launch failed until 08-11: the application class could not be instantiated.
2. A RenderThread "no surface" abort came about 27 s after launch, fixed 08-14.
3. The network was dead because of DNS, an empty network-callback specifier that OH rejected with 401, the CA store, and the INTERNET gid.

## 2. metasec and TLS: what hanbin did (acceptance 2)

hanbin went through two eras. Only the second one works for Toutiao.

**Era 1: musl + libbc (retired 2026-07-30…08-07).** Every mechanism is listed with its status:

| Mechanism | Files | Status | Needs OH system change |
|---|---|---|---|
| Rewrite each APK `.so` at install time: `DT_NEEDED libdl.so`→`libbc.so`, rename symbols (`pthread_self`→`Pthread_self`, `mmap`→`Mmap`), GOT patch | `framework/retired/package-manager-jni/so_symbol_rewriter.cpp`; `apk_installer.cpp:722-797` | retired; today libraries are extracted byte-identical (`apk_installer.cpp:11-14`) | yes (system installer, patched loader) |
| libbc: 181 Bionic-named exports (off_t, `__sF`, `pthread_attr` 24 vs 36 B, sigset, `pthread_getattr_np`) | `framework/bionic-compat/` | directory deleted | loader patch |
| **Shadow descriptor**: `bc_pthread_create` writes a Bionic-shaped `pthread_internal_t` into `tp[1]`; `bc_pthread_self` returns it | libbc | worked, but covered **6 of 93 threads**; ART's threads bypass libbc ("证伪二：影子覆盖面只有 6%", layout design:148) | no (app-side) |
| **musl `struct pthread` reordered into Bionic order, and `tp[1] = td` in `__copy_tls`**: tid@8, pid@12 = `cached_pid_`, errno@664 | `ohos_patches/third_party/musl/{pthread_impl.h, pthread_create.c, __init_tls.c, …}` (deleted), shipped as `/system/lib/ld-musl-arm-adapter.so.1` | built and verified, no regressions, **no effect on Toutiao**; `__arm__` only; only `tp[1]` aligned, because arm32 musl leaves just 8 bytes above TP (layout design:216, 366) | **yes** |
| ART dug a 4 KB dead page into every thread's live stack. `InstallImplicitProtection` assumes Bionic's guard-inclusive `pthread_getattr_np`; musl reports the stack without the guard. Fixed by `-Wl,--wrap=pthread_getattr_np` reporting `base − guard` (plus a 1 MB default stack) | `pthread_stack_compat.cpp` (deleted); compat design §9.7 | fixed; did not change metasec's crash | own libart build |
| ART fault handler registered in OH musl's special sigchain slot (`add_special_signal_handler`, not `…_at_last`, which aborts because Dfx owns the last slot) | `sigchain.cc.patch` (deleted) | retired | own libart build |
| In-process crash forensics through a sigchain special handler (the only tool that "真正破局"); `struct_offsets.sh` takes struct offsets from the compiler | `crash_forensics.cpp` (deleted); `build/retired/tools/struct_offsets.sh` (present) | tools | no |

What metasec actually did on hanbin (arm32):
- It read `/proc/self/maps`, then scanned downward from `load base − 824`, and faulted at the first unreadable page. Five ASLR samples showed zero deviation.
- Why that scan is harmless on a real device was never found.
- Separately, **shadowhook's safe/linker modules can never initialise on musl, and xhook cannot hook anything**, because both parse the Bionic linker's internal `soinfo` (`libc_adaptation_directions.html:1237`).
- Their conclusion: aligning the thread descriptor "只解线程描述符一类"; the rest is structural.

**Era 2: a single real Bionic in the app process (current, since 2026-08-03).**
- The zygote runs with `PT_INTERP=/system/android/bin/linker`. Bionic libc, libm, libdl and libc++ are built from unpatched source. OH client libraries are rebuilt against Bionic.
- The only Bionic changes are:
  - two hunks in `aosp_patches/bionic/linker/linker.cpp.patch`, pointing the linker's configuration and paths at `/system/android`;
  - `aosp_patches/bionic/libc/bionic/pthread_create.cpp.patch`, which raises caller-shrunk thread stacks to 2 MiB because app code runs interpreted (Cronet's "NetNormal" thread is 512 KiB).
- Configuration lives in `framework/zygote-x/config/{ld.config.txt, zygote.cfg}`.
- Because the app process runs real Bionic, metasec, shadowhook and every `std::__ndk1` library see what they expect. Nothing in the Era 2 reports mentions metasec again. We infer that the crash disappeared, but no document says "fixed".

**Offsets: hanbin's arm32 fix against our arm64 crash**

| | hanbin arm32 musl patch | our arm64 `#23` |
|---|---|---|
| slot 1 `TLS_SLOT_THREAD_ID` | TP+4 → musl descriptor | TP+8; codex measured 0 on normal OH threads and -1 on metasec's thread |
| `pthread_internal_t.tid` | +8 (musl field moved there) | +16 |
| `cached_pid_` / `vforked_` | +12 (musl pid moved there) | +20 (`str wzr,[x0,#0x14]` at 0x2043c0) |
| musl space above TP | 8 bytes; only `tp[1]` fits | 16 bytes (musl `GAP_ABOVE_TP`); TP+8 unused by musl, **to confirm on OH 6.1** |
| stack guard, slot 5 | not aligned (static TLS data) | 1456 canary reads at TP+0x28, which on musl is static TLS data. Harmless while the word is stable (79–84 s runs in #23 showed no `__stack_chk_fail`), but not guaranteed |

Our census (`metasec-tls-census.txt`) matches the crash sequence to the old Bionic `vfork.S`:
- `mrs x0,TPIDR_EL0; ldr x0,[x0,#8]; str wzr,[x0,#20]`, then `clone(CLONE_VM|CLONE_VFORK|SIGCHLD)`;
- the Android 15 source stores `0x80000000` there instead of 0.

It also finds the second slot-1 user: slot 1 compared with `pthread_self()`, with the result stored in two globals. On Bionic those are the same pointer. A compat object at TP+8 therefore has to pick one of two behaviours:
- **be** the pointer the app sees as `pthread_self()`, which is hanbin's `Pthread_self` design and means translating every `pthread_t` passed back into musl;
- or **differ** from it and let that comparison come out false, with unknown consequences.

## 3. What westlake can take (acceptance 3; input to #23 and #31)

Estimates are engineer-days for westlake, excluding board time.

| # | Item (hanbin source) | Class | westlake status / what to do | Est. |
|---|---|---|---|---|
| 1 | Stack floor for caller-shrunk thread stacks: <default and <2 MiB → 2 MiB (`pthread_create.cpp.patch`) | direct | We also run app code interpreted and have had stack faults (#11, #12). Add the floor where app threads are created: the Android-ABI shim's `pthread_create`, and an exported interposer in appspawn-x like `wl_fastlibc` for the default namespace | 1 |
| 2 | ART guard-exclusive `pthread_getattr_np` → dead page inside live stacks (compat §9.7; `--wrap=pthread_getattr_np`) | direct, verify first | westlake's ART runs the unmodified `GetThreadStack` + `stack_begin += guard + protected; InstallImplicitProtection()` (`art-build …/thread.cc:1347, 1440, 1444`) with `implicit_so_checks_ = true` on arm64 (`runtime.cc:4652`). **Likely present on our board.** Check one Java thread's `/proc/<pid>/maps` for a `---p` page inside its stack, then port the wrap | 0.5 check + 1 fix |
| 3 | Process identity through all three channels: `ActivityThread.currentProcessName`, `/proc/self/cmdline`, `getRunningAppProcesses` returning the app's own entry (PI-28, PI-33) | direct | #11 fixed four channels; audit that `getRunningAppProcesses` is among them | 0.5 |
| 4 | madvise property seeds `dalvik.vm.madvise.*` (PI-73: main-thread D state 7.60→4.58 s) | direct | seed through the #23 libbase property table; measure on #31 | 0.5 |
| 5 | Local caches that cut binder traffic: package query + `cache_key.package_info` nonces (584→127 BMS calls, PI-70); display info (888→50, PI-71); settings (170→28, PI-72) | adapt | #31's remaining UI-thread time includes display/config work. Count our calls first; our package manager is in-process, so PI-70 may not apply | 1–2 each |
| 6 | Install-time speed-profile dexopt (PI-77: JIT compiles 401→7, first pixel 15.2→14.0 s) | adapt | host-side profile + dex2oat into our `/data/local/tmp` app directory | 2–3 |
| 7 | **TLS slot 1 for metasec's `vfork()`** (hanbin's shadow descriptor idea, arm64 form) | adapt | Per-thread zeroed block shaped like LP64 `pthread_internal_t`, tid@16 filled, at TP+8. Coverage: ART-attached threads + shim-created threads + main thread; hanbin's shim alone reached 6%. Decide the `pthread_self()` identity (§2). Confirm musl's 16-byte gap. Expect the next layers hanbin met: maps geometry, shadowhook | 3–5, then unknown |
| 8 | WebView multi-process off at the Java level: `isMultiProcessEnabled()` returns false (`WebViewUpdateServiceAdapter.java:146-147`) | optional | same effect as #20's `--single-process`; only a cleanup | 0.5 |
| 9 | Tools and triage rules: `struct_offsets.sh`; in-process sigchain-slot crash forensics; OH `LiteProcessDumper` app reports have no memory content (debug.md §7.1b); `pgrep -f` matches itself; `hilog -x` ring loss for heavy apps; TTNet's cookie init needs a working WebView provider, so a broken provider looks like "no network" | direct | adopt as runbook | 0–1 |
| 10 | **Single real Bionic in the app process** (Era 2) | not applicable as built | It needs `/system/android` and a Bionic `PT_INTERP`, 14 overwritten OH service libraries, OH client libraries rebuilt against Bionic, and SELinux changes. A `/data/local/tmp` variant would have to ship a Bionic linker as the interpreter, rebuild every in-process OH 6.1 client library (IPC, window, input, graphics, GPU glue) against Bionic, and keep them ABI-compatible with the stock services. It is the only route that removes the whole Bionic-vs-musl class (metasec TLS, maps geometry, shadowhook `soinfo`, `__ndk1`) at once | weeks; the "large" tier for #23 |
| 11 | arm32 musl layout patches, install-time `.so` rewriting and symbol renames, OH service patches (AMS/WMS/BMS/installd/RS), init env size, gid 1097→3003 for Bionic's netd client | not applicable | system image, arm32, or Bionic-only; hanbin itself retired the rewriting | — |

Suggested order for #23:
1. Items 2 and 1: cheap, and they fix real ART and interpreter stack geometry either way.
2. Item 7 as a bounded experiment: does metasec pass `vfork` and what fails next?
3. Decide on item 10 only if item 7 runs into shadowhook or maps-geometry walls, as hanbin's did.

## 4. Toutiao specifics against #17, #20, #30 (acceptance 4)

| Topic | hanbin | westlake | Reading |
|---|---|---|---|
| WebView engine | AOSP 14 SystemWebView (Chromium 113) in-process; `WebViewFactory` routed to an in-process update service | pinned Chromium 109 engine with a source-built boundary | — |
| **#17** SurfaceControl | real AOSP `libandroid.so` (full NDK table); overrides the 13 symbols hwui looks up; WebView-path setters are no-ops (`surfacecontrol_bridge.cpp:943-966`) | no-op table in the WebView `libandroid.so` | Same outcome. hanbin never crashed because the table exists |
| **#20** renderer process | `isMultiProcessEnabled()` returns `false`; Chromium's in-package `bindService` failures accepted | `--single-process` in plat_support | Same outcome at a different layer |
| Cronet | nothing special: every APK library shares one Bionic namespace; network fixes were DNS, OH's 401 on an empty network specifier, the CA store and the INTERNET gid | `libsscronet.so` as Android-ABI target | Our namespace split creates the choice that hanbin does not have |
| **#30** HEIC thumbnails | no HEIC/bdheif/gif handling; `libbdheif`/`libgifimage` bind to the APK's own `libc++_shared` because OH's `/system/lib` is never searched (`ld.config.txt:14-16`) | load them in the Android-ABI namespace | Their retired musl design hit the same `__ndk1` class and fixed it by loading the APK `libc++_shared` per app (compat design:2522). That confirms #30's direction |
| detail-page crash, fonts | PI-59: Skia reads `$ANDROID_ROOT/fonts`, crashed about 5 s after the article opened | already handled: only `libwebviewchromium.so` gets `/data/local/tmp/asx/android-root` (`wl_fastlibc.cpp:376-380`) | Covered |
| process identity | PI-33: same `TokenUtils` → `TokenObjectProvider.query` recursion (report:1142) | #11 | Same bug, same fix family |
| Toutiao's own application class | report:802: the 17.6.0 `Mute` application class failed to instantiate | not seen on 13.9.0 | Version-specific |

## Method and limits

Three read-only research passes ran in parallel:
- Toutiao status and traces;
- metasec and TLS;
- WebView, network and deployment.

I then re-read every claim used here against the original line: the report lines 802/859/993/1048/1142/1487/3153, the performance report 175/182/184, the design documents' 824/shadow/6% lines, the two Java sources, and the six trace milestones. Everything is quoted in `hanbin-evidence.txt`. The binary census is mine (`metasec-tls-census.txt`).

Limits:
- hanbin's `memory/` has no Toutiao file: the ones its documents cite are absent from the local copy.
- The traces contain no touches and run at most 81 s, so L6 and L7 rest on written sign-offs.
- Nothing here was run on a board. The westlake-side "likely" items (dead stack page, musl's 16-byte gap on OH 6.1, whether shadowhook initialises) need one board check each; shadowhook logs to hilog, which our child stderr does not capture.

## Rules this adds

- A claim that an app "works" must name the level it reached and the evidence for that level. Commands accepted, frames drawn, content loaded and interaction are different levels, and one trace rarely proves more than one of them.
- Before porting a fix from another adapter, compare the board, the ABI and the app version. hanbin's metasec is a different binary on a different ABI.
- For a direct TLS dependency, count the accesses per slot in the binary before designing a compat layer. Two slot-1 users make a narrow problem.
- When another tree shares our ancestry, read its retired designs first: they record the walls we are about to hit.

## Layout

| Path | What |
|---|---|
| `README.md` | this report |
| `results.json` | levels, mechanisms, the portability table and comparisons in machine-readable form |
| `metasec-tls-census.txt` | direct thread-pointer accesses in both metasec builds, with disassembly |
| `hanbin-evidence.txt` | hanbin (and westlake) source lines quoted verbatim with file:line |
| `excerpt.py` | regenerates `hanbin-evidence.txt` from the two trees |
