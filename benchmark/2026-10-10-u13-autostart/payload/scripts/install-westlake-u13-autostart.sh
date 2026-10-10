#!/system/bin/sh
# INSTALLER for the U13 boot autostart (ON-BOARD step; run while the board is live in a healthy U13 state).
# Deterministic, fail-closed, idempotent. It does the durable-snapshot + artifact placement; it does NOT reboot.
#
# What it does, in order:
#   1. Preconditions: boot.completed, /data pkg root, live U13 (appspawn-x up @ pinned SHA, 56 layers present).
#   2. Snapshot the 56 live baseline targets into a reboot-persistent archive ($ROOT/sources) and SHA-verify each
#      against the pinned table (the table's own `source` host dirs are ephemeral; we archive the TARGET bytes).
#   3. Stage the BoatAttack overlay artifacts (C8 adapter 8ab85446 + C9 jar 6333bcab + 3 private) from $DEPLOY into
#      $ROOT/sources-boat and SHA-verify.
#   4. Emit the line-oriented replay list $ROOT/u13-recover-table.tsv (jq-free worker input), copy the JSON table.
#   5. Place the two boot scripts + the init .cfg at the init-scanned locations, backing up anything overwritten.
#   6. chcon/label + lock down $ROOT, then re-verify every placement. Print a report incl. the ADMISSION result.
# ADMISSION: the exact init-cfg dir that survives sealed /system and is scanned by init is a board property. Override
# INIT_CFG_DIR / SCRIPT_DIR / ALLOW_REMOUNT per the board step; if placement is not persistable sealed, the installer
# STOPS (it never makes the board permissive and never leaves a cfg init won't read). No setenforce. No reboot here.
set -u
ROOT=/data/westlake-demo/u13
DEPLOY=${DEPLOY:?set DEPLOY to the staged payload dir (holds boat-artifacts/ + init/ + scripts/ + u13-recover-table.json)}
TABLE_SRC="$DEPLOY/u13-recover-table.json"
INIT_CFG_DIR=${INIT_CFG_DIR:-/system/etc/init}
SCRIPT_DIR=${SCRIPT_DIR:-/system/etc}
ALLOW_REMOUNT=${ALLOW_REMOUNT:-0}
APPSPAWN_SHA=2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e
ARCH="$ROOT/sources"; BARCH="$ROOT/sources-boat"; BACKUP="$ROOT/backup"; TSV="$ROOT/u13-recover-table.tsv"
log(){ echo "install-u13: $*"; }
fail(){ echo "install-u13: FAIL $*" >&2; exit 1; }
sha(){ sha256sum "$1" 2>/dev/null | cut -d' ' -f1; }
need(){ command -v "$1" >/dev/null 2>&1 || fail "MISSING_TOOL $1"; }
need sha256sum   # board has no python3/awk/tr — stay POSIX-sh + sed/cut/grep only
SUPERSEDE=${SUPERSEDE:-0}
WITH_BOAT=${WITH_BOAT:-1}   # 1 = stage + place the BoatAttack overlay; 0 = U13-only (e.g. 61b: U13 + Toutiao placeholder)

# root /-remount helpers (proven: donor install-boat-attack-autostart.sh root_mount_options). Reseal ro on ANY exit.
root_opt(){ grep ' / ' /proc/mounts 2>/dev/null | head -n1 | cut -d' ' -f4; }
root_rw(){ case ",$(root_opt)," in *,rw,*) return 0;; esac
  [ "$ALLOW_REMOUNT" = 1 ] || fail "ROOT_RO (ADMISSION: set ALLOW_REMOUNT=1 to remount / rw — board step, do NOT force)"
  mount -o rw,remount / 2>/dev/null || fail REMOUNT_RW
  case ",$(root_opt)," in *,rw,*) RESEAL=1; log "remounted / rw";; *) fail REMOUNT_RW_VERIFY;; esac }
root_ro(){ [ "${RESEAL:-0}" = 1 ] || return 0; sync; mount -o ro,remount / 2>/dev/null && log "re-sealed / ro" || log "WARN could not re-seal / ro"; RESEAL=0; }
RESEAL=0; trap 'root_ro' EXIT INT TERM

# --- 1. preconditions -------------------------------------------------------
case "$(param get bootevent.boot.completed 2>/dev/null)" in true*) ;; *) fail BOOT_NOT_COMPLETED ;; esac
[ -d /data/app/el1/bundle/public ] || fail DATA_PKG_ROOT_NOT_READY
[ -f "$TABLE_SRC" ] || fail "MISSING_TABLE $TABLE_SRC"
pid=$(pidof appspawn-x 2>/dev/null); [ -n "$pid" ] || fail APPSPAWN_NOT_RUNNING
[ "$(sha /system/bin/appspawn-x)" = "$APPSPAWN_SHA" ] || fail APPSPAWN_SHA_MISMATCH
log "preconditions ok (appspawn-x pid=$pid sha-ok, U13 live)"

