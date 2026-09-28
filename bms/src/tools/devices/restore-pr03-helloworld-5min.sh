#!/usr/bin/env bash
# 刷机后，从本地 PR03 74e6 完整载荷恢复 Android HelloWorld 并上屏。
# 不编译；只传已有 APK / so / framework / 配置。
#
# 用法：
#   ./restore-pr03-helloworld-5min.sh 61ae0be500000000000000000324012c
#   ./restore-pr03-helloworld-5min.sh --check-only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"
PAYLOAD_ROOT="${BRIDGE_PAYLOAD:-/Users/zhaoyue/orca/.bridge-payload/pr03-74e6-portable}"
HDC_BIN="${HDC_BIN:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}"
FFMPEG_BIN="${FFMPEG_BIN:-$(command -v ffmpeg || true)}"
PACKAGE="com.example.helloworld"
ABILITY="com.example.helloworld.MainActivity"
GENERATION="74e6f75976087d7890088b29c08482f17573a588fa5857cb6ca39264838ce16d"
REMOTE_ROOT="/data/pr03-74e6-portable"
REMOTE_ANDROID="${REMOTE_ROOT}/android"
REMOTE_ROUTE="${REMOTE_ROOT}/route"
REMOTE_RUNTIME="${REMOTE_ROOT}/runtime"
REMOTE_HOST="${REMOTE_ROOT}/host"
REMOTE_APK="${REMOTE_ROOT}/HelloWorld.apk"
ROUTE_TARGET="/system/lib64/westlake/route-a/${GENERATION}"

APK_SHA="2d122a7973ffd68c799700aaaaaa0593e5deec30bac83e22a9dc1bf9f64319fd"
APPSPAWN_SOURCE_SHA="c7fd4bd6f7474841eccf93687009e79748fbd7016a208faed0a70ea580a2976e"
CHILD_SOURCE_SHA="f9a36217ebf8a6d08a239d8412be540d9f8cf0ebe9614bfc9486890954d8a828"
SANDBOX_SHA="49a278fa47c28ef58ef056864278195d8ac8cdac5a362d737c0c71d7ec0a3f6a"
CFG_SHA="5a499244840da582060a0d4db94fb769354b0d4f9e79bac56d4cf63414cfefb4"
PROVIDER_SOURCE_SHA="9c650fe37734d8aa29f0abe954021153f831db3c264c35aca7c02b07ce26dc1d"
RUNTIME_SOURCE_SHA="9689ce764083b4f6db848b036ff292cdd4962ecb2e1ca26373850390efb42812"
# No-compile coherent touch closure.  Two class-name bytes make input use the
# already-present BCP InputEventBridge; the three parents are re-pinned to the
# resulting child SHA values so exact runtime admission remains closed.
RUNTIME_SHA="9ccf64f8d1f6e1748665057273eaa4c2770098934d39afa160f2c6b4c18b06db"
PROVIDER_SHA="6787ea7d3c4ec0a382621360e3434885b0167446e22217a439b8d17745e54630"
CHILD_SHA="66afb06c10db5e986d294a465cf787f4be3302ce6be3a17d49309b368b1ec090"
APPSPAWN_SHA="43d5a319fa43e30fb712c2e39d29ba55e4bf82d171e97af1e6da9fcacc28920c"
ROUTE_TGR_SHA="674d3ef3b9b00b367e389b539df4ae71bf2a12e3dd25dba962d6fcc7f240f063"
LZMA_SHA="239bdf61bcc8c971ef65c6e688c87048d01781d4ab8707546668f5d5e4cc7d40"
LIBBMS_SHA="f8ef078df8a0fa483b60c1a997831a8190448545e141b9568fb14eacaf9da105"
LIBINSTALLS_SHA="2c9a5294a253acb57394cc79956a4b30182a7a0ecad570844c395b38d34d82e0"
LIBAPK_INSTALLER_SHA="184d40a56a9116ab87d079413ba31d92e3d45c86a2f9b1088ffc97725ec650f9"
LIBAPPMS_SHA="182937bb194cdc73a559f72cf6949ddba3df912ee0a852e69215fe3009eb9006"
LIBAPPSPAWN_CLIENT_SHA="f4df7769e64bf836015b5374f4f98915a1279a88e97f05714879855d55d3658f"
LIBABILITYMS_SHA="23f77771a40e2229f55df0e0a5348f5dec977992aae945a48e4358bdd26ca46a"
HAP_WRAPPER_SHA="06c35353b67494f061b99d2691d2c9acdd16b89d1a65865c0c96f8aa5dc8e30f"
ANDROID_MANIFEST_SHA="55e0af34bb41ed717f114c016c8f377a705157815691c88a2540746a7c0add15"
ROUTE_MANIFEST_SHA="b3f958e2413508f9c3f5a4f1a5f454c5660b5577502a5ca80036b28b2eb0c02d"

die() { echo "失败：$*" >&2; exit 1; }
step() { echo; echo "==> $*"; }
local_hash() { shasum -a 256 "$1" | cut -d ' ' -f 1; }
local_tree_hash() {
  (cd "$1" && find . -type f -print0 | xargs -0 shasum -a 256 | LC_ALL=C sort | shasum -a 256 | cut -d ' ' -f 1)
}
check_local_hash() {
  local expected="$1" path="$2" actual
  [ -f "$path" ] || die "本地缺件：$path"
  actual="$(local_hash "$path")"
  [ "$actual" = "$expected" ] || die "本地文件 hash 不对：$path ($actual)"
}

