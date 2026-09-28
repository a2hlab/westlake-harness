#!/bin/bash
# === GUARD: internal helper, do not invoke directly ===
if [ "${BUILD_INNER_INVOKED}" != "1" ]; then
    echo "[GUARD] $(basename "$0") is an internal helper — invoke via build_*.sh / restore_after_sync.sh / etc." >&2
    echo "[GUARD] Escape hatch (debug only): BUILD_INNER_INVOKED=1 bash $(basename "$0")" >&2
    exit 2
fi
# === END GUARD ===
# [DEPRECATED Phase 1 — 2026-05-21] Use build_appspawn_x.sh instead.
echo "[DEPRECATED] $(basename "$0") is wrapped by build_appspawn_x.sh — Phase 4 will absorb this" >&2
# ============================================================================
# 重复犯错警示 (appspawn-x 编译，调改前必读)
# ============================================================================
#
# [AS-1] C++ LOG 必须走 HiLogPrint，禁止 fprintf(stderr) 兜底
#   现象：init service 模式下 appspawn-x 启动后看不到任何 log，blocker 排查
#         完全黑盒；只有手工 shell exec 跑同一个 binary 才能看到 stderr。
#   根因：init service 启动子进程时 stderr=/dev/null（被 init 重定向丢弃）；
#         fprintf(stderr) 永远不会被任何观测到。
#   措施：appspawn-x 所有 C++ LOG 宏必须扩展为 HiLogPrint(LOG_TYPE_CORE,
#         level, 0xD000F00, tag, fmt, ...)；现存 fprintf(stderr) 必须改写。
#         B.31 已沉淀。
#         （memory: feedback_appspawnx_log_to_hilog.md）
#
# [AS-2] socket 必须用 init 传入的 fd，不要自己 unlink+bind
#   现象：begetctl start_service appspawn-x 后客户端连不上 socket；从 stderr
#         (改 hilog 后从 hilog) 看到 EADDRINUSE 或 bind 失败。
#   根因：appspawn-x 早期 main() 自己 unlink(socket_path) + socket+bind+listen，
#         绕过了 init 已经 listen 好的 socket。Init 给的是现成 fd，要从环境变量
#         OHOS_SOCKET_<name> 读出来直接 fcntl/listen。
#   措施：main() 用 GetControlSocket 读 init fd，禁止 unlink+bind 路径。
#         B.29/B.30 已修。
#         （memory: feedback_appspawnx_socket_bug.md）
#
# [AS-3] main() 必须 setenv 关键环境变量，不能依赖 init cfg env 字段
#   现象：appspawn-x 启动后 ART JNI_CreateJavaVM 报 BOOTCLASSPATH 没设；或者
#         AT_SECURE 被剥光了 LD_LIBRARY_PATH 等关键 env 进不去 child。
#   根因：(a) OH init_service_manager.c:1023 strcpy_s 用 srcLen+1 当 destMax，
#         env value > 127 字节会覆盖相邻 ServiceEnv 结构（OH bug，非本项目能改）；
#         (b) init 通过 execve 启 service 时 AT_SECURE 会剥 LD_PRELOAD/LD_LIBRARY_PATH
#         等敏感 env，传不到子进程。
#   措施：appspawn-x main() 第一步 seedRequiredEnvs() 自己 setenv 全部需要的
#         env (BOOTCLASSPATH / DEX2OATBOOTCLASSPATH / LD_LIBRARY_PATH 等)，
#         不依赖 cfg env 字段传递。
#         （memory: feedback_appspawnx_env_seed.md / reference_oh_init_env_overflow.md）
#
# [AS-4] cfg path 不能用 sh -c 包装
#   现象：init service 启动失败 + 反复 respawn-fail，hilog 报 execv EACCES (errno 13)。
#   根因：appspawn_x.cfg 里 path 字段写 ["sh", "-c", "/system/bin/appspawn-x"]
#         之类，secon=appspawn:s0 SELinux 域不允许 execve sh_exec → 执行立刻被
#         拒，service 永远起不来。
#   措施：path 字段必须直接是 ["/system/bin/appspawn-x"] 列表，不可 sh -c 包装。
#         （memory: feedback_init_service_sh_wrapper_regression.md）
#
# [AS-5] 替换 /system/bin/appspawn-x 必须 restorecon
#   现象：见部署脚本 [P-2]。
#   措施：本脚本编出 ELF 后 push 到 device，部署阶段必须 restorecon；本脚本
#         本身只负责编出二进制，restorecon 在 deploy 脚本里。
#         （memory: feedback_appspawnx_restorecon_invalid_flag.md）
#
# [AS-6] ART VM 必须从 boot.art 启动，禁止只靠 -Xbootclasspath
#   现象：appspawn-x 启动 ART VM 后 ClassLinker 深递归爆栈，core dump 显示
#         上千层 LinkClass 调用栈。
#   根因：只传 -Xbootclasspath 让 ART 现场从 raw dex 加载所有 BCP 类，类间引用
#         触发递归解析，stack 一定会爆。boot image 把这层预解析做掉了。
#   措施：appspawn-x runtime VM options 必须包含 -Ximage:/system/android/framework/
#         arm/boot.art；本脚本编的代码里这个 option 不能去掉。
#         （memory: feedback_always_use_boot_image.md）
#
# [AS-7] parent appspawn-x stderr 默认 /dev/null —— 抓 ART OrDie/LOG(FATAL) 时
#         必须把诊断 redirect 加到 parent，并且**不能用 freopen mode "a"**
#   现象（此条已重犯多次，2026-05-06 又一次浪费时间）：
#     1) 找不到 parent appspawn-x 在 ART startReg / kHwuiRegFns OrDie 失败的具体类/方法
#        message。hilog -x | grep D002000 经常没结果（libart 内部 libbase 实例与 adapter
#        SetLogger 的实例分裂），dmesg 也没 message（ART 没写 kmsg），cppcrash 经常
#        size=0 被 faultloggerd 删（critical mode init 抢先 respawn）。
#     2) 想到 freopen(/data/local/tmp/parent.stderr, "a", stderr) → 设备上文件不出现
#        （SELinux 域 appspawn:s0 不能写 /data/local/tmp，dmesg avc denied）。
#     3) 改 mode "a" 到 /data/service/el1/public/appspawnx/ → 文件创建 0 字节，但
#        dmesg avc denied { append } —— appspawn:s0 域只允许 create+write，禁止
#        append（与 child_main.cpp:64 用 O_TRUNC 的原因一致）。
#     4) 改 mode "w" → 文件正常写入，但 critical service 反复 respawn 每次都
#        truncate file，最后一次 respawn 进度可能比之前更早，message 被覆盖丢失。
#   根因综合：parent appspawn-x 的 fd 2 默认指向 /dev/null（init 启动 service 时
#         设的）。要让 ART libart_log_bridge.cpp 的 fprintf(stderr) 双写真正
#         可见，必须 (a) 在 main() 早期 freopen 到 appspawn:s0 域可写的位置；
#         (b) mode 必须是 "w" 不能是 "a"（SELinux append deny）；
#         (c) 路径必须带 PID 后缀（每次 respawn 独立文件），否则 truncate 互覆。
#   正确写法：
#         char path[160];
#         snprintf(path, sizeof(path),
#                  "/data/service/el1/public/appspawnx/parent_appspawnx_%d.stderr",
#                  (int)getpid());
#         FILE* fp = freopen(path, "w", stderr);
#         setvbuf(stderr, nullptr, _IOLBF, 0);  // line-buffered for crash safety
#   措施：
#     A. 该 redirect **是诊断手段，非生产代码**——抓到 OrDie 真因 + 修完根因后
#        必须立即从 main.cpp 删除（不能让 parent stderr 留在文件里污染 disk）。
#     B. 平时 parent 不需要 stderr —— OrDie 真因若发生在 child（如 helloworld
#        Paint.nGetFontMetricsInt NULL jclass），child 自己有 redirect 到
#        adapter_child_<pid>.stderr，message 总有完整原文（feedback_art_abort_check_stderr_file.md）。
#        只有 OrDie 发生在 parent startReg 阶段（如 register_android_graphics_Graphics
#        内部 GetStaticMethodIDOrDie 失败），才需要 parent stderr redirect。
#     C. **此问题已重犯 2 次以上**（不同 attempt 被 SELinux 拒、被 truncate 覆盖、
#        路径错——浪费数小时反复实验）；下一次再遇到先回此节复诵 4 步：
#        路径(/data/service/el1/public/appspawnx/) + mode("w") + PID 后缀 + 立即回滚。
#
# ============================================================================
# Standalone compilation of appspawn-x for ARM32
# Uses OH clang + OH system libraries directly (bypasses GN/ninja)
set -o pipefail

