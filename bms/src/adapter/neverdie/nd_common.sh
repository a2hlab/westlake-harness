#!/usr/bin/env bash
# ============================================================================
# nd_common.sh — adapter「永不死机」共用底座 (路径 / 日志 / 范围 / helper)
# ============================================================================
#
# 来源：移植自 16.16-NeverDie (D200 daemon 永不死机)。该框架原本守护一个长驻
# daemon binary (R1 watchdog + R3/R13 golden A/B + R2 fail-counter + R17 disk
# caps + R14 metrics)。本工程 /data/adapter 不是 daemon，而是「源码+构建工作区」，
# 所以这里把同一套思想从「守护进程」适配成「守护恢复弹药」。
#
# 为什么需要它（补位，不重复 restore_after_sync.sh）：
#   restore_after_sync.sh 负责把改动「恢复进」~/aosp/、~/oh/ 源码树，
#   它的输入是 adapter 自己的权威资产：framework/ aosp_patches/ ohos_patches/
#   build/ restore_after_sync.sh CLAUDE.md ……
#   但这些「弹药」本身没有任何保护——一次坏 edit / 坏 patch / 坏 repo sync /
#   误删，就让一键恢复自己「死机」。本子系统给这批权威输入做 golden 快照 +
#   完整性校验 + 一键回滚，让恢复源「永不死机」。
#
# 三性 (遵守 adapter CLAUDE.md「一键恢复规则」)：
#   * 自包含 — 只依赖干净源码树 + 本目录脚本，不依赖任何残留本地状态
#   * 幂等   — 所有脚本可重复执行，不破坏已恢复状态
#   * 可追溯 — 每步落 $ND_LOG，失败 set -e 立即退出，不静默吞错
#
# 本文件被其它 nd_*.sh source，不单独执行。
# ----------------------------------------------------------------------------

# --- 路径自检测 (与 restore_after_sync.sh 同款) ----------------------------
ND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 默认 = neverdie/ 的父目录 (即 adapter 根)。可用 ND_ADAPTER_ROOT 覆盖
# (演练 / 对副本操作时有用)。
ADAPTER_ROOT="${ND_ADAPTER_ROOT:-$(cd "$ND_DIR/.." && pwd)}"

# Golden 仓库刻意放在 adapter/ 之外的兄弟目录：
#   1) 能扛住「整个 adapter/ 被 rm / 被坏 repo sync 覆盖」
#   2) 不污染 adapter 的 Local↔ECS 同步 (golden 体积不进同步链)
# 可用环境变量 ND_GOLDEN_ROOT 覆盖。GZ05 上建议 ND_GOLDEN_ROOT=/data/.adapter-neverdie
ND_GOLDEN_ROOT="${ND_GOLDEN_ROOT:-$(cd "$ADAPTER_ROOT/.." && pwd)/.adapter-neverdie}"

ND_LOG="$ND_GOLDEN_ROOT/nd.log"
ND_ACTIVE="$ND_GOLDEN_ROOT/active"          # 内含 "A" 或 "B"，记录当前生效 slot
ND_FAILCNT="$ND_GOLDEN_ROOT/fail.cnt"       # 连续校验失败计数 (R2 analog)
ND_METRICS="$ND_GOLDEN_ROOT/metrics"        # 简单 KV 指标 (R14 analog)
ND_CORRUPT_DIR="$ND_GOLDEN_ROOT/corrupt"    # 回滚时隔离的坏副本 (R3 .corrupt analog)

# --- 保护范围：权威输入「白名单」(相对 ADAPTER_ROOT) -------------------------
# 用白名单而非黑名单：只快照已知的权威资产，天然排除 out/ 大包 / 正在复制的
# OH 产物 / 工具链快捷方式，绝不误纳编译产物。
# 依据 CLAUDE.md Sync Map「authoritative source」+「一键恢复规则」的恢复弹药清单。
ND_PROTECT="
CLAUDE.md
readme.txt
build.sh
bundle.json
restore_after_sync.sh
appspawn_x_design.html
framework
aosp_patches
ohos_patches
app
appspawn
config
deploy
doc
build
"

# tar / manifest 内部仍要排除的「嵌套产物 / 体积 / 噪声」(白名单目录里夹带的):
#   build/out, build/inner 可能含编译中间物；*.log 噪声；VCS / 缓存
ND_EXCLUDES="
--exclude=build/out
--exclude=build/inner/out
--exclude=*.log
--exclude=__pycache__
--exclude=.git
--exclude=.DS_Store
--exclude=*.tar.gz
"

# --- 配额 (R17 analog) ------------------------------------------------------
ND_MAX_CORRUPT_COPIES="${ND_MAX_CORRUPT_COPIES:-5}"     # 最多留 5 份坏副本
ND_MAX_GOLDEN_ROOT_MB="${ND_MAX_GOLDEN_ROOT_MB:-2048}"  # golden 仓库总上限 2GB

# --- 失败阈值 (R2 analog) ---------------------------------------------------
ND_FAIL_THRESHOLD="${ND_FAIL_THRESHOLD:-3}"             # 连续 3 次校验失败 → 自动回滚

# --- 颜色日志 (与 restore_after_sync.sh 同款，落 stdout + 落 $ND_LOG) ---------
if [ -t 1 ]; then
    C_RED=$'\033[31m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'
    C_BLUE=$'\033[34m'; C_BOLD=$'\033[1m'; C_RESET=$'\033[0m'
