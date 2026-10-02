# firefox and fd-fennec_fdroid die before bind on one native wall: libmozglue.so cannot relocate `__gnu_strerror_r`, and 9 more bionic symbols are queued behind it

#90, offline. Nothing was deployed to a board. Input: the U12 stage-A runs that `bind_status.py` marks
`fatal_before_bind` (firefox window 4 / 61b, fd-fennec_fdroid window 3 / 5cd; fd-immich is the AssetManager cluster and
is not covered here).

## 1. Termination signature and earliest wall (both keys identical)

`first_fatal.py` gives only `process-disappeared, cause unknown`, and `run_facts` gives `child_hilog=0`. The cause is in
the process's own lines (`evidence/hilog-excerpts.txt`, verbatim):

```
firefox 00:50:28.329 1575/1636 MUSL-LDSO: relocating failed: symbol not found. dso=.../org.mozilla.firefox/android/lib/arm64-v8a/libmozglue.so s=__gnu_strerror_r use_vna_hash=1 van_hash=50d63
        00:50:28.331 ExceptionHandler: Caused by: java.lang.UnsatisfiedLinkError: F02-A12-UNSUPPORTED-SYMBOL: dlopen_ns failed for .../libmozglue.so: Error relocating .../libmozglue.so: __gnu_strerror_r: symbol not found
        00:50:28.444 [B8-UEH] background thread 'Gecko' uncaught, thread ended (process kept alive): RuntimeException: Library exists but couldn't load ... lib: mozglue
        00:50:28.478 AMS: Ability on scheduler died: 'org.mozilla.firefox.App'
fennec  00:01:29.060 2983/3029 same relocation line (libmozglue.so, __gnu_strerror_r, van_hash=50d63 = LIBC)
        00:01:29.264 AMS: Ability on scheduler died: 'org.mozilla.fennec_fdroid.App'
```

**Sequence.**
1. The GeckoThread calls `GeckoLoader.loadMozGlue` → `System.loadLibrary("mozglue")`. The route-A loader opens it in
   the app domain, and musl aborts the relocation at the first missing strong symbol.
2. Our `B8-UEH` keeps the process alive.
3. mozac's own `ExceptionHandler` / CrashReporter posts its notification and ends the process about 35 ms later.

**One wall, two keys:** the same engine (Gecko 156) and the same first fatal.

## 2. Layer: native (the route-A bionic ABI provider), not JAR

Static, from the sources and deployed binaries:
- `app_native_loader.c:62` lists both packages in the 13-package `native_cluster_path`, so they get the **native**
  domain (`flutter_domain.inc`: search `westlake_native/` first).
- `westlake_stock_host_main.c:330-340` loads `westlake_native/libwestlake_native_abi.so` **RTLD_GLOBAL** into that
  domain. It is `d2053066`, 26 exports, version `LIBC`; source `westlake-harness-bms-deploy/benchmark/2026-09-30-n4-native/src/native_abi.c`
  + `native_abi.map`.
- `libbionic_compat.so` (`015aa3a6`) is the only deployed exporter of `__gnu_strerror_r`. It is **not inherited for
  `native_private`** (`!flutter_private && !native_private`). It is only in the shared-by-name list, and libmozglue does
  not NEED it.
- NEEDED `libc.so / libm.so / libdl.so` are musl's reserved names, so they bind to musl itself. The android `libc.so`
  stub (`ee6034f5`) is never reached by name.

**Check of this provider model against the board** (`reloc_order.py`, replaying musl's order: JMPREL, then REL, then
RELA). With provider = musl + native_abi + the app's own libs + NDK API symbols, the first unresolved strong symbol of
libmozglue is `__gnu_strerror_r` for **both** builds, exactly what both hilogs report (`reloc-order-u12.txt`).

**The full gap list** (`evidence/imports-*.txt`, `reloc-order-u12.txt`). Strong `@LIBC` imports that no provider in
scope satisfies:

