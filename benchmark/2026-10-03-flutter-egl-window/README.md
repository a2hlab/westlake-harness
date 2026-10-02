# Flutter EGL window wall: libflutter binds platform libEGL directly and hands it the AdapterAnw wrapper. Flutter-only, exposed (not caused) by U13; fix = the eglCreateWindowSurface interposer in the Flutter-private libandroid

#90, offline. Nothing was deployed to a board.

**Input.** U13 stage A window 1, 5ea, movers shard: localsend and fd-kitchenowl now get past U12's `GetLongField`
JniAbort, and their bind returns OK. Both then die identically:
- `SIGSEGV SEGV_MAPERR @0xbf3a9be7eed`;
- `#00 libnativewindow.z.so ANativeWindow_getFormat+60` ← `libGLES_mali new_window_surface` ← platform
  `libEGL.so eglCreateWindowSurface` ← `libflutter.so`.

Evidence: `evidence/u13-*-window-path.txt` (verbatim) and `evidence/binding-static.txt`.

## ① Where the window pointer comes from, and what sits in between

**The faulting thread.** It is the app's own **`1.raster`** thread (pid 18309 tid 18347 localsend; pid 16151 for
kitchenowl). The `18369` / `16205` pids in the stack lines are DfxProcessDump writing the dump.

**The window's path.**
1. Flutter calls **`ANativeWindow_fromSurface`**. libflutter imports it, but the Flutter-private `libandroid.so`
   (`westlake_flutter/`, ee2fb82c in the generation payload) does not define it. It resolves one level down, in that
   libandroid's NEEDED `liboh_android_runtime.so`, i.e. the U13 runtime / M1 compat shim.