OH="${OH_ROOT:-$HOME/oh}"
ADAPTER="${ADAPTER_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
PLUGIN="$ADAPTER/framework/appspawn-x/security_specialization/stock_child_plugin"
JNI_ATTACH="$ADAPTER/framework/native-compat/jni-attach-admission"
THREAD_GUARD_REGISTRY="$ADAPTER/framework/native-compat/thread-guard-registry"
THREAD_GUARD_REGISTRY_LIB_DIR="${WLTG_REGISTRY_LIB_DIR:-$THREAD_GUARD_REGISTRY/out/target}"
THREAD_TEMPLATE_PUBLISHER="$ADAPTER/framework/native-compat/thread-template-publisher"
BIONIC_PTHREAD_BRIDGE="$ADAPTER/framework/native-compat/bionic-pthread-bridge"
O="${ADAPTER_OUT_DIR:-$ADAPTER/out/adapter}"
TARGET_ARCH="${APPSPAWN_TARGET_ARCH:-arm32}"
STRICT_BUILD="${L03_A12_STRICT_BUILD:-0}"

case "$TARGET_ARCH" in
    arm32)
        TARGET_TRIPLE=arm-linux-ohos
        TARGET_INCLUDE=arm-linux-ohos
        TARGET_LIBDIR=lib
        BUILTINS_TRIPLE=arm-linux-ohos
        DEFAULT_PRODUCT=rk3568
        EXTRA_ARCH_LIB_PATHS="-L$OH/out/rk3568/innerkits/ohos-arm/selinux_adapter/libhap_restorecon -L$OH/out/rk3568/innerkits/ohos-arm/access_token/libtokensetproc_shared"
        ;;
    arm64|aarch64)
        TARGET_ARCH=arm64
        TARGET_TRIPLE=aarch64-linux-ohos
        TARGET_INCLUDE=aarch64-linux-ohos
        TARGET_LIBDIR=lib64
        BUILTINS_TRIPLE=aarch64-linux-ohos
        DEFAULT_PRODUCT=wukong100
        EXTRA_ARCH_LIB_PATHS=""
        ;;
    *) echo "ERROR: APPSPAWN_TARGET_ARCH must be arm32 or arm64" >&2; exit 2 ;;