| library | unresolved in musl order |
|---|---|
| libmozglue (fennec) | `__gnu_strerror_r`, `strtoll_l`, `strtoull_l` |
| libmozglue (firefox) | `__gnu_strerror_r`, `__pthread_cleanup_push`, `__pthread_cleanup_pop`, `strtoll_l`, `strtoull_l`, `__assert2` |
| libxul (both) | `__assert2`, `__open_2`, `__cmsg_nxthdr`, `__strncpy_chk2`, `android_dlopen_ext`, `__gnu_strerror_r` (order differs per build) |
| libnss3, libfreebl3 | `__open_2` |
| firefox libcrashhelper / libcrashtools | `__cmsg_nxthdr` / `__assert2` |
| libplugin-container | `__libc_init` (child-process executable stub, not loaded in the app process) |

`android_res_nquery` / `android_res_nresult` are WEAK and do not fail.

**Adding only `__gnu_strerror_r` would move the first fatal to `strtoll_l` (fennec) or `__pthread_cleanup_push`
(firefox)** (`reloc-order-only-strerror.txt`). The fix must export the whole set at once.

## 3. Does U13 move it? No.

- U13 runtime 18763dd4 = `asset_manager.o` + the compat-shim M1. U13 JAR bbc3f530 is Java.
- Neither touches `libwestlake_native_abi`, `libapp_native_loader`, the stock host's namespace setup or
  `libbionic_compat`.
- The failure happens in the linker before any Java code of the app's engine runs.

Prediction for U13: **0 moves; same signature.**

## 4. Minimal fix (native, one provider; not built in this round)

- **Where:** extend `libwestlake_native_abi.so`, already GLOBAL in exactly these domains (`native_abi.map` `LIBC { … }`
  + `build-abi.sh`). It is not in `knowledge/frozen/frozen.json`.
- **What to add, as a new source file:** export these 10 symbols with version `LIBC`:
  `__gnu_strerror_r strtoll_l strtoull_l __pthread_cleanup_push __pthread_cleanup_pop __assert2 __open_2 __cmsg_nxthdr __strncpy_chk2 android_dlopen_ext`.
- **Copy the verified implementations; do not rewrite them:**
  - 8 come from the old-route shim `vm-copies/westlake-current/framework/webview-shim/webview_bionic_shim.c`
    (commit 532633d). That is the source of `libwebview_bionic_shim.so 85c789f4`, which exported all 9 on the old
    route (`2026-10-02-toutiao-oldroute-diff/evidence/abi-symbols.txt`).
    - `__gnu_strerror_r`: line 1481;
    - `__open_2`: 1619;
    - `__cmsg_nxthdr`: 1630;
    - `strtoll_l` / `strtoull_l`: 1680 / 1686;
    - `__strncpy_chk2`: 1749;
    - `__pthread_cleanup_push` / `__pthread_cleanup_pop`: 1869 / 1877.
  - `android_dlopen_ext` is exported by both the old shim binary (85c789f4) and `libbionic_compat` (015aa3a6), but
    **no local source was found** (vm-copies, `bms/src`). Next in the lookup order: a2hlab, then hw248. Until then its
    behaviour is unverified.
  - `__assert2` comes from `vm-copies/westlake-current/framework/appspawn-x/bionic_compat/src/bionic_assert_compat.c:133`.
- **Static proof:** with those 10 added to the provider, `reloc_order.py` leaves **0** unresolved strong symbols in
  every Gecko library of both APKs, except `libplugin-container.__libc_init`, which the app process does not load
  (`reloc-order-with-fix.txt`).
- **Effect on other keys:** the change only adds exports to a library that is GLOBAL only in the 13 native-cluster
  packages' domains. Watch item: those packages now find these symbols where they previously failed or bound
  elsewhere.
