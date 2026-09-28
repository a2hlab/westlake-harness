#!/bin/bash
# config.sh - Shared build configuration for Android-OH Adapter project
#
# Source this file from other build scripts:
#   source "$(dirname "$0")/config.sh"

# ============================================================
# Paths (can be overridden by environment or command-line args)
# ============================================================

# Adapter project root (auto-detected from this script's location)
export ADAPTER_ROOT="${ADAPTER_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

# Source roots (default: cloud server layout)
OH_ROOT="${OH_ROOT:-$HOME/oh}"
AOSP_ROOT="${AOSP_ROOT:-$HOME/aosp}"

# OH product configuration.  The active product is D600/wukong100 (ARM64);
# callers may still pin a value explicitly, and product-specific entries must
# validate it rather than silently falling back to the retired rk3568 default.
OH_PRODUCT_NAME="${OH_PRODUCT_NAME:-wukong100}"

# OH output directory: $OH_ROOT/out/<product_name>
detect_oh_output_dir() {
    local dir="$OH_ROOT/out/$OH_PRODUCT_NAME"
    if [ -d "$dir" ]; then
        echo "$dir"
        return
    fi
    # Default: use product name, will be created by build
    echo "$dir"
}

# Adapter output directory
ADAPTER_OUT="$ADAPTER_ROOT/out"

# ============================================================
# OH build targets
# ============================================================

# System service ninja targets (all 8 .so that OH patches produce)
OH_SERVICE_TARGETS=(abilityms libappms libwms libbms scene_session scene_session_manager librender_service_base skia_canvaskit)

# GN args
OH_GN_ARGS="allow_sanitize_debug=true"