mkdir -p "$ARCH" "$BARCH" "$BACKUP" || fail MKDIR_ROOT
cp "$TABLE_SRC" "$ROOT/u13-recover-table.json" || fail COPY_TABLE

# --- 2. snapshot the 56 live targets into the durable archive ----------------
# Emit the .tsv while snapshotting: seq \t kind \t group \t target \t archived_source \t sha256
# The replay plan (seq\tkind\tgroup\ttarget\tsha) is pre-generated on the host (board has no python3/jq) and pushed
# next to the JSON table. It is checksum-pinned by the KA tests against the table so it cannot silently diverge.
: > "$TSV.tmp"
if [ -f "$DEPLOY/u13-recover-table.plan" ]; then
  cp "$DEPLOY/u13-recover-table.plan" "$ROOT/.layers.plan" || fail PLAN_COPY
elif command -v python3 >/dev/null 2>&1; then
  python3 - "$ROOT/u13-recover-table.json" <<'PY' > "$ROOT/.layers.plan" || fail PLAN_TABLE
import json,sys
t=json.load(open(sys.argv[1]))
for r in t["recover_layers"]:
    print("%d\t%s\t%s\t%s\t%s" % (r["sequence"], r["kind"], r["group"], r["target"], r["sha256"] or ""))
PY
else
  fail "NO_PLAN (board has no python3; stage u13-recover-table.plan next to the JSON table)"
fi
n=0
while IFS="$(printf '\t')" read -r seq kind group target sha_want; do
  [ -z "$seq" ] && continue
  n=$((n+1))
  [ -e "$target" ] || fail "LIVE_TARGET_MISSING seq=$seq $target"
  dst="$ARCH/seq$seq"
  if [ "$kind" = directory ]; then
    /bin/rm -rf "$dst"; mkdir -p "$dst" || fail "MKARCH seq=$seq"
    cp -a "$target/." "$dst/" 2>/dev/null || fail "ARCHIVE_DIR seq=$seq $target"
    aline="$dst"; shaout=""
  else
    cp -a "$target" "$dst" 2>/dev/null || fail "ARCHIVE_FILE seq=$seq $target"
    got=$(sha "$dst"); [ -n "$sha_want" ] && [ "$got" != "$sha_want" ] && fail "ARCHIVE_SHA seq=$seq want=$sha_want got=$got"
    aline="$dst"; shaout="$sha_want"
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$seq" "$kind" "$group" "$target" "$aline" "$shaout" >> "$TSV.tmp"
done < "$ROOT/.layers.plan"
[ "$n" = 56 ] || fail "PLAN_COUNT got=$n want=56"
mv "$TSV.tmp" "$TSV" || fail MV_TSV
log "archived + verified $n/56 baseline layers -> $ARCH; emitted $TSV"

# --- 3. stage the BoatAttack overlay artifacts (SHA-gated; skipped when WITH_BOAT=0) ---
stage_boat(){ # srcfile want
  src="$DEPLOY/boat-artifacts/$1"; [ -f "$src" ] || fail "BOAT_ARTIFACT_MISSING $1"
  [ "$(sha "$src")" = "$2" ] || fail "BOAT_ARTIFACT_SHA $1"
  cp -a "$src" "$BARCH/$1" || fail "BOAT_STAGE $1"; log "staged boat/$1 ($2)"; }
if [ "$WITH_BOAT" = 1 ]; then
  stage_boat liboh_adapter_bridge.so 8ab85446f8b386c4a649576326d5f393669b3a22529874fb673eea7c3b1cd71e
  stage_boat oh-adapter-runtime.jar  6333bcab4ca2daad03965712deac6adf028a6ff0dfac04fc8ea91af177828852
  stage_boat libunity.so             1bea0fae1e6e76db15f17fca2bfa91b9c303ce278d6a4dcfba6af233b68b64ac
  stage_boat libil2cpp.so            f6b806b5c55e702b98caa2e85d2f9afb678bc47dcc4067017b33f5269afed746
  stage_boat libwestlake_bionic_signal_box.so 7a931c79c0be28468bdd02a626a637431f2447f5fd0aba87176e5acdb071f5da
  stage_boat liboh_android_runtime.so adc125f4dfb800c25d80e7d73216c8885fd64a31c6b91f064494166c63a59130
else
  log "WITH_BOAT=0 -> U13-only (no BoatAttack overlay staged)"
fi