- **Risk to note:** `android_dlopen_ext` in the old shim. DIGEST 683 (PPSSPP) records that `android_dlopen_ext`
  callers may need `USE_NAMESPACE` / `USE_LIBRARY_FD` semantics. If libxul calls it with those flags, that call is the
  next wall. It would surface as a Gecko load error, not a relocation failure.

**Prediction (first fatal).**

| key | with the fix |
|---|---|
| firefox | **moves (high)**: libmozglue and libxul relocate; the next first fatal is later in Gecko init, unknown statically. Lit: low. |
| fd-fennec_fdroid | **moves (high)**, same |
| other keys | 0 |

## 5. libandroidio.so / libjavacore.so ENOENT in the app domain: not fatal for any key

**Is it fatal? No.**
- `dlopen_failures.py --near-fatal 3` over U12 windows 1–4: both libraries fail in `westlake.anl.app` for exactly
  antennapod, fd-client, fd-tusky and fd-tutanota, with **`near_fatal_keys=0`**
  (`evidence/dlopen-near-fatal-androidio-javacore.txt`).
- `first_fatal.py`: all 4 runs `no-observed-termination`. `run_facts`: all 4 alive at t5 and t20 (antennapod w1,
  fd-client w4, fd-tusky w1, fd-tutanota w3).

**Who asks for them in the app domain.**

What it is not:
- **Not the apps' own native code.** antennapod's APK (`3f43a433`, the board's) ships no native libraries at all.
- **Not a Java `System.loadLibrary("javacore"|"androidio")` with literal names.** Those strings (with or without
  `lib`/`.so`) appear in none of the 4 APKs' dex, the runtime jar, oh-adapter-framework 2257b835, or the 9 board BCP
  jars.

What the evidence shows:
- The three bare-name opens (`liblog.so` found, then `libandroidio.so` ENOENT, then `libjavacore.so` ENOENT, 6 ms
  apart) are separate requests on the bind thread that also logs `[B8-NATIVE] native namespace created for runtime
  CL`.
- They go through route-A `libnativeloader` (`2a6ec73f`) `native_loader_registry.cpp:373` → `ANL_Dlopen` in the
  ClassLoader's app domain (`westlake.anl.app.<pid>.2`).
- That loader's system-library table names `liblog.so`, `libjavacore.so`, `libopenjdk.so`… with `/system/android/lib64`
  paths, and the app domain cannot see that directory.

The exact Java call site is not visible: the loader's own diagnostics are not in hilog.

**Agreement with cc-wiki:** they are ART-internal libraries, harmless in these runs. Keep them out of the public wall
table.

## What was wrong before

- `first_fatal.py` reported "cause unknown" because the process ended through the app's own crash handler after
  `B8-UEH` had kept it alive. The cause sits in a background thread's exception plus a linker line, not in a fault log.
- `bind_status`'s `fatal_before_bind` grouped the two Gecko keys with fd-immich. Their walls are unrelated: linker ABI
  vs. AssetManager.

## Rules this round sets

- **For a relocation failure, replay the linker statically before fixing the reported symbol.** musl `dlopen` aborts
  at the first missing strong symbol, so one log line hides the rest of the list. `reloc_order.py` gives the full list
  in the linker's order and is checked against the board by reproducing the reported first symbol.
- **"Exported somewhere on the device" is not "visible to the library".** `libbionic_compat` exports
  `__gnu_strerror_r`, but in the native domain only the GLOBAL ABI DSO, musl and the library's own NEEDED closure are
  searched.

## Files

- `gecko_imports.py`: libc-class imports musl lacks, and who exports them.
- `reloc_order.py`: musl-order replay with the native-domain provider model; `--extra` for candidate exports.
- `reloc-order-u12.txt`, `reloc-order-with-fix.txt`, `reloc-order-only-strerror.txt`.
- `evidence/`: `hilog-excerpts.txt`, `imports-{fennec,firefox}.txt`, `dlopen-near-fatal-androidio-javacore.txt`.
- `results.json`.
