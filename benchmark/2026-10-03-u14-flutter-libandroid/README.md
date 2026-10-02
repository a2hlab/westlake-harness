# U14 Flutter-private libandroid: ee2fb82c faithfully reproduced on hw248, then the hwui EGL interposer = fff9be31 (old functions 15/15 equal, +4 LIBEGL exports); deploy to westlake_flutter/ only

#90, native, offline. Nothing went to a board; a2hlab was not used. The wall is `2026-10-03-flutter-egl-window`.
- libflutter's `eglCreateWindowSurface` binds platform libEGL, because the Flutter-private `libandroid.so` it searches
  first lacks the interposer.
- It then hands mali the AdapterAnw wrapper → `ANativeWindow_getFormat+60` SEGV.

**Board identity (outer, 61b, read-only).** `/system/android/lib64/westlake_flutter/libandroid.so` = **`ee2fb82c6351…`**,
the same as the generation payload.

## 1. Faithful reproduction of ee2fb82c (standard A′: same compiler, same-length root, path-only diffs)

| | |
|---|---|
| source + recipe | `westlake-harness-bms-deploy` `benchmark/2026-09-30-n1-native/flutter/{libandroid_webview_shim.c, bionic_extra.c, android.map}` + `build-flutter.sh` (commit 0b8588216c) |
| receipt | `build-identities.txt:2`: `ee2fb82c… bms/src/.work/n1-native/flutter/libwestlake_flutter_android.so` |
| compiler | DWARF producer of both CUs: `OHOS clang 15.0.4 (llvm-project feef13a3)` = the frozen clang-15. Run on hw248 in the same 58-char mirror root as `2026-10-03-u14-native-abi-gecko`. |
| link inputs | runtime `../westlake-generation-v3c-candidate/…/liboh_android_runtime.so` `9e14bf20`; platform-pool `libnative_window.so` = `libnative_buffer.so` `8f1879f8` (SONAME libsurface.z.so) |
| recipe | `build_flutter_android_hw248.sh`: the recipe's android.o / bionic.o / link lines verbatim. Its other outputs and its `check_frozen` gate are separate. |

**First try: `cbdc2517` ×2. All allocated sections and PT_LOAD were identical, but one DWARF line differed:**
`jni.h` `md5_checksum` `04a2fac2` (original) vs `15e2f200` (mirror).
- The committed `n1-native/flutter/include/jni.h` (one version only, 0b8588216c) is `15e2f200`.
- The original build read the **AOSP libnativehelper jni.h** (`04a2fac2`, identical to
  `bms/src/adapter/prebuilts/android/jni/include/jni.h`).
- The two differ by **one trailing blank line**, so no line number moves.
- The mirror's copy was set to the `04a2fac2` content, which is what the original DWARF records. Nothing in bms-deploy
  was touched.

**Result: `e4c271977d88…` ×2.** Against ee2fb82c (`evidence/faithful-e4c27197-vs-ee2fb82c.txt`):
- allocated sections and all 4 PT_LOAD segments (build-id masked) are **identical**;
- after the root placeholder, the remaining bytes are only in `.debug_line / _line_str / _str / _str_offsets` and
  `.symtab` (`$d` in debug-string sections);
- string multisets are equal, and `llvm-dwarfdump` with strings resolved shows 44874 lines, **0 different**.

## 2. The interposer: `fff9be3190f1b1c99c3fd4559d258cbac131fb657d10b1fa7060f61c4002d5e5` ×2

**What.**
- `src/flutter_egl.cpp` = N6 `2026-10-01-n6-native/src/flutter_egl.cpp` (14f79c5b). That is the verbatim copy of
  hwui's §4 window unwrap + §5 swap/destroy owner bookkeeping, the path that unwraps in all 11 U13 keys with
  `OH_EglHijack` lines.
- It has **two changes** for the Flutter app namespace (`src/flutter_egl-vs-n6.diff`, 20 lines):
  1. The bridge is reached through the already-shared `liboh_android_runtime.so` handle when NOLOAD
     `liboh_adapter_bridge.so` misses. That bridge is not shared by name in this namespace, and `dlsym(handle)` also
     searches the runtime's dependencies. **N6's plain-`dlopen` fallback, which could load a second bridge copy, is
     removed.**
  2. `HiLogPrint` is looked up the same way when `RTLD_DEFAULT` cannot see it, so the `OH_EglHijack` lines reach hilog
     for the board check.
- `oh_anw_get_oh` is a pure struct read. `oh_anw_notify_presented` updates its bridge copy's FN03 state, and the copy
  reached via the runtime is the one hwui's own NOLOAD reaches from that namespace.
