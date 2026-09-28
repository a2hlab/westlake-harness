#!/usr/bin/env bash
# Fixed R45 / OpenHarmony 6.1 LTS / wukong100 BASE-image build wrapper.
#
# This entry builds only the stock OpenHarmony base images.  Adapter payload
# compilation and image integration belong to
# build_wukong100_adapter_product.sh, whose readback gates consume this base.

set -Eeo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ADAPTER_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"

readonly GENERATION="R45"
readonly OH_PRODUCT_NAME="wukong100"
readonly OH_ROOT="/opt/build-trees/oh610_lts_source"
readonly OUT_DIR="$OH_ROOT/out/$OH_PRODUCT_NAME"
readonly RUN_ROOT="/opt/build-trees/build-runs/r45-wukong100"
readonly LOCK_ROOT="/opt/build-trees/.locks"
readonly LOCK_FILE="$LOCK_ROOT/r45-oh610-wukong100-full.lock"

readonly OH_PYTHON_ROOT="$OH_ROOT/prebuilts/python/linux-x86/3.11.4"
readonly OH_BUILD_TOOLS="$OH_ROOT/prebuilts/build-tools/linux-x86/bin"
readonly NINJA="$OH_BUILD_TOOLS/ninja"
readonly VALIDATOR="$ADAPTER_ROOT/build/verify_wukong100_full_product_inputs.sh"
readonly PHASE0="$ADAPTER_ROOT/build/inner/apply_ohos_patches.sh"

# Exact environment from the successful 2026-07-13 AlexPC build.
readonly PINNED_LIBRARY_PATH="/usr/lib/gcc/x86_64-linux-gnu/12:/usr/lib/gcc/x86_64-linux-gnu/11:/usr/lib/x86_64-linux-gnu"
readonly PINNED_CCACHE="/usr/bin/ccache"
readonly PINNED_CCACHE_DIR="/home/alexyang/.ccache"
readonly PINNED_CCACHE_BASEDIR="$OH_ROOT"
readonly PINNED_CCACHE_UMASK="002"
readonly PINNED_CCACHE_MAXSIZE="200G"
readonly PINNED_GN_ARGS='linux_use_bundled_binutils_override=false cc_wrapper="/usr/bin/ccache"'

# These three files define the build CLI semantics on which this wrapper
# depends.  In particular, this HB version accepts the historical `-j2` but
# silently ignores it; `--ninja-args=-j2` is what actually limits Ninja.
readonly EXPECTED_BUILD_SH_SHA="510f780f85f68d105292d054791c4fbb854ab55bd6d9c67481eeb5e83401f04f"
readonly EXPECTED_BUILDARGS_SHA="9d7f8a713db720b5aaaa0f0a3f58d36b4a4c6404e963c456d797666ffa310f92"
readonly EXPECTED_NINJA_PY_SHA="accf572c18e3b8998ac58860355cca51c46f74e9385d8fe55b9322799a91e16f"

readonly -a HISTORICAL_BUILD_ARGS=(
    --product-name wukong100
    --ccache
    -j2
    --gn-args "$PINNED_GN_ARGS"
    --prebuilts-sdk-gn-args linux_use_bundled_binutils_override=false
)

readonly -a FIVE_TARGETS=(
    obj/base/inputmethod/imf/services/dialog/input_method_choose_hap/js_assets.zip
    obj/base/location/location/services/location_ui/location_dialog_hap/js_assets.zip
    obj/base/notification/distributed_notification_service/services/dialog_ui/enable_notification_dialog/enable_notification_dialog_hap/js_assets.zip
    obj/applications/standard/auth_widget/auth_widget/js_assets.zip
    obj/base/usb/usb_manager/frameworks/dialog/dialog_ui/usb_right_dialog/dialog_hap/js_assets.zip
)

readonly -a IMAGE_ARTIFACTS=(
    chip_prod.img
    eng_system.img
    ramdisk.img
    sys_prod.img
    system.img
    updater.img
    userdata.img
    vendor.img
)

DRY_RUN=0
RUN_DIR=""
ACTIVE_PID=""
ACTIVE_PGID=""
MONITOR_PID=""
LAST_STAGE="preflight"
LAST_LOG=""
FINALIZED=0
FINALIZING=0

usage() {
    cat <<'EOF'
Usage: build/build_wukong100_full.sh [--dry-run]

Build the fixed R45 OpenHarmony 6.1 LTS wukong100 BASE images on AlexPC.

  --dry-run  Print the exact immutable stage contract.  Do not acquire a lock,
             create a run directory, apply patches, generate GN, or run Ninja.
  --help     Show this help.

The generation and product are not configurable.  This entry never creates,
integrates, or verifies an adapter generation and must not be reported as an
adapter product build.
EOF
}

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --help|-h) usage; exit 0 ;;
        *) printf 'ERROR unknown argument: %s\n' "$arg" >&2; usage >&2; exit 64 ;;
    esac
done

shell_join() {
    local arg
    for arg in "$@"; do
        printf '%q ' "$arg"
    done
}