esac

IDENTITY_ENV="${WLAR_IDENTITY_ENV:-$PLUGIN/r45_adapter_identity.env}"
identity_complete=1
for var in \
    WLAR_ADAPTER_BRIDGE_PATH WLAR_ADAPTER_BRIDGE_SHA256_HEX \
    WLAR_ADAPTER_BRIDGE_BUILD_ID_HEX WLAR_ANDROID_RUNTIME_PATH \
    WLAR_ANDROID_RUNTIME_SHA256_HEX WLAR_ANDROID_RUNTIME_BUILD_ID_HEX; do
    eval "value=\${$var:-}"
    [ -n "$value" ] || identity_complete=0
done
if [ "$identity_complete" -ne 1 ] && [ -f "$IDENTITY_ENV" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$IDENTITY_ENV"
    set +a
fi
if [ "$STRICT_BUILD" = 1 ]; then
    for var in \
        WLAR_ADAPTER_BRIDGE_PATH WLAR_ADAPTER_BRIDGE_SHA256_HEX \
        WLAR_ADAPTER_BRIDGE_BUILD_ID_HEX WLAR_ANDROID_RUNTIME_PATH \
        WLAR_ANDROID_RUNTIME_SHA256_HEX WLAR_ANDROID_RUNTIME_BUILD_ID_HEX; do
        eval "value=\${$var:-}"
        if [ -z "$value" ]; then
            echo "ERROR: strict build missing Route-A identity field: $var" >&2
            exit 2
        fi
    done
fi
case "$STRICT_BUILD" in
    0|1) ;;
    *) echo "ERROR: L03_A12_STRICT_BUILD must be 0 or 1" >&2; exit 2 ;;
