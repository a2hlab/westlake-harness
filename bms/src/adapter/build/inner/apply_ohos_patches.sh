#!/bin/bash
# ============================================================================
# apply_ohos_patches.sh — OH 源 .patch 应用(sourceable 函数库)
# ============================================================================
# 2026-05-27 原则1重构:由独立子进程脚本改为 *sourceable 函数*,由
# restore_after_sync.sh 与各 build_*.sh 的 phase0 `source` 后调用(与 apply_hwui_patches.sh
# 模式一致)。**OH 源准备的唯一真相源**。
#
# 2026-05-27 (b) 批收口:apply_ohos_patches 升级为 *完整 OH 源准备* 顶层编排——除 mandatory
# diff patch 外,把 restore 历史内联的 OH-build 必需步骤一并纳入,使任一 build 入口的
# phase0 在干净源码树上单跑即可把 OH 源 patch 到可编译态(gn gen / graphic_2d / libbms 等
# 不再因缺步骤而失败)。调用顺序:
#   apply_ohos_diff_patches      — OH-mirrored .patch(两层幂等,见下)
#   apply_ohos_b6_buffer_reclaim — graphic_2d rs_buffer_reclaim.cpp %u→%zu(git apply)
#   apply_ohos_b9_ets2abc        — 仅供显式 legacy-rk3568-module-only profile
#   apply_ohos_b10_bmgr_sources  — cp apk_manifest_parser + adapter_apk_install_minimal → bmgr/src
# B12/B13 已退役：原 B12 的 Mission full-file 输入已恢复为 exact pre/post
# diff（mission.h + mission.cpp），其余残留快照与 mandatory diff post-image
# 逐字节相同；B13 遗失的 legacy file_contexts 已由 mandatory OH-root SELinux diff 覆盖。
# 注:B0(build.sh guard,非构建产物依赖)按决定保留在 restore,不纳入此处。
#
# 依赖调用方作用域已定义:
#   变量: ADAPTER_ROOT, OH_ROOT, DRY_RUN
#   函数: run(), log_info(), log_ok(), log_warn()
#
# apply_ohos_diff_patches 的两层幂等(避免每次重复 dry-run 浪费时间):
#   Layer 1 组件级快速短路:marker 绑定全部 patch 内容 SHA-256 和所有 target
#           的 exact SHA-256。marker 后的任意目标漂移均 fail-closed，不用 hunk
#           applicability 重新“洗绿”。marker 放 $OH_ROOT/.adapter_applied/(untracked)。
#   Layer 2 逐 patch:用 --force --forward/-R --fuzz=0 强制判向，禁止 GNU patch
#           自动翻转方向。无 FAIL/MISSING 才写 exact marker。
# B6/B9 各自 reverse-check 或 forward-dry-run 幂等;B10 是 cp(天然幂等)。
# wukong100 full-product 固定保留 OH6.1 LTS 官方 app_internal/ets2abc 输入；
# HanBing 的 rk3568 module-only 裁剪不得进入本 canonical Phase 0。
# ============================================================================

# 顶层:完整 OH 源准备(31 条 diff + B10)。restore 与 build phase0 都调它。
# B6 targeted an older graphic_2d tree; OpenHarmony-6.1-LTS wukong100 has no
# rs_buffer_reclaim.cpp, so carrying that patch into this generation would
# manufacture a source dependency instead of fixing an active call graph.
apply_ohos_patches() (
    local full_lock="" full_lock_owned=0 marker_dir input_snapshot=""
    local live_adapter_root input_sha_start input_sha_snapshot input_sha_after_copy input_sha_end
    ADAPTER_ROOT=$(cd "$ADAPTER_ROOT" && pwd -P) || return 1
    live_adapter_root="$ADAPTER_ROOT"
    OH_ROOT=$(cd "$OH_ROOT" && pwd -P) || return 1
    trap 'if [ -n "$input_snapshot" ]; then rm -rf "$input_snapshot"; fi; if [ "$full_lock_owned" = "1" ]; then rmdir "$full_lock" 2>/dev/null || true; fi' EXIT
    if [ "${DRY_RUN:-0}" != "1" ]; then
        marker_dir="$OH_ROOT/.adapter_applied"
        _ohos_assert_no_symlink_components "$OH_ROOT" ".adapter_applied" 1 || return 1
        mkdir -p "$marker_dir" || return 1
        _ohos_assert_no_symlink_components "$OH_ROOT" ".adapter_applied" || return 1
        full_lock="$marker_dir/ohos_full_prepare.lock"
        if ! mkdir "$full_lock" 2>/dev/null; then
            log_warn "another complete OH source preparation owns the lock: $full_lock"
            return 1
        fi
        full_lock_owned=1
    fi

    input_sha_start=$(_ohos_adapter_inputs_sha256 "$live_adapter_root") || return 1
    input_snapshot=$(mktemp -d "${TMPDIR:-/tmp}/ohos-complete-input.XXXXXX") || return 1
    mkdir -p "$input_snapshot/build/inner" "$input_snapshot/framework/package-manager/jni"
    cp "$live_adapter_root/build/inner/apply_ohos_patches.sh" "$input_snapshot/build/inner/"
    cp "$live_adapter_root/build/inner/ohos_diff_patch_oracle.tsv" "$input_snapshot/build/inner/"
    cp "$live_adapter_root/build/inner/ohos_aux_patch_oracle.tsv" "$input_snapshot/build/inner/"
    cp -R "$live_adapter_root/ohos_patches" "$input_snapshot/"
    cp "$live_adapter_root/framework/package-manager/jni/apk_manifest_parser.h" \
       "$live_adapter_root/framework/package-manager/jni/apk_manifest_parser.cpp" \
       "$input_snapshot/framework/package-manager/jni/"
    input_sha_snapshot=$(_ohos_adapter_inputs_sha256 "$input_snapshot") || return 1
    input_sha_after_copy=$(_ohos_adapter_inputs_sha256 "$live_adapter_root") || return 1
    if [ "$input_sha_start" != "$input_sha_snapshot" ] || [ "$input_sha_start" != "$input_sha_after_copy" ]; then
        log_warn "adapter inputs changed while creating the complete source snapshot"
        return 1
    fi
    ADAPTER_ROOT="$input_snapshot"
    log_info "complete_adapter_input_sha256=$input_sha_snapshot"

    if ! _ohos_verify_wukong100_full_product_build_inputs; then
        log_warn "wukong100 full-product build input gate failed (see above)"
        return 1
    fi
    if ! apply_ohos_diff_patches; then
        log_warn "apply_ohos_diff_patches: some OH diff patches failed (see above)"
        return 1
    fi
    if ! _ohos_verify_bms_lts_adapter_contract; then
        log_warn "OH6.1 LTS BMS adapter contract gate failed (see above)"
        return 1
    fi
    if ! apply_ohos_b10_bmgr_sources; then
        log_warn "apply_ohos_b10_bmgr_sources: failed (see above)"
        return 1
    fi
    input_sha_end=$(_ohos_adapter_inputs_sha256 "$live_adapter_root") || return 1
    if [ "$input_sha_end" != "$input_sha_snapshot" ]; then
        log_warn "adapter inputs changed during OH source preparation; refusing build handoff"
        return 1
    fi
    return 0
)

