#!/bin/sh
set -eu
action=${1:-preview}
stage=${2:?private root-owned stage}
boot=${3:?current boot pin}
apply_sha=${4:?apply SQL SHA}
rollback_sha=${5:?rollback SQL SHA}
before_sha=${6:?before verifier SHA}
after_sha=${7:?after verifier SHA}
database=/data/app/el1/100/database/com.ohos.sceneboard/phone_sceneboard/rdb/Launcher.db
case "$action" in preview|apply|rollback) ;; *) exit 2 ;; esac
case "$stage" in /data/local/tmp/demo-icons-*) ;; *) exit 2 ;; esac
name=${stage##*/}
case "$name" in *[!a-zA-Z0-9-]*|'') exit 2 ;; esac
test "$(id -u)" = 0
test "$(cat /proc/sys/kernel/random/boot_id)" = "$boot"
test -d "$stage" && test ! -L "$stage"
test "$(stat -c '%u:%g:%a' "$stage")" = '0:0:700'
test -f "$database" && test ! -L "$database"
pin() {
    test -f "$1" && test ! -L "$1" || return 2
    value=$(sha256sum "$1") || return 2
    set -- $value "$2"
    test "$1" = "$3"
}
pin "$stage/apply.sql" "$apply_sha"
pin "$stage/rollback.sql" "$rollback_sha"
pin "$stage/verify-before.sql" "$before_sha"
pin "$stage/verify-after.sql" "$after_sha"
verify() {
    /bin/sqlite3 -readonly -bail "$database" < "$stage/verify-$1.sql"
}
restore() {
    test "$(cat /proc/sys/kernel/random/boot_id)" = "$boot" || return 2
    if verify before > /dev/null 2>&1; then
        printf '%s\n' 'LAUNCHER_ROWS_ALREADY_ORIGINAL'
    elif verify after > /dev/null 2>&1; then
        /bin/sqlite3 -bail "$database" < "$stage/rollback.sql" || return 2
        verify before || return 2
        printf '%s\n' 'LAUNCHER_17_ROWS_ROLLED_BACK'
    else
        printf '%s\n' 'ROLLBACK_REFUSED_FOREIGN_LAUNCHER_ROWS' >&2
        return 2
    fi
}
if [ "$action" = preview ]; then
    verify before
    printf '%s\n' 'PREVIEW_17_ICON_ROWS_NO_MAIN_DB_WRITES'
    exit 0
fi
if [ "$action" = rollback ]; then restore; exit; fi
armed=0
finish() {
    status=$?
    trap - EXIT HUP INT TERM
    if [ "$status" != 0 ] && [ "$armed" = 1 ]; then
        if ! restore; then printf '%s\n' 'ROLLBACK_INCOMPLETE_KEEP_LOCK_AND_STAGE' >&2; exit 97; fi
    fi
    exit "$status"
}
trap finish EXIT
trap 'exit 130' HUP INT TERM
verify before
armed=1
/bin/sqlite3 -bail "$database" < "$stage/apply.sql"
verify after
test "$(cat /proc/sys/kernel/random/boot_id)" = "$boot"
armed=0
printf '%s\n' 'LAUNCHER_17_COMBINE_PIC_ROWS_APPLIED_FRESH_MEMORY_RELOAD_AND_UI_REVIEW_REQUIRED'