esac

if [ -n "${L03_A12_GENERATION_ID:-}" ]; then
    : "${ADAPTER_OUT_DIR:?generation build requires ADAPTER_OUT_DIR}"
    : "${APPSPAWN_OBJ_DIR:?generation build requires APPSPAWN_OBJ_DIR}"
    : "${AOSP_LIB_DIR:?generation build requires AOSP_LIB_DIR}"
    : "${L03_A12_CXX:?generation build requires L03_A12_CXX}"
    : "${L03_A12_CC:?generation build requires L03_A12_CC}"
    : "${L03_A12_BUILTINS:?generation build requires L03_A12_BUILTINS}"
fi

CXX=${L03_A12_CXX:-$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang++}
CC=${L03_A12_CC:-$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang}

OH_PRODUCT="${OH_PRODUCT_NAME:-$DEFAULT_PRODUCT}"
if [ -d "$OH/out/$OH_PRODUCT" ]; then OH_OUT="$OH/out/$OH_PRODUCT"
else echo "ERROR: OH output dir not found: $OH/out/$OH_PRODUCT"; exit 1; fi

SR=$OH_OUT/obj/third_party/musl/usr
ML=$SR/lib/$TARGET_TRIPLE
SYS_LIB=$OH_OUT/packages/phone/system/$TARGET_LIBDIR
SYS_LIB_SDK=$SYS_LIB/platformsdk

mkdir -p $O

echo "=========================================="
echo "  appspawn-x compilation ($TARGET_ARCH)"
echo "=========================================="

# Include paths
INC="-I$ADAPTER/framework/appspawn-x/src \
-I$OH/base/startup/appspawn/interfaces/innerkits/include \
-I$OH/base/startup/appspawn/standard/appspawn_msg/include \
-I$OH/base/startup/init/interfaces/innerkits/include \
-I$OH/base/startup/init/interfaces/innerkits/include/syspara \
-I$OH/base/hiviewdfx/hilog/interfaces/native/innerkits/include \
-I$OH/commonlibrary/c_utils/base/include \
-I$OH/foundation/communication/ipc/interfaces/innerkits/ipc_core/include \
-I$OH/foundation/systemabilitymgr/samgr/interfaces/innerkits/samgr_proxy/include \
-I$OH/third_party/json/include \
-I$OH/base/security/selinux_adapter/interfaces/policycoreutils/include \
-I$OH/third_party/selinux/libselinux/include \
-I$OH/base/security/access_token/interfaces/innerkits/token_setproc/include \
-I$OH/base/security/access_token/interfaces/innerkits/accesstoken/include \
-I$PLUGIN/include \
-I$JNI_ATTACH/include \
-I$THREAD_GUARD_REGISTRY/include \
-I$THREAD_TEMPLATE_PUBLISHER/include \
-I$BIONIC_PTHREAD_BRIDGE/include \
-I$ADAPTER/framework/appspawn-x/bionic_compat/include \
-I${AOSP_ROOT:-$HOME/aosp}/libnativehelper/include_jni \
-I${AOSP_ROOT:-$HOME/aosp}/libnativehelper/include \
-I${AOSP_ROOT:-$HOME/aosp}/libnativehelper/include_platform_header_only \
-I${AOSP_ROOT:-$HOME/aosp}/libnativehelper/include_platform"

BC=$ADAPTER/framework/appspawn-x/bionic_compat/include
CFLAGS="--target=$TARGET_TRIPLE --sysroot=$SR -I$SR/include/$TARGET_INCLUDE \
-fPIC -O2 -std=c++17 -D__OHOS__ \
-include $BC/libcxx_compat.h -I$BC \
-Wno-unused-parameter -Wno-missing-field-initializers -Wno-error"
CFLAGS_C="--target=$TARGET_TRIPLE --sysroot=$SR -I$SR/include/$TARGET_INCLUDE \
-fPIC -O2 -std=gnu11 -D__OHOS__ -I$BC \
-Wno-unused-parameter -Wno-missing-field-initializers -Wno-error"

