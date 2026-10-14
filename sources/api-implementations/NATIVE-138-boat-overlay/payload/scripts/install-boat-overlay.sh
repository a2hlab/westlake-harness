#!/system/bin/sh
# INSTALLER for the standalone Boat-layer boot overlay (v2 seal, cc-t3 #91). ON-BOARD step; run while the board is
# live in its normal route-a-complete unified state. Deterministic, fail-closed, idempotent, NO reboot, NO setenforce.
# Does NOT archive the 56 U13 layers and NEVER touches /system/android or $ROOT/sources (the base recover owns those).
#
# Order: preconditions -> stage sources-boat (SHA-gated) -> place cfg + overlay script (backup first; ALLOW_REMOUNT for
# sealed /system, reseal ro on exit) -> re-verify placements. BoatAttack APK install + prepare_sandbox are done by the
# rehearsal runner (they need the app UID); this installer only requires the app already installed when WITH_PRIVATE=1.
set -u
ROOT=/data/westlake-demo/u13; BARCH="$ROOT/sources-boat-v2"; BACKUP="$ROOT/backup-boat"
DEPLOY=${DEPLOY:?set DEPLOY to the staged payload dir (holds sources-boat/ + init/ + scripts/)}
INIT_CFG_DIR=${INIT_CFG_DIR:-/system/etc/init}
SCRIPT_DIR=${SCRIPT_DIR:-/system/etc}
ALLOW_REMOUNT=${ALLOW_REMOUNT:-0}
# ownership (a): place the v2 overlay script + a boatv2 cfg that REPLACES cc-wiki's recover cfg (same name, repointing
# only the boat-overlay service to the v2 script); cc-wiki's recover script + their boat-overlay script stay on disk,
# untouched (the swapped cfg just no longer invokes the old boat script). Original cc-wiki cfg is backed up for rollback.
CFG_SRC=00_westlake_u13_recover-boatv2.cfg; CFG_DST_NAME=00_westlake_u13_recover.cfg
OVERLAY=westlake-u13-boat-overlay-v2.sh; DISABLE=westlake-boat-overlay-disable.sh
BUNDLE=com.Unity3d.BoatAttackDay
# the 5 Boat source files + pinned SHAs (v2: NO runtime)
BOAT_SRCS="liboh_adapter_bridge.so:8ab85446f8b386c4a649576326d5f393669b3a22529874fb673eea7c3b1cd71e \
oh-adapter-runtime.jar:6333bcab4ca2daad03965712deac6adf028a6ff0dfac04fc8ea91af177828852 \
libunity.so:1bea0fae1e6e76db15f17fca2bfa91b9c303ce278d6a4dcfba6af233b68b64ac \
libil2cpp.so:f6b806b5c55e702b98caa2e85d2f9afb678bc47dcc4067017b33f5269afed746 \
libwestlake_bionic_signal_box.so:7a931c79c0be28468bdd02a626a637431f2447f5fd0aba87176e5acdb071f5da"
log(){ echo "install-boat: $*"; }
fail(){ echo "install-boat: FAIL $*" >&2; exit 1; }
sha(){ sha256sum "$1" 2>/dev/null|cut -d' ' -f1; }

root_opt(){ grep ' / ' /proc/mounts 2>/dev/null|head -n1|cut -d' ' -f4; }
root_rw(){ case ",$(root_opt)," in *,rw,*) return 0;; esac
  [ "$ALLOW_REMOUNT" = 1 ] || fail "ROOT_RO (ADMISSION: set ALLOW_REMOUNT=1 to remount / rw — board step, do NOT force)"
  mount -o rw,remount / 2>/dev/null || fail REMOUNT_RW
  case ",$(root_opt)," in *,rw,*) RESEAL=1; log "remounted / rw";; *) fail REMOUNT_RW_VERIFY;; esac }
