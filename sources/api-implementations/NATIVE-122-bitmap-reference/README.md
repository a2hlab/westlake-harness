# Bitmap JNI owner source reference

The original row documents an existing null ColorSpace boundary, not a completed sRGB fix. This is the exact AOSP `android-14.0.0_r1` `libs/hwui/jni/Bitmap.cpp` read in that analysis: 48,185 bytes, SHA `7bcb7148d6333f5f89b35f761de8ccecc24a4ec6ae0408a4539f3c4fbec40877`. The local copy was independently compared byte for byte with the official Gitiles tag. Its Apache-2.0 notice is preserved.

`Bitmap_computeColorSpace` at lines 942–949 returns null when the source bitmap has no color space. `Bitmap_isSRGB` at 925–930 accepts null as sRGB. The original report's minimal fallback patch remains an unimplemented proposal and is not applied here.

The related checked-in build driver is `../source-build-native691/westlake/tools/build_hwui_objects.py`, with its pinned `native/hwui-sources.json`. It requires the full preserved HWUI/Skia/toolchain closure, not this one translation unit. This source delivery neither recreates that closure nor proves these bytes produced historical `libhwui.so` be59260f. No fresh build or deployment is asserted.