preflight_local() {
  step "检查本地 PR03 完整载荷"
  [ -x "$HDC_BIN" ] || die "找不到 hdc：$HDC_BIN"
  [ -x "$FFMPEG_BIN" ] || die "找不到 ffmpeg（用于拒绝白屏截图）"
  [ -f "$SCRIPT_DIR/pr03-runtime-recover-device.sh" ] || die "缺少开机恢复脚本"
  [ -f "$SCRIPT_DIR/pr03-runtime-recovery.cfg" ] || die "缺少开机恢复 init 配置"
  [ -d "$PAYLOAD_ROOT/android" ] || die "缺少 $PAYLOAD_ROOT/android"
  [ -d "$PAYLOAD_ROOT/route" ] || die "缺少 $PAYLOAD_ROOT/route"
  [ "$(find "$PAYLOAD_ROOT/android" -type f | wc -l | tr -d ' ')" = "226" ] || die "Android 载荷不是 226 个文件"
  [ "$(find "$PAYLOAD_ROOT/route" -type f | wc -l | tr -d ' ')" = "28" ] || die "route 载荷不是 28 个文件"
  [ "$(local_tree_hash "$PAYLOAD_ROOT/android")" = "$ANDROID_MANIFEST_SHA" ] || die "Android 226 文件全量 manifest 不匹配"
  [ "$(local_tree_hash "$PAYLOAD_ROOT/route")" = "$ROUTE_MANIFEST_SHA" ] || die "route 28 文件全量 manifest 不匹配"

  check_local_hash "$APK_SHA" "$PAYLOAD_ROOT/apk/HelloWorld.apk"
  check_local_hash "$APPSPAWN_SOURCE_SHA" "$PAYLOAD_ROOT/runtime/appspawn-x"
  check_local_hash "$CHILD_SOURCE_SHA" "$PAYLOAD_ROOT/runtime/libwestlake_android_child.z.so"
  check_local_hash "$SANDBOX_SHA" "$PAYLOAD_ROOT/runtime/appdata-sandbox.json"
  check_local_hash "$CFG_SHA" "$PAYLOAD_ROOT/runtime/appspawn_x.cfg"
  check_local_hash "$PROVIDER_SOURCE_SHA" "$PAYLOAD_ROOT/route/libwestlake_android_runtime_provider.so"
  check_local_hash "$RUNTIME_SOURCE_SHA" "$PAYLOAD_ROOT/android/lib64/liboh_android_runtime.so"
  check_local_hash "$ROUTE_TGR_SHA" "$PAYLOAD_ROOT/route/libwestlake_thread_guard_registry.so"
  check_local_hash "$LZMA_SHA" "$PAYLOAD_ROOT/route/liblzma.so"
  check_local_hash "$LIBBMS_SHA" "$PAYLOAD_ROOT/host/system/lib64/libbms.z.so"
  check_local_hash "$LIBINSTALLS_SHA" "$PAYLOAD_ROOT/host/system/lib64/libinstalls.z.so"
  check_local_hash "$LIBAPK_INSTALLER_SHA" "$PAYLOAD_ROOT/host/system/lib64/libapk_installer.so"
  check_local_hash "$LIBAPPMS_SHA" "$PAYLOAD_ROOT/host/system/lib64/libappms.z.so"
  check_local_hash "$LIBAPPSPAWN_CLIENT_SHA" "$PAYLOAD_ROOT/host/system/lib64/libappspawn_client.z.so"
  check_local_hash "$LIBABILITYMS_SHA" "$PAYLOAD_ROOT/host/system/lib64/platformsdk/libabilityms.z.so"
  check_local_hash "$HAP_WRAPPER_SHA" "$PAYLOAD_ROOT/host/system/lib64/libwestlake_hap_domain_wrapper.so"
  echo "本地载荷完整：Android=226，route=28，APK/运行库/宿主库 hash 全部正确。"
}

if [ "${1:-}" = "--check-only" ]; then
  preflight_local
  exit 0
fi

BOARD="${1:-}"
if [ -z "$BOARD" ]; then
  TARGETS="$($HDC_BIN list targets 2>/dev/null | sed '/^$/d')"
  TARGET_COUNT="$(printf '%s\n' "$TARGETS" | sed '/^$/d' | wc -l | tr -d ' ')"
  [ "$TARGET_COUNT" = "1" ] || die "请传设备序列号；当前连接设备数：$TARGET_COUNT"
  BOARD="$TARGETS"
fi

H() { "$HDC_BIN" -t "$BOARD" "$@"; }
D() { H shell "$1" 2>&1 | tr -d '\r'; }
device_hash() { D "sha256sum $1 2>/dev/null" | head -n 1 | cut -d ' ' -f 1; }
device_tree_hash() {
  D "cd $1 && find . -type f -exec sha256sum {} \; | sort | sha256sum" | head -n 1 | cut -d ' ' -f 1
}
appspawn_pids() {
  D "pidof appspawn-x" 2>/dev/null | tr ' ' '\n' | sed '/^$/d' || true
}
app_child_lines() {
  D "ps -ef | grep '^$APP_UID ' | grep 'appspawn-x --socket-name AppSpawnX' | grep -v grep" 2>/dev/null || true
}
parent_maps_ready() {
  D "grep -q /system/lib64/appspawn/libwestlake_android_child.z.so /proc/$1/maps && grep -q /system/android/lib64/libwestlake_thread_guard_registry.so /proc/$1/maps && grep -q /system/android/lib64/liblzma.so /proc/$1/maps" >/dev/null 2>&1
}

wait_device() {
  local i
  for i in $(seq 1 90); do
    if "$HDC_BIN" list targets 2>/dev/null | grep -qx "$BOARD" && \
       D "param get bootevent.boot.completed" 2>/dev/null | grep -q true; then
      echo "设备已启动。"
      return 0
    fi
    sleep 2
  done
  die "等待设备启动超时：$BOARD"
}

send_file() {
  local src="$1" dst="$2"
  H file send "$src" "$dst" >/dev/null || die "传输失败：$src"
}

preflight_local
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-${BOARD:0:8}"
OUT_DIR="$PROJECT_ROOT/var/state/pr03-helloworld-restore/$RUN_ID"
REMOTE_STAGE="${REMOTE_ROOT}.staging-${RUN_ID}"
REMOTE_STAGE_ANDROID="${REMOTE_STAGE}/android"
REMOTE_STAGE_ROUTE="${REMOTE_STAGE}/route"
REMOTE_STAGE_RUNTIME="${REMOTE_STAGE}/runtime"
REMOTE_STAGE_HOST="${REMOTE_STAGE}/host"
REMOTE_STAGE_APK="${REMOTE_STAGE}/HelloWorld.apk"
REMOTE_PREVIOUS="${REMOTE_ROOT}.pre-restore-${RUN_ID}"
mkdir -p "$OUT_DIR"
exec > >(tee -a "$OUT_DIR/restore.log") 2>&1

step "连接设备 $BOARD"
D "echo alive" | grep -q alive || die "设备不通"
OS_NAME="$(D "param get const.ohos.fullname" | tr -d ' ')"
ARCH="$(D "uname -m" | tr -d ' ')"
[ "$OS_NAME" = "OpenHarmony-6.1.0.31" ] || die "ROM 不匹配：${OS_NAME}（本载荷只验证过 OpenHarmony-6.1.0.31）"
[ "$ARCH" = "aarch64" ] || die "架构不匹配：$ARCH"
H target mount >/dev/null 2>&1 || true
wait_device

step "停止全部 Android 进程，解除 backing 使用者"
D "aa force-stop $PACKAGE >/dev/null 2>&1 || true; aa force-stop com.a2hlab.bridge.zigzag >/dev/null 2>&1 || true; begetctl stop_service appspawn-x >/dev/null 2>&1 || true; for pid in \$(pidof appspawn-x 2>/dev/null); do kill -9 \$pid 2>/dev/null || true; done; true"
for i in $(seq 1 20); do
  [ -z "$(appspawn_pids)" ] && break
  sleep 1
done
[ -z "$(appspawn_pids)" ] || die "无法停止全部 appspawn-x parent/child"

