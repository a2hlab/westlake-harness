#!/bin/bash
# compile_android_runtime_layer4.sh — focused Layer 4 runner.
#
# Extracts ONLY the "Layer 4: libandroid_runtime" step from
# cross_compile_arm32.sh and re-runs it, so we can iterate on the
# android_runtime cross-compile without paying the 20+ min cost of
# rebuilding libart / libbase / libcutils / libutils etc. first.
#
# Reuses the same flags and the `bld` helper as the full script by
# re-declaring them locally (copy-paste is acceptable here because the
# original script is append-only and its env vars are stable).

set -o pipefail

VERBOSE=0
for arg in "$@"; do
    [ "$arg" = "--verbose" ] && VERBOSE=1
done

OH=/home/HanBingChen/oh
A=/home/HanBingChen/aosp
ADAPTER_ROOT=/home/HanBingChen/adapter
# No .so output; .o files go to /tmp/cc100/android_runtime/ consumed by link_libandroid_runtime_full.sh
ERRLOG=/tmp/cc100/build_errors_layer4.log

CXX=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++
CC=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang
READELF=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-readelf

OH_OUT=$OH/out/rk3568
SR=$OH_OUT/obj/third_party/musl/usr
ML=$SR/lib/arm-linux-ohos
BC=$ADAPTER_ROOT/framework/appspawn-x/bionic_compat/include

WARN_FLAGS="-Wno-unused-parameter -Wno-format -Wno-sign-compare -Wno-missing-field-initializers -Wno-c99-designator -Wno-gnu-designator -Wno-extern-c-compat -Wno-deprecated-declarations -Wno-c++11-narrowing -Wno-error"
COMMON_BASE="--target=arm-linux-ohos --sysroot=$SR -I$SR/include/arm-linux-ohos -fPIC -O2 -D__OHOS__ -D_GNU_SOURCE -D_POSIX_SOURCE $WARN_FLAGS"
CXXF="$CXX $COMMON_BASE -include $BC/libcxx_compat.h -I$BC -std=c++17"
# Layer 4 override: AOSP core/jni files mix <atomic> / <stdatomic.h>, which
# the OH libcxx-ohos header checks against C++23. Use -std=c++2b for the whole
# Layer 4 build to satisfy the check without touching individual files.
CXXF_LAYER4="$CXX $COMMON_BASE -include $BC/libcxx_compat.h -I$BC -std=c++2b"
CF="$CC $COMMON_BASE -std=c11 -D__ANDROID_API__=34 -DPAGE_SIZE=4096"

mkdir -p /tmp/cc100
: > "$ERRLOG"

