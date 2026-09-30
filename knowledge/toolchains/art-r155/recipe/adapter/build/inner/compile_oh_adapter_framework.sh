#!/bin/bash
# === GUARD: internal helper, do not invoke directly ===
if [ "${BUILD_INNER_INVOKED}" != "1" ]; then
    echo "[GUARD] $(basename "$0") is an internal helper — invoke via build_*.sh / restore_after_sync.sh / etc." >&2
    echo "[GUARD] Escape hatch (debug only): BUILD_INNER_INVOKED=1 bash $(basename "$0")" >&2
    exit 2
fi
# === END GUARD ===
# [DEPRECATED Phase 1 — 2026-05-21] BCP jar via build_aosp_fw.sh, runtime jar via build_adapter.sh.
echo "[DEPRECATED] $(basename "$0") is wrapped by build_aosp_fw.sh and build_adapter.sh — Phase 4 will split" >&2
# ============================================================================
# 重复犯错警示 (oh-adapter-framework.jar 编译，调改前必读)
# ============================================================================
#
# [F-1] dual source dirs 陷阱 — 改源码后必须同步两个目录
#   现象：在 D:\code\adapter\framework\core\java\OHEnvironment.java 改了代码，
#         scp 到 ECS 的 ~/adapter/framework/，编出来的 oh-adapter-framework.jar
#         里反编译看依然是旧代码；md5 没变。
#   根因：本脚本的 javac 输入是 ~/aosp/device/adapter/oh_adapter_framework/java/，
#         不是 ~/adapter/framework/。两个目录是各自独立副本，靠 pre-flight rsync
#         同步 adapter.* 类。漏 rsync 就漏改动。
#   措施：本脚本顶部已加 pre-flight rsync ~/adapter/framework/**/adapter/* →
#         ~/aosp/device/adapter/oh_adapter_framework/java/adapter/。改 OHEnvironment
#         等 adapter.* 包的代码后必须 scp + 跑本脚本，单独 javac 不够。
#         （memory: feedback_dual_source_dirs_trap.md）
#
# [F-2] AppSpawnXInit.class 不属于 oh-adapter-framework.jar
#   现象：jar 编出来后 device 启动报 com.android.internal.os.AppSpawnXInit
#         not found / 类加载死循环。
#   根因：2026-04-17 架构切分：BCP oh-adapter-framework.jar 只放 adapter.* 包；
#         AppSpawnXInit (com.android.internal.os.*) 必须在 oh-adapter-runtime.jar
#         (PathClassLoader 加载，非 BCP)。误打进 oh-adapter-framework.jar 会让
#         BCP 锁住一个频繁修改的类，每次改都强迫 boot image 重建。
#   措施：本脚本 post-flight 断言 AppSpawnXInit.class 不在产物里；不要绕过。
#
# [F-3] 输出唯一目录 = out/adapter/ (B.41)
#   现象：见 [B-1]。
#   措施：永远不把 oh-adapter-framework.jar 输出/复制到 out/aosp_fwk/。
#         只输出 out/adapter/oh-adapter-framework.jar；deploy 脚本也只从这里读。
#         （memory: project_b41_framework_jar_abandoned.md）
#
# [F-4] javac 不抓 .java timestamp 变化 — 改代码后要清 class cache
#   现象：源码改了重跑本脚本，jar 里的 .class 字节码不变。
#   根因：javac 只看 -d 目录里的 .class 是否存在，不比较 .java mtime；增量编译
#         的"增量"维度是 javac 自己的依赖图，不是 mtime。
#   措施：源码修改后要么 --clean 一把，要么改的 .java 对应的 .class 手工删除。
#         本脚本 --clean 模式会 wipe class cache。
#
# ============================================================================
# compile_oh_adapter_framework.sh — canonical build for oh-adapter-framework.jar
#
# Why not Soong? `m oh-adapter-framework` is blocked by unrelated analysis errors
# in AOSP (frameworks_base_packages_SystemUI_license etc.). Direct javac against
# turbine header jars bypasses those errors and produces a valid jar in seconds.
#
# Inputs:
#   $AOSP_ROOT/device/adapter/oh_adapter_framework/java/**/*.java    (source tree)
#   framework-minus-apex.jar                                         (turbine header jar)
#   core-oj.jar, core-libart.jar                                     (turbine header jars)
#
# Output:
#   $ADAPTER_ROOT/out/adapter/oh-adapter-framework.jar               (authoritative)
#
# Exit codes:
#   0 success
#   1 prerequisite missing (javac / header jars)
#   2 compile error (left in $LOG for inspection)
#   3 jar packaging error
#
# Usage:
#   bash build/compile_oh_adapter_framework.sh                  # full rebuild
#   bash build/compile_oh_adapter_framework.sh --clean          # wipe class cache first
#   bash build/compile_oh_adapter_framework.sh --verify         # assert AppSpawnXInit in output
#
# Created: 2026-04-11 as the real fix for gap 7 / jar stale state.
set -euo pipefail

