#!/usr/bin/env bash
# oatdump_remote.sh — 在 Mac 上被当作 oatdump 调用,实际把镜像与 BCP jar 同步到 hw248,
# 用 r1+22 树的 host oatdump 执行,原样回传 stdout/stderr/退出码。
#
# 用法(与 oatdump 兼容):
#   oatdump_remote.sh --oat-file=<path> [--class-filter=X] [--method-filter=Y] [--dump:code] [--no-disassemble] ...
#   oatdump_remote.sh --image=<dir>/arm64/boot.art [--instruction-set=arm64] [--header-only] ...
#
# 环境变量(全部必须显式设置,不设则报错):
#   LAB_HOME    hw248 上的工作目录前缀(必填,无默认)
#   HW248       hw248 的 ssh 目标             默认 hw248
#   OATDUMP     hw248 上 oatdump 二进制路径   默认 $LAB_HOME/aosp-14.0.0_r1-art/out/host/linux-x86/bin/oatdump
#   OATDUMP_LIB hw248 上 host lib64 路径      默认 $LAB_HOME/aosp-14.0.0_r1-art/out/host/linux-x86/lib64
#
# 缓存:按内容 sha256 前 16 位在 hw248 的 $LAB_HOME/.oatdump-cache/ 下建目录,
# 同内容不重复 scp。
#
# 退出码:oatdump 的退出码原样回传;同步/连接失败返回 2。
set -euo pipefail

LAB_HOME="${LAB_HOME:?set LAB_HOME to the lab dir on hw248 (env.md)}"
HW248="${HW248:-hw248}"
OATDUMP="${OATDUMP:-$LAB_HOME/aosp-14.0.0_r1-art/out/host/linux-x86/bin/oatdump}"
OATDUMP_LIB="${OATDUMP_LIB:-$LAB_HOME/aosp-14.0.0_r1-art/out/host/linux-x86/lib64}"

# ── 解析参数,提取 --oat-file 或 --image 路径 ──
OAT_FILE=""
IMAGE_FILE=""
ARGS=()
set +u  # ARGS[@] 可能为空,set -u 下展开会炸
for arg in "$@"; do
  case "$arg" in
    --oat-file=*)
      OAT_FILE="${arg#--oat-file=}"
      ;;
    --image=*)
      IMAGE_FILE="${arg#--image=}"
      ;;
    *)
      ARGS+=("$arg")
      ;;
  esac
done
set -u

[ -n "$OAT_FILE" ] || [ -n "$IMAGE_FILE" ] || { echo "ERROR: --oat-file=<path> or --image=<path> required" >&2; exit 2; }

# ── 按内容哈希缓存同步到 hw248 ──
sha16() { shasum -a 256 "$1" | cut -c1-16; }

sync_file() {
  # sync_file <local_path> <cache_dir>
  local f="$1" dir="$2"
  local base=$(basename "$f")
  if ! ssh "$HW248" "test -f $dir/$base" 2>/dev/null; then
    ssh "$HW248" "mkdir -p $dir"
    scp -q "$f" "$HW248:$dir/$base"
  fi
}

if [ -n "$OAT_FILE" ]; then
  [ -f "$OAT_FILE" ] || { echo "ERROR: oat file not found: $OAT_FILE" >&2; exit 2; }
  OAT_SHA=$(sha16 "$OAT_FILE")
  OAT_BASE=$(basename "$OAT_FILE")
  CACHE_DIR="$LAB_HOME/.oatdump-cache/$OAT_SHA"
  sync_file "$OAT_FILE" "$CACHE_DIR"
  # 同步同名 .vdex(若存在,oatdump 需要)
  VDEX_FILE="${OAT_FILE%.oat}.vdex"
  if [ -f "$VDEX_FILE" ]; then
    sync_file "$VDEX_FILE" "$CACHE_DIR"
  fi
  REMOTE_OAT="$CACHE_DIR/$OAT_BASE"
  REMOTE_CMD="export LD_LIBRARY_PATH='$OATDUMP_LIB' && '$OATDUMP' --oat-file='$REMOTE_OAT'"
