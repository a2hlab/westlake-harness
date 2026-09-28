#!/bin/bash
# pull_ecs_artifacts.sh — runs on LOCAL Windows (Git Bash / MSYS2)
#
# Pulls FINAL build artifacts from ECS cloud server to local D:/code/adapter/out/
# Direction: ECS → Local (pull only), per CLAUDE.md sync strategy.
#
# Only final products are synced (.so / .jar / executables / .apk / boot images).
# Intermediate files (.o, .err, obj/, old versions) are NOT synced.
#
# ============================================================================
# !!! 重要：路径映射不可自创 !!!  (2026-05-08 G2.14w 沉淀)
# ============================================================================
#
# ECS 上 .so 严格分布在 out/<sub>/ 子目录，本机镜像必须**完全相同**子目录路径。
# 手工 scp / cp 时**禁止**自己想"应该放哪"，**必须**严格遵循 ECS → Local 的
# 同名子目录映射：
#
#                ECS                                      Local
#   ~/adapter/out/adapter/X.so      ↔  D:\code\adapter\out\adapter\X.so
#   ~/adapter/out/aosp_lib/X.so     ↔  D:\code\adapter\out\aosp_lib\X.so
#   ~/adapter/out/oh-service/X.so   ↔  D:\code\adapter\out\oh-service\X.so
#
# 不能因为 .so 名字像 AOSP 就放 aosp_lib，必须按 ECS 实际位置。deploy 脚本
# 读特定子目录（如 `push_file "$OUT/adapter/liboh_android_runtime.so" ...`），
# 路径错位会让 deploy 推**旧版**到设备但脚本 silent 通过 → 灾难性误导
# （"看似部署成功实际推了旧版"）。
#
# 历史血训（G2.14w / 2026-05-08）：agent 多次手工
#   `scp oh-build:~/adapter/out/adapter/liboh_android_runtime.so \
#        D:/code/adapter/out/aosp_lib/...`
# （误以为 liboh_android_runtime.so 属 aosp_lib 类——本脚本旧 --list 描述
# 也漏列 / 错列），deploy 推 out/adapter/ 下的旧版到设备 → helloworld attach
# 后 AMS NotifyStartProcessFailed → 花数小时排查"退步原因"才回溯到 pull 路径
# 错位。修法：本注释 + 修正下方 --list 描述 + 改 memory feedback。
#
# ============================================================================
# ECS 实际 .so 分布（2026-05-08 验证，权威清单）
# ============================================================================
#
# out/adapter/ (adapter 自编 / 适配层独有)：
#   appspawn-x                  (executable)
#   libapk_installer.so
#   liboh_adapter_bridge.so
#   liboh_android_runtime.so   ← 不在 out/aosp_lib/，常被误放！
#   liboh_hwui_shim.so
#   oh-adapter-framework.jar   (jar)
#   oh-adapter-runtime.jar     (jar)
#   adapter-mainline-stubs.jar (jar)
#
# out/aosp_lib/ (~39 个 — AOSP 交叉编译产物)：
#   libandroidfw / libandroidio / libandroid_runtime
#   libartbase / libart / libart-compiler / libartpalette / libartpalette-system
#   libart_runtime_stubs        ← 在这里，不在 out/adapter/
#   libbase / libbionic_compat  ← 在这里，不在 out/adapter/
#   libcrypto / libcutils / libdexfile / libelffile / libexpat
#   libft2 / libharfbuzz_ng
#   libhwui                     ← 是 libhwui.so，liboh_hwui_shim.so 才在 out/adapter/
#   libicui18n / libicu_jni / libicuuc
#   libjavacore / liblog / liblz4 / libminikin
#   libnativebridge / libnativehelper / libnativeloader
#   libopenjdk / libopenjdkjvm / libprofile / libsigchain
#   libtinyxml2 / libunwindstack / libutils / libvixl / libziparchive
#
# out/oh-service/ (~10 个 — OH 系统服务 patches)：
#   libabilityms.z / libappms.z / libbms.z / libwms.z / libinstalls.z
#   libappspawn_client.z / libskia_canvaskit.z / libappexecfwk_common.z
#   librender_service_base.z / librender_service.z (G2.14au r5 RT probes)
#   libscene_session.z / libscene_session_manager.z
#   libsurface.z (G2.14aw probe — BufferQueue::FlushBuffer BLOGI; required
#                 for the three-level identity reconciliation §5.6)
# Note: `oh-service *.so` wildcard auto-pulls any new .z.so dropped into
# ~/adapter/out/oh-service/ on ECS. The explicit list above is the
# current-expected set for audit purposes.
#
# 检验方法（手工 scp 前必做）：
#   ssh oh-build 'ls ~/adapter/out/adapter/'    # 看 ECS 真实分布
#   ssh oh-build 'ls ~/adapter/out/aosp_lib/'
# 然后镜像同名 sub 到本机，绝不跨 sub。
#
# ============================================================================
#
# Usage:
#   bash pull_ecs_artifacts.sh              # Pull all categories
#   bash pull_ecs_artifacts.sh adapter      # Pull single category
#   bash pull_ecs_artifacts.sh oh-service aosp_lib  # Pull multiple categories
#   bash pull_ecs_artifacts.sh --dry-run    # Show what would be pulled
#   bash pull_ecs_artifacts.sh --list       # List available categories
#   bash pull_ecs_artifacts.sh --only-files=liboh_android_runtime.so          # Pull single file
#   bash pull_ecs_artifacts.sh --only-files=X.so,Y.jar,Z.apk                  # Pull multiple files
#       (file-level pull, basename only — script auto-detects ECS sub and
#        mirrors to local same-name sub; enforces sync map automatically)
#
# DEPRECATED categories (2026-04-14, see CLAUDE.md "废弃目录清单"):
#   - `deploy` (out/deploy_package/) — removed; deploy_to_dayu200.sh now reads
#     authoritative dirs directly
#   - `libart-full` (out/libart-full/) — removed; libart.so comes from aosp_lib

