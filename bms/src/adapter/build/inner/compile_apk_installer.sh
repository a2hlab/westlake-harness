#!/bin/bash
# === GUARD: internal helper, do not invoke directly ===
if [ "${BUILD_INNER_INVOKED}" != "1" ]; then
    echo "[GUARD] $(basename "$0") is an internal helper — invoke via build_*.sh / restore_after_sync.sh / etc." >&2
    echo "[GUARD] Escape hatch (debug only): BUILD_INNER_INVOKED=1 bash $(basename "$0")" >&2
    exit 2
fi
# === END GUARD ===
# [ARM64 2026-07-12] Retargeted arm-linux-ohos(rk3568)->aarch64-linux-ohos(wukong100)
# per L02.package-inspect/handoff/ARM64_PRODUCER_REBUILD_PLAN.md. Strict link
# (no --unresolved-symbols=ignore-all) — see plan §"验收判据" item 2.
# [DEPRECATED Phase 1 — 2026-05-21] Use build_adapter.sh --target=libapk_installer.so instead.
echo "[DEPRECATED] $(basename "$0") is wrapped by build_adapter.sh — Phase 4 will absorb this" >&2
# Standalone compilation of apk_installer for ARM64
# Uses OH clang + OH system libraries directly (bypasses GN/ninja)
set -o pipefail

OH="${OH_ROOT:-$HOME/oh}"
ADAPTER="${ADAPTER_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
O="$ADAPTER/out/adapter"

CXX=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++

if [ -d "$OH/out/wukong100" ]; then OH_OUT="$OH/out/wukong100"
else echo "ERROR: OH output dir not found (expected \$OH_ROOT/out/wukong100, arm64 product)"; exit 1; fi

SR=$OH_OUT/obj/third_party/musl/usr
ML=$SR/lib/aarch64-linux-ohos
# arm64 product packages under system/lib64 (not system/lib, which is the
# arm32/rk3568 layout) — confirmed against gz02's wukong100 output tree.
SYS_LIB=$OH_OUT/packages/phone/system/lib64
SYS_LIB_SDK=$SYS_LIB/platformsdk

mkdir -p $O

echo "=========================================="
echo "  apk_installer compilation (ARM64)"
echo "=========================================="

# Include paths
A="${AOSP_ROOT:-$HOME/aosp}"
INC="-I$ADAPTER/framework/package-manager/jni \
-I$ADAPTER/third_party/lodepng \
-I$ADAPTER/framework/package-manager/install_plan/include \
-I$ADAPTER/framework/package-manager/package_transaction/include \
-I$ADAPTER/framework/package-manager/signing_metadata/include \
-I$ADAPTER/framework/package-manager/package_query/include \
-I$ADAPTER/framework/package-manager/package_authority/include \
-I$OH/foundation/bundlemanager/bundle_framework/interfaces/inner_api/appexecfwk_base/include \
-I$OH/foundation/bundlemanager/bundle_framework/services/bundlemgr/include \
-I$OH/foundation/bundlemanager/bundle_framework/services/bundlemgr/include/installd \
-I$OH/foundation/bundlemanager/bundle_framework/interfaces/inner_api/appexecfwk_core/include"