print_contract() {
    local -a gn_cmd full_cmd target_cmd validator_cmd ccache_gate_cmd
    gn_cmd=("$OH_ROOT/build.sh" "${HISTORICAL_BUILD_ARGS[@]}" --build-only-gn)
    validator_cmd=(env OH_ROOT="$OH_ROOT" OH_PRODUCT_NAME="$OH_PRODUCT_NAME" "$VALIDATOR")
    target_cmd=("$NINJA" -j2 -w dupbuild=warn -C "$OUT_DIR" "${FIVE_TARGETS[@]}")
    ccache_gate_cmd=(ccache_graph_gate "$OUT_DIR/args.gn" "$OUT_DIR/toolchain.ninja" "$OUT_DIR/clang_x64/toolchain.ninja")
    full_cmd=("$OH_ROOT/build.sh" "${HISTORICAL_BUILD_ARGS[@]}" --ninja-args=-j2 --fast-rebuild --build-target images)

    printf 'DRY_RUN generation=%s product=%s scope=BASE_ONLY\n' "$GENERATION" "$OH_PRODUCT_NAME"
    printf 'DRY_RUN adapter_root=%s\n' "$ADAPTER_ROOT"
    printf 'DRY_RUN oh_root=%s\n' "$OH_ROOT"
    printf 'DRY_RUN run_root=%s\n' "$RUN_ROOT"
    printf 'DRY_RUN lock=%s\n' "$LOCK_FILE"
    printf 'DRY_RUN LIBRARY_PATH=%s\n' "$PINNED_LIBRARY_PATH"
    printf 'DRY_RUN USE_CCACHE=1 CCACHE_EXEC=%s CCACHE_DIR=%s CCACHE_BASEDIR=%s CCACHE_UMASK=%s CCACHE_MAXSIZE=%s\n' \
        "$PINNED_CCACHE" "$PINNED_CCACHE_DIR" "$PINNED_CCACHE_BASEDIR" "$PINNED_CCACHE_UMASK" "$PINNED_CCACHE_MAXSIZE"
    printf 'DRY_RUN phase0=source %q && apply_ohos_patches\n' "$PHASE0"
    printf 'DRY_RUN gn='; shell_join "${gn_cmd[@]}"; printf '\n'
    printf 'DRY_RUN ccache_graph_post_gn='; shell_join "${ccache_gate_cmd[@]}"; printf '\n'
    printf 'DRY_RUN validator_pre_target='; shell_join "${validator_cmd[@]}"; printf '\n'
    printf 'DRY_RUN five_targets='; shell_join "${target_cmd[@]}"; printf '\n'
    printf 'DRY_RUN ccache_graph_post_targets='; shell_join "${ccache_gate_cmd[@]}"; printf '\n'
    printf 'DRY_RUN validator_pre_full='; shell_join "${validator_cmd[@]}"; printf '\n'
    printf 'DRY_RUN ccache_graph_pre_full='; shell_join "${ccache_gate_cmd[@]}"; printf '\n'
    printf 'DRY_RUN full='; shell_join "${full_cmd[@]}"; printf '\n'
    printf 'DRY_RUN_BASE_ONLY_PASS no process started and no filesystem state created\n'
}

if [ "$DRY_RUN" = "1" ]; then
    print_contract
    exit 0
fi

export OH_ROOT OH_PRODUCT_NAME ADAPTER_ROOT
export PATH="$OH_BUILD_TOOLS:$OH_PYTHON_ROOT/bin:$PATH"
export PYTHONPATH="$OH_PYTHON_ROOT/lib/python3.11/site-packages"
export LIBRARY_PATH="$PINNED_LIBRARY_PATH"
export USE_CCACHE=1
export CCACHE_EXEC="$PINNED_CCACHE"
export CCACHE_DIR="$PINNED_CCACHE_DIR"
export CCACHE_BASEDIR="$PINNED_CCACHE_BASEDIR"
export CCACHE_UMASK="$PINNED_CCACHE_UMASK"
export CCACHE_MAXSIZE="$PINNED_CCACHE_MAXSIZE"

sha256_file() {
    sha256sum "$1" | awk '{print $1}'
}

expect_sha() {
    local file="$1" expected="$2" label="$3" actual
    if [ ! -f "$file" ] || [ -L "$file" ]; then
        printf 'ERROR %s is absent or not a regular non-symlink file: %s\n' "$label" "$file" >&2
        return 1
    fi
    actual="$(sha256_file "$file")" || return 1
    if [ "$actual" != "$expected" ]; then
        printf 'ERROR %s drift: expected=%s actual=%s file=%s\n' \
            "$label" "$expected" "$actual" "$file" >&2
        return 1
    fi
}

