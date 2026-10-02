# U13 runtime v2 — NOT BUILT: Gap 1 shows nGetColorSpace is the wrong path for fd-musicplayer

Offline, no board, board #90. Goal was `U13 runtime v2 = 18763dd4 + ImageDecoder.nGetColorSpace returns sRGB`, gated on
first closing two gaps. **Gap 1 fails the gate: fd-musicplayer's null color space does not come through
`ImageDecoder.nGetColorSpace`, so that change would not move its first fatal.** Per the dispatch
("若是 BitmapFactory → 该修法无效、停"), I stopped and did not build v2. No runtime artifact produced.

## Gap 1 (decode path) — the deciding evidence
The crash is not on the album-cover path; it is a **resource bitmap**. Decompiling the exact frame
(`df.j.<init>`, androguard) shows (`evidence/decode-path.txt`):

```
v5_2 = v3_2.getDrawable(2131231018);   // R.drawable.ic_headset_padded  (a drawable RESOURCE)
createScaledBitmap( ((BitmapDrawable) v5_2).getBitmap(), dim, dim, 0 );   // <- the crash
```

`2131231018 = drawable/ic_headset_padded`, `2131231017 = drawable/ic_headset` — placeholder icons, cast to
`BitmapDrawable` (no ClassCastException in the stack → raster resources). Raster resource drawables decode via
`Resources → Drawable.createFromResourceStream → BitmapFactory.decodeResourceStream` (**BitmapFactory**), **not
ImageDecoder**. (The app's ImageDecoder path — `ContentResolver.loadThumbnail` for actual album art — is a different,
non-crashing path.)

## Where the null actually comes from — `Bitmap.nativeComputeColorSpace` (libhwui), proven from AOSP 14 source
`createBitmap(source,…)` reads `source.getColorSpace()` (Bitmap.java:956). For a BitmapFactory-decoded bitmap,
`mColorSpace` is lazy, so `getColorSpace()` (Bitmap.java:1871) calls `nativeComputeColorSpace(mNativePtr)`
(Bitmap.java:1874, native decl :2466). For the ic_headset resource bitmap that returns **null** → `cs == null` →
Bitmap.java:1203 throws `"can't create bitmap without a color space"`.

The fd-musicplayer hilog `OH_RegHook` confirms which impl runs:
- `Bitmap::nativeComputeColorSpace` → **libhwui** (pageOff 0xb10) — the method that returns null here.
- `BitmapFactory::nativeDecode*`, `Bitmap::nativeCreate`, `ImageDecoder::nCreate/nDecodeBitmap` → all **libhwui** (real).
- `ImageDecoder::nGetColorSpace` → registered twice (libhwui then the runtime compat_shim stub, which wins and returns
  null) — but it is on the **ImageDecoder** path only, not this resource/BitmapFactory crash.

So the v2 change (`ID_nGetColorSpace → sRGB`) targets a method that is **not on fd-musicplayer's path**. It would not
move the first fatal. **STOP.**

## Gap 2 — not reached
The register-order verification (ColorSpace before Bitmap/ImageDecoder, statically in deployed `ac59dec0`) was the
second gate. It is moot because Gap 1 already stops the build. It would only matter for the alternative below.

## The real layer, and why it is blocked
The null is `Bitmap.nativeComputeColorSpace` in **libhwui** (`be59260f`), which has **no reproducible frozen source**
(DIGEST 610; cx-bms deferred libhwui). The root-layer fix (make the resource/decode path attach an SkColorSpace, or
make `nativeComputeColorSpace` map it to sRGB) is in that blocked library — the same blocker as fd-plus's
`nativeLockCanvas`.

## An on-path runtime alternative (proposal only — needs its own authorization, NOT built here)
There IS a runtime-side fix on the correct method: override `Bitmap.nativeComputeColorSpace` in the compat_shim (as
`nGetColorSpace` is already overridden) so that, when the real libhwui result would be null, it returns
`ColorSpace.get(Named.SRGB)`. This is a one-.o runtime change and **is** on fd-musicplayer's path. Caveats that make it
a separate decision, not this round's authorized change:
- it would need to call through to the real libhwui `nativeComputeColorSpace` (resolve its address, e.g. dlsym on
  libhwui) and default to sRGB only on null, so bitmaps with a genuine non-sRGB space keep it;
- returning sRGB unconditionally (simpler) changes the reported color space for every bitmap — a broader behavior
  change needing review;
- Gap 2 (ColorSpace registers before Bitmap, verified in the deployed binary) must then be confirmed, since the
  override constructs a `ColorSpace` object.

Recommend: the outer decides whether to pursue this `nativeComputeColorSpace` override (new scope) or defer
fd-musicplayer with fd-plus until libhwui has a reproducible source. **U13 runtime stays `18763dd4`** (the three Flutter
keys ride it unchanged; nothing new is needed for them).

## This round's rule
Close the fix-invalidating gap before building: the authorized fix named a method (`nGetColorSpace`), but the decompiled
crash frame + AOSP source + the deployed `OH_RegHook` libs show the null is produced by a *different* method
(`nativeComputeColorSpace`, libhwui) on a *different* decode path (resource/BitmapFactory, not ImageDecoder). A one-read
decompile of the actual crash frame (`df.j.<init>`) is what distinguishes "placeholder resource icon" from "album cover"
and flips BUILD into STOP.

## Files
- `evidence/decode-path.txt` — the df.j.<init> decompile, the resource ids, the AOSP Bitmap.java line proof, and the
  OH_RegHook native-registration libs showing nativeComputeColorSpace→libhwui vs nGetColorSpace→runtime stub.