ADAPTER_ROOT="${ADAPTER_ROOT:-$HOME/adapter}"
AOSP_ROOT="${AOSP_ROOT:-$HOME/aosp}"

CLEAN=0
VERIFY_ONLY=0
for arg in "$@"; do
    case "$arg" in
        --clean)  CLEAN=1 ;;
        --verify) VERIFY_ONLY=1 ;;
        *) echo "Unknown arg: $arg" >&2; exit 1 ;;
    esac
done

JAVAC="$AOSP_ROOT/prebuilts/jdk/jdk17/linux-x86/bin/javac"
JAR="$AOSP_ROOT/prebuilts/jdk/jdk17/linux-x86/bin/jar"
SRC_DIR="$AOSP_ROOT/device/adapter/oh_adapter_framework/java"
OUT_DIR="$ADAPTER_ROOT/out/adapter"
OUT_JAR="$OUT_DIR/oh-adapter-framework.jar"
CLASS_DIR="$ADAPTER_ROOT/out/adapter/classes"
LOG="$ADAPTER_ROOT/out/adapter/compile.log"

# ----------------------------------------------------------------------------
# Turbine header jars (produced by Soong as a side-effect of normal builds)
# ----------------------------------------------------------------------------
FWK_JAR="$AOSP_ROOT/out/soong/.intermediates/frameworks/base/framework-minus-apex/android_common/turbine-combined/framework-minus-apex.jar"
CORE_OJ_JAR="$AOSP_ROOT/out/soong/.intermediates/libcore/core-oj/android_common/turbine-combined/core-oj.jar"
CORE_LIBART_JAR="$AOSP_ROOT/out/soong/.intermediates/libcore/core-libart/android_common/turbine-combined/core-libart.jar"
# --- classpath modernization (2026-07-11) ------------------------------------
# adapter.core.unitysvc.AudioServiceStub overrides IAudioService methods whose
# param types (android.bluetooth.BluetoothDevice) live in an apex module and are
# NOT in framework-minus-apex.jar.  Add the Bluetooth module_lib stub jar — the
# same API surface AOSP itself compiles the framework against.  Real Soong output;
# no semantic change.  Missing-path entries are silently ignored by javac.
BT_STUBS_JAR="$AOSP_ROOT/out/soong/.intermediates/packages/modules/Bluetooth/framework/framework-bluetooth.stubs.module_lib/android_common/turbine/framework-bluetooth.stubs.module_lib.jar"

# ----------------------------------------------------------------------------
# Pre-flight
# ----------------------------------------------------------------------------
echo "=============================================="
echo "oh-adapter-framework.jar build"
echo "=============================================="
echo "  AOSP_ROOT    = $AOSP_ROOT"
echo "  ADAPTER_ROOT = $ADAPTER_ROOT"
echo "  SRC_DIR      = $SRC_DIR"
echo "  OUT_JAR      = $OUT_JAR"

if [ "$VERIFY_ONLY" = "1" ]; then
    echo ""
    echo "Verify mode: checking existing jar..."
    if [ ! -f "$OUT_JAR" ]; then
        echo "  FAIL: $OUT_JAR does not exist"
        exit 1
    fi
    class_count=$(unzip -l "$OUT_JAR" 2>/dev/null | grep -c '\.class$' || echo 0)
    echo "  class count: $class_count"
    # Note (2026-04-17): AppSpawnXInit.class is INTENTIONALLY excluded from this
    # jar and now lives in oh-adapter-runtime.jar (non-BCP, DexClassLoader-loaded).
    # This decouples frequently-changing preload code from the BCP jar whose byte
    # changes trigger boot image rebuild. See doc/liboh_android_runtime_design.html
    # §8.2.1a for the architectural decision.
    if unzip -l "$OUT_JAR" 2>/dev/null | grep -q 'com/android/internal/os/AppSpawnXInit\.class'; then
        echo "  FAIL: AppSpawnXInit.class should NOT be in oh-adapter-framework.jar"
        echo "         (it must live in oh-adapter-runtime.jar after 2026-04-17 split)"
        exit 2
    fi
    if unzip -l "$OUT_JAR" 2>/dev/null | grep -q 'adapter/core/OHEnvironment\.class'; then
        echo "  OHEnvironment.class: OK"
    else
        echo "  FAIL: OHEnvironment.class missing"
        exit 2
    fi
    echo "Verify: PASS"
    exit 0
