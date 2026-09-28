#!/usr/bin/env bash
# bridge-postboot-pr3.sh — 重启后恢复 PR#3 布局的 Bridge 运行态。
#
# 为什么需要它（2026-08-08 实测代价）：
#   deploy_fn01_fn03_r18_runtime_d600.sh 把安卓运行时放在 /data 里再 bind-mount 到
#   /system/android。**bind-mount 活不过重启**，而该脚本没有配套的 postboot——
#   它自己那次重启后的恢复步骤写死在脚本内部（第 912–970 行），无法单独复用。
#
#   于是板子一旦被重启（任何原因），Bridge 就静默失效：/system/android 变空目录，
#   appspawn-x 不再自动起。表现是 `aa start` 返回 success 但白屏，
#   AMS 报 `spawn new app fail, errCode ffffffff`。本轮为此耗掉一轮完整排查。
#
# 恢复顺序照抄 deploy 脚本第 912–970 行，一条也不能省。实测漏掉任何一条的后果：
#   - 漏 `find -type d -exec chmod 0755`：hdc file send 建的目录是 0750 root:root，
#     应用 UID 无法遍历 → provider 入口失败（ENTRY_RESULT 非 0）
#   - 漏 chcon 标签：同上
#   - 漏应用数据目录：孵化阶段 `DoAppSandboxMountOnce section app-base failed`，
#     errCode 0d000008
#   - 漏 ro.product.cpu.abilist：ro.* 参数不写盘，重启即失
#
# 另一个必须知道的坑：**每次孵化失败都会把 AMS 的 mission 卡在 state #INITIAL**，
# 之后所有 `aa start` 被去重成空操作（返回 success 但 AMS 毫无动作）。
# `aa force-stop` 对不存在的进程无效。唯一可靠的清法是重启——所以本脚本设计成
# 「重启 → 恢复」一条龙，让这个循环的代价降到可接受。
#
# 用法:
#   ./bridge-postboot-pr3.sh <板序列号> [--reboot-first]
set -euo pipefail
BOARD="${1:?usage: bridge-postboot-pr3.sh <板序列号> [--reboot-first]}"
REBOOT_FIRST=0
[ "${2:-}" = "--reboot-first" ] && REBOOT_FIRST=1

HDC="${HDC:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}"
SHORT="${BOARD:0:8}"
GEN="/data/a64deploy/fn0103-r18-merged-${SHORT}"
SRC="${GEN}/android"
PKGS="${PKGS:-com.example.helloworld com.a2hlab.bridge.zigzag}"

H() { "${HDC}" -t "${BOARD}" "$@"; }
D() { H shell "$1" 2>&1 | tr -d '\r'; }
die() { echo "❌ $*" >&2; exit 1; }

if [ "${REBOOT_FIRST}" = "1" ]; then
  echo "══ 重启（清掉卡死的 mission）"
  D "sync; reboot" >/dev/null 2>&1 || true
  sleep 10
fi

echo "══ 等板子回来"
for i in $(seq 1 60); do
  sleep 5
  D "echo alive" 2>/dev/null | grep -q alive && { echo "  第 ${i} 次探测：起来了"; break; }
done
D "echo alive" | grep -q alive || die "板子没回来"
# deploy 脚本注释：部分 D600 板需要额外 settle 时间，shell 才可靠
sleep 25

H target mount >/dev/null 2>&1 || true
sleep 5

echo "══ 重建 /system/android bind-mount"
D "test -d ${SRC} && echo ok" | grep -q ok || die "载荷不在: ${SRC}（须重跑 deploy）"
D "mkdir -p /system/android; umount /system/android 2>/dev/null || true; mount --bind ${SRC} /system/android"
D "ls /system/android/lib64/libart.so" | grep -q libart || die "挂载后 libart.so 不可见"