# Artifact paths (relative to OH output dir). Complete set of OH-built .so
# deployed by deploy/deploy_to_dayu200.sh + deploy/deploy_stage.sh.
# Paths verified against ~/oh/out/rk3568/ on 2026-04-17 (OH V7.0.0.18 / rk3568).
#
# 2026-05-12 G2.14aw post-mortem: this map went unmaintained from 2026-04-17
# through G2.14aq/au-r5/aw (~3 weeks). During that period:
#   - G2.14aq patched rs_transaction_data.cpp (IsCallingPidValid fallback,
#     2026-05-11) → librender_service_base.z.so already in map but
#     collect_build_artifacts.sh wasn't re-run, so adapter/out/oh-service/
#     stayed on the Apr 17 build (md5 329232cb) while ~/oh/out/.../ had the
#     fresh build (md5 c81d6de1).
#   - G2.14au r5 added probes to librender_service.z.so (2026-05-11) but the
#     file was never in this map → never copied to adapter/out/oh-service/.
#   - G2.14aw added BLOGI to libsurface.z.so (2026-05-12) — same gap.
# All three were pushed to the device via ad-hoc scp routes that bypassed
# this map, violating the 一键恢复规则.  Map now expanded so the next
# `bash collect_build_artifacts.sh` brings adapter/out/oh-service/ back into
# alignment with ~/oh/out/rk3568/.
declare -A OH_ARTIFACTS
OH_ARTIFACTS[libabilityms.z.so]="ability/ability_runtime/libabilityms.z.so"
# 2026-05-26 (1D mission teardown fix): mission_list_manager.cpp links into
# libmission_list.z.so (NOT libabilityms).  Deploy scripts already carried it
# but this collect/pull map did not -> relied on manual scp, violating the
# one-key-restore rule.  Added so collect_build_artifacts.sh / pull keeps
# adapter/out/oh-service/ aligned with ~/oh/out/rk3568/ automatically.
OH_ARTIFACTS[libmission_list.z.so]="ability/ability_runtime/libmission_list.z.so"
OH_ARTIFACTS[libappms.z.so]="ability/ability_runtime/libappms.z.so"
OH_ARTIFACTS[libwms.z.so]="window/window_manager/libwms.z.so"
OH_ARTIFACTS[libbms.z.so]="bundlemanager/bundle_framework/libbms.z.so"
OH_ARTIFACTS[libscene_session.z.so]="window/window_manager/libscene_session.z.so"
OH_ARTIFACTS[libscene_session_manager.z.so]="window/window_manager/libscene_session_manager.z.so"
OH_ARTIFACTS[librender_service_base.z.so]="graphic/graphic_2d/librender_service_base.z.so"
OH_ARTIFACTS[libskia_canvaskit.z.so]="thirdparty/skia/libskia_canvaskit.z.so"
# G2.14au r5 (2026-05-11): RS server-side .so carries RT call-site probes
# (RSUniRenderVisitor / RSUniRenderProcessor / RSUniRenderComposerAdapter).
# Device path /system/lib/librender_service.z.so (NOT platformsdk/).
OH_ARTIFACTS[librender_service.z.so]="graphic/graphic_2d/librender_service.z.so"
# G2.14aw probe (2026-05-12): graphic_surface module's libsurface.z.so
# carries the BufferQueue::FlushBuffer BLOGI diagnostic
# (uniqueId / pid / dirtyList trace).  Device path /system/lib/libsurface.z.so.
OH_ARTIFACTS[libsurface.z.so]="graphic/graphic_surface/libsurface.z.so"
# 2026-05-27: collect-map 缺口收口。以下 3 个是 deploy 脚本会推、且在 ~/oh/out 编出来、
# 但此前不在 OH_ARTIFACTS 的部署文件 -> collect_build_artifacts.sh 从未拷到 out/oh-service/，
# 只靠本机历史 collect/手动留底（违反一键恢复：本机丢了 ECS 无从重建）。源路径均经 md5 核验。
# libinstalls / libappexecfwk_common 是 OH .z.so；file_contexts 是 selinux_adapter 产物
# (621 行 = 618 factory + 3 adapter)，由 deploy_to_dayu200.sh:697 推到设备。
# 注：policy.31 不纳入——无任何 deploy 脚本引用，属本机 leftover（非部署文件）。
OH_ARTIFACTS[libinstalls.z.so]="bundlemanager/bundle_framework/libinstalls.z.so"
OH_ARTIFACTS[libappexecfwk_common.z.so]="bundlemanager/bundle_framework/libappexecfwk_common.z.so"
OH_ARTIFACTS[file_contexts]="obj/base/security/selinux_adapter/file_contexts"

# Unstripped artifact paths (not all .so have unstripped — script skips missing;
# libscene_session_manager has no unstripped on OH V7 rk3568)
declare -A OH_ARTIFACTS_UNSTRIPPED
OH_ARTIFACTS_UNSTRIPPED[libabilityms.z.so]="lib.unstripped/ability/ability_runtime/libabilityms.z.so"
OH_ARTIFACTS_UNSTRIPPED[libmission_list.z.so]="lib.unstripped/ability/ability_runtime/libmission_list.z.so"
OH_ARTIFACTS_UNSTRIPPED[libappms.z.so]="lib.unstripped/ability/ability_runtime/libappms.z.so"
OH_ARTIFACTS_UNSTRIPPED[libwms.z.so]="lib.unstripped/window/window_manager/libwms.z.so"
OH_ARTIFACTS_UNSTRIPPED[libbms.z.so]="lib.unstripped/bundlemanager/bundle_framework/libbms.z.so"
OH_ARTIFACTS_UNSTRIPPED[libscene_session.z.so]="lib.unstripped/window/window_manager/libscene_session.z.so"
OH_ARTIFACTS_UNSTRIPPED[librender_service_base.z.so]="lib.unstripped/graphic/graphic_2d/librender_service_base.z.so"
OH_ARTIFACTS_UNSTRIPPED[libskia_canvaskit.z.so]="lib.unstripped/thirdparty/skia/libskia_canvaskit.z.so"
# G2.14au r5 + G2.14aw parallel unstripped entries (companion to OH_ARTIFACTS above)
OH_ARTIFACTS_UNSTRIPPED[librender_service.z.so]="lib.unstripped/graphic/graphic_2d/librender_service.z.so"
OH_ARTIFACTS_UNSTRIPPED[libsurface.z.so]="lib.unstripped/graphic/graphic_surface/libsurface.z.so"
# 2026-05-27 collect-map 缺口收口（与上方 OH_ARTIFACTS 配套；file_contexts 无 unstripped 不列）
OH_ARTIFACTS_UNSTRIPPED[libinstalls.z.so]="lib.unstripped/bundlemanager/bundle_framework/libinstalls.z.so"
OH_ARTIFACTS_UNSTRIPPED[libappexecfwk_common.z.so]="lib.unstripped/bundlemanager/bundle_framework/libappexecfwk_common.z.so"

