#!/system/bin/sh
# Disable ONLY this additive boot slot. Keep pre-existing HAP/data and U13 recovery.
# Never enable/remove wl_toutiao.cfg.disabled, signal an init service, or kill by name.
set -u
ROOT=/data/westlake-demo/toutiao
F=/data/local/tmp/operator45/selfheal48
D=/data/local/tmp/operator45
[ -d "$ROOT" ] || { echo 'TT rollback: not installed'; exit 0; }
touch "$ROOT/DISABLED" "$F/stop" "$D/keeper.stop" || exit 1
. "$ROOT/scripts/route-b-owner.sh"
field(){ sed -n "s/^$1=//p" "$ROOT/receipt.env" 2>/dev/null; }
boot=$(cat /proc/sys/kernel/random/boot_id)
if [ "$(field boot_id)" = "$boot" ]; then
 for kind in guardian keeper; do
  p=$(field "$kind"); b=$(field "${kind}_birth")
  case "$kind" in guardian) script="$ROOT/scripts/watchdog.sh";; keeper) script="$ROOT/scripts/onscreen_keeper.sh";; esac
  [ -z "$p" ] || rb_script_signal "$p" "$b" "$script" || echo "TT rollback: no signal to stale/unowned $kind pid=$p"
 done
fi
sleep 3
# The slot stays disabled before and throughout cleanup. Freshly select only its own
# namespace/binary/UID, then retain the selected birth across TERM -> KILL fallback.
for p in $(rb_owned_pids); do
 b=$(rb_birth "$p") || continue
 rb_signal "$p" "$b" 15 || continue
 n=0
 while [ "$(rb_birth "$p")" = "$b" ] && [ "$n" -lt 20 ]; do sleep .1; n=$((n+1)); done
 [ "$(rb_birth "$p")" != "$b" ] || rb_signal "$p" "$b" 9 || exit 1
done
remaining=$(rb_owned_pids)
[ -z "$remaining" ] || { echo "TT rollback: owned processes remain: $remaining"; exit 1; }
echo 'TT rollback: slot disabled; owned B processes drained; HAP/data preserved; U13 untouched'
# Later, under an approved installer/remount window: remove only the cfg/worker
# listed in placement.json (or restore their pre-install backups). No broad rm.