preflight() {
    local path
    local -a library_paths
    [ "${BASH_VERSINFO[0]}" -ge 4 ] || { printf 'ERROR Bash 4+ required for process provenance tracking\n' >&2; return 1; }
    [ "$(uname -s)" = "Linux" ] || { printf 'ERROR Linux host required\n' >&2; return 1; }
    [ "$(uname -m)" = "x86_64" ] || { printf 'ERROR x86_64 host required\n' >&2; return 1; }
    [ "$(readlink -f "$OH_ROOT")" = "$OH_ROOT" ] || { printf 'ERROR OH_ROOT must be a real absolute root: %s\n' "$OH_ROOT" >&2; return 1; }
    [ -x "$OH_ROOT/build.sh" ] || { printf 'ERROR missing OH build.sh: %s\n' "$OH_ROOT/build.sh" >&2; return 1; }
    [ -x "$NINJA" ] || { printf 'ERROR missing Ninja: %s\n' "$NINJA" >&2; return 1; }
    [ -x "$OH_PYTHON_ROOT/bin/python3" ] || { printf 'ERROR missing OH Python\n' >&2; return 1; }
    [ -x "$VALIDATOR" ] || { printf 'ERROR missing validator: %s\n' "$VALIDATOR" >&2; return 1; }
    [ -f "$PHASE0" ] && [ ! -L "$PHASE0" ] || { printf 'ERROR missing Phase0: %s\n' "$PHASE0" >&2; return 1; }
    [ -x "$PINNED_CCACHE" ] || { printf 'ERROR missing pinned ccache: %s\n' "$PINNED_CCACHE" >&2; return 1; }
    [ -d "$PINNED_CCACHE_DIR" ] && [ ! -L "$PINNED_CCACHE_DIR" ] \
        || { printf 'ERROR missing preserved ccache directory: %s\n' "$PINNED_CCACHE_DIR" >&2; return 1; }
    command -v flock >/dev/null 2>&1 || { printf 'ERROR flock is required\n' >&2; return 1; }
    IFS=: read -r -a library_paths <<< "$PINNED_LIBRARY_PATH"
    for path in "${library_paths[@]}"; do
        [ -d "$path" ] || { printf 'ERROR missing pinned LIBRARY_PATH entry: %s\n' "$path" >&2; return 1; }
    done

    expect_sha "$OH_ROOT/build.sh" "$EXPECTED_BUILD_SH_SHA" "OH build.sh" || return 1
    expect_sha "$OH_ROOT/build/hb/resources/args/default/buildargs.json" "$EXPECTED_BUILDARGS_SHA" "HB build args schema" || return 1
    expect_sha "$OH_ROOT/build/hb/services/ninja.py" "$EXPECTED_NINJA_PY_SHA" "HB Ninja service" || return 1
}

process_is_our_build() {
    local proc="$1" pid exe cwd cmd
    pid="${proc##*/}"
    [ "$pid" != "$$" ] || return 1
    [ -r "$proc/cmdline" ] || return 1
    exe="$(basename "$(readlink -f "$proc/exe" 2>/dev/null || true)")"
    cwd="$(readlink -f "$proc/cwd" 2>/dev/null || true)"
    cmd="$(tr '\0' ' ' < "$proc/cmdline" 2>/dev/null || true)"

    case "$exe" in
        ninja)
            [[ "$cwd" == "$OUT_DIR"* || "$cmd" == *"out/wukong100"* ]] || return 1
            ;;
        bash|sh)
            [[ "$cwd" == "$OH_ROOT"* && "$cmd" == *"build.sh"* && "$cmd" == *"wukong100"* ]] || return 1
            ;;
        python|python3|python3.*)
            [[ "$cwd" == "$OH_ROOT"* ]] || return 1
            [[ "$cmd" == *"build.py"* || "$cmd" == *"build/hb/main.py"* ]] || return 1
            ;;
        *) return 1 ;;
    esac

    printf '%s\t%s\t%s\t%s\n' "$pid" "$exe" "$cwd" "$cmd"
}

reject_active_build_chain() {
    local proc found=0
    for proc in /proc/[0-9]*; do
        if process_is_our_build "$proc"; then
            found=1
        fi
    done
    if [ "$found" -ne 0 ]; then
        printf 'ERROR an existing wukong100 build chain is active; refusing a duplicate build\n' >&2
        return 1
    fi
}

atomic_write() {
    local destination="$1" tmp
    tmp="${destination}.tmp.$$"
    if ! cat > "$tmp"; then
        rm -f "$tmp"
        return 1
    fi
    if ! mv -f "$tmp" "$destination"; then
        rm -f "$tmp"
        return 1
    fi
}

write_summary() {
    local state="$1" detail="$2" next="$3"
    {
        printf '当前难点：%s\n' "$detail"
        printf '已证：generation=%s；product=%s；周末构建参数和真实 Ninja 并发参数已固定。\n' "$GENERATION" "$OH_PRODUCT_NAME"
        printf '正在做：%s\n' "$state"
        printf '下一步：%s\n' "$next"
        printf '依赖：AlexPC 固定 OH6.1 LTS 源、官方 prebuilts、固定 ccache/LIBRARY_PATH。\n'
    } | atomic_write "$RUN_DIR/SUMMARY.txt"
}

