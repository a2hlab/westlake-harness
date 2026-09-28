#!/usr/bin/env bash
# bridge-postboot.sh — 重启后重建 Bridge 的易失状态。
#
# 为什么需要它：deploy-bridge.sh 里有三件东西**活不过重启**——
#   1. /system/android 的 bind-mount（载荷本体在 /data/bridge-gen，会留下）
#   2. setenforce 0（SELinux 模式不持久）
#   3. `param set ro.*`（ro 前缀参数不写盘；persist.* 前缀的会留下）
# 而 init 只在开机时解析 /system/etc/init/*.cfg，所以装完 appspawn_x.cfg 必须重启一次
# 才能让 init 认识 appspawn-x 服务——于是「必须重启」与「重启丢状态」同时成立。
#
# 用法: ./bridge-postboot.sh <板序列号>
set -euo pipefail
BOARD="${1:?usage: bridge-postboot.sh <板序列号>}"
GEN=/data/bridge-gen

H() { hdc -t "${BOARD}" "$@"; }
D() { H shell "$1" 2>&1 | tr -d '\r'; }

echo "══ 等板子回来"
for i in $(seq 1 60); do
  if D "echo alive" 2>/dev/null | grep -q alive; then echo "  第 ${i} 次探测：起来了"; break; fi
  sleep 3
done
D "echo alive" | grep -q alive || { echo "❌ 板子没回来" >&2; exit 1; }
sleep 5   # 等 init 把开机 job 跑完，否则 mount 会被后续启动流程盖掉

echo "══ 重挂读写 + SELinux permissive"
H target mount >/dev/null 2>&1 || true
D "setenforce 0"

echo "══ 重建 /system/android bind-mount"
D "ls ${GEN}/android >/dev/null 2>&1 && echo ok || echo missing" | grep -q ok \
  || { echo "❌ ${GEN}/android 不在了，需重跑 deploy-bridge.sh" >&2; exit 1; }
D "mkdir -p /system/android"
D "umount /system/android 2>/dev/null || true"
D "mount --bind ${GEN}/android /system/android"
D "ls /system/android" | tr '\n' ' ' | sed 's/^/  /'; echo

echo "══ 补回 ro.* 参数（不持久）"
D "param set ro.product.cpu.abilist arm64-v8a"
D "param set ro.product.cpu.abilist64 arm64-v8a"

echo "══ appspawn-x 状态"
D "begetctl dump_service all 2>&1 | grep -i appspawn-x | head -3; echo '(dump end)'"
PID=$(D "pidof appspawn-x.real" | head -1)
if [ -z "${PID}" ]; then
  echo "  未自动拉起，手动 start_service"
  D "begetctl start_service appspawn-x >/dev/null 2>&1 || true"
  sleep 3
  PID=$(D "pidof appspawn-x.real" | head -1)
fi
echo "  appspawn-x.real pid=${PID:-无}"
D "ls -laZ /dev/unix/socket/AppSpawnX 2>/dev/null || echo '  socket 未见'" | sed 's/^/  /'
echo "  近期 stderr:"
D "tail -6 /data/local/tmp/appspawn-x-stderr.log 2>/dev/null" | sed 's/^/    /'