SRCS="$ADAPTER/framework/appspawn-x/src/main.cpp \
$ADAPTER/framework/appspawn-x/src/appspawnx_runtime.cpp \
$ADAPTER/framework/appspawn-x/src/spawn_server.cpp \
$ADAPTER/framework/appspawn-x/src/child_main.cpp \
$ADAPTER/framework/appspawn-x/src/apk_verify_service.cpp \
$ADAPTER/framework/appspawn-x/tls_prefix/bionic_tls_prefix_reservation.cpp"

# Compile
# Build scratch is project-local by default so source, objects, logs and final
# evidence remain under the canonical WestLake workspace.  Generation builds
# still supply an isolated APPSPAWN_OBJ_DIR explicitly.
TMP="${APPSPAWN_OBJ_DIR:-$ADAPTER/out/.work/appspawnx_build}"
rm -rf "$TMP" && mkdir -p "$TMP"
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

echo ""
echo "  Compiled: $ok/$(( ok + fl ))"

if [ $ok -eq 0 ] || { [ "$STRICT_BUILD" = 1 ] && [ $fl -ne 0 ]; }; then
    echo "  ❌ Incomplete object set, refusing link"
    exit 1
fi

# BUILD.gn support closure is required in the standalone producer too. Keep it
# separate from the six core translation units so receipts expose both counts.
support_ok=0; support_fl=0

IDENTITY_DEFINES=""
for var in \
    WLAR_ADAPTER_BRIDGE_PATH WLAR_ADAPTER_BRIDGE_SONAME \
    WLAR_ADAPTER_BRIDGE_SHA256_HEX WLAR_ADAPTER_BRIDGE_BUILD_ID_HEX \
    WLAR_ANDROID_RUNTIME_PATH WLAR_ANDROID_RUNTIME_SONAME \
    WLAR_ANDROID_RUNTIME_SHA256_HEX WLAR_ANDROID_RUNTIME_BUILD_ID_HEX; do
    eval "value=\${$var:-}"
    if [ -n "$value" ]; then
        escaped=$(printf '%s' "$value" | sed 's/\\/\\\\/g; s/"/\\"/g')
        IDENTITY_DEFINES="$IDENTITY_DEFINES -D$var=\"$escaped\""
    fi
done

echo -n "  Compiling adapter_bridge_identity (support)... "
if $CXX $CFLAGS $INC $IDENTITY_DEFINES \
    -c -o "$TMP/adapter_bridge_identity.o" \
    "$ADAPTER/framework/appspawn-x/src/adapter_bridge_identity.cpp" \
    2>"$TMP/adapter_bridge_identity.err"; then
    echo "OK"
    support_ok=$((support_ok+1))
else
    echo "FAIL"
    head -5 "$TMP/adapter_bridge_identity.err" | sed 's/^/    /'
    support_fl=$((support_fl+1))
fi

echo -n "  Compiling jni_attach_admission (support)... "
if $CXX $CFLAGS $INC \
    -c -o "$TMP/jni_attach_admission.o" \
    "$JNI_ATTACH/src/jni_attach_admission.cpp" \
    2>"$TMP/jni_attach_admission.err"; then
    echo "OK"
    support_ok=$((support_ok+1))
else
    echo "FAIL"
    head -5 "$TMP/jni_attach_admission.err" | sed 's/^/    /'
    support_fl=$((support_fl+1))
fi

echo -n "  Compiling native_compat_prepare (support)... "
if $CXX $CFLAGS $INC \
    -c -o "$TMP/native_compat_prepare.o" \
    "$ADAPTER/framework/appspawn-x/src/native_compat_prepare.cpp" \
    2>"$TMP/native_compat_prepare.err"; then
    echo "OK"
    support_ok=$((support_ok+1))
else
    echo "FAIL"
    head -5 "$TMP/native_compat_prepare.err" | sed 's/^/    /'
    support_fl=$((support_fl+1))
fi

