#!/usr/bin/env bash
# Invoke through dockbuild.sh. Diagnostic build; no deployment authority.
set -euo pipefail
ROOT=${B6_REPO_ROOT:?}
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

export AOSP_OUT_DIR=$ROOT/bms/src/.work/b6-task44/providers
export AOSP_OBJ_DIR=$ROOT/bms/src/.work/b6-task44/objects
export AOSP_BUILD_ERROR_LOG=$ROOT/bms/src/.work/b6-task44/build-errors.log
export B6_ABORT_BRIDGE=$ROOT/bms/src/.work/b6-real-work/adapter/framework/appspawn-x/src/art_abort_message_bridge.cpp
bash "$ROOT/bms/src/.work/b6-task44/art-link-inner.sh"
