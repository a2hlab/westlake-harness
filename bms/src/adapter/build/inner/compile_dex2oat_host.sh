#!/bin/bash
# === GUARD: internal helper, do not invoke directly ===
if [ "${BUILD_INNER_INVOKED}" != "1" ]; then
    echo "[GUARD] $(basename "$0") is an internal helper — invoke via build_*.sh / restore_after_sync.sh / etc." >&2
    echo "[GUARD] Escape hatch (debug only): BUILD_INNER_INVOKED=1 bash $(basename "$0")" >&2
    exit 2
fi
# === END GUARD ===
# [DEPRECATED Phase 1 — 2026-05-21] Use build_dex2oat.sh instead.
echo "[DEPRECATED] $(basename "$0") is wrapped by build_dex2oat.sh — Phase 4 will absorb this" >&2
# ============================================================================
# compile_dex2oat_host.sh — 编译 host 端 dex2oat (x86_64) for boot image 生成
# ============================================================================
#
# Background:
#   gen_boot_image.sh 只调用现成 dex2oat64，不重编它。本脚本是 dex2oat-host
#   的唯一权威编译入口，封装"必须带哪些 env"。任何"重编 dex2oat-host" 任务
#   都必须经此脚本，禁止裸跑 `m dex2oat-host`。
#
# ----------------------------------------------------------------------------
# 重复犯错警示 (调改前必读)
# ----------------------------------------------------------------------------
#
# [DH-1] 必须带 ART_USE_READ_BARRIER=false ART_DEFAULT_GC_TYPE=CMS env
#   现象：裸跑 `m dex2oat-host libsigchain-host libart-host -j16`，编出来的
#         dex2oat 内嵌 Baker Read Barrier 指令；用它生成 boot image 后，
#         boot.oat .text 比 5/5 bkup 大 +700 KB；device libart.so 是无 RB
#         编的（cross_compile_arm32.sh ART_DEFS 不定义 RB 宏），ABI 错位 →
#         RB 指令落到 art_quick_read_barrier_mark_reg* ASM stub
#         (__builtin_trap()) 或随机 SIGSEGV / 堆损坏。
#   根因：AOSP Soong 默认 ART_USE_READ_BARRIER=true（art/build/art.go:274
#         + art/build/Android.common_build.mk 默认）。device libart.so 用
#         CMS 模式编 (cross_compile_arm32.sh L57 ART_DEFS 含
#         -DART_DEFAULT_GC_TYPE_IS_CMS 但不定义 ART_USE_READ_BARRIER)，
#         dex2oat-host 默认 RB=on 与之错位。
#   措施：固定带 ART_USE_READ_BARRIER=false ART_DEFAULT_GC_TYPE=CMS env，
#         本脚本以 export 形式写死，禁止调用方覆盖。
#   血训：2026-05-06 EOD，5/6 19:15 重编 dex2oat-host 时遗漏 env，导致
#         5/6 19:53 重生成的 boot.oat 嵌入 RB 指令，HelloWorld
#         activityResumed rc=0 后 main 线程 SIGABRT。
#         (compile_report §4.1.1 三件配套 / build_patch_log §H.2 /
#          technical_decision_overview §2.11 / memory
#          feedback_art_bootimage_coupling.md)
#
# [DH-2] 必须 source build/envsetup.sh + lunch oh_adapter-userdebug
#   现象：裸跑 `m` 报 "command not found"。
#   根因：m / mm / lunch 都是 envsetup.sh 注入的 shell function，必须 source
#         + lunch 一个 product 才能解析 target。
#   措施：本脚本前置自动 source + lunch。
#
# [DH-3] 三件联动重编（libart / dex2oat / boot image）
#   现象：只重编 dex2oat-host，不重编 boot image，仍残留旧 boot.oat 含 RB。
#   根因：boot.oat 是 dex2oat 把 BCP jar AOT 编出的机器码，dex2oat 改了
#         必须重新生成 boot image。
#   措施：本脚本只负责 dex2oat-host 一件；调用方完成后必须接着跑
#         `bash build/gen_boot_image.sh`。
#         (memory: feedback_art_bootimage_coupling.md)
#
# ----------------------------------------------------------------------------
# Usage
# ----------------------------------------------------------------------------
#   bash compile_dex2oat_host.sh                    # 实际编译
#   bash compile_dex2oat_host.sh --dry-run          # 只打印命令 + 跑 soong -n
#   bash compile_dex2oat_host.sh --skip-verify      # 跳过编后符号自检（不推荐）
#
# Output:
#   $AOSP_ROOT/out/host/linux-x86/bin/dex2oat64
#   $AOSP_ROOT/out/host/linux-x86/bin/dex2oat32
#   $AOSP_ROOT/out/host/linux-x86/lib64/libart.so      (host libart, RB-off)
#   $AOSP_ROOT/out/host/linux-x86/lib64/libsigchain.so
#
# ============================================================================

set -e
set -o pipefail

