#!/bin/sh
set -eu
action=${1:-preview}
stage=${2:?root supplies private staged directory}
expected_boot=${3:?root supplies pinned current boot}
apply_sha=${4:?apply SQL SHA}
rollback_sha=${5:?rollback SQL SHA}
before_sha=${6:?before verifier SQL SHA}
after_sha=${7:?after verifier SQL SHA}
database=/data/service/el1/public/bms/bundle_resources/bundleResource.db
original=53ce1f45f81705a84f05aa0d6956a64180d1fd6984a79b7a784f3931a311bd6f
case "$action" in preview|apply|rollback) ;; *) exit 2 ;; esac
case "$stage" in /data/local/tmp/demo-icons-*) ;; *) exit 2 ;; esac
name=${stage##*/}
case "$name" in *[!a-zA-Z0-9-]*|'') exit 2 ;; esac
test "$(id -u)" = 0
test "$(cat /proc/sys/kernel/random/boot_id)" = "$expected_boot"
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

candidate_pin() {
    case "$1" in
        com.kaajjo.libresudoku) printf '%s' c5448a81acbda7f21b5ab47c4976eec7a2a8788151c4d970c68e273c4c922fdb ;;
        com.lcdcode.moodcairns) printf '%s' 8fa1a3aa4aa1f0605492cac07e5b5200cf82c6354738fe3af55758548fbe5c64 ;;
        com.paperknifeplus.app) printf '%s' 2a7b8085bd5761f1a043da9b4caac283154193d6650e6f2626878fd49836bcfa ;;
        com.groce.app) printf '%s' 9bcff83e0eacffe0dc7d3af2f1a99c4dd909070a6a107e8f061695df62f978da ;;
        org.fossify.calendar) printf '%s' fe44ba3eeaf4fafd1e1e130637f6e07b553c65cfb263bb94bc069a5fccdbe109 ;;
        *) return 2 ;;
    esac
}

metadata() {
    test -f "$1" && test ! -L "$1" || return 2
    test "$(stat -c '%u:%g:%a' "$1")" = '3060:3060:644' || return 2
    value=$(ls -dZ "$1") || return 2
    case "$value" in *u:object_r:data_app_el1_file:s0*) ;; *) return 2 ;; esac
}

replace() {
    package=$1
    target=/data/app/el1/bundle/public/$package/android/icon.png
    test ! -L "${target%/*}" && test ! -L "/data/app/el1/bundle/public/$package" || return 2
    metadata "$target" || return 2
    if pin "$target" "$3"; then return 0; fi
    pin "$target" "$2" || return 2
    source=$stage/after/$package.png
    if [ "$3" = "$original" ]; then source=$stage/before/$package.png; fi
    pin "$source" "$3" || return 2
    temporary=$target.$name
    (set -C; : > "$temporary") || return 2
    inode=$(stat -c '%d:%i' "$temporary") || return 2
    if ! (cat "$source" > "$temporary" && chown 3060:3060 "$temporary" && chmod 0644 "$temporary" && chcon u:object_r:data_app_el1_file:s0 "$temporary" && metadata "$temporary" && pin "$temporary" "$3" && pin "$target" "$2" && test "$(stat -c '%d:%i' "$temporary")" = "$inode" && mv "$temporary" "$target"); then
        if [ -f "$temporary" ] && [ ! -L "$temporary" ] && [ "$(stat -c '%d:%i' "$temporary")" = "$inode" ]; then rm "$temporary"; fi
        return 2
    fi
    pin "$target" "$3" || return 2
    metadata "$target"
}

for package in com.kaajjo.libresudoku com.lcdcode.moodcairns com.paperknifeplus.app com.groce.app org.fossify.calendar; do
    pin "$stage/before/$package.png" "$original"
    pin "$stage/after/$package.png" "$(candidate_pin "$package")"
done

verify_rows() {
    /bin/sqlite3 -readonly -bail "$database" < "$stage/verify-$1.sql"
}

restore() {
    test "$(cat /proc/sys/kernel/random/boot_id)" = "$expected_boot" || return 2
    if verify_rows before > /dev/null 2>&1; then
        :
    elif verify_rows after > /dev/null 2>&1; then
        /bin/sqlite3 -bail "$database" < "$stage/rollback.sql" || return 2
        verify_rows before || return 2
    else
        printf '%s\n' 'ROLLBACK_REFUSED_FOREIGN_RESOURCE_ROWS' >&2
        return 2
    fi
    for package in com.kaajjo.libresudoku com.lcdcode.moodcairns com.paperknifeplus.app com.groce.app org.fossify.calendar; do
        replace "$package" "$(candidate_pin "$package")" "$original" || return 2
    done
    printf '%s\n' 'ICON_ROLLBACK_COMPLETE_5_FILES_49_ROWS'
}

if [ "$action" = preview ]; then
    verify_rows before
    for package in com.kaajjo.libresudoku com.lcdcode.moodcairns com.paperknifeplus.app com.groce.app org.fossify.calendar; do
        target=/data/app/el1/bundle/public/$package/android/icon.png
        pin "$target" "$original"
        metadata "$target"
    done
    printf '%s\n' 'PREVIEW_PASS_NO_TARGET_WRITES_HAP_UNCHANGED'
    exit 0
fi

if [ "$action" = rollback ]; then restore; exit; fi
armed=0
finish() {
    status=$?
    trap - EXIT HUP INT TERM
    if [ "$status" != 0 ] && [ "$armed" = 1 ]; then
        if ! restore; then printf '%s\n' 'ROLLBACK_INCOMPLETE_KEEP_STAGE_AND_LOCK' >&2; exit 97; fi
    fi
    exit "$status"
}
trap finish EXIT
trap 'exit 130' HUP INT TERM
verify_rows before
armed=1
/bin/sqlite3 -bail "$database" < "$stage/apply.sql"
verify_rows after
for package in com.kaajjo.libresudoku com.lcdcode.moodcairns com.paperknifeplus.app com.groce.app org.fossify.calendar; do
    replace "$package" "$original" "$(candidate_pin "$package")"
done
test "$(cat /proc/sys/kernel/random/boot_id)" = "$expected_boot"
verify_rows after
armed=0
printf '%s\n' 'ICON_METADATA_APPLIED_5_FILES_49_ROWS_HAP_UNCHANGED_UI_REVIEW_REQUIRED'