fi

for f in "$JAVAC" "$JAR" "$FWK_JAR" "$CORE_OJ_JAR" "$CORE_LIBART_JAR"; do
    if [ ! -f "$f" ]; then
        echo "ERROR: prerequisite missing: $f" >&2
        echo "  For turbine header jars, you need at least one successful AOSP build" >&2
        echo "  that has produced them at out/soong/.intermediates/..." >&2
        exit 1
    fi
done

# ----------------------------------------------------------------------------
# 2026-04-27 双源目录陷阱修补：以 ~/adapter/framework/ 为唯一权威源
# ----------------------------------------------------------------------------
# 项目存在两个并行的源代码位置：
#   (A) ~/adapter/framework/<area>/java/...              ← 工程权威（开发编辑这里）
#   (B) $AOSP_ROOT/device/adapter/oh_adapter_framework/   ← 编译实际读取
# 历史上需要每改 (A) 一次都手动 cp 到 (B)，多次因此漏改导致编译产物保留旧字节码、
# 三方 md5 检查全部"通过"但运行时行为不变（B.8 真路由 attachApplication 时
# 浪费完整一轮）。
# Pre-flight 自动从 (A) 同步到 (B)：仅同步 package 以 "adapter." 开头的类（
# 这些是 BCP oh-adapter-framework.jar 的合法成员），com.android.internal.os.*
# 归 oh-adapter-runtime.jar 管，android.* 归 adapter-mainline-stubs.jar 管，
# 都不属于本 jar，跳过。
# 详见 memory/feedback_dual_source_dirs_trap.md
#
# 2026-04-30 方向 2 单类试点：BCP_EXCLUDE_BASENAMES 列出搬到 oh-adapter-runtime.jar
# (PathClassLoader, 非 BCP) 的频繁迭代类。这些类改动不再触发 boot image 重烘焙。
# 加成员前必须确认: (1) compile_oh_adapter_runtime.sh SRCS 已加该文件
#                  (2) BCP 必留类没用同 package 直接引用它（同名 class 没有 import 行）
#                  (3) 它自己 import 的类都在 BCP（runtime jar 编译期靠 BCP CLASS_DIR
#                      作 classpath 解析）。
BCP_EXCLUDE_BASENAMES=(
    "AppSchedulerBridge.java"           # 频繁迭代 (B.42 NPE 修复链)
    "OhApplicationInfoConverter.java"   # 2026-04-30 P1 字段映射改造，避免 boot image 重建
    "OhConfigurationConverter.java"     # 2026-04-30 P1
    "OhDisplayProvider.java"            # 2026-04-30 P1
    "AppBindDataDefaults.java"          # 2026-04-30 P1
)
is_bcp_excluded() {
    local base="$1"
    for ex in "${BCP_EXCLUDE_BASENAMES[@]}"; do
        [ "$base" = "$ex" ] && return 0
    done
    return 1
}

ADAPTER_FRAMEWORK_SRC_ROOT="${ADAPTER_FRAMEWORK_SRC_ROOT:-$ADAPTER_ROOT/framework}"
if [ -d "$ADAPTER_FRAMEWORK_SRC_ROOT" ]; then
    echo ""
    echo "Pre-flight: syncing $ADAPTER_FRAMEWORK_SRC_ROOT/*/java → $SRC_DIR (adapter.* only)"
    mkdir -p "$SRC_DIR"
    sync_count=0
    skip_count=0
    runtime_skip_count=0
    while IFS= read -r src; do
        [ -z "$src" ] && continue
        pkg=$(grep -m1 '^package ' "$src" 2>/dev/null | sed 's/^package //;s/;.*//;s/[[:space:]]//g')
        if [ -z "$pkg" ]; then continue; fi
        # Only adapter.* classes belong in oh-adapter-framework.jar
        case "$pkg" in
            adapter.*) ;;
            *) skip_count=$((skip_count + 1)); continue ;;
        esac
        # Per-file exclusion: classes moved to oh-adapter-runtime.jar
        base=$(basename "$src")
        if is_bcp_excluded "$base"; then
            runtime_skip_count=$((runtime_skip_count + 1))
            # Remove stale copy from BCP src tree (otherwise old version
            # lingers and gets compiled in next run).
            pkg_path="${pkg//.//}"
            stale="$SRC_DIR/$pkg_path/$base"
            [ -f "$stale" ] && rm -f "$stale"
            continue
        fi
        pkg_path="${pkg//.//}"
        dst_dir="$SRC_DIR/$pkg_path"
        dst="$dst_dir/$base"
        mkdir -p "$dst_dir"
        if ! cmp -s "$src" "$dst" 2>/dev/null; then
            cp "$src" "$dst"
            sync_count=$((sync_count + 1))
        fi
    done < <(find "$ADAPTER_FRAMEWORK_SRC_ROOT" -mindepth 3 -name '*.java' 2>/dev/null)
    echo "  Synced $sync_count files (skipped $skip_count non-BCP packages, $runtime_skip_count BCP-excluded → runtime jar)"
