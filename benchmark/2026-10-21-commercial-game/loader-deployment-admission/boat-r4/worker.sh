#!/system/bin/sh
# Retains a8bb2 five-bind order; appends the reviewed runtime port then original ADC libandroid repair; no app launch, global disable, or relabel fallback.
set -eu
umask 022
ROOT=/data/westlake-demo/u13
OWN="$ROOT/boat-v2-20261013-r4"
TABLE="$OWN/binds.tsv"
TABLE_SHA=a10586a19ca0a812356e6dc65490f3e4a4f236e011021909bb174015c2c66cde
BOOT=$(cat /proc/sys/kernel/random/boot_id)
LOG="$OWN/boat-$BOOT.log"
receipt="$OWN/boat-$BOOT.receipt"
log(){ echo "$*" >> "$LOG"; }
fail(){ log "FAILED $*"; printf 'state=FAILED\nboot_id=%s\nreason=%s\n' "$BOOT" "$*" > "$receipt"; exit 1; }
sha(){ sha256sum "$1" | cut -d' ' -f1; }
meta(){ stat -c '%a:%u:%g:%C' "$1"; }
[ ! -e "$ROOT/BOAT_DISABLED" ] || { log BOAT_DISABLED; exit 0; }
[ "$(sha "$TABLE")" = "$TABLE_SHA" ] || fail TABLE_SHA
self_ns_rc=0; self_ns=$(readlink /proc/self/ns/mnt 2>>"$LOG") || self_ns_rc=$?
init_ns_rc=0; init_ns=$(readlink /proc/1/ns/mnt 2>>"$LOG") || init_ns_rc=$?
log "MOUNT_NS self_rc=$self_ns_rc self=$self_ns init_rc=$init_ns_rc init=$init_ns"
[ "$self_ns_rc" = 0 ] || fail SELF_MOUNT_NS_READ
[ "$init_ns_rc" = 0 ] || fail INIT_MOUNT_NS_READ
printf '%s\n' "$self_ns" | grep -Eq '^mnt:\[[0-9]+\]$' || fail SELF_MOUNT_NS_FORMAT
printf '%s\n' "$init_ns" | grep -Eq '^mnt:\[[0-9]+\]$' || fail INIT_MOUNT_NS_FORMAT
[ "$self_ns" = "$init_ns" ] || fail NOT_INIT_MOUNT_NS
[ "$(sha /system/bin/appspawn-x)" = 2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e ] || fail U13_HOST
no_parent(){
    for p in $(pidof appspawn-x 2>/dev/null || true); do
        exe=$(readlink "/proc/$p/exe" 2>/dev/null) || fail PARENT_READ
        case "$exe" in /system/bin/appspawn-x*) fail U13_PARENT_ALREADY_RUNNING;; esac
    done
}
case "${1:---verify-bound}" in
    --bind-before-ready)
        [ "$(sha /system/android/lib64/liboh_android_runtime.so)" = 18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae ] || fail STOCK_RUNTIME
        [ "$(sha /system/android/lib64/libandroid.so)" = 9ccf64f8d1f6e1748665057273eaa4c2770098934d39afa160f2c6b4c18b06db ] || fail STOCK_LIBANDROID
        no_parent;;
    --verify-bound)
        [ "$(sha /system/android/lib64/liboh_android_runtime.so)" = 94718e0d0b617a0f9a860e0b50b879b0d7d4639f32e8230b1f90f8e26e2c1354 ] || fail CANDIDATE_RUNTIME
        [ "$(sha /system/android/lib64/libandroid.so)" = adc125f4dfb800c25d80e7d73216c8885fd64a31c6b91f064494166c63a59130 ] || fail CANDIDATE_LIBANDROID
        grep -qx 'state=BOUND' "$receipt" && grep -qx "boot_id=$BOOT" "$receipt" && grep -qx 'layers=7' "$receipt" || fail NO_SYNCHRONOUS_BOUND
        n=0
        while IFS="$(printf '\t')" read -r name target before after before_meta metadata; do
            n=$((n+1)); src="$OWN/sources/$name"
            [ "$(sha "$target")" = "$after" ] && [ "$(meta "$target")" = "$metadata" ] || fail "VERIFY_$n"
            [ "$(stat -c '%d:%i' "$target")" = "$(stat -c '%d:%i' "$src")" ] || fail "VERIFY_OWNER_$n"
        done < "$TABLE"
        [ "$n" = 7 ] || fail VERIFY_COUNT
        exit 0;;
    *) fail UNKNOWN_MODE;;
esac
grep -qx 'state=READY' "$ROOT/receipt.env" || fail U13_STATE
grep -qx 'layers=56' "$ROOT/receipt.env" || fail U13_LAYERS
grep -qx "boot_id=$BOOT" "$ROOT/receipt.env" || fail U13_BOOT
# All inputs and all target preimages pass before the first bind. Placeholder creation belongs to installer.
n=0
while IFS="$(printf '\t')" read -r name target before after before_meta metadata; do
    n=$((n+1)); src="$OWN/sources/$name"
    [ -f "$src" ] && [ ! -L "$src" ] && [ -f "$target" ] && [ ! -L "$target" ] || fail "TYPE_$n"
    [ "$(sha "$src")" = "$after" ] && [ "$(meta "$src")" = "$metadata" ] || fail "SOURCE_$n"
    [ "$(sha "$target")" = "$before" ] && [ "$(meta "$target")" = "$before_meta" ] || fail "PREIMAGE_$n"
done < "$TABLE"
[ "$n" = 7 ] || fail COUNT
# Repeated invocation rejects rather than double-binding; immutable per-boot intents retain partial failure evidence.
[ ! -e "$OWN/boat-$BOOT.intents" ] || fail ALREADY_ATTEMPTED_THIS_BOOT
(set -C; : > "$OWN/boat-$BOOT.intents") || fail INTENT_CREATE
n=0
while IFS="$(printf '\t')" read -r name target before after before_meta metadata; do
    n=$((n+1)); src="$OWN/sources/$name"
    [ "$(cat /proc/sys/kernel/random/boot_id)" = "$BOOT" ] || fail BOOT_CHANGED
    [ "$(sha "$target")" = "$before" ] && [ "$(meta "$target")" = "$before_meta" ] || fail "PRE_BIND_DRIFT_$n"
    printf '%s\t%s\t%s\t%s\n' "$n" "$src" "$target" "$after" >> "$OWN/boat-$BOOT.intents"
    no_parent
    mount -o bind "$src" "$target" || fail "BIND_$n"
    no_parent
    [ "$(sha "$target")" = "$after" ] && [ "$(meta "$target")" = "$metadata" ] || fail "READBACK_$n"
    [ "$(stat -c '%d:%i' "$target")" = "$(stat -c '%d:%i' "$src")" ] || fail "OWNER_$n"
    log "BOUND $n $target $after"
done < "$TABLE"
no_parent
printf 'state=BOUND\nboot_id=%s\nlayers=7\nui_accepted=false\n' "$BOOT" > "$receipt"