# The APK registration block is compiled inside libbms, whose OH6.1 LTS
# contract is -fno-exceptions.  A 2026-03 upstream five-file refactor split
# ProcessBundleCodePath into InnerProcessCodePath* helpers, but R45 intentionally
# remains on the LTS monolithic API.  Byte-oracle checks alone cannot detect a
# cross-vintage API splice, so reject both failure classes before GN/Ninja.
_ohos_verify_bms_lts_adapter_contract() {
    local rel="foundation/bundlemanager/bundle_framework/services/bundlemgr/src/base_bundle_installer.cpp"
    local source="$OH_ROOT/$rel"
    _ohos_assert_no_symlink_components "$OH_ROOT" "$rel" || return 1
    [ -f "$source" ] || return 1
    if grep -Eq 'InnerProcessCodePath(CreateNewDir|RealToOld|NewToReal)' "$source"; then
        log_warn "cross-vintage BMS InnerProcessCodePath helper found: $rel"
        return 1
    fi
    if grep -Eq '(^|[^[:alnum:]_])(try|catch)[[:space:]]*[({]' "$source"; then
        log_warn "exception syntax found in OH6.1 LTS -fno-exceptions libbms source: $rel"
        return 1
    fi
    grep -Fq 'nlohmann::json::parse(std::string(jsonBuf.data()), nullptr, false)' "$source" || {
        log_warn "no-throw APK manifest parser contract missing: $rel"
        return 1
    }
    grep -Fq 'InstallRenameExceptionStatus::RENAME_RELA_TO_OLD_PATH' "$source" || return 1
    grep -Fq 'InstallRenameExceptionStatus::RENAME_NEW_TO_RELA_PATH' "$source" || return 1
    log_ok "OH6.1 LTS BMS adapter API/no-exception contract passed"
    return 0
}

_ohos_assert_no_symlink_components() {
    local root="$1" rel="$2" allow_missing="${3:-0}" part current="$1"
    case "$rel" in
        ""|*$'\n'*|/*|../*|*/../*|*/..) return 1 ;;
    esac
    local IFS='/'
    for part in $rel; do
        current="$current/$part"
        [ ! -L "$current" ] || return 1
        if [ ! -e "$current" ]; then
            [ "$allow_missing" = "1" ] && return 0
            return 1
        fi
    done
}

_ohos_normalize_known_crlf_targets() {
    local oracle_file="$1" spec rel target probe normalized_sha oracle_entry oracle_target oracle_patch_sha expected_pre_sha expected_post_sha
    local targets=(
        "foundation/bundlemanager/bundle_framework/services/bundlemgr/include/ipc/extract_param.h.patch|foundation/bundlemanager/bundle_framework/services/bundlemgr/include/ipc/extract_param.h"
        "base/startup/init/services/init/include/init_service.h.patch|base/startup/init/services/init/include/init_service.h"
    )

    for spec in "${targets[@]}"; do
        IFS='|' read -r rel target <<< "$spec"
        target="$OH_ROOT/${spec#*|}"
        if ! _ohos_assert_no_symlink_components "$OH_ROOT" "${spec#*|}" \
            || [ ! -f "$target" ]; then
            log_warn "known CRLF target is not a regular non-symlink file: $target"
            return 1
        fi
        if LC_ALL=C grep -q $'\r$' "$target"; then
            probe=$(mktemp "${TMPDIR:-/tmp}/ohos-crlf-probe.XXXXXX") || return 1
            if ! perl -pe 's/\r$//' "$target" > "$probe"; then
                rm -f "$probe"
                return 1
            fi
            normalized_sha=$(_ohos_sha256_file "$probe") || {
                rm -f "$probe"
                return 1
            }
            rm -f "$probe"
            oracle_entry=$(_ohos_oracle_entry "$oracle_file" "$rel") || return 1
            IFS=$'\t' read -r oracle_target oracle_patch_sha expected_pre_sha expected_post_sha <<< "$oracle_entry"
            if [ "$normalized_sha" != "$expected_pre_sha" ] && [ "$normalized_sha" != "$expected_post_sha" ]; then
                log_warn "CRLF normalization would not produce an exact oracle image: $rel"
                return 1
            fi
            if ! perl -pi -e 's/\r$//' "$target"; then
                log_warn "failed to normalize CRLF target: $target"
                return 1
            fi
            [ "$(_ohos_sha256_file "$target")" = "$normalized_sha" ] || return 1
        fi
    done
}

_ohos_patch_target() {
    local patch_file="$1" old_raw new_raw old_target target
    old_raw=$(sed -n 's/^---[[:space:]]\([^[:space:]]*\).*/\1/p' "$patch_file")
    new_raw=$(sed -n 's/^+++[[:space:]]\([^[:space:]]*\).*/\1/p' "$patch_file")
    case "$old_raw:$new_raw" in
        */*:*/*) ;;
        *) return 1 ;;
    esac
    old_target=${old_raw#*/}
    target=${new_raw#*/}
    [ "$old_target" = "$target" ] || return 1
    case "$target" in
        ""|*$'\n'*|/*|../*|*/../*|*/..) return 1 ;;
    esac
    printf '%s\n' "$target"
}

_ohos_oracle_entry() {
    local oracle_file="$1" rel="$2"
    awk -F '\t' -v key="$rel" '
        NR > 1 && $1 == key { count++; value = $2 FS $3 FS $4 FS $5 }
        END { if (count != 1) exit 2; print value }
    ' "$oracle_file"
}

_ohos_is_sha256() {
    [ "${#1}" = "64" ] || return 1
    case "$1" in
        *[!0-9a-f]*) return 1 ;;
    esac
}

_ohos_sha256_file() {
    local output hash
    output=$(sha256sum "$1") || return 1
    hash=${output%% *}
    _ohos_is_sha256 "$hash" || return 1
    printf '%s\n' "$hash"
}

