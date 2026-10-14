#!/bin/sh
set -eu
action=${1:-preview}
pid=${2:?current exact SceneBoard PID}
birth=${3:?current stat field22}
cmd_sha=${4:?current raw cmdline SHA}
boot=${5:?current boot pin}
case "$action" in preview|term) ;; *) exit 2 ;; esac
case "$pid:$birth" in *[!0-9:]*|:*) exit 2 ;; esac
test "$pid" -gt 1
test "$(id -u)" = 0
test "$(cat /proc/sys/kernel/random/boot_id)" = "$boot"
status=$(cat "/proc/$pid/status")
uid=
while IFS= read -r line; do
    case "$line" in Uid:*) set -- $line; uid=$2; test "$2:$3:$4:$5" = '20010018:20010018:20010018:20010018' ;; esac
done <<EOF
$status
EOF
test "$uid" = 20010018
stat_text=$(cat "/proc/$pid/stat")
tail=${stat_text##*) }
set -- $tail
shift 19
test "$1" = "$birth"
cmd=$(strings "/proc/$pid/cmdline")
IFS= read -r first <<EOF
$cmd
EOF
test "$first" = com.ohos.sceneboard
checksum=$(sha256sum "/proc/$pid/cmdline")
set -- $checksum
test "$1" = "$cmd_sha"
printf 'SCENEBOARD_GUARD_PASS pid=%s birth=%s uid=%s boot=%s\n' "$pid" "$birth" "$uid" "$boot"
if [ "$action" = preview ]; then
    printf '%s\n' 'PREVIEW_NO_SIGNAL'
    exit 0
fi
kill -TERM "$pid"
printf '%s\n' 'ONE_TERM_SENT_SCENEBOARD_ONLY_WAIT_FOR_NEW_PID_AND_ACTUAL_ICON_SCREENSHOTS'