if D "grep -Eq '/(data/)?(pr03-74e6-portable|zigzag-apk-lightup)(/|[[:space:]])' /proc/self/mountinfo" >/dev/null 2>&1; then
  step "检测到活跃 PR03/ZigZag bind，逐层卸载完整目标集合"
  D "set -e; for pass in 1 2 3 4 5 6 7 8; do changed=0; for target in \
'/data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libwestlake_bionic_signal_box.so' \
'/data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libmediandk.so' \
'/data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libtuanjie.so' \
'/data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libil2cpp.so' \
'/data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libmain.so' \
'/system/android/lib64/liboh_adapter_bridge.so' \
'/system/android/framework/oh-adapter-runtime.jar' \
'/system/android/lib64/libwestlake_bionic_pthread_bridge.so' \
'/system/android/lib64/libnativeloader.so' \
'/system/android/lib64/libandroid.so' \
'$ROUTE_TARGET/libwestlake_android_runtime_provider.so' \
'$ROUTE_TARGET/libnativeloader.so' \
'/system/lib64/libwestlake_thread_guard_registry.so' \
'/system/etc/sandbox/appdata-sandbox.json' \
'/system/bin/appspawn-x' \
'/system/lib64/appspawn/libwestlake_android_child.z.so' \
'/system/android/lib64/liblzma.so' \
'$ROUTE_TARGET' \
'/system/android'; do if grep -F \" \$target \" /proc/self/mountinfo | grep -Eq '/(data/)?(pr03-74e6-portable|zigzag-apk-lightup)(/|[[:space:]])'; then umount \"\$target\" || exit 31; changed=1; fi; done; [ \$changed = 0 ] && break; done; ! grep -Eq '/(data/)?(pr03-74e6-portable|zigzag-apk-lightup)(/|[[:space:]])' /proc/self/mountinfo"
fi

step "从 Mac 传入独立 staging 载荷（约 430 MB，不编译）"
D "set -e; test ! -e '$REMOTE_STAGE'; mkdir -p '$REMOTE_STAGE' '$REMOTE_STAGE_RUNTIME' '$REMOTE_STAGE_HOST/platformsdk'"
H file send "$PAYLOAD_ROOT/android" "$REMOTE_STAGE" >/dev/null || die "Android staging 传输失败"
H file send "$PAYLOAD_ROOT/route" "$REMOTE_STAGE" >/dev/null || die "route staging 传输失败"
send_file "$PAYLOAD_ROOT/runtime/appspawn-x" "$REMOTE_STAGE_RUNTIME/appspawn-x"
send_file "$PAYLOAD_ROOT/runtime/libwestlake_android_child.z.so" "$REMOTE_STAGE_RUNTIME/libwestlake_android_child.z.so"
send_file "$PAYLOAD_ROOT/runtime/appdata-sandbox.json" "$REMOTE_STAGE_RUNTIME/appdata-sandbox.json"
send_file "$PAYLOAD_ROOT/runtime/appspawn_x.cfg" "$REMOTE_STAGE_RUNTIME/appspawn_x.cfg"
send_file "$SCRIPT_DIR/pr03-runtime-recover-device.sh" "$REMOTE_STAGE_RUNTIME/pr03-runtime-recover.sh"
send_file "$SCRIPT_DIR/pr03-runtime-recovery.cfg" "$REMOTE_STAGE_RUNTIME/00_pr03_runtime_recovery.cfg"
send_file "$PAYLOAD_ROOT/apk/HelloWorld.apk" "$REMOTE_STAGE_APK"
send_file "$PAYLOAD_ROOT/host/system/lib64/libbms.z.so" "$REMOTE_STAGE_HOST/libbms.z.so"
send_file "$PAYLOAD_ROOT/host/system/lib64/libinstalls.z.so" "$REMOTE_STAGE_HOST/libinstalls.z.so"
send_file "$PAYLOAD_ROOT/host/system/lib64/libapk_installer.so" "$REMOTE_STAGE_HOST/libapk_installer.so"
send_file "$PAYLOAD_ROOT/host/system/lib64/libappms.z.so" "$REMOTE_STAGE_HOST/libappms.z.so"
send_file "$PAYLOAD_ROOT/host/system/lib64/libappspawn_client.z.so" "$REMOTE_STAGE_HOST/libappspawn_client.z.so"
send_file "$PAYLOAD_ROOT/host/system/lib64/libwestlake_hap_domain_wrapper.so" "$REMOTE_STAGE_HOST/libwestlake_hap_domain_wrapper.so"
send_file "$PAYLOAD_ROOT/host/system/lib64/platformsdk/libabilityms.z.so" "$REMOTE_STAGE_HOST/platformsdk/libabilityms.z.so"

D "set -e; find '$REMOTE_STAGE_ANDROID' -type d -exec chmod 0755 {} \;; find '$REMOTE_STAGE_ROUTE' -type d -exec chmod 0755 {} \;; find '$REMOTE_STAGE_ROUTE' -type f -exec chmod 0644 {} \;; chmod 0755 '$REMOTE_STAGE_RUNTIME/appspawn-x' '$REMOTE_STAGE_RUNTIME/libwestlake_android_child.z.so'; chmod 0644 '$REMOTE_STAGE_RUNTIME/appdata-sandbox.json' '$REMOTE_STAGE_RUNTIME/appspawn_x.cfg' '$REMOTE_STAGE_RUNTIME/pr03-runtime-recover.sh' '$REMOTE_STAGE_RUNTIME/00_pr03_runtime_recovery.cfg'"
[ "$(D "find '$REMOTE_STAGE_ANDROID' -type f | wc -l" | tr -d ' ')" = "226" ] || die "板上 staging Android 文件数不对"
[ "$(D "find '$REMOTE_STAGE_ROUTE' -type f | wc -l" | tr -d ' ')" = "28" ] || die "板上 staging route 文件数不对"
[ "$(device_tree_hash "$REMOTE_STAGE_ANDROID")" = "$ANDROID_MANIFEST_SHA" ] || die "板上 staging Android 226 文件全量 manifest 不对"
[ "$(device_tree_hash "$REMOTE_STAGE_ROUTE")" = "$ROUTE_MANIFEST_SHA" ] || die "板上 staging route 28 文件全量 manifest 不对"
[ "$(device_hash "$REMOTE_STAGE_APK")" = "$APK_SHA" ] || die "板上 staging APK hash 不对"
[ "$(device_hash "$REMOTE_STAGE_RUNTIME/appspawn-x")" = "$APPSPAWN_SOURCE_SHA" ] || die "板上 staging 源 appspawn-x hash 不对"
[ "$(device_hash "$REMOTE_STAGE_RUNTIME/libwestlake_android_child.z.so")" = "$CHILD_SOURCE_SHA" ] || die "板上 staging 源 child hash 不对"
[ "$(device_hash "$REMOTE_STAGE_ROUTE/libwestlake_android_runtime_provider.so")" = "$PROVIDER_SOURCE_SHA" ] || die "板上 staging 源 provider hash 不对"
[ "$(device_hash "$REMOTE_STAGE_ANDROID/lib64/liboh_android_runtime.so")" = "$RUNTIME_SOURCE_SHA" ] || die "板上 staging 源 runtime hash 不对"
echo "载荷传输与读回通过。"

