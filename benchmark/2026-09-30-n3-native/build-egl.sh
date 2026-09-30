#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../.." && pwd)
BASE=$REPO/bms/src/.work/b68-generation
FROZEN=$BASE/.work/product-tls-generation/frozen
TC=$FROZEN/toolchain
SYS=$FROZEN/sysroot
AOSP=$REPO/bms/src/.work/b6-art14-recovery/aosp-restoration
OUT=$REPO/bms/src/.work/n3-native/gl
export LD_LIBRARY_PATH=$TC/runtime
mkdir -p "$OUT/include"
ln -sfn "$AOSP/frameworks/native/opengl/include/GLES" "$OUT/include/GLES"
FLAGS=(--target=aarch64-linux-ohos --sysroot=$SYS -B$TC/bin -fPIC -O2 -g -ffunction-sections -fdata-sections -D_GNU_SOURCE -D__OHOS__ -DGL_GLEXT_PROTOTYPES -DEGL_EGLEXT_PROTOTYPES -include limits.h -include sys/types.h -I$REPO/benchmark/2026-09-30-n2-native/westlake-gl/compat -I$AOSP/libnativehelper/include -I$AOSP/libnativehelper/include_platform -I$AOSP/libnativehelper/include_jni -I$AOSP/system/logging/liblog/include -I$OUT/include)
"$TC/bin/clang++" "${FLAGS[@]}" -std=c++17 -isystem "$TC/include/c++/v1" -Wno-unused-parameter -Wno-unused-function -c "$HERE/src/oh_egl_impl.cpp" -o "$OUT/EGLImpl.o"
sha256sum "$OUT/EGLImpl.o" > "$HERE/egl-object.txt"