# --- 4. remount / rw, supersede any conflicting boot worker, place scripts + init cfg --
# Proven mechanics (donor install-boat-attack-autostart.sh:343): root rw remount, explicit labels, re-seal ro (trap).
root_rw
# Never two boot workers (plan: "do not leave two boot workers replaying different generations in parallel").
# Back up then remove any OTHER init cfg that defines a recovery/appspawn-x owner; only our cfg remains.
for old in "$INIT_CFG_DIR"/*.cfg; do
  [ -e "$old" ] || continue
  bn=$(basename "$old"); [ "$bn" = 00_westlake_u13_recover.cfg ] && continue
  grep -qiE 'pr03-runtime-recover|boatattack-autostart|westlake-u13|start_service appspawn-x|start appspawn-x' "$old" 2>/dev/null || continue
  [ "$SUPERSEDE" = 1 ] || fail "CONFLICT_OWNER $old (a foreign boot worker; set SUPERSEDE=1 to back up + remove — board step, do NOT force)"
  cp -a "$old" "$BACKUP/$bn.superseded" 2>/dev/null; echo "$old" >> "$BACKUP/superseded.list"
  for ref in $(grep -oE '/system/etc/[A-Za-z0-9._/-]+\.sh' "$old" 2>/dev/null | sort -u); do
    [ -e "$ref" ] && { cp -a "$ref" "$BACKUP/$(basename "$ref").superseded" 2>/dev/null; echo "$ref" >> "$BACKUP/superseded.list"; rm -f "$ref" 2>/dev/null && log "superseded script $ref"; }
  done
  rm -f "$old" 2>/dev/null && log "superseded cfg $old (backed up)" || fail "SUPERSEDE_RM $old"
done

place(){ # srcfile destdir  -> explicit proven label (system_etc_file) + 0550 + root:root
  s="$1" d="$2"; b="$(basename "$s")"
  [ -f "$s" ] || fail "PLACE_SRC_MISSING $s"
  [ -d "$d" ] || fail "PLACE_DESTDIR_MISSING $d (override INIT_CFG_DIR/SCRIPT_DIR for this board)"
  [ -e "$d/$b" ] && cp -a "$d/$b" "$BACKUP/$b.orig" 2>/dev/null
  echo "$d/$b" >> "$BACKUP/placed.list"
  cp -a "$s" "$d/$b" || fail "PLACE_CP $d/$b"
  chown 0:0 "$d/$b" 2>/dev/null; chmod 0550 "$d/$b" 2>/dev/null
  chcon u:object_r:system_etc_file:s0 "$d/$b" 2>/dev/null || log "WARN chcon $d/$b (verify context)"
}
place "$DEPLOY/scripts/westlake-u13-recover.sh"      "$SCRIPT_DIR"
[ "$WITH_BOAT" = 1 ] && place "$DEPLOY/scripts/westlake-u13-boat-overlay.sh" "$SCRIPT_DIR"
place "$DEPLOY/init/00_westlake_u13_recover.cfg"     "$INIT_CFG_DIR"

# --- 5. lock down durable root, re-verify ----------------------------------
chmod -R go-w "$ROOT" 2>/dev/null; chmod 0444 "$ROOT/u13-recover-table.json" "$TSV" 2>/dev/null
rm -f "$ROOT/DISABLED" 2>/dev/null   # install implies enabled
rm -f "$ROOT/.layers.plan" 2>/dev/null
# re-verify placements exist + readable
PLACED="$SCRIPT_DIR/westlake-u13-recover.sh $INIT_CFG_DIR/00_westlake_u13_recover.cfg"
[ "$WITH_BOAT" = 1 ] && PLACED="$PLACED $SCRIPT_DIR/westlake-u13-boat-overlay.sh"
for f in $PLACED; do
  [ -r "$f" ] || fail "POST_VERIFY_MISSING $f"
done
[ -s "$BACKUP/superseded.list" ] && log "superseded owners: $(sed -e ':a' -e 'N' -e '$!ba' -e 's/\n/ /g' "$BACKUP/superseded.list")"
root_ro   # re-seal / (trap is the safety net)
log "ok. scripts@$SCRIPT_DIR  cfg@$INIT_CFG_DIR  durable@$ROOT (archive=$ARCH boat=$BARCH)"
log "cfg context: $(ls -Z "$INIT_CFG_DIR/00_westlake_u13_recover.cfg" 2>/dev/null | cut -d' ' -f1) (want u:object_r:system_etc_file:s0)"
log "NEXT (board step): reboot without Mac -> read-only verify 319 fingerprint + appspawn-x + tap HelloWorld/ZigZag/BoatAttack."
echo "INSTALL_OK"
