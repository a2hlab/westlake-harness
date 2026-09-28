#!/usr/bin/env bash
# deploy-bridge.sh — 把 Bridge 装到一块 factory 态的鸿蒙板上，然后跑一个安卓 APK。
#
# 配方来源：src/tools/experiments/d600/recover_fn04_runtime_after_reflash.sh
# 与 alexpc:/opt/build-trees/adapter/deploy/DEPLOY_SOP.md（v4）。
# 本脚本相对原配方的改动只有一处：载荷来源改为「本机 07-27 覆盖层 + 8-05/8-06 delta」
# 的合成件，因为原配方引用的 /Volumes/Bridge 外置卷在本机不可达（隧道 6.5 kB/s 搬不动）。
#
# ⚠️ 版本已知不一致（本轮是**试探**，不是复现 PR#3）：
#   覆盖层 libart.so 11,761,184 B（07-27）vs alexpc 整包 11,662,488 B（07-25）
#   boot.art 亦不同。补进去的 6 个图形库来自后者。若 ART 与图形层耦合超出预期，
#   本轮会失败——**失败点落在哪一层本身就是要采的数据**（ab-compare-plan §7）。
#
# SOP 铁律（照抄，不得省）：
#   1. 禁裸 kill <PID>；停服务用 begetctl stop_service
#   2. 推 /system 必走 staging：先 send 到 /data/local/tmp/stage/，验是文件，再 cp
#   3. hdc 返回 connect-key / 超时 / [Fail]Not a directory → 立即停手
#
# 用法:
#   ./deploy-bridge.sh <板序列号> [APK路径]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"

BOARD="${1:?usage: deploy-bridge.sh <板序列号> [APK路径]}"
APK="${2:-${REPO}/var/evidence/task70-android-golden/bringup-20260804/apk/HelloWorld.apk}"
PKG=com.example.helloworld
ACT=com.example.helloworld.MainActivity

OVERLAY="${REPO}/.fn02-materialized/FN02-E01-CLOSURE-20260727T203000Z-f4-r7/system/android"
DELTA="${HOME}/orca/.bridge-payload/delta"
TS=$(date -u +%Y%m%dT%H%M%SZ)
EV="${REPO}/var/evidence/bridge-deploy/${TS}-${BOARD:0:4}"
STAGE=/data/local/tmp/bridge-stage
GEN=/data/bridge-gen

H() { hdc -t "${BOARD}" "$@"; }
D() { H shell "$1" 2>&1 | tr -d '\r'; }
die() { echo "❌ $*" >&2; exit 1; }
step() { echo; echo "══ $*"; }

for p in "${OVERLAY}" "${DELTA}" "${APK}"; do [ -e "${p}" ] || die "缺件: ${p}"; done
mkdir -p "${EV}"
exec > >(tee -a "${EV}/deploy.log") 2>&1

echo "板=${BOARD}  时间=${TS}  证据=${EV}"

step "Stage 0 · 前置检查（SOP 要求 factory 态）"
D "echo alive" | grep -q alive || die "板不通"
if D "ls -d /system/android 2>/dev/null" | grep -q /system/android; then
  echo "  ⚠️ /system/android 已存在——非 factory 态。继续会覆盖既有部署。"
fi
D "param get const.ohos.fullname" | sed 's/^/  ROM: /'

