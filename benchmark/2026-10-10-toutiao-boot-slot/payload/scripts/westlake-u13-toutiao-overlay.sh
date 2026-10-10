#!/system/bin/sh
# #91 boot slot: use the existing Route B watchdog/namespace launcher after U13 READY.
# NO HAP install/extraction, global mount, aa start, service start/stop, or U13 mutation.
# The user desktop tap supplies imehost0; we only wait for that real foreground window.
set -u
ROOT=/data/westlake-demo/toutiao
F=/data/local/tmp/operator45/selfheal48
D=/data/local/tmp/operator45
RT=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d
log(){ echo "[TT-BOOT-SLOT] $*"; }
fail(){ log "FAIL $*"; exit 1; }
sha(){ sha256sum "$1" 2>/dev/null | cut -d' ' -f1; }
[ -e "$ROOT/DISABLED" ] && { log DISABLED; exit 0; }
[ ! -e /data/westlake-demo/u13/DISABLED ] || fail U13_DISABLED
[ "$(param get sys.westlake.demo.u13.ready 2>/dev/null)" = true ] || fail U13_NOT_READY
BOOT=$(cat /proc/sys/kernel/random/boot_id)
grep -qx 'state=READY' /data/westlake-demo/u13/receipt.env || fail U13_RECEIPT
 grep -qx "boot_id=$BOOT" /data/westlake-demo/u13/receipt.env || fail U13_BOOT_MISMATCH
[ -f "$ROOT/immutable.tsv" ] || fail UNPREPARED_SLOT
# Current Route B donor hardcodes the host sandbox UID; refuse any different install.
bm dump -n org.westlake.imehost > "$ROOT/host-bundle.txt" 2>&1 || fail HOST_ABSENT
grep -q '"uid"[[:space:]]*:[[:space:]]*20010053\([^0-9]\|$\)' "$ROOT/host-bundle.txt" || fail HOST_UID
while read -r digest file; do
 [ -n "$digest" ] || continue
 [ "$(sha "$file")" = "$digest" ] || fail "IDENTITY $file"
done < "$ROOT/immutable.tsv"
[ -d "$RT/private-tmp/asx" ] || fail PRIVATE_ASX_MOUNTPOINT
[ "$(stat -c '%u:%g' "$RT/private-tmp" 2>/dev/null)" = 20010053:20010053 ] || fail PRIVATE_TMP_OWNER
# Never call a WAITING or failed previous attempt ARMED. Init once semantics
# owns this worker; a second same-boot invocation refuses instead of duplicating it.
[ -e "$ROOT/receipt.env" ] && grep -qx "boot_id=$BOOT" "$ROOT/receipt.env" && fail SAME_BOOT_ALREADY_ATTEMPTED
# Stop/lock/state files are durable, PIDs are not. Donor watchdog validates/reclaims its own stale lock.
[ -S /dev/unix/socket/A2HSourcec91d26bfb4db4fd5a002 ] && fail EXISTING_ROUTE_B_SOCKET
printf 'state=WAITING_FOR_DESKTOP_TAP\nboot_id=%s\n' "$BOOT" > "$ROOT/receipt.env"
log 'WAITING_FOR_DESKTOP_TAP (no background launch; U13 remains ondemand)'
while :; do
 [ ! -e "$ROOT/DISABLED" ] && [ ! -e /data/westlake-demo/u13/DISABLED ] || exit 0
 [ "$(cat /proc/sys/kernel/random/boot_id)" = "$BOOT" ] || fail BOOT_CHANGED
 # Exact donor WMS columns: window-name/display/pid/id/type/mode/flags/z-order.
 row=$(hidumper -s WindowManagerService -a '-a' 2>/dev/null | grep '^imehost0[[:space:]]' | head -1)
 if [ -n "$row" ]; then
  set -- $row
  case "${4:-}" in ''|*[!0-9]*) :;; *)
   case "${8:--1}" in ''|-*|*[!0-9]*) :;; *) break;; esac;; esac
 fi
 sleep 1
done
rm -f "$F/stop" "$D/stop" "$D/fresh48/stop" "$D/keeper.stop"
# Exact donor nohup/watchdog and keeper startup. NO eager spawner: start-parent.sh
# establishes its private mount namespace and refreshes WL_PARENT_ID for this host.
nohup /system/bin/sh "$ROOT/scripts/watchdog.sh" > "$ROOT/watchdog-boot.log" 2>&1 </dev/null &
guardian=$!
. "$ROOT/scripts/route-b-owner.sh"
gb=$(rb_birth "$guardian") || fail GUARDIAN_EXITED
KDIR="$D" INTERVAL=5 nohup /system/bin/sh "$ROOT/scripts/onscreen_keeper.sh" > "$ROOT/keeper-boot.log" 2>&1 </dev/null &
keeper=$!; kb=$(rb_birth "$keeper") || fail KEEPER_EXITED
printf 'state=ARMED\nboot_id=%s\nguardian=%s\nguardian_birth=%s\nkeeper=%s\nkeeper_birth=%s\n' "$BOOT" "$guardian" "$gb" "$keeper" "$kb" > "$ROOT/receipt.env"
log "ARMED guardian=$guardian keeper=$keeper; screenshots, not this state, decide lighting"
