#!/bin/bash
# link_libandroid_runtime_full.sh — Gap 2 linker.
#
# Links ALL cross-compiled core/jni .o files + hand-written stubs into a
# full libandroid_runtime.so with correct DT_NEEDED entries. Should produce
# a ~2 MB .so with 70+ T register_*, properly resolved against libhwui.so /
# libutils / libcutils / liblog / libnativehelper / libandroidfw / libminikin /
# libart / libbase / libziparchive / libsurface.z / librender_service_client.z.
set -e

OH=/home/HanBingChen/oh
A=/home/HanBingChen/aosp
ADAPTER=/home/HanBingChen/adapter
SR=$OH/out/rk3568/obj/third_party/musl/usr
ML=$SR/lib/arm-linux-ohos
CXX=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++
NM=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-nm
READELF=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-readelf
BUILTINS=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/lib/clang/15.0.4/lib/arm-linux-ohos/libclang_rt.builtins.a

OUT=$ADAPTER/out/aosp_lib
HWUI_DIR=$ADAPTER/out/aosp_lib

RT_OBJS=$(ls /tmp/cc100/android_runtime/*.o | tr "\n" " ")
# 2026-05-08 G2.14ad: STUB_O removed. android_view_surface_stubs.cpp was
# deactivated 2026-05-06 (#if 0 entire body, see file header) and renamed
# to .cpp.deprecated. Its three Parts are now in framework/android-runtime/
# src/{android_view_DisplayEventReceiver,android_graphics_compat_shim,
# android_view_SurfaceControl}.cpp.
OH_BUF_O=$OUT/obj/oh_graphic_buffer_producer.o
SURF_HELPER_O=$OUT/obj/surface_oh_helper.o
RS_HELPER_O=$OUT/obj/rs_surface_helper.o

echo "Cross-compiled core/jni .o count: $(ls /tmp/cc100/android_runtime/*.o | wc -l)"
echo "Linking..."

$CXX --target=arm-linux-ohos -B$ML -L$ML -L$OUT -L$HWUI_DIR \
    -shared -fPIC -Wl,-soname,libandroid_runtime.so \
    -o $OUT/libandroid_runtime.so \
    $RT_OBJS $SURF_HELPER_O $RS_HELPER_O $OH_BUF_O \
    -lhwui \
    -lutils -lcutils -llog -lnativehelper -landroidfw \
    -lminikin -lart -lbase -lziparchive \
    -L$OH/out/rk3568/innerkits/ohos-arm/graphic_surface/surface -lsurface.z \
    -L$OH/out/rk3568/innerkits/ohos-arm/graphic_2d/librender_service_client -lrender_service_client.z \
    -lc -lbionic_compat -ldl -lpthread $BUILTINS \
    -Wl,--unresolved-symbols=ignore-all 2>&1 | tail -8

if [ ! -f $OUT/libandroid_runtime.so ]; then
    echo "FAIL: libandroid_runtime.so not produced"
    exit 1
fi

SIZE=$(stat -c%s $OUT/libandroid_runtime.so)
echo ""
echo "=== libandroid_runtime.so ==="
echo "size: $SIZE bytes"
echo ""
echo "--- DT_NEEDED ---"
$READELF -d $OUT/libandroid_runtime.so 2>&1 | grep NEEDED
echo ""
echo "--- register_* statistics ---"
T_REG=$($NM -C $OUT/libandroid_runtime.so | grep -cE "T (android::)?register_android_|T register_android_")
U_REG=$($NM -C $OUT/libandroid_runtime.so | grep -cE "U (android::)?register_android_|U register_android_")
echo "  T register_*: $T_REG"
echo "  U register_*: $U_REG"

echo ""
echo "--- U register_* details (runtime-resolved via DT_NEEDED) ---"
$NM -C $OUT/libandroid_runtime.so | grep -E "U (android::)?register_" | head -5
echo ""
echo "--- Total U dynamic symbols (runtime-resolved or dangling) ---"
$NM -D --undefined-only $OUT/libandroid_runtime.so | wc -l
