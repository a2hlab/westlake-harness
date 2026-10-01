#!/bin/bash
# read80-window.sh — #80 readout for the N10b board window over the 6 keys.
# Run AFTER N10b (setJavaVM + AssetManager field-offset + whatever #80 fix) is deployed and the overlay is
# active. Per key: launch once (bms --launch-only --execute), let it settle, do ONE sequential hdc read of the
# child's bridge maps, pull the per-key hilog, run read80.py --tsv. Prints a per-key table.
# RUNBOOK §1: single sequential hdc commands; NO concurrent /proc scans during a launch; NO hdc kill/start.
set -u
SER="${1:?serial}"; LANE=cc-wiki
HERE="$(cd "$(dirname "$0")" && pwd)"
# WORKSPACES = the ancestor holding westlake-harness/ + westlake-inputs/ (no user-specific abs path; gate
# check_user_paths.py). Walk up from this script, then let scripts/lab/lab_paths.sh validate + add lab_* homes.
_d="$HERE"; while [ "$_d" != / ] && [ ! -d "$_d/westlake-harness" ]; do _d="$(dirname "$_d")"; done; WORKSPACES="$_d"
. "$WORKSPACES/westlake-harness/scripts/lab/lab_paths.sh" || { echo "cannot source lab_paths.sh" >&2; exit 1; }
W="$WORKSPACES/westlake-harness"
NOTE="$WORKSPACES/westlake-inputs/tools/board_note.sh"
HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
BMS="$W/benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py"
MAN="$W/benchmark/2026-09-28-bms-route-deploy/batch/apps.json"
INPUT="${INPUT_ROOT:-$HOME/a2hlab/app-inputs}"
OUT="${OUT:-$WORKSPACES/_cc-wiki-read80}"; mkdir -p "$OUT"
# content package per key (for the live child uid -> maps read)
declare -A PKG=(
  [wikipedia]=org.wikipedia [fd-app]=com.unciv.app
  [fd-shatteredpixeldungeon]=com.shatteredpixel.shatteredpixeldungeon
  [flowitgame]=com.bytehamster.flowitgame [dddmodel2]=org.andresoviedo.dddmodel2
  [webrtc-check]=timur.webrtc.check )
KEYS="${KEYS:-wikipedia fd-app fd-shatteredpixeldungeon flowitgame dddmodel2 webrtc-check}"
[ "${WINDOW:-0}" = 1 ] || { echo "set WINDOW=1 to run a board window"; exit 3; }
hs(){ "$HDC" -t "$SER" shell "$1" 2>/dev/null | tr -d '\r'; }
trap '"$NOTE" unlock "$W/.octos/boards/app-lighting.md" "$SER" "$LANE"' EXIT
"$NOTE" lock "$W/.octos/boards/app-lighting.md" "$SER" "$LANE" "#80 read80 readout (N10b, 6 keys)" || { trap - EXIT; exit 5; }
"$HDC" -t "$SER" shell "power-shell wakeup; power-shell timeout -o 86400000" >/dev/null 2>&1; sleep 2

printf 'key\tverdict\tunknown\tsurf_ok\tsurf_empty\trescued\tff\tbridge\tdrew\n' | tee "$OUT/read80-table.tsv"
for k in $KEYS; do
  rd="$OUT/$k"; mkdir -p "$rd"
  # launch one key (no reinstall); bms waits ~t20 and pulls the per-key hilog
  python3 "$BMS" --execute --serial "$SER" --lane "$LANE" --manifest "$MAN" --input-root "$INPUT" \
    --keys "$k" --out "$rd/run" --shots 20 --hilog 20 --focus-check --launch-only \
    --hdc-cmd "$HDC" --lock-cmd "$NOTE" >"$rd/bms.log" 2>&1
  hilog=$(find "$rd/run" -path "*/$k/hilog.txt" | head -1)
  # ONE sequential maps read of the live child (uid -> ppid=appspawn-x child); no concurrent /proc scan
  uid=$(hs "bm dump -n ${PKG[$k]}" | grep -m1 '\"uid\"' | grep -oE '[0-9]+' | head -1)
  pid=$(hs "ps -A -o PID,UID,NAME | awk -v u=$uid '\$2==u{print \$1; exit}'")
  maps="$rd/child.maps.txt"
  [ -n "$pid" ] && hs "cat /proc/$pid/maps" > "$maps" || : > "$maps"
  python3 "$HERE/read80.py" --key "$k" --hilog "${hilog:-/dev/null}" --maps "$maps" --tsv | tee -a "$OUT/read80-table.tsv"
  hs "aa force-stop ${PKG[$k]}" >/dev/null
done
echo "table: $OUT/read80-table.tsv ; per-key maps+hilog under $OUT/<key>/"
