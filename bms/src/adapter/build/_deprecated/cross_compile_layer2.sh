#!/bin/bash
# Cross-compile AOSP base libraries (Layer 2) using OH Clang
# Target: aarch64-linux-ohos (musl libc)
# Dependencies: Layer 0 (musl) + Layer 1 (bionic_compat)
set -e

AOSP=~/aosp
OH=~/oh
OUT=~/adapter/out/native
BUILD=/tmp/layer2_build

OH_CLANG=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++
OH_CC=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang
OH_AR=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-ar
READELF=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-readelf

MUSL_INC=$OH/out/rk3588/obj/third_party/musl/intermidiates/linux/musl_src_ported/include
MUSL_PORTING_INC=$OH/third_party/musl/porting/linux/user/include
MUSL_LIB=$OH/out/rk3588/obj/third_party/musl/usr/lib/aarch64-linux-ohos
CLANG_INC=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/lib/clang/15.0.4/include
BIONIC_COMPAT=~/adapter/framework/appspawn-x/bionic_compat

TARGET="--target=aarch64-linux-ohos"
COMMON_CFLAGS="$TARGET -fPIC -O2 -D__OHOS__ -DPARAM_VALUE_LEN_MAX=96 -D_FORTIFY_SOURCE=0 -Wno-constant-conversion"
COMMON_CXXFLAGS="$COMMON_CFLAGS -std=c++17 -nostdinc++"
SYS_INCLUDES="-isystem $CLANG_INC -isystem $MUSL_INC -isystem $MUSL_PORTING_INC"
LINK_FLAGS="$TARGET -B$MUSL_LIB -L$MUSL_LIB -L$OUT"

mkdir -p $BUILD $OUT

compile_lib() {
    local name=$1
    shift
    local sources=("$@")
    local obj_dir=$BUILD/$name
    mkdir -p $obj_dir

    echo ""
    echo "================================================================"
    echo "  Building: $name (${#sources[@]} source files)"
    echo "================================================================"

    local objs=""
    local ok=0
    local fail=0
    for src in "${sources[@]}"; do
        local base=$(basename "$src" | sed 's/\.[^.]*$//')
        local obj="$obj_dir/${base}.o"

        local ext="${src##*.}"
        local compiler=$OH_CLANG
        local flags="$COMMON_CXXFLAGS"
        if [ "$ext" = "c" ]; then
            compiler=$OH_CC
            flags="$COMMON_CFLAGS -std=c11"
        fi

        echo -n "  $base.$ext ... "
        if $compiler $flags $INCLUDES $SYS_INCLUDES -c -o "$obj" "$src" 2>/tmp/layer2_err.log; then
            echo "OK"
            ok=$((ok+1))
        else
            echo "FAILED"
            cat /tmp/layer2_err.log | head -3
            fail=$((fail+1))
        fi
        objs="$objs $obj"
    done

    echo "  Compiled: $ok OK, $fail FAILED"

    if [ $fail -gt 0 ]; then
        echo "  SKIP linking due to failures"
        return 1
    fi

    # Link shared library
    echo "  Linking lib${name}.so ..."
    $OH_CLANG $LINK_FLAGS -shared -fPIC -o $OUT/lib${name}.so $objs -lc -lbionic_compat 2>/tmp/layer2_err.log
    if [ $? -eq 0 ]; then
        local size=$(ls -lh $OUT/lib${name}.so | awk '{print $5}')
        echo "  => lib${name}.so ($size)"
        $READELF -d $OUT/lib${name}.so | grep NEEDED | sed 's/^/    /'
        return 0
    else
        echo "  Link FAILED:"
        cat /tmp/layer2_err.log | head -5
        return 1
    fi
}

echo "============================================================"
echo "  Layer 2: AOSP Base Libraries Cross-Compilation"
echo "  Target: aarch64-linux-ohos (OH Clang 15.0.4)"
echo "============================================================"

# ================================================================
# 1. liblog
# ================================================================
INCLUDES="-I$BIONIC_COMPAT/include \
    -I$AOSP/system/logging/liblog/include \
    -I$AOSP/system/libbase/include \
    -I$AOSP/system/core/libcutils/include \
    -I$AOSP/system/core/include \
    -DLIBLOG_LOG_TAG=1006 \
    -DSNET_EVENT_LOG_TAG=1397638484"

compile_lib "log" \
    $AOSP/system/logging/liblog/log_event_list.cpp \
    $AOSP/system/logging/liblog/log_event_write.cpp \
    $AOSP/system/logging/liblog/logger_name.cpp \
    $AOSP/system/logging/liblog/logger_read.cpp \
    $AOSP/system/logging/liblog/logger_write.cpp \
    $AOSP/system/logging/liblog/logprint.cpp \
    $AOSP/system/logging/liblog/properties.cpp \
    $AOSP/system/logging/liblog/event_tag_map.cpp \
    $AOSP/system/logging/liblog/log_time.cpp

# ================================================================
# 2. libbase
# ================================================================
INCLUDES="-I$BIONIC_COMPAT/include \
    -I$AOSP/system/libbase/include \
    -I$AOSP/system/logging/liblog/include \
    -I$AOSP/system/core/include \
    -I$AOSP/external/fmtlib/include \
    -DANDROID_BASE_UNIQUE_FD_DISABLE_FDSAN"

