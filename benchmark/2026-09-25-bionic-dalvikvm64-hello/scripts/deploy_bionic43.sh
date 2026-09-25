#!/usr/bin/env bash
# #43 one-shot deploy: assemble the EXACT on-board layout from the VM stage + scripts/
# and push it to /data/local/tmp/bionic43 on the board. Everything that was previously
# placed by hand (apex/ roots, ICU/tz copies, emptied public.libraries.txt, ld.config.txt,
# run.sh) is produced here, so the board layout is 100% reproducible.
#
# Runs on the Mac (needs hdc); uses `orb -m a2hlab` for the VM-side assembly/tar.
# Writes only /data/local/tmp/bionic43. Does NOT run the VM; does NOT launch any app.
#
# usage: deploy_bionic43.sh [SERIAL]
#   SERIAL defaults to the #43 board. Set HDC=... to override the hdc path.
set -euo pipefail
SERIAL="${1:-5cd1e3dd00000000000000000923012c}"
HDC="${HDC:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}"
VMDIR="${VMDIR:-\$HOME/a2hlab/bionic43}"      # VM path (expanded inside orb)
RD=/data/local/tmp/bionic43

echo "== [VM] assemble the complete layout under stage/ from raw pieces + scripts/ =="
orb -m a2hlab bash -lc '
set -euo pipefail
B='"$VMDIR"'
S="$B/stage"
# base pieces must already exist (produced by resolve.py + extraction; see README)
for p in linker64 bin/dalvikvm64 lib64 framework/arm64 bcp icu/icudt72l.dat tz/tzdata hello.jar; do
  [ -e "$S/$p" ] || { echo "MISSING base piece: $S/$p" >&2; exit 3; }
done
# --- overlay that used to be manual ---
mkdir -p "$S/apex/com.android.art" \
         "$S/apex/com.android.i18n/etc/icu" \
         "$S/apex/com.android.tzdata/etc/tz" \
         "$S/system/etc" "$S/data"
cp -f "$S/icu/icudt72l.dat" "$S/apex/com.android.i18n/etc/icu/icudt72l.dat"
cp -f "$S/tz/tzdata"        "$S/apex/com.android.tzdata/etc/tz/tzdata"
printf "# empty for #43 java hello (no NDK public libs needed)\n" > "$S/system/etc/public.libraries.txt"
cp -f "$B/ld.config.txt"     "$S/ld.config.txt"
cp -f "$B/run_bionic43.sh"   "$S/run.sh"
# --- pack ---
cd "$S" && tar czf "$B/deploy.tar.gz" .
echo "packed: $(du -h "$B/deploy.tar.gz" | cut -f1)"
'

echo "== [board] push + extract to $RD (only /data/local/tmp is written) =="
"$HDC" -t "$SERIAL" shell "rm -rf $RD $RD.tar.gz; mkdir -p $RD"
"$HDC" -t "$SERIAL" file send "$HOME/OrbStack/a2hlab/home/zhaoyue/a2hlab/bionic43/deploy.tar.gz" "$RD.tar.gz"
"$HDC" -t "$SERIAL" shell "cd $RD && tar xzf ../bionic43.tar.gz 2>/dev/null || tar xzf $RD.tar.gz; rm -f $RD.tar.gz; chmod -R 755 $RD"

echo "== [board] verify layout =="
"$HDC" -t "$SERIAL" shell "cd $RD && echo 'top:' && ls && echo 'apex:' && ls apex && \
  echo 'i18n icu:' && ls apex/com.android.i18n/etc/icu && \
  echo 'tz:' && ls apex/com.android.tzdata/etc/tz && \
  echo 'public.libraries.txt:' && cat system/etc/public.libraries.txt && \
  echo 'boot files:' && ls framework/arm64 | wc -l && \
  echo 'libs:' && ls lib64 | wc -l && echo 'bcp:' && ls bcp | wc -l"
echo "== done. run with:  hdc -t $SERIAL shell 'cd $RD && sh run.sh'  (check pidof com.ss.android.article.news is empty first) =="