is_descendant_of() {
    local pid="$1" ancestor="$2" ppid
    while [ "$pid" -gt 1 ] 2>/dev/null; do
        [ "$pid" = "$ancestor" ] && return 0
        ppid="$(awk '/^PPid:/{print $2}' "/proc/$pid/status" 2>/dev/null || true)"
        [ -n "$ppid" ] || return 1
        pid="$ppid"
    done
    return 1
}

monitor_stage_processes() {
    local stage="$1" root_pid="$2" proc pid exe cwd cmd key now
    declare -A seen=()
    while kill -0 "$root_pid" 2>/dev/null; do
        now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        for proc in /proc/[0-9]*; do
            pid="${proc##*/}"
            is_descendant_of "$pid" "$root_pid" || continue
            exe="$(basename "$(readlink -f "$proc/exe" 2>/dev/null || true)")"
            cmd="$(tr '\0' ' ' < "$proc/cmdline" 2>/dev/null || true)"
            case "$exe:$cmd" in
                bash:*build.sh*|python*:*build.py*|python*:*build/hb/main.py*|ninja:*) ;;
                *) continue ;;
            esac
            key="$stage:$pid"
            [ -z "${seen[$key]:-}" ] || continue
            seen[$key]=1
            cwd="$(readlink -f "$proc/cwd" 2>/dev/null || true)"
            printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$now" "$stage" "$pid" "$exe" "$cwd" "$cmd" >> "$RUN_DIR/pids.tsv"
        done
        sleep 2
    done
}

stop_monitor() {
    local pid="${MONITOR_PID:-}"
    MONITOR_PID=""
    [ -n "$pid" ] || return 0
    kill -TERM "$pid" 2>/dev/null || true
    if wait "$pid" 2>/dev/null; then
        :
    else
        :
    fi
}

process_group_has_live_members() {
    local pgid="$1"
    ps -eo pgid=,stat= 2>/dev/null | awk -v wanted="$pgid" '
        $1 == wanted && $2 !~ /^Z/ { found = 1 }
        END { exit(found ? 0 : 1) }
    '
}

terminate_active_stage() {
    local pid="${ACTIVE_PID:-}" pgid="${ACTIVE_PGID:-}" wrapper_pgid attempt
    stop_monitor
    [ -n "$pid" ] || return 0

    wrapper_pgid="$(ps -o pgid= -p $$ 2>/dev/null | tr -d '[:space:]')"
    if [[ "$pgid" =~ ^[0-9]+$ ]] && [ "$pgid" -gt 1 ] \
        && [ "$pgid" != "$wrapper_pgid" ]; then
        # Every stage is launched as its own process group.  Signal the whole
        # group so build.py/Ninja cannot outlive the receipt that closes it.
        kill -TERM -- "-$pgid" 2>/dev/null || true
        for ((attempt = 0; attempt < 50; attempt++)); do
            process_group_has_live_members "$pgid" || break
            sleep 0.1
        done
        if process_group_has_live_members "$pgid"; then
            kill -KILL -- "-$pgid" 2>/dev/null || true
        fi
    else
        # Fail closed if process-group provenance is unexpectedly unavailable.
        # The stage root remains our direct child and is still reaped below.
        kill -TERM "$pid" 2>/dev/null || true
    fi

    if wait "$pid" 2>/dev/null; then
        :
    else
        :
    fi
    if [[ "$pgid" =~ ^[0-9]+$ ]] && [ "$pgid" -gt 1 ] \
        && [ "$pgid" != "$wrapper_pgid" ]; then
        for ((attempt = 0; attempt < 20; attempt++)); do
            process_group_has_live_members "$pgid" || break
            kill -KILL -- "-$pgid" 2>/dev/null || true
            sleep 0.1
        done
    fi
    ACTIVE_PID=""
    ACTIVE_PGID=""
}

record_stage() {
    local stage="$1" started="$2" ended="$3" pid="$4" rc="$5" log="$6" command="$7" log_sha="MISSING"
    [ -f "$log" ] && log_sha="$(sha256_file "$log")"
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$stage" "$started" "$ended" "$pid" "$rc" "$log" "$log_sha" "$command" >> "$RUN_DIR/stages.tsv"
}

run_stage() {
    local stage="$1" log="$2" command="$3" started ended rc pid job_control_was_enabled=0
    shift 3
    LAST_STAGE="$stage"
    LAST_LOG="$log"
    started="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    write_summary "$stage" "none" "等待该阶段精确 rc；失败则封存第一条事实 marker。"

    [[ "$-" == *m* ]] && job_control_was_enabled=1
    set -m
    "$@" > "$log" 2>&1 &
    pid=$!
    [ "$job_control_was_enabled" -eq 1 ] || set +m
    ACTIVE_PID="$pid"
    # Bash monitor mode gives the background stage a dedicated process group
    # whose PGID is its root PID.  The monitor itself is started after monitor
    # mode is restored, so it is never included in this kill domain.
    ACTIVE_PGID="$pid"
    printf '%s\t%s\t%s\t%s\n' "$started" "$stage" "$pid" "$command" >> "$RUN_DIR/stage-starts.tsv"
    monitor_stage_processes "$stage" "$pid" &
    MONITOR_PID=$!

    if wait "$pid"; then
        rc=0
    else
        rc=$?
    fi
    ACTIVE_PID=""
    ACTIVE_PGID=""
    stop_monitor
    ended="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    record_stage "$stage" "$started" "$ended" "$pid" "$rc" "$log" "$command"
    return "$rc"
}

