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
# RECOVER_VARIANT selects the recover script+cfg to place. Default v2 = sealed-Enforcing recover (unchanged).
# v3 = recover + a default-OFF permissive opt-in switch (needs user approval; see benchmark/2026-10-10-permissive-switch).
RECOVER_VARIANT=${RECOVER_VARIANT:-v2}
case "$RECOVER_VARIANT" in
  v2) RECOVER_SCRIPT=westlake-u13-recover.sh;    RECOVER_CFG=00_westlake_u13_recover.cfg ;;
  v3) RECOVER_SCRIPT=westlake-u13-recover-v3.sh; RECOVER_CFG=00_westlake_u13_recover-v3.cfg ;;
  *)  fail "RECOVER_VARIANT must be v2 or v3 (got $RECOVER_VARIANT)" ;;
esac

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
# [cc-t3 #91 fail-closed guard, 2026-10-10 incident] NEVER run on an ALREADY-RECOVERED board. Step 2 archives the
# 56 layers incl. the /system/android directory; when recover's binds are live, that archive deleted the UNBOUND
# physical base (/system/android lost ~200 files on a recovered 5ea). Recover must be OFF (DISABLED) and the board
# bare-rebooted (no binds) before installing. Refuse fail-closed otherwise, naming the required remedy.
if grep -qE ' /system/android[/ ]' /proc/mounts 2>/dev/null; then
  fail "RECOVERED_BOARD recover binds are live (/proc/mounts has /system/android). DISABLE autostart (touch $ROOT/DISABLED or westlake-u13-autostart-disable.sh) + bare reboot, THEN install (else the archive deletes the unbound base)."
fi
_cur_boot=$(cat /proc/sys/kernel/random/boot_id 2>/dev/null)
if [ -f "$ROOT/receipt.env" ]; then
  _rstate=$(sed -n 's/^state=//p' "$ROOT/receipt.env"); _rboot=$(sed -n 's/^boot_id=//p' "$ROOT/receipt.env")
  if [ "$_rstate" = READY ] && [ -n "$_cur_boot" ] && [ "$_rboot" = "$_cur_boot" ]; then
    fail "RECOVERED_BOARD receipt.env state=READY for THIS boot ($_cur_boot). DISABLE autostart + bare reboot before install."
  fi
fi
[ -d /data/app/el1/bundle/public ] || fail DATA_PKG_ROOT_NOT_READY
[ -f "$TABLE_SRC" ] || fail "MISSING_TABLE $TABLE_SRC"
# A bare boot (DISABLED then target boot) has, by design, NO appspawn-x parent yet. ALLOW_NO_PARENT=1 lets the
# installer run in that bare-boot "install for next boot only" case; default still fails. The appspawn-x SHA gate
# below is UNCHANGED. Source: westlake-harness-tools-inventory/benchmark/2026-10-10-5ea-u13-restore/v2/allow-no-parent.patch
# (proven on 5ea v2 restore); cx-t0 hit APPSPAWN_NOT_RUNNING on 5cd bare boot 2026-10-10 19:30:58.
pid=$(pidof appspawn-x 2>/dev/null)
if [ -z "$pid" ]; then
  [ "${ALLOW_NO_PARENT:-0}" = 1 ] || fail APPSPAWN_NOT_RUNNING
  log "ALLOW_NO_PARENT=1: install for next boot only; parent gate skipped"
