# U16 Flutter Impeller proc gap — BUILD (rebased on U15 `9b824502`): the eglGetProcAddress interposer compiled into the U15 flutter libandroid; A″ = `b1c9f76e`, ×2 byte-identical, 34/34 old functions instruction-equal (incl. the 3 ATrace), exports only +`eglGetProcAddress@@LIBEGL`, abi `--calls` REMOVED empty

#90, native, offline. Nothing went to a board. Design: `benchmark/2026-10-03-u16-flutter-impeller-proc/` (slot #468 =
`glDepthRange`, build 0d216f3f). For cx-bms's U16 合包 draft.

## Base correction (outer R2, 12:48)

The first build (`15e9885a`) used **U14 `fff9be31`** as base. But U16's content base is **U15** — whose
`westlake_flutter/libandroid` is **`9b824502` = fff9 + the 3 NDK ATrace exports** (`ATrace_beginSection` /
`ATrace_endSection` / `ATrace_isEnabled`, forwarding to the runtime `atrace_*_body`). Rebasing the interposer onto fff9
would have **deleted those 3 ATrace exports** from the U16 pack (immich's libcronet imports `ATrace_beginSection/
endSection`). This build is rebased onto `9b824502` so the ATrace exports are preserved. (The fff9-based `15e9885a` is
discarded.)

## What was built

A″ = **U15 `9b824502` + the `eglGetProcAddress` interposer** (`src/flutter_egl_getprocaddress.cpp`). Same recipe and
inputs as U15, one extra object and one extra version-script export over U15's three extras.

- **Recipe:** `build_flutter_android_hw248.sh` (verbatim) on hw248, reused U15/U14 mirror
  `/home/alvin/cc-t3-nabi-2026103/westlake-harness-bms-deploy` (58-char root), frozen clang-15 `feef13a3`, v3c runtime
  `9e14bf20`, platform-pool `libnative_window`/`libnative_buffer`. Extras: `clang++ -std=c++17 -nostdinc++
  -fno-exceptions -fno-rtti`, linked after `bionic.o`, `libclang_rt.builtins.a` before `libc++.so`.
- **Extras (3):** `flutter_egl.cpp` (U14, eglCreateWindowSurface interposer) + `ndk_trace.cpp` (U15, ATrace) +
  `flutter_egl_getprocaddress.cpp` (new, this round).
- **Map:** `android_v3.map` = U15's `android_v2.map` with `eglGetProcAddress` added to the `LIBEGL` node (ATrace stay in
  `FLUTTER_ANDROID_1`).

```
A″  sha256 = b1c9f76e5b248c2c707b7a61f52503d379dd7564547bf461589ed23cdf903fe9   (built ×2 identical)
9b824502   = 9b8245022f9c98dac41a85acfa553e96e6385073fd7b15298199a1cce223647b   (U15, the base/deploy target A″ supersedes)
```

## Gates — A″ vs U15 `9b824502` (`evidence/`)

| gate | result |
|---|---|
| ×2 byte-identical | **yes** (`evidence/x2-identical.txt`) — both hw248 builds = `b1c9f76e` |
| old functions (`equiv.py`) | **34/34 common instruction-equal** (33 direct + 1 EQUAL-AFTER-RESIDUAL), differ 0, only-deployed 0 — **includes the 3 ATrace functions** (`evidence/equiv-9b824502-vs-Aprime2.txt`) |
| exports | **exactly +1** `eglGetProcAddress@@LIBEGL`; **0 removed**; the 3 ATrace + 4 EGL retained (`evidence/exports-needed-diff.txt`) |
| only-rebuilt functions | **6, all from the new file**: `eglGetProcAddress`, `gl_log`, `wl_glDepthRange`, `wl_glClearDepth`, `wl_gl_noop`, `first_time` (`ensure_driver` inlined) |
| NEEDED | **identical** to 9b824502 (`liboh_android_runtime.so`, `libsurface.z.so`, `libc++.so`, `libc.so`) |
| abi_diff `--calls` vs 9b824502 | **removed 0, added 1** (eglGetProcAddress), signature drift 0, consumer breaks 0, **call-set diffs 0**, exit 0 — **REMOVED empty** (`evidence/abi-calls-9b824502-vs-Aprime2.txt`) |
| compiler diagnostics | the **one** original `bionic_extra.c` `_GNU_SOURCE` warning; **none** from any extra `.cpp` |

So A″ is `9b824502` with original behaviour instruction-identical (the ATrace functions included), plus exactly the new
file's functions and the one new export — the outer's acceptance shape, with the ATrace exports preserved.

## Outer conditions (12:23)

- **Fallback no-op stub logs `[FLUTTER-GLSTUB] <name>` once per name per process.** case-C returns `wl_gl_noop`;
  before returning it, `gl_log(name)` prints `HiLogPrint(..., "FLUTTER-GLSTUB", "%{public}s", name)` gated by
  `first_time(name)` (dedupe). `HiLogPrint` is dlsym'd (RTLD_DEFAULT → the shared `liboh_android_runtime.so` handle) so
  there is **no undefined symbol** for `-Wl,--no-undefined,--fatal-warnings`.
- **glDepthRange call-width (dispatcher).** The resolved name string is exactly `glDepthRange` (not `glDepthRangef`) —
  the desktop-GL double entry, GL-spec `void(GLclampd, GLclampd)`; Impeller resolves the proc by that literal string, so
  the shim uses `(GLclampd, GLclampd)` → `glDepthRangef((GLfloat)…)`. Crash-prevention is ABI-independent.

## Deploy scope / relation to U14+U15

- Deploy **only** to `/system/android/lib64/westlake_flutter/libandroid.so`; A″ **supersedes** U15 `9b824502` there
  (A″ ⊃ 9b824502 ⊃ fff9). `westlake_native/libandroid.so` (`ee2fb82c`) for the 13 native-cluster packages is unchanged.
- A″ **is** 9b824502 + eglGetProcAddress. If `9b824502` is frozen before U16 ships, A″ goes through the frozen
  "add new functionality, original behaviour preserved" path — the 34/34 instruction-equal + abi `--calls` empty-REMOVED
  gates are that proof.
- **cx-bms U16 合包:** take the Flutter libandroid from the release below (A″), not fff9 and not bare 9b824502.

## Release (for cx-bms)

`$WORKSPACES/westlake-inputs/generations/u16-flutter-impeller-libandroid-v1/`
- `payload/android/lib64/westlake_flutter/libandroid.so` = `b1c9f76e5b248c2c707b7a61f52503d379dd7564547bf461589ed23cdf903fe9`
- `logs/u16-gpa2-{a,b}.log`, `SHA256SUMS`.

## Board check (when A0 window 11 produces a frame)

- Flutter raster thread gets past `+0x4b655c` (no `pc=0`); watch `[FLUTTER-GLSTUB] <name>` naming any residual gap proc.
- One read-only `sha256sum` of the deployed `westlake_flutter/libandroid.so` (underlay, not in the runtime fingerprint)
  to confirm it is `9b824502` before swapping in A″.

## Files

- `src/flutter_egl_getprocaddress.cpp` — the interposer (new). `src/android_v3.map` — version script (android_v2 + eglGetProcAddress).
- `src/flutter_egl.cpp` (U14), `src/ndk_trace.cpp` (U15), `build_flutter_android_hw248.sh` — copied for a self-contained build.
- `evidence/equiv-9b824502-vs-Aprime2.txt`, `exports-needed-diff.txt`, `abi-calls-9b824502-vs-Aprime2.txt`, `x2-identical.txt`, `u16-gpa2-{a,b}.log`.
- `artifacts/*.so` — A″ and 9b824502 (gitignored; A″ in the release generation).
- `results.json`.