phase0_impl() {
    export DRY_RUN=0
    # Do not source config.sh here: it assigns OH_ROOT/OH_PRODUCT_NAME and
    # would collide with this wrapper's immutable full-product identity.
    # Phase0 is a sourceable library whose only caller-provided interface is
    # these logging/command helpers.
    log_info() { printf '[INFO] %s\n' "$*"; }
    log_ok() { printf '[OK] %s\n' "$*"; }
    log_warn() { printf '[WARN] %s\n' "$*" >&2; }
    run() { "$@"; }
    # shellcheck source=/dev/null
    source "$PHASE0" || return 1
    apply_ohos_patches
}

run_in_oh_root() {
    cd "$OH_ROOT" || return 1
    "$@"
}

validator_impl() {
    env OH_ROOT="$OH_ROOT" OH_PRODUCT_NAME="$OH_PRODUCT_NAME" "$VALIDATOR"
}

extract_cxx_command() {
    local toolchain_file="$1"
    awk '
        $1 == "rule" && ($2 == "cxx" || $2 ~ /^cxx__/) { in_cxx = 1; next }
        in_cxx && $1 == "command" && $2 == "=" {
            sub(/^[[:space:]]*command[[:space:]]*=[[:space:]]*/, "")
            print
            found = 1
            exit
        }
        in_cxx && $1 == "rule" { exit }
        END { exit(found ? 0 : 1) }
    ' "$toolchain_file"
}

ccache_toolchain_gate() {
    local label="$1" toolchain_file="$2" cxx_command
    [ -f "$toolchain_file" ] && [ ! -L "$toolchain_file" ] || {
        printf 'ERROR missing %s toolchain graph: %s\n' "$label" "$toolchain_file" >&2
        return 1
    }
    cxx_command="$(extract_cxx_command "$toolchain_file")" || {
        printf 'ERROR %s toolchain has no CXX command: %s\n' "$label" "$toolchain_file" >&2
        return 1
    }
    case "$cxx_command" in
        *"$PINNED_CCACHE"*) ;;
        *)
            printf 'ERROR %s CXX command lost pinned ccache: %s\n' "$label" "$cxx_command" >&2
            return 1
            ;;
    esac
    printf 'CCACHE_CXX_PASS toolchain=%s file=%s ccache=%s\n' \
        "$label" "$toolchain_file" "$PINNED_CCACHE"
}

ccache_graph_gate_impl() {
    local args_gn="$OUT_DIR/args.gn"
    local target_toolchain="$OUT_DIR/toolchain.ninja"
    local clang_x64_toolchain="$OUT_DIR/clang_x64/toolchain.ninja"

    [ "${USE_CCACHE:-}" = "1" ] \
        && [ "${CCACHE_EXEC:-}" = "$PINNED_CCACHE" ] \
        && [ "${CCACHE_DIR:-}" = "$PINNED_CCACHE_DIR" ] \
        && [ "${CCACHE_BASEDIR:-}" = "$PINNED_CCACHE_BASEDIR" ] \
        && [ "${CCACHE_UMASK:-}" = "$PINNED_CCACHE_UMASK" ] \
        && [ "${CCACHE_MAXSIZE:-}" = "$PINNED_CCACHE_MAXSIZE" ] || {
            printf 'ERROR ccache lifecycle environment drifted before graph gate\n' >&2
            return 1
        }
    [ -f "$args_gn" ] && [ ! -L "$args_gn" ] || {
        printf 'ERROR missing GN args: %s\n' "$args_gn" >&2
        return 1
    }
    grep -Eq '^[[:space:]]*cc_wrapper[[:space:]]*=[[:space:]]*"/usr/bin/ccache"[[:space:]]*$' "$args_gn" || {
        printf 'ERROR args.gn lost cc_wrapper="/usr/bin/ccache": %s\n' "$args_gn" >&2
        return 1
    }
    ccache_toolchain_gate target "$target_toolchain" || return 1
    ccache_toolchain_gate clang_x64 "$clang_x64_toolchain" || return 1
    printf 'CCACHE_GRAPH_PASS args=%s target=%s clang_x64=%s\n' \
        "$args_gn" "$target_toolchain" "$clang_x64_toolchain"
}

