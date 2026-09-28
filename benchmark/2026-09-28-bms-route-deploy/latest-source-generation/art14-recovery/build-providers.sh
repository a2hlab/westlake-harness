#!/usr/bin/env bash
# Invoke through dockbuild.sh. Diagnostic build; no deployment authority.
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)
WORK=$ROOT/bms/src/.work/b6-art14-recovery
TC=$ROOT/bms/src/.work/product-tls-generation/frozen/toolchain
export BUILD_INNER_INVOKED=1
export ADAPTER_ROOT=$ROOT/bms/src/adapter
export OH_ROOT=$WORK/oh AOSP_ROOT=$WORK/aosp-restoration
export AOSP_OUT_DIR=$WORK/build/providers AOSP_OBJ_DIR=$WORK/build/objects
export AOSP_BUILD_ERROR_LOG=$WORK/build/errors.log
export L03_A12_GENERATION_ID=b6-art14-recovery
export L03_A12_STRICT_BUILD=1
export L03_A12_CC=$TC/bin/clang-15 L03_A12_CXX=$TC/bin/clang++ L03_A12_AS=$TC/bin/clang-15
export L03_A12_READELF=$TC/bin/llvm-readelf L03_A12_NM=$TC/bin/llvm-nm
export L03_A12_BUILTINS=$TC/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a
export L03_A12_LIBCXX_INCLUDE=$TC/include/c++/v1
export L03_A12_LIBART_ZERO_ARRAY_HEADER_COHORT=$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/include/libcxx_array_aosp
export L03_A12_PYTHON=/usr/bin/python3 BUILD_NJOBS=12
export LD_LIBRARY_PATH=$TC/runtime
mkdir -p "$WORK/build"
# Same SDK-15 compatibility switch already used by the TGR/native builds.
cat > "$WORK/build/sdk15-declarations.h" <<'EOF'
// The SDK libc exports these objects but its headers omit their declaration.
// Declaration only: no replacement implementation or provider.
#ifdef __cplusplus
extern "C" {
#endif
extern char *program_invocation_name;
extern char *program_invocation_short_name;
#ifdef __cplusplus
}
#endif
#include <stddef.h>
// Linux UAPI asm-generic/siginfo.h: asynchronous ARM MTE tag check fault.
#ifndef SEGV_MTEAERR
#define SEGV_MTEAERR 8
#endif
EOF
# Reuse the existing recipe's C++17 span block. SDK 15 supplies math overloads
# but does not provide span in C++17; those capabilities are independent.
python3 - "$ADAPTER_ROOT" "$WORK" <<'PY'
import sys
from pathlib import Path
p = Path(sys.argv[1]) / 'framework/appspawn-x/bionic_compat/include/libcxx_compat.h'
s = p.read_text().split('// Minimal std::span polyfill for C++17', 1)[1]
s = '// Minimal std::span polyfill for C++17' + s
assert s.count(' && !WESTLAKE_LIBCXX_HAS_NATIVE_COMPAT') == 1
s = s.replace(' && !WESTLAKE_LIBCXX_HAS_NATIVE_COMPAT', '')
with (Path(sys.argv[2]) / 'build/sdk15-declarations.h').open('a') as f:
    f.write(s)
PY
printf '#!/usr/bin/env bash\nexec "%s/bin/clang++" -DWESTLAKE_LIBCXX_HAS_NATIVE_COMPAT=1 -DHAVE_SIGCHAIN -include "%s/build/sdk15-declarations.h" -I"%s/art/sigchainlib" -I"%s/art/tools/cpp-define-generator" "$@"\n' "$TC" "$WORK" "$AOSP_ROOT" "$AOSP_ROOT" > "$WORK/build/cxx-sdk15"
chmod +x "$WORK/build/cxx-sdk15"
export L03_A12_CXX=$WORK/build/cxx-sdk15
export ANL_OUT_DIR=$AOSP_OUT_DIR ANL_FIXTURE_OUT_DIR=$WORK/build/anl-fixtures
export OH_CC=$TC/bin/clang-15 OH_READELF=$TC/bin/llvm-readelf
export OH_SYSROOT=$ROOT/bms/src/.work/product-tls-generation/frozen/sysroot
export OH_DLNS_PROVIDER=$ADAPTER_ROOT/framework/appspawn-x/security_specialization/stock_child_plugin/frozen/target_external/openharmony-6.1.0.31-d600/libc.so
export OH_DLNS_PROVIDER_SHA256=fd3c4701acf719738fbd14cf1d419e4dd222c06a6df41f53d973354d648af7e2
# Product invocation from compile_app_native_loader_arm64.sh lines 86–107.
# Its later fixture build references a tests/target file absent in this snapshot.
test "$(sha256sum "$OH_DLNS_PROVIDER" | awk '{print $1}')" = "$OH_DLNS_PROVIDER_SHA256"
mkdir -p "$AOSP_OUT_DIR"
ANL_SRC=$ADAPTER_ROOT/framework/app-native-loader
"$OH_CC" --target=aarch64-linux-ohos --sysroot="$OH_SYSROOT" \
    -D_GNU_SOURCE -std=c11 -fPIC -fvisibility=hidden -Wall -Wextra -Werror \
    -I"$ANL_SRC/include" \
    -I"$ADAPTER_ROOT/framework/native-compat/bionic-pthread-bridge/include" \
    -shared -Wl,-soname,libapp_native_loader.so -Wl,--build-id=sha1 -Wl,-z,defs \
    -Wl,--version-script,"$ANL_SRC/app_native_loader.map" \
    "$ANL_SRC/src/app_native_loader.c" \
    -L"$(dirname "$OH_DLNS_PROVIDER")" -l:"$(basename "$OH_DLNS_PROVIDER")" \
    -o "$AOSP_OUT_DIR/libapp_native_loader.so"
bash "$ADAPTER_ROOT/build/inner/cross_compile_arm64.sh"
