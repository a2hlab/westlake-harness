#!/usr/bin/env bash
set -euo pipefail
R=/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy
S=$R/bms/src/adapter/framework/native-compat/westlake-bionic
W=$R/bms/src/.work/b87-native
SDK=/home/dspfac/a2hlab/source-closure/verify/toolchains/ohos-sdk/native
OLD=$R/bms/src/.work/b6-art14-recovery/build/objects/log
P=/Users/zhaoyue/orca/workspaces/westlake-generation-v3a-74d1d6d4-r8b/payload
export LD_LIBRARY_PATH=$SDK/llvm/lib
mkdir -p "$W/log-bionic"
for n in bionic_assert_compat bionic_stdio_compat; do
 "$SDK/llvm/bin/clang-15" --target=aarch64-linux-ohos --sysroot="$SDK/sysroot" -D_GNU_SOURCE -fPIC -O2 -Wall -Wextra -c "$S/$n.c" -o "$W/log-bionic/$n.o"
done
A=$R/bms/src/.work/b6-art14-recovery/aosp-restoration
TC=$R/bms/src/.work/product-tls-generation/frozen/toolchain
BC=$R/bms/src/.work/b67-generation/adapter/framework/appspawn-x/bionic_compat/include
cp "$OLD"/*.o "$W/log-bionic/"
"$SDK/llvm/bin/clang++" --target=aarch64-linux-ohos --sysroot="$SDK/sysroot" -std=gnu++20 -DWESTLAKE_LIBCXX_HAS_NATIVE_COMPAT=1 -nostdinc++ -I"$TC/include/c++/v1" -I"$BC" -include "$BC/libcxx_compat.h" -include "$R/benchmark/2026-09-29-native-abi-port/ohos_port.h" -I"$A/system/logging/liblog/include" -I"$A/system/libbase/include" -I"$A/system/core/libcutils/include" -I"$A/system/core/include" -DLIBLOG_LOG_TAG=1006 -DSNET_EVENT_LOG_TAG=1397638484 -D_GNU_SOURCE -fPIC -O2 -c "$A/system/logging/liblog/logger_write.cpp" -o "$W/log-bionic/logger_write.o"
"$SDK/llvm/bin/clang-15" --target=aarch64-linux-ohos --sysroot="$SDK/sysroot" -shared -fuse-ld=lld -Wl,-z,defs -Wl,--no-undefined -Wl,--build-id=sha1 -Wl,-soname,liblog.so -Wl,--version-script="$R/benchmark/2026-09-29-native-abi-port/liblog-bionic.map" -Wl,--undefined-version "$W/log-bionic"/*.o "$W/link/libbionic_compat.so" "$W/link/libc++.so" "$W/link/libhilog.so" -o "$W/log-bionic/liblog.so"
"$SDK/llvm/bin/llvm-readelf" --dyn-syms --version-info "$W/log-bionic/liblog.so" > "$R/benchmark/2026-09-29-native-abi-port/log-bionic-symbols.txt"
sha256sum "$W/log-bionic/liblog.so" "$W/runtime-out/liboh_android_runtime.so"