step "从现成二进制生成主线程触摸一致闭包（不编译）"
D "set -e; printf X | dd of='$REMOTE_STAGE_ANDROID/lib64/liboh_android_runtime.so' bs=1 seek=174938 conv=notrunc 2>/dev/null; printf X | dd of='$REMOTE_STAGE_ANDROID/lib64/liboh_android_runtime.so' bs=1 seek=182866 conv=notrunc 2>/dev/null; printf '%s' '$RUNTIME_SHA' | dd of='$REMOTE_STAGE_ROUTE/libwestlake_android_runtime_provider.so' bs=1 seek=24106 conv=notrunc 2>/dev/null; printf '%s' '$RUNTIME_SHA' | dd of='$REMOTE_STAGE_ROUTE/libwestlake_android_runtime_provider.so' bs=1 seek=24318 conv=notrunc 2>/dev/null; printf '%s' '$PROVIDER_SHA' | dd of='$REMOTE_STAGE_RUNTIME/libwestlake_android_child.z.so' bs=1 seek=27568 conv=notrunc 2>/dev/null; for off in 38549 38761 38891; do printf '%s' '$CHILD_SHA' | dd of='$REMOTE_STAGE_RUNTIME/appspawn-x' bs=1 seek=\$off conv=notrunc 2>/dev/null; done; chmod 0755 '$REMOTE_STAGE_RUNTIME/appspawn-x' '$REMOTE_STAGE_RUNTIME/libwestlake_android_child.z.so'; chmod 0644 '$REMOTE_STAGE_ANDROID/lib64/liboh_android_runtime.so' '$REMOTE_STAGE_ROUTE/libwestlake_android_runtime_provider.so'"
[ "$(device_hash "$REMOTE_STAGE_ANDROID/lib64/liboh_android_runtime.so")" = "$RUNTIME_SHA" ] || die "staging 触摸 runtime 闭包 hash 不对"
[ "$(device_hash "$REMOTE_STAGE_ROUTE/libwestlake_android_runtime_provider.so")" = "$PROVIDER_SHA" ] || die "staging 触摸 provider 闭包 hash 不对"
[ "$(device_hash "$REMOTE_STAGE_RUNTIME/libwestlake_android_child.z.so")" = "$CHILD_SHA" ] || die "staging 触摸 child 闭包 hash 不对"
[ "$(device_hash "$REMOTE_STAGE_RUNTIME/appspawn-x")" = "$APPSPAWN_SHA" ] || die "staging 触摸 appspawn-x 闭包 hash 不对"
echo "触摸一致闭包已生成：runtime → provider → child → appspawn-x。"

step "原子切换完整 PR03 backing，保留旧根作为恢复点"
D "set -e; test ! -e '$REMOTE_PREVIOUS'; if [ -e '$REMOTE_ROOT' ]; then mv '$REMOTE_ROOT' '$REMOTE_PREVIOUS'; fi; mv '$REMOTE_STAGE' '$REMOTE_ROOT'; sync"
[ "$(device_hash "$REMOTE_RUNTIME/appspawn-x")" = "$APPSPAWN_SHA" ] || die "原子切换后 appspawn-x hash 不对"
echo "旧 backing（如存在）保留在：$REMOTE_PREVIOUS"

step "安装 PR03 宿主库、init 配置和每次开机自动恢复 hook"
D "set -e; begetctl stop_service appspawn-x >/dev/null 2>&1 || true; mkdir -p /system/etc/init /system/lib64/platformsdk /system/android /system/lib64/appspawn $ROUTE_TARGET /system/etc/sandbox; [ -e /system/bin/appspawn-x ] || touch /system/bin/appspawn-x; [ -e /system/lib64/appspawn/libwestlake_android_child.z.so ] || touch /system/lib64/appspawn/libwestlake_android_child.z.so; [ -e /system/etc/sandbox/appdata-sandbox.json ] || touch /system/etc/sandbox/appdata-sandbox.json; [ -e /system/lib64/libwestlake_thread_guard_registry.so ] || touch /system/lib64/libwestlake_thread_guard_registry.so; cp $REMOTE_RUNTIME/appspawn_x.cfg /system/etc/init/appspawn_x.cfg; cp $REMOTE_RUNTIME/pr03-runtime-recover.sh /system/etc/pr03-runtime-recover.sh; cp $REMOTE_RUNTIME/00_pr03_runtime_recovery.cfg /system/etc/init/00_pr03_runtime_recovery.cfg; chown 0:0 /system/etc/init/appspawn_x.cfg /system/etc/pr03-runtime-recover.sh /system/etc/init/00_pr03_runtime_recovery.cfg; chmod 0550 /system/etc/init/appspawn_x.cfg /system/etc/pr03-runtime-recover.sh /system/etc/init/00_pr03_runtime_recovery.cfg; chcon u:object_r:system_etc_file:s0 /system/etc/init/appspawn_x.cfg /system/etc/pr03-runtime-recover.sh /system/etc/init/00_pr03_runtime_recovery.cfg"

# 核心库被 foundation 正在加载。覆盖和 reboot 必须在同一次设备 shell 内完成，
# 中间不能再从主机发命令。
D "(set -e; cp $REMOTE_HOST/libbms.z.so /system/lib64/libbms.z.so; cp $REMOTE_HOST/libinstalls.z.so /system/lib64/libinstalls.z.so; cp $REMOTE_HOST/libapk_installer.so /system/lib64/libapk_installer.so; cp $REMOTE_HOST/libappms.z.so /system/lib64/libappms.z.so; cp $REMOTE_HOST/libappspawn_client.z.so /system/lib64/libappspawn_client.z.so; cp $REMOTE_HOST/libwestlake_hap_domain_wrapper.so /system/lib64/libwestlake_hap_domain_wrapper.so; cp $REMOTE_HOST/libbms.z.so /system/lib64/platformsdk/libbms.z.so; cp $REMOTE_HOST/libinstalls.z.so /system/lib64/platformsdk/libinstalls.z.so; cp $REMOTE_HOST/libapk_installer.so /system/lib64/platformsdk/libapk_installer.so; cp $REMOTE_HOST/libappms.z.so /system/lib64/platformsdk/libappms.z.so; cp $REMOTE_HOST/libappspawn_client.z.so /system/lib64/platformsdk/libappspawn_client.z.so; cp $REMOTE_HOST/platformsdk/libabilityms.z.so /system/lib64/platformsdk/libabilityms.z.so; chmod 0755 /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so /system/lib64/libapk_installer.so /system/lib64/libappms.z.so /system/lib64/libappspawn_client.z.so /system/lib64/libwestlake_hap_domain_wrapper.so /system/lib64/platformsdk/libbms.z.so /system/lib64/platformsdk/libinstalls.z.so /system/lib64/platformsdk/libapk_installer.so /system/lib64/platformsdk/libappms.z.so /system/lib64/platformsdk/libappspawn_client.z.so /system/lib64/platformsdk/libabilityms.z.so; chcon u:object_r:system_lib_file:s0 /system/lib64/libbms.z.so /system/lib64/libinstalls.z.so /system/lib64/libapk_installer.so /system/lib64/libappms.z.so /system/lib64/libappspawn_client.z.so /system/lib64/libwestlake_hap_domain_wrapper.so /system/lib64/platformsdk/libbms.z.so /system/lib64/platformsdk/libinstalls.z.so /system/lib64/platformsdk/libapk_installer.so /system/lib64/platformsdk/libappms.z.so /system/lib64/platformsdk/libappspawn_client.z.so /system/lib64/platformsdk/libabilityms.z.so); host_rc=\$?; sync; reboot; exit \$host_rc" >/dev/null 2>&1 || true

wait_device
sleep 5
H target mount >/dev/null 2>&1 || true
wait_device

