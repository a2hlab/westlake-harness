#!/bin/bash
# Host-side orchestration of one measured run on the Android reference phone.
# usage: run.sh TAG fresh|second
set -u
ADB=~/Library/Android/sdk/platform-tools/adb; S=N100CU025C18D000128
PKG=com.ss.android.article.news
TAG=$1; MODE=$2
HERE=$(cd "$(dirname "$0")" && pwd)
R=$HERE/../runs/$TAG; mkdir -p "$R"
D=/data/local/tmp/tt26/$TAG
a() { $ADB -s $S "$@"; }
a push "$HERE/drive.sh" /data/local/tmp/tt26/drive.sh >/dev/null
a shell "am force-stop $PKG; rm -rf $D; mkdir -p $D"
[ "$MODE" = fresh ] && a shell pm clear $PKG
a shell 'logcat -b all -c'
# Run adb itself in the background (not via a()): $! must be adb's pid, or
# the kill below leaves the reader alive, appending later runs to this file.
$ADB -s $S logcat -b main,system,crash,events -v threadtime -v epoch -v usec > "$R/logcat.txt" 2>&1 &
LPID=$!
a shell "atrace --async_start -b 16384 -a $PKG input view gfx am wm dalvik" > /dev/null 2>&1
a shell "screenrecord --bit-rate 8000000 --time-limit 75 $D/screen.mp4" > /dev/null 2>&1 &
SPID=$!
sleep 1.5
a shell "sh /data/local/tmp/tt26/drive.sh $MODE $D"
a shell "atrace --async_stop -o $D/atrace.txt" > /dev/null 2>&1
P=$(a shell pidof $PKG | awk '{print $1}')
echo "APP_PID $P" >> "$R/meta.txt"
a shell "ps -A -o PID,PPID,STIME,NAME | grep $PKG" >> "$R/meta.txt"
a shell "su 0 sh -c 'grep -E \"metasec|bdheif|gifimage|imagepipeline|static-webp|sscronet\" /proc/$P/maps; echo ---; ls -d /data/user/0/$PKG/app_lib* 2>&1; find /data/user/0/$PKG /data/user_de/0/$PKG -name \"*metasec*\" 2>/dev/null'" > "$R/native-maps.txt"
a shell "su 0 sh -c 'cd /data/user/0/$PKG/cache; for f in \$(find image_cache -type f -name \"*.cnt\"); do echo \"\$f \$(stat -c %s \$f) \$(od -A n -t x1 -N 16 \$f | tr -d \" \n\")\"; done'" > "$R/imgmagic.txt"
wait $SPID
sleep 1
kill $LPID 2>/dev/null
a pull $D/. "$R/" > /dev/null
echo "done $TAG -> $R"
