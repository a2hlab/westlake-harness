#!/system/bin/sh
set -eu
ACTION=$1
ROOT=$2
EXPECTED_BOOT=$3
ORIGINAL=2c9a5294a253acb57394cc79956a4b30182a7a0ecad570844c395b38d34d82e0
CANDIDATE=51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5
test "$(cat /proc/sys/kernel/random/boot_id)" = "$EXPECTED_BOOT"
case "$ROOT" in /data/local/tmp/spare-installer-[a-z0-9]*) ;; *) exit 20 ;; esac
case "$ROOT" in *..*|*[!a-zA-Z0-9/_-]*) exit 20 ;; esac
case "$ACTION" in backup|apply|rollback) ;; *) exit 21 ;; esac
hash_file() {
    sha256sum "$1" | { read -r digest rest; printf '%s' "$digest"; }
}
assert_ro() {
    FOUND=0
    while read -r dev point type options extra; do
        if test "$point" = /; then
            case ",$options," in *,ro,*) FOUND=1 ;; *) return 22 ;; esac
        fi
        case "$point" in /system|/system/lib64|/system/lib64/platformsdk|/system/lib64/libinstalls.z.so|/system/lib64/platformsdk/libinstalls.z.so) return 23 ;; esac
    done < /proc/mounts
    test "$FOUND" = 1
}
metadata() {
    stat -c '%u:%g:%a:%h' "$1"
    ls -Zd "$1"
}
assert_ro
for INDEX in 0 1; do
    if test "$INDEX" = 0; then TARGET=/system/lib64/libinstalls.z.so; else TARGET=/system/lib64/platformsdk/libinstalls.z.so; fi
    test -f "$TARGET" && test ! -L "$TARGET"
    metadata "$TARGET" > "$ROOT/meta-now-$INDEX.txt"
    cmp "$ROOT/meta-$INDEX.txt" "$ROOT/meta-now-$INDEX.txt"
    ACTUAL=$(hash_file "$TARGET")
    if test "$ACTION" = rollback; then
        test "$ACTUAL" = "$ORIGINAL" || test "$ACTUAL" = "$CANDIDATE"
    else
        test "$ACTUAL" = "$ORIGINAL"
    fi
done
if test "$ACTION" = backup; then
    test ! -e "$ROOT/backup"
    mkdir "$ROOT/backup"
    cp -p /system/lib64/libinstalls.z.so "$ROOT/backup/0.so"
    cp -p /system/lib64/platformsdk/libinstalls.z.so "$ROOT/backup/1.so"
    for INDEX in 0 1; do test "$(hash_file "$ROOT/backup/$INDEX.so")" = "$ORIGINAL"; done
    sync
    printf '%s\n' BACKUP_VERIFIED
    exit 0
fi
for INDEX in 0 1; do test "$(hash_file "$ROOT/backup/$INDEX.so")" = "$ORIGINAL"; done
if test "$ACTION" = apply; then
    test "$(hash_file "$ROOT/candidate.so")" = "$CANDIDATE"
    DESIRED=$CANDIDATE
else
    DESIRED=$ORIGINAL
fi
REMOUNT_ATTEMPTED=0
TEMP_OWNED=
finish() {
    STATUS=$?
    trap - 0
    if test -n "$TEMP_OWNED"; then rm -f "$TEMP_OWNED" || STATUS=24; fi
    if test "$REMOUNT_ATTEMPTED" = 1; then
        if ! mount -o ro,remount /; then printf '%s\n' ROOT_RO_RESTORE_FAILED >&2; STATUS=24; fi
        if ! assert_ro; then printf '%s\n' ROOT_NOT_RO >&2; STATUS=24; fi
    fi
    printf 'TRANSACTION_EXIT=%s\n' "$STATUS"
    exit "$STATUS"
}
trap finish 0
trap 'exit 25' 1 2 15
REMOUNT_ATTEMPTED=1
mount -o rw,remount /
for INDEX in 0 1; do
    if test "$INDEX" = 0; then TARGET=/system/lib64/libinstalls.z.so; else TARGET=/system/lib64/platformsdk/libinstalls.z.so; fi
    IFS=: read -r OWNER GROUP MODE LINKS < "$ROOT/meta-$INDEX.txt"
    test "$OWNER" = 0 && test "$GROUP" = 0 && test "$LINKS" = 1
    case "$MODE" in 644|755) ;; *) exit 26 ;; esac
    CONTEXT=$(sed -n '2s/ .*//p' "$ROOT/meta-$INDEX.txt")
    test "$CONTEXT" = u:object_r:system_lib_file:s0
    if test "$ACTION" = apply; then SOURCE="$ROOT/candidate.so"; else SOURCE="$ROOT/backup/$INDEX.so"; fi
    TEMP="$TARGET.spare-unify-new"
    test ! -e "$TEMP" && test ! -L "$TEMP"
    TEMP_OWNED=$TEMP
    cp -p "$SOURCE" "$TEMP"
    chmod "$MODE" "$TEMP"
    chown "$OWNER:$GROUP" "$TEMP"
    chcon "$CONTEXT" "$TEMP"
    test "$(hash_file "$TEMP")" = "$DESIRED"
    mv -f "$TEMP" "$TARGET"
    TEMP_OWNED=
    metadata "$TARGET" > "$ROOT/meta-after-$INDEX.txt"
    cmp "$ROOT/meta-$INDEX.txt" "$ROOT/meta-after-$INDEX.txt"
done
for TARGET in /system/lib64/libinstalls.z.so /system/lib64/platformsdk/libinstalls.z.so; do
    test "$(hash_file "$TARGET")" = "$DESIRED"
done
sync
printf '%s\n' INSTALLED_REBOOT_AND_VISUAL_PENDING