# Dynamically add all BMS subdirectory includes
# Recursively add ALL BMS include directories + common log/utils
BMS_INC=$(find $OH/foundation/bundlemanager/bundle_framework -type d -name 'include' 2>/dev/null | grep -v test | sed 's/^/-I/' | tr '\n' ' ')
# Also add BMS subdirs (quick_fix, aot, etc. that contain headers without 'include' dir)
BMS_INC="$BMS_INC $(find $OH/foundation/bundlemanager/bundle_framework/services/bundlemgr/include -mindepth 1 -type d 2>/dev/null | grep -v test | sed 's/^/-I/' | tr '\n' ' ')"
BMS_INC="$BMS_INC $(find $OH/foundation/bundlemanager/bundle_framework/interfaces/inner_api/appexecfwk_base/include -mindepth 1 -type d 2>/dev/null | sed 's/^/-I/' | tr '\n' ' ')"
# minizip dirs MUST come BEFORE BMS_INC so our `#include <zip.h>` picks
# minizip's zip.h, not OH's bundle_framework/.../zip/include/zip.h (which
# transitively pulls event_handler.h not available cross-arch).
INC="-I$OH/third_party/zlib/contrib/minizip -I$OH/third_party/zlib $INC $BMS_INC
-I$OH/third_party/openssl/include \
-I$OH_OUT/obj/third_party/openssl/build_all_generated/include \
-I$OH/base/hiviewdfx/hilog/interfaces/native/innerkits/include \
-I$OH/commonlibrary/c_utils/base/include \
-I$OH/foundation/communication/ipc/interfaces/innerkits/ipc_core/include \
-I$OH/foundation/ability/ability_base/interfaces/kits/native/want/include \
-I$OH/foundation/ability/ability_base/interfaces/kits/native/uri/include \
-I$OH/foundation/ability/ability_base/interfaces/inner_api/base/include \
-I$OH/foundation/ability/ability_base/interfaces/inner_api/uri/include \
-I$OH_OUT/innerkits/ohos-arm/ability_base/want/include \
-I$A/frameworks/base/libs/androidfw/include \
-I$A/system/core/include \
-I$A/system/core/libutils/include \
-I$A/system/logging/liblog/include \
-I$A/system/libbase/include \
-I$A/system/incremental_delivery/incfs/util/include \
-I$A/system/core/libutils/include \
-I$OH/foundation/bundlemanager/bundle_framework/interfaces/inner_api/appexecfwk_core/include/bundlemgr \
-I$OH/utils/native/base/include \
-I$OH/commonlibrary/c_utils/base/include \
-I$OH/foundation/communication/ipc/interfaces/innerkits/ipc_core/include \
-I$A/external/fmtlib/include \
-I$A/frameworks/native/include \
-I$OH/third_party/json/include \
-I$OH/third_party/json/single_include \
-I$OH/base/security/access_token/interfaces/innerkits/accesstoken/include \
-I$OH/base/security/access_token/interfaces/innerkits/token_setproc/include"

BC=$ADAPTER/framework/appspawn-x/bionic_compat/include
CFLAGS="--target=aarch64-linux-ohos --sysroot=$SR -I$SR/include/aarch64-linux-ohos \
-fPIC -O2 -std=c++17 -D__OHOS__ \
-include $BC/libcxx_compat.h -I$BC \
-include sys/types.h \
-Wno-unused-parameter -Wno-missing-field-initializers -Wno-error -Wno-macro-redefined -Wno-c++11-narrowing"

# libclang_rt.builtins.a; OH ships it under prebuilts/clang.
BUILTINS="$OH/prebuilts/clang/ohos/linux-x86_64/llvm/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a"

# Current-generation source list (2026-08-04): mirrors the apk_installer
# target in framework/package-manager/BUILD.gn plus its static-library deps
# (fn01_package_authority -> fn01_package_query -> fn01_package_transaction)
# and app_data_dir_provisioner (post-registration app data dir fix).
SRCS="$ADAPTER/framework/package-manager/jni/apk_manifest_parser.cpp \
$ADAPTER/framework/package-manager/jni/apk_native_inventory.cpp \
$ADAPTER/framework/package-manager/jni/apk_native_inventory_names.cpp \
$ADAPTER/framework/package-manager/jni/apk_verify_result.cpp \
$ADAPTER/framework/package-manager/jni/apk_verifier_client.cpp \
$ADAPTER/framework/package-manager/jni/axml_parser.cpp \
$ADAPTER/framework/package-manager/jni/apk_installer.cpp \
$ADAPTER/framework/package-manager/jni/icon_normalize.cpp \
$ADAPTER/third_party/lodepng/lodepng.cpp \
$ADAPTER/framework/package-manager/jni/arsc_resolver.cpp \
$ADAPTER/framework/package-manager/jni/permission_mapper.cpp \
$ADAPTER/framework/package-manager/jni/apk_signature_verifier.cpp \
$ADAPTER/framework/package-manager/signing_metadata/src/signing_metadata_v1.cpp \
$ADAPTER/framework/package-manager/package_authority/src/package_authority_service_v1.cpp \
$ADAPTER/framework/package-manager/package_query/src/package_query_v1.cpp \
$ADAPTER/framework/package-manager/package_transaction/src/elf_prepass_analyzer.cpp \
$ADAPTER/framework/package-manager/package_transaction/src/prepass_bundle.cpp \
$ADAPTER/framework/package-manager/package_transaction/src/package_transaction.cpp \
$ADAPTER/framework/package-manager/jni/game_install_plan_wire.cpp \
$ADAPTER/framework/package-manager/jni/install_prepass_materializer.cpp \
$ADAPTER/framework/package-manager/jni/prepass_context_wire.cpp \
$ADAPTER/framework/package-manager/jni/app_data_dir_provisioner.cpp \
$ADAPTER/framework/package-manager/jni/oh_adapter_install_apk_c_entry.cpp"