artifact_gate_impl() {
    local image_dir="$OUT_DIR/packages/phone/images" name
    : > "$RUN_DIR/artifacts.sha256" || return 1
    for name in "${IMAGE_ARTIFACTS[@]}"; do
        [ -f "$image_dir/$name" ] && [ ! -L "$image_dir/$name" ] || {
            printf 'ERROR missing image artifact: %s\n' "$image_dir/$name" >&2
            return 1
        }
        sha256sum "$image_dir/$name" >> "$RUN_DIR/artifacts.sha256" || return 1
    done
}

first_marker() {
    local log="$1"
    [ -f "$log" ] || return 0
    grep -m1 -E '\[NINJA\].*Excuting ninja command|^\[[0-9]+/[0-9]+\]' "$log" 2>/dev/null || true
}

first_failure() {
    local log="$1" failure
    [ -f "$log" ] || return 0
    failure="$(grep -n -m1 -E '^FAILED:|fatal error:|ninja: build stopped|\[OHOS ERROR\]|^ERROR([: ]|$)' "$log" 2>/dev/null || true)"
    if [ -n "$failure" ]; then
        printf '%s\n' "$failure"
    else
        awk 'NF { print NR ":" $0; exit }' "$log" 2>/dev/null || true
    fi
}

finalize() {
    local state="$1" rc="$2" marker marker_log failure receipt_sha current_tmp finished_utc
    local wrapper_sha phase0_sha validator_sha build_ninja_sha stages_sha pids_sha artifacts_sha summary_sha
    [ "$FINALIZED" = "0" ] || return 0
    [ "$FINALIZING" = "0" ] || return 1
    FINALIZING=1

    marker_log="$LAST_LOG"
    if [ "$state" = "PASS" ]; then
        marker_log="$RUN_DIR/full.log"
        if [ ! -f "$marker_log" ] || [ ! -s "$RUN_DIR/artifacts.sha256" ]; then
            FINALIZING=0
            printf 'ERROR refusing PASS without full.log and artifacts.sha256\n' >&2
            return 1
        fi
    fi
    marker="$(first_marker "$marker_log")"
    failure=""
    if [ "$state" != "PASS" ]; then
        failure="$(first_failure "$LAST_LOG")"
    fi

    wrapper_sha="$(sha256_file "${BASH_SOURCE[0]}")" || { FINALIZING=0; return 1; }
    phase0_sha="$(sha256_file "$PHASE0")" || { FINALIZING=0; return 1; }
    validator_sha="$(sha256_file "$VALIDATOR")" || { FINALIZING=0; return 1; }
    build_ninja_sha="$([ -f "$OUT_DIR/build.ninja" ] && sha256_file "$OUT_DIR/build.ninja" || printf MISSING)"
    [ -f "$RUN_DIR/stages.tsv" ] && [ ! -L "$RUN_DIR/stages.tsv" ] \
        || { FINALIZING=0; printf 'ERROR missing stages.tsv during finalize\n' >&2; return 1; }
    [ -f "$RUN_DIR/pids.tsv" ] && [ ! -L "$RUN_DIR/pids.tsv" ] \
        || { FINALIZING=0; printf 'ERROR missing pids.tsv during finalize\n' >&2; return 1; }
    stages_sha="$(sha256_file "$RUN_DIR/stages.tsv")" || { FINALIZING=0; return 1; }
    pids_sha="$(sha256_file "$RUN_DIR/pids.tsv")" || { FINALIZING=0; return 1; }
    if [ -f "$RUN_DIR/artifacts.sha256" ] && [ ! -L "$RUN_DIR/artifacts.sha256" ]; then
        artifacts_sha="$(sha256_file "$RUN_DIR/artifacts.sha256")" || { FINALIZING=0; return 1; }
    else
        artifacts_sha="MISSING"
    fi
    finished_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    # Finish all human- and machine-readable support files before publishing
    # the receipt.  CURRENT is the final atomic commit point below.
    if [ "$state" = "PASS" ]; then
        write_summary "完成" "none" "校验 CURRENT/receipt 后交给镜像与设备准入。" \
            || { FINALIZING=0; return 1; }
    else
        write_summary "已停止并封存" "stage=$LAST_STAGE rc=$rc first_failure=${failure:-unavailable}" \
            "只处理该首个事实墙，不自动重启全编译。" \
            || { FINALIZING=0; return 1; }
    fi
    summary_sha="$(sha256_file "$RUN_DIR/SUMMARY.txt")" || { FINALIZING=0; return 1; }

    {
        printf 'schema=m04-r45-wukong100-base-images-v2\n'
        printf 'scope=BASE_ONLY_NOT_ADAPTER_PRODUCT\n'
        printf 'generation=%s\n' "$GENERATION"
        printf 'product=%s\n' "$OH_PRODUCT_NAME"
        printf 'state=%s\n' "$state"
        printf 'wrapper_rc=%s\n' "$rc"
        printf 'terminal_stage=%s\n' "$LAST_STAGE"
        printf 'host=%s\n' "$(hostname)"
        printf 'wrapper_pid=%s\n' "$$"
        printf 'adapter_root=%s\n' "$ADAPTER_ROOT"
        printf 'oh_root=%s\n' "$OH_ROOT"
        printf 'run_dir=%s\n' "$RUN_DIR"
        printf 'wrapper_sha256=%s\n' "$wrapper_sha"
        printf 'phase0_sha256=%s\n' "$phase0_sha"
        printf 'validator_sha256=%s\n' "$validator_sha"
        printf 'build_ninja_sha256=%s\n' "$build_ninja_sha"
        printf 'stages_path=%s\n' "$RUN_DIR/stages.tsv"
        printf 'stages_sha256=%s\n' "$stages_sha"
        printf 'pids_path=%s\n' "$RUN_DIR/pids.tsv"
        printf 'pids_sha256=%s\n' "$pids_sha"
        printf 'artifacts_manifest_path=%s\n' "$RUN_DIR/artifacts.sha256"
        printf 'artifacts_manifest_sha256=%s\n' "$artifacts_sha"
        printf 'summary_sha256=%s\n' "$summary_sha"
        printf 'first_marker_log=%s\n' "$marker_log"
        printf 'first_marker=%s\n' "$marker"
        printf 'first_failure=%s\n' "$failure"
        printf 'finished_utc=%s\n' "$finished_utc"
    } | atomic_write "$RUN_DIR/RECEIPT.txt" || { FINALIZING=0; return 1; }

    receipt_sha="$(sha256_file "$RUN_DIR/RECEIPT.txt")" || { FINALIZING=0; return 1; }
    printf '%s  %s\n' "$receipt_sha" "$RUN_DIR/RECEIPT.txt" \
        | atomic_write "$RUN_DIR/RECEIPT.sha256" || { FINALIZING=0; return 1; }

    # Prepare CURRENT completely, then remove ACTIVE and atomically rename
    # CURRENT last.  Readers can therefore never observe a terminal CURRENT
    # whose receipt, hashes, summary, or ACTIVE transition is unfinished.
    current_tmp="$RUN_ROOT/.CURRENT.tmp.$$"
    {
        printf 'state=%s\n' "$state"
        printf 'run_dir=%s\n' "$RUN_DIR"
        printf 'receipt=%s\n' "$RUN_DIR/RECEIPT.txt"
        printf 'receipt_sha256=%s\n' "$receipt_sha"
        printf 'wrapper_rc=%s\n' "$rc"
    } > "$current_tmp" || { rm -f "$current_tmp"; FINALIZING=0; return 1; }
    rm -f "$RUN_ROOT/ACTIVE" || { rm -f "$current_tmp"; FINALIZING=0; return 1; }
    mv -f "$current_tmp" "$RUN_ROOT/CURRENT" \
        || { rm -f "$current_tmp"; FINALIZING=0; return 1; }

    FINALIZED=1
    FINALIZING=0
}