step "确认本次 boot 已自动恢复 PR03 运行闭包"
[ "$(D "param get sys.pr03.runtime.ready" | tr -d ' ')" = "true" ] || die "开机恢复没有进入 READY"
D "grep -q '^host_boot_completed=true$' /data/service/el1/public/appspawnx/pr03-boot-recovery.txt; grep -q '^selinux_mode=Permissive$' /data/service/el1/public/appspawnx/pr03-boot-recovery.txt; grep -q '^touch_closure=READY$' /data/service/el1/public/appspawnx/pr03-boot-recovery.txt; grep -q '^mount_count=7$' /data/service/el1/public/appspawnx/pr03-boot-recovery.txt; grep -q '^state=READY$' /data/service/el1/public/appspawnx/pr03-boot-recovery.txt" || die "开机恢复回执不完整"
[ "$(D "grep -c ' /pr03-74e6-portable/' /proc/self/mountinfo" | tr -d ' ')" = "7" ] || die "开机没有自动恢复精确 7 个 bind"

step "确认宿主库已由 foundation 加载"
[ "$(device_hash /system/lib64/libbms.z.so)" = "$LIBBMS_SHA" ] || die "libbms 未激活"
[ "$(device_hash /system/lib64/libappms.z.so)" = "$LIBAPPMS_SHA" ] || die "libappms 未激活"
[ "$(device_hash /system/lib64/libappspawn_client.z.so)" = "$LIBAPPSPAWN_CLIENT_SHA" ] || die "libappspawn_client 未激活"
[ "$(device_hash /system/lib64/platformsdk/libabilityms.z.so)" = "$LIBABILITYMS_SHA" ] || die "libabilityms 未激活"
[ "$(device_hash /system/lib64/libinstalls.z.so)" = "$LIBINSTALLS_SHA" ] || die "libinstalls 未激活"
[ "$(device_hash /system/lib64/libapk_installer.so)" = "$LIBAPK_INSTALLER_SHA" ] || die "libapk_installer 未激活"
[ "$(device_hash /system/lib64/libwestlake_hap_domain_wrapper.so)" = "$HAP_WRAPPER_SHA" ] || die "HAP wrapper 未激活"
[ "$(device_hash /system/lib64/platformsdk/libbms.z.so)" = "$LIBBMS_SHA" ] || die "platformsdk/libbms 未激活"
[ "$(device_hash /system/lib64/platformsdk/libinstalls.z.so)" = "$LIBINSTALLS_SHA" ] || die "platformsdk/libinstalls 未激活"
[ "$(device_hash /system/lib64/platformsdk/libapk_installer.so)" = "$LIBAPK_INSTALLER_SHA" ] || die "platformsdk/libapk_installer 未激活"
[ "$(device_hash /system/lib64/platformsdk/libappms.z.so)" = "$LIBAPPMS_SHA" ] || die "platformsdk/libappms 未激活"
[ "$(device_hash /system/lib64/platformsdk/libappspawn_client.z.so)" = "$LIBAPPSPAWN_CLIENT_SHA" ] || die "platformsdk/libappspawn_client 未激活"
FOUNDATION_PIDS="$(D "pidof foundation" 2>/dev/null | tr ' ' '\n' | sed '/^$/d' || true)"
[ "$(printf '%s\n' "$FOUNDATION_PIDS" | sed '/^$/d' | wc -l | tr -d ' ')" = "1" ] || die "foundation 不是唯一进程"
FOUNDATION_PID="$(printf '%s\n' "$FOUNDATION_PIDS" | sed '/^$/d' | head -n 1)"
D "grep -q /system/lib64/libbms.z.so /proc/$FOUNDATION_PID/maps && grep -q /system/lib64/libappms.z.so /proc/$FOUNDATION_PID/maps && grep -q /system/lib64/libappspawn_client.z.so /proc/$FOUNDATION_PID/maps && grep -q /system/lib64/platformsdk/libabilityms.z.so /proc/$FOUNDATION_PID/maps" || die "foundation 没加载完整 PR03 宿主库"

step "重装精确 HelloWorld APK"
D "bm uninstall -n $PACKAGE" >/dev/null 2>&1 || true
INSTALL_RESULT="$(D "bm install -p $REMOTE_APK")"
echo "$INSTALL_RESULT"
printf '%s\n' "$INSTALL_RESULT" | grep -q "install bundle successfully" || die "APK 安装失败"
[ "$(device_hash "/data/app/el1/bundle/public/$PACKAGE/android/base.apk")" = "$APK_SHA" ] || die "安装后的 APK hash 不对"
BUNDLE_DUMP="$(D "bm dump -n $PACKAGE")"
printf '%s\n' "$BUNDLE_DUMP" | grep -q '"bundleType": 10' || die "包没有注册成 Android bundleType=10"
APP_UID="$(printf '%s\n' "$BUNDLE_DUMP" | grep -oE '"uid": *[0-9]+' | head -n 1 | grep -oE '[0-9]+')"
[ -n "$APP_UID" ] || die "取不到应用 UID"
echo "HelloWorld UID=${APP_UID}, bundleType=10。"

step "建立应用沙箱目录"
D "set -e; for d in /data/app/el1/100/base /data/app/el1/100/database /data/app/el2/100/base /data/app/el2/100/database /data/app/el2/100/sharefiles /data/app/el3/100/base /data/app/el3/100/database /data/app/el4/100/base /data/app/el4/100/database; do mkdir -p \${d}/$PACKAGE; done; mkdir -p /data/app/el2/100/log/$PACKAGE; for s in cache code_cache databases files haps no_backup preferences shared_prefs temp; do mkdir -p /data/app/el2/100/base/$PACKAGE/\${s}; done; chown -R $APP_UID:$APP_UID /data/app/el1/100/base/$PACKAGE /data/app/el1/100/database/$PACKAGE /data/app/el2/100/base/$PACKAGE /data/app/el2/100/database/$PACKAGE /data/app/el2/100/sharefiles/$PACKAGE /data/app/el3/100/base/$PACKAGE /data/app/el3/100/database/$PACKAGE /data/app/el4/100/base/$PACKAGE /data/app/el4/100/database/$PACKAGE; chown $APP_UID:log /data/app/el2/100/log/$PACKAGE; chmod -R 0700 /data/app/el1/100/base/$PACKAGE /data/app/el2/100/base/$PACKAGE /data/app/el2/100/sharefiles/$PACKAGE /data/app/el3/100/base/$PACKAGE /data/app/el4/100/base/$PACKAGE; chmod 0770 /data/app/el1/100/database/$PACKAGE /data/app/el2/100/database/$PACKAGE /data/app/el2/100/log/$PACKAGE /data/app/el3/100/database/$PACKAGE /data/app/el4/100/database/$PACKAGE; chcon -R u:object_r:appdat:s0 /data/app/el1/100/base/$PACKAGE /data/app/el1/100/database/$PACKAGE /data/app/el2/100/base/$PACKAGE /data/app/el2/100/database/$PACKAGE /data/app/el2/100/sharefiles/$PACKAGE /data/app/el3/100/base/$PACKAGE /data/app/el3/100/database/$PACKAGE /data/app/el4/100/base/$PACKAGE /data/app/el4/100/database/$PACKAGE; chcon u:object_r:data_app_el2_file:s0 /data/app/el2/100/log/$PACKAGE"
# OH 6.1 toolbox 的 chcon -R 在这个目录树上只处理首个子项；逐项执行，
# 否则严格校验会在安装器预建的 code_cache/files 等目录上随机 first-bad。
D "set -e; for app_root in /data/app/el1/100/base/$PACKAGE /data/app/el1/100/database/$PACKAGE /data/app/el2/100/base/$PACKAGE /data/app/el2/100/database/$PACKAGE /data/app/el2/100/sharefiles/$PACKAGE /data/app/el3/100/base/$PACKAGE /data/app/el3/100/database/$PACKAGE /data/app/el4/100/base/$PACKAGE /data/app/el4/100/database/$PACKAGE; do find \${app_root} -exec chcon u:object_r:appdat:s0 {} \;; done"
for APP_DIR in \
  "/data/app/el2/100/base/$PACKAGE" \
  "/data/app/el2/100/base/$PACKAGE/cache" \
  "/data/app/el2/100/base/$PACKAGE/code_cache" \
  "/data/app/el2/100/base/$PACKAGE/databases" \
  "/data/app/el2/100/base/$PACKAGE/files" \
  "/data/app/el2/100/base/$PACKAGE/haps" \
  "/data/app/el2/100/base/$PACKAGE/no_backup" \
  "/data/app/el2/100/base/$PACKAGE/preferences" \
  "/data/app/el2/100/base/$PACKAGE/shared_prefs" \
  "/data/app/el2/100/base/$PACKAGE/temp"; do
  [ "$(D "stat -c '%a:%u:%g:%C' $APP_DIR" | tr -d ' ')" = "700:$APP_UID:$APP_UID:u:object_r:appdat:s0" ] || die "应用目录 owner/mode/label 不对：$APP_DIR"
