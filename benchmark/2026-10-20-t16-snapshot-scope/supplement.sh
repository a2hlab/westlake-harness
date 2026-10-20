set -eu
before=$(cat /proc/sys/kernel/random/boot_id)
printf "T16_SUPPLEMENT_BOOT %s\n" "$before"
test "$before" = "$1"
printf 'T16_TARGET 0 %s\n' /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/real-start-parent-bounded.sh
test -f /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/real-start-parent-bounded.sh; test ! -L /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/real-start-parent-bounded.sh
ls -Zd /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/real-start-parent-bounded.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/real-start-parent-bounded.sh
stat -c %d:%i:%a:%u:%g:%s /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/real-start-parent-bounded.sh
printf 'T16_TARGET 1 %s\n' /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/entry.sh
test -f /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/entry.sh; test ! -L /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/entry.sh
ls -Zd /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/entry.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/entry.sh
stat -c %d:%i:%a:%u:%g:%s /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/entry.sh
printf 'T16_TARGET 2 %s\n' /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/launch-common.sh
test -f /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/launch-common.sh; test ! -L /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/launch-common.sh
ls -Zd /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/launch-common.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/launch-common.sh
stat -c %d:%i:%a:%u:%g:%s /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/launch-common.sh
printf 'T16_TARGET 3 %s\n' /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/real-spawn.sh
test -f /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/real-spawn.sh; test ! -L /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/real-spawn.sh
ls -Zd /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/real-spawn.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/real-spawn.sh
stat -c %d:%i:%a:%u:%g:%s /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/real-spawn.sh
printf 'T16_TARGET 4 %s\n' /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/real-start-parent.sh
test -f /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/real-start-parent.sh; test ! -L /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/real-start-parent.sh
ls -Zd /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/real-start-parent.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/real-start-parent.sh
stat -c %d:%i:%a:%u:%g:%s /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/real-start-parent.sh
printf 'T16_TARGET 5 %s\n' /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/route-b-owner.sh
test -f /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/route-b-owner.sh; test ! -L /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/route-b-owner.sh
ls -Zd /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/route-b-owner.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/route-b-owner.sh
stat -c %d:%i:%a:%u:%g:%s /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/route-b-owner.sh
printf 'T16_TARGET 6 %s\n' /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/spawn.sh
test -f /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/spawn.sh; test ! -L /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/spawn.sh
ls -Zd /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/spawn.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/spawn.sh
stat -c %d:%i:%a:%u:%g:%s /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/spawn.sh
printf 'T16_TARGET 7 %s\n' /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/start-parent.sh
test -f /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/start-parent.sh; test ! -L /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/start-parent.sh
ls -Zd /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/start-parent.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/start-parent.sh
stat -c %d:%i:%a:%u:%g:%s /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/start-parent.sh
printf 'T16_TARGET 8 %s\n' /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/watchdog.sh
test -f /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/watchdog.sh; test ! -L /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/watchdog.sh
ls -Zd /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/watchdog.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/watchdog.sh
stat -c %d:%i:%a:%u:%g:%s /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/watchdog.sh
printf 'T16_TARGET 9 %s\n' /data/westlake-demo/toutiao/scripts/watchdog.sh
test -f /data/westlake-demo/toutiao/scripts/watchdog.sh; test ! -L /data/westlake-demo/toutiao/scripts/watchdog.sh
ls -Zd /data/westlake-demo/toutiao/scripts/watchdog.sh
sha256sum /data/westlake-demo/toutiao/scripts/watchdog.sh
stat -c %d:%i:%a:%u:%g:%s /data/westlake-demo/toutiao/scripts/watchdog.sh
printf 'T16_TARGET 10 %s\n' /data/westlake-demo/toutiao/scripts/route-b-owner.sh
test -f /data/westlake-demo/toutiao/scripts/route-b-owner.sh; test ! -L /data/westlake-demo/toutiao/scripts/route-b-owner.sh
ls -Zd /data/westlake-demo/toutiao/scripts/route-b-owner.sh
sha256sum /data/westlake-demo/toutiao/scripts/route-b-owner.sh
stat -c %d:%i:%a:%u:%g:%s /data/westlake-demo/toutiao/scripts/route-b-owner.sh
printf 'T16_TARGET 11 %s\n' /data/local/tmp/operator45/selfheal48/watchdog.sh
test -f /data/local/tmp/operator45/selfheal48/watchdog.sh; test ! -L /data/local/tmp/operator45/selfheal48/watchdog.sh
ls -Zd /data/local/tmp/operator45/selfheal48/watchdog.sh
sha256sum /data/local/tmp/operator45/selfheal48/watchdog.sh
stat -c %d:%i:%a:%u:%g:%s /data/local/tmp/operator45/selfheal48/watchdog.sh
printf 'T16_TARGET 12 %s\n' /data/local/tmp/operator45/selfheal48/route-b-owner.sh
test -f /data/local/tmp/operator45/selfheal48/route-b-owner.sh; test ! -L /data/local/tmp/operator45/selfheal48/route-b-owner.sh
ls -Zd /data/local/tmp/operator45/selfheal48/route-b-owner.sh
sha256sum /data/local/tmp/operator45/selfheal48/route-b-owner.sh
stat -c %d:%i:%a:%u:%g:%s /data/local/tmp/operator45/selfheal48/route-b-owner.sh
printf 'T16_TARGET 13 %s\n' /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/screen-gate
test -f /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/screen-gate; test ! -L /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/screen-gate
ls -Zd /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/screen-gate
sha256sum /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/screen-gate
stat -c %d:%i:%a:%u:%g:%s /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/screen-gate
printf 'T16_TARGET 14 %s\n' /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/decoder-probe.jpeg
test -f /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/decoder-probe.jpeg; test ! -L /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/decoder-probe.jpeg
ls -Zd /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/decoder-probe.jpeg
sha256sum /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/decoder-probe.jpeg
stat -c %d:%i:%a:%u:%g:%s /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/decoder-probe.jpeg
printf 'T16_TARGET 15 %s\n' /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/boot-entry.sh
test -f /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/boot-entry.sh; test ! -L /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/boot-entry.sh
ls -Zd /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/boot-entry.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/boot-entry.sh
stat -c %d:%i:%a:%u:%g:%s /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/boot-entry.sh
printf 'T16_TARGET 16 %s\n' /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/config-common.sh
test -f /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/config-common.sh; test ! -L /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/config-common.sh
ls -Zd /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/config-common.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/config-common.sh
stat -c %d:%i:%a:%u:%g:%s /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/config-common.sh
printf 'T16_TARGET 17 %s\n' /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/members.tsv
test -f /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/members.tsv; test ! -L /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/members.tsv
ls -Zd /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/members.tsv
sha256sum /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/members.tsv
stat -c %d:%i:%a:%u:%g:%s /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/members.tsv
printf 'T16_TARGET 18 %s\n' /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/startup.env
test -f /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/startup.env; test ! -L /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/startup.env
ls -Zd /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/startup.env
sha256sum /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/startup.env
stat -c %d:%i:%a:%u:%g:%s /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/startup.env
printf 'T16_TARGET 19 %s\n' /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/startup.expected.sha256
test -f /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/startup.expected.sha256; test ! -L /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/startup.expected.sha256
ls -Zd /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/startup.expected.sha256
sha256sum /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/startup.expected.sha256
stat -c %d:%i:%a:%u:%g:%s /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/startup.expected.sha256
printf 'T16_TARGET 20 %s\n' /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/recovery.cfg
test -f /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/recovery.cfg; test ! -L /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/recovery.cfg
ls -Zd /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/recovery.cfg
sha256sum /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/recovery.cfg
stat -c %d:%i:%a:%u:%g:%s /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/recovery.cfg
printf 'T16_TARGET 21 %s\n' /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/rollback-inert.cfg
test -f /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/rollback-inert.cfg; test ! -L /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/rollback-inert.cfg
ls -Zd /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/rollback-inert.cfg
sha256sum /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/rollback-inert.cfg
stat -c %d:%i:%a:%u:%g:%s /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/rollback-inert.cfg
printf 'T16_TARGET 22 %s\n' /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/readiness-probe.sh
test -f /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/readiness-probe.sh; test ! -L /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/readiness-probe.sh
ls -Zd /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/readiness-probe.sh
sha256sum /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/readiness-probe.sh
stat -c %d:%i:%a:%u:%g:%s /data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/readiness-probe.sh
printf 'T16_TARGET 23 %s\n' /data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/request.bin
test -f /data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/request.bin; test ! -L /data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/request.bin
ls -Zd /data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/request.bin
sha256sum /data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/request.bin
stat -c %d:%i:%a:%u:%g:%s /data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/request.bin
printf 'T16_TARGET 24 %s\n' /data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/source_app_namespace
test -f /data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/source_app_namespace; test ! -L /data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/source_app_namespace
ls -Zd /data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/source_app_namespace
sha256sum /data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/source_app_namespace
stat -c %d:%i:%a:%u:%g:%s /data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/source_app_namespace
printf 'T16_TARGET 25 %s\n' /data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/host_spawn
test -f /data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/host_spawn; test ! -L /data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/host_spawn
ls -Zd /data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/host_spawn
sha256sum /data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/host_spawn
stat -c %d:%i:%a:%u:%g:%s /data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/host_spawn
printf 'T16_COMPAT_STATE\n'
test ! -L /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so
if test -e /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so; then test -f /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so; ls -Zd /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so; sha256sum /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so; stat -c %d:%i:%a:%u:%g:%s /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/libopensles_android_compat.so; else printf "ABSENT\n"; fi
test "$(cat /proc/sys/kernel/random/boot_id)" = "$before"
printf 'T16_SUPPLEMENT_COMPLETE\n'
