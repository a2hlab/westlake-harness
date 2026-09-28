#!/usr/bin/env bash
# Runs inside the locked linux/amd64 container.  /inputs and /toolchain are
# immutable project-local mounts; /work, /artifacts and /tmp are project-local
# writable mounts.  No external source tree is visible here.

set -euo pipefail
IFS=$'\n\t'
umask 022
export LC_ALL=C
export LANG=C
export TZ=UTC
export SOURCE_DATE_EPOCH=0
export ZERO_AR_DATE=1
export HOME=/work/home
export TMPDIR=/tmp

mkdir -p /work/home /work/obj/compat /work/obj/wrapper /work/obj/appspawn /work/logs /artifacts
: > /work/logs/commands.sh

CXX=/toolchain/bin/clang-15
CC=/toolchain/bin/clang-15
READELF=/toolchain/bin/llvm-readelf
STRIP=/toolchain/bin/llvm-strip
OBJDUMP=/toolchain/bin/llvm-objdump
TARGET=aarch64-linux-ohos
SYSROOT=/inputs/sysroot
TARGET_LIB="$SYSROOT/lib/$TARGET"
BUILTINS=/toolchain/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a

for required in "$CXX" "$READELF" "$STRIP" "$OBJDUMP"; do
    [[ -f "$required" && -x "$required" ]] || {
        echo "ERROR: frozen tool input missing: $required" >&2
        exit 1
    }
done
[[ -f "$BUILTINS" ]] || { echo "ERROR: frozen builtins missing: $BUILTINS" >&2; exit 1; }

record_command()
{
    printf '%q ' "$@" >>/work/logs/commands.sh
    printf '\n' >>/work/logs/commands.sh
}

run_logged()
{
    local label=$1
    shift
    record_command "$@"
    if ! "$@" >"/work/logs/$label.stdout" 2>"/work/logs/$label.stderr"; then
        echo "ERROR: $label failed; see project-local work/logs/$label.stderr" >&2
        exit 1
    fi
}

COMMON=(
    "--target=$TARGET"
    "--sysroot=$SYSROOT"
    -B/toolchain/bin
    -fPIC
    -O2
    -g
    -D__OHOS__
    -D_GNU_SOURCE
    -D_POSIX_SOURCE
    -ffile-prefix-map=/inputs=inputs
    -fdebug-prefix-map=/inputs=inputs
    -ffile-prefix-map=/work=work
    -fdebug-prefix-map=/work=work
    -isystem "$SYSROOT/include/$TARGET"
    -Wno-unused-parameter
    -Wno-format
    -Wno-sign-compare
    -Wno-missing-field-initializers
    -Wno-c99-designator
    -Wno-gnu-designator
    -Wno-extern-c-compat
    -Wno-deprecated-declarations
    -Wno-c++11-narrowing
    -Wno-error
)

CXX_STD=(
    -nostdinc++
    -isystem /toolchain/include/c++/v1
    -std=gnu++17
)

LINK_BASE=(
    "--target=$TARGET"
    "--sysroot=$SYSROOT"
    -B/toolchain/bin
    -B"$TARGET_LIB"
    -fuse-ld=lld
    -Wl,-z,defs
    -Wl,-z,now
    -Wl,--build-id=sha1
    -Wl,--hash-style=both
    -Wl,--no-undefined
    -Wl,--fatal-warnings
)

# ---------------------------------------------------------------------------
# 1. Build the admitted bionic/musl compatibility library from exact reviewed
#    sources.  No TLS ABI writer, pthread broker, signal broker, deprecated
#    minizip provider, or libziparchive ABI fallback is compiled.
# ---------------------------------------------------------------------------
COMPAT_SRC=/inputs/sources/bionic_compat/src
COMPAT_INC=/inputs/sources/bionic_compat/include
[[ ! -e "$COMPAT_SRC/minizip.cpp" ]] || {
    echo "ERROR: deprecated minizip.cpp entered the compat producer" >&2
    exit 1
}
COMPAT_OBJECTS=()
for source_name in \
    system_properties.cpp \
    malloc_compat.cpp \
    fdsan_stubs.cpp \
    misc_compat.cpp \
    abort_message_compat.cpp \
    liblog_android_supplement.cpp \
    sync_builtins.c
do
    source="$COMPAT_SRC/$source_name"
    object="/work/obj/compat/${source_name%.*}.o"
    COMPAT_OBJECTS+=("$object")
    if [[ $source_name == *.c ]]; then
        run_logged "compat_${source_name%.*}" \
            "$CC" "${COMMON[@]}" -std=c11 -D__ANDROID_API__=34 -DPAGE_SIZE=4096 \
            -I"$COMPAT_INC" -c "$source" -o "$object"
    else
        run_logged "compat_${source_name%.*}" \
            "$CXX" "${COMMON[@]}" "${CXX_STD[@]}" \
            -include "$COMPAT_INC/libcxx_compat.h" -I"$COMPAT_INC" \
            -DPARAM_VALUE_LEN_MAX=96 -Wno-constant-conversion \
            -c "$source" -o "$object"
    fi
