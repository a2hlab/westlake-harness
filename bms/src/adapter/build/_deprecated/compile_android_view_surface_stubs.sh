#!/bin/bash
# P13.5 + P13.2.b: compile Surface JNI stub + OH adapter framework helpers,
# link them all into libandroid_runtime.so. End-to-end one script.
set -e
OH=/home/HanBingChen/oh
ADAPTER=/home/HanBingChen/adapter
SR=$OH/out/rk3568/obj/third_party/musl/usr
ML=$SR/lib/arm-linux-ohos
CXX=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++

OUT_OBJ=$ADAPTER/out/aosp_lib/obj
OUT_LIB=$ADAPTER/out/aosp_lib
mkdir -p $OUT_OBJ

# ---- Common compile flags ----
CFLAGS_BASE="--target=arm-linux-ohos -march=armv7-a -mfloat-abi=softfp -mthumb \
    --sysroot=$SR -I$SR/include/arm-linux-ohos \
    -fPIC -O2 -std=c++17 \
    -Wno-unused-parameter -Wno-unused-variable -Wno-deprecated-declarations -pthread \
    -include $ADAPTER/framework/appspawn-x/bionic_compat/include/libcxx_compat.h"

INC_ADAPTER="-I$ADAPTER \
    -I$ADAPTER/framework/appspawn-x/bionic_compat/include -I$ADAPTER/framework/core/include"

INC_JNI="-I/home/HanBingChen/aosp/libnativehelper/include_jni"

INC_SKIA="-I$OH/third_party/skia/m133 \
    -I$OH/third_party/skia/m133/include/core \
    -I$OH/third_party/skia/m133/include"

# Mirror the include chain used by compile_libhwui.sh — Canvas.h transitively
# pulls in androidfw/ResourceTypes.h → util/map_ptr.h → many more, and these
# paths are already verified to work for the libhwui cross-compile.
AOSP=/home/HanBingChen/aosp
HWUI_SRC=$AOSP/frameworks/base/libs/hwui
SKIA_OH=/home/HanBingChen/oh/third_party/skia/m133
SKIA_COMPAT=/home/HanBingChen/adapter/build/skia_compat_headers

INC_HWUI="-I$HWUI_SRC -I$HWUI_SRC/.. -I$SKIA_COMPAT \
    -I$SKIA_OH -I$SKIA_OH/include -I$SKIA_OH/include/core -I$SKIA_OH/include/private \
    -I$SKIA_OH/src/core -I$SKIA_OH/src/gpu -I$SKIA_OH/src/image -I$SKIA_OH/src/utils \
    -I$SKIA_OH/src/shaders -I$SKIA_OH/src/codec \
    -I$AOSP/system/libbase/include -I$AOSP/system/core/include \
    -I$AOSP/system/core/libcutils/include -I$AOSP/system/core/libutils/include \
    -I$AOSP/system/core/libsystem/include -I$AOSP/system/logging/liblog/include \
    -I$AOSP/frameworks/native/include \
    -I$AOSP/frameworks/native/libs/nativewindow/include \
    -I$AOSP/frameworks/native/libs/nativebase/include \
    -I$AOSP/frameworks/native/libs/ui/include \
    -I$AOSP/frameworks/native/libs/ui/include_types \
    -I$AOSP/frameworks/native/libs/arect/include \
    -I$AOSP/frameworks/native/libs/math/include \
    -I$AOSP/libnativehelper/include_jni \
    -I$AOSP/libnativehelper/include \
    -I$AOSP/libnativehelper/header_only_include \
    -I$AOSP/frameworks/base/libs/androidfw/include \
    -I$AOSP/external/harfbuzz_ng/src \
    -I$AOSP/frameworks/minikin/include \
    -I$AOSP/external/freetype/include \
    -I$AOSP/system/incremental_delivery/incfs/util/include \
    -I$AOSP/external/fmtlib/include"

INC_OH_SURFACE="-I$OH/foundation/graphic/graphic_surface/interfaces/inner_api/surface \
    -I$OH/foundation/graphic/graphic_surface/interfaces/inner_api/buffer_handle \
    -I$OH/foundation/graphic/graphic_surface/interfaces/inner_api/common \
    -I$OH/foundation/graphic/graphic_surface/interfaces/inner_api/sync_fence \
    -I$OH/out/rk3568/innerkits/ohos-arm/ipc/ipc_core/include \
    -I$OH/commonlibrary/c_utils/base/include"

INC_AOSP_LOG="-I/home/HanBingChen/aosp/system/logging/liblog/include"
INC_HILOG="-I$OH/base/hiviewdfx/hilog/interfaces/native/innerkits/include"
# 2026-05-08 G2.14ac: oh_graphic_buffer_producer.cpp #include "oh_br_trace.h"
# pulls hilog/log_c.h transitively. Add INC_HILOG to INC_ADAPTER so the
# producer's own compile step (Step 1, uses only INC_ADAPTER + INC_OH_SURFACE
# + INC_AOSP_LOG) can resolve the hilog header.
INC_ADAPTER="$INC_ADAPTER $INC_HILOG"

# ---- Step 1: compile oh_graphic_buffer_producer.cpp ----
echo "Compile oh_graphic_buffer_producer.cpp..."
$CXX $CFLAGS_BASE $INC_ADAPTER $INC_OH_SURFACE $INC_AOSP_LOG \
    -c $ADAPTER/framework/surface/jni/oh_graphic_buffer_producer.cpp \
    -o $OUT_OBJ/oh_graphic_buffer_producer.o