# The active D600 product is a complete OH6.1 LTS image build.  Two historical
# patches in this adapter were authored for HanBing's OH7/rk3568 *module-only*
# workflow: app_internal.gni.patch removed the official JS/ETS loader producers,
# and B9 removed the ETS stdlib/API producers.  Applying either patch to a full
# wukong100 graph deterministically creates missing-input failures.  Pin their
# official R45 preimages here so Phase 0 fails before GN/Ninja can waste a build.
_ohos_verify_wukong100_full_product_build_inputs() {
    local product="${OH_PRODUCT_NAME:-wukong100}"
    local app_rel="build/ohos/app/app_internal.gni"
    local ets_rel="build/config/components/ets_frontend/ets2abc_config.gni"
    local product_rel="vendor/revoview/wukong100/config.json"
    local updater_rel="foundation/arkui/ui_lite/ext/updater/BUILD.gn"
    local app_expected="595c739b0741f9fbc1e32990cb1d95bee37bd2fd68daae17e65b726ff44edd1c"
    local ets_expected="28fc4cdcd620fda21c3cb6728d5cfc6a40f0162b93247f2ab86c2c5d4d763867"
    local product_expected="45a94f39a529b81577542b02900bbea82dca74d9d8368dd30eb994c9a8b951bd"
    local updater_expected="2a59138648ef7e8771836ea532c7effde7c1fb7387f45bdd74f1bf1cfcc81e13"
    local app_actual ets_actual product_actual updater_actual

    if [ "$product" != "wukong100" ]; then
        log_warn "canonical OH source preparation is pinned to wukong100 full-product; got: $product"
        return 1
    fi
    _ohos_assert_no_symlink_components "$OH_ROOT" "$app_rel" || return 1
    _ohos_assert_no_symlink_components "$OH_ROOT" "$ets_rel" || return 1
    _ohos_assert_no_symlink_components "$OH_ROOT" "$product_rel" || return 1
    _ohos_assert_no_symlink_components "$OH_ROOT" "$updater_rel" || return 1
    app_actual=$(_ohos_sha256_file "$OH_ROOT/$app_rel") || return 1
    ets_actual=$(_ohos_sha256_file "$OH_ROOT/$ets_rel") || return 1
    product_actual=$(_ohos_sha256_file "$OH_ROOT/$product_rel") || return 1
    updater_actual=$(_ohos_sha256_file "$OH_ROOT/$updater_rel") || return 1
    if [ "$app_actual" != "$app_expected" ]; then
        log_warn "full-product app_internal.gni drift: expected=$app_expected actual=$app_actual"
        return 1
    fi
    if [ "$ets_actual" != "$ets_expected" ]; then
        log_warn "full-product ets2abc_config.gni drift: expected=$ets_expected actual=$ets_actual"
        return 1
    fi
    if [ "$product_actual" != "$product_expected" ]; then
        log_warn "full-product config.json drift: expected=$product_expected actual=$product_actual"
        return 1
    fi
    if [ "$updater_actual" != "$updater_expected" ]; then
        log_warn "full-product updater BUILD.gn drift: expected=$updater_expected actual=$updater_actual"
        return 1
    fi
    if grep -Fq '_ace_loader_home = "/developtools/' "$OH_ROOT/$app_rel"; then
        log_warn "forbidden static /developtools loader path in $app_rel"
        return 1
    fi
    log_ok "wukong100 full-product build inputs pinned to official OH6.1 LTS preimages"
    return 0
}

_ohos_sha256_string() {
    local output hash
    output=$(printf '%s' "$1" | sha256sum) || return 1
    hash=${output%% *}
    _ohos_is_sha256 "$hash" || return 1
    printf '%s\n' "$hash"
}

_ohos_adapter_inputs_sha256() {
    local root="$1" file rel file_sha manifest=""
    [ -d "$root/ohos_patches" ] || return 1
    [ -f "$root/build/inner/apply_ohos_patches.sh" ] || return 1
    [ -f "$root/build/inner/ohos_diff_patch_oracle.tsv" ] || return 1
    [ -f "$root/build/inner/ohos_aux_patch_oracle.tsv" ] || return 1
    [ -f "$root/framework/package-manager/jni/apk_manifest_parser.h" ] || return 1
    [ -f "$root/framework/package-manager/jni/apk_manifest_parser.cpp" ] || return 1
    if find "$root/ohos_patches" -type l -print | grep -q .; then
        return 1
    fi
    while IFS= read -r file; do
        case "$file" in *$'\n'*) return 1 ;; esac
        rel=${file#"$root"/}
        _ohos_assert_no_symlink_components "$root" "$rel" || return 1
        file_sha=$(_ohos_sha256_file "$file") || return 1
        printf -v manifest '%s%s\t%s\n' "$manifest" "$rel" "$file_sha"
    done < <(
        {
            printf '%s\n' \
                "$root/build/inner/apply_ohos_patches.sh" \
                "$root/build/inner/ohos_diff_patch_oracle.tsv" \
                "$root/build/inner/ohos_aux_patch_oracle.tsv" \
                "$root/framework/package-manager/jni/apk_manifest_parser.h" \
                "$root/framework/package-manager/jni/apk_manifest_parser.cpp"
            find "$root/ohos_patches" -type f -print
        } | LC_ALL=C sort
    )
    _ohos_sha256_string "$manifest"
}

_ohos_current_target_sha256() {
    local oracle_file="$1" rel target patch_sha pre_sha post_sha path file_sha manifest=""
    while IFS=$'\t' read -r rel target patch_sha pre_sha post_sha; do
        [ "$rel" = "patch" ] && continue
        path="$OH_ROOT/$target"
        if ! _ohos_assert_no_symlink_components "$OH_ROOT" "$target" \
            || [ ! -f "$path" ]; then
            printf 'oracle target is not a regular non-symlink file: %s\n' "$target" >&2
            return 1
        fi
        file_sha=$(_ohos_sha256_file "$path") || return 1
        if ! _ohos_assert_no_symlink_components "$OH_ROOT" "$target" \
            || [ ! -f "$path" ]; then
            printf 'oracle target changed type while hashing: %s\n' "$target" >&2
            return 1
        fi
        printf -v manifest '%s%s\t%s\n' "$manifest" "$target" "$file_sha"
    done < "$oracle_file"
    _ohos_sha256_string "$manifest"
}

_ohos_prepare_dry_run_root() {
    local oracle_file="$1" source_root="$2" shadow_root="$3"
    local rel target patch_sha pre_sha post_sha source target_path
    while IFS=$'\t' read -r rel target patch_sha pre_sha post_sha; do
        [ "$rel" = "patch" ] && continue
        case "$target" in
            ""|*$'\n'*|/*|../*|*/../*|*/..) return 1 ;;
        esac
        source="$source_root/$target"
        target_path="$shadow_root/$target"
        if ! _ohos_assert_no_symlink_components "$source_root" "$target" \
            || [ ! -f "$source" ]; then
            printf 'dry-run source is not a regular non-symlink file: %s\n' "$target" >&2
            return 1
        fi
        mkdir -p "$(dirname "$target_path")" || return 1
        cp "$source" "$target_path" || return 1
    done < "$oracle_file"
    if [ -e "$source_root/.adapter_applied/ohos_service" ]; then
        if ! _ohos_assert_no_symlink_components "$source_root" ".adapter_applied/ohos_service" \
            || [ ! -f "$source_root/.adapter_applied/ohos_service" ]; then
            printf 'dry-run marker is not a regular non-symlink file\n' >&2
            return 1
        fi
        mkdir -p "$shadow_root/.adapter_applied" || return 1
        cp "$source_root/.adapter_applied/ohos_service" "$shadow_root/.adapter_applied/ohos_service" || return 1
    fi
}