# ============================================================
# Patch file mappings
# ============================================================

# OH_BUILD_PATCHES + OH_FULL_FILE_REPLACEMENTS + OH_DIFF_PATCHES + OH_FUNC_PATCH_DIRS
# dicts REMOVED 2026-05-21 in Phase 7. All OH-side patches now use single mechanism:
# restore_after_sync.sh B6b OH_DIFF_PATCH_LIST (full OH-mirrored path .patch files).
# apply_oh_patches.sh retired.

# Patch applied marker file (still referenced by some legacy code paths)
PATCH_MARKER="$OH_ROOT/.adapter_patches_applied"

# ============================================================
# Logging utilities
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# run() — DRY_RUN-aware executor (2026-05-27). 满足 inner/apply_*.sh 组件函数从 build_*.sh
# 调用时的契约(它们用 run 做实际 apply,以支持 --dry-run)。restore_after_sync.sh / deploy
# 各自定义了同名 run(),source 顺序使其本地版生效,不受此影响。
run() {
    if [ "${DRY_RUN:-0}" = "1" ]; then
        echo -e "${BLUE}[DRY]${NC}   $*"
    else
        eval "$@"
    fi
}

# ============================================================
# Prerequisite checks
# ============================================================

check_oh_source() {
    if [ ! -d "$OH_ROOT/build" ] || [ ! -f "$OH_ROOT/build.sh" ]; then
        log_error "OH source not found at $OH_ROOT"
        log_error "Set OH_ROOT or pass --oh-root=PATH"
        return 1
    fi
    log_ok "OH source found at $OH_ROOT"
}

check_disk_space() {
    local avail_gb
    avail_gb=$(df -BG "$OH_ROOT" | awk 'NR==2{print $4}' | tr -d 'G')
    if [ "$avail_gb" -lt 50 ]; then
        log_warn "Low disk space: ${avail_gb}GB available (recommend >50GB)"
    else
        log_ok "Disk space: ${avail_gb}GB available"
    fi
}

check_prerequisites() {
    check_oh_source || return 1
    check_disk_space

    if ! command -v ccache &>/dev/null; then
        log_warn "ccache not found - build will be slower"
    fi

    # Check OH Python has pyyaml
    local oh_python="$OH_ROOT/prebuilts/python/linux-x86/3.11.4/bin/python3"
    if [ -x "$oh_python" ]; then
        if ! "$oh_python" -c "import yaml" 2>/dev/null; then
            log_warn "pyyaml not installed in OH Python - installing..."
            "$oh_python" -m pip install pyyaml -q
        fi
    fi

    # Check autotools (needed by libnl)
    if ! command -v autoreconf &>/dev/null; then
        log_warn "autotools not found - installing..."
        apt-get install -y autoconf automake libtool -q 2>/dev/null || true
    fi

    # Create prebuilt SDK dir to skip SDK build
    mkdir -p "$OH_ROOT/prebuilts/ohos-sdk/linux/23"
}