done

run_logged compat_link \
    "$CXX" "${LINK_BASE[@]}" -shared -nostdlib++ \
    -Wl,-soname,libbionic_compat.so \
    -L/inputs/libraries/oh -L"$TARGET_LIB" \
    -o /artifacts/libbionic_compat.so.unstripped \
    "${COMPAT_OBJECTS[@]}" \
    -Wl,--no-as-needed -lbegetutil.z -lc++ -Wl,--as-needed \
    -lc -ldl -lpthread "$BUILTINS"
cp -p /artifacts/libbionic_compat.so.unstripped /artifacts/libbionic_compat.so
run_logged compat_strip "$STRIP" --strip-unneeded /artifacts/libbionic_compat.so

# ---------------------------------------------------------------------------
# 2. Build the pure-C ABI wrapper around stock HapContext specialization.
# ---------------------------------------------------------------------------
WRAPPER_SRC=/inputs/sources/hap_domain_wrapper/westlake_hap_domain_wrapper.cpp
run_logged wrapper_compile \
    "$CXX" "${COMMON[@]}" "${CXX_STD[@]}" \
    -include "$COMPAT_INC/libcxx_compat.h" -I"$COMPAT_INC" \
    -I/inputs/includes/oh/selinux_policycoreutils \
    -I/inputs/includes/oh/libselinux \
    -c "$WRAPPER_SRC" -o /work/obj/wrapper/westlake_hap_domain_wrapper.o

run_logged wrapper_link \
    "$CXX" "${LINK_BASE[@]}" -shared -nostdlib++ \
    -Wl,-soname,libwestlake_hap_domain_wrapper.so \
    -L/inputs/libraries/oh -L"$TARGET_LIB" \
    -o /artifacts/libwestlake_hap_domain_wrapper.so.unstripped \
    /work/obj/wrapper/westlake_hap_domain_wrapper.o \
    -Wl,--no-as-needed -lhap_restorecon.z -lc++ -Wl,--as-needed \
    -lc -ldl -lpthread "$BUILTINS"
cp -p /artifacts/libwestlake_hap_domain_wrapper.so.unstripped \
    /artifacts/libwestlake_hap_domain_wrapper.so
run_logged wrapper_strip "$STRIP" --strip-unneeded \
    /artifacts/libwestlake_hap_domain_wrapper.so

WRAPPER_BUILD_ID=$(
    "$READELF" -nW /artifacts/libwestlake_hap_domain_wrapper.so |
        awk '/Build ID:/ {print $3; exit}'
)
[[ "$WRAPPER_BUILD_ID" =~ ^[0-9a-f]{40}$ ]] || {
    echo "ERROR: wrapper must have a 20-byte sha1 Build-ID, got '$WRAPPER_BUILD_ID'" >&2
    exit 1
}
printf '%s\n' "$WRAPPER_BUILD_ID" >/artifacts/wrapper.build-id

if [[ ${WESTLAKE_WRAPPER_ID_PROBE:-0} == 1 ]]; then
    echo "wrapper_build_id=$WRAPPER_BUILD_ID"
    exit 0
fi

EXPECTED_WRAPPER_BUILD_ID=$(tr -d '[:space:]' </inputs/config/expected_wrapper_build_id.txt)
[[ "$EXPECTED_WRAPPER_BUILD_ID" =~ ^[0-9a-f]{40}$ ]] || {
    echo "ERROR: expected_wrapper_build_id.txt is not pinned to sha1" >&2
    exit 1
}
[[ "$WRAPPER_BUILD_ID" == "$EXPECTED_WRAPPER_BUILD_ID" ]] || {
    echo "ERROR: deterministic wrapper Build-ID changed: actual=$WRAPPER_BUILD_ID expected=$EXPECTED_WRAPPER_BUILD_ID" >&2
    exit 1
}
grep -Fq "\"$WRAPPER_BUILD_ID\"" /inputs/sources/appspawn/src/child_main.cpp || {
    echo "ERROR: child_main.cpp does not pin final wrapper Build-ID $WRAPPER_BUILD_ID" >&2
    exit 1
}

