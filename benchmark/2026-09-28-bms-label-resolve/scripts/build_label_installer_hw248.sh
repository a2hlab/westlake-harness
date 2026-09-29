#!/bin/bash
# Entry #25: rebuild libapk_installer.so WITH apk_label_resolver.cpp (fixes the
# "Hello World" desktop labels: the on-board so predates label resolution and the
# historical compile script's SRCS list omits apk_label_resolver.cpp entirely).
#
# Adapted from bms/src/adapter/build/inner/compile_apk_installer.sh for the
# hw248 oh610_lts_source tree, whose out/wukong100 has lib.unstripped/ layout
# instead of packages/phone/system/lib64. Runs ON hw248.
set -o pipefail

OH=/opt/build-trees/oh610_lts_source
ADAPTER=/opt/build-runs/2026-09-28-oh6.1.0.31-bms-label/adapter
O=$ADAPTER/out/adapter
OUTDIR=/opt/build-runs/2026-09-28-oh6.1.0.31-bms-label
OH_OUT=$OH/out/wukong100

CXX=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++
CC=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang

SR=$OH_OUT/obj/third_party/musl/usr
ML=$SR/lib/aarch64-linux-ohos

# hw248 lib layout: lib.unstripped/<domain>/<part>/lib*.so
SYS_LIB=$OH_OUT/lib.unstripped/thirdparty/zlib           # libshared_libz.z.so
SYS_LIB_SDK="$OH_OUT/lib.unstripped/thirdparty/openssl
$OH_OUT/lib.unstripped/hiviewdfx/hilog
$OH_OUT/lib.unstripped/commonlibrary/c_utils"
SDK_SP=$OH_OUT/lib.unstripped/commonlibrary/c_utils

mkdir -p "$O" "$OUTDIR/tmp" "$OUTDIR/logs"

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

BMS_INC=$(find $OH/foundation/bundlemanager/bundle_framework -type d -name 'include' 2>/dev/null | grep -v test | sed 's/^/-I/' | tr '\n' ' ')
BMS_INC="$BMS_INC $(find $OH/foundation/bundlemanager/bundle_framework/services/bundlemgr/include -mindepth 1 -type d 2>/dev/null | grep -v test | sed 's/^/-I/' | tr '\n' ' ')"
BMS_INC="$BMS_INC $(find $OH/foundation/bundlemanager/bundle_framework/interfaces/inner_api/appexecfwk_base/include -mindepth 1 -type d 2>/dev/null | grep -v test | sed 's/^/-I/' | tr '\n' ' ')"

BC=$ADAPTER/build/compat
CFLAGS="--target=aarch64-linux-ohos --sysroot=$SR -I$SR/include/aarch64-linux-ohos \
-std=c++17 -fPIC -O2 -fvisibility=hidden -D__OHOS__ \
-shared-libgcc -fno-omit-frame-pointer \
-fexceptions -frtti \
-include $BC/libcxx_compat.h -I$BC \
-include sys/types.h \
-Wno-unused-parameter -Wno-missing-field-initializers -Wno-error -Wno-macro-redefined -Wno-c++11-narrowing"

BUILTINS="$OH/prebuilts/clang/ohos/linux-x86_64/llvm/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a"

# FIX for entry #25: apk_label_resolver.cpp ADDED (was missing -> no ResolveApkLabel)
SRCS="$ADAPTER/framework/package-manager/jni/apk_label_resolver.cpp \
$ADAPTER/framework/package-manager/jni/apk_manifest_parser.cpp \
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

MINIZIP_C="$OH/third_party/zlib/contrib/minizip/unzip.c \
$OH/third_party/zlib/contrib/minizip/zip.c \
$OH/third_party/zlib/contrib/minizip/ioapi.c \
$ADAPTER/framework/package-manager/install_plan/src/sha256.c"

TMP=$OUTDIR/tmp
ok=0; fl=0
for src in $SRCS; do
    name=$(basename $src .cpp)
    echo -n "  Compiling $name... "
    if $CXX $CFLAGS $INC -c -o $TMP/$name.o $src 2>$OUTDIR/logs/$name.err; then
        echo "OK"; ok=$((ok+1))
    else
        echo "FAIL"; head -5 $OUTDIR/logs/$name.err | sed 's/^/    /'; fl=$((fl+1))
    fi
done

CFLAGS_C="--target=aarch64-linux-ohos --sysroot=$SR -I$SR/include/aarch64-linux-ohos \
-fPIC -O2 -D__OHOS__ -DUSE_FILE32API \
-I$OH/third_party/zlib -I$OH/third_party/zlib/contrib/minizip \
-I$ADAPTER/framework/package-manager/install_plan/include \
-Wno-implicit-function-declaration -Wno-error"
for src in $MINIZIP_C; do
    name=$(basename $src .c)
    echo -n "  Compiling $name (C, minizip)... "
    if $CC $CFLAGS_C -c -o $TMP/${name}_minizip.o $src 2>$OUTDIR/logs/${name}_minizip.err; then
        echo "OK"; ok=$((ok+1))
    else
        echo "FAIL"; head -5 $OUTDIR/logs/${name}_minizip.err | sed 's/^/    /'; fl=$((fl+1))
    fi
done

echo ""
echo "  Compiled: $ok/$(( ok + fl ))"
if [ $fl -ne 0 ]; then echo "  some objects FAILED - aborting link"; exit 1; fi

echo -n "  Linking libapk_installer.so... "
OBJ=$(ls $TMP/*.o 2>/dev/null | tr '\n' ' ')
LIBS=""
for d in $ML $SYS_LIB $SYS_LIB_SDK $SDK_SP; do LIBS="$LIBS -L$d"; done
LIBS="$LIBS -lc -ldl -lshared_libz -lutils.z -lhilog -lcrypto_openssl.z -lssl_openssl.z"

if $CXX $CFLAGS -shared -o $O/libapk_installer.so $OBJ $LIBS $BUILTINS \
    -Wl,--no-undefined 2>$OUTDIR/logs/link.err; then
    echo "OK (strict link)"
else
    echo "FAIL"; head -20 $OUTDIR/logs/link.err | sed 's/^/    /'; exit 1
fi

file $O/libapk_installer.so
sha256sum $O/libapk_installer.so
echo "DONE: $O/libapk_installer.so"