step "Stage 1 · 合成载荷（本机）"
WORK=$(mktemp -d); trap 'rm -rf "${WORK}"' EXIT
cp -R "${OVERLAY}" "${WORK}/android"
cp "${DELTA}"/lib64/*.so       "${WORK}/android/lib64/"
cp "${DELTA}"/adapter/*.so     "${WORK}/android/lib64/"
echo "  覆盖层 $(find "${WORK}/android" -type f | wc -l | tr -d ' ') 个文件"
echo "  其中 lib64: $(find "${WORK}/android/lib64" -type f | wc -l | tr -d ' ') 个"

step "Stage 2 · 挂读写 + SELinux permissive + AMS 路由参数"
H target mount >/dev/null 2>&1 || true
D "setenforce 0"
# support_anco_app：让 AMS 把安卓应用路由到 appspawn-x 而非原生 appspawn
D "param set persist.sys.abilityms.support_anco_app true"
# 生命周期预算旋钮：默认 14.5s 窗口对冷启动 ART 太紧（§9 ③线约束，须记录）
D "param set persist.sys.abilityms.timeout_unit_time_ratio 20"
D "param set ro.product.cpu.abilist arm64-v8a"
D "param set ro.product.cpu.abilist64 arm64-v8a"
echo "旋钮: support_anco_app=true timeout_unit_time_ratio=20" > "${EV}/knobs.txt"

step "Stage 3 · 推覆盖层到 /data 并 bind-mount（SOP 铁律 2：不直推 /system）"
D "rm -rf ${GEN}; mkdir -p ${GEN} ${STAGE} /system/android"
H file send "${WORK}/android" "${GEN}" 2>&1 | tail -1
D "ls -ld ${GEN}/android" | grep -q '^d' || die "覆盖层未落地（SOP 中止条件）"
D "umount /system/android 2>/dev/null || true"
D "mount --bind ${GEN}/android /system/android"
D "ls /system/android" | tr '\n' ' ' | sed 's/^/  挂载后: /'; echo

step "Stage 4 · boot 镜像软链与 SELinux 标签"
D "if [ -f /system/android/framework/arm64/boot.art ] && [ ! -e /system/android/framework/boot.art ]; then ln -sf arm64/boot.art /system/android/framework/boot.art; fi"
D "find /system/android -exec chcon u:object_r:system_file:s0 {} \; 2>/dev/null; echo done"
D "find /system/android/lib64 -exec chcon u:object_r:system_lib_file:s0 {} \; 2>/dev/null; echo done"
D "for f in /system/android/framework/arm64/boot*.art /system/android/framework/arm64/boot*.oat /system/android/framework/arm64/boot*.vdex; do chcon u:object_r:system_lib_file:s0 \$f 2>/dev/null; done; echo done"
# musl 兼容软链：AOSP 侧二进制找 libc_musl.so
D "ln -sf /lib/ld-musl-aarch64.so.1 /system/lib/libc_musl.so"
D "chcon -h u:object_r:system_lib_file:s0 /system/lib/libc_musl.so 2>/dev/null || true"

step "Stage 5 · 装 appspawn-x 与 init cfg"
H file send "${DELTA}/adapter/appspawn-x-stock" "${STAGE}/appspawn-x" 2>&1 | tail -1
H file send "${DELTA}/config/appspawn_x.cfg" "${STAGE}/appspawn_x.cfg" 2>&1 | tail -1
D "ls -la ${STAGE}/appspawn-x" | grep -q '^-' || die "appspawn-x 未落地成文件（SOP 中止条件）"
D "cp ${STAGE}/appspawn-x /system/bin/appspawn-x; chmod 0755 /system/bin/appspawn-x"
D "chcon u:object_r:appspawn_exec:s0 /system/bin/appspawn-x 2>/dev/null || restorecon -F /system/bin/appspawn-x 2>/dev/null || true"
D "cp ${STAGE}/appspawn_x.cfg /system/etc/init/appspawn_x.cfg; chmod 0550 /system/etc/init/appspawn_x.cfg"
D "chcon u:object_r:system_etc_file:s0 /system/etc/init/appspawn_x.cfg 2>/dev/null || restorecon -F /system/etc/init/appspawn_x.cfg 2>/dev/null || true"

step "Stage 6 · 起 appspawn-x（SOP 铁律 1：begetctl，不裸 kill）"
D "begetctl stop_service appspawn-x >/dev/null 2>&1 || true"
sleep 1
D "begetctl start_service appspawn-x >/dev/null 2>&1 || true"
sleep 3
SPID=$(D "pidof appspawn-x" | head -1)
echo "  appspawn-x pid=${SPID:-无}"
D "ls -la /dev/unix/socket/AppSpawnX 2>/dev/null || ls -la /dev/socket/AppSpawnX 2>/dev/null || echo '  socket 未见'" | sed 's/^/  /'

step "Stage 7 · 装安卓 APK 并启动"
"${SCRIPT_DIR}/keep-awake.sh" on harmony >/dev/null 2>&1 || true
H file send "${APK}" "${STAGE}/app.apk" 2>&1 | tail -1
D "bm install -p ${STAGE}/app.apk" | tee "${EV}/bm-install.txt"
D "aa force-stop ${PKG} 2>/dev/null || true"
D "hilog -r >/dev/null 2>&1 || true"
sleep 1
D "aa start -a ${ACT} -b ${PKG}" | tee "${EV}/aa-start.txt"
sleep 15

step "Stage 8 · 收证据"
D "hilog -x" > "${EV}/hilog.txt" 2>&1 || true
D "ps -A -o PID,PPID,UID,NAME | grep -E 'appspawn-x|${PKG}' | grep -v grep" > "${EV}/processes.txt" 2>&1 || true
D "snapshot_display -f /data/local/tmp/bridge-shot.jpeg" >/dev/null 2>&1 || true
H file recv /data/local/tmp/bridge-shot.jpeg "${EV}/screen.jpeg" >/dev/null 2>&1 || true

APP_PID=$(D "pidof ${PKG}" | head -1)
n() { grep -c "$1" "${EV}/hilog.txt" 2>/dev/null | head -1 || echo 0; }
{
  echo "board: ${BOARD}"
  echo "timestamp: ${TS}"
  echo "payload: 07-27 overlay + 20260805/06 delta（**版本不一致，本轮为试探**）"
  echo "appspawn_x_pid: ${SPID:-none}"
  echo "app_pid: ${APP_PID:-none}"
  echo "hits_AppSpawnX: $(n AppSpawnX)"
  echo "hits_AndroidRuntime: $(n AndroidRuntime)"
  echo "hits_ActivityThread: $(n ActivityThread)"
  echo "hits_onCreate: $(n onCreate)"
  echo "note: 本文件不产出「通过」结论；判定须依 ab-compare-plan §4 证据等级与 §6.3 三记号"
} | tee "${EV}/VERDICT.yaml"

echo
echo "证据目录: ${EV}"