compile_lib "base" \
    $AOSP/system/libbase/abi_compatibility.cpp \
    $AOSP/system/libbase/chrono_utils.cpp \
    $AOSP/system/libbase/cmsg.cpp \
    $AOSP/system/libbase/errors_unix.cpp \
    $AOSP/system/libbase/file.cpp \
    $AOSP/system/libbase/hex.cpp \
    $AOSP/system/libbase/logging.cpp \
    $AOSP/system/libbase/mapped_file.cpp \
    $AOSP/system/libbase/parsebool.cpp \
    $AOSP/system/libbase/parsenetaddress.cpp \
    $AOSP/system/libbase/posix_strerror_r.cpp \
    $AOSP/system/libbase/process.cpp \
    $AOSP/system/libbase/properties.cpp \
    $AOSP/system/libbase/stringprintf.cpp \
    $AOSP/system/libbase/strings.cpp \
    $AOSP/system/libbase/threads.cpp \
    $AOSP/system/libbase/test_utils.cpp \
    $AOSP/system/libbase/utf8.cpp

# ================================================================
# 3. libcutils
# ================================================================
INCLUDES="-I$BIONIC_COMPAT/include \
    -I$AOSP/system/core/libcutils/include \
    -I$AOSP/system/logging/liblog/include \
    -I$AOSP/system/libbase/include \
    -I$AOSP/system/core/include \
    -I$AOSP/external/fmtlib/include"

compile_lib "cutils" \
    $AOSP/system/core/libcutils/config_utils.cpp \
    $AOSP/system/core/libcutils/hashmap.cpp \
    $AOSP/system/core/libcutils/iosched_policy.cpp \
    $AOSP/system/core/libcutils/load_file.cpp \
    $AOSP/system/core/libcutils/native_handle.cpp \
    $AOSP/system/core/libcutils/properties.cpp \
    $AOSP/system/core/libcutils/record_stream.cpp \
    $AOSP/system/core/libcutils/socket_inaddr_any_server_unix.cpp \
    $AOSP/system/core/libcutils/socket_local_client_unix.cpp \
    $AOSP/system/core/libcutils/socket_local_server_unix.cpp \
    $AOSP/system/core/libcutils/socket_network_client_unix.cpp \
    $AOSP/system/core/libcutils/sockets_unix.cpp \
    $AOSP/system/core/libcutils/sockets.cpp \
    $AOSP/system/core/libcutils/str_parms.cpp \
    $AOSP/system/core/libcutils/threads.cpp

# ================================================================
# 4. libutils
# ================================================================
INCLUDES="-I$BIONIC_COMPAT/include \
    -I$AOSP/system/core/libutils/include \
    -I$AOSP/system/core/libcutils/include \
    -I$AOSP/system/logging/liblog/include \
    -I$AOSP/system/libbase/include \
    -I$AOSP/system/core/include \
    -I$AOSP/system/core/libprocessgroup/include \
    -I$AOSP/system/core/libvndksupport/include \
    -I$AOSP/external/fmtlib/include"

compile_lib "utils" \
    $AOSP/system/core/libutils/Errors.cpp \
    $AOSP/system/core/libutils/FileMap.cpp \
    $AOSP/system/core/libutils/JenkinsHash.cpp \
    $AOSP/system/core/libutils/LightRefBase.cpp \
    $AOSP/system/core/libutils/Looper.cpp \
    $AOSP/system/core/libutils/NativeHandle.cpp \
    $AOSP/system/core/libutils/Printer.cpp \
    $AOSP/system/core/libutils/RefBase.cpp \
    $AOSP/system/core/libutils/SharedBuffer.cpp \
    $AOSP/system/core/libutils/StopWatch.cpp \
    $AOSP/system/core/libutils/String8.cpp \
    $AOSP/system/core/libutils/String16.cpp \
    $AOSP/system/core/libutils/StrongPointer.cpp \
    $AOSP/system/core/libutils/SystemClock.cpp \
    $AOSP/system/core/libutils/Threads.cpp \
    $AOSP/system/core/libutils/Timers.cpp \
    $AOSP/system/core/libutils/Tokenizer.cpp \
    $AOSP/system/core/libutils/Unicode.cpp \
    $AOSP/system/core/libutils/VectorImpl.cpp

# ================================================================
# 5. libnativehelper
# ================================================================
INCLUDES="-I$BIONIC_COMPAT/include \
    -I$AOSP/libnativehelper/include \
    -I$AOSP/libnativehelper/include_jni \
    -I$AOSP/libnativehelper/header_only_include \
    -I$AOSP/system/logging/liblog/include \
    -I$AOSP/system/libbase/include \
    -I$AOSP/system/core/include"

compile_lib "nativehelper" \
    $AOSP/libnativehelper/JNIHelp.cpp \
    $AOSP/libnativehelper/JniInvocation.cpp \
    $AOSP/libnativehelper/JniConstants.cpp

# ================================================================
# Summary
# ================================================================
echo ""
echo "============================================================"
echo "  Layer 2 Cross-Compilation Summary"
echo "============================================================"
echo ""
for lib in liblog libbase libcutils libutils libnativehelper; do
    if [ -f $OUT/${lib}.so ]; then
        size=$(ls -lh $OUT/${lib}.so | awk '{print $5}')
        echo "  ✅ ${lib}.so  ($size)"
    else
        echo "  ❌ ${lib}.so  NOT BUILT"
    fi
done
echo ""
echo "  ✅ libbionic_compat.so  ($(ls -lh $OUT/libbionic_compat.so | awk '{print $5}'))"
echo ""
ls -lh $OUT/
