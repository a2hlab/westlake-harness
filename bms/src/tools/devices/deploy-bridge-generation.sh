#!/usr/bin/env bash
# deploy-bridge-generation.sh — 用一整套自洽的 deploy generation 部署 Bridge。
#
# 载荷：PR#3（feat(p0): reproduce Android HelloWorld first frame on D600）实际跑出
# 首帧的 generation 快照 `deploy-generation-24deb5f6-v1`，含四部分：
#   system/android/   安卓运行时覆盖层（ART / framework / etc，约 405 MB）
#   system/lib64/     **宿主侧服务补丁**（见下方致命警告）
#   appspawn-x + appspawn_x.cfg + appdata-sandbox.json
#   HelloWorld.apk    已验证的安卓样本
#
# ⚠️⚠️ 致命警告：替换宿主服务库之后不得再操作，必须立刻重启 ⚠️⚠️
#
#   system/lib64/ 里的 libbms.z.so（包管理）、libappms.z.so（应用管理）、
#   libinstalls.z.so（安装服务）是 **foundation 进程正在加载运行的核心库**。
#   在线覆盖它们 = 当场抽掉系统的包管理与应用管理能力。
#
#   2026-08-08 板 61ae 就是这样刷废的：`cp -a` 覆盖这三个库后继续跑
#   chcon / find / ln 等一长串命令，设备立即失联，最终必须重新刷机。
#
#   本脚本的对策是把顺序固定成：
#     先做完所有不碰这三个库的事（覆盖层、appspawn-x、cfg、标签、软链）
#     → **最后一步**才覆盖 system/lib64
#     → 覆盖完**立刻 reboot，中间不插任何命令**
#
# 用法:
#   ./deploy-bridge-generation.sh <板序列号> <generation目录>
#   # 重启后接 src/tools/devices/bridge-postboot.sh <板序列号>
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"

BOARD="${1:?usage: deploy-bridge-generation.sh <板序列号> <generation目录>}"
GENDIR="${2:?缺 generation 目录（含 system/android、system/lib64、appspawn-x）}"

TS=$(date -u +%Y%m%dT%H%M%SZ)
EV="${REPO}/var/evidence/bridge-deploy/${TS}-${BOARD:0:4}-gen"
STAGE=/data/local/tmp/gen-stage
GEN=/data/bridge-gen

H() { hdc -t "${BOARD}" "$@"; }
D() { H shell "$1" 2>&1 | tr -d '\r'; }
die() { echo "❌ $*" >&2; exit 1; }
step() { echo; echo "══ $*"; }

for p in "${GENDIR}/system/android" "${GENDIR}/system/lib64" "${GENDIR}/appspawn-x" "${GENDIR}/appspawn_x.cfg"; do
  [ -e "${p}" ] || die "generation 缺件: ${p}"
done
mkdir -p "${EV}"
exec > >(tee -a "${EV}/deploy.log") 2>&1
echo "板=${BOARD}  generation=${GENDIR}  证据=${EV}"

step "Stage 0 · 前置"
D "echo alive" | grep -q alive || die "板不通"
D "param get const.ohos.fullname" | sed 's/^/  ROM: /'
H target mount >/dev/null 2>&1 || true
D "setenforce 0"
D "param set persist.sys.abilityms.support_anco_app true"
D "param set persist.sys.abilityms.timeout_unit_time_ratio 20"
D "param set ro.product.cpu.abilist arm64-v8a"
D "param set ro.product.cpu.abilist64 arm64-v8a"
D "begetctl stop_service appspawn-x >/dev/null 2>&1 || true"
D "rm -rf ${STAGE}; mkdir -p ${STAGE}"

step "Stage 1 · 安卓运行时覆盖层 → /data 再 bind-mount（不碰 /system 服务）"
D "umount /system/android 2>/dev/null || true"
D "rm -rf ${GEN}; mkdir -p ${GEN} /system/android"
H file send "${GENDIR}/system/android" "${GEN}" 2>&1 | tail -1
D "ls -ld ${GEN}/android" | grep -q '^d' || die "覆盖层未落地"
D "mount --bind ${GEN}/android /system/android"
D "ls /system/android" | tr '\n' ' ' | sed 's/^/  /'; echo

step "Stage 2 · appspawn-x / wrapper / cfg / sandbox"
H file send "${GENDIR}/appspawn-x"   "${STAGE}/appspawn-x"   2>&1 | tail -1
H file send "${GENDIR}/appspawn_x.cfg" "${STAGE}/appspawn_x.cfg" 2>&1 | tail -1
[ -f "${GENDIR}/appdata-sandbox.json" ] && \
  H file send "${GENDIR}/appdata-sandbox.json" "${STAGE}/appdata-sandbox.json" 2>&1 | tail -1
