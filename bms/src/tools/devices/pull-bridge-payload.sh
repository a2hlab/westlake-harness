#!/usr/bin/env bash
# pull-bridge-payload.sh — 把 Bridge 部署载荷从 alexpc 拉到本机，断线自动续。
#
# 为什么要专门写个脚本：alexpc 只能经 FRP（69.194.3.128:60022）到达，该隧道实测
# 仅 3–7 kB/s 且频繁断连（rsync 报 broken pipe / code 255）。整包 400MB 在这条链路上
# 需十几小时，单次 rsync 必然中途死掉。故必须循环重试 + --partial 续传。
#
# 已排除的加速路线（别再重复试）：
#   - Tailscale：本 tailnet 只有本机与一台 iPhone，alexpc/mac-server 均未加入
#   - 内网直连：本机 192.168.31/139 段，mac-server 在 192.168.8 段，不通
#   - 公网中转：alexpc 国内带宽 1.5 MB/s 正常，但
#       0x0.st 已停用上传 · transfer.sh 拒连 · litterbox 超时 · bashupload DNS 不通
#       temp.sh / filebin.net / tempfile.link / sodatool 均为浏览器落地页，脚本取不到直链
#     （filebin 能上传且校验一致，但下载侧被人工审核页挡住）
#
# 用法:
#   ./pull-bridge-payload.sh <目标目录> [子目录…]
#   ./pull-bridge-payload.sh /path/out                      # 默认拉全套
#   ./pull-bridge-payload.sh /path/out aosp_lib64 boot_image # 只拉指定几块
set -euo pipefail

DEST="${1:?usage: pull-bridge-payload.sh <目标目录> [子目录…]}"
shift || true
SUBDIRS=("$@")
[ ${#SUBDIRS[@]} -eq 0 ] && SUBDIRS=(aosp_lib64 boot_image aosp_fwk icu config adapter)

REMOTE=alexpc
SRC=/opt/build-trees/adapter/deploy/d600_5ce1227d_wall5_pkg
SSH_OPTS="-o ConnectTimeout=20 -o ServerAliveInterval=8 -o ServerAliveCountMax=10 -o TCPKeepAlive=yes"
MAX_ROUNDS="${MAX_ROUNDS:-500}"

mkdir -p "${DEST}"
echo "目标: ${DEST}"
echo "子目录: ${SUBDIRS[*]}"
echo "隧道很慢（3–7 kB/s），预计十几小时；断线会自动重连，可随时 Ctrl-C 后重跑续传。"
echo

for ((r=1; r<=MAX_ROUNDS; r++)); do
  # -z 压缩：boot.art/oat 压缩率一般，但 jar/dex 有收益，且隧道瓶颈在带宽不在 CPU
  if rsync -az --partial --partial-dir=".rsync-partial" --append-verify \
       -e "ssh ${SSH_OPTS}" \
       "${REMOTE}:${SRC}/{$(IFS=,; echo "${SUBDIRS[*]}")}" \
       "${DEST}/" 2>/dev/null; then
    echo "✅ 第 ${r} 轮：传输完成"
    break
  fi
  n=$(find "${DEST}" -type f ! -path "*/.rsync-partial/*" 2>/dev/null | wc -l | tr -d ' ')
  echo "  第 ${r} 轮中断（隧道断线属预期），已落地 ${n} 个文件，3 秒后续传…"
  sleep 3
done

echo
echo "落地统计:"
find "${DEST}" -maxdepth 1 -type d ! -path "${DEST}" -exec sh -c \
  'printf "  %-14s %s 个文件\n" "$(basename "$1")" "$(find "$1" -type f | wc -l | tr -d " ")"' _ {} \;