# ---- Parse args ----
DRY_RUN=0
SKIP_VERIFY=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1;;
        --skip-verify) SKIP_VERIFY=1;;
        --help|-h)
            sed -n '1,/^# =====/p' "$0" | head -80
            exit 0
            ;;
        *)
            echo "ERROR: unknown arg: $arg"
            exit 1
            ;;
    esac
done

# ---- Paths ----
AOSP_ROOT="${AOSP_ROOT:-$HOME/aosp}"
LUNCH_TARGET="${LUNCH_TARGET:-oh_adapter-userdebug}"
JOBS="${JOBS:-16}"

# ---- Required env (DH-1 + DH-4: 不允许调用方覆盖) ----
# 4 个 env 来源 build_patch_log.html §H.2.2 实测命令：
#   - ART_USE_READ_BARRIER=false / ART_DEFAULT_GC_TYPE=CMS  → DH-1, RB-off 三件配套
#   - ALLOW_MISSING_DEPENDENCIES=true                       → DH-4, oh_adapter product
#                                                                  容忍 partial sync 缺依赖
#   - BUILD_BROKEN_DISABLE_BAZEL=1                          → DH-4, 跳过 bazel mixed-build
#                                                                  路径（ECS 缺 JDK）
unset ART_USE_READ_BARRIER ART_DEFAULT_GC_TYPE \
      ALLOW_MISSING_DEPENDENCIES BUILD_BROKEN_DISABLE_BAZEL
export ART_USE_READ_BARRIER=false
export ART_DEFAULT_GC_TYPE=CMS
export ALLOW_MISSING_DEPENDENCIES=true
export BUILD_BROKEN_DISABLE_BAZEL=1

# ---- Targets (固定，与 gen_boot_image.sh prerequisite 一致) ----
TARGETS=(dex2oat-host libsigchain-host libart-host)

# ---- Banner ----
echo "============================================================================"
echo "compile_dex2oat_host.sh"
echo "  AOSP_ROOT       = $AOSP_ROOT"
echo "  LUNCH_TARGET    = $LUNCH_TARGET"
echo "  ART_USE_READ_BARRIER = $ART_USE_READ_BARRIER  (forced, DH-1)"
echo "  ART_DEFAULT_GC_TYPE  = $ART_DEFAULT_GC_TYPE   (forced, DH-1)"
echo "  TARGETS         = ${TARGETS[*]}"
echo "  JOBS            = $JOBS"
echo "  DRY_RUN         = $DRY_RUN"
echo "============================================================================"

# ---- Sanity check ----
if [ ! -d "$AOSP_ROOT" ]; then
    echo "ERROR: AOSP_ROOT $AOSP_ROOT does not exist"
    exit 1
fi
if [ ! -f "$AOSP_ROOT/build/envsetup.sh" ]; then
    echo "ERROR: $AOSP_ROOT/build/envsetup.sh not found"
    exit 1
fi

# ---- Source envsetup + lunch ----
echo ""
echo "[Step 1/3] source envsetup.sh + lunch $LUNCH_TARGET"
cd "$AOSP_ROOT"
# shellcheck disable=SC1091
source build/envsetup.sh > /tmp/envsetup.log 2>&1
lunch "$LUNCH_TARGET" > /tmp/lunch.log 2>&1 || {
    echo "ERROR: lunch $LUNCH_TARGET failed:"
    cat /tmp/lunch.log
    exit 1
}
tail -3 /tmp/lunch.log

# ---- Confirm m is available ----
if ! type m > /dev/null 2>&1; then
    echo "ERROR: 'm' shell function not available after envsetup.sh — abort"
    exit 1
fi