# OH device libz.so / libshared_libz.z.so do NOT export minizip unz*/zip* APIs.
# libapk_installer.so calls:
#   unzOpen/unzGoToFirstFile/unzReadCurrentFile  (read APK + read template)
#   zipOpen/zipOpenNewFileInZip/zipWriteInFileInZip/zipClose  (write resources HAP)
# Compile minizip's unzip.c + zip.c + ioapi.c into libapk_installer.so directly.
MINIZIP_C="$OH/third_party/zlib/contrib/minizip/unzip.c \
$OH/third_party/zlib/contrib/minizip/zip.c \
$OH/third_party/zlib/contrib/minizip/ioapi.c \
$ADAPTER/framework/package-manager/install_plan/src/sha256.c"

# Compile
# Overridable: the hardcoded /tmp path collides between builders sharing a
# machine (sticky-bit /tmp means a previous owner's dir cannot be removed).
TMP="${APK_INSTALLER_BUILD_TMP:-/tmp/apk_installer_build}"
rm -rf $TMP && mkdir -p $TMP
ok=0; fl=0
for src in $SRCS; do
    name=$(basename $src .cpp)
    echo -n "  Compiling $name... "
    if $CXX $CFLAGS $INC -c -o $TMP/$name.o $src 2>$TMP/$name.err; then
        echo "OK"
        ok=$((ok+1))
    else
        echo "FAIL"
        head -5 $TMP/$name.err | sed 's/^/    /'
        fl=$((fl+1))
    fi
done

# Compile minizip C sources (unzip.c, ioapi.c) — symbols not in OH device libz.
CC=$(echo $CXX | sed 's/clang++/clang/')
CFLAGS_C="--target=aarch64-linux-ohos --sysroot=$SR -I$SR/include/aarch64-linux-ohos \
-fPIC -O2 -D__OHOS__ -DUSE_FILE32API \
-I$OH/third_party/zlib -I$OH/third_party/zlib/contrib/minizip \
-I$ADAPTER/framework/package-manager/install_plan/include \
-Wno-implicit-function-declaration -Wno-error"
for src in $MINIZIP_C; do
    name=$(basename $src .c)
    echo -n "  Compiling $name (C, minizip)... "
    if $CC $CFLAGS_C -c -o $TMP/${name}_minizip.o $src 2>$TMP/${name}_minizip.err; then
        echo "OK"
        ok=$((ok+1))
    else
        echo "FAIL"
        head -5 $TMP/${name}_minizip.err | sed 's/^/    /'
        fl=$((fl+1))
    fi
done

echo ""
echo "  Compiled: $ok/$(( ok + fl ))"

if [ $ok -eq 0 ]; then
    echo "  ❌ No objects, skipping link"
    exit 1
fi

# Link as shared library
echo -n "  Linking libapk_installer.so... "
OBJ=$(ls $TMP/*.o 2>/dev/null | tr '\n' ' ')
# Note: -L is searched in order. chipset-sdk-sp has libutils.z.so + libshared_libz.z.so.
SDK_SP="$OH_OUT/packages/phone/system/lib/chipset-sdk-sp"
# All NEEDED resolve in OH systemscence default lib paths:
#   libc/libc++/libdl from /system/lib (musl/clang ohos runtime)
#   libutils.z.so from /system/lib/chipset-sdk-sp
#   libhilog from /system/lib/platformsdk
#   libcrypto_openssl.z / libssl_openssl.z from /system/lib/platformsdk
# Removed (compared to pre-AXML-self-parse build): -L$AOSPLIB, -landroidfw,
# -lbase, -lcutils, -llog, RUNPATH /system/android/lib. AXML parsing now
# happens in baked-in axml_parser.{h,cpp}; ZIP parsing in baked-in minizip.
LIBS="-L$ML -L$SYS_LIB -L$SYS_LIB_SDK -L$SDK_SP \
-lc -ldl -lz -lutils.z \
-lhilog -lcrypto_openssl.z -lssl_openssl.z"
# [ARM64 2026-07-12] Strict link: --unresolved-symbols=ignore-all removed on
# purpose (plan §验收判据 item 2) — any missing dependency must fail HERE at
# link time, not silently defer to a runtime crash on-device.

# RUNPATH no longer needed (no NEEDED libs from /system/android/lib).
if $CXX --target=aarch64-linux-ohos -B$ML -shared -fPIC -Wl,-z,defs $OBJ $LIBS $BUILTINS -o $O/libapk_installer.so 2>$TMP/link.err; then
    echo "OK"
    sz=$(ls -lh $O/libapk_installer.so | awk '{print $5}')
    echo "  ✅ libapk_installer.so: $sz"
else
    echo "FAIL"
    head -5 $TMP/link.err | sed 's/^/    /'
fi

echo ""
ls -lh $O/libapk_installer.so 2>/dev/null
