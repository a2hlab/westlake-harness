#!/bin/bash
# Board #17: Toutiao on the integrated build with a chosen WebView candidate, across the consent tap.
# Prints what decides the entry: does the process survive consent, does the SurfaceControl probe still
# fail, do the no-op entry points get called, and does the feed get article rows.
# usage: sc17_run.sh <serial> <framework-report (VM)> <webview-candidate dir (VM)> <tag> [extra probe args...]
set -u
S=$1; FW=$2; CAND=$3; TAG=$4; shift 4; EXTRA="$*"
. "$(dirname "${BASH_SOURCE[0]}")/lab_paths.sh" || exit 1
H=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
HDC=$WORKSPACES/westlake-inputs/tools/hdc_mac.sh
D=$WORKSPACES/westlake-inputs/tools/ttdrive.sh
VMH=$(lab_vm_home) || exit 1
RUN=$VMH/a2hlab/board/$S/$TAG
LOCAL=$HOME/OrbStack/a2hlab$VMH/a2hlab/board/$S/$TAG   # the same directory through OrbStack's Mac view
dev() { "$H" -t "$S" shell "$1" | LC_ALL=C tr -d '\r'; }
texts() {
  VT_WAIT=6 "$D" "$S" "$RUN" vt 2>/dev/null | python3 -c '
import re, sys
sys.stdin.reconfigure(errors="replace")
seen = []
for line in sys.stdin:
    m = re.search(r"\"(.+?)\"\s*$", line.rstrip())
    if m and m.group(1) not in seen: seen.append(m.group(1))
print("\n".join(seen))'
}

dev 'kill -9 $(pidof appspawn-x) 2>/dev/null; power-shell wakeup >/dev/null; power-shell timeout -o 86400000 >/dev/null' >/dev/null
CHILD=$(orb -m a2hlab bash -lc "A=/home/dspfac/a2hlab/source-closure/verify; cd ~/a2hlab/manifest && python3 \$A/out-integrate/probe-local/tools/probe_source_app.py \
  --workspace \$A --westlake-source \$A/westlake-integrate --framework-report $FW --app-input ~/a2hlab/app-inputs/toutiao --app toutiao \
  --hdc $HDC --serial $S --out $RUN --host-build \$A/out/signed-host --webview-input \$A/out/webview-input-source \
  --source-webview-build $CAND --android-native-target libvision_core.so --android-native-target libc++_shared.so $EXTRA 2>&1" \
  | grep -o '"child": [0-9]*' | grep -o '[0-9]*$')
[ -z "$CHILD" ] && { echo "LAUNCH FAILED (see $LOCAL)"; exit 1; }
RT=$(python3 -c "import json;print(json.load(open('$LOCAL/device-report.json'))['runtime'])")
echo "child=$CHILD candidate=$CAND"
sleep 50
echo "t=50s alive=$(dev "[ -d /proc/$CHILD ] && echo 1 || echo 0")"
dev "rm -f /data/local/tmp/sc17.pcap; (/data/local/tmp/wl-netcap wlan0 60 /data/local/tmp/sc17.pcap > /data/local/tmp/sc17.netcap.log 2>&1 &); aa start -b org.westlake.imehost -a EntryAbility >/dev/null"
sleep 4
"$D" "$S" "$RUN" consent 2>&1 | tr '\n' ' '; echo
died=""
for i in 1 2 3 4 5 6 7 8 9; do
  sleep 10
  a=$(dev "[ -d /proc/$CHILD ] && echo 1 || echo 0")
  echo "+$((i*10))s after consent alive=$a"
  [ "$a" = 0 ] && { died="+$((i*10))s"; break; }
done
if [ -z "$died" ]; then
  feed=$(texts)
  printf '%s\n' "$feed" > "$LOCAL/feed-texts.txt"
  echo "view-tree texts: $(printf '%s\n' "$feed" | grep -c .)  (>=12 chars: $(printf '%s\n' "$feed" | awk 'length($0)>=12' | grep -vcE '个人信息|同意|搜你想看的'))"
  printf '%s\n' "$feed" | awk 'length($0)>=12' | grep -vE '个人信息|同意|搜你想看的' | head -8 | sed 's/^/  | /'
  "$D" "$S" "$RUN" shot "$TAG" >/dev/null 2>&1
  echo "libsscronet mapped: $(dev "grep -c sscronet /proc/$CHILD/maps")"
  LOGP=$(python3 -c "import json;print(json.load(open('$LOCAL/device-report.json'))['runtime'])")/private-tmp/adapter_child_$CHILD.stderr
  dev "echo N > /data/local/tmp/noice_tap; sleep 4; grep -a 'CRONET-803' $LOGP | tail -1"
fi
sleep 5
LOG=$RT/private-tmp/adapter_child_$CHILD.stderr
echo "died=${died:-no}"
echo "Unable-to-load ASurfaceControl lines: $(dev "grep -c 'Unable to load function ASurface' $LOG")"
echo "no-op table first calls:"; dev "grep -a 'WESTLAKE-WEBVIEW-SC' $LOG" | sed 's/^/  /'
echo "webview cmd: $(dev "grep -a -m1 'SOURCE-WEBVIEW-CMD' $LOG")"
echo "faultlog: $(dev "ls /data/log/faultlog/temp/ | grep -- '-$CHILD-'")"
f=$(dev "ls /data/log/faultlog/temp/ | grep -- '-$CHILD-' | head -1")
[ -n "$f" ] && dev "grep -m1 Reason /data/log/faultlog/temp/$f; grep -m1 -A1 'Fault thread' /data/log/faultlog/temp/$f; grep -m1 '#00 pc' /data/log/faultlog/temp/$f"
dev "cat $LOG" > "$LOCAL/child.stderr" 2>/dev/null
"$H" -t "$S" file recv /data/local/tmp/sc17.pcap "$LOCAL/consent.pcap" >/dev/null 2>&1 && \
  python3 "$WORKSPACES/westlake-harness/probes/network-capture/read.py" "$LOCAL/consent.pcap" | sed -n '1,/TLS SNI/p;/TLS SNI/,/^$/p' | head -20