if [ "$TARGET_ARCH" = arm64 ]; then
    echo -n "  Compiling native_compat_prepare_owner_aarch64 (support)... "
    if $CC --target=$TARGET_TRIPLE --sysroot=$SR \
        -c -o "$TMP/native_compat_prepare_owner_aarch64.o" \
        "$ADAPTER/framework/appspawn-x/src/native_compat_prepare_owner_aarch64.S" \
        2>"$TMP/native_compat_prepare_owner_aarch64.err"; then
        echo "OK"
        support_ok=$((support_ok+1))
    else
        echo "FAIL"
        head -5 "$TMP/native_compat_prepare_owner_aarch64.err" | sed 's/^/    /'
        support_fl=$((support_fl+1))
    fi
fi

echo -n "  Compiling thread_template_publisher (support)... "
if $CC $CFLAGS_C $INC \
    -c -o "$TMP/thread_template_publisher.o" \
    "$THREAD_TEMPLATE_PUBLISHER/src/thread_template_publisher.c" \
    2>"$TMP/thread_template_publisher.err"; then
    echo "OK"
    support_ok=$((support_ok+1))
else
    echo "FAIL"
    head -5 "$TMP/thread_template_publisher.err" | sed 's/^/    /'
    support_fl=$((support_fl+1))
fi

for support_src in westlake_elf_identity westlake_sha256; do
    echo -n "  Compiling $support_src (support)... "
    if $CC $CFLAGS_C $INC \
        -c -o "$TMP/$support_src.o" "$PLUGIN/src/$support_src.c" \
        2>"$TMP/$support_src.err"; then
        echo "OK"
        support_ok=$((support_ok+1))
    else
        echo "FAIL"
        head -5 "$TMP/$support_src.err" | sed 's/^/    /'
        support_fl=$((support_fl+1))
    fi
done

echo "  Support: $support_ok/$(( support_ok + support_fl ))"
if [ "$STRICT_BUILD" = 1 ] && [ $support_fl -ne 0 ]; then
    echo "  ❌ Incomplete support object set, refusing link"
    exit 1
fi

