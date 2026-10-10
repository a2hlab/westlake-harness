#!/system/bin/sh
# FULL ROLLBACK of the U13 autostart -> leave bare /system with no autostart trace. Removes the init cfg + the two boot
# scripts (restoring any backed-up originals), then removes the durable root. Live bind overlays (if any were applied
# this boot) are cleared by the reboot that follows; this script does NOT itself launch/kill apps and does NOT reboot.
# Idempotent and conservative: it only removes files THIS payload installed (tracked in $BACKUP/placed.list).
set -u
ROOT=/data/westlake-demo/u13
BACKUP="$ROOT/backup"
INIT_CFG_DIR=${INIT_CFG_DIR:-/system/etc/init}
SCRIPT_DIR=${SCRIPT_DIR:-/system/etc}
KEEP_ARCHIVE=${KEEP_ARCHIVE:-0}   # set 1 to keep $ROOT/sources* for re-install
log(){ echo "rollback-u13: $*"; }
[ -d "$ROOT" ] || { log "nothing to roll back ($ROOT absent)"; exit 0; }

# 1. restore/remove the files we placed, from the install-time manifest (authoritative)
if [ -f "$BACKUP/placed.list" ]; then
  while IFS= read -r dst; do
    [ -z "$dst" ] && continue
    b=$(basename "$dst")
    if [ -f "$BACKUP/$b.orig" ]; then
      cp -a "$BACKUP/$b.orig" "$dst" 2>/dev/null && log "restored original $dst" || log "WARN could not restore $dst"
    else
      rm -f "$dst" 2>/dev/null && log "removed $dst" || log "WARN could not remove $dst (ro? remount at board step)"
    fi
  done < "$BACKUP/placed.list"
else
  # fallback: remove the known placements by name
  for f in "$INIT_CFG_DIR/00_westlake_u13_recover.cfg" "$SCRIPT_DIR/westlake-u13-recover.sh" "$SCRIPT_DIR/westlake-u13-boat-overlay.sh"; do
    [ -e "$f" ] && { rm -f "$f" 2>/dev/null && log "removed $f" || log "WARN could not remove $f (ro?)"; }
  done
  log "no placed.list found; removed known placements by name"
fi

# 2. remove durable root (unless keeping the archive for a re-install)
if [ "$KEEP_ARCHIVE" = 1 ]; then
  rm -f "$ROOT"/*.json "$ROOT"/*.tsv "$ROOT"/receipt* "$ROOT"/*.log "$ROOT"/DISABLED 2>/dev/null
  log "kept $ROOT/sources* ; cleared tables/receipts/logs"
else
  /bin/rm -rf "$ROOT" 2>/dev/null && log "removed durable root $ROOT" || log "WARN could not remove $ROOT"
fi
# 3. best-effort removal of the two physical additions finalize_runtime makes OUTSIDE the bound trees (need / rw).
#    (Bound-tree relabels + boot.art symlink live inside overlays that clear on reboot; anco params are persist.* that
#    any U13 deploy sets, so leaving them is a no-op.)
if [ -L /system/lib/libc_musl.so ] || [ -f /system/etc/fonts.xml ]; then
  opt=$(grep ' / ' /proc/mounts 2>/dev/null | head -n1 | cut -d' ' -f4); resealed=0
  case ",$opt," in *,rw,*) ;; *) mount -o rw,remount / 2>/dev/null && resealed=1 ;; esac
  [ -L /system/lib/libc_musl.so ] && { rm -f /system/lib/libc_musl.so 2>/dev/null && log "removed libc_musl.so symlink"; }
  # only remove fonts.xml if it is the copy finalize placed (leave a pre-existing stock one alone): compare to source
  [ -f /system/etc/fonts.xml ] && [ -f /system/android/etc/fonts.xml ] && cmp -s /system/etc/fonts.xml /system/android/etc/fonts.xml 2>/dev/null && { rm -f /system/etc/fonts.xml 2>/dev/null && log "removed finalize fonts.xml copy"; }
  [ "$resealed" = 1 ] && { sync; mount -o ro,remount / 2>/dev/null; }
fi
log "DONE -> reboot to land on bare /system (boot-time binds clear on reboot; verify with the KA bare-system check)"
echo "ROLLBACK_OK"