else
    C_RED=""; C_GREEN=""; C_YELLOW=""; C_BLUE=""; C_BOLD=""; C_RESET=""
fi

# 同时打屏 + 落文件 (可追溯)。文件行不带颜色。
_nd_file_log() {
    [ -d "$ND_GOLDEN_ROOT" ] || mkdir -p "$ND_GOLDEN_ROOT" 2>/dev/null || return 0
    printf '%s [%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" "$2" >> "$ND_LOG"
}
log_info()  { printf '%s[INFO]%s  %s\n' "$C_BLUE"   "$C_RESET" "$*"; _nd_file_log INFO "$*"; }
log_ok()    { printf '%s[OK]%s    %s\n' "$C_GREEN"  "$C_RESET" "$*"; _nd_file_log OK   "$*"; }
log_warn()  { printf '%s[WARN]%s  %s\n' "$C_YELLOW" "$C_RESET" "$*" >&2; _nd_file_log WARN "$*"; }
log_error() { printf '%s[ERR]%s   %s\n' "$C_RED"    "$C_RESET" "$*" >&2; _nd_file_log ERR  "$*"; }
log_phase() { printf '\n%s========== %s ==========%s\n' "$C_BOLD" "$*" "$C_RESET"; _nd_file_log PHASE "$*"; }

# --- 跨平台 sha256 (本机 macOS=shasum / GZ05 Linux=sha256sum) -----------------
if command -v sha256sum >/dev/null 2>&1; then
    nd_sha256() { sha256sum "$1" 2>/dev/null | cut -d' ' -f1; }
elif command -v shasum >/dev/null 2>&1; then
    nd_sha256() { shasum -a 256 "$1" 2>/dev/null | cut -d' ' -f1; }
else
    nd_sha256() { echo "NO-SHA256-TOOL"; }
fi

# --- 幂等初始化 golden 仓库 -------------------------------------------------
nd_init_root() {
    if [ ! -d "$ND_GOLDEN_ROOT" ]; then
        mkdir -p "$ND_GOLDEN_ROOT"
        _nd_file_log INIT "created golden root $ND_GOLDEN_ROOT"
    fi
    mkdir -p "$ND_CORRUPT_DIR"
}

# 读当前生效 slot；无则空。注意：必须恒返回 0，否则在调用方 `set -e` +
# 命令替换 (SLOT="$(nd_active_slot)") 下，文件不存在会直接中止脚本。
nd_active_slot() { [ -f "$ND_ACTIVE" ] && cat "$ND_ACTIVE" 2>/dev/null || true; }

# 写生效 slot (原子：写 tmp 再 mv)
nd_set_active_slot() {
    printf '%s\n' "$1" > "$ND_ACTIVE.tmp" && mv "$ND_ACTIVE.tmp" "$ND_ACTIVE"
}

# 取与 slot 对应的 inactive slot 字母
nd_inactive_slot() {
    case "$(nd_active_slot)" in
        A) echo "B" ;;
        *) echo "A" ;;   # 空 / B / 异常 → 都写 A 端
    esac
}

# slot 对应的归档 / manifest 路径
nd_tarball() { echo "$ND_GOLDEN_ROOT/golden.$1.tar.gz"; }
nd_manifest() { echo "$ND_GOLDEN_ROOT/golden.$1.manifest"; }

# 写一条 metric (KV，覆盖式)
nd_metric_set() {
    nd_init_root
    local key="$1" val="$2" tmp="$ND_METRICS.tmp"
    # 关键：metrics 文件不存在时 grep 返回 exit 2 (file error)，在调用方 set -e 下
    # 会以 rc=2 中止整个脚本。必须先 touch + 给 grep 兜 || true。
    [ -f "$ND_METRICS" ] || : > "$ND_METRICS"
    { grep -v "^$key=" "$ND_METRICS" 2>/dev/null || true; echo "$key=$val"; } > "$tmp"
    mv "$tmp" "$ND_METRICS"
}
# 恒返回 0 (pipefail + set -e 下，grep 未命中会中止调用方的命令替换)
nd_metric_get() { { grep "^$1=" "$ND_METRICS" 2>/dev/null || true; } | head -1 | cut -d= -f2-; }

# 配额清理 (R17 analog)：限坏副本数 + 限 golden 仓库总大小
nd_disk_cleanup() {
    # 1) 坏副本超额删最旧
    if [ -d "$ND_CORRUPT_DIR" ]; then
        local i=0 f
        for f in $(ls -1dt "$ND_CORRUPT_DIR"/* 2>/dev/null); do
            i=$((i + 1))
            [ "$i" -gt "$ND_MAX_CORRUPT_COPIES" ] && rm -rf "$f" 2>/dev/null
        done
    fi
    # 2) golden 仓库总大小超 cap → 告警 (不自动删 golden，只删坏副本)
    local total_kb cap_kb
    total_kb=$(du -sk "$ND_GOLDEN_ROOT" 2>/dev/null | cut -f1)
    case "$total_kb" in ''|*[!0-9]*) total_kb=0 ;; esac
    cap_kb=$((ND_MAX_GOLDEN_ROOT_MB * 1024))
    if [ "$total_kb" -gt "$cap_kb" ]; then
        log_warn "golden root $total_kb KB 超 cap ${cap_kb} KB — 清空坏副本目录"
        rm -rf "$ND_CORRUPT_DIR"/* 2>/dev/null || true
    fi
}
