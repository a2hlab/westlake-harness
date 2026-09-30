#!/bin/bash
# T6 board L2 test (specs/dex2oat-once/t6-board-l2.spec.md) — offline-authored, runs in ONE
# command when a board reconnects. Overlays T5's 27 boot-image files (resident libart
# UNTOUCHED), restarts appspawn-x via begetctl (NEVER kill -9), runs HW/ZZ + 5 lit apps,
# checks for CheckSystemClass abort, pulls cppcrash on abort, then rolls back to U2 and
# verifies the runtime fingerprint. Whole window <= 30 min.
#
# Usage:
#   t6_board_test.sh --serial <sn> --image-dir <T5-out-with-27-files+boot-image-inputs.sha256> [--dry-run]
#
# --dry-run: validate args + print the plan, touch NO board (for offline review).
#
# SAFETY (project.spec + T6 boundary):
#   - resident libart is NOT overlaid; only the 27 image files under arm64/ are bind-mounted.
#   - appspawn-x: begetctl stop_service/start_service + socket owner fix ONLY; never kill -9.
#   - bind-mount overlay is trivially reversible (umount) => exact-byte rollback, no /system rw.
#   - end: umount all, restart appspawn-x, verify runtime fingerprint == expected U2 value.
#   - whitelist-only serial; window guard 30 min.
set -u
# ---------------- config ----------------
HDC="${HDC:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}"
LANE="${LANE:-cc-wiki}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # no user-bound absolute paths (AGENTS.md)
. "$REPO/scripts/lab/lab_paths.sh" || exit 1                # sets WORKSPACES; the board lives in the main checkout, not a lane worktree
BOARD_MD="${BOARD_MD:-$WORKSPACES/westlake-harness/.octos/boards/app-lighting.md}"
BOARD_NOTE="${BOARD_NOTE:-$REPO/scripts/lab/board_note.sh}"
BMS_BATCH="${BMS_BATCH:-$REPO/benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py}"
EXPECT_FP="${EXPECT_FP:-0b81cdbe0ed9}"          # U3 runtime fingerprint (rollback target; override via env or bms_batch facts)
FW=/system/android/framework
ARM64=$FW/arm64
APPSPAWN_SVC="${APPSPAWN_SVC:-appspawn-x}"        # begetctl service name (confirmed on 5cd 2026-09-30: begetctl {stop,start}_service appspawn-x)
SOCK="${SOCK:-/dev/unix/socket/AppSpawnX}"        # appspawn socket; owner/mode/label reset on every restart (deploy_generation.py:261)
# HW + ZZ + 5 reliably-lit U2 apps (adjust to the live U2 lit list at run time):
APPS="${APPS:-helloworld,zigzag,fd-droidify,fd-auxio,aegis,fd-calendar,ooniprobe}"
WIN_SECS=1800

SERIAL=""; IMGDIR=""; DRY=0
while [ $# -gt 0 ]; do case "$1" in
  --serial) SERIAL="$2"; shift 2;;
  --image-dir) IMGDIR="$2"; shift 2;;
  --dry-run) DRY=1; shift;;
  *) echo "unknown arg: $1"; exit 2;;
esac; done
[ -n "$SERIAL" ] && [ -n "$IMGDIR" ] || { echo "usage: t6_board_test.sh --serial <sn> --image-dir <dir> [--dry-run]"; exit 2; }

OUT="$(cd "$(dirname "$0")" && pwd)/runs/t6-$SERIAL-$(date +%Y%m%dT%H%M%S)"
SHA_MANIFEST="$IMGDIR/boot-image-inputs.sha256"

log(){ echo "[t6] $*"; }
hdc(){ "$HDC" -t "$SERIAL" "$@"; }

