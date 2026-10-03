# U16 Flutter libandroid A‴ = b1c9f76e + the libre eglGetProcAddress EGL-name fix

#90, native, offline. Builds the `u16-libre-anw` fix (`flutter_egl_getprocaddress.egl-names.patch`) into the U16
Flutter-private `libandroid.so`, on top of cc-t3's A″ `b1c9f76e` (`benchmark/2026-10-03-u16-flutter-impeller-build/`),
with that build's recipe, hw248 58-char mirror, and frozen clang `feef13a3` verbatim. The fix makes the Flutter raster
thread's `eglGetProcAddress`-resolved `eglCreateWindowSurface` go through our ANW-unwrapping hook (not just the PLT
path), so fd-libre (Aves) gets the same unwrap localsend already got. **A‴ built ×2 byte-identical; all three gates pass.**

```
A‴  sha256 = eb90a6409c9caaba058d2463cad9c193d344527051455d8aca8421e6b7011b4f   (×2 identical)
A″  (base) = b1c9f76e5b248c2c707b7a61f52503d379dd7564547bf461589ed23cdf903fe9   (cc-t3, superseded)
U15 (orig) = 9b8245022f9c98dac41a85acfa553e96e6385073fd7b15298199a1cce223647b
```

## The change (one function body)
A‴ = A″ with `src/flutter_egl_getprocaddress.cpp` extended so `eglGetProcAddress` returns our own
`eglCreateWindowSurface / eglDestroySurface / eglSwapBuffers / eglSwapBuffersWithDamageKHR` (defined in
`flutter_egl.cpp`, same `.so`) **before** delegating to the platform resolver. A″ returned the platform function for
those names, so the raster thread's proc-address-resolved `eglCreateWindowSurface` bypassed the unwrap (see
`../2026-10-03-u16-libre-anw/`). No map change: those 4 names (and `eglGetProcAddress`) were already exported by
`android_v3.map`. So the only code that changes is `eglGetProcAddress`'s body (123 → 158 instructions); **no new
export, no new NEEDED.**

## Build (hw248, verbatim A″ recipe)
`build_flutter_android_hw248.sh <mirror> <dest> flutter_egl.cpp ndk_trace.cpp <patched flutter_egl_getprocaddress.cpp>`
with `ANDROID_MAP=android_v3.map`, in the 58-char mirror `.../cc-t3-nabi-2026103/westlake-harness-bms-deploy`, frozen
clang-15 `feef13a3`, v3c runtime input `9e14bf20`, platform-pool `libnative_window`/`libnative_buffer` — exactly as
A″'s log records. **Command locked by reproduction:** building the *unpatched* `u16-src` with this command first
reproduced `b1c9f76e` byte-for-byte, so the only variable in A‴ is the patched `.cpp`. Only the one original
`bionic_extra.c` `_GNU_SOURCE` warning; none from any `.cpp`.

## Gates (evidence/)
| gate | result |
|---|---|
| ③ ×2 byte-identical | **yes** — both hw248 builds = `eb90a640…` (`x2-identical.txt`, `u16-eglnames-{a,b}.log`) |
| ① vs A″ `b1c9f76e`: only `eglGetProcAddress` changed | **yes** — 40/40 common, **differ 1 = `eglGetProcAddress` (123→158)**, 0 only-deployed, 0 only-rebuilt, other 39 instruction-equal (`equiv-b1c9f76e-vs-Aprime3.txt`) |
| ① exports Δ0, NEEDED same vs `b1c9f76e` | **yes** — exports IDENTICAL (13), NEEDED IDENTICAL (`exports-needed-Aprime3.txt`) |
| ② vs U15 `9b824502`: original 34 funcs instruction-equal | **yes** — common 34, **differ 0** (33 + 1 after-residual), 6 only-rebuilt = the new file (`eglGetProcAddress`, `gl_log`, `wl_glDepthRange`, `wl_glClearDepth`, `wl_gl_noop`, `first_time`) (`equiv-9b824502-vs-Aprime3.txt`) |
| ② abi_diff `--calls` vs `9b824502` REMOVED empty | **yes** — exports old 12→new 13, removed 0 / added 1 (`eglGetProcAddress`), signature drift 0, consumer breaks 0, **call-set diffs 0**, exit 0 (`abi-calls-9b824502-vs-Aprime3.txt`) |

Identical gate profile to A″ vs U15 — the patch adds nothing to the ABI surface or call-set; it only grows
`eglGetProcAddress`'s body. (A‴ vs `b1c9f76e` is purely `eglGetProcAddress`.)

## Release (for cx-bms — outer will notify to swap)
`$WORKSPACES/westlake-inputs/generations/u16-flutter-egl-names-libandroid-v1/`
- `payload/android/lib64/westlake_flutter/libandroid.so` = **`eb90a6409c9caaba058d2463cad9c193d344527051455d8aca8421e6b7011b4f`**
- `logs/u16-eglnames-{a,b}.log`, `SHA256SUMS`.
- Deploy **only** to `/system/android/lib64/westlake_flutter/libandroid.so`; A‴ **supersedes** A″ `b1c9f76e` there
  (A‴ ⊃ b1c9f76e ⊃ 9b824502 ⊃ fff9). `westlake_native/libandroid.so` (`ee2fb82c`) unchanged.
- If `9b824502` is frozen before U16 ships, A‴ takes the "add new functionality, original behaviour preserved" path —
  the 34/34 instruction-equal + abi `--calls` empty-REMOVED gates are that proof.

Persistent copies of the `.so`: the release generation above (Mac) and hw248
`$HW248_HOME/cc-wiki-eglnames/aprime3-{a,b}/libwestlake_flutter_android.so`.

## Build inputs (snapshot in `src/`, hashes for restore)
- `src/flutter_egl_getprocaddress.cpp` (PATCHED, sha16 `fbc96152`), `src/flutter_egl.cpp` (`59d69fa6`),
  `src/ndk_trace.cpp` (`837b2b16`), `src/android_v3.map` (`c573163c`), `src/build_flutter_android_hw248.sh` (`c2ca5918`).
- Toolchain: frozen clang-15 `feef13a36e78b7a2ff3e9e3f180a958f2782be1e`; runtime-input `liboh_android_runtime.so`
  `9e14bf20…`; mirror root `$HW248_HOME/cc-t3-nabi-2026103/westlake-harness-bms-deploy` (58 chars) on hw248 (ecs-9f6c).
- The `_GNU_SOURCE` warning and the "other outputs / check_frozen" exclusions are the A″ recipe's, unchanged.

## Boundaries
Built on hw248 (isolated `FLUTTER_BUILD_OUT`/dest under `$HW248_HOME/cc-wiki-eglnames/`, cc-t3's `u16-src` and
`n1-native/flutter` work area untouched). No board, no deploy, no push. cx-bms swaps the Flutter libandroid in the U16
合包 on the outer's go; the on-board move (libre past `eglCreateWindowSurface`) is verified there against the
`../2026-10-03-u16-libre-anw/` prediction. The committed `artifacts/*.so` is gitignored; the `.so` lives in the release
generation + hw248, recorded here by sha256.