done

step "恢复 PR03 的 7 个精确 bind-mount"
D "aa force-stop $PACKAGE >/dev/null 2>&1 || true; begetctl stop_service appspawn-x >/dev/null 2>&1 || true"
sleep 2
D "set -e; umount /system/lib64/libwestlake_thread_guard_registry.so 2>/dev/null || true; umount /system/etc/sandbox/appdata-sandbox.json 2>/dev/null || true; umount /system/bin/appspawn-x 2>/dev/null || true; umount /system/lib64/appspawn/libwestlake_android_child.z.so 2>/dev/null || true; umount /system/android/lib64/liblzma.so 2>/dev/null || true; umount $ROUTE_TARGET 2>/dev/null || true; umount /system/android 2>/dev/null || true; mkdir -p /system/android /system/lib64/appspawn $ROUTE_TARGET /system/etc/sandbox; touch /system/bin/appspawn-x /system/lib64/appspawn/libwestlake_android_child.z.so /system/etc/sandbox/appdata-sandbox.json /system/lib64/libwestlake_thread_guard_registry.so; mount --bind $REMOTE_ANDROID /system/android; mount --bind $REMOTE_ROUTE $ROUTE_TARGET; mount --bind $REMOTE_ROUTE/liblzma.so /system/android/lib64/liblzma.so; mount --bind $REMOTE_RUNTIME/libwestlake_android_child.z.so /system/lib64/appspawn/libwestlake_android_child.z.so; mount --bind $REMOTE_RUNTIME/appspawn-x /system/bin/appspawn-x; mount --bind $REMOTE_RUNTIME/appdata-sandbox.json /system/etc/sandbox/appdata-sandbox.json; mount --bind $REMOTE_ROUTE/libwestlake_thread_guard_registry.so /system/lib64/libwestlake_thread_guard_registry.so"

D "set -e; find /system/android -type d -exec chmod 0755 {} \;; find /system/android -exec chcon u:object_r:system_file:s0 {} \;; find /system/android/lib64 -exec chcon u:object_r:system_lib_file:s0 {} \;; find $ROUTE_TARGET -exec chcon u:object_r:system_lib_file:s0 {} \;; chmod 0755 /system/bin/appspawn-x /system/lib64/appspawn/libwestlake_android_child.z.so; chmod 0644 /system/etc/sandbox/appdata-sandbox.json /system/lib64/libwestlake_thread_guard_registry.so /system/android/lib64/liblzma.so; chcon u:object_r:appspawn_exec:s0 /system/bin/appspawn-x; chcon u:object_r:system_lib_file:s0 /system/lib64/appspawn/libwestlake_android_child.z.so /system/lib64/libwestlake_thread_guard_registry.so /system/android/lib64/liblzma.so; chcon u:object_r:system_etc_file:s0 /system/etc/sandbox/appdata-sandbox.json; if [ -f /system/android/framework/arm64/boot.art ] && [ ! -e /system/android/framework/boot.art ]; then ln -sf arm64/boot.art /system/android/framework/boot.art; fi; for f in /system/android/framework/arm64/boot*.art /system/android/framework/arm64/boot*.oat /system/android/framework/arm64/boot*.vdex; do chcon u:object_r:system_lib_file:s0 \$f; done; chcon u:object_r:system_fonts_file:s0 /system/android/etc/fonts.xml 2>/dev/null || true; cp /system/android/etc/fonts.xml /system/etc/fonts.xml 2>/dev/null || true; chcon u:object_r:system_fonts_file:s0 /system/etc/fonts.xml 2>/dev/null || true; ln -sf /lib/ld-musl-aarch64.so.1 /system/lib/libc_musl.so; chcon -h u:object_r:system_lib_file:s0 /system/lib/libc_musl.so 2>/dev/null || true"