W=$(mktemp)
cat > "${W}" <<'WRAP'
#!/system/bin/sh
export ANDROID_ROOT=/system/android
export ANDROID_DATA=/data
export ANDROID_BOOT_IMAGE=
export ANDROID_I18N_ROOT=/system/android
export ANDROID_TZDATA_ROOT=/system/android
export ICU_DATA=/system/android/etc/icu
export APPSPAWNX_FAST_DEV=0
export APPSPAWNX_CHECK_JNI=0
export APPSPAWNX_NO_JIT=1
export APPSPAWNX_VERBOSE_VERIFIER=1
export LD_LIBRARY_PATH=/system/android/lib64:/system/lib64/chipset-sdk-sp:/system/lib64:/system/lib64/platformsdk:/system/lib64/chipset-sdk:/system/lib64/ndk
exec /system/bin/appspawn-x.real "$@" 2>/data/local/tmp/appspawn-x-stderr.log
WRAP
H file send "${W}" "${STAGE}/wrap.sh" >/dev/null 2>&1; rm -f "${W}"
D "ls -la ${STAGE}/appspawn-x" | grep -q '^-' || die "appspawn-x 未落地成文件"
D "cp ${STAGE}/appspawn-x /system/bin/appspawn-x.real; chmod 0755 /system/bin/appspawn-x.real
   cp ${STAGE}/wrap.sh    /system/bin/appspawn-x;      chmod 0755 /system/bin/appspawn-x
   chcon u:object_r:appspawn_exec:s0 /system/bin/appspawn-x /system/bin/appspawn-x.real 2>/dev/null || true
   cp ${STAGE}/appspawn_x.cfg /system/etc/init/appspawn_x.cfg; chmod 0550 /system/etc/init/appspawn_x.cfg
   chcon u:object_r:system_etc_file:s0 /system/etc/init/appspawn_x.cfg 2>/dev/null || true
   [ -f ${STAGE}/appdata-sandbox.json ] && { mkdir -p /system/etc/sandbox; cp ${STAGE}/appdata-sandbox.json /system/etc/sandbox/; }
   echo ok"

step "Stage 3 · 标签与软链（仍不碰宿主服务库）"
D "find /system/android -exec chcon u:object_r:system_file:s0 {} \; 2>/dev/null; echo ok"
D "find /system/android/lib64 -exec chcon u:object_r:system_lib_file:s0 {} \; 2>/dev/null; echo ok"
D "for f in /system/android/framework/arm64/boot*.art /system/android/framework/arm64/boot*.oat /system/android/framework/arm64/boot*.vdex; do chcon u:object_r:system_lib_file:s0 \$f 2>/dev/null; done; echo ok"
D "ln -sf /lib/ld-musl-aarch64.so.1 /system/lib/libc_musl.so 2>/dev/null || true"
D "if [ -f /system/android/framework/arm64/boot.art ] && [ ! -e /system/android/framework/boot.art ]; then ln -sf arm64/boot.art /system/android/framework/boot.art; fi; echo ok"

step "Stage 4 · 宿主服务补丁 —— 覆盖后立刻重启，中间不得插任何命令"
echo "  ⚠️ libbms/libappms/libinstalls 是 foundation 正在加载的库；"
echo "     2026-08-08 板 61ae 因覆盖后继续操作而刷废，见本文件头部警告。"
H file send "${GENDIR}/system/lib64" "${STAGE}" 2>&1 | tail -1
# 把「覆盖 + 打标签 + reboot」压成设备端一条命令，中间不回主机、不再发第二条
D "cp -a ${STAGE}/lib64/. /system/lib64/ \
   && find /system/lib64/westlake /system/lib64/appspawn /system/lib64/platformsdk -exec chcon u:object_r:system_lib_file:s0 {} \; 2>/dev/null \
   && for f in /system/lib64/libbms.z.so /system/lib64/libappms.z.so /system/lib64/libinstalls.z.so /system/lib64/libapk_installer.so /system/lib64/libappspawn_client.z.so /system/lib64/libwestlake_thread_guard_registry.so /system/lib64/libwestlake_hap_domain_wrapper.so; do chcon u:object_r:system_lib_file:s0 \$f 2>/dev/null; done \
   ; sync; reboot"

echo
echo "已发出重启。板子回来后执行："
echo "  src/tools/devices/bridge-postboot.sh ${BOARD}"
echo "证据目录: ${EV}"