echo "══ 目录权限与 SELinux 标签（漏掉即 provider 入口失败）"
D "find /system/android -type d -exec chmod 0755 {} \; 2>/dev/null; echo ok" >/dev/null
D "if [ -f /system/android/framework/arm64/boot.art ] && [ ! -e /system/android/framework/boot.art ]; then ln -sf arm64/boot.art /system/android/framework/boot.art; fi"
D "find /system/android -exec chcon u:object_r:system_file:s0 {} \; 2>/dev/null; echo ok" >/dev/null
D "find /system/android -type d -exec chcon u:object_r:system_lib_file:s0 {} \; 2>/dev/null; echo ok" >/dev/null
D "find /system/android/lib64 -exec chcon u:object_r:system_lib_file:s0 {} \; 2>/dev/null; echo ok" >/dev/null
D "for f in /system/android/framework/arm64/boot*.art /system/android/framework/arm64/boot*.oat /system/android/framework/arm64/boot*.vdex; do chcon u:object_r:system_lib_file:s0 \$f 2>/dev/null; done; echo ok" >/dev/null
D "chcon u:object_r:system_fonts_file:s0 /system/android/etc/fonts.xml 2>/dev/null || true
   cp /system/android/etc/fonts.xml /system/etc/fonts.xml 2>/dev/null || true
   chcon u:object_r:system_fonts_file:s0 /system/etc/fonts.xml 2>/dev/null || true
   ln -sf /lib/ld-musl-aarch64.so.1 /system/lib/libc_musl.so 2>/dev/null || true
   chcon -h u:object_r:system_lib_file:s0 /system/lib/libc_musl.so 2>/dev/null || true"

echo "══ 参数（ro.* 不持久，必须每次补）"
D "param set persist.sys.abilityms.support_anco_app true
   param set persist.sys.abilityms.timeout_unit_time_ratio 20
   param set persist.sys.prefork.enable false
   param set ro.product.cpu.abilist arm64-v8a
   param set ro.product.cpu.abilist64 arm64-v8a
   chmod 0666 /dev/mali0 2>/dev/null || true
   power-shell wakeup; power-shell timeout -o 86400000" >/dev/null 2>&1 || true

echo "══ 应用沙箱数据目录（deploy 不建，缺则孵化报 0d000008）"
for P in ${PKGS}; do
  U=$(D "bm dump -n ${P}" | grep -oE '"uid": *[0-9]{6,}' | head -1 | grep -oE '[0-9]+$')
  [ -n "${U}" ] || { echo "  跳过 ${P}（未安装）"; continue; }
  D "for d in /data/app/el1/100/base /data/app/el1/100/database /data/app/el2/100/base \
             /data/app/el2/100/database /data/app/el2/100/sharefiles /data/app/el3/100/base \
             /data/app/el3/100/database /data/app/el4/100/base /data/app/el4/100/database; do
       mkdir -p \${d}/${P}; done
     mkdir -p /data/app/el2/100/log/${P}
     for s in cache code_cache databases files haps no_backup preferences shared_prefs temp; do
       mkdir -p /data/app/el2/100/base/${P}/\$s; done
     chown -R ${U}:${U} /data/app/el1/100/base/${P} /data/app/el1/100/database/${P} \
       /data/app/el2/100/base/${P} /data/app/el2/100/database/${P} /data/app/el2/100/sharefiles/${P} \
       /data/app/el3/100/base/${P} /data/app/el3/100/database/${P} \
       /data/app/el4/100/base/${P} /data/app/el4/100/database/${P}
     chown ${U}:log /data/app/el2/100/log/${P}
     chmod 0700 /data/app/el1/100/base/${P} /data/app/el2/100/base/${P} \
       /data/app/el2/100/sharefiles/${P} /data/app/el3/100/base/${P} /data/app/el4/100/base/${P}
     chmod 0770 /data/app/el1/100/database/${P} /data/app/el2/100/database/${P} \
       /data/app/el2/100/log/${P} /data/app/el3/100/database/${P} /data/app/el4/100/database/${P}
     chcon -R u:object_r:appdat:s0 /data/app/el1/100/base/${P} /data/app/el1/100/database/${P} \
       /data/app/el2/100/base/${P} /data/app/el2/100/database/${P} /data/app/el2/100/sharefiles/${P} \
       /data/app/el3/100/base/${P} /data/app/el3/100/database/${P} \
       /data/app/el4/100/base/${P} /data/app/el4/100/database/${P}
     chcon u:object_r:data_app_el2_file:s0 /data/app/el2/100/log/${P}" >/dev/null 2>&1
  echo "  ${P} uid=${U} ok"
done

echo "══ 起 appspawn-x"
D "begetctl stop_service appspawn-x >/dev/null 2>&1 || true"
sleep 2
D "begetctl start_service appspawn-x >/dev/null 2>&1 || true"
sleep 4
SPID=$(D "pidof appspawn-x" | head -1)
echo "  appspawn-x pid=${SPID:-无}"
D "ls -laZ /dev/unix/socket/AppSpawnX 2>/dev/null || echo '  socket 未见'" | sed 's/^/  /'
D "sync"

echo
echo "恢复完成。验基线：aa start -a com.example.helloworld.MainActivity -b com.example.helloworld"
