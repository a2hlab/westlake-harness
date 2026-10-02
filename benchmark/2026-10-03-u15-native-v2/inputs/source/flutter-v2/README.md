# U15 Flutter-private libandroid v2 = fff9be31 + ATrace_beginSection / ATrace_endSection / ATrace_isEnabled = `9b824502` (×2): exports exactly +3, 31/31 old functions instruction-equal, no new NEEDED or open site; immich's libraries replay 0 missing in the Flutter domain

#90, native, offline. No board touched. Built on hw248 with frozen clang feef13a3, with fff9be31's own recipe in the same
58-char mirror. The wall: cluster C4 / `2026-10-03-u15-ndk-private-domains` (cc-wiki 4e7c41000b). With the NSD stubs
(94a94905) this is immich's second wall.

## 1. Semantics: AOSP 14 r1, not a guess (`aosp/`, `src/ndk_trace.cpp`)

**The NDK functions.** `frameworks/base/native/android/trace.cpp` (android-14.0.0_r1, frameworks/base 299fe6f5,
sha256 `7c4a1504…`; sparse-fetched on hw248):
- `ATrace_isEnabled()` = `atrace_is_tag_enabled(ATRACE_TAG_APP)`;
- `ATrace_beginSection(n)` = `atrace_begin(ATRACE_TAG_APP, n)`;
- `ATrace_endSection()` = `atrace_end(ATRACE_TAG_APP)`.

**The helpers** (`system/core/libcutils/include/cutils/trace.h`, sha256 `341eed8d…`, lines 149-178):
- `atrace_is_tag_enabled(tag) = atrace_get_enabled_tags() & tag`, with `ATRACE_TAG_APP = 1<<12`;
- begin and end call `atrace_begin_body(name)` / `atrace_end_body()` **only when that tag is enabled**.

**Correction to the draft in cc-wiki's report.** It had `ATrace_isEnabled` return `atrace_get_enabled_tags() != 0`, i.e.
any tag. AOSP masks `ATRACE_TAG_APP`, and so does this file.

## 2. Binding: through the existing NEEDED, not dlsym

**The choice.** `ndk_trace.cpp` references `atrace_get_enabled_tags`, `atrace_begin_body` and `atrace_end_body`
directly.

**Why direct reference.**
- All three are exported by the runtime, checked in every copy that matters: the recipe's link input `9e14bf20`
  (v3c), U13 `18763dd4` and U15 `94c31177`.
- fff9be31 **already NEEDs `liboh_android_runtime.so`**, so the link adds 3 imports and **no NEEDED**.
- At load they bind through that edge to the runtime instance the Flutter domain already shares: it is inherited from
  the owners, and published RTLD_GLOBAL by `needs_runtime`, which is true for every `flutter_private` app.
- No `dlopen`/`dlsym` is added, so there is no new open site and no way to reach a second copy.
- A dlsym on a runtime handle, flutter_egl.cpp-style, would only add an open-site-like lookup for symbols the static
  edge already provides.

**Version node.** The three names go into the existing `FLUTTER_ANDROID_1` node (`src/android_v2.map`, a one-line diff
from `android_egl.map`). libcronet imports them unversioned (board: `use_vna_hash=0`), which any node satisfies. No new
version definition.

## 3. Build (`evidence/build-*.log`, teed)

**Baseline check.** fff9be31's script on hw248 (`build_flutter_android_hw248.sh` c2ca5918), run again unchanged with
`flutter_egl.cpp`, gives **`fff9be31` exactly**. The environment is intact.

**v2.**
- Same script, extras `flutter_egl.cpp` (unchanged, same mirror path) + `src/ndk_trace.cpp`, `ANDROID_MAP=android_v2.map`.
- Result: **`9b8245022f9c98dac41a85acfa553e96e6385073fd7b15298199a1cce223647b`** ×2, rc 0.
- Compiler output: only the pre-existing `bionic_extra.c` `_GNU_SOURCE` warning, also present in the fff9 baseline.

## 4. Gates vs fff9be31 (`evidence/gates.txt`)

| gate | result |
|---|---|
| exports | **+3 exactly**: `ATrace_beginSection`, `ATrace_endSection`, `ATrace_isEnabled` `@@FLUTTER_ANDROID_1`; 0 removed |
| imports | +3: `atrace_begin_body`, `atrace_end_body`, `atrace_get_enabled_tags` (from the runtime); 0 removed |
| NEEDED / SONAME | identical (`liboh_android_runtime.so`, `libsurface.z.so`, `libc++.so`, `libc.so`) |
| open sites | `open_site_scan` 7 = 7, identical; dlopen 7 = 7, dlsym 8 = 8 |
| old functions (`equiv.py`) | **31/31 instruction-equal** (30 + 1 after residual resolution), 0 differ; 3 new (the ATrace functions) |
| strings | + the 3 names, the 3 body names, the helper name, `ndk_trace.cpp`, `sectionName`, debug path; 0 removed |

## 5. immich in the Flutter-private domain (`replay_flutter.py` → `evidence/replay-immich-flutter.txt`)

**Model** (wrapper over `../2026-10-03-u15-compat-v3/replay_normal.py`):
- `westlake_flutter/` is searched right after the app directory;
- globals: westlake_flutter native_abi d2053066 + the resident runtime;
- the parent's "NDK names count as provided" shortcut is off, because the libandroid is the object under test.

| immich library (APK 36b0d136) | westlake_flutter as in U14 (fff9be31) | with v2 (9b824502) |
|---|---|---|
| libcronet.143.0.7445.0.so | **2 missing: `ATrace_beginSection`, `ATrace_endSection`**: reproduces the board's line | **0** |
| the other 9 (libflutter, libapp, libmaplibre, libsqlite3*, libdartjni, …) | 0 | 0 |

## 6. Prediction (immich, with U15 = NSD stubs 94a94905 + this libandroid)

| | |
|---|---|
| wall 1, bind VerifyError `A2.b` | moves (NSD stubs; host ART proven) |
| wall 2, libcronet `ATrace_beginSection` | **moves (high)**: replay 0 missing, calibrated on the board line |
| next | the Flutter raster path. This same libandroid carries U14's `eglCreateWindowSurface` interposer, which moved localsend / kitchenowl / fluffychat / libre (prediction high). fd-saber lit under U13 through the Impeller GLES fallback. |
| **lit** | **low–medium**. If the engine draws, immich's first screen is its own server-URL login page (own UI). Unknowns: Impeller/Vulkan fallback, maplibre, and the next unseen wall after the network stack. |
| other keys | 0 first-fatal moves. The 6 Flutter packages get 3 more exports that are never called unless an app library imports them, and of the 6 Flutter packages only immich has an ATrace_* importer (libcronet; scan of all their arm64 libraries). |

## Release (for cx-bms, westlake_flutter/ slot)

- `$WORKSPACES/westlake-inputs/generations/u15-flutter-libandroid-v2/payload/android/lib64/westlake_flutter/libandroid.so`
  = **9b824502**.
- It replaces fff9be31 in `westlake_flutter/` only; `westlake_native/libandroid.so` is unchanged.
- Also there: `builds/` (a, b), `logs/` (baseline check + v2 ×2), the source and map, `SHA256SUMS` (8).

## Files

- `src/ndk_trace.cpp`, `src/android_v2.map`.
- `aosp/trace.cpp.aosp14r1`, `aosp/cutils-trace.h.aosp14r1`.
- `replay_flutter.py`.
- `evidence/`: `build-*.log`, `gates.txt`, `replay-immich-flutter.txt`.
- `results.json`.