on_signal() {
    local signal="$1" rc=130
    # Do not interrupt the short terminal publication transaction.  Bash
    # delivers traps between commands, so returning here lets finalize()
    # finish removing ACTIVE and atomically publishing CURRENT before any
    # later signal is handled normally.
    if [ "$FINALIZING" = "1" ]; then
        return 0
    fi
    [ "$signal" = "TERM" ] && rc=143
    trap - INT TERM
    terminate_active_stage
    exit "$rc"
}

on_exit() {
    local rc=$?
    trap - EXIT INT TERM
    terminate_active_stage
    if [ "$FINALIZED" = "0" ] && [ "$FINALIZING" = "0" ] && [ -n "$RUN_DIR" ]; then
        finalize "FAILED" "$rc" || true
    fi
    exit "$rc"
}

trap 'on_signal INT' INT
trap 'on_signal TERM' TERM
trap on_exit EXIT

preflight || exit 65

if [ -e "$LOCK_ROOT" ] && { [ -L "$LOCK_ROOT" ] || [ ! -d "$LOCK_ROOT" ]; }; then
    printf 'ERROR unsafe lock root: %s\n' "$LOCK_ROOT" >&2
    exit 66
fi
mkdir -p "$LOCK_ROOT"
chmod 700 "$LOCK_ROOT"
if [ -e "$LOCK_FILE" ] && { [ -L "$LOCK_FILE" ] || [ ! -f "$LOCK_FILE" ]; }; then
    printf 'ERROR unsafe lock file: %s\n' "$LOCK_FILE" >&2
    exit 66
fi
exec 9>>"$LOCK_FILE"
chmod 600 "$LOCK_FILE"
if ! flock -n 9; then
    printf 'ERROR another R45 wukong100 wrapper owns the build lock: %s\n' "$LOCK_FILE" >&2
    exit 73
fi

active_report="$(reject_active_build_chain 2>&1)" || {
    printf '%s\n' "$active_report" >&2
    exit 74
}

