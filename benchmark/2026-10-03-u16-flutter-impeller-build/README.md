# U16 Flutter Impeller proc gap — BUILD: the eglGetProcAddress interposer compiled into the U14 flutter libandroid; A′ = `15e9885a`, ×2 byte-identical, 31/31 old functions instruction-equal to fff9, +1 export `eglGetProcAddress@@LIBEGL`

#90, native, offline. Nothing went to a board. Design: `benchmark/2026-10-03-u16-flutter-impeller-proc/` (slot #468 =
`glDepthRange`, build 0d216f3f). For cx-bms's U16 合包 draft.

## What was built

A′ = **U14 `fff9be31` + the `eglGetProcAddress` interposer** (`src/flutter_egl_getprocaddress.cpp`). Same Flutter-private
`libandroid.so`, same recipe and inputs as U14, one extra object and one extra version-script export.

- **Recipe:** `build_flutter_android_hw248.sh` (U14's, verbatim) on hw248, in the reused U14 mirror
  `/home/alvin/cc-t3-nabi-2026103/westlake-harness-bms-deploy` (58-char root), frozen clang-15 `feef13a3`, the v3c
  runtime `9e14bf20`, platform-pool `libnative_window`/`libnative_buffer`. Extras compiled with
  `clang++ -std=c++17 -nostdinc++ -fno-exceptions -fno-rtti`, linked after `bionic.o` with
  `libclang_rt.builtins.a` before `libc++.so` (U14's emutls ordering).
- **Extras:** `flutter_egl.cpp` (U14's, unchanged — keeps the eglCreateWindowSurface interposer) **+**
  `flutter_egl_getprocaddress.cpp` (new).
- **Map:** `android_egl_procaddr.map` = U14's `android_egl.map` with `eglGetProcAddress` added to the `LIBEGL` node.

```
A′ sha256 = 15e9885a2086ab854e4489fdaf3a39d74aa94c7155e9b7184d4ac2e3c281a85a   (built ×2 identical)
fff9      = fff9be3190f1b1c99c3fd4559d258cbac131fb657d10b1fa7060f61c4002d5e5   (U14, the deploy target A′ supersedes)
```

## Gates — A′ vs fff9 (`evidence/`)

| gate | result |
|---|---|
| ×2 byte-identical | **yes** (`evidence/x2-identical.txt`) — both hw248 builds = `15e9885a` |
| old functions (`equiv.py`) | **31/31 common instruction-equal** (30 direct + 1 EQUAL-AFTER-RESIDUAL), differ 0, only-deployed 0 (`evidence/equiv-fff9-vs-Aprime.txt`) |
| exports | **exactly +1**: `eglGetProcAddress@@LIBEGL`; 0 removed; `eglCreateWindowSurface@@LIBEGL` etc. unchanged (`evidence/exports-needed-diff.txt`) |
| only-rebuilt functions | **6, all from the new file**: `eglGetProcAddress`, `gl_log`, `wl_glDepthRange`, `wl_glClearDepth`, `wl_gl_noop`, `first_time` (`ensure_driver` inlined) |
| NEEDED | **identical** to fff9 (`liboh_android_runtime.so`, `libsurface.z.so`, `libc++.so`, `libc.so`) — no new dep |
| compiler diagnostics | the **one** original warning (`bionic_extra.c` `_GNU_SOURCE` redefined); **none** from either extra `.cpp` |

So A′ is fff9 with original behaviour instruction-identical, plus exactly the new file's functions and the one new
export/redirect — the outer's acceptance shape.

## Outer conditions (12:23)

- **Fallback no-op stub logs `[FLUTTER-GLSTUB] <name>` once per name per process.** Implemented: case-C returns
  `wl_gl_noop`; before returning it, `gl_log(name)` prints `HiLogPrint(..., "FLUTTER-GLSTUB", "%{public}s", name)`,
  gated by `first_time(name)` (dedupe by name pointer/string). `HiLogPrint` is resolved by `dlsym` (RTLD_DEFAULT → the
  shared `liboh_android_runtime.so` handle), exactly as U14's `n6_log`, so there is **no undefined symbol** for
  `-Wl,--no-undefined,--fatal-warnings`.
- **glDepthRange call-width check (dispatcher).** The resolved name string is exactly `glDepthRange` (not
  `glDepthRangef`) — the desktop-GL double entry, GL-spec signature `void(GLclampd, GLclampd)`; Impeller resolves the
  proc by that literal string, so the slot's typedef is the double ABI. The shim uses `(GLclampd, GLclampd)` and
  forwards to `glDepthRangef((GLfloat)…)`. Crash-prevention is ABI-independent (any non-NULL resolve fills the slot);
  the double signature is what keeps depth-range correct. (The crash call goes through a shared wrapper `x21`
  (`[sp,#0x20]`) stored at entry+0x18; the raw proc is at entry+0x10 — see the design dir's `crash-slot-trace.txt`.)

## Deploy scope / relation to U14

- Deploy **only** to `/system/android/lib64/westlake_flutter/libandroid.so`; A′ **supersedes** U14 `fff9be31` there (A′ ⊃
  fff9). The `westlake_native/libandroid.so` copy for the 13 native-cluster packages stays `ee2fb82c`.
- A′ **is** fff9 + eglGetProcAddress. If U14's `fff9be31` is frozen before U16 ships, A′ goes through the frozen
  "add new functionality, original behaviour preserved" path — the 31/31 instruction-equal gate is that proof.
- **cx-bms U16 合包:** take the Flutter libandroid from the release below instead of fff9.

## Release (for cx-bms)

`$WORKSPACES/westlake-inputs/generations/u16-flutter-impeller-libandroid-v1/`
- `payload/android/lib64/westlake_flutter/libandroid.so` = `15e9885a2086ab854e4489fdaf3a39d74aa94c7155e9b7184d4ac2e3c281a85a`
- `logs/u16-gpa-{a,b}.log`, `SHA256SUMS`.

## Pre-deploy / board check (unchanged from U14 + this)

- One read-only `sha256sum` of the deployed `westlake_flutter/libandroid.so` (underlay, not in the runtime
  fingerprint) to confirm it is `ee2fb82c`/`fff9be31` before swapping in A′.
- On a board run: the Flutter raster thread should get past `+0x4b655c` (no `pc=0`); watch for `[FLUTTER-GLSTUB] <name>`
  lines naming any residual gap proc that fell to the no-op path.

## Files

- `src/flutter_egl_getprocaddress.cpp` — the interposer (new). `src/android_egl_procaddr.map` — version script (+eglGetProcAddress).
- `src/flutter_egl.cpp`, `build_flutter_android_hw248.sh` — copied from `2026-10-03-u14-flutter-libandroid` for a self-contained build.
- `evidence/equiv-fff9-vs-Aprime.txt`, `exports-needed-diff.txt`, `x2-identical.txt`, `u16-gpa-{a,b}.log`.
- `artifacts/*.so` — A′ and fff9 (gitignored; in the release generation).
- `results.json`.
