#!/usr/bin/env bash
# Assemble the FROZEN_TEST input tree consumed by
# src/tools/experiments/d600/build_appspawnx_frozen_test_nohardcode.sh.
#
# That build script takes a single self-contained input directory and never
# reaches outside it, which is what makes its output reproducible.  Nothing in
# the repository built that directory, so every earlier legacy-child build had
# to hand-assemble it and the layout was lost with the shell history.  This
# script is that missing step, written so the daemon can be produced on a bare
# x86 build host from source trees alone.
#
# Everything here is a link input: adapter sources from the repository, OH
# headers and .so stubs from the OpenHarmony source tree, and the AOSP-facing
# headers/libraries that are already frozen in the repository.  No prebuilt
# appspawn-x artifact is copied in.
#
#   SRC   adapter source tree               (default /opt/wl-src)
#   OHT   OpenHarmony 6.1.0.31 source tree  (default /opt/build-trees/oh610_lts_source)
#   OHOUT OpenHarmony build output          (default $OHT/out/wukong100)
#   BASE  frozen toolchain+sysroot tree     (default $SRC/.work/product-tls-generation/frozen)
#   FT    output directory                  (required)
set -euo pipefail
IFS=$'\n\t'
umask 022
export LC_ALL=C

SRC=${SRC:-/opt/wl-src}
OHT=${OHT:-/opt/build-trees/oh610_lts_source}
OHOUT=${OHOUT:-$OHT/out/wukong100}
BASE=${BASE:-$SRC/.work/product-tls-generation/frozen}
FT=${FT:?set FT to the frozen-test output directory}

ADAPTER=$SRC/adapter/framework/appspawn-x
NATIVE_COMPAT=$SRC/adapter/framework/native-compat
PLUGIN=$ADAPTER/security_specialization/stock_child_plugin
FROZEN_LIBS=$PLUGIN/frozen/runtime_provider
ROUTEA_OUT=$PLUGIN/out/route-a-generation

fail() { echo "ERROR: $*" >&2; exit 1; }

# Symlink rather than copy: the tree is ~2.5 GB of toolchain and the build
# script only reads from it.  -ffile-prefix-map still rewrites the recorded
# paths because the compiler sees them through $FT.
link_dir()
{
    local target=$1 name=$2
    [[ -d $target ]] || fail "missing input directory: $target"
    ln -sfn "$target" "$name"
}

copy_lib()
{
    local target=$1 dest=$2
    [[ -f $target ]] || fail "missing input library: $target"
    cp -pf "$target" "$dest"
}

# Prefer an artifact that was just built here over the checked-in frozen copy,
# so a from-source run on a fresh host stays from-source end to end.
first_existing()
{
    local candidate
    for candidate in "$@"; do
        [[ -f $candidate ]] && { printf '%s\n' "$candidate"; return 0; }
    done
    fail "none of these exist: $*"
}

rm -rf "$FT"
mkdir -p "$FT"/{sources/identity,includes/oh,includes/aosp/libnativeloader,libraries/oh,libraries/aosp,config}
cd "$FT"

# ---- toolchain + sysroot -------------------------------------------------
link_dir "$BASE/toolchain" toolchain
link_dir "$BASE/sysroot" sysroot
[[ -x $BASE/toolchain/bin/clang-15 ]] || fail "no clang-15 under $BASE/toolchain/bin"
[[ -f $BASE/toolchain/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a ]] ||
    fail "no aarch64-linux-ohos compiler-rt builtins under $BASE/toolchain"

# ---- adapter sources -----------------------------------------------------
# sources/appspawn is the adapter directory itself: the build script reads both
# src/ and tls_prefix/ out of it.
link_dir "$ADAPTER" sources/appspawn
link_dir "$ADAPTER/bionic_compat" sources/bionic_compat
link_dir "$ADAPTER/hap_domain_wrapper" sources/hap_domain_wrapper
link_dir "$NATIVE_COMPAT/jni-attach-admission" sources/jni_attach_admission
link_dir "$NATIVE_COMPAT/thread-guard-registry" sources/thread_guard_registry
link_dir "$NATIVE_COMPAT/bionic-pthread-bridge" sources/bionic_pthread_bridge
link_dir "$NATIVE_COMPAT/thread-template-publisher" sources/thread_template_publisher
# westlake_elf_identity.c / westlake_sha256.c live beside the Route A plugin;
# only those two translation units are compiled out of that directory.
link_dir "$PLUGIN/src" sources/identity/src
link_dir "$PLUGIN/include" sources/identity/include