# Link
echo -n "  Linking appspawn-x... "
OBJ=$(ls $TMP/*.o 2>/dev/null | tr '\n' ' ')
BUILTINS=${L03_A12_BUILTINS:-$OH/prebuilts/clang/ohos/linux-x86_64/llvm/lib/clang/15.0.4/lib/$BUILTINS_TRIPLE/libclang_rt.builtins.a}
[ -f "$THREAD_GUARD_REGISTRY_LIB_DIR/libwestlake_thread_guard_registry.so" ] || {
    echo "FAIL"
    echo "    missing registry provider: $THREAD_GUARD_REGISTRY_LIB_DIR/libwestlake_thread_guard_registry.so"
    exit 1
}
# Gap 5 fix 2026-04-11: link against real libart.so (in out/aosp_lib/) instead of
# libart_runtime_stubs.so. The stub had `JNI_CreateJavaVM` as a no-op; the real
# libart.so provides the actual ART VM bootstrap so the spawned app process can
# start a real JVM.
# RUNPATH: Enforcing mode prevents init from passing a long LD_LIBRARY_PATH to
# the service, and AT_SECURE strips it during domain transition. Bake the
# search path into appspawn-x itself so the linker can find ART/adapter libs
# without relying on the environment.
RPATH="-Wl,-rpath,/system/android/lib64 \
-Wl,-rpath,/system/lib64/chipset-sdk-sp \
-Wl,-rpath,/system/lib64 \
-Wl,-rpath,/system/lib64/platformsdk \
-Wl,-rpath,/system/lib64/chipset-sdk \
-Wl,-rpath,/system/lib64/ndk"

LIBS="-L$ML -L$SYS_LIB -L$SYS_LIB_SDK -L${AOSP_LIB_DIR:-$ADAPTER/out/aosp_lib} -L$THREAD_GUARD_REGISTRY_LIB_DIR -L$O $EXTRA_ARCH_LIB_PATHS \
$RPATH \
-Wl,--no-as-needed -lwestlake_thread_guard_registry -Wl,--as-needed \
-lc -ldl -lpthread \
-lhilog -lipc_core.z -lsamgr_proxy.z -lbegetutil.z -lselinux.z \
-lhap_restorecon.z \
-ltokensetproc_shared.z \
-lnativehelper -llog -lbionic_compat \
-Wl,--no-as-needed -llzma -Wl,--as-needed -lart \
$BUILTINS"

if [ "$STRICT_BUILD" = 1 ]; then
    LIBS="$LIBS -Wl,-z,defs -Wl,--no-allow-shlib-undefined -Wl,--build-id=sha1"
else
    LIBS="$LIBS -Wl,--allow-shlib-undefined"
fi

if $CXX --target=$TARGET_TRIPLE -B$ML $OBJ $LIBS -o "$O/appspawn-x" 2>"$TMP/link.err"; then
    echo "OK"
    sz=$(ls -lh $O/appspawn-x | awk '{print $5}')
    echo "  ✅ appspawn-x: $sz"
else
    echo "FAIL"
    head -5 $TMP/link.err | sed 's/^/    /'
    rm -f "$O/appspawn-x"
    exit 1
fi

if [ "$STRICT_BUILD" = 1 ]; then
    TOOL_DIR=$(cd "$(dirname "$CXX")" && pwd)
    READELF=${L03_A12_READELF:-$TOOL_DIR/llvm-readelf}
    NM=${L03_A12_NM:-$TOOL_DIR/llvm-nm}
    STRINGS=${L03_A12_STRINGS:-$TOOL_DIR/llvm-strings}
    for tool in "$READELF" "$NM" "$STRINGS"; do
        [ -x "$tool" ] || {
            echo "  ❌ Strict adapter-content audit tool missing: $tool"
            rm -f "$O/appspawn-x"
            exit 1
        }
    done

    "$READELF" -lW "$O/appspawn-x" >"$TMP/postlink.program-headers"
    "$READELF" -dW "$O/appspawn-x" >"$TMP/postlink.dynamic"
    "$NM" -C "$O/appspawn-x" >"$TMP/postlink.symbols"
    "$STRINGS" "$O/appspawn-x" >"$TMP/postlink.strings"

    audit_fail()
    {
        echo "  ❌ Strict adapter-content audit failed: $1"
        rm -f "$O/appspawn-x"
        exit 1
    }

    awk '$1 == "TLS" && $5 == "0x000030" && $6 == "0x000030" && \
         $7 == "R" && $8 == "0x10" {ok=1} END {exit !ok}' \
        "$TMP/postlink.program-headers" || audit_fail "exact PT_TLS contract"

    for needed in \
        libwestlake_thread_guard_registry.so libnativehelper.so libart.so; do
        grep -Fq "Shared library: [$needed]" "$TMP/postlink.dynamic" || \
            audit_fail "missing DT_NEEDED $needed"
    done

    for symbol in \
        'AppSpawnXRuntime::startVm()' \
        'LoadVerifiedAdapterBridge' \
        'ScopedJniAttachment::ScopedJniAttachment' \
        'westlake_native_compat_prepare_main_thread' \
        'WestLakeNativeCompatReservationBase' \
        'WLTP_PublishMainThreadTemplate' \
        'wltp_publisher_contract_v1' \
        'westlake_bionic_tls_slots_2_7_reservation'; do
        grep -Fq "$symbol" "$TMP/postlink.symbols" || \
            audit_fail "missing adapter symbol $symbol"
    done

    for var in \
        WLAR_ADAPTER_BRIDGE_PATH WLAR_ADAPTER_BRIDGE_SHA256_HEX \
        WLAR_ADAPTER_BRIDGE_BUILD_ID_HEX WLAR_ANDROID_RUNTIME_PATH \
        WLAR_ANDROID_RUNTIME_SHA256_HEX WLAR_ANDROID_RUNTIME_BUILD_ID_HEX; do
        eval "value=\${$var:-}"
        grep -Fxq "$value" "$TMP/postlink.strings" || \
            audit_fail "missing Route-A identity bytes $var"
    done
    echo "  ✅ Strict adapter-content audit: PASS"
fi

echo ""
ls -lh $O/appspawn-x 2>/dev/null
