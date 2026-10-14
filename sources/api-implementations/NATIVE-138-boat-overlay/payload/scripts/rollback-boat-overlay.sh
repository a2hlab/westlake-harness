#!/system/bin/sh
# Full rollback of the Boat boot overlay (cc-t3 #91). Removes the init cfg + overlay/disable scripts (restoring any
# backed-up originals), unmounts any live Boat binds, and removes the durable sources-boat archive — returning the
# board to the plain unified state on the next boot. NO setenforce. ALLOW_REMOUNT to touch sealed /system; reseal ro.
# Does NOT uninstall BoatAttack (the seal installer owns that; pass --uninstall to also bm uninstall it).
set -u
ROOT=/data/westlake-demo/u13; BARCH="$ROOT/sources-boat-v2"; BACKUP="$ROOT/backup-boat"
INIT_CFG_DIR=${INIT_CFG_DIR:-/system/etc/init}; SCRIPT_DIR=${SCRIPT_DIR:-/system/etc}
ALLOW_REMOUNT=${ALLOW_REMOUNT:-0}
# ownership (a): CFG is cc-wiki's recover cfg name — rollback RESTORES the backed-up original (reverting the boat
# service back to cc-wiki's adc125f4 script); the v2 overlay script (no backup) is removed. cc-wiki's recover script
# is never touched.
CFG=00_westlake_u13_recover.cfg; OVERLAY=westlake-u13-boat-overlay-v2.sh; DISABLE=westlake-boat-overlay-disable.sh
BUNDLE=com.Unity3d.BoatAttackDay; LIBD="/data/app/el1/bundle/public/$BUNDLE/android/lib/arm64-v8a"
ADAPTER_T=/system/android/lib64/liboh_adapter_bridge.so; JAR_T=/system/android/framework/oh-adapter-runtime.jar
log(){ echo "rollback-boat: $*"; }
root_opt(){ grep ' / ' /proc/mounts 2>/dev/null|head -n1|cut -d' ' -f4; }
root_rw(){ case ",$(root_opt)," in *,rw,*) return 0;; esac
  [ "$ALLOW_REMOUNT" = 1 ] || { log "ROOT_RO (set ALLOW_REMOUNT=1 to remove /system cfg)"; return 1; }
  mount -o rw,remount / 2>/dev/null && { RESEAL=1; log "remounted / rw"; } || log "WARN remount rw failed"; }
root_ro(){ [ "${RESEAL:-0}" = 1 ] || return 0; sync; mount -o ro,remount / 2>/dev/null && log "re-sealed / ro"; RESEAL=0; }
RESEAL=0; trap 'root_ro' EXIT INT TERM

# 1. unmount any live Boat binds (idempotent; harmless if not mounted)
for t in "$LIBD/libwestlake_bionic_signal_box.so" "$LIBD/libunity.so" "$LIBD/libil2cpp.so" "$JAR_T" "$ADAPTER_T"; do
  umount "$t" 2>/dev/null && log "umounted $t"
done
# 2. remove init cfg + scripts (restore backups if present) — sealed /system
root_rw
for dst in "$INIT_CFG_DIR/$CFG" "$SCRIPT_DIR/$OVERLAY" "$SCRIPT_DIR/$DISABLE"; do
  if [ -f "$BACKUP/$(basename "$dst").bak" ]; then cp "$BACKUP/$(basename "$dst").bak" "$dst" && log "restored $dst"; else rm -f "$dst" 2>/dev/null && log "removed $dst"; fi
done
root_ro
# 3. remove durable archive + markers
rm -rf "$BARCH" "$ROOT/BOAT_DISABLED" "$ROOT/boat-overlay.log" 2>/dev/null; log "removed $BARCH + markers"
# 4. optional: uninstall BoatAttack
if [ "${1:-}" = "--uninstall" ]; then bm uninstall -n "$BUNDLE" 2>&1 | tail -1; log "requested BoatAttack uninstall"; fi
log "ROLLBACK done — next boot = plain unified state (no Boat binds)."
exit 0
