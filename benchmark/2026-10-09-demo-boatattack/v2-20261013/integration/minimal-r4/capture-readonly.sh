#!/system/bin/sh
# Outer executes this body using its pinned transport; no mkdir, mount, or writes.
set -eu
boot=$(cat /proc/sys/kernel/random/boot_id)
printf 'BOOT_BEFORE=%s\n' "$boot"
for path in /system/android/lib64/libandroid.so /system/android/lib64/liboh_android_runtime.so /system/etc/init/00_westlake_u13_recover-v3.cfg; do
    test -f "$path"; test ! -L "$path"
    printf 'FILE=%s\n' "$path"
    sha256sum "$path"
    stat -c 'META=%a:%u:%g:%C' "$path"
done
path=/data/westlake-demo/u13/boat-v2-20261013-r4
if [ -e "$path" ] || [ -L "$path" ]; then
    printf 'R4_ROOT=PRESENT\n'; exit 3
fi
# Explicit traversable ancestor proof; unknown path errors must not imply absence.
test -d /data/westlake-demo/u13; test ! -L /data/westlake-demo/u13
ls -ld /data /data/westlake-demo /data/westlake-demo/u13
printf 'R4_ROOT=ABSENT\n'
cat /data/westlake-demo/u13/receipt.env
end=$(cat /proc/sys/kernel/random/boot_id)
printf 'BOOT_AFTER=%s\n' "$end"
test "$boot" = "$end"