for required in \
    sources/appspawn/src/main.cpp \
    sources/appspawn/src/native_compat_prepare_owner_aarch64.S \
    sources/appspawn/tls_prefix/bionic_tls_prefix_reservation.cpp \
    sources/hap_domain_wrapper/westlake_hap_domain_wrapper.cpp \
    sources/bionic_pthread_bridge/westlake_bionic_pthread_bridge.map \
    sources/thread_guard_registry/src/guard_store_aarch64.S \
    sources/identity/src/westlake_elf_identity.c \
    sources/identity/src/westlake_sha256.c
do
    [[ -f $required ]] || fail "assembled tree is missing $required"
done

# ---- OpenHarmony headers -------------------------------------------------
link_dir "$OHT/base/startup/appspawn/interfaces/innerkits/include" includes/oh/appspawn_innerkits
link_dir "$OHT/base/startup/init/interfaces/innerkits/include" includes/oh/init_innerkits
link_dir "$OHT/base/hiviewdfx/hilog/interfaces/native/innerkits/include" includes/oh/hilog
link_dir "$OHT/commonlibrary/c_utils/base/include" includes/oh/c_utils
link_dir "$OHT/foundation/communication/ipc/interfaces/innerkits/ipc_core/include" includes/oh/ipc_core
link_dir "$OHT/foundation/systemabilitymgr/samgr/interfaces/innerkits/samgr_proxy/include" includes/oh/samgr_proxy
link_dir "$OHT/third_party/json/include" includes/oh/json
link_dir "$OHT/base/security/selinux_adapter/interfaces/policycoreutils/include" includes/oh/selinux_policycoreutils
link_dir "$OHT/third_party/selinux/libselinux/include" includes/oh/libselinux
link_dir "$OHT/base/security/access_token/interfaces/innerkits/token_setproc/include" includes/oh/token_setproc
link_dir "$OHT/base/security/access_token/interfaces/innerkits/accesstoken/include" includes/oh/accesstoken

# ---- AOSP-facing headers -------------------------------------------------
# libnativehelper's four include roots are already frozen next to the
# toolchain; NativeLoader's header is the adapter's own OH port.
link_dir "$BASE/includes/aosp/libnativehelper" includes/aosp/libnativehelper
link_dir "$SRC/adapter/framework/native-loader-oh/include" includes/aosp/libnativeloader/include

# ---- link-time shared objects -------------------------------------------
copy_lib "$OHOUT/startup/init/libbegetutil.z.so" libraries/oh/
copy_lib "$OHOUT/hiviewdfx/hilog/libhilog.so" libraries/oh/
copy_lib "$OHOUT/systemabilitymgr/samgr/libsamgr_proxy.z.so" libraries/oh/
copy_lib "$OHOUT/thirdparty/selinux/libselinux.z.so" libraries/oh/
copy_lib "$OHOUT/security/selinux_adapter/libhap_restorecon.z.so" libraries/oh/
copy_lib "$OHOUT/security/access_token/libtokensetproc_shared.z.so" libraries/oh/
# The board resolves IPC through libipc_single.z.so (there is no
# libipc_core.z.so anywhere on 5ce1227d); link against the same soname.
copy_lib "$OHOUT/communication/ipc/libipc_single.z.so" libraries/oh/
copy_lib "$(first_existing "$FROZEN_LIBS/libraries/oh/libc++.so" \
                           "$BASE/sysroot/lib/aarch64-linux-ohos/libc++.so")" libraries/oh/

copy_lib "$(first_existing "$ROUTEA_OUT/providers/libart.so" \
                           "$FROZEN_LIBS/libraries/aosp/libart.so")" libraries/aosp/
copy_lib "$(first_existing "$ROUTEA_OUT/providers/libnativehelper.so" \
                           "$FROZEN_LIBS/libraries/aosp/libnativehelper.so")" libraries/aosp/
copy_lib "$(first_existing "$ROUTEA_OUT/providers/liblog.so" \
                           "$FROZEN_LIBS/libraries/aosp/liblog.so")" libraries/aosp/
copy_lib "$(first_existing "$ROUTEA_OUT/providers/libnativeloader.so" \
                           "$FROZEN_LIBS/provider-v12/providers/libnativeloader.so")" libraries/aosp/

# ---- init config ---------------------------------------------------------
copy_lib "$ADAPTER/config/appspawn_x.cfg" config/

echo "assembled_frozen_test: $FT"
find "$FT" -maxdepth 2 -mindepth 1 \( -type l -o -type f \) -printf '  %P\n' | sort
