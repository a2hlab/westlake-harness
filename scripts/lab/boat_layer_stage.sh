#!/usr/bin/env bash
# boat_layer_stage.sh — installer-free Boat-layer staging for a board already on v2.
#
# WHY THIS EXISTS (cc-t3 #91, 2026-10-10): the U13 autostart installer re-archives /system/android
# (its step 2) and, on an already-recovered board, deleted the unbound physical base — the 5ea incident.
# The Boat overlay, however, is a SEPARATE init job (cfg param sys.westlake.demo.u13.ready ->
# westlake-u13-boat-overlay.sh) that only reads $ROOT/sources-boat and binds over the restored base.
# So the Boat layer can be added/removed WITHOUT the installer, WITHOUT touching sources/seq1, and
# WITHOUT remounting /system: just stage (or remove) the 6 source files under $ROOT/sources-boat and
# reboot. The on-board boat-overlay job does the binds on the next boot; recover (seq1) is untouched.
#
# This script is a Mac-side orchestrator over hdc. It is DRY-RUN BY DEFAULT: it prints the exact plan
# and only mutates the board with --execute. It refuses to run if the board's recover cfg does not
# already carry the boat job (it never edits the cfg). It is used by:
#   (1) 5cd: full-128 regression WITH the Boat layer (after the cx-t0 baseline);
#   (2) 61b: v2 re-seal (after v1 is frozen) — stage + one reboot.
#
# HARD INVARIANTS (also pinned by scripts/lab/test_boat_layer_stage.py):
#   * never writes/deletes/archives $ROOT/sources or sources/seq1 (the U13 base archive);
#   * never invokes the installer (install-westlake-u13-autostart*);
#   * never remounts /system (no `mount -o remount` / `mount -o rw` of /system);
#   * never calls setenforce;
#   * forward never removes sources-boat; reverse never adds it;
#   * it reboots nothing itself — it only PRINTS the `hdc ... target boot` to run.
#
# Usage:
#   boat_layer_stage.sh --serial <sn> --src <boat-artifacts-dir> [--execute]           # stage (dry-run default)
#   boat_layer_stage.sh --serial <sn> --reverse [--execute]                            # remove the staged layer
#   boat_layer_stage.sh --serial <sn> --src <dir> --hdc "/path/to/hdc" --execute       # explicit hdc
#
# <boat-artifacts-dir> must hold the 6 signed Boat files (SHA-gated below).
set -euo pipefail
LC_ALL=C; export LC_ALL

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
# shellcheck source=/dev/null
. "$HERE/lab_paths.sh" || { echo "FAIL cannot source lab_paths.sh" >&2; exit 2; }
RECIPE="$HERE/selinux_label_recipe.sh"

ROOT=/data/westlake-demo/u13            # the U13 demo root on the board (holds sources/, sources-boat/)
BARCH="$ROOT/sources-boat"              # the ONLY board dir this script writes to (forward)
SEQ1="$ROOT/sources/seq1"              # the U13 base archive — this script MUST NOT touch it
CFG=/system/etc/init/00_westlake_u13_recover.cfg
BOAT_JOB=westlake-u13-boat-overlay      # the init service/param that applies the overlay on boot

HDC=${HDC:-hdc}
SERIAL=""; SRC=""; MODE=stage; EXECUTE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --serial) SERIAL=${2:?}; shift 2 ;;
    --src)    SRC=${2:?};    shift 2 ;;
    --hdc)    HDC=${2:?};    shift 2 ;;
    --root)   ROOT=${2:?}; BARCH="$ROOT/sources-boat"; SEQ1="$ROOT/sources/seq1"; shift 2 ;;
    --reverse) MODE=reverse; shift ;;
    --execute) EXECUTE=1; shift ;;
    --dry-run) EXECUTE=0; shift ;;
    -h|--help) sed -n '1,40p' "$0"; exit 0 ;;
    *) echo "FAIL unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -n "$SERIAL" ] || { echo "FAIL --serial required" >&2; exit 2; }

# The 6 signed Boat source files: name<TAB>sha256<TAB>bind-target (target drives the single-recipe label).
# SHAs are cross-checked against the payload by test_boat_layer_stage.py so they cannot silently drift.
BUNDLE=com.Unity3d.BoatAttackDay
LIBD="/data/app/el1/bundle/public/$BUNDLE/android/lib/arm64-v8a"
BOAT_FILES="\
liboh_adapter_bridge.so	8ab85446f8b386c4a649576326d5f393669b3a22529874fb673eea7c3b1cd71e	/system/android/lib64/liboh_adapter_bridge.so
oh-adapter-runtime.jar	6333bcab4ca2daad03965712deac6adf028a6ff0dfac04fc8ea91af177828852	/system/android/framework/oh-adapter-runtime.jar
liboh_android_runtime.so	adc125f4dfb800c25d80e7d73216c8885fd64a31c6b91f064494166c63a59130	/system/android/lib64/liboh_android_runtime.so
libunity.so	1bea0fae1e6e76db15f17fca2bfa91b9c303ce278d6a4dcfba6af233b68b64ac	$LIBD/libunity.so
libil2cpp.so	f6b806b5c55e702b98caa2e85d2f9afb678bc47dcc4067017b33f5269afed746	$LIBD/libil2cpp.so
libwestlake_bionic_signal_box.so	7a931c79c0be28468bdd02a626a637431f2447f5fd0aba87176e5acdb071f5da	$LIBD/libwestlake_bionic_signal_box.so"

