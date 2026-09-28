#!/bin/bash
# Compile oh_graphic_buffer_producer.cpp standalone using OH headers.
# Outputs oh_graphic_buffer_producer.o into out/surface/.
#
# ============================================================================
# GAP 0.5 status (2026-04-11):
# ============================================================================
# This standalone .o was originally an "orphan" — it built but no .so linked it.
#
# RESOLUTION: framework/jni/BUILD.gn line 85 already lists
#   ../surface/jni/oh_graphic_buffer_producer.cpp
# as a source of the OH GN target `oh_adapter_bridge`. So when liboh_adapter_bridge.so
# is rebuilt (via `cd ~/oh && OH_FULL_BUILD_INVOKED=1 ./build.sh --product-name rk3568 --build-target oh_adapter_bridge`),
# it picks up oh_graphic_buffer_producer.cpp automatically.
#
# This standalone script remains useful for:
#   1. Quick compile-only smoke test (no link step)
#   2. Building the .o for ad-hoc dlopen / unit-test scenarios
#   3. Verifying include paths during refactors
#
# But it is NOT on the canonical build path. The canonical build path is:
#   cd ~/adapter && bash build/oh_full_build.sh   # rebuilds liboh_adapter_bridge.so
#
# If you find liboh_adapter_bridge.so missing producer symbols, the fix is to
# rebuild it via the OH GN target above, NOT to run this script.
# ============================================================================
set -e

OH=/home/HanBingChen/oh
ADAPTER=/home/HanBingChen/adapter
SR=$OH/out/rk3568/obj/third_party/musl/usr
CXX=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++

OUT=$ADAPTER/out/surface
mkdir -p $OUT

# OH inner-API include paths
OH_INC="-I$OH/foundation/graphic/graphic_surface/interfaces/inner_api/surface"
OH_INC="$OH_INC -I$OH/foundation/graphic/graphic_surface/interfaces/inner_api/common"
OH_INC="$OH_INC -I$OH/foundation/graphic/graphic_surface/interfaces/inner_api/buffer_handle"
OH_INC="$OH_INC -I$OH/foundation/graphic/graphic_surface/interfaces/inner_api/sync_fence"
OH_INC="$OH_INC -I$OH/commonlibrary/c_utils/base/include"
OH_INC="$OH_INC -I$OH/base/hiviewdfx/hilog/interfaces/native/innerkits/include"
OH_INC="$OH_INC -I$OH/out/rk3568/innerkits/ohos-arm/ipc/ipc_single/include"
OH_INC="$OH_INC -I$OH/out/rk3568/innerkits/ohos-arm/ipc/ipc_core/include"
OH_INC="$OH_INC -I$OH/foundation/communication/ipc/interfaces/innerkits/ipc_core/include"
OH_INC="$OH_INC -I$OH/foundation/communication/ipc/interfaces/innerkits/ipc_single/include"
# AOSP for android/log.h
OH_INC="$OH_INC -I/home/HanBingChen/aosp/system/logging/liblog/include"
OH_INC="$OH_INC -I$ADAPTER/framework/surface/jni"

DEFS="-D__OHOS__ -D_GNU_SOURCE"

CXXFLAGS="--target=arm-linux-ohos -march=armv7-a -mfloat-abi=softfp -mthumb"
CXXFLAGS="$CXXFLAGS --sysroot=$SR -I$SR/include/arm-linux-ohos"
CXXFLAGS="$CXXFLAGS -fPIC -O2 -std=c++17"
CXXFLAGS="$CXXFLAGS -Wno-unused-parameter -Wno-deprecated-declarations -Wno-error"
CXXFLAGS="$CXXFLAGS -include $ADAPTER/framework/appspawn-x/bionic_compat/include/libcxx_compat.h"
CXXFLAGS="$CXXFLAGS -I$ADAPTER/framework/appspawn-x/bionic_compat/include"

SRC=$ADAPTER/framework/surface/jni/oh_graphic_buffer_producer.cpp

echo "Compiling oh_graphic_buffer_producer.cpp..."
$CXX $CXXFLAGS $DEFS $OH_INC -c $SRC -o $OUT/oh_graphic_buffer_producer.o 2>&1 | tee $OUT/compile.log | tail -40

if [ -f $OUT/oh_graphic_buffer_producer.o ]; then
    echo "OK: $(stat -c%s $OUT/oh_graphic_buffer_producer.o) bytes"
fi