- `src/android_egl.map` = the original map + `LIBEGL { eglCreateWindowSurface; eglDestroySurface; eglSwapBuffers;
  eglSwapBuffersWithDamageKHR; }` (N6's node). libflutter's imports are unversioned.

**Build.**
- Same recipe plus N6's C++ line (`-std=c++17 -nostdinc++ -isystem $TC/include/c++/v1 -fno-exceptions -fno-rtti`) and
  N6's `--no-as-needed libc++.so`.
- The toolchain's own `libclang_rt.builtins.a` goes before `libc++.so`. Reason: in the intermediate build `20bbe90b`,
  libc++.so's exported `__emutls_get_address` displaced the static compiler-rt emutls the original code was linked
  with, changing `__emutls_get_address`, `emutls_init`, `emutls_key_destructor` and `__emutls_unregister_key`. With
  the archive first, the original objects keep their static emutls.
- Environment-only fixes during the run: copied the `clang++` symlink. One script slip, my own: a failed `cd` left a
  variable empty and put two files under `/benchmark` at hw248's root. They were removed immediately (only my two files
  and three empty directories, created 03:57:51).

### Gates vs the faithful `e4c27197`

| gate | result |
|---|---|
| old functions (`equiv.py`) | **15/15 instruction-equal, 0 changed**; 16 new (the 4 EGL entries, the two resolvers, `notify_presented_after_success`, `n6_log`, unordered_map instantiations, static init) |
| exports | **exactly +4**, `@@LIBEGL`, 0 removed |
| NEEDED | + `libc++.so` (in the Flutter domain's shared-by-name list, so no new copy) |
| imports | only additions: libc++ (`mutex`, `new/delete`, `__cxa_guard_*`, `__cxa_atexit`, `__next_prime`), `dlopen / dlsym / dlerror`, `vsnprintf`; nothing removed |
| strings | only `flutter_egl.cpp`'s own (log formats, `libEGL.so`, `liboh_adapter_bridge.so`, `liboh_android_runtime.so`, `oh_anw_*`, `HiLogPrint`) |
| open sites | 0 → 7: NOLOAD `liboh_adapter_bridge.so`, NOLOAD `liboh_android_runtime.so` ×2, NOLOAD `libEGL.so` ×2, plus N6's plain `dlopen("libEGL.so")` ×2 fallback. `libEGL.so` is shared by name, so that fallback returns the resident platform instance. **No plain dlopen of the bridge.** |
| compiler diagnostics | the same 2 warning lines as the faithful build (from the original source); none from `flutter_egl.cpp` |

**Binding (static, `evidence/libflutter-lookup-order.txt`).**
- libflutter's NEEDED order is `libc libdl libm libandroid.so libEGL.so …`.
- ee2fb82c defines none of `eglCreateWindowSurface / eglSwapBuffers / eglDestroySurface`, so platform libEGL (position 5)
  is the first definer.
- fff9be31 defines all three at position 4. This is the mechanism by which the root libandroid 9ccf64f8 already
  captures libunity (`[UNITY-EGL]` in zigzag).

## Deployment scope

- **Only** `/system/android/lib64/westlake_flutter/libandroid.so` (ee2fb82c → fff9be31).
- `westlake_native/libandroid.so` is the same ee2fb82c and serves the 13 native-cluster packages (vlc, ppsspp, firefox,
  …). **It stays unchanged.**
- The Flutter-private `westlake_flutter/libwestlake_native_abi.so` (d2053066) is not touched here; see
  `2026-10-03-u14-native-abi-gecko`.

## Prediction (first fatal) and board check

| key | prediction |
|---|---|
| localsend, fd-kitchenowl, fd-fluffychat, fd-libre | **first fatal moves past `eglCreateWindowSurface` (high)**; next wall unknown (Impeller/Vulkan fallback, plugins, textures); lit low–medium |
| fd-immich, fd-saber | 0 (die earlier) |
| every non-Flutter key | 0 (file only on the Flutter-private path) |

Board check:
- on the Flutter raster thread, `OH_EglHijack resolve_egl_hijack_funcs: oh_anw_get_oh_fn=<non-null> …` then
  `eglCreateWindowSurface: detected ANW shim … unwrapped to OH NativeWindow=…` and `-> EGLSurface=<non-null>`;
- no `ANativeWindow_getFormat+60`;
- maps: no second `liboh_adapter_bridge.so` inode in the process.

## Files

- `build_flutter_android_hw248.sh`; `src/flutter_egl.cpp`, `src/flutter_egl-vs-n6.diff`, `src/android_egl.map`.
- `evidence/`:
  - `faithful-e4c27197-vs-ee2fb82c.txt`;
  - `exports-imports-*`, `equiv-*`, `strings-*`, `open-sites-*` (both the 20bbe90b intermediate and the fff9be31
    candidate);
  - `libflutter-lookup-order.txt`, `hw248-*.log`.
- `results.json`.
- Artifacts: `$WORKSPACES/westlake-inputs/generations/u14-flutter-libandroid/` (`fl-repro*`, `fl-egl*`, `SHA256SUMS`,
  `logs/`).