elif [ -n "$IMAGE_FILE" ]; then
  [ -f "$IMAGE_FILE" ] || { echo "ERROR: image file not found: $IMAGE_FILE" >&2; exit 2; }
  IMG_SHA=$(sha16 "$IMAGE_FILE")
  IMG_BASE=$(basename "$IMAGE_FILE")
  # oatdump --image 需要 <dir>/arm64/boot.art 目录结构(自动加 arch)
  CACHE_DIR="$LAB_HOME/.oatdump-cache/$IMG_SHA"
  IMG_DIR=$(dirname "$IMAGE_FILE")
  # 同步整个 arm64/ 目录(boot.art + boot-*.{art,oat,vdex})
  for f in "$IMG_DIR"/boot*.art "$IMG_DIR"/boot*.oat "$IMG_DIR"/boot*.vdex; do
    [ -f "$f" ] || continue
    base=$(basename "$f")
    if ! ssh "$HW248" "test -f $CACHE_DIR/arm64/$base" 2>/dev/null; then
      ssh "$HW248" "mkdir -p $CACHE_DIR/arm64"
      scp -q "$f" "$HW248:$CACHE_DIR/arm64/$base"
    fi
  done
  # 同步 BCP jar 目录(若 --boot-image 或 --boot-class-path 在 ARGS 里)
  set +u
  for arg in "${ARGS[@]}"; do
    case "$arg" in
      --boot-image=*|--boot-class-path=*)
        BCP_PATH="${arg#*=}"
        IFS=':' read -ra BCP_JARS <<< "$BCP_PATH"
        for jar in "${BCP_JARS[@]}"; do
          jar=$(echo "$jar" | sed 's|^.*=||')
          [ -f "$jar" ] && sync_file "$jar" "$CACHE_DIR"
        done
        ;;
    esac
  done
  set -u
  REMOTE_IMG="$CACHE_DIR/$IMG_BASE"
  REMOTE_CMD="export LD_LIBRARY_PATH='$OATDUMP_LIB' && '$OATDUMP' --image='$REMOTE_IMG'"
fi

# ── 透传其余参数;对 --runtime-arg 的 -Xbootclasspath 值做本地→远端路径翻译 ──
# G2 调用形态:--runtime-arg -Xbootclasspath:<dir>/core-oj.jar:... --runtime-arg -Xbootclasspath-locations:...
# jar 按内容哈希缓存;参数里的本地路径逐jar替换为远端缓存路径。
translate_arg() {
  local arg="$1"
  case "$arg" in
    -Xbootclasspath:*)
      local prefix="-Xbootclasspath:" rest="${arg#-Xbootclasspath:}"
      local out="" IFS_SAVE="$IFS"
      IFS=':'
      for jar in $rest; do
        if [ -f "$jar" ]; then
          local jsha=$(sha16 "$jar")
          local jdir="$LAB_HOME/.oatdump-cache/$jsha"
          sync_file "$jar" "$jdir"
          out="$out${out:+:}$jdir/$(basename "$jar")"
        else
          out="$out${out:+:}$jar"
        fi
      done
      IFS="$IFS_SAVE"
      printf '%s%s' "$prefix" "$out"
      ;;
    *)
      printf '%s' "$arg"
      ;;
  esac
}

set +u
i=0
while [ $i -lt ${#ARGS[@]} ]; do
  arg="${ARGS[$i]}"
  if [ "$arg" = "--runtime-arg" ] && [ $((i+1)) -lt ${#ARGS[@]} ]; then
    next=$(translate_arg "${ARGS[$((i+1))]}")
    REMOTE_CMD="$REMOTE_CMD '--runtime-arg' '$next'"
    i=$((i+2))
  else
    REMOTE_CMD="$REMOTE_CMD '$arg'"
    i=$((i+1))
  fi
done
set -u

ssh "$HW248" "$REMOTE_CMD"
exit $?