# ---- appspawn-x lifecycle (mirrors deploy_generation.py: begetctl {stop,start}_service + socket fix) ----
# NEVER kill -9 the uid=0 appspawn-x parent: OH init CheckOndemandService NULL-derefs (SEGV@0x34) and the
# whole board wedges (RUNBOOK L12). Cold-stop only the uid!=0 app CHILDREN, then begetctl stop_service.
# NOTE: the board shell has NO awk — parse ps with grep -c (an awk parent-up check silently returns an
# error string, which made the first scripted run mis-report REJECTED). Count uid=0 (root) appspawn-x lines.
appspawn_parent_up(){ hdc shell "ps -ef | grep appspawn-x | grep -v grep | grep -c root" 2>/dev/null | tr -d '\r'; }
coldstop_children(){
  # SIGTERM every appspawn-x process whose user column is NOT root (= forked app instances). Parent untouched.
  hdc shell 'ps -ef | grep appspawn-x | grep -v grep | while read u pid rest; do [ "$u" != root ] && kill "$pid" 2>/dev/null; done' 2>/dev/null
  sleep 1
}
socket_fix(){
  hdc shell "chown 0:6005 $SOCK && chmod 0660 $SOCK && chcon u:object_r:appspawn_socket:s0 $SOCK" 2>/dev/null
  hdc shell "stat -c '%a:%u:%g:%C' $SOCK" 2>/dev/null | tr -d '\r'
}
appspawn_stop(){ coldstop_children; hdc shell "begetctl stop_service $APPSPAWN_SVC" 2>/dev/null; sleep 2; }
appspawn_start(){
  hdc shell "begetctl start_service $APPSPAWN_SVC" 2>/dev/null; sleep 3
  local s; s=$(socket_fix)
  log "appspawn-x parent up=$(appspawn_parent_up) socket=$s (want 660:0:6005:u:object_r:appspawn_socket:s0)"
}

# ---------------- 0. offline validation (always) ----------------
[ -f "$SHA_MANIFEST" ] || { echo "MISSING $SHA_MANIFEST (T5 output not ready?)"; exit 3; }
# the 27 image files = the arm64/*.{art,oat,vdex} rows of the manifest
IMG_FILES=$(awk '{print $2}' "$SHA_MANIFEST" | grep -E '^arm64/.*\.(art|oat|vdex)$')
NIMG=$(echo "$IMG_FILES" | grep -c .)
log "image files in manifest: $NIMG (expect 27)"
miss=0
for rel in $IMG_FILES; do [ -f "$IMGDIR/$rel" ] || { echo "MISSING image file: $IMGDIR/$rel"; miss=$((miss+1)); }; done
[ "$miss" = 0 ] || { echo "FAIL: $miss image files missing from $IMGDIR"; exit 3; }
# L1 verify: the provided files match the reference manifest sha256
( cd "$IMGDIR" && shasum -a 256 -c "$SHA_MANIFEST" >/dev/null 2>&1 ) && log "L1: 27 files match boot-image-inputs.sha256" || log "WARN: files differ from reference sha256 (new build = expected; recorded)"

if [ "$DRY" = 1 ]; then
  log "DRY-RUN plan:"
  log "  lock $SERIAL ($LANE); preflight boot_id + runtime fingerprint (expect $EXPECT_FP)"
  log "  backup resident 27 files (sha + copy to /data/local/tmp/t6-backup) [read-only capture]"
  log "  begetctl stop_service $APPSPAWN_SVC  (NO kill -9)"
  log "  bind-mount T5 27 files over $ARM64/*  (libart untouched)"
  log "  fix appspawn socket owner; begetctl start_service $APPSPAWN_SVC"
  log "  bms_batch --keys $APPS --hilog 20 --shots 5,20  -> facts + hilogs to $OUT"
  log "  grep facts/hilog for 'CheckSystemClass' abort; on abort pull /data/log/faultlog/temp/*"
  log "  rollback: stop appspawn-x; umount all binds; start appspawn-x; verify fp==$EXPECT_FP; unlock"
  log "DRY-RUN ok (no board touched)."
  exit 0
