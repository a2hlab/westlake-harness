#!/bin/bash
# P13.2.b: compile OH adapter surface framework files (oh_graphic_buffer_producer.cpp,
# oh_surface_bridge.cpp) using OH ARM32 toolchain, then link them into
# libandroid_runtime.so along with android_view_surface_stubs.cpp.
#
# Pre-existing liboh_adapter_bridge.so (Apr 8) does NOT contain these symbols
# because they failed to build via GN. We bypass GN by manually compiling here.
set -e
OH=/home/HanBingChen/oh
ADAPTER=/home/HanBingChen/adapter
SR=$OH/out/rk3568/obj/third_party/musl/usr
ML=$SR/lib/arm-linux-ohos
CXX=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++

OUT_OBJ=$ADAPTER/out/aosp_lib/obj
OUT_LIB=$ADAPTER/out/aosp_lib
mkdir -p $OUT_OBJ

CFLAGS="--target=arm-linux-ohos -march=armv7-a -mfloat-abi=softfp -mthumb \
    --sysroot=$SR -I$SR/include/arm-linux-ohos \
    -fPIC -O2 -std=c++17 -DUSE_M133_SKIA \
    -Wno-unused-parameter -Wno-unused-variable -Wno-deprecated-declarations \
    -include $ADAPTER/framework/appspawn-x/bionic_compat/include/libcxx_compat.h \
    -I$ADAPTER/framework/appspawn-x/bionic_compat/include \
    -I/home/HanBingChen/aosp/system/logging/liblog/include -I$ADAPTER/framework/surface/jni"

OH_INC="-I$OH/foundation/graphic/graphic_surface/interfaces/inner_api/surface \
    -I$OH/foundation/graphic/graphic_surface/interfaces/inner_api/buffer_handle \
    -I$OH/foundation/graphic/graphic_surface/interfaces/inner_api/common \
    -I$OH/foundation/graphic/graphic_surface/interfaces/inner_api/sync_fence \
    -I$OH/out/rk3568/innerkits/ohos-arm/graphic_2d/librender_service_client/include \
    -I$OH/out/rk3568/innerkits/ohos-arm/graphic_2d/librender_service_base/include \
    -I$OH/out/rk3568/innerkits/ohos-arm/graphic_2d/2d_graphics/include \
    -I$OH/foundation/graphic/graphic_2d/rosen/modules/render_service_client/core \
    -I$OH/foundation/graphic/graphic_2d/rosen/modules/render_service_base/include \
    -I$OH/third_party/skia/m133 -I$OH/foundation/graphic/graphic_2d/rosen/modules/2d_graphics/src/drawing/engine_adapter -I$OH/foundation/graphic/graphic_2d/rosen/modules/2d_graphics/src -I$OH/foundation/graphic/graphic_2d/rosen/modules/2d_graphics/include \
    -I$OH/out/rk3568/innerkits/ohos-arm/ipc/ipc_core/include -I$OH/third_party/bounds_checking_function/include -I$OH/base/notification/eventhandler/interfaces/inner_api -I$OH/commonlibrary/c_utils/base/include \
    -I$OH/base/hiviewdfx/hilog/interfaces/native/innerkits/include"

# ---- Step 1: compile oh_graphic_buffer_producer.cpp ----
echo "Compiling oh_graphic_buffer_producer.cpp..."
$CXX $CFLAGS $OH_INC \
    -c $ADAPTER/framework/surface/jni/oh_graphic_buffer_producer.cpp \
    -o $OUT_OBJ/oh_graphic_buffer_producer.o 2>&1 | tail -20
if [ -f $OUT_OBJ/oh_graphic_buffer_producer.o ]; then
    echo "  OK: $(stat -c%s $OUT_OBJ/oh_graphic_buffer_producer.o) bytes"
else
    echo "  FAIL"
    exit 1
fi

# ---- Step 2: compile oh_surface_bridge.cpp ----
echo "Compiling oh_surface_bridge.cpp..."
$CXX $CFLAGS $OH_INC \
    -c $ADAPTER/framework/surface/jni/oh_surface_bridge.cpp \
    -o $OUT_OBJ/oh_surface_bridge.o 2>&1 | tail -20
if [ -f $OUT_OBJ/oh_surface_bridge.o ]; then
    echo "  OK: $(stat -c%s $OUT_OBJ/oh_surface_bridge.o) bytes"
else
    echo "  FAIL"
    exit 1
fi

# ---- Step 3: pixel_format_mapper has no .cpp; oh_canvas_renderer skipped (uses NDK) ----

echo ""
echo "All OH surface framework .o produced."
ls -l $OUT_OBJ/oh_graphic_buffer_producer.o $OUT_OBJ/oh_surface_bridge.o
