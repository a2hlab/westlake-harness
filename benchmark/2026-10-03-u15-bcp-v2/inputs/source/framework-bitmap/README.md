# U15 JAR #1: framework.jar Bitmap.getColorSpace() sRGB fallback (null-colorspace wall)

#90, JAR, offline build on Mac + host re-bake on hw248; no board, no a2hlab. The fix for the Bitmap null
ColorSpace wall (`benchmark/2026-10-03-bitmap-colorspace`, C5: privacybrowser + fd-musicplayer) chosen by the
outer **not** as a libhwui patch (DIGEST 613: libhwui `be59260f` has no reproducible frozen build input — the only
recorded build `a11c9154` ≠ `be59260f`, so a patch can't land on a faithful baseline) but as a one-method edit in
**framework.jar `Bitmap.getColorSpace()`** (BCP; re-baked). **Not folded into U14** (U14 is emitting pairing
receipts; a framework change needs its own re-bake + review) — this is the first U15 JAR item.

## Frozen gate (checked first) — PASS
`knowledge/frozen/frozen.json` (FZ-001..008): **framework.jar is not a frozen artifact**, and no entry covers
`android.graphics.Bitmap`/`getColorSpace`. The frozen BCP classes (FZ-007 tagsoup, FZ-008 SSLSockets) live in a
*different* jar (`adapter-mainline-stubs.jar`, earlier in BCP order), so a Bitmap-only edit doesn't touch them;
FZ-005 is the re-bake *toolchain* I use, not modify. Proceeded. (`evidence/frozen-gate.txt`.)

## The fix (one method, `evidence/build-gates.txt`, `recipe/Bitmap.getColorSpace.smali.patch`)
At the Java read point `Bitmap.getColorSpace()` — after it caches `mColorSpace = nativeComputeColorSpace(mNativePtr)`:

```
if (mColorSpace == null && getConfig() != Config.ALPHA_8)
    mColorSpace = ColorSpace.get(ColorSpace.Named.SRGB);
```

Semantics match (a) `Bitmap_isSRGB` which **already treats a null `SkColorSpace` as sRGB**
(`Bitmap.cpp:930`), and (b) real-device behavior where decoded/created bitmaps always carry a color space. ALPHA_8
legitimately has none and is preserved (and the explicit-null `createBitmap(...,null)` guard at `Bitmap.java:1203`
is intentionally left intact — the fix only supplies a space for the *implicit* `getColorSpace()` path that
`createScaledBitmap` reads). The injected smali reuses registers `v0/v1/p0` (`.registers 3` unchanged); every
member it references (`getConfig`, `Config.ALPHA_8`, `ColorSpace$Named.SRGB`, `ColorSpace.get`) already exists in
`classes.dex`.

## Gates (cc-t3 JAR playbook)
Base deployed framework.jar `3e106350…`; `android/graphics/Bitmap` is in `classes.dex` (1 of 5).
- **2-pass determinism:** `smali assemble -j1` twice → identical `classes.dex` =
  `e14cb9ecfbe4e55523287f975cdec35388bbae9f0022f341356100170c06be7d`.
- **Round-trip smali diff vs base:** 18 files differ = **1** `Bitmap.smali` (the intended change) + **17 benign**
  static-`final` default-value re-encodings (`= 0x0`/`= false` dropped on round-trip — semantically identical;
  ART inits statics to the type default regardless); **0** instruction/method-body changes outside Bitmap.
- **deployed_class_diff vs 3e106350:** 29341 classes both, **0 dropped / 0 added / 0 superclass-or-interface
  change**; Bitmap unchanged (`Object` / `[Parcelable]`). (The stock `deployed_class_diff.py` crashes on this dex
  with a `UnicodeDecodeError` — it hardcodes `text=True` on `dexdump` output that holds non-UTF8 bytes; reproduced
  its exact `{class:(superclass,interfaces)}` logic with latin-1 decoding.)
- Repack: `zip -X -0` (STORED, matching base dex entries) swap of `classes.dex` only →
  `framework-u15.jar` = `9e55e286…`.

## hw248 host re-bake — PASS (`evidence/hw248-rebake-and-native-boundary.txt`)
framework.jar is BCP, so it needs a boot-image re-bake (FZ-005 `dex2oat64`, board cmdline). Baseline (orig jar)
and modified (u15 jar) both **`dex2oat rc=0` (~7 s)**. dex2oat ran ART's class verifier (log phases
`before_verification`/`after_verification`/`ClassVerifier_Init`) with **no verification failure for any class,
incl. `android.graphics.Bitmap`** → **ART's verifier accepts the new `getColorSpace` bytecode**; the modified jar
bakes into a valid boot image. The u15 `boot.oat` differs from baseline (the Bitmap class is recompiled).