fi

# ---------------- 1. preflight (read-only) + lock ----------------
mkdir -p "$OUT"
hdc shell "echo alive" 2>/dev/null | grep -q alive || { echo "board $SERIAL not reachable"; exit 4; }
BOOT0=$(hdc shell "cat /proc/sys/kernel/random/boot_id" 2>/dev/null | tr -d '\r')
log "boot_id=$BOOT0"
"$BOARD_NOTE" lock "$BOARD_MD" "$SERIAL" "$LANE" "T6 dex2oat L2: overlay 27 boot-image files, HW/ZZ+5, rollback to U2" || { echo "lock failed/busy"; exit 5; }
START=$(date +%s)
guard(){ [ $(( $(date +%s) - START )) -lt $WIN_SECS ] || { echo "WINDOW EXCEEDED -> forcing rollback"; rollback; exit 9; }; }

# ---------------- 2. backup resident 27 files (read-only capture) ----------------
hdc shell "mkdir -p /data/local/tmp/t6-backup/arm64" 2>/dev/null
hdc shell "cd $ARM64 && sha256sum *.art *.oat *.vdex 2>/dev/null" > "$OUT/resident-before.sha256"
for rel in $IMG_FILES; do bn=$(basename "$rel"); hdc shell "cp -a $ARM64/$bn /data/local/tmp/t6-backup/arm64/$bn" 2>/dev/null; done
log "backed up resident 27 files (hashes: $OUT/resident-before.sha256)"

# ---------------- 3. stage T5 files on board ----------------
hdc shell "mkdir -p /data/local/tmp/t6-new/arm64" 2>/dev/null
for rel in $IMG_FILES; do bn=$(basename "$rel"); hdc file send "$IMGDIR/$rel" /data/local/tmp/t6-new/arm64/$bn >/dev/null 2>&1; done

rollback(){
  log "ROLLBACK"
  appspawn_stop
  for rel in $IMG_FILES; do bn=$(basename "$rel"); hdc shell "umount $ARM64/$bn 2>/dev/null"; done
  appspawn_start
  FP1=$(runtime_fp)
  log "post-rollback runtime fingerprint=$FP1 (expect $EXPECT_FP)"
  hdc shell "cd $ARM64 && sha256sum *.art *.oat *.vdex 2>/dev/null" > "$OUT/resident-after.sha256"
  if diff -q "$OUT/resident-before.sha256" "$OUT/resident-after.sha256" >/dev/null 2>&1; then log "resident 27 files restored byte-identical"; else echo "WARN resident files differ after rollback — see $OUT"; fi
  "$BOARD_NOTE" unlock "$BOARD_MD" "$SERIAL" "$LANE"
}
runtime_fp(){ hdc shell "cat /data/local/tmp/asx/runtime-fingerprint.txt 2>/dev/null" 2>/dev/null | grep -oE '[0-9a-f]{12}' | head -1; }

# ---- RB discriminative-experiment evidence capture ----
# Root cause hypothesis (cx-bms T5 2/3, board ACK 21:38): board R155 ART built ART_USE_READ_BARRIER=false
# (kv concurrent-copying=false); our T5 image kv concurrent-copying=true. ImageSpace::ValidateOatFile
# (image_space.cc:3445-3451) returns false when IsConcurrentCopying != gUseReadBarrier. PREDICTED result:
# R155 libart REJECTS this image at the appspawn-x/zygote boot-image load. Capture the verbatim reject
# log + any faultlog either way (dispatch: "faultlog 原文拉回").
RB_TERMS='rb_mismatch|read.?barrier|concurrent.?copying|ValidateOatFile|VOF_IN|CheckSystemClass|not compatible|image space|boot image|checksum|Runtime aborting|Could not create|Failed to.*image|gUseReadBarrier'
capture_evidence(){
  local tag="$1"
  hdc shell "hilog -x 2>/dev/null" > "$OUT/hilog-$tag.txt" 2>/dev/null
  grep -iE "$RB_TERMS" "$OUT/hilog-$tag.txt" 2>/dev/null | tail -120 > "$OUT/rb-hits-$tag.txt"
  hdc shell "ls -t /data/log/faultlog/temp/ 2>/dev/null | head -8" > "$OUT/faultlog-$tag.list" 2>/dev/null
  hdc shell "cd /data/log/faultlog/temp && tar -c \$(ls -t 2>/dev/null | head -8) 2>/dev/null" > "$OUT/faultlog-$tag.tar" 2>/dev/null
  log "  evidence[$tag]: rb/mismatch hilog hits=$(wc -l < "$OUT/rb-hits-$tag.txt" 2>/dev/null | tr -d ' ') faultlogs=$(grep -c . "$OUT/faultlog-$tag.list" 2>/dev/null || echo 0)"
}