fi
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
    # [cc-t3 #91 2026-10-10 SECOND fail-closed guard — bare-boot empty-base incident on 5ea]
    # A bare boot drops recover's bind, so a physical dir target (e.g. /system/android <- sources/seq1)
    # can be EMPTY/degraded while a GOOD archive from a prior install still exists. The step below used to
    # rm -rf the archive then copy the empty dir -> it destroyed the only good base. The first guard only
    # catches a LIVE bind / READY receipt, not a bare-boot empty physical target. So: NEVER overwrite an
    # existing archive with a physical target that has FEWER files — reuse the preserved archive instead
    # (recover binds from it); refuse outright if neither physical nor archive has a usable base.
    cur_files=$(find "$target" -type f 2>/dev/null | sed -n '$='); cur_files=$((cur_files + 0))
    arch_files=0; [ -d "$dst" ] && { arch_files=$(find "$dst" -type f 2>/dev/null | sed -n '$='); arch_files=$((arch_files + 0)); }
    # Never archive an EMPTY or SHRUNKEN physical dir over a good archive: that is the bare-boot bind-gone
    # state that destroyed the base. If a LARGER archive exists, reuse it; if the physical is empty and
    # there is no larger archive, refuse (no good base to archive or reuse).
    if [ "$cur_files" -lt "$arch_files" ]; then
      log "REUSE_ARCHIVE seq=$seq $target: physical=$cur_files files < existing archive=$arch_files (bare-boot bind-gone); keeping existing archive seq$seq, NOT overwriting"
      printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$seq" "$kind" "$group" "$target" "$dst" "reused" >> "$TSV.tmp"
      continue
    fi
    [ "$cur_files" -gt 0 ] || fail "LIVE_TARGET_EMPTY seq=$seq $target has $cur_files files (archive=$arch_files); a bare-boot bind-gone base cannot be archived and there is no larger archive to reuse — restore the base first"
    /bin/rm -rf "$dst"; mkdir -p "$dst" || fail "MKARCH seq=$seq"
    cp -a "$target/." "$dst/" 2>/dev/null || fail "ARCHIVE_DIR seq=$seq $target"
    aline="$dst"; shaout=""
  else
    # [cc-t3 #91 2026-10-10 FILE version of the bare-boot archive-destroy incident — cx-t0 19:33:32 readonly proof:
    #  benchmark/2026-10-10-5cd-demo-regression/boat-full128/bare-file-layer-readonly/results.json: after a bare boot
    #  all 53 kind=file physical targets != signed SHA while sources/seqN == signed. The old 'cp -a target dst THEN
    #  check ARCHIVE_SHA' overwrote the GOOD archive with the stale physical file and only then failed -> destroyed
    #  it (file version of the 5ea incident). So NEVER write $dst before deciding, symmetric with the dir branch:]
    if [ -n "$sha_want" ] && [ -f "$dst" ] && [ "$(sha "$dst")" = "$sha_want" ]; then
      # (1) archive already == signed -> reuse it, copy nothing. TSV keeps the real signed sha so recover.sh's
      #     SHA gate still verifies the reused archive (a literal "reused" there would break recover's file check).
      log "REUSE_ARCHIVE_FILE seq=$seq $target: existing archive seq$seq already == signed; NOT overwriting (reused)"
      aline="$dst"; shaout="$sha_want"
    elif [ -n "$sha_want" ] && [ "$(sha "$target")" = "$sha_want" ]; then
      # (2) physical target is the signed byte -> safe to archive it, then re-verify.
      cp -a "$target" "$dst" 2>/dev/null || fail "ARCHIVE_FILE seq=$seq $target"
      got=$(sha "$dst"); [ "$got" = "$sha_want" ] || fail "ARCHIVE_SHA seq=$seq want=$sha_want got=$got"
      aline="$dst"; shaout="$sha_want"
    else
      # (3) neither archive nor physical is the signed byte -> refuse, $dst untouched.
      fail "ARCHIVE_SOURCE_UNSIGNED seq=$seq target=$target want=$sha_want got=$(sha "$target") (dst untouched)"
    fi
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
  bn=$(basename "$old"); [ "$bn" = "$RECOVER_CFG" ] && continue
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
place "$DEPLOY/scripts/$RECOVER_SCRIPT"              "$SCRIPT_DIR"
[ "$WITH_BOAT" = 1 ] && place "$DEPLOY/scripts/westlake-u13-boat-overlay.sh" "$SCRIPT_DIR"
place "$DEPLOY/init/$RECOVER_CFG"                    "$INIT_CFG_DIR"

# --- 5. lock down durable root, re-verify ----------------------------------
chmod -R go-w "$ROOT" 2>/dev/null; chmod 0444 "$ROOT/u13-recover-table.json" "$TSV" 2>/dev/null
rm -f "$ROOT/DISABLED" 2>/dev/null   # install implies enabled
rm -f "$ROOT/.layers.plan" 2>/dev/null
# re-verify placements exist + readable
PLACED="$SCRIPT_DIR/$RECOVER_SCRIPT $INIT_CFG_DIR/$RECOVER_CFG"
[ "$WITH_BOAT" = 1 ] && PLACED="$PLACED $SCRIPT_DIR/westlake-u13-boat-overlay.sh"
for f in $PLACED; do
  [ -r "$f" ] || fail "POST_VERIFY_MISSING $f"
done
[ -s "$BACKUP/superseded.list" ] && log "superseded owners: $(sed -e ':a' -e 'N' -e '$!ba' -e 's/\n/ /g' "$BACKUP/superseded.list")"
root_ro   # re-seal / (trap is the safety net)
log "ok. scripts@$SCRIPT_DIR  cfg@$INIT_CFG_DIR  durable@$ROOT (archive=$ARCH boat=$BARCH)"
log "cfg context: $(ls -Z "$INIT_CFG_DIR/$RECOVER_CFG" 2>/dev/null | cut -d' ' -f1) (want u:object_r:system_etc_file:s0)  variant=$RECOVER_VARIANT"
log "NEXT (board step): reboot without Mac -> read-only verify 319 fingerprint + appspawn-x + tap HelloWorld/ZigZag/BoatAttack."
echo "INSTALL_OK"
