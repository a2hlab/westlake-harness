# Bitmap null ColorSpace (C5): the JNI is complete; the source bitmaps genuinely have no SkColorSpace

Offline, board #90, no board. U15 candidate #2. privacybrowser (U13/5ea) and fd-musicplayer (U12/5cd) die at
`Bitmap.createScaledBitmap → createBitmap(Bitmap.java:979) → :1203` with `IllegalArgumentException: can't create
bitmap without a color space` (ref `master 49e6f805da benchmark/2026-10-03-u13-first-fatal-clusters`, cluster C5).
This pins the layer: **the Bitmap color-space JNI is fully registered and matches AOSP 14 — the null is genuine
(`SkBitmap.info().colorSpace()==nullptr` on the source bitmap)**, and a one-function `sRGB`-fallback in libhwui (or
framework.jar) clears it.

## ① B10 JNI coverage: nativeComputeColorSpace is registered, matches AOSP 14 (`evidence/jni-coverage-bitmap-colorspace.txt`)
The Bitmap JNI is hosted in **`libhwui.so`** (`be59260f…`), not `liboh_android_runtime.so` 18763dd4 (the runtime only
*calls* `register_android_graphics_Bitmap`). libhwui's `gBitmapMethods` table contains the live method strings
`nativeComputeColorSpace`, `nativeIsSRGB`, `nativeIsSRGBLinear`, `nativeSetColorSpace` (+ the full Bitmap set), and the
backing C++ fns (`Bitmap_computeColorSpace`, `GraphicsJNI::getNativeColorSpace/getColorSpace`, `SkColorSpace::MakeSRGB`)
are defined. Compared to AOSP 14 `frameworks/base/libs/hwui/jni/Bitmap.cpp:1261-1265` — the registered set **matches
exactly**. `hwui_register_stubs.cpp` stubs only `register_android_graphics_BitmapRegionDecoder` / `YuvToJpegEncoder`,
**not** the main `register_android_graphics_Bitmap`.

So — correcting cc-t3's "nativeComputeColorSpace has no ColorSpace" at the *registration* level — the native is present
and genuine. `Bitmap_computeColorSpace` (`Bitmap.cpp:942-949`) returns null **by design** when
`bitmapHolder->info().colorSpace()==nullptr`. **The JNI coverage is complete; the null is a real "source SkBitmap
carries no SkColorSpace", not a missing/stubbed method.**

**The fix lever (internal inconsistency):** `Bitmap_isSRGB` (`Bitmap.cpp:925-930`) already does
`return colorSpace == nullptr || colorSpace->isSRGB();` — it treats a null colorspace **as sRGB** — while
`computeColorSpace` returns null. Aligning the two is the minimal fix (§④).

## ② dexdump of the two call sites (`evidence/callers-dexdump.txt`, `evidence/hilog-scan.txt`)
Both scale a bitmap that was **not** minted by Java `Bitmap.createBitmap(w,h,config)` (which defaults to sRGB):

| key | caller (dexdumped) | source bitmap | config |
|---|---|---|---|
| privacybrowser | `MainWebViewActivity.u → .B → .z` → `NestedScrollWebView.getFavoriteIcon()` → `createScaledBitmap(…,0x80,0x80,…)` | the **WebView favicon** (`WebHistoryItem.getFavicon()` / `onReceivedIcon`), minted by OH WebView (ArkWeb-chromium) | non-ALPHA_8 |
| fd-musicplayer | `AlbumsFragment.f → df.j.<init>` → `((BitmapDrawable)p3).getBitmap()` → `createScaledBitmap(…)` | a **resource/placeholder `BitmapDrawable`** (the default album-cover drawable passed to the adapter ctor) | non-ALPHA_8 |

The AOSP 14 chain (`evidence/aosp14-bitmap-refs.txt`): `createScaledBitmap → createBitmap(source,…)` reads
`source.getColorSpace()` (`Bitmap.java:956`); `getColorSpace()` calls `nativeComputeColorSpace` (`:1873-1874, :2466`),
which returns null; the checked `createBitmap` throws at `:1202-1203` because `colorSpace==null && config!=ALPHA_8`.
**Why null:** neither source went through the sRGB-defaulting Java `createBitmap(w,h,config)` — one is a native
WebView bitmap, one is a decoded/placeholder drawable — and route-A's producers left `SkBitmap.info().colorSpace()`
unset for them. (It is *not* a universal decode break: see ③ — only these two keys, and both come from a non-standard
producer.)

## ③ Cross-key scan of U12/U13 hilogs (`evidence/hilog-scan.txt`)
Exactly **2 distinct keys**, matching cluster C5 — no others (the `GetSupportedColorSpaces` lines elsewhere are OS
`C04201/DMS` display noise, not app faults):

| key | U-gen | board | first-fatal? |
|---|---|---|---|
| fd-musicplayer | U12 | 5cd | **yes — terminal** (only `initChild failed`; the earlier `MediaStore$Audio$Artists` NCDFE was a *background* Thread-5/6 "process kept alive", non-terminal) |
| cv2-com-stoutner-privacybrowser-standard | U13 | 5ea | **yes — terminal** (only `initChild failed`; an earlier `kotlinx CoroutineStart` CNFE was caught, bind continued) |

