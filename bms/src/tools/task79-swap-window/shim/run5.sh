#!/bin/bash
# run5.sh <label> [secs] — like run3 but keeps the WHOLE hilog and pulls it, so we can
# see who kills the child rather than guessing from a pre-filtered grep.
. ~/hdcenv.sh
L=${1:-run}; W=${2:-40}
mkdir -p ~/wl/logs
$HDC -t $B shell "rm -f /data/service/el1/public/appspawnx/adapter_child_*.stderr /data/local/tmp/hl-$L.txt; hilog -r >/dev/null 2>&1"
$HDC -t $B shell "(hilog > /data/local/tmp/hl-$L.txt 2>&1 &) ; sleep 1; echo hilog_on"
$HDC -t $B shell "aa start -b com.github.ashutoshgngwr.noice -a com.github.ashutoshgngwr.noice.activity.MainActivity -m entry" 2>&1 | tail -1
$HDC -t $B shell '
D=/data/service/el1/public/appspawnx
seen=
for i in $(seq 1 '"$W"'); do
  F=$(ls -t $D/adapter_child_*.stderr 2>/dev/null | head -1)
  P=${F##*adapter_child_}; P=${P%.stderr}
  if [ -n "$P" ] && [ -d /proc/$P ]; then
    seen=$P
    echo "t=${i} pid=$P $(grep -m1 ^State /proc/$P/status) lines=$(wc -l < $F)"
  elif [ -n "$seen" ]; then
    echo "t=${i} pid=$seen GONE lines=$(wc -l < $D/adapter_child_$seen.stderr 2>/dev/null)"
    break
  else
    echo "t=${i} nochild"
  fi
  sleep 1
done'
sleep 2
$HDC -t $B shell "snapshot_display -f /data/local/tmp/shot-$L.jpeg" >/dev/null 2>&1
$HDC -t $B file recv /data/local/tmp/shot-$L.jpeg ~/wl/logs/shot-$L.jpeg >/dev/null 2>&1 && echo "shot ok"
CH=$($HDC -t $B shell "ls -t /data/service/el1/public/appspawnx/adapter_child_*.stderr 2>/dev/null | head -1" | tr -d "\r\n ")
$HDC -t $B file recv "$CH" ~/wl/logs/ch-$L.txt >/dev/null 2>&1 && echo "child $(wc -l < ~/wl/logs/ch-$L.txt) lines -> ch-$L.txt"
$HDC -t $B file recv /data/local/tmp/hl-$L.txt ~/wl/logs/hl-$L.txt >/dev/null 2>&1 && echo "hilog $(wc -l < ~/wl/logs/hl-$L.txt) lines -> hl-$L.txt"
$HDC -t $B shell "rm -f /data/local/tmp/hl-$L.txt"
echo "CHILDPID=${CH##*adapter_child_}"
