# Fix (proposal) — fd-musicplayer: ImageDecoder.nGetColorSpace returns SRGB instead of null

Verdict: **ALIVE**. Layer: **runtime** (android_graphics_compat_shim.cpp -> one .o in liboh_android_runtime.so).
Owner to assemble: cc-t3 (final U13 runtime 18763dd4 lineage); cc-wiki can write the .o change.

## Root
`ID_nGetColorSpace` (android_graphics_compat_shim.cpp:79, registered as `android.graphics.ImageDecoder.nGetColorSpace`)
deliberately returns `nullptr` (G2.4 workaround for a ColorSpace-class fid==null abort). A bitmap decoded via
ImageDecoder then has `mColorSpace = null`; `createScaledBitmap(src) -> createBitmap(src,...) -> source.getColorSpace()`
is null -> `Bitmap.java:1203` throws `IllegalArgumentException: can't create bitmap without a color space`. The G2.4
note's assumption ("sRGB is assumed when null; no path strict-requires non-null") is refuted by this key.

## Minimal change (one .o, runtime)
Make `ID_nGetColorSpace` return the sRGB `ColorSpace` instead of null -- call Java
`ColorSpace.get(ColorSpace.Named.SRGB)` via JNI and return the result (fall back to null only if that call itself
fails). ColorSpace now registers before ImageDecoder/Bitmap (AndroidRuntime.cpp:306), so the original fid==null risk
that motivated the null stub should no longer apply.
```c
jobject ID_nGetColorSpace(JNIEnv* env, jclass, jlong /*nativePtr*/) {
    // Return sRGB (the AOSP default) instead of null: Bitmap.createBitmap(source,...) strict-requires a non-null
    // color space (fd-musicplayer: createScaledBitmap -> IllegalArgumentException "can't create bitmap without a
    // color space"). ColorSpace registers before ImageDecoder (AndroidRuntime.cpp:306), so get(Named.SRGB) is safe.
    jclass cs = env->FindClass("android/graphics/ColorSpace");
    jclass named = env->FindClass("android/graphics/ColorSpace$Named");
    if (cs == nullptr || named == nullptr) { if (env->ExceptionCheck()) env->ExceptionClear(); return nullptr; }
    jfieldID srgbField = env->GetStaticFieldID(named, "SRGB", "Landroid/graphics/ColorSpace$Named;");
    jmethodID get = env->GetStaticMethodID(cs, "get",
        "(Landroid/graphics/ColorSpace$Named;)Landroid/graphics/ColorSpace;");
    if (srgbField == nullptr || get == nullptr) { if (env->ExceptionCheck()) env->ExceptionClear(); return nullptr; }
    jobject srgbNamed = env->GetStaticObjectField(named, srgbField);
    jobject result = env->CallStaticObjectMethod(cs, get, srgbNamed);
    if (env->ExceptionCheck()) { env->ExceptionClear(); return nullptr; }
    return result;
}
```
(Keep the null fallback so a regression cannot re-introduce the original abort.)

## Prediction (move + evidence)
- **First fatal MOVES** for fd-musicplayer: the source bitmap gets a non-null sRGB color space, so
  `createScaledBitmap` no longer throws at `Bitmap.java:1203`. Next fatal / t20 unknown.
- **Real count: 1 confirmed (fd-musicplayer).** The fix is general (any key that scales/copies an ImageDecoder-decoded
  bitmap whose color space was nulled benefits), but no other key is enumerated here, so the asserted move is 1.

## Confirmation gaps (see evidence)
1. Confirm the decode path is ImageDecoder (nGetColorSpace on the path) vs BitmapFactory (null would originate in the
   blocked libhwui decode instead). If BitmapFactory, this .o does not fix it and the fix moves into libhwui (DIGEST 610).
2. Confirm returning sRGB no longer trips the ColorSpace-class fid==null abort the G2.4 null-stub guarded against.