Generation note: privacybrowser's U12 first-fatal was a **WebView** wall (`UnsupportedOperationException … current
WebView APK`); in U13 it cleared that and *advanced* to this colorspace wall ("the U12 webkit wall moved here"), so this
is its **current** first-fatal, newly exposed. That the symptom is confined to 2 keys (not dozens) confirms this is a
**non-standard-producer** issue, not a blanket decode regression.

## ④ Minimal fix + prediction
**Layer / artifact — primary: `libhwui.so`** (one function; same patch mechanism as the existing
`aosp_patches/libs/hwui/patches/jni/BitmapFactory.cpp.patch`). Patch `Bitmap_computeColorSpace` to fall back to sRGB
for a **non-ALPHA_8** bitmap with a null `SkColorSpace`, matching `Bitmap_isSRGB`'s existing null==sRGB treatment
(`recipe/bitmap-computecolorspace-srgb.patch`):

```cpp
SkColorSpace* colorSpace = bitmapHolder->info().colorSpace();
const SkColorType ct = bitmapHolder->info().colorType();
if (colorSpace == nullptr) {
    if (ct == kAlpha_8_SkColorType) return nullptr;        // ALPHA_8 legitimately has none (Java guard allows it)
    return GraphicsJNI::getColorSpace(env, SkColorSpace::MakeSRGB().get(), ct);
}
return GraphicsJNI::getColorSpace(env, colorSpace, ct);
```

Rollback = drop the patch. This fixes at the single read point `getColorSpace()`, so it covers **every**
`createBitmap`/`createScaledBitmap`/`getColorSpace` caller (webview favicon, placeholder drawable, and any future
null-colorspace scaler), not just these two. Assuming sRGB for an untagged bitmap is the legacy-Android default and is
already what `isSRGB` implies — semantically safe; the only legitimately-null case (ALPHA_8) is preserved.

**Alternative — framework.jar `Bitmap.java`** (if a native rebuild is undesirable): at `createBitmap(source,…)`
(AOSP14 `:956`) default `cs = source.getColorSpace(); if (cs == null && source.getConfig() != Config.ALPHA_8) cs =
ColorSpace.get(Named.SRGB);`. Same effect, one line, but patches the JAR. **Can it go into U14?** Yes — either is a
single small artifact; the libhwui patch is the cleaner fit since we already patch hwui jni and it needs no framework.jar
rebuild. The outer decides whether to fold it into U14.

**Prediction (first-fatal metric).** Both failures are `bound` java-causes (bind reached `createApplication`/first
layout) and are each the *terminal* first-fatal, so clearing them lets execution proceed past the scaler:
- **privacybrowser**: favicon scaling succeeds → moves past this wall; next first-fatal unknown (it already cleared the
  U12 webkit wall), lit likelihood **medium** (webview content may surface further walls).
- **fd-musicplayer**: album-art scaling succeeds → the adapter builds; the earlier `MediaStore$Audio$Artists` NCDFE is a
  *background* thread (process stays alive), so the main UI likely surfaces. Lit likelihood **medium–high**.
- **Blast radius**: static — only these 2 keys carry the signature (③), so this clears cluster C5 (2 keys) and
  hardens any future null-colorspace scaler.

## This round's rule
Before blaming a missing JNI, check the registration table and the native's own logic: here `nativeComputeColorSpace`
is registered and matches AOSP 14 — it returns null *correctly* for a colorspace-less source. The real gap is upstream
(producers mint bitmaps without a colorspace) and the cheapest durable fix is a defensive sRGB fallback at the one read
point, aligned with the `isSRGB` null==sRGB convention the codebase already uses.

## Files
- `evidence/jni-coverage-bitmap-colorspace.txt` — libhwui registration vs AOSP 14 (①), the isSRGB inconsistency.
- `evidence/callers-dexdump.txt` — the two dexdumped call sites + source bitmaps (②).
- `evidence/aosp14-bitmap-refs.txt` — exact AOSP 14 Bitmap.java / Bitmap.cpp line refs for the throw chain.
- `evidence/hilog-scan.txt` — the full U12/U13 scan = 2 keys, both terminal (③).
- `recipe/bitmap-computecolorspace-srgb.patch` — the proposed minimal libhwui fix + the JAR alternative (④, staging only).
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline; no board; no push. Decompile via Android SDK `apkanalyzer` (read-only on the two apks); binary symbols via
`nm`/`strings`. The fix is the hwui/framework owner's to build + ship — this is static staging only. Sources read
read-only: the two apks (`westlake-inputs/corpus-v2`, `westlake-inputs/apks/fdroid100`), the deployed `libhwui.so` +
runtime (`westlake-inputs/generations`), the AOSP 14 reference (`westlake-inputs/aosp-14.0.0_r1-src`), the adapter hwui
patches (`westlake-harness/bms`), the run records (`westlake-harness`, `-u7-executor`).
