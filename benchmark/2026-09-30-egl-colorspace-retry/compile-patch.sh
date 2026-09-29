#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
ADAPTER=$ROOT/bms/src/adapter
FROZEN=$ROOT/bms/src/.work/product-tls-generation/frozen
OUT=$ROOT/bms/src/.work/b11-egl-retry
export LD_LIBRARY_PATH=$FROZEN/toolchain/runtime
"$FROZEN/toolchain/bin/clang++" --target=aarch64-linux-ohos \
  --sysroot="$FROZEN/sysroot" -isystem "$FROZEN/sysroot/include/aarch64-linux-ohos" \
  -nostdinc++ -isystem "$FROZEN/toolchain/include/c++/v1" \
  -fPIC -O2 -std=c++17 -DWESTLAKE_LIBCXX_HAS_NATIVE_COMPAT=1 \
  -Wno-unused-parameter -Wno-unused-private-field \
  -I"$ADAPTER/framework/appspawn-x/bionic_compat/include" \
  -I"$ROOT/bms/src/.work/b6-art14-recovery/aosp-restoration/libnativehelper/include_jni" \
  -include "$ADAPTER/framework/appspawn-x/bionic_compat/include/libcxx_compat.h" \
  -c "$ADAPTER/aosp_patches/libs/hwui/hwui_oh_abi_patch.cpp" \
  -o "$OUT/hwui_oh_abi_patch.o"
sha256sum "$OUT/hwui_oh_abi_patch.o"