set -e

ECS_HOST="oh-build"
ECS_OUT="/home/HanBingChen/adapter/out"
LOCAL_OUT="D:/code/adapter/out"

DRY_RUN=false
CATEGORIES=()
ONLY_FILES=""

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --dry-run)        DRY_RUN=true ;;
        --list)
            echo "Available categories:"
            echo "  adapter      — appspawn-x, liboh_adapter_bridge.so, libapk_installer.so, liboh_android_runtime.so, liboh_hwui_shim.so, oh-adapter-framework.jar, oh-adapter-runtime.jar, adapter-mainline-stubs.jar (唯一来源 out/adapter/) ← 注：liboh_android_runtime.so 在这里不在 aosp_lib"
            echo "  oh-service   — OH service patches (.z.so)"
            echo "  aosp_fwk     — AOSP-built core jars (core-oj.jar, core-libart.jar, framework.jar, etc.); 2026-04-30 framework.jar 重新作为 BCP 成员（B.41 抛弃决策已回退）"
            echo "  aosp_lib     — cross-compiled AOSP native .so (incl. libhwui.so, libart.so, libart_runtime_stubs.so, libbionic_compat.so) ← 注：liboh_android_runtime.so 不在这里，在 adapter 类"
            echo "  boot-image   — boot.art, boot.oat, boot.vdex"
            echo "  host-tools   — dex2oat64 (host only, not deployed to device)"
            echo "  app          — OHAdapterHelloWorld.apk"
            echo ""
            echo "File-level pull:"
            echo "  --only-files=<basename1,basename2,...>"
            echo "      Pull specific files by basename (e.g. liboh_android_runtime.so)."
            echo "      Script auto-detects which ECS sub the file lives in and mirrors"
            echo "      to local same-name sub — enforces sync map automatically, no"
            echo "      manual 'guess which sub' risk.  Mirrors deploy_to_dayu200.sh's"
            echo "      --only-files=<csv> CLI for consistency."
            exit 0
            ;;
        # 2026-05-08 G2.14w: --only-files=<csv> for file-level pull.  Auto-detects
        # ECS sub from `ls ~/adapter/out/<sub>/<basename>` scan, mirrors to local
        # same-name sub.  Refuses to pull when basename not found in any known sub
        # (avoids silent "looks pulled but actually missing" failure).  Removes
        # the historical class of bug where agent/user manually scp'd to wrong
        # local sub (e.g. liboh_android_runtime.so → out/aosp_lib/) and deploy
        # silently pushed stale out/adapter/ version to device.
        --only-files=*)   ONLY_FILES="${arg#*=}" ;;
        --*)
            echo "Unknown option: $arg"
            echo "(Note: --deploy removed 2026-04-14; deploy_package/ is deprecated)"
            exit 1
            ;;
        *)  CATEGORIES+=("$arg") ;;
    esac