## Honest limit: the live behavioral test is native-bound-infeasible on host ART
The dispatch asked for a host-ART run showing "new `createScaledBitmap` doesn't throw on a colorspace-less source;
old reproduces the on-board line". This **cannot run on hw248 host ART**: it is `linux-x86` and has **no**
`libhwui.so`/`libandroid_runtime.so` (arm64 board libs). `getColorSpace()`'s branch is driven by the *native*
`nativeComputeColorSpace` (libhwui), and minting a source bitmap needs `nativeCreate` (libhwui) — both absent on
host (the same native boundary cc-t3's `u14-jar-v1` host-ART test documented). Behavioral correctness is therefore
established by: the **verified bytecode** (the recipe patch + dex2oat verifier acceptance), **AOSP 14 semantics**
(getColorSpace→nativeComputeColorSpace; createScaledBitmap→createBitmap(source) reads `source.getColorSpace()`;
null+config≠ALPHA_8 throws at `:1203` — the fix returns sRGB so the throw cannot fire), and **alignment with
`Bitmap_isSRGB`** (null==sRGB). A true pass/fail requires an on-board (arm64) deploy of the re-baked image, which
is the deploy owner's step.

## Prediction (first-fatal metric)
With the re-baked BCP, `privacybrowser` (favicon scaling) and `fd-musicplayer` (album-cover scaling) no longer hit
`createScaledBitmap → "can't create bitmap without a color space"`; both are `bound` java-cause terminals, so the
first-fatal moves past the scaler. Lit likelihood: musicplayer medium–high (background `MediaStore$Audio$Artists`
NCDFE doesn't block the main UI), privacybrowser medium (already cleared its U12 WebView wall). Clears cluster C5
(2 keys) and hardens any future null-colorspace scaler.

## Persisted artifacts (`$WORKSPACES/westlake-inputs/generations/u15-framework-bitmap-v1/`)
`framework-u15.jar` (`9e55e286…`), `classes.dex` (`e14cb9ec…`), `Bitmap.getColorSpace.smali.patch`,
`build-commands.txt`, `logs/` (dex2oat baseline+u15 logs, boot-image shas), `SHA256SUMS`. Base `3e106350…`.
Toolchain: baksmali/smali-2.5.2 (+dexlib2-2.5.2, guava-31.1-jre, jcommander-1.78, util-2.5.2).

## Boundaries
Offline build (Mac) + host re-bake (hw248); no board; no push. Not folded into U14 (outer decides U15 deploy).
The on-board (arm64) behavioral pass is the deploy owner's. Sources read read-only: base framework.jar
(`westlake-inputs/generations/.../gate-reference`), AOSP 14 ref, the frozen toolchain + BCP on hw248.

## Files
- `evidence/frozen-gate.txt` — the freeze check (PASS, framework.jar not frozen).
- `evidence/build-gates.txt` — 2-pass determinism, round-trip diff categorization, deployed_class_diff.
- `evidence/hw248-rebake-and-native-boundary.txt` — dex2oat re-bake result + the native-boundary caveat.
- `recipe/Bitmap.getColorSpace.smali.patch` — the one-method smali change.
- `results.json`, `documentation.json`, `landing-paths.txt`.