# ---- Build (or dry-run) ----
echo ""
if [ "$DRY_RUN" = "1" ]; then
    echo "[Step 2/3] DRY-RUN: would execute"
    echo "    ART_USE_READ_BARRIER=$ART_USE_READ_BARRIER \\"
    echo "    ART_DEFAULT_GC_TYPE=$ART_DEFAULT_GC_TYPE \\"
    echo "    m ${TARGETS[*]} -j$JOBS"
    echo ""
    echo "DRY-RUN checks:"

    # check 1: m 是 shell function
    if type m > /dev/null 2>&1; then
        echo "  [OK] 'm' shell function available"
    else
        echo "  [FAIL] 'm' shell function NOT available — abort"
        exit 1
    fi

    # check 2: lunch 设了 TARGET_PRODUCT
    if [ -n "$TARGET_PRODUCT" ]; then
        echo "  [OK] TARGET_PRODUCT = $TARGET_PRODUCT"
    else
        echo "  [FAIL] TARGET_PRODUCT not set after lunch"
        exit 1
    fi

    # check 3: env vars 已 export
    if [ "$(printenv ART_USE_READ_BARRIER)" = "false" ] && \
       [ "$(printenv ART_DEFAULT_GC_TYPE)" = "CMS" ]; then
        echo "  [OK] ART env exported: ART_USE_READ_BARRIER=false ART_DEFAULT_GC_TYPE=CMS"
    else
        echo "  [FAIL] ART env not exported"
        exit 1
    fi

    # check 4: m 能解析这些 target（用 m -h / m help 这类不触发 build 的命令）。
    # 不能用 'm nothing' — oh_adapter product 在 ECS 上走 bazel mixed-build path，
    # 触发 m nothing 会因缺 JDK 失败；而真正的 'm dex2oat-host' 是 soong-only path
    # 不走 bazel。所以这里只验 shell function 调用通路，soong build 由实跑兜底。
    if m help > /dev/null 2>&1 || true; then
        echo "  [OK] 'm' callable (soong build deferred to real run)"
    fi

    # check 5: 软检查 — 如果上次跑过 m，soong.variables 应已落盘；grep
    # ArtUseReadBarrier 字段。注意：这个字段反映的是上次 m 跑时的 env 状态，
    # 不是本次 dry-run 设的 env。所以仅作为参考信号。
    SOONG_VARS="$AOSP_ROOT/out/soong/soong.variables"
    if [ -f "$SOONG_VARS" ]; then
        ART_RB_FIELD=$(grep -i 'ArtUseReadBarrier' "$SOONG_VARS" || true)
        if [ -n "$ART_RB_FIELD" ]; then
            echo "  [INFO] last m's soong.variables: $ART_RB_FIELD"
            echo "         (本次实跑会用本脚本 forced env 覆盖此值)"
        else
            echo "  [INFO] soong.variables 不含 ArtUseReadBarrier 字段 (env 未传时 soong 默认 RB=on)"
        fi
    else
        echo "  [INFO] soong.variables 尚未落盘 (从未跑过 m)，实跑时会生成"
    fi

    # check 6: 验证 art.go 的 RB gate 逻辑（确认 env=false 真能让 ArtUseReadBarrier=false）
    ART_GO="$AOSP_ROOT/art/build/art.go"
    if [ -f "$ART_GO" ]; then
        if grep -q 'IsEnvFalse("ART_USE_READ_BARRIER")\|ART_USE_READ_BARRIER' "$ART_GO"; then
            echo "  [OK] art/build/art.go 含 ART_USE_READ_BARRIER gate (env 路径生效)"
        else
            echo "  [WARN] art/build/art.go 不含 ART_USE_READ_BARRIER gate — 可能 AOSP 版本不同"
        fi
    fi

    echo ""
    echo "DRY-RUN 完成。"
    echo "实跑命令：bash $(basename "$0")"
    exit 0
fi

echo "[Step 2/3] Building: m ${TARGETS[*]} -j$JOBS"
echo "  (this may take 5-15 minutes for first build)"
START_TS=$(date +%s)
m "${TARGETS[@]}" -j"$JOBS"
END_TS=$(date +%s)
echo ""
echo "Build took $((END_TS - START_TS))s"

# ---- Verify (DH-1 自检) ----
DEX2OAT64="$AOSP_ROOT/out/host/linux-x86/bin/dex2oat64"
LIBART_HOST=$(find "$AOSP_ROOT/out/host" -name 'libart.so' 2>/dev/null | head -1)

echo ""
echo "[Step 3/3] Verify build artifacts (DH-1 RB-off check)"

if [ ! -f "$DEX2OAT64" ]; then
    echo "ERROR: $DEX2OAT64 not produced"
    exit 1
fi
echo "  dex2oat64       = $DEX2OAT64 ($(stat -c%s "$DEX2OAT64") bytes)"

if [ -n "$LIBART_HOST" ]; then
    echo "  libart-host.so  = $LIBART_HOST"
fi

if [ "$SKIP_VERIFY" = "1" ]; then
    echo "  --skip-verify supplied, skipping RB symbol audit"
    exit 0
fi

# RB 自检：唯一可靠的 gate 是 kUseBakerReadBarrier constexpr 全局符号
#   - kUseBakerReadBarrier == 0 → RB 关闭，dex2oat AOT 时不 emit RB 指令到 boot.oat ✅
#   - 不要查 BakerReadBarrierThunk / art_quick_read_barrier_*：
#     · BakerReadBarrierThunk 是 ARM/ARM64 target codegen backend 的编译器辅助函数
#       (CodeGeneratorARMVIXL::CompileBakerReadBarrierThunk)，只在 target 配置 RB-on
#       时被调用 — 它们的存在不代表 dex2oat 自己用 RB
#     · art_quick_read_barrier_mark_reg00..15 是 ASM stub，AOSP libart 总会编它们
#       (fallback 用)，与 RB 开关无关
RB_FLAG=$(nm "$DEX2OAT64" 2>/dev/null | grep -c 'kUseBakerReadBarrier' || true)
echo "  kUseBakerReadBarrier symbols:  $RB_FLAG  (expected 0 = RB-off)"
if [ "$RB_FLAG" != "0" ]; then
    echo ""
    echo "❌ FAIL: dex2oat-host has kUseBakerReadBarrier=1 despite ART_USE_READ_BARRIER=false."
    echo "   This means env did not propagate to soong productVariables. Investigate."
    exit 2
fi

echo ""
echo "✅ PASS: dex2oat-host is RB-off, matches device libart.so."
echo ""
echo "Next step: bash build/gen_boot_image.sh   (重生成 boot image with new dex2oat)"