bld() {
    local N=$1 I=$2; shift 2
    local D=/tmp/cc100/$N; mkdir -p $D
    local ok=0 fl=0
    for s in "$@"; do
        local b=$(basename $s); b=${b%.*}; local ext=${s##*.}
        local comp=$CXXF_LAYER4; [ "$ext" = "c" ] && comp=$CF
        if $comp $I -c -o $D/$b.o $s 2>/tmp/cc100/${N}_${b}.err; then
            ok=$((ok+1))
            [ $VERBOSE -eq 1 ] && echo "    OK   $b"
        else
            fl=$((fl+1))
            echo "=== FAIL: $N/$b ===" >> "$ERRLOG"
            grep -m5 -E "error:|fatal error:" /tmp/cc100/${N}_${b}.err >> "$ERRLOG" 2>/dev/null || head -10 /tmp/cc100/${N}_${b}.err >> "$ERRLOG"
            echo "" >> "$ERRLOG"
            if [ $VERBOSE -eq 1 ]; then
                echo "    FAIL $b:"
                grep -m3 -E "error:|fatal error:" /tmp/cc100/${N}_${b}.err 2>/dev/null | sed 's/^/      /'
            fi
        fi
    done
    echo ""
    echo "  lib$N: $ok OK / $fl FAIL / $((ok+fl)) total"
}

# ============================================================
# Layer 4: libandroid_runtime (expanded)
# ============================================================
echo "--- Layer 4: libandroid_runtime ---"
AR_INC="-I$A/frameworks/base/core/jni -I$A/frameworks/base/core/jni/include \
-I$A/frameworks/base/include -I$A/frameworks/base/native/include \
-I$A/frameworks/base/libs/androidfw/include \
-I$A/frameworks/base/libs/hwui/apex/include \
-I$A/frameworks/native/include -I$A/frameworks/native/libs/binder/include \
-I$A/frameworks/native/libs/input/include -I$A/frameworks/native/libs/gui/include \
-I$A/frameworks/native/libs/ui/include -I$A/frameworks/native/libs/nativewindow/include \
-I$A/frameworks/native/libs/arect/include -I$A/frameworks/native/libs/math/include \
-I$A/frameworks/native/libs/nativebase/include \
-I$A/frameworks/native/libs/binderthreadstate/include \
-I$A/system/logging/liblog/include -I$A/system/libbase/include \
-I$A/system/core/include -I$A/system/core/libcutils/include \
-I$A/system/core/libutils/include -I$A/system/core/libsystem/include \
-I$A/system/core/libprocessgroup/include \
-I$A/system/core/debuggerd/include \
-I$A/system/core/debuggerd/common/include \
-I$A/system/libhwbinder/include \
-I$A/system/incremental_delivery/incfs/util/include \
-I$A/external/sqlite/android \
-I$A/external/sqlite/dist \
-I$A/libnativehelper/include_jni -I$A/libnativehelper/include \
-I$A/libnativehelper/header_only_include -I$A/libnativehelper/include_platform_header_only \
-I$A/libnativehelper/include_platform \
-I$A/external/fmtlib/include \
-I$A/external/icu/libandroidicu/include -I$A/external/icu/icu4c/source/common \
-I$A/art/runtime -I$A/art/libdexfile/external/include \
-I$A/system/libziparchive/include \
-I$A/system/libhidl/base/include \
-I$A/system/core/libusbhost/include \
-I$A/frameworks/minikin/include \
-I$A/frameworks/native/libs/cputimeinstate \
-I$A/frameworks/native/libs/binder/ndk/include_ndk \
-I$A/frameworks/native/libs/binder/ndk/include_cpp \
-I$A/frameworks/av/media/libaudioclient/include \
-I$A/art/libnativeloader/include \
-I$A/bionic/libc/async_safe/include \
-I$OH/third_party/sqlite/include \
-I$OH/third_party/zlib \
-I$OH/third_party/EGL/api \
-I$OH/third_party/openGLES/api \
-I$ADAPTER_ROOT/aosp_patches/replacement_headers \
-I$ADAPTER_ROOT/build/aidl_gen \
-fno-rtti"

RT_DIR=$A/frameworks/base/core/jni

# EXCLUSIONS — files known to require libraries not in the partial sync OR
# replaced by hand-written stubs:
#   - android_os_Debug.cpp        (dmabufinfo + memtrack + memunreachable + vintf)
#   - android_view_Surface.cpp    (replaced by build/android_view_surface_stubs.cpp)
#   - android_view_SurfaceControl.cpp (same)
#   - android_os_VintfObject.cpp / android_os_VintfRuntimeInfo.cpp (libvintf missing)
#   - android_os_SELinux.cpp      (external/selinux missing)
#   - any *VintfObject.cpp / SELinux.cpp — libraries not in sync
EXCLUDED_FILES="android_os_Debug.cpp android_view_Surface.cpp android_view_SurfaceControl.cpp \
android_os_VintfObject.cpp android_os_VintfRuntimeInfo.cpp android_os_SELinux.cpp \
LayoutlibLoader.cpp"

# Build the full file list from disk so we try EVERY source, then report
# honest success/failure counts. This gives us a ground truth view of which
# additional files the partial sync can cover.
RT_FILES=""
for f in $RT_DIR/*.cpp; do
    b=$(basename "$f")
    skip=0
    for x in $EXCLUDED_FILES; do
        [ "$b" = "$x" ] && skip=1 && break
    done
    [ $skip -eq 0 ] && RT_FILES="$RT_FILES $f"
done

# AOSP-specific SQLite extensions — provide register_android_functions()
# called from android_database_SQLiteConnection.cpp. These live outside
# core/jni but are part of libandroid_runtime's effective dependency set.
SQLITE_EXT_DIR=$A/external/sqlite/android
if [ -f $SQLITE_EXT_DIR/sqlite3_android.cpp ]; then
    RT_FILES="$RT_FILES $SQLITE_EXT_DIR/sqlite3_android.cpp \
$SQLITE_EXT_DIR/PhoneNumberUtils.cpp \
$SQLITE_EXT_DIR/OldPhoneNumberUtils.cpp"
fi

# Clean previous .o / .err so the counts are accurate.
rm -rf /tmp/cc100/android_runtime /tmp/cc100/android_runtime_*.err
mkdir -p /tmp/cc100/android_runtime

bld android_runtime "$AR_INC" $RT_FILES

echo ""
echo "=== Summary ==="
echo "  .o files produced: $(ls /tmp/cc100/android_runtime/*.o 2>/dev/null | wc -l)"
echo "  .err non-empty:    $(for f in /tmp/cc100/android_runtime_*.err; do [ -s "$f" ] && echo 1; done 2>/dev/null | wc -l)"
echo "  log: $ERRLOG"