# ---------------- 4. overlay (bind-mount; libart NOT touched) ----------------
guard
hdc shell "hilog -r" 2>/dev/null   # clear buffer BEFORE the restart; hilog -x otherwise returns a stale buffer that misses it
appspawn_stop
for rel in $IMG_FILES; do bn=$(basename "$rel"); hdc shell "mount --bind /data/local/tmp/t6-new/arm64/$bn $ARM64/$bn" 2>/dev/null; done
appspawn_start
sleep 2
capture_evidence overlay
PARENT_UP=$(appspawn_parent_up)
if [ "$PARENT_UP" != 1 ]; then
  REJECTED=1
  log "PREDICTED OUTCOME: appspawn-x parent did NOT load the T5 (read-barrier-ON) image."
  log "  => R155 libart (read-barrier-OFF) rejected it. See rb-hits-overlay.txt / faultlog-overlay.tar."
else
  REJECTED=0
  log "UNEXPECTED: appspawn-x parent ALIVE under T5 (RB-ON) image -> running HW/ZZ to see if apps spawn."
fi

# ---------------- 5. run HW/ZZ only if the image was accepted ----------------
if [ "$REJECTED" = 0 ]; then
  guard
  python3 "$BMS_BATCH" --manifest "$(dirname "$BMS_BATCH")/apps.json" --serial "$SERIAL" --lane "$LANE" \
    --hdc-cmd "$HDC" --keys "$APPS" --hilog 20 --shots 5,20 --execute --out "$OUT/batch" --run-id "t6" >/dev/null 2>&1
  capture_evidence postrun
  find "$OUT/batch" -name facts.txt -exec cat {} \; > "$OUT/facts.txt" 2>/dev/null
  log "facts:"; cat "$OUT/facts.txt" 2>/dev/null | grep -E 'alive|TOTAL|RUNTIME'
fi

# ---------------- 6. classify outcome ----------------
ABORT=$(grep -rlE 'CheckSystemClass' "$OUT/batch" 2>/dev/null | head -1)
RBHIT=$(cat "$OUT"/rb-hits-*.txt 2>/dev/null | grep -iE 'rb_mismatch|concurrent.?copying|read.?barrier|ValidateOatFile|gUseReadBarrier' | head -1)

# ---------------- 7. rollback + verify + unlock ----------------
rollback
if [ "${REJECTED:-1}" = 1 ]; then
  VERDICT="IMAGE REJECTED (predicted): appspawn-x could not load T5 RB-ON image under RB-OFF R155 libart"
elif [ -n "$ABORT" ]; then
  VERDICT="CheckSystemClass ABORT while running apps (cppcrash pulled)"
else
  VERDICT="image ACCEPTED + apps ran (UNEXPECTED given RB mismatch; read t20 for own-UI, human review per d6)"
fi
log "T6(discriminative) done. REJECTED=${REJECTED:-1} rb_hit=${RBHIT:-none}"
log "VERDICT: $VERDICT"