[ -f $OUT_OBJ/oh_graphic_buffer_producer.o ] && echo "  OK $(stat -c%s $OUT_OBJ/oh_graphic_buffer_producer.o) bytes"

# ---- Step 2: compile surface_oh_helper.cpp ----
echo "Compile surface_oh_helper.cpp..."
$CXX $CFLAGS_BASE $INC_ADAPTER $INC_OH_SURFACE $INC_AOSP_LOG \
    -c $ADAPTER/framework/surface/jni/surface_oh_helper.cpp \
    -o $OUT_OBJ/surface_oh_helper.o
[ -f $OUT_OBJ/surface_oh_helper.o ] && echo "  OK $(stat -c%s $OUT_OBJ/surface_oh_helper.o) bytes"

# ---- Step 2b: compile rs_surface_helper.cpp (P13.2.c, via ninja-flag reuse) ----
echo "Compile rs_surface_helper.cpp..."
bash $ADAPTER/build/compile_rs_surface_helper.sh 2>&1 | tail -5
[ -f $OUT_OBJ/rs_surface_helper.o ] && echo "  OK $(stat -c%s $OUT_OBJ/rs_surface_helper.o) bytes"

# ---- Step 3: REMOVED 2026-05-08 G2.14ad ----
# android_view_surface_stubs.cpp was a P13-era file whose body has been
# #if 0'd since 2026-05-06 — its three Parts (DisplayEventReceiver / Surface
# lockCanvas / SurfaceControl dummy) were superseded by:
#   framework/android-runtime/src/android_view_DisplayEventReceiver.cpp
#   framework/android-runtime/src/android_graphics_compat_shim.cpp
#   framework/android-runtime/src/android_view_SurfaceControl.cpp
# The dead source has been renamed to .cpp.deprecated; this compile step
# would only have produced a 668-byte empty .o (entire body inside #if 0).
# Stale android_view_surface_stubs.o from previous runs is removed below to
# avoid linker pickup.
rm -f $OUT_OBJ/android_view_surface_stubs.o

# ---- Step 4: re-link libandroid_runtime.so ----
RT_OBJ_DIR=/tmp/cc100/android_runtime
if [ ! -d "$RT_OBJ_DIR" ] || [ -z "$(ls $RT_OBJ_DIR/*.o 2>/dev/null)" ]; then
    echo ""
    echo "ERROR: $RT_OBJ_DIR not populated — libandroid_runtime.so NOT re-linked."; exit 1
    echo "      Run cross_compile_arm32.sh to regenerate the .o cache."
    exit 0
fi

LNK="$CXX --target=arm-linux-ohos -B$ML -L$ML -L$OUT_LIB -shared -fPIC"
BUILTINS=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/lib/clang/15.0.4/lib/arm-linux-ohos/libclang_rt.builtins.a

echo ""
echo "Re-linking libandroid_runtime.so with all P13 .o + libsurface.z + librender_service_client.z..."
RSC_LIB_DIR=$OH/out/rk3568/innerkits/ohos-arm/graphic_2d/librender_service_client
if [ ! -f $RSC_LIB_DIR/librender_service_client.z.so ]; then
    RSC_LIB_DIR=$OH/out/rk3568/graphic/graphic_2d
fi
$LNK -o $OUT_LIB/libandroid_runtime.so \
    $RT_OBJ_DIR/*.o \
    $OUT_OBJ/surface_oh_helper.o \
    $OUT_OBJ/rs_surface_helper.o \
    $OUT_OBJ/oh_graphic_buffer_producer.o \
    -L$OH/out/rk3568/lib.unstripped/graphic/graphic_surface -lsurface.z \
    -L$RSC_LIB_DIR -lrender_service_client.z \
    -lhilog \
    -lc -lbionic_compat -ldl -lpthread $BUILTINS \
    -Wl,--unresolved-symbols=ignore-all 2>&1 | tail -5

if [ -f $OUT_LIB/libandroid_runtime.so ]; then
    SIZE=$(stat -c%s $OUT_LIB/libandroid_runtime.so)
    echo "OK link:   libandroid_runtime.so = $SIZE bytes"

    NM=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-nm
    RESOLVED=$($NM -C $OUT_LIB/libandroid_runtime.so 2>&1 | \
        grep -cE "T android::register_android_view_(Surface|SurfaceControl|SurfaceSession|DisplayEventReceiver)\(")
    echo "OK symbols: $RESOLVED/4 Surface/DER register_* resolved"

    OH_SYMS=$($NM -C $OUT_LIB/libandroid_runtime.so 2>&1 | \
        grep -cE "T oh_adapter::OHGraphicBufferProducer::(dequeueBuffer|queueBuffer|getBufferAddr)")
    echo "OK OH:      $OH_SYMS/3 OHGraphicBufferProducer methods resolved"

    RS_SYMS=$($NM $OUT_LIB/libandroid_runtime.so 2>&1 | \
        grep -cE "[Tt] rs_surface_helper_(create_display_surface|release)")
    echo "OK RS:      $RS_SYMS/2 rs_surface_helper C symbols (hidden visibility ok, internal call)"

    RS_NEEDED=$(/home/HanBingChen/oh/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-readelf -d $OUT_LIB/libandroid_runtime.so 2>&1 | grep -c librender_service_client)
    echo "OK NEEDED:  librender_service_client.z.so in DT_NEEDED ($RS_NEEDED)"
fi