mkdir -p "$RUN_ROOT"
chmod 700 "$RUN_ROOT"
RUN_DIR="$RUN_ROOT/$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir "$RUN_DIR"
printf 'stage\tstarted_utc\tended_utc\tpid\trc\tlog\tlog_sha256\tcommand\n' > "$RUN_DIR/stages.tsv"
printf 'observed_utc\tstage\tpid\texe\tcwd\tcommand\n' > "$RUN_DIR/pids.tsv"
{
    printf 'generation=%s\n' "$GENERATION"
    printf 'product=%s\n' "$OH_PRODUCT_NAME"
    printf 'run_dir=%s\n' "$RUN_DIR"
    printf 'wrapper_pid=%s\n' "$$"
    printf 'started_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} | atomic_write "$RUN_ROOT/ACTIVE"
write_summary "Phase0 待执行" "none" "Phase0 后生成同一锁内 GN 图。"

phase0_cmd="source $(printf '%q' "$PHASE0") && apply_ohos_patches"
if run_stage phase0 "$RUN_DIR/phase0.log" "$phase0_cmd" phase0_impl; then
    :
else
    rc=$?; finalize FAILED "$rc"; exit "$rc"
fi

gn_cmd=("$OH_ROOT/build.sh" "${HISTORICAL_BUILD_ARGS[@]}" --build-only-gn)
gn_display="$(shell_join "${gn_cmd[@]}")"
if run_stage gn_only "$RUN_DIR/gn.log" "$gn_display" run_in_oh_root "${gn_cmd[@]}"; then
    :
else
    rc=$?; finalize FAILED "$rc"; exit "$rc"
fi

ccache_gate_display="$(shell_join ccache_graph_gate "$OUT_DIR/args.gn" "$OUT_DIR/toolchain.ninja" "$OUT_DIR/clang_x64/toolchain.ninja")"
if run_stage ccache_graph_post_gn "$RUN_DIR/ccache-graph-post-gn.log" "$ccache_gate_display" ccache_graph_gate_impl; then
    :
else
    rc=$?; finalize FAILED "$rc"; exit "$rc"
fi

validator_display="OH_ROOT=$(printf '%q' "$OH_ROOT") OH_PRODUCT_NAME=wukong100 $(printf '%q' "$VALIDATOR")"
if run_stage validator_pre_target "$RUN_DIR/validator-pre-target.log" "$validator_display" validator_impl; then
    :
else
    rc=$?; finalize FAILED "$rc"; exit "$rc"
fi

target_cmd=("$NINJA" -j2 -w dupbuild=warn -C "$OUT_DIR" "${FIVE_TARGETS[@]}")
target_display="$(shell_join "${target_cmd[@]}")"
if run_stage five_targets "$RUN_DIR/five-targets.log" "$target_display" run_in_oh_root "${target_cmd[@]}"; then
    :
else
    rc=$?; finalize FAILED "$rc"; exit "$rc"
fi

if run_stage ccache_graph_post_targets "$RUN_DIR/ccache-graph-post-targets.log" "$ccache_gate_display" ccache_graph_gate_impl; then
    :
else
    rc=$?; finalize FAILED "$rc"; exit "$rc"
fi

if run_stage validator_pre_full "$RUN_DIR/validator-pre-full.log" "$validator_display" validator_impl; then
    :
else
    rc=$?; finalize FAILED "$rc"; exit "$rc"
fi

if run_stage ccache_graph_pre_full "$RUN_DIR/ccache-graph-pre-full.log" "$ccache_gate_display" ccache_graph_gate_impl; then
    :
else
    rc=$?; finalize FAILED "$rc"; exit "$rc"
fi

full_cmd=("$OH_ROOT/build.sh" "${HISTORICAL_BUILD_ARGS[@]}" --ninja-args=-j2 --fast-rebuild --build-target images)
full_display="$(shell_join "${full_cmd[@]}")"
if run_stage full_images "$RUN_DIR/full.log" "$full_display" run_in_oh_root "${full_cmd[@]}"; then
    :
else
    rc=$?; finalize FAILED "$rc"; exit "$rc"
fi

ninja_marker="$(grep -m1 -E '\[NINJA\].*Excuting ninja command:' "$RUN_DIR/full.log" 2>/dev/null || true)"
if ! printf '%s\n' "$ninja_marker" | grep -Fq ' images ' \
    || ! printf '%s\n' "$ninja_marker" | grep -Fq -- '-j2'; then
    printf 'ERROR full build returned zero without the pinned -j2 images Ninja marker\n' >> "$RUN_DIR/full.log"
    finalize FAILED 75
    exit 75
fi

declare -a artifact_paths=()
image_name=""
for image_name in "${IMAGE_ARTIFACTS[@]}"; do
    artifact_paths+=("$OUT_DIR/packages/phone/images/$image_name")
done
artifact_display="$(shell_join sha256sum "${artifact_paths[@]}")"
if run_stage artifacts "$RUN_DIR/artifacts.log" "$artifact_display" artifact_gate_impl; then
    :
else
    rc=$?; finalize FAILED "$rc"; exit "$rc"
fi

finalize PASS 0
printf 'BASE_IMAGE_PASS scope=BASE_ONLY current=%s\n' "$RUN_ROOT/CURRENT"
exit 0