[ "$(device_hash /system/bin/appspawn-x)" = "$APPSPAWN_SHA" ] || die "appspawn-x bind 失败"
[ "$(device_hash /system/lib64/appspawn/libwestlake_android_child.z.so)" = "$CHILD_SHA" ] || die "child so bind 失败"
[ "$(device_hash "$ROUTE_TARGET/libwestlake_android_runtime_provider.so")" = "$PROVIDER_SHA" ] || die "provider bind 失败"
[ "$(device_hash /system/android/lib64/liboh_android_runtime.so)" = "$RUNTIME_SHA" ] || die "runtime bind 失败"
[ "$(device_hash /system/etc/sandbox/appdata-sandbox.json)" = "$SANDBOX_SHA" ] || die "sandbox bind 失败"
[ "$(device_hash /system/lib64/libwestlake_thread_guard_registry.so)" = "$ROUTE_TGR_SHA" ] || die "TGR bind 失败"
[ "$(device_hash /system/android/lib64/liblzma.so)" = "$LZMA_SHA" ] || die "liblzma bind 失败"
[ "$(D "grep -F ' $ROUTE_TARGET ' /proc/self/mountinfo | wc -l" | tr -d ' ')" = "1" ] || die "route generation mount 不对"
[ "$(D "grep -F ' /system/lib64/westlake/route-a ' /proc/self/mountinfo | wc -l" | tr -d ' ')" = "0" ] || die "禁止覆盖整个 route-a 父目录"
[ "$(D "grep -c ' /pr03-74e6-portable/' /proc/self/mountinfo" | tr -d ' ')" = "7" ] || die "PR03 bind 数量不是精确 7 个"
D "set -e; grep -F ' /system/android ' /proc/self/mountinfo | grep -q '/pr03-74e6-portable/android '; grep -F ' $ROUTE_TARGET ' /proc/self/mountinfo | grep -q '/pr03-74e6-portable/route '; grep -F ' /system/android/lib64/liblzma.so ' /proc/self/mountinfo | grep -q '/pr03-74e6-portable/route/liblzma.so '; grep -F ' /system/lib64/appspawn/libwestlake_android_child.z.so ' /proc/self/mountinfo | grep -q '/pr03-74e6-portable/runtime/libwestlake_android_child.z.so '; grep -F ' /system/bin/appspawn-x ' /proc/self/mountinfo | grep -q '/pr03-74e6-portable/runtime/appspawn-x '; grep -F ' /system/etc/sandbox/appdata-sandbox.json ' /proc/self/mountinfo | grep -q '/pr03-74e6-portable/runtime/appdata-sandbox.json '; grep -F ' /system/lib64/libwestlake_thread_guard_registry.so ' /proc/self/mountinfo | grep -q '/pr03-74e6-portable/route/libwestlake_thread_guard_registry.so '" || die "7 个 bind 的 source/target 对应关系不对"
[ "$(D "stat -c '%a:%u:%g:%C' /system/android" | tr -d ' ')" = "755:0:0:u:object_r:system_file:s0" ] || die "Android root mode/label 不对"
[ "$(D "stat -c '%a:%u:%g:%C' $ROUTE_TARGET" | tr -d ' ')" = "755:0:0:u:object_r:system_lib_file:s0" ] || die "route 目录 mode/label 不对"
[ "$(D "stat -c '%a:%u:%g:%C' /system/android/lib64/liblzma.so" | tr -d ' ')" = "644:0:0:u:object_r:system_lib_file:s0" ] || die "liblzma mode/label 不对"
[ "$(D "stat -c '%a:%u:%g:%C' /system/bin/appspawn-x" | tr -d ' ')" = "755:0:0:u:object_r:appspawn_exec:s0" ] || die "appspawn-x mode/label 不对"
[ "$(D "stat -c '%a:%u:%g:%C' /system/lib64/appspawn/libwestlake_android_child.z.so" | tr -d ' ')" = "755:0:0:u:object_r:system_lib_file:s0" ] || die "child so mode/label 不对"
[ "$(D "stat -c '%a:%u:%g:%C' /system/etc/sandbox/appdata-sandbox.json" | tr -d ' ')" = "644:0:0:u:object_r:system_etc_file:s0" ] || die "sandbox mode/label 不对"
[ "$(D "stat -c '%a:%u:%g:%C' /system/lib64/libwestlake_thread_guard_registry.so" | tr -d ' ')" = "644:0:0:u:object_r:system_lib_file:s0" ] || die "TGR mode/label 不对"
[ "$(D "stat -c '%a:%u:%g:%C' /system/android/framework/framework.jar" | tr -d ' ')" = "644:0:0:u:object_r:system_file:s0" ] || die "framework.jar mode/label 不对"

step "设置参数、唤醒并启动 appspawn-x"
D "set -e; param set persist.sys.abilityms.support_anco_app true; param set persist.sys.abilityms.timeout_unit_time_ratio 20; param set persist.sys.prefork.enable false; param set ro.product.cpu.abilist arm64-v8a >/dev/null 2>&1 || true; param set ro.product.cpu.abilist64 arm64-v8a >/dev/null 2>&1 || true; chmod 0666 /dev/mali0; chcon u:object_r:dev_mali:s0 /dev/mali0; power-shell setmode 602; power-shell timeout -o 86400000; power-shell wakeup; power-shell display -o 230; hilog -r >/dev/null 2>&1 || true; sync"
[ "$(D "param get persist.sys.abilityms.support_anco_app" | tr -d ' ')" = "true" ] || die "support_anco_app 参数未生效"
[ "$(D "param get persist.sys.abilityms.timeout_unit_time_ratio" | tr -d ' ')" = "20" ] || die "timeout ratio 参数未生效"
[ "$(D "param get persist.sys.prefork.enable" | tr -d ' ')" = "false" ] || die "prefork 参数未生效"
[ "$(D "param get ro.product.cpu.abilist" | tr -d ' ')" = "arm64-v8a" ] || die "abilist 参数未生效"
[ "$(D "param get ro.product.cpu.abilist64" | tr -d ' ')" = "arm64-v8a" ] || die "abilist64 参数未生效"
[ "$(D "stat -c '%a:%C' /dev/mali0" | tr -d ' ')" = "666:u:object_r:dev_mali:s0" ] || die "Mali mode/label 不对"
POWER_READBACK="$(D "power-shell dump -s | head -n 6")"
printf '%s\n' "$POWER_READBACK" | grep -q "Current State: AWAKE" || die "屏幕没有保持 AWAKE"
printf '%s\n' "$POWER_READBACK" | grep -q "OverrideTimeout=86400000ms" || die "屏幕超时覆盖未生效"
[ -z "$(appspawn_pids)" ] || die "启动 token 前已有 appspawn-x parent"
[ -z "$(app_child_lines)" ] || die "启动 token 前已有 HelloWorld child"
D "begetctl start_service appspawn-x"

PARENT_PID=""
LAST_PID=""
STABLE_COUNT=0
for i in $(seq 1 20); do
  sleep 1
  PIDS="$(appspawn_pids)"
  PID_COUNT="$(printf '%s\n' "$PIDS" | sed '/^$/d' | wc -l | tr -d ' ')"
  PARENT_PID="$(printf '%s\n' "$PIDS" | sed '/^$/d' | head -n 1)"
  SOCKET_INFO="$(D "stat -c '%a:%u:%g:%C' /dev/unix/socket/AppSpawnX 2>/dev/null" | tr -d ' ' || true)"
  if [ "$PID_COUNT" = "1" ] && [ -n "$PARENT_PID" ] && [ "$PARENT_PID" = "$LAST_PID" ] && \
     [ "$SOCKET_INFO" = "666:0:6005:u:object_r:appspawn_socket:s0" ] && \
     [ -z "$(app_child_lines)" ] && parent_maps_ready "$PARENT_PID"; then
    STABLE_COUNT=$((STABLE_COUNT + 1))
  else
    STABLE_COUNT=0
  fi
  LAST_PID="$PARENT_PID"
  [ "$STABLE_COUNT" -ge 2 ] && break
done
[ "$STABLE_COUNT" -ge 2 ] || die "appspawn-x 没有稳定到 0666 settle 状态"
[ "$(device_hash "/proc/$PARENT_PID/exe")" = "$APPSPAWN_SHA" ] || die "运行中的 appspawn-x 不是 PR03 二进制"

D "set -e; chmod 0660 /dev/unix/socket/AppSpawnX; chown 0:6005 /dev/unix/socket/AppSpawnX; chcon u:object_r:appspawn_socket:s0 /dev/unix/socket/AppSpawnX"
for i in 1 2 3 4 5; do
  sleep 1
  PIDS="$(appspawn_pids)"
  [ "$(printf '%s\n' "$PIDS" | sed '/^$/d' | wc -l | tr -d ' ')" = "1" ] || die "appspawn-x heartbeat $i 时不是 sole parent"
  [ "$(printf '%s\n' "$PIDS" | sed '/^$/d' | head -n 1)" = "$PARENT_PID" ] || die "appspawn-x heartbeat $i 时 PID 变化"
  [ "$(D "stat -c '%a:%u:%g:%C' /dev/unix/socket/AppSpawnX" | tr -d ' ')" = "660:0:6005:u:object_r:appspawn_socket:s0" ] || die "socket heartbeat $i 不稳定"
  [ -z "$(app_child_lines)" ] || die "appspawn-x heartbeat $i 前已有 child"
  parent_maps_ready "$PARENT_PID" || die "appspawn-x heartbeat $i 的 key maps 不完整"