2. The shim returns `Surface.mNativeObject` unchanged: `[STAGE0] mNativeObject=0x7f32cdbdd0` → `returning
   OHNativeWindow=… directly`. On route A that value is the bridge's **AdapterAnw** (AOSP-ABI wrapper, magic `'_wnd'`)
   around the real OH NativeWindow. The same process's hwui shows this: `OH_EglHijack: detected ANW shim
   0x7f32037c90, unwrapped to OH NativeWindow=0x7f31b9be70`. So the shim's log text "OHNativeWindow" is a misnomer.
3. libflutter's **`eglCreateWindowSurface`** (an UND import; NEEDED order `libc libdl libm libandroid.so libEGL.so …`)
   binds to **platform `/system/lib64/platformsdk/libEGL.so`**, because:
   - `libEGL.so` is in the Flutter domain's shared-by-name list (`app_native_loader` eebd62f2: `libc.so:libdl.so:libm.so:libEGL.so:…`);
   - the private libandroid (level 1) does not define the symbol;
   - the interposers exist only one level further down (runtime) or in other objects (hwui, root libandroid).
4. Platform libEGL → mali `new_window_surface` treats the AdapterAnw as an OH NativeWindow →
   `ANativeWindow_getFormat` reads a wrong field → SEGV.

**Is the U13 M1 shim's `eglCreateWindowSurface` (u13-m1-compat-shim.cpp ~1408, NOLOAD `libEGL.so`) in the path? No.**
- There is no `[UNITY-EGL]` line in either Flutter process, and no shim frame in the stack.
- That interposer only wins when it is the first definition in the caller's lookup order: libunity → root libandroid
  9ccf64f8, which defines `eglCreateWindowSurface`. For libflutter it is not.
- The shim's part in the crash is only that its `ANativeWindow_fromSurface` passes the wrapper through, which is
  correct for every caller that later goes through an unwrapping EGL entry.

**Known before, not new.** N5/N6 found the same LocalSend raster crash on 2026-10-01.
- N6 put an EGL hijack into the GLOBAL `westlake_flutter/libwestlake_native_abi.so`. On the board, libflutter still
  bound platform EGL; a later GLOBAL load does not displace the earlier provider.
- N7 built a private `libEGL.so` facade (6963d954) plus host/ANL changes, bundled with a libz alias. Its window failed
  on the ZigZag control (`inflateInit2_`), so the Flutter EGL path was never exercised.
- Source: `westlake-harness-bms-deploy` `benchmark/2026-10-01-n6-*`, `n7-*`.

## ② The same window's lit / GL keys: different path, which is why they do not crash

- **Population** (`rg` over every hilog):
  - `ANativeWindow_getFormat+60` crashes: U13 stage A = **4 keys, all Flutter** (localsend, fd-kitchenowl,
    fd-fluffychat, fd-libre); U12 = 0; U10.1T8 = 0.
  - In U12 the four died earlier, `art::JNI::GetLongField → JavaVMExt::JniAbort`. U13 runtime 18763dd4 fixed that.
- **hwui (every app's Activity window, Flutter apps included):** `OH_EglHijack … detected ANW shim … unwrapped`
  appears in 11 U13 stage-A keys. Non-Flutter: privacybrowser, clipboardeditor, fd-client, fd-uhabits, helloworld,
  wikipedia, zigzag; plus the 4 Flutter apps' Activity windows. libhwui defines its own `eglCreateWindowSurface`
  (`hwui_oh_abi_patch.cpp` §4) and unwraps.
- **Native engines in the normal domain (Unity):** libunity's `libandroid.so` is the root libandroid (9ccf64f8), which
  defines `eglCreateWindowSurface`. `[UNITY-EGL]` appears in zigzag.
- **Java EGL14 / GLSurfaceView:** the framework EGL JNI unwraps before calling EGL (N6 `native-checks/egl.cpp`).
- **Verdict: a Flutter-only wall, exposed by U13 removing the wall in front of it. Not a U13-introduced regression.**
  No non-Flutter key gained this crash.
- Only the 6 Flutter packages get the private `westlake_flutter/` libandroid, whose level-1 slot lacks the interposer.

## ③ Minimal fix and prediction

**Fix.** Give the Flutter-private `libandroid.so` the same `eglCreateWindowSurface` interposer, so libflutter's level-1
lookup finds it before platform libEGL. This is exactly the mechanism Unity uses with the root libandroid.
- **One file:** source `westlake-harness-bms-deploy benchmark/2026-09-30-n1-native/flutter/libandroid_webview_shim.c`
  (the ee2fb82c build).
- **Copy the verified code, don't rewrite it:** hwui's §4 hijack (`hwui_oh_abi_patch.cpp`, the path that works in all
  11 keys above), already extracted verbatim in N6 `src/flutter_egl.cpp` with its offline window tests:
  - detect the AdapterAnw with the bridge's `oh_anw_get_oh` (NOLOAD dlsym);
  - pass non-wrapped windows through unchanged;
  - call platform `eglCreateWindowSurface` resolved from the already-loaded `libEGL.so` (NOLOAD);
  - keep its successful-create / swap / destroy bookkeeping.
- **Scope:** deploy the rebuilt file **only to `westlake_flutter/libandroid.so`**. The identical `westlake_native/`
  copy serves the 13 native-cluster packages (vlc, ppsspp, firefox, …) and must stay as it is. No host, ANL,
  platform-EGL or libz change (N7 bundled exactly those).
- **Build route:** same as `2026-10-03-u14-native-abi-gecko`. First faithfully rebuild ee2fb82c with its recipe
  (frozen clang feef13a3 on hw248, same-length root, path-only diffs), then add the interposer, ×2.
- **Unknown to settle first:** the hash of the deployed `/system/android/lib64/westlake_flutter/libandroid.so` on the
  board. Neither the runtime fingerprint nor the U12 bundle covers that directory (it is an underlay; N6 noted the
  same blind spot). One read-only `sha256sum` on the board settles it.

**Prediction (first fatal).**

| key | with the fix |
|---|---|
| localsend, fd-kitchenowl, fd-fluffychat, fd-libre | first fatal moves past `eglCreateWindowSurface` (high). Next unknown: Impeller/Vulkan fallback (`libvulkan.so` ENOENT is already logged on the raster thread, non-fatal), Flutter plugins, texture paths. Lit: low–medium. |
| fd-immich, fd-saber (the other Flutter packages) | 0 here; they die earlier (immich: libcronet `ATrace_beginSection`, N6) |
| every non-Flutter key | 0 (the file is only on the Flutter-private path) |

## Rules this round sets

- **An interposer only works where it is the first definition in the caller's lookup order.** Before saying "X is
  intercepted", check the caller's NEEDED order and which object at that level defines the symbol. A GLOBAL-loaded
  provider loaded later does not displace an earlier one (N6).
- **Check the faulting pid against the app pid.** In DfxFaultLogger lines the pid column is the dumper; the crashed
  process/thread is in `TargetPid/TargetTid` and `Tid:…, Name:…`.

## Files

- `evidence/u13-localsend-window-path.txt`, `evidence/u13-fd-kitchenowl-window-path.txt`: verbatim fromSurface /
  hijack / fault lines.
- `evidence/binding-static.txt`: libflutter NEEDED + imports, private vs root libandroid exports, the Flutter-domain
  shared list.
- `results.json`.