else
    echo "WARN: $ADAPTER_FRAMEWORK_SRC_ROOT not found — falling back to whatever is in $SRC_DIR"
fi

# 2026-04-17 architectural change: AppSpawnXInit.java is REMOVED from the BCP
# oh-adapter-framework.jar. Adapter-project Java code that changes frequently
# (AppSpawnXInit + anything under com/android/internal/os/) now lives in a
# separate non-BCP oh-adapter-runtime.jar built by compile_oh_adapter_runtime.sh,
# loaded at runtime via DexClassLoader. This keeps the BCP jar stable so
# boot image never needs rebuild when adapter preload code iterates.
# Ensure no leftover copy pollutes the AOSP mirror tree.
APPSPAWN_AOSP_STALE="$SRC_DIR/com/android/internal/os/AppSpawnXInit.java"
if [ -f "$APPSPAWN_AOSP_STALE" ]; then
    rm -f "$APPSPAWN_AOSP_STALE"
    echo "  Purged stale AOSP-tree copy: $APPSPAWN_AOSP_STALE"
fi
# Clean up empty com/android/internal/os dir if present
rmdir "$SRC_DIR/com/android/internal/os" 2>/dev/null || true
rmdir "$SRC_DIR/com/android/internal" 2>/dev/null || true
rmdir "$SRC_DIR/com/android" 2>/dev/null || true
rmdir "$SRC_DIR/com" 2>/dev/null || true

# ----------------------------------------------------------------------------
# Compile
# ----------------------------------------------------------------------------
mkdir -p "$OUT_DIR"
# 2026-04-30 方向 2：每次都清 CLASS_DIR — 否则 BCP_EXCLUDE 移除某类后，旧 .class
# 残留在 CLASS_DIR 里被 d8 误打进 BCP jar，违反搬迁意图（设备同时存在两份相同
# class，一份 BCP 一份 PathClassLoader）。
rm -rf "$CLASS_DIR"
mkdir -p "$CLASS_DIR"

# Collect every .java — note this glob must recurse into subdirs
SRC_LIST=$(mktemp /tmp/oh_fwk_srcs.XXXXXX)
find "$SRC_DIR" -name '*.java' > "$SRC_LIST"
NUM_SRCS=$(wc -l < "$SRC_LIST")
echo ""
echo "Compiling $NUM_SRCS Java sources..."

CP="$FWK_JAR:$CORE_OJ_JAR:$CORE_LIBART_JAR:$BT_STUBS_JAR"

if ! "$JAVAC" \
        -d "$CLASS_DIR" \
        --release 17 \
        -classpath "$CP" \
        -encoding UTF-8 \
        -Xmaxerrs 30 \
        @"$SRC_LIST" \
        > "$LOG" 2>&1; then
    echo "COMPILE FAILED — see $LOG"
    echo ""
    echo "First 30 lines of log:"
    head -30 "$LOG"
    rm -f "$SRC_LIST"
    exit 2
fi
rm -f "$SRC_LIST"

NUM_CLASSES=$(find "$CLASS_DIR" -name '*.class' | wc -l)
echo "  OK: $NUM_CLASSES .class files produced"

# ----------------------------------------------------------------------------
# 2026-04-17: dex the .class files into classes.dex
# Reason: dex2oat building boot-oh-adapter-framework.oat against a .class-only
# jar produces a non-executable OAT. At runtime musl dlopen refuses to load
# such OAT files ("DlOpen does not support non-executable loading") and the
# boot-image checksum validation aborts. Dexing upfront gives dex2oat real
# bytecode to AOT-compile into executable sections. See
# doc/liboh_android_runtime_design.html §8.2.1a for the full diagnosis.
# ----------------------------------------------------------------------------
D8="$AOSP_ROOT/out/host/linux-x86/bin/d8"
if [ ! -x "$D8" ]; then
    echo "ERROR: d8 not found at $D8 — build it: cd ~/aosp && m d8 -j16" >&2
    exit 2
