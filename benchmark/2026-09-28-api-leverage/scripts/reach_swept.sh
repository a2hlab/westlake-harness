#!/bin/bash
# Entry #12 worker (swept-first): only the 63 keys that have 09-27 sweep labels,
# because the ranking counts (startup_blocked/startup_lit) need lit/blocked labels.
# co-* commercial apps are unswept -> not required by entry #12 (out of scope).
W=${1:-?}
PY=~/reachenv/bin/python3
OUT=~/a2hlab/static/reach-20260928
SCANS=~/a2hlab/static/scans
INPUTS=~/a2hlab/app-inputs
RUNTIME=~/a2hlab/static/runtime-index.json
LOCKD=$OUT/.locks
mkdir -p "$LOCKD"
KEYS="wikipedia termux ooniprobe antennapod aegis fd-AppManager fd-auxio fd-com-amaze-filemanager fd-com-kunzisoft-keepass-libre fd-droidify fd-fitness fd-netguard fd-noice toutiao mcdonalds burgerking subwaysurfers firefox vlc localsend ppsspp mindustry markor opencamera anki newpipe fd-android fd-api fd-app fd-binaryeye fd-breezyweather fd-calendar fd-catima fd-client fd-etar fd-feeder fd-fennec_fdroid fd-filemanager fd-fluffychat fd-gallery fd-im-vector-app fd-immich fd-k9 fd-kitchenowl fd-libre fd-libretube fd-meet fd-minetest fd-mobile fd-mpv fd-musicplayer fd-notes fd-organicmaps fd-plus fd-reader fd-saber fd-seal fd-shatteredpixeldungeon fd-stk fd-tasks fd-tusky fd-tutanota fd-uhabits fd-wifianalyzer x noice"
for key in $KEYS; do
  scan_json="$SCANS/$key.json"
  [ -f "$scan_json" ] || continue
  out="$OUT/$key.reach.json"
  [ -s "$out" ] && continue
  mkdir "$LOCKD/$key" 2>/dev/null || continue
  apk=$(ls "$INPUTS/$key"/*.apk "$INPUTS/$key"/*.xapk "$INPUTS/$key"/*.apkm 2>/dev/null | head -1)
  if [ -z "$apk" ]; then echo "S$W SKIP $key (no apk)"; continue; fi
  if PYTHONPATH=~/reach-repo/harness timeout 900 $PY -m westlake_gap.cli startup-reach "$apk" \
      --runtime "$RUNTIME" --scan "$scan_json" --out "$out" >/dev/null 2>"$OUT/$key.reach.err"; then
    echo "S$W OK $key"
  else
    echo "S$W FAIL $key"
  fi
done
echo "S$W DONE"
