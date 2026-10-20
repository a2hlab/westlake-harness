test "$(cat /proc/sys/kernel/random/boot_id)" = 11111111-2222-3333-4444-555555555555
row=$(cat /proc/4992/stat) || exit 81
rest=${row##*) }; set -- $rest
test "${20}" = 5694 && test "$1" != Z && test "$1" != X && test "$2" = 1 || exit 81
u=$(sed -n 's/^Uid:[[:space:]]*//p' /proc/4992/status) || exit 81; set -- $u
test "$1:$2:$3:$4" = 0:0:0:0 || exit 81
test "$(sed -n 's/^TracerPid:[[:space:]]*//p' /proc/4992/status)" = 0 || exit 81
test "$(readlink /proc/4992/ns/mnt)" = 'mnt:[4026533005]' || exit 81
h=$(sha256sum /proc/4992/exe) || exit 81; test "${h%% *}" = a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c || exit 81
printf 'IDENTITY 4992 '; cat /proc/4992/stat || exit 81
test "$(readlink /proc/1/ns/mnt)" = 'mnt:[4026531841]'
sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh
sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/liboh_adapter_bridge.so
sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libmffmpeg.so
sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libttmplayer.so
sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/webview-t-lib/libwebview_bionic_shim.so
test ! -e /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so || exit 81
test ! -L /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so || exit 81
test ! -e /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libopensles_android_compat.so || exit 81
test ! -L /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/libopensles_android_compat.so || exit 81
echo PHYSICAL_COMPAT_ABSENT
sha256sum /proc/4992/root/data/local/tmp/asx/run.sh
sha256sum /proc/4992/root/data/local/tmp/asx/liboh_adapter_bridge.so
sha256sum /proc/4992/root/data/local/tmp/asx/lib/arm64-v8a/libmffmpeg.so
sha256sum /proc/4992/root/data/local/tmp/asx/lib/arm64-v8a/libttmplayer.so
sha256sum /proc/4992/root/data/local/tmp/asx/webview-t-lib/libwebview_bionic_shim.so
test ! -e /proc/4992/root/data/local/tmp/asx/libopensles_android_compat.so || exit 81
test ! -L /proc/4992/root/data/local/tmp/asx/libopensles_android_compat.so || exit 81
test ! -e /proc/4992/root/data/local/tmp/asx/lib/arm64-v8a/libopensles_android_compat.so || exit 81
test ! -L /proc/4992/root/data/local/tmp/asx/lib/arm64-v8a/libopensles_android_compat.so || exit 81
echo PRIVATE_COMPAT_ABSENT
sha256sum /data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r2/boot-entry.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r2/config-common.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r2/entry.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r2/exit-verdict.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r2/launch-common.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r2/members.tsv
sha256sum /data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r2/readiness-probe.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r2/real-spawn.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r2/real-start-parent-bounded.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r2/real-start-parent.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r2/reentry-common.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r2/reentry-seams.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r2/route-b-owner.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r2/spawn.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r2/start-parent.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r2/startup.env
sha256sum /data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r2/startup.expected.sha256
sha256sum /data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r2/watchdog.sh
sha256sum /system/etc/init/01_westlake_u13_toutiao.cfg
sha256sum /data/app/el1/bundle/public/org.westlake.imehost/entry.hap
envrows=$(strings /proc/4992/environ)
wids=$(printf '%s\n' "$envrows" | sed -n 's/^WL_PARENT_ID=//p')
printf 'WL_PARENT_ID=%s\n' "$wids"
test "$wids" = 30
power-shell dump -s
set +e
debug=$(param get debug.ttplayer.log.enable 2>&1); debug_rc=$?
set -e
printf 'DEBUG_PROCESS_RC=%s\n%s\n' "$debug_rc" "$debug"
test "$(cat /proc/sys/kernel/random/boot_id)" = 11111111-2222-3333-4444-555555555555
row=$(cat /proc/4992/stat) || exit 81
rest=${row##*) }; set -- $rest
test "${20}" = 5694 && test "$1" != Z && test "$1" != X && test "$2" = 1 || exit 81
u=$(sed -n 's/^Uid:[[:space:]]*//p' /proc/4992/status) || exit 81; set -- $u
test "$1:$2:$3:$4" = 0:0:0:0 || exit 81
test "$(sed -n 's/^TracerPid:[[:space:]]*//p' /proc/4992/status)" = 0 || exit 81
test "$(readlink /proc/4992/ns/mnt)" = 'mnt:[4026533005]' || exit 81
h=$(sha256sum /proc/4992/exe) || exit 81; test "${h%% *}" = a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c || exit 81
printf 'IDENTITY 4992 '; cat /proc/4992/stat || exit 81
test "$(readlink /proc/1/ns/mnt)" = 'mnt:[4026531841]'
echo RESTORE_IDENTITY_MATCH
