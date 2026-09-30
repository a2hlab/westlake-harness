#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../.." && pwd)
BASE=$REPO/bms/src/.work/b68-generation
FROZEN=$BASE/.work/product-tls-generation/frozen
TC=$FROZEN/toolchain
SYS=$FROZEN/sysroot
AOSP=$REPO/bms/src/.work/b6-art14-recovery/aosp-restoration
OUT=$REPO/bms/src/.work/n2-native/gl
export LD_LIBRARY_PATH=$TC/runtime
mkdir -p "$OUT/include"
ln -sfn "$AOSP/frameworks/native/opengl/include/GLES" "$OUT/include/GLES"
FLAGS=(--target=aarch64-linux-ohos --sysroot=$SYS -B$TC/bin -fPIC -O2 -g -ffunction-sections -fdata-sections -D_GNU_SOURCE -D__OHOS__ -DGL_GLEXT_PROTOTYPES -DEGL_EGLEXT_PROTOTYPES -include limits.h -include sys/types.h -I$HERE/westlake-gl/compat -I$AOSP/libnativehelper/include -I$AOSP/libnativehelper/include_platform -I$AOSP/libnativehelper/include_jni -I$AOSP/system/logging/liblog/include -I$OUT/include)
"$TC/bin/clang++" "${FLAGS[@]}" -std=c++17 -Wno-unused-parameter -Wno-unused-function -c "$HERE/src/com_google_android_gles_jni_GLImpl.cpp" -o "$OUT/GLImpl.o"
"$TC/bin/llvm-readelf" -W --dyn-syms "$BASE/platform-pool/system/lib64/platformsdk/libGLESv3.so" | awk '$7!="UND"{split($8,a,"@"); print a[1]}' > "$OUT/gles3.exports"
python3 "$HERE/westlake-gl/gen_gl_forwarders.py" "$OUT/gles3.exports" "$OUT/gl_forwarders.c" "$OUT/include/GLES/gl.h" "$OUT/include/GLES/glext.h" "$SYS/usr/include/GLES2/gl2ext.h"
"$TC/bin/clang-15" "${FLAGS[@]}" -c "$OUT/gl_forwarders.c" -o "$OUT/forwarders.o"
"$TC/bin/clang-15" "${FLAGS[@]}" -c "$HERE/westlake-gl/gles1_pointer_bounds.c" -o "$OUT/bounds.o"
sha256sum "$OUT"/*.o "$OUT/gl_forwarders.c" > "$HERE/gl-identities.txt"