say(){ printf '%s\n' "$*"; }
plan(){ printf 'PLAN  %s\n' "$*"; }        # dry-run line
act(){  printf 'EXEC  %s\n' "$*"; }        # executed line
dev(){ "$HDC" -t "$SERIAL" shell "$1" 2>/dev/null | tr -d '\r'; }    # read-only board query
recipe_label(){ sh "$RECIPE" context "$1"; }                         # single recipe = source of truth

local_sha(){ shasum -a 256 "$1" 2>/dev/null | cut -d' ' -f1; }

# --- preflight: board reachable + is a v2 board that ALREADY carries the boat job (never edit the cfg) ---
preflight(){
  local up; up=$(dev 'echo up' || true)
  [ "$up" = up ] || { echo "FAIL board $SERIAL unreachable" >&2; exit 3; }
  local cfg; cfg=$(dev "cat $CFG 2>/dev/null" || true)
  [ -n "$cfg" ] || { echo "FAIL recover cfg $CFG absent -> not a v2 board; refusing (install v2 first)" >&2; exit 3; }
  if ! printf '%s' "$cfg" | grep -q "$BOAT_JOB"; then
    echo "FAIL boat job '$BOAT_JOB' NOT present in $CFG. This script never edits the cfg." >&2
    echo "     Deploy a v2 payload whose cfg wires the boat-overlay job, then re-run." >&2
    exit 3
  fi
  say "OK board $SERIAL is v2 and carries the boat job ($BOAT_JOB) in $CFG"
  # safety echo: seq1 presence is informational only; we never write it.
  local n; n=$(dev "find $SEQ1 -type f 2>/dev/null | wc -l" | tr -d ' ')
  say "OK U13 base archive seq1 present (${n:-?} files) — this script will NOT touch it"
}

stage(){
  [ -n "$SRC" ] || { echo "FAIL --src <boat-artifacts-dir> required for staging" >&2; exit 2; }
  [ -d "$SRC" ] || { echo "FAIL --src dir not found: $SRC" >&2; exit 2; }
  preflight
  # 1) verify every source file exists + SHA matches (Mac-side) BEFORE any board write
  printf '%s\n' "$BOAT_FILES" | while IFS="$(printf '\t')" read -r name want target; do
    [ -n "$name" ] || continue
    local f="$SRC/$name"
    [ -f "$f" ] || { echo "FAIL BOAT_ARTIFACT_MISSING $f" >&2; exit 4; }
    local got; got=$(local_sha "$f")
    [ "$got" = "$want" ] || { echo "FAIL BOAT_ARTIFACT_SHA $name want=$want got=$got" >&2; exit 4; }
    say "OK src $name sha=$want"
  done
  say "---- staging plan ($BARCH) ----"
  if [ "$EXECUTE" -eq 1 ]; then act "mkdir -p $BARCH"; dev "mkdir -p $BARCH" >/dev/null; else plan "mkdir -p $BARCH"; fi
  printf '%s\n' "$BOAT_FILES" | while IFS="$(printf '\t')" read -r name want target; do
    [ -n "$name" ] || continue
    local label; label=$(recipe_label "$target")
    local dst="$BARCH/$name"
    if [ "$EXECUTE" -eq 1 ]; then
      act "send $name -> $dst ; chcon $label (recipe target=$target)"
      "$HDC" -t "$SERIAL" file send "$SRC/$name" "$dst" >/dev/null 2>&1 || { echo "FAIL send $name" >&2; exit 5; }
      local sgot; sgot=$(dev "sha256sum $dst 2>/dev/null | cut -d' ' -f1")
      [ "$sgot" = "$want" ] || { echo "FAIL STAGED_SHA $name want=$want got=$sgot" >&2; exit 5; }
      dev "chmod 0644 $dst && chcon $label $dst" >/dev/null || { echo "FAIL chcon $name" >&2; exit 5; }
    else
      plan "send $name -> $dst ; verify sha=$want ; chcon $label (recipe target=$target)"
    fi
  done
  if [ "$EXECUTE" -eq 1 ]; then
    say "DONE staged 6 Boat files into $BARCH (seq1 untouched, installer not called, /system not remounted)."
    say "NEXT: reboot to apply the Boat layer:  $HDC -t $SERIAL target boot"
  else
    say "DRY-RUN only. Re-run with --execute to stage, then: $HDC -t $SERIAL target boot"
  fi
}

reverse(){
  preflight
  local held="$BARCH.held-$(date +%Y%m%dT%H%M%S 2>/dev/null || echo manual)"
  if dev "[ -d $BARCH ] && echo yes" | grep -q yes; then
    if [ "$EXECUTE" -eq 1 ]; then
      act "mv $BARCH $held"
      dev "mv $BARCH $held" >/dev/null || { echo "FAIL mv sources-boat aside" >&2; exit 5; }
      say "DONE moved $BARCH -> $held (boat job will skip: MISSING_BOAT_SOURCES). seq1 untouched."
      say "NEXT: reboot to drop the Boat layer (pure base):  $HDC -t $SERIAL target boot"
    else
      plan "mv $BARCH $held   (boat-overlay then fails closed -> pure base on next boot)"
      say "DRY-RUN only. Re-run with --execute, then: $HDC -t $SERIAL target boot"
    fi
  else
    say "OK $BARCH already absent — boat layer not staged; nothing to reverse."
  fi
}

case "$MODE" in
  stage)   stage ;;
  reverse) reverse ;;
  *) echo "FAIL bad mode" >&2; exit 2 ;;
esac