# ---------------------------------------------------------------------------
# 3. Build appspawn-x against the same generated compat and exact frozen OH /
#    AOSP closure.  --no-as-needed preserves the pre-fork load order whose TLS
#    layout is part of the generation contract.
# ---------------------------------------------------------------------------
APPSPAWN_SRC=/inputs/sources/appspawn/src
APPSPAWN_INC=(
    -I"$APPSPAWN_SRC"
    -I/inputs/includes/oh/appspawn_innerkits
    -I/inputs/includes/oh/init_innerkits
    -I/inputs/includes/oh/init_innerkits/syspara
    -I/inputs/includes/oh/hilog
    -I/inputs/includes/oh/c_utils
    -I/inputs/includes/oh/ipc_core
    -I/inputs/includes/oh/samgr_proxy
    -I/inputs/includes/oh/json
    -I/inputs/includes/oh/selinux_policycoreutils
    -I/inputs/includes/oh/libselinux
    -I/inputs/includes/oh/token_setproc
    -I/inputs/includes/oh/accesstoken
    -I/inputs/includes/native
    -I/inputs/includes/native/bionic_pthread_bridge
    -I/inputs/includes/native/jni_attach_admission
    -I/inputs/includes/native/thread_guard_registry
    -I/inputs/includes/native/thread_template_publisher
    -I/inputs/includes/native_loader
    -I"$COMPAT_INC"
    -I/inputs/includes/aosp/libnativehelper/include_jni
    -I/inputs/includes/aosp/libnativehelper/include
    -I/inputs/includes/aosp/libnativehelper/include_platform_header_only
    -I/inputs/includes/aosp/libnativehelper/include_platform
)

APPSPAWN_OBJECTS=()
for source_name in main.cpp appspawnx_runtime.cpp spawn_server.cpp child_main.cpp apk_verify_service.cpp native_compat_prepare.cpp; do
    source="$APPSPAWN_SRC/$source_name"
    object="/work/obj/appspawn/${source_name%.cpp}.o"
    APPSPAWN_OBJECTS+=("$object")
    run_logged "appspawn_${source_name%.cpp}" \
        "$CXX" "${COMMON[@]}" "${CXX_STD[@]}" \
        -include "$COMPAT_INC/libcxx_compat.h" "${APPSPAWN_INC[@]}" \
        -c "$source" -o "$object"
done

run_logged appspawn_native_compat_owner \
    "$CC" "${COMMON[@]}" -c /inputs/sources/appspawn/src/native_compat_prepare_owner_aarch64.S \
    -o /work/obj/appspawn/native_compat_prepare_owner_aarch64.o
APPSPAWN_OBJECTS+=(/work/obj/appspawn/native_compat_prepare_owner_aarch64.o)

run_logged appspawn_tls_prefix \
    "$CXX" "${COMMON[@]}" "${CXX_STD[@]}" \
    -c /inputs/sources/appspawn/tls_prefix/bionic_tls_prefix_reservation.cpp \
    -o /work/obj/appspawn/bionic_tls_prefix_reservation.o
APPSPAWN_OBJECTS+=(/work/obj/appspawn/bionic_tls_prefix_reservation.o)

run_logged appspawn_link \
    "$CXX" "${LINK_BASE[@]}" -pie \
    -L/artifacts -L/inputs/libraries/aosp -L/inputs/libraries/oh -L"$TARGET_LIB" \
    -o /artifacts/appspawn-x.unstripped \
    "${APPSPAWN_OBJECTS[@]}" \
    -Wl,--no-as-needed \
    -lc -lhilog -lipc_core.z -lsamgr_proxy.z -lbegetutil.z -lselinux.z \
    -lhap_restorecon.z -ltokensetproc_shared.z \
    -lnativehelper -llog -lbionic_compat -lart -lc++ \
    -Wl,--as-needed -ldl -lpthread "$BUILTINS"
cp -p /artifacts/appspawn-x.unstripped /artifacts/appspawn-x
run_logged appspawn_strip "$STRIP" --strip-unneeded /artifacts/appspawn-x

# The init-owned production service configuration is a same-generation
# artifact.  Shipping the ELF triplet with a stale ARM32/dev-mode cfg is a
# mixed-generation failure even when the ELF checks pass.
cp -p /inputs/config/appspawn_x.cfg /artifacts/appspawn_x.cfg

python3 /inputs/config/verify_generation.py \
    --artifacts /artifacts \
    --inputs /inputs \
    --readelf "$READELF" \
    --objdump "$OBJDUMP" \
    --expected-wrapper-build-id "$EXPECTED_WRAPPER_BUILD_ID" \
    >/work/logs/verify_generation.stdout \
    2>/work/logs/verify_generation.stderr

sha256sum \
    /artifacts/appspawn-x \
    /artifacts/appspawn-x.unstripped \
    /artifacts/libbionic_compat.so \
    /artifacts/libbionic_compat.so.unstripped \
    /artifacts/libwestlake_hap_domain_wrapper.so \
    /artifacts/libwestlake_hap_domain_wrapper.so.unstripped \
    /artifacts/appspawn_x.cfg \
    | sed 's#  /artifacts/#  #' > /artifacts/artifacts.sha256

echo "build_pass: frozen same-generation ELF gate passed"
