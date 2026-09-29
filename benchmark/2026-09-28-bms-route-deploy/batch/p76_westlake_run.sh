#!/usr/bin/env bash
# #76-A: relaunch Westlake-route Wikipedia on 61b (reusing the 09-27 staged
# runtime) and capture a COMPLETE success log: 16M hilog, private off,
# child stderr preserved, screenshots toward onboarding.
set -uo pipefail
H="/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh"
S="61b0657200000000000000000324012c"
HASH="0033a17c88394b7da128ea1f6fac94fa"
SRC="/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-$HASH"
STG="/data/local/tmp/a2hlab-app-$HASH"
SOCK="A2HSource$HASH"
OUT="/home/zhaoyue/a2hlab/board/p76-westlake"
mkdir -p "$OUT"

sh() { "$H" -t "$S" shell "$*" 2>/dev/null; }

echo "== 0. preflight (hilog 16M + privacy off) =="
sh "hilog -G 16M; hilog -p off; hilog -g" | tee "$OUT/preflight.txt"
sh "hilog -r" >/dev/null 2>&1

echo "== 1. imehost alive =="
sh "pgrep -f org.westlake.imehost | head -2" | tee -a "$OUT/state.txt"

echo "== 2. wipe app data of org.wikipedia (clean onboarding) =="
sh "rm -rf $SRC/app-data/org.wikipedia; mkdir -p $SRC/app-data/org.wikipedia; chown -R 20010053:20010053 $SRC/app-data/org.wikipedia; chcon -R u:object_r:data_app_el2_file:s0 $SRC/app-data/org.wikipedia"

echo "== 3. launch (run.sh rewritten: /data/local/tmp/asx -> $SRC) =="
# the original run.sh cds to /data/local/tmp/asx which no longer exists; the
# staged source dir IS the runtime root. Rewrite it in place (backup first).
sh "cp $SRC/run.sh $SRC/run.sh.orig 2>/dev/null; sed -i s#/data/local/tmp/asx#$SRC#g $SRC/run.sh; head -2 $SRC/run.sh"
sh "cd $SRC && nohup /system/bin/sh $SRC/run.sh > $STG/wl-parent.log 2> $STG/wl-parent.stderr & echo started" | tee -a "$OUT/state.txt"
sleep 2

echo "== 4. wait for socket =="
for i in 1 2 3 4 5 6 7 8 9 10; do
  R=$(sh "if [ -S /dev/unix/socket/$SOCK ]; then echo READY; fi" | tr -d '\r')
  [ "$R" = "READY" ] && break
  sleep 1
done
echo "socket: ${R:-NOT-UP}" | tee -a "$OUT/state.txt"
if [ "${R:-}" != "READY" ]; then
  echo "FATAL: source runtime socket not up; parent stderr:" | tee -a "$OUT/state.txt"
  sh "tail -20 $STG/wl-parent.stderr" | tee -a "$OUT/state.txt"
  exit 1
fi

echo "== 5. host_spawn the launch request =="
sh "$STG/host_spawn /dev/unix/socket/$SOCK $STG/request.bin; echo rc=\$?" | tee "$OUT/host_spawn.txt"

echo "== 6. wait, snapshot t+8/t+16/t+30 =="
for t in 8 16 30; do
  sleep $(( t == 8 ? 8 : t - 16 > 0 ? t - 16 : 1 ))
  sh "power-shell wakeup >/dev/null 2>&1; snapshot_display -f /data/local/tmp/p76-wl-t${t}.jpeg >/dev/null 2>&1; stat -c %s /data/local/tmp/p76-wl-t${t}.jpeg" | tr -d '\r' | tee -a "$OUT/shots.txt"
done
for t in 8 16 30; do
  "$H" -t "$S" file recv "/data/local/tmp/p76-wl-t${t}.jpeg" "$OUT/wl-t${t}.jpeg" >/dev/null 2>&1
done

echo "== 7. dump hilog + parent/child logs =="
sh "hilog -x" > "$OUT/wl-hilog.txt" 2>/dev/null
sh "cat $STG/wl-parent.log" > "$OUT/wl-parent.log" 2>/dev/null
sh "cat $STG/wl-parent.stderr" > "$OUT/wl-parent.stderr" 2>/dev/null
# child stderr lives under the source dir (WESTLAKE_SOURCE_LOG_STDERR=1)
sh "find $SRC -name '*.log' -newer $SRC/run.sh 2>/dev/null | head -10" | tee -a "$OUT/state.txt"
sh "cat $SRC/private-tmp/asx/*.log 2>/dev/null | tail -80" > "$OUT/wl-asx-logs.txt" 2>/dev/null

echo "== 8. process state =="
sh "ps -A -o PID,PPID,UID,NAME | grep -E '20010053|appspawn-x'" | tee -a "$OUT/state.txt"

echo DONE