root_ro(){ [ "${RESEAL:-0}" = 1 ] || return 0; sync; mount -o ro,remount / 2>/dev/null && log "re-sealed / ro" || log "WARN could not re-seal / ro"; RESEAL=0; }
RESEAL=0; trap 'root_ro' EXIT INT TERM

# --- 1. preconditions ---
case "$(param get bootevent.boot.completed 2>/dev/null)" in true*) ;; *) fail BOOT_NOT_COMPLETED ;; esac
[ -d /data/app/el1/bundle/public ] || fail DATA_PKG_ROOT_NOT_READY
[ -d "$DEPLOY/sources-boat" ] || fail "MISSING_DEPLOY_SOURCES $DEPLOY/sources-boat"
[ -f "$DEPLOY/init/$CFG_SRC" ] || fail "MISSING_CFG $DEPLOY/init/$CFG_SRC"
[ -f "$INIT_CFG_DIR/$CFG_DST_NAME" ] || fail "NO_CCWIKI_RECOVER_CFG $INIT_CFG_DIR/$CFG_DST_NAME (ownership-(a) replaces cc-wiki's recover cfg in place; it must exist)"
[ -f "$DEPLOY/scripts/$OVERLAY" ] || fail "MISSING_OVERLAY $DEPLOY/scripts/$OVERLAY"
mkdir -p "$BARCH" "$BACKUP" || fail MKDIR_ROOT

# --- 2. stage sources-boat (SHA-gated) ---
for pr in $BOAT_SRCS; do
  f=${pr%:*}; want=${pr##*:}
  [ -f "$DEPLOY/sources-boat/$f" ] || fail "DEPLOY_SRC_MISSING $f"
  [ "$(sha "$DEPLOY/sources-boat/$f")" = "$want" ] || fail "DEPLOY_SRC_SHA $f want=$want got=$(sha "$DEPLOY/sources-boat/$f")"
  cp "$DEPLOY/sources-boat/$f" "$BARCH/$f" || fail "STAGE_CP $f"
  [ "$(sha "$BARCH/$f")" = "$want" ] || fail "STAGE_SHA $f"
  log "staged $f -> $want"
done

# --- 3. place cfg + scripts (backup first; remount sealed /system) ---
root_rw
for pair in "scripts/$OVERLAY:$SCRIPT_DIR/$OVERLAY" "scripts/$DISABLE:$SCRIPT_DIR/$DISABLE" "init/$CFG_SRC:$INIT_CFG_DIR/$CFG_DST_NAME"; do
  src="$DEPLOY/${pair%:*}"; dst=${pair##*:}
  [ -f "$src" ] || { [ "${pair%:*}" = "scripts/$DISABLE" ] && { log "no $DISABLE in deploy — skipping (optional)"; continue; } || fail "PLACE_SRC_MISSING $src"; }
  [ -e "$dst" ] && { cp "$dst" "$BACKUP/$(basename "$dst").bak" 2>/dev/null && log "backed up $dst"; }
  cp "$src" "$dst" || fail "PLACE_CP $dst"
  chmod 0644 "$dst" 2>/dev/null; [ "${dst##*.}" = sh ] && chmod 0755 "$dst" 2>/dev/null
  chcon u:object_r:system_file:s0 "$dst" 2>/dev/null
  [ "$(sha "$src")" = "$(sha "$dst")" ] || fail "PLACE_VERIFY $dst"
  log "placed $dst"
done
root_ro

# --- 4. report ---
log "INSTALL OK (sources-boat staged + cfg/overlay placed). NO reboot. WITH_PRIVATE requires BoatAttack installed:"
if [ -d "/data/app/el1/bundle/public/$BUNDLE" ]; then log "BoatAttack installed — boot overlay will bind private libs."; else log "WARN BoatAttack NOT installed — install APK + prepare_sandbox before the seal reboot (runner does this)."; fi
log "enable=placed; disable: touch $ROOT/BOAT_DISABLED (or $SCRIPT_DIR/$DISABLE); rollback: rollback-boat-overlay.sh"
exit 0