done

# ============================================================================
# --only-files mode: file-level pull with auto-sub-detection.
#
# For each basename in CSV, ssh ECS to scan all known subs for a file with
# that basename; mirror to local same-name sub.  This is the safe path:
# script enforces sync map, no opportunity for path-mapping mistakes.
# ============================================================================
if [ -n "$ONLY_FILES" ]; then
    echo "Checking ECS connectivity..."
    if ! ssh -o ConnectTimeout=5 "$ECS_HOST" "echo ok" >/dev/null 2>&1; then
        echo "ERROR: Cannot connect to $ECS_HOST"
        exit 1
    fi
    echo "ECS connected."
    echo ""

    KNOWN_SUBS="adapter aosp_lib aosp_fwk oh-service boot-image host-tools app"
    IFS=',' read -ra _ONLY_FILE_LIST <<< "$ONLY_FILES"
    pulled=0
    failed=0
    for raw in "${_ONLY_FILE_LIST[@]}"; do
        # trim whitespace
        bn=$(echo "$raw" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
        [ -z "$bn" ] && continue
        # Reject if user passed a path — only basename allowed, sub auto-detected.
        if [[ "$bn" == */* ]]; then
            echo "  ERROR: $bn — pass basename only, sub will be auto-detected"
            failed=$((failed+1))
            continue
        fi
        # Scan ECS subs for the basename.
        sub=$(ssh "$ECS_HOST" "for s in $KNOWN_SUBS; do
            if [ -f $ECS_OUT/\$s/$bn ]; then echo \$s; break; fi
        done" 2>/dev/null)
        if [ -z "$sub" ]; then
            echo "  ERROR: $bn — not found in any ECS sub ($KNOWN_SUBS)"
            failed=$((failed+1))
            continue
        fi
        local_dir="$LOCAL_OUT/$sub"
        mkdir -p "$local_dir"
        if $DRY_RUN; then
            echo "  [DRY] scp $ECS_HOST:$ECS_OUT/$sub/$bn $local_dir/$bn  (auto-sub=$sub)"
        else
            if scp -q "$ECS_HOST:$ECS_OUT/$sub/$bn" "$local_dir/$bn" 2>/dev/null; then
                echo "  ✓ $bn → out/$sub/  (auto-detected)"
                pulled=$((pulled+1))
            else
                echo "  ERROR: scp failed for $bn"
                failed=$((failed+1))
            fi
        fi
    done
    echo ""
    echo "=========================================="
    if [ $failed -gt 0 ]; then
        echo "--only-files: $pulled pulled, $failed FAILED"
        exit 1
    else
        echo "--only-files: $pulled file(s) pulled to D:/code/adapter/out/"
    fi
    echo "=========================================="
    exit 0
fi

ALL_CATEGORIES=(adapter oh-service aosp_fwk aosp_lib boot-image host-tools app)

if [ ${#CATEGORIES[@]} -eq 0 ]; then
    CATEGORIES=("${ALL_CATEGORIES[@]}")
fi

# Verify ECS connectivity
echo "Checking ECS connectivity..."
if ! ssh -o ConnectTimeout=5 $ECS_HOST "echo ok" >/dev/null 2>&1; then
    echo "ERROR: Cannot connect to $ECS_HOST"
    exit 1
fi
echo "ECS connected."
echo ""

TOTAL_FILES=0
TOTAL_ERRORS=0

# Pull only final artifacts matching pattern from ECS subdir to local subdir
pull_category() {
    local cat="$1"
    local ecs_dir="$2"
    local local_dir="$3"
    local pattern="$4"
    local desc="$5"

    echo "[$cat] $desc"

    if ! ssh $ECS_HOST "test -d $ecs_dir" 2>/dev/null; then
        echo "  SKIP: $ecs_dir does not exist on ECS"
        echo ""
        return
    fi

    # List matching files on ECS (final artifacts only, no subdirs)
    local files
    files=$(ssh $ECS_HOST "cd $ecs_dir && ls -1 $pattern 2>/dev/null" 2>/dev/null || true)
    if [ -z "$files" ]; then
        echo "  SKIP: no matching files ($pattern) in $ecs_dir"
        echo ""
        return
    fi

    local count=$(echo "$files" | wc -l)
    echo "  ECS: $count files"

    if $DRY_RUN; then
        echo "$files" | while read f; do
            echo "  [DRY] scp $ECS_HOST:$ecs_dir/$f $local_dir/$f"
        done
        echo ""
        return
    fi

    mkdir -p "$local_dir"
    echo "$files" | while read f; do
        scp "$ECS_HOST:$ecs_dir/$f" "$local_dir/$f" 2>/dev/null && echo "  $f" || echo "  FAIL: $f"
    done

    TOTAL_FILES=$((TOTAL_FILES + count))
    echo ""
}

echo "=========================================="
echo "Pulling ECS build artifacts → local out/"
echo "Categories: ${CATEGORIES[*]}"
if $DRY_RUN; then
    echo "MODE: DRY-RUN"
fi
echo "=========================================="
echo ""

for cat in "${CATEGORIES[@]}"; do
    case "$cat" in
        adapter)
            pull_category "$cat" "$ECS_OUT/adapter" "$LOCAL_OUT/adapter" \
                "*.so *.jar appspawn-x" \
                "Adapter binaries + shims (appspawn-x, JNI bridges, hwui shim, stubs, bionic compat)"
            ;;
        oh-service)
            pull_category "$cat" "$ECS_OUT/oh-service" "$LOCAL_OUT/oh-service" \
                "*.so" \
                "OH service patches (.z.so)"
            ;;
        aosp_fwk)
            pull_category "$cat" "$ECS_OUT/aosp_fwk" "$LOCAL_OUT/aosp_fwk" \
                "*.jar" \
                "AOSP framework JARs"
            ;;
        aosp_lib)
            pull_category "$cat" "$ECS_OUT/aosp_lib" "$LOCAL_OUT/aosp_lib" \
                "*.so" \
                "AOSP native libs (cross-compiled ARM32, incl. libhwui.so)"
            ;;
        boot-image)
            pull_category "$cat" "$ECS_OUT/boot-image" "$LOCAL_OUT/boot-image" \
                "*.art *.oat *.vdex" \
                "ARM32 boot image"
            ;;
        host-tools)
            pull_category "$cat" "$ECS_OUT/host-tools" "$LOCAL_OUT/host-tools" \
                "dex2oat64" \
                "Host tools (dex2oat64)"
            ;;
        app)
            pull_category "$cat" "$ECS_OUT/app" "$LOCAL_OUT/app" \
                "*.apk" \
                "Hello World APK"
            ;;
        deploy|libart-full)
            echo "  [SKIP] '$cat' is deprecated — see CLAUDE.md 废弃目录清单"
            echo "         deploy_to_dayu200.sh now reads from $cat's source dirs directly."
            echo ""
            ;;
        *)
            echo "  ERROR: Unknown category '$cat'"
            TOTAL_ERRORS=$((TOTAL_ERRORS + 1))
            ;;
    esac
done

echo "=========================================="
if $DRY_RUN; then
    echo "DRY-RUN complete."
else
    echo "Sync complete: $TOTAL_FILES files pulled to $LOCAL_OUT/"
    echo ""
    echo "Next: bash deploy/deploy_to_dayu200.sh"
fi
if [ $TOTAL_ERRORS -gt 0 ]; then
    echo "WARNING: $TOTAL_ERRORS errors"
    exit 1
fi
echo "=========================================="