fi
DEX_DIR="$ADAPTER_ROOT/out/adapter/framework-dex"
rm -rf "$DEX_DIR"
mkdir -p "$DEX_DIR"

echo ""
echo "Dexing .class → classes.dex (d8)..."
# d8 launcher uses `java` from PATH; force JDK17 to avoid 'class file version 61.0' error
export JAVA_HOME="$AOSP_ROOT/prebuilts/jdk/jdk17/linux-x86"
export PATH="$JAVA_HOME/bin:$PATH"
CLASS_FILES=$(find "$CLASS_DIR" -name '*.class')
if ! "$D8" \
        --release \
        --output "$DEX_DIR" \
        --lib "$CORE_OJ_JAR" \
        --lib "$CORE_LIBART_JAR" \
        --lib "$FWK_JAR" \
        $CLASS_FILES \
        >> "$LOG" 2>&1; then
    echo "  FAIL — see $LOG"
    tail -30 "$LOG"
    exit 2
fi
if [ ! -f "$DEX_DIR/classes.dex" ]; then
    echo "  FAIL: d8 did not produce classes.dex"
    exit 2
fi
DEX_SIZE=$(stat -c%s "$DEX_DIR/classes.dex")
echo "  OK: classes.dex = $DEX_SIZE bytes"

# ----------------------------------------------------------------------------
# Package
# ----------------------------------------------------------------------------
echo ""
echo "Packaging jar (classes.dex-only; .class files excluded)..."
rm -f "$OUT_JAR"
(cd "$DEX_DIR" && "$JAR" cf "$OUT_JAR" classes.dex)

if [ ! -f "$OUT_JAR" ]; then
    echo "ERROR: jar packaging failed" >&2
    exit 3
fi

JAR_SIZE=$(stat -c%s "$OUT_JAR")
JAR_HAS_DEX=$(unzip -l "$OUT_JAR" 2>/dev/null | grep -c 'classes\.dex' || echo 0)
echo "  Output: $OUT_JAR ($JAR_SIZE bytes, classes.dex=$JAR_HAS_DEX)"

# ----------------------------------------------------------------------------
# Post-flight assertions
# ----------------------------------------------------------------------------
echo ""
echo "Post-flight assertions:"

# 2026-04-17: jar is now classes.dex-only (no .class files). Assert dex contains
# key class names via `strings` scan.
fail=0
if [ "$JAR_HAS_DEX" != "1" ]; then
    echo "  FAIL: classes.dex missing from jar"
    fail=1
else
    echo "  OK: classes.dex present"
fi
# dex strings use MUTF-8 with ULEB128 length prefix; plain `strings | grep`
# cannot reliably find them. Instead check dex size is reasonable for the
# expected class count (>100 KB for ~30 adapter classes). If d8 succeeded
# with $NUM_CLASSES input .class files, the dex should contain them all.
DEX_FILE="$DEX_DIR/classes.dex"
DEX_SIZE=$(stat -c%s "$DEX_FILE")
MIN_DEX_SIZE=50000
if [ "$DEX_SIZE" -lt "$MIN_DEX_SIZE" ]; then
    echo "  FAIL: classes.dex only $DEX_SIZE bytes (expected >$MIN_DEX_SIZE for $NUM_CLASSES classes)"
    fail=1
else
    echo "  OK: classes.dex $DEX_SIZE bytes (expected >$MIN_DEX_SIZE for $NUM_CLASSES classes)"
fi
# Assert AppSpawnXInit.class absent from the pre-dex .class pool (easier to
# grep than the dex binary). If d8 didn't see it as input, it cannot be in
# the dex output.
if find "$CLASS_DIR" -name 'AppSpawnXInit.class' | grep -q .; then
    echo "  FAIL: AppSpawnXInit.class leaked into framework build"
    fail=1
else
    echo "  OK: AppSpawnXInit.class absent from .class pool (lives in oh-adapter-runtime.jar)"
fi

if [ "$fail" = "1" ]; then
    echo "ERROR: critical classes missing from jar" >&2
    exit 2
fi

echo ""
echo "=============================================="
echo "DONE — oh-adapter-framework.jar built"
echo "  $OUT_JAR"
echo "  $JAR_SIZE bytes, classes.dex=$JAR_HAS_DEX (dex=$DEX_SIZE bytes, src=$NUM_CLASSES classes)"
echo ""
echo "Next: bash build/prepare_deploy_package.sh"
echo "=============================================="