_ohos_load_aux_patch() {
    local name="$1" oracle_source="$ADAPTER_ROOT/build/inner/ohos_aux_patch_oracle.tsv"
    local header row_count bad_rows entry
    if ! _ohos_assert_no_symlink_components "$ADAPTER_ROOT" "build/inner/ohos_aux_patch_oracle.tsv" \
        || [ ! -s "$oracle_source" ]; then
        log_warn "mandatory aux patch oracle missing or unsafe"
        return 1
    fi
    AUX_ORACLE_SNAPSHOT=$(mktemp "${TMPDIR:-/tmp}/ohos-aux-oracle.XXXXXX") || return 1
    cp "$oracle_source" "$AUX_ORACLE_SNAPSHOT" || return 1
    IFS= read -r header < "$AUX_ORACLE_SNAPSHOT" || return 1
    [ "$header" = $'name\tpatch\ttarget\tpatch_sha256\tpre_sha256\tpost_sha256' ] || return 1
    row_count=$(awk 'NR > 1 { count++ } END { print count + 0 }' "$AUX_ORACLE_SNAPSHOT") || return 1
    bad_rows=$(awk -F '\t' 'NR > 1 && (NF != 6 || $0 ~ /\r/) { bad++ } END { print bad + 0 }' "$AUX_ORACLE_SNAPSHOT") || return 1
    [ "$row_count" = "2" ] && [ "$bad_rows" = "0" ] || return 1
    entry=$(awk -F '\t' -v key="$name" 'NR > 1 && $1 == key {
        count++; value = $2 FS $3 FS $4 FS $5 FS $6
    } END { if (count != 1) exit 2; print value }' "$AUX_ORACLE_SNAPSHOT") || return 1
    IFS=$'\t' read -r AUX_PATCH_REL AUX_TARGET_REL AUX_PATCH_SHA AUX_PRE_SHA AUX_POST_SHA <<< "$entry"
    case "$AUX_PATCH_REL:$AUX_TARGET_REL" in
        *$'\n'*|/*:*|*:/*|../*:*|*:../*|*/../*:*|*:*/../*) return 1 ;;
    esac
    _ohos_is_sha256 "$AUX_PATCH_SHA" && _ohos_is_sha256 "$AUX_PRE_SHA" \
        && _ohos_is_sha256 "$AUX_POST_SHA" || return 1
    [ "$AUX_PRE_SHA" != "$AUX_POST_SHA" ] || return 1
    if ! _ohos_assert_no_symlink_components "$ADAPTER_ROOT" "ohos_patches/$AUX_PATCH_REL"; then
        return 1
    fi
    AUX_PATCH_SNAPSHOT=$(mktemp "${TMPDIR:-/tmp}/ohos-aux-patch.XXXXXX") || return 1
    cp "$ADAPTER_ROOT/ohos_patches/$AUX_PATCH_REL" "$AUX_PATCH_SNAPSHOT" || return 1
    [ "$(_ohos_sha256_file "$AUX_PATCH_SNAPSHOT")" = "$AUX_PATCH_SHA" ] || return 1
}

_ohos_apply_exact_aux_patch() (
    local name="$1" patch_root_rel="$2" backup_rel="${3:-}"
    local AUX_ORACLE_SNAPSHOT="" AUX_PATCH_SNAPSHOT="" AUX_PATCH_REL="" AUX_TARGET_REL=""
    local AUX_PATCH_SHA="" AUX_PRE_SHA="" AUX_POST_SHA="" parsed_target expected_target
    local current_sha patch_root lock_dir="" lock_owned=0 backup_file backup_sha backup_tmp=""
    trap 'rm -f "$AUX_ORACLE_SNAPSHOT" "$AUX_PATCH_SNAPSHOT"; if [ -n "$backup_tmp" ]; then rm -f "$backup_tmp"; fi; if [ "$lock_owned" = "1" ]; then rmdir "$lock_dir" 2>/dev/null || true; fi' EXIT
    ADAPTER_ROOT=$(cd "$ADAPTER_ROOT" && pwd -P) || return 1
    OH_ROOT=$(cd "$OH_ROOT" && pwd -P) || return 1
    command -v sha256sum >/dev/null 2>&1 || return 1
    _ohos_load_aux_patch "$name" || return 1
    parsed_target=$(_ohos_patch_target "$AUX_PATCH_SNAPSHOT") || return 1
    if [ -n "$patch_root_rel" ]; then
        expected_target="$patch_root_rel/$parsed_target"
        patch_root="$OH_ROOT/$patch_root_rel"
    else
        expected_target="$parsed_target"
        patch_root="$OH_ROOT"
    fi
    [ "$expected_target" = "$AUX_TARGET_REL" ] || return 1
    _ohos_assert_no_symlink_components "$OH_ROOT" "$AUX_TARGET_REL" || return 1
    [ -f "$OH_ROOT/$AUX_TARGET_REL" ] || return 1

    if [ "${DRY_RUN:-0}" != "1" ]; then
        _ohos_assert_no_symlink_components "$OH_ROOT" ".adapter_applied" 1 || return 1
        mkdir -p "$OH_ROOT/.adapter_applied" || return 1
        _ohos_assert_no_symlink_components "$OH_ROOT" ".adapter_applied" || return 1
        lock_dir="$OH_ROOT/.adapter_applied/ohos_aux_${name}.lock"
        mkdir "$lock_dir" 2>/dev/null || return 1
        lock_owned=1
    fi

    current_sha=$(_ohos_sha256_file "$OH_ROOT/$AUX_TARGET_REL") || return 1
    if [ -n "$backup_rel" ]; then
        backup_file="$OH_ROOT/$backup_rel"
        _ohos_assert_no_symlink_components "$OH_ROOT" "$(dirname "$backup_rel")" || return 1
        if [ -L "$backup_file" ]; then
            log_warn "$name failed — backup is a symlink"
            return 1
        fi
        if [ -e "$backup_file" ]; then
            _ohos_assert_no_symlink_components "$OH_ROOT" "$backup_rel" || return 1
            [ -f "$backup_file" ] || return 1
            backup_sha=$(_ohos_sha256_file "$backup_file") || return 1
            if [ "$backup_sha" != "$AUX_PRE_SHA" ]; then
                log_warn "$name failed — backup is not the exact oracle pre-image"
                return 1
            fi
        elif [ "$current_sha" != "$AUX_PRE_SHA" ]; then
            log_warn "$name failed — exact pre-image backup is missing for a post-image target"
            return 1
        elif [ "${DRY_RUN:-0}" != "1" ]; then
            backup_tmp=$(mktemp "$(dirname "$backup_file")/.$(basename "$backup_file").tmp.XXXXXX") || return 1
            cp "$OH_ROOT/$AUX_TARGET_REL" "$backup_tmp" || return 1
            [ "$(_ohos_sha256_file "$backup_tmp")" = "$AUX_PRE_SHA" ] || return 1
            if ! ln "$backup_tmp" "$backup_file" 2>/dev/null; then
                [ ! -L "$backup_file" ] && [ -f "$backup_file" ] \
                    && [ "$(_ohos_sha256_file "$backup_file")" = "$AUX_PRE_SHA" ] || return 1
            fi
            rm -f "$backup_tmp"
            backup_tmp=""
            _ohos_assert_no_symlink_components "$OH_ROOT" "$backup_rel" || return 1
        fi
    fi

    if [ "$current_sha" = "$AUX_POST_SHA" ]; then
        patch --force -R --fuzz=0 --no-backup-if-mismatch --dry-run -p1 -d "$patch_root" \
            < "$AUX_PATCH_SNAPSHOT" >/dev/null 2>&1 || return 1
        log_ok "$name: exact oracle post-image already present"
        return 0
    fi
    if [ "$current_sha" != "$AUX_PRE_SHA" ]; then
        log_warn "$name failed — target differs from exact oracle pre/post images"
        return 1
    fi
    patch --force --forward --fuzz=0 --no-backup-if-mismatch --dry-run -p1 -d "$patch_root" \
        < "$AUX_PATCH_SNAPSHOT" >/dev/null 2>&1 || return 1

    if [ "${DRY_RUN:-0}" = "1" ]; then
        log_info "[dry-run] $name exact pre-image would be patched"
        return 0
    fi
    patch --force --forward --fuzz=0 --no-backup-if-mismatch -p1 -d "$patch_root" \
        < "$AUX_PATCH_SNAPSHOT" || return 1
    [ "$(_ohos_sha256_file "$OH_ROOT/$AUX_TARGET_REL")" = "$AUX_POST_SHA" ] || return 1
    if [ -n "$backup_rel" ]; then
        _ohos_assert_no_symlink_components "$OH_ROOT" "$backup_rel" || return 1
        [ "$(_ohos_sha256_file "$OH_ROOT/$backup_rel")" = "$AUX_PRE_SHA" ] || return 1
    fi
    log_ok "$name: exact oracle pre-image patched"
    return 0
)

apply_ohos_diff_patches() (
    ADAPTER_ROOT=$(cd "$ADAPTER_ROOT" && pwd -P) || return 1
    OH_ROOT=$(cd "$OH_ROOT" && pwd -P) || return 1
    log_info "B6b. Apply OH diff patches at full OH-mirrored paths"
    log_info "  ADAPTER_ROOT=$ADAPTER_ROOT  OH_ROOT=$OH_ROOT"

    if [ "${DRY_RUN:-0}" = "1" ]; then
        local oracle_file="$ADAPTER_ROOT/build/inner/ohos_diff_patch_oracle.tsv"
        local source_oh_root="$OH_ROOT" dry_root
        if ! _ohos_assert_no_symlink_components "$ADAPTER_ROOT" "build/inner/ohos_diff_patch_oracle.tsv" \
            || [ ! -s "$oracle_file" ]; then
            log_warn "mandatory exact patch oracle missing or unsafe: $oracle_file"
            return 1
        fi
        dry_root=$(mktemp -d "${TMPDIR:-/tmp}/ohos-diff-dry.XXXXXX") || return 1
        trap 'rm -rf "$dry_root"' EXIT
        _ohos_prepare_dry_run_root "$oracle_file" "$source_oh_root" "$dry_root" || return 1
        log_info "[dry-run] validating all OH patches in an isolated exact shadow"
        OH_ROOT="$dry_root"
        DRY_RUN=0
        if _apply_ohos_diff_patches_real dry-run; then
            log_ok "[dry-run] isolated exact patch simulation passed"
            return 0
        fi
        log_warn "[dry-run] isolated exact patch simulation failed"
        return 1
    fi

    _apply_ohos_diff_patches_real apply
)

_apply_ohos_diff_patches_real() (
    local apply_mode="${1:-apply}"

    local OH_DIFF_PATCH_LIST=(
        "foundation/bundlemanager/bundle_framework/services/bundlemgr/BUILD.gn.patch"
        "foundation/bundlemanager/bundle_framework/common/BUILD.gn.patch"
        "foundation/bundlemanager/bundle_framework/common/utils/src/bundle_file_util.cpp.patch"
        "foundation/bundlemanager/bundle_framework/services/bundlemgr/src/bundle_util.cpp.patch"
        "foundation/bundlemanager/bundle_framework/services/bundlemgr/src/bundle_stream_installer_host_impl.cpp.patch"
        # APK dispatch has a single owner in BaseBundleInstaller::ProcessBundleInstall.
        # The retired bundle_installer.cpp v1 patch bypassed BMS registration.
        "foundation/bundlemanager/bundle_framework/services/bundlemgr/src/base_bundle_installer.cpp.patch"
        "foundation/bundlemanager/bundle_framework/services/bundlemgr/src/bundle_data_mgr.cpp.patch"
        "foundation/bundlemanager/bundle_framework/services/bundlemgr/include/ipc/extract_param.h.patch"
        "foundation/bundlemanager/bundle_framework/services/bundlemgr/src/ipc/extract_param.cpp.patch"
        "foundation/bundlemanager/bundle_framework/services/bundlemgr/src/zip_file.cpp.patch"
        "foundation/bundlemanager/bundle_framework/services/bundlemgr/include/installd/installd_operator.h.patch"
        "foundation/bundlemanager/bundle_framework/services/bundlemgr/src/installd/installd_operator.cpp.patch"
        "base/startup/appspawn/interfaces/innerkits/include/appspawn.h.patch"
        "base/startup/appspawn/modules/module_engine/include/appspawn_msg.h.patch"
        "base/startup/appspawn/interfaces/innerkits/client/appspawn_client.c.patch"
        "base/startup/appspawn/interfaces/innerkits/client/appspawn_client.h.patch"
        "foundation/ability/ability_runtime/services/appmgr/src/app_spawn_client.cpp.patch"
        "foundation/ability/ability_runtime/services/appmgr/include/remote_client_manager.h.patch"
        "foundation/ability/ability_runtime/services/appmgr/src/remote_client_manager.cpp.patch"
        "base/security/selinux_adapter/sepolicy/ohos_policy/startup/appspawn/system/file_contexts.patch"
        "third_party/musl/config/ld-musl-namespace-arm.ini.patch"
        # The retired product patch registered an in-tree oh_adapter component.
        # R45 integrates adapter bytes post-image, so full-product keeps the
        # official wukong100 component graph instead.
        "base/startup/init/services/init/include/init_service.h.patch"
        # adapter project (2026-05-20 A+B 改造): Android Activity-stack semantics
        # via OH Mission multi-ability mode.  See doc/build_patch_log.html I.A+B.
        "foundation/ability/ability_runtime/services/abilitymgr/src/ability_record.cpp.patch"
        "foundation/ability/ability_runtime/services/abilitymgr/include/mission/mission.h.patch"
        "foundation/ability/ability_runtime/services/abilitymgr/src/mission/mission.cpp.patch"
        "foundation/ability/ability_runtime/services/abilitymgr/include/mission/mission_list_manager.h.patch"
        "foundation/ability/ability_runtime/services/abilitymgr/src/mission/mission_list_manager.cpp.patch"
        # HanBing's app_internal.gni module-only loader cut is intentionally
        # excluded from the wukong100 full-product graph.  The historical patch
        # remains under ohos_patches for an explicit legacy workflow only.
        # The retired updater patch removed an official graphic_utils_lite
        # dependency.  wukong100 declares that component and the four updater
        # objects build with the official edge, so the full graph keeps it.
        # 2026-05-21 Phase 7: graphic_2d transaction + graphic_surface buffer_queue
        # 2026-05-21 Phase 7: AppMS token fallback (G2.14h);缺则 child accessTokenId=0 → onResume 不触发
        "foundation/ability/ability_runtime/services/appmgr/src/app_mgr_service_inner.cpp.patch"
        # 2026-05-27 orphan-audit 收口:icu/skia cross-compile 修补(std::div→手写除模;OH
        # clang/musl 缺 std::div(long long) 重载)。历史已应用到 ECS 源但漏列 → repo sync 必丢
        # → libskia_canvaskit 编译断。reverse-check 验证为有效 diff。
        "third_party/icu/icu4c/source/i18n/decimfmt.cpp.patch"
        "third_party/icu/icu4c/source/i18n/number_decimalquantity.cpp.patch"
        "third_party/skia/m133/third_party/externals/icu/source/i18n/decimfmt.cpp.patch"
        "third_party/skia/m133/third_party/externals/icu/source/i18n/number_decimalquantity.cpp.patch"
        # 2026-05-27 orphan-audit:application_info.h 加 BundleType::APP_ANDROID=10(libbms/
        # base_bundle_installer 硬依赖)。已重派生为 OH-root 相对路径。
        "foundation/bundlemanager/bundle_framework/interfaces/inner_api/appexecfwk_base/include/application_info.h.patch"
    )

    # ---- Layer 1: exact oracle + structured patch manifest ----
    local oracle_source="$ADAPTER_ROOT/build/inner/ohos_diff_patch_oracle.tsv"
    local input_snapshot oracle_file lock_dir="" lock_owned=0 marker_tmp=""
    local oracle_header oracle_rows duplicate_rows bad_oracle_rows patch_version_output patch_version
    if ! command -v sha256sum >/dev/null 2>&1; then
        log_warn "required SHA-256 tool not found: sha256sum"
        return 1
    fi
    patch_version_output=$(patch --version 2>/dev/null) || {
        log_warn "required patch tool does not support --version"
        return 1
    }
    patch_version=${patch_version_output%%$'\n'*}
    [ -n "$patch_version" ] || {
        log_warn "patch --version returned an empty identity"
        return 1
    }
    log_info "  patch_tool=$patch_version"
    if ! _ohos_assert_no_symlink_components "$ADAPTER_ROOT" "build/inner/ohos_diff_patch_oracle.tsv" \
        || [ ! -s "$oracle_source" ]; then
        log_warn "mandatory exact patch oracle missing or unsafe: $oracle_source"
        return 1
    fi
    input_snapshot=$(mktemp -d "${TMPDIR:-/tmp}/ohos-patch-input.XXXXXX") || return 1
    trap 'rm -rf "$input_snapshot"; if [ -n "$marker_tmp" ]; then rm -f "$marker_tmp"; fi; if [ "$lock_owned" = "1" ]; then rmdir "$lock_dir" 2>/dev/null || true; fi' EXIT
    oracle_file="$input_snapshot/ohos_diff_patch_oracle.tsv"
    cp "$oracle_source" "$oracle_file" || return 1
    IFS= read -r oracle_header < "$oracle_file" || return 1
    if [ "$oracle_header" != $'patch\ttarget\tpatch_sha256\tpre_sha256\tpost_sha256' ]; then
        log_warn "invalid exact patch oracle header: $oracle_file"
        return 1
    fi
    oracle_rows=$(awk 'NR > 1 { count++ } END { print count + 0 }' "$oracle_file") || return 1
    duplicate_rows=$(awk -F '\t' 'NR > 1 { rel[$1]++; target[$2]++ } END {
        for (key in rel) if (rel[key] != 1) bad++;
        for (key in target) if (target[key] != 1) bad++;
        print bad + 0
    }' "$oracle_file") || return 1
    bad_oracle_rows=$(awk -F '\t' 'NR > 1 && (NF != 5 || $0 ~ /\r/) { bad++ } END { print bad + 0 }' "$oracle_file") || return 1
    if [ "$oracle_rows" != "${#OH_DIFF_PATCH_LIST[@]}" ] \
        || [ "$duplicate_rows" != "0" ] || [ "$bad_oracle_rows" != "0" ]; then
        log_warn "exact patch oracle cardinality/uniqueness mismatch"
        return 1
    fi

    local marker_dir="$OH_ROOT/.adapter_applied"
    local marker="$marker_dir/ohos_service"
    local rel source_patch_file patch_file target parsed_target oracle_entry expected_patch_sha expected_pre_sha expected_post_sha
    local actual_patch_sha patch_bytes patch_manifest="" expected_post_manifest=""
    for rel in "${OH_DIFF_PATCH_LIST[@]}"; do
        source_patch_file="$ADAPTER_ROOT/ohos_patches/$rel"
        if ! _ohos_assert_no_symlink_components "$ADAPTER_ROOT" "ohos_patches/$rel" \
            || [ ! -s "$source_patch_file" ]; then
            log_warn "mandatory patch missing, empty, or symlink: $rel"
            return 1
        fi
        patch_file="$input_snapshot/ohos_patches/$rel"
        mkdir -p "$(dirname "$patch_file")" || return 1
        cp "$source_patch_file" "$patch_file" || return 1
        parsed_target=$(_ohos_patch_target "$patch_file") || {
            log_warn "patch must contain exactly one safe old/new target: $rel"
            return 1
        }
        oracle_entry=$(_ohos_oracle_entry "$oracle_file" "$rel") || {
            log_warn "patch missing or duplicated in exact oracle: $rel"
            return 1
        }
        IFS=$'\t' read -r target expected_patch_sha expected_pre_sha expected_post_sha <<< "$oracle_entry"
        if [ "$parsed_target" != "$target" ]; then
            log_warn "patch target differs from exact oracle: $rel"
            return 1
        fi
        if ! _ohos_is_sha256 "$expected_patch_sha" \
            || ! _ohos_is_sha256 "$expected_pre_sha" \
            || ! _ohos_is_sha256 "$expected_post_sha"; then
            log_warn "invalid SHA-256 field in exact oracle: $rel"
            return 1
        fi
        if [ "$expected_pre_sha" = "$expected_post_sha" ]; then
            log_warn "exact oracle pre/post hashes must differ: $rel"
            return 1
        fi
        actual_patch_sha=$(_ohos_sha256_file "$patch_file") || return 1
        if [ "$actual_patch_sha" != "$expected_patch_sha" ]; then
            log_warn "patch SHA-256 differs from exact oracle: $rel"
            return 1
        fi
        patch_bytes=$(wc -c < "$patch_file" | tr -d ' ') || return 1
        printf -v patch_manifest '%s%s\t%s\t%s\n' "$patch_manifest" "$rel" "$patch_bytes" "$actual_patch_sha"
    done

    while IFS=$'\t' read -r rel target expected_patch_sha expected_pre_sha expected_post_sha; do
        [ "$rel" = "patch" ] && continue
        printf -v expected_post_manifest '%s%s\t%s\n' "$expected_post_manifest" "$target" "$expected_post_sha"
    done < "$oracle_file"

    local patch_sig oracle_sig expected_post_sig target_sig marker_value stored_marker
    patch_sig=$(_ohos_sha256_string "$patch_manifest") || return 1
    oracle_sig=$(_ohos_sha256_file "$oracle_file") || return 1
    expected_post_sig=$(_ohos_sha256_string "$expected_post_manifest") || return 1
    marker_value="v3:$patch_sig:$oracle_sig:$expected_post_sig"

    _ohos_assert_no_symlink_components "$OH_ROOT" ".adapter_applied" 1 || return 1
    mkdir -p "$marker_dir" || return 1
    _ohos_assert_no_symlink_components "$OH_ROOT" ".adapter_applied" || return 1
    lock_dir="$marker_dir/ohos_service.lock"
    if ! mkdir "$lock_dir" 2>/dev/null; then
        log_warn "another OH patch preparation owns the lock: $lock_dir"
        return 1
    fi
    lock_owned=1

    if [ -e "$marker" ]; then
        if ! _ohos_assert_no_symlink_components "$OH_ROOT" ".adapter_applied/ohos_service" \
            || [ ! -f "$marker" ]; then
            log_warn "exact patch marker is not a regular non-symlink file"
            return 1
        fi
        stored_marker=$(cat "$marker" 2>/dev/null) || return 1
        if [ "$stored_marker" != "$marker_value" ]; then
            # A manifest/oracle revision invalidates the fast-path certificate,
            # but it must not force a manual marker deletion.  Drop only the
            # already-validated regular marker, then re-enter the exact per-file
            # pre/post checks below.  Any real target drift still fails closed.
            log_info "stale/legacy marker ignored; revalidating every exact target"
            rm -f "$marker" || return 1
        else
            target_sig=$(_ohos_current_target_sha256 "$oracle_file") || return 1
            if [ "$target_sig" != "$expected_post_sig" ]; then
                log_warn "target SHA-256 drift after marker; refusing to bless or reapply"
                return 1
            fi
            log_ok "B6b: OH patches already applied (exact oracle marker) — skip"
            return 0
        fi
    fi

    _ohos_normalize_known_crlf_targets "$oracle_file" || return 1

    # ---- Layer 2: current bytes must equal oracle pre or oracle post ----
    local PATCH_APPLIED=0 PATCH_SKIPPED=0 current_sha
    for rel in "${OH_DIFF_PATCH_LIST[@]}"; do
        patch_file="$input_snapshot/ohos_patches/$rel"
        oracle_entry=$(_ohos_oracle_entry "$oracle_file" "$rel") || return 1
        IFS=$'\t' read -r target expected_patch_sha expected_pre_sha expected_post_sha <<< "$oracle_entry"
        if ! _ohos_assert_no_symlink_components "$OH_ROOT" "$target" \
            || [ ! -f "$OH_ROOT/$target" ]; then
            log_warn "oracle target is not a regular non-symlink file: $target"
            return 1
        fi
        current_sha=$(_ohos_sha256_file "$OH_ROOT/$target") || return 1
        if [ "$current_sha" = "$expected_post_sha" ]; then
            if ! patch --force -R --fuzz=0 --no-backup-if-mismatch --dry-run -p1 -d "$OH_ROOT" < "$patch_file" >/dev/null 2>&1; then
                log_warn "oracle post-image failed strict reverse check: $rel"
                return 1
            fi
            PATCH_SKIPPED=$((PATCH_SKIPPED+1))
        elif [ "$current_sha" = "$expected_pre_sha" ]; then
            if ! patch --force --forward --fuzz=0 --no-backup-if-mismatch --dry-run -p1 -d "$OH_ROOT" < "$patch_file" >/dev/null 2>&1; then
                log_warn "oracle pre-image failed strict forward check: $rel"
                return 1
            fi
            if ! patch --force --forward --fuzz=0 --no-backup-if-mismatch -p1 -d "$OH_ROOT" < "$patch_file"; then
                log_warn "strict apply failed after successful dry-run: $rel"
                return 1
            fi
            current_sha=$(_ohos_sha256_file "$OH_ROOT/$target") || return 1
            if [ "$current_sha" != "$expected_post_sha" ]; then
                log_warn "strict apply did not produce the exact oracle post-image: $rel"
                return 1
            fi
            if [ "$apply_mode" = "dry-run" ]; then
                log_info "[dry-run] APPLY: $rel"
            else
                log_ok "APPLY: $rel"
            fi
            PATCH_APPLIED=$((PATCH_APPLIED+1))
        else
            log_warn "target differs from both exact oracle pre/post images: $rel"
            return 1
        fi
    done
    log_info "B6b summary: $PATCH_APPLIED applied / $PATCH_SKIPPED already-applied / 0 failed"

    target_sig=$(_ohos_current_target_sha256 "$oracle_file") || return 1
    if [ "$target_sig" != "$expected_post_sig" ]; then
        log_warn "final target manifest differs from exact oracle post-image"
        return 1
    fi
    _ohos_assert_no_symlink_components "$OH_ROOT" ".adapter_applied" 1 || return 1
    mkdir -p "$marker_dir" || return 1
    _ohos_assert_no_symlink_components "$OH_ROOT" ".adapter_applied" || return 1
    marker_tmp=$(mktemp "$marker_dir/ohos_service.tmp.XXXXXX") || return 1
    if [ -L "$marker_tmp" ] || [ ! -f "$marker_tmp" ]; then
        log_warn "mktemp did not create a regular marker file"
        return 1
    fi
    chmod 600 "$marker_tmp" || return 1
    printf '%s\n' "$marker_value" > "$marker_tmp" || return 1
    [ -f "$marker_tmp" ] && [ ! -L "$marker_tmp" ] || return 1
    mv -f "$marker_tmp" "$marker" || return 1
    marker_tmp=""
    _ohos_assert_no_symlink_components "$OH_ROOT" ".adapter_applied/ohos_service" || return 1
    [ "$(cat "$marker")" = "$marker_value" ] || return 1
    return 0
)

# ============================================================================
# 以下 helper 由 restore_after_sync.sh 的历史内联段搬入(2026-05-27
# (b) 批收口),使 apply_ohos_patches 成为完整 OH 源准备。各自幂等。restore 对应内联段已删,
# 改由 B6b 处的 apply_ohos_patches 顶层调用统一覆盖。
# ============================================================================

# B6 — graphic_2d rs_buffer_reclaim.cpp (%u → %zu format fix), exact pre/post oracle。
apply_ohos_b6_buffer_reclaim() {
    log_info "B6. Apply graphic_2d rs_buffer_reclaim.cpp.patch (size_t format)"
    _ohos_apply_exact_aux_patch B6 "foundation/graphic/graphic_2d"
}

# B9 — legacy rk3568 module-only ets2abc_config.gni cut, exact pre/post oracle。
apply_ohos_b9_ets2abc() {
    if [ "${OHOS_PATCH_PROFILE:-}" != "legacy-rk3568-module-only" ]; then
        log_warn "B9 is retired from the canonical wukong100 full-product profile"
        return 1
    fi
    log_info "B9. Apply ets2abc_config.gni collision fix"
    _ohos_apply_exact_aux_patch B9 "" \
        "build/config/components/ets_frontend/ets2abc_config.gni.before_collision_fix"
}

# B10 — 把 apk_manifest_parser.{h,cpp} + adapter_apk_install_minimal.cpp 部署进 bmgr/src/
# (gn 禁跨组件 include,libbms 编译期需就地);source snapshot + atomic exact copy。
apply_ohos_b10_bmgr_sources() (
    log_info "B10. Deploy apk_manifest_parser + adapter_apk_install_minimal into bundlemgr/src/"
    local bms_rel="foundation/bundlemanager/bundle_framework/services/bundlemgr/src"
    local BMS_SRC_DIR snapshot lock_dir="" lock_owned=0 spec source_rel dest_name snapshot_file source_sha dest_tmp=""
    local specs=(
        "framework/package-manager/jni/apk_manifest_parser.h|apk_manifest_parser.h"
        "framework/package-manager/jni/apk_manifest_parser.cpp|apk_manifest_parser.cpp"
        "ohos_patches/bundle_framework/services/bundlemgr/src/adapter_apk_install_minimal.cpp|adapter_apk_install_minimal.cpp"
    )
    ADAPTER_ROOT=$(cd "$ADAPTER_ROOT" && pwd -P) || return 1
    OH_ROOT=$(cd "$OH_ROOT" && pwd -P) || return 1
    BMS_SRC_DIR="$OH_ROOT/$bms_rel"
    if ! _ohos_assert_no_symlink_components "$OH_ROOT" "$bms_rel" || [ ! -d "$BMS_SRC_DIR" ]; then
        log_warn "B10 failed — bundlemgr src dir not found: $BMS_SRC_DIR"
        return 1
    fi
    snapshot=$(mktemp -d "${TMPDIR:-/tmp}/ohos-b10-input.XXXXXX") || return 1
    trap 'rm -rf "$snapshot"; if [ -n "$dest_tmp" ]; then rm -f "$dest_tmp"; fi; if [ "$lock_owned" = "1" ]; then rmdir "$lock_dir" 2>/dev/null || true; fi' EXIT
    for spec in "${specs[@]}"; do
        IFS='|' read -r source_rel dest_name <<< "$spec"
        if ! _ohos_assert_no_symlink_components "$ADAPTER_ROOT" "$source_rel" \
            || [ ! -f "$ADAPTER_ROOT/$source_rel" ]; then
            log_warn "B10 failed — canonical source missing or symlinked: $source_rel"
            return 1
        fi
        snapshot_file="$snapshot/$dest_name"
        cp "$ADAPTER_ROOT/$source_rel" "$snapshot_file" || return 1
        _ohos_sha256_file "$snapshot_file" >/dev/null || return 1
        if [ -L "$BMS_SRC_DIR/$dest_name" ]; then
            log_warn "B10 failed — destination is symlinked: $dest_name"
            return 1
        fi
        if [ -e "$BMS_SRC_DIR/$dest_name" ] \
            && ! _ohos_assert_no_symlink_components "$OH_ROOT" "$bms_rel/$dest_name"; then
            log_warn "B10 failed — destination is symlinked: $dest_name"
            return 1
        fi
    done
    if [ "${DRY_RUN:-0}" = "1" ]; then
        log_info "[dry-run] B10 exact source snapshots would replace 3 managed files"
        return 0
    fi
    _ohos_assert_no_symlink_components "$OH_ROOT" ".adapter_applied" 1 || return 1
    mkdir -p "$OH_ROOT/.adapter_applied" || return 1
    _ohos_assert_no_symlink_components "$OH_ROOT" ".adapter_applied" || return 1
    lock_dir="$OH_ROOT/.adapter_applied/ohos_aux_B10.lock"
    mkdir "$lock_dir" 2>/dev/null || return 1
    lock_owned=1
    for spec in "${specs[@]}"; do
        IFS='|' read -r source_rel dest_name <<< "$spec"
        snapshot_file="$snapshot/$dest_name"
        source_sha=$(_ohos_sha256_file "$snapshot_file") || return 1
        dest_tmp=$(mktemp "$BMS_SRC_DIR/.${dest_name}.tmp.XXXXXX") || return 1
        cp "$snapshot_file" "$dest_tmp" || return 1
        chmod 0644 "$dest_tmp" || return 1
        [ "$(_ohos_sha256_file "$dest_tmp")" = "$source_sha" ] || return 1
        mv -f "$dest_tmp" "$BMS_SRC_DIR/$dest_name" || return 1
        dest_tmp=""
        _ohos_assert_no_symlink_components "$OH_ROOT" "$bms_rel/$dest_name" || return 1
        [ "$(_ohos_sha256_file "$BMS_SRC_DIR/$dest_name")" = "$source_sha" ] || return 1
    done
    log_ok "B10: 3 files deployed into $BMS_SRC_DIR"
    return 0
)