done
[ "$(device_hash /system/lib64/libwestlake_thread_guard_registry.so)" = "$ROUTE_TGR_SHA" ] || die "heartbeat 后 route-side 674d TGR 漂移"

step "唯一一次冷启动 HelloWorld"
D "set -e; power-shell setmode 602; power-shell timeout -o 86400000; power-shell wakeup; power-shell display -o 230; uinput -T -m 600 1500 600 600 500 >/dev/null 2>&1 || true; hilog -r >/dev/null 2>&1 || true"
sleep 1
LAUNCH_TOKEN="PR03-${BOARD:0:8}-${RUN_ID}-one-shot-001"
echo "launch_token=$LAUNCH_TOKEN"
AA_RESULT="$(D "aa start -a $ABILITY -b $PACKAGE -W")"
echo "$AA_RESULT"
printf '%s\n' "$AA_RESULT" | grep -q "start ability successfully" || die "aa start 失败"

CHILD_PID=""
for i in $(seq 1 20); do
  CHILD_LINE="$(D "ps -ef | grep '^$APP_UID ' | grep 'appspawn-x --socket-name AppSpawnX' | grep -v grep | head -n 1" || true)"
  if [ -n "$CHILD_LINE" ]; then
    set -- $CHILD_LINE
    if [ "${3:-}" = "$PARENT_PID" ]; then
      CHILD_PID="${2:-}"
      break
    fi
  fi
  sleep 1
done
if [ -z "$CHILD_PID" ]; then
  D "hilog -x | grep -E '$PACKAGE|WLCGATE|LOAD_ERROR|VALIDATED_COUNT|NotifyStartProcessFailed' | tail -n 500" > "$OUT_DIR/failure-hilog.txt" || true
  die "应用子进程没有稳定生成；日志：$OUT_DIR/failure-hilog.txt"
fi
echo "应用子进程 PID=$CHILD_PID PPID=$PARENT_PID UID=${APP_UID}。"

VIS_LOG=""
for i in $(seq 1 12); do
  D "power-shell setmode 602 >/dev/null 2>&1; power-shell timeout -o 86400000 >/dev/null 2>&1; power-shell wakeup >/dev/null 2>&1" || true
  sleep 1
  VIS_LOG="$(D "hilog -x | grep -E '^[^ ]+ +[^ ]+ +$CHILD_PID +' | grep -E 'mVisibleFromServer=|text=.Hello World|WLCGATE|VALIDATED_COUNT|LOAD_ERROR' | tail -n 600" || true)"
  if printf '%s\n' "$VIS_LOG" | grep -q "mVisibleFromServer=true" && printf '%s\n' "$VIS_LOG" | grep -q "Hello World"; then
    break
  fi
done
printf '%s\n' "$VIS_LOG" > "$OUT_DIR/visibility.txt"
printf '%s\n' "$VIS_LOG" | grep -q "mVisibleFromServer=true" || die "应用已运行但窗口仍未可见"
printf '%s\n' "$VIS_LOG" | grep -q "Hello World" || die "窗口可见，但日志未读到 HelloWorld 界面树"

step "截图确认"
D "snapshot_display -f /data/local/tmp/pr03-helloworld-success.jpeg" >/dev/null
H file recv /data/local/tmp/pr03-helloworld-success.jpeg "$OUT_DIR/HelloWorld.jpeg" >/dev/null
[ -s "$OUT_DIR/HelloWorld.jpeg" ] || die "截图失败"
SCREENSHOT_BYTES="$(wc -c < "$OUT_DIR/HelloWorld.jpeg" | tr -d ' ')"
[ "$SCREENSHOT_BYTES" -ge 50000 ] || die "截图像素量异常（${SCREENSHOT_BYTES}B，可能仍是黑/白占位屏）"
"$FFMPEG_BIN" -hide_banner -loglevel error -i "$OUT_DIR/HelloWorld.jpeg" \
  -vf signalstats,metadata=print:file="$OUT_DIR/screenshot-signalstats.txt" -f null - || die "截图解码失败"
YMIN="$(sed -n 's/^lavfi.signalstats.YMIN=//p' "$OUT_DIR/screenshot-signalstats.txt" | head -n 1)"
YMAX="$(sed -n 's/^lavfi.signalstats.YMAX=//p' "$OUT_DIR/screenshot-signalstats.txt" | head -n 1)"
[ -n "$YMIN" ] && [ -n "$YMAX" ] || die "取不到截图像素统计"
[ "$YMIN" -le 20 ] && [ "$YMAX" -ge 240 ] || die "截图缺少预期明暗像素（YMIN=$YMIN YMAX=${YMAX}），拒绝白屏/黑屏"

step "点击 CHANGE COLOR，确认触摸回到主 Looper"
D "power-shell wakeup; uinput -T -m 600 1500 600 300 500 >/dev/null 2>&1 || true"
sleep 1
D "hilog -r >/dev/null 2>&1 || true; uinput -T -c 600 500 100"
sleep 2
TOUCH_LOG="$(D "hilog -x | grep -E '^[^ ]+ +[^ ]+ +$CHILD_PID +' | grep -E 'Color changed to: RED|AndroidRuntimeException|Animators may only be run on Looper threads' | tail -n 200" || true)"
printf '%s\n' "$TOUCH_LOG" > "$OUT_DIR/touch.txt"
printf '%s\n' "$TOUCH_LOG" | grep -q "Color changed to: RED" || die "触摸没有触发变色"
if printf '%s\n' "$TOUCH_LOG" | grep -qE "AndroidRuntimeException|Animators may only be run on Looper threads"; then
  die "触摸仍在非 Looper 线程执行"
fi
[ "$(printf '%s\n' "$(appspawn_pids)" | sed '/^$/d' | wc -l | tr -d ' ')" = "2" ] || die "触摸后 parent/child 数量不对"
D "snapshot_display -f /data/local/tmp/pr03-helloworld-touch-red.jpeg" >/dev/null
H file recv /data/local/tmp/pr03-helloworld-touch-red.jpeg "$OUT_DIR/HelloWorld-touch-red.jpeg" >/dev/null
[ "$(wc -c < "$OUT_DIR/HelloWorld-touch-red.jpeg" | tr -d ' ')" -ge 50000 ] || die "触摸后截图异常"

echo
echo "成功：HelloWorld 已在 $BOARD 上屏，CHANGE COLOR 点击后变为 RED。"
echo "launch token：$LAUNCH_TOKEN"
echo "parent/child：$PARENT_PID/$CHILD_PID"
echo "截图：$OUT_DIR/HelloWorld.jpeg"
echo "触摸截图：$OUT_DIR/HelloWorld-touch-red.jpeg"
echo "完整日志：$OUT_DIR/restore.log"
echo "本地载荷：$PAYLOAD_ROOT"
echo "重启恢复：已安装；以后每次重启后打开 HelloWorld 都会自动恢复运行闭包"
