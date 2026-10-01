# libstdc++ consumers static scan — U9 full corpus (66 original + 100 cv2)

Dispatch (ACK(90) 2026-10-01T19:16:10): scan all U9 full-corpus APKs' `lib/arm64-v8a/*.so` NEEDED entries for `libstdc++.so` / `libc++_shared.so`; anchor: toutiao's `libflipped.so` must appear.

## Numbers first

- Scanned: **66 original keys** (`~/a2hlab/app-inputs/<key>/*.apk`) + **100 cv2 keys** (`$WORKSPACES/westlake-inputs/corpus-v2/app-inputs/<key>/*.apk`).
- Consumers with NEEDED `libstdc++.so` or `libc++_shared.so`: **606** (all in original-66, **0 in cv2-100**).
- Anchor: **toutiao's libflipped.so IS in list** ✅ (toutiao.apk has `lib/arm64-v8a/libflipped.so` + `lib/arm64-v8a/libc++_shared.so`).
- Self-contained C++ runtime: **554 keys** have `libc++_shared.so` (they ship their own C++ runtime, not dependent on system libstdc++).

## Verdict distribution (U8 sign-off)

| Verdict | Count |
|---|---|
| dead | 115 |
| unknown | 479 |
| alive-white-window | 5 |
| lit | 6 |
| alive-black-window | 1 |

**Lit keys (regression candidates for U10 namespace change):** fd-minetest, fd-mpv (×2), fd-seal (×3).

## Per-key consumers (sample)

| Key | .so | NEEDED | U8 verdict | Source |
|---|---|---|---|---|
| toutiao | lib/arm64-v8a/libflipped.so | libstdc++.so | dead | original-66 |
| burgerking | lib/arm64-v8a/libNitroMmkv.so | libc++_shared.so | dead | original-66 |
| burgerking | lib/arm64-v8a/libNitroModules.so | libc++_shared.so | dead | original-66 |
| burgerking | lib/arm64-v8a/libappmodules.so | libc++_shared.so | dead | original-66 |
| burgerking | lib/arm64-v8a/libexpo-modules-core.so | libc++_shared.so | dead | original-66 |
| burgerking | lib/arm64-v8a/libexpo-updates.so | libc++_shared.so | dead | original-66 |

## Scope note

commercial100 (TikTok / Lemon) is **not** in the U9 full corpus — not scanned. The `libflipped.so` anchor is on the original-66 toutiao APK, not on commercial100's TikTok/Lemon packages.

## Method

- `llvm-readelf -d` on each `lib/arm64-v8a/*.so` in each APK.
- Join with outer-signoff.json (U8 verdict) for regression candidates.
- No board writes; all files in t4 worktree.

## Self-bundled libstdc++.so (regression risk for U10 namespace change)

**0 keys** bundle their own `libstdc++.so` in `lib/arm64-v8a/` — all 554 keys with C++ runtime ship `libc++_shared.so` (the NDK shared runtime), not `libstdc++.so`. The regression risk for U10's shared SONAME set change is the **554 keys with `libc++_shared.so`**: if U10 adds `libstdc++.so` to the shared SONAME set, these keys' self-contained C++ runtime may collide with the shared one (duplicate symbols, ODR violations).

**Regression candidates for U10 namespace change:** the 554 keys with `libc++_shared.so` (fd-minetest, fd-mpv, fd-seal are lit; the other 551 are dead/unknown/white-window). The lit keys are the ones to watch: if the shared SONAME change breaks them, U10 regresses.

Outer note (19:32): "554 keys" in the lane's section counts `.so` rows, not keys (the sweep has 166 keys). No key bundles its
own `libstdc++.so`, so adding it to the inherited SONAME set overrides nothing. Libraries that NEED only
`libc++_shared.so` never load `libstdc++.so`, so the ODR risk the lane raises does not arise for them; fd-minetest,
fd-mpv, fd-seal (lit, bundle libc++_shared) stay as cheap regression controls anyway.

## Outer-loop reading (2026-10-01 19:30) -- key level, U9 sweep only

The 606 rows are per `.so`; at key level 22 keys appear, 9 of them `co-*` commercial inputs outside the U9 sweep.
Sweep keys whose bundled `.so` NEED the system `libstdc++.so`: **toutiao, mindustry, fd-plus** (dead), **fd-app,
fd-shatteredpixeldungeon, termux** (white), **x** (black). Their U9 hilogs (5cd/5ea runs) show:

- fd-app / shatteredpixeldungeon / termux: no libstdc++ load failure (only the benign B8-NATIVE html_compat load every
  app logs) -- the U10 shared-SONAME change is not expected to move them; they are the **regression controls** that
  must stay at least white.
- mindustry: fatal `Error relocating libarc.so: slCreateEngine: symbol not found` -- U9's libOpenSLES.so facade
  (cx-bms 452b8f18f) exports no slCreateEngine. An OpenSLES wall, not libstdc++.
- fd-plus: `Error relocating libc++_shared.so: android_set_abort_message: symbol not found` -- the symbol U10's abort
  visibility shim provides (so fd-plus joins meet as a beneficiary).
- toutiao, x: not yet run on U9.
