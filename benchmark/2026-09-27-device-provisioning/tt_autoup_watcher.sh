#!/usr/bin/env bash
# Mac-side auto-up watcher: whenever 61b06572 has no Toutiao watchdog running (e.g. right after a
# reboot), auto-bring-up the Toutiao selfheal watchdog + on-screen keeper. Zero on-device command.
HDC="/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc"
K=61b0657200000000000000000324012c
bringup(){
  gtimeout 25 "$HDC" -t "$K" shell "D=/data/local/tmp/operator45; F=\$D/selfheal48; rm -f \$F/stop \$D/stop \$D/fresh48/stop \$D/keeper.stop \$D/keeper.pid 2>/dev/null; rm -rf \$F/lock 2>/dev/null; echo 1048576 > /proc/sys/vm/max_map_count 2>/dev/null; power-shell timeout -o 86400000 >/dev/null 2>&1; power-shell wakeup >/dev/null 2>&1; nohup /system/bin/sh \$F/watchdog.sh >\$D/wd-auto.log 2>&1 </dev/null & KDIR=\$D INTERVAL=5 nohup /system/bin/sh \$D/onscreen_keeper.sh >\$D/keeper.out 2>&1 </dev/null & echo brought-up" 2>&1 | tail -1
}
while true; do
  if gtimeout 8 "$HDC" list targets 2>/dev/null | grep -q "$K"; then
    up=$(gtimeout 8 "$HDC" -t "$K" shell 'cat /proc/uptime 2>/dev/null' 2>&1 | awk '{print int($1)}')
    wd=$(gtimeout 8 "$HDC" -t "$K" shell 'ps -ef 2>/dev/null | grep -c "[w]atchdog.sh"' 2>&1 | tail -1)
    if [ "${wd:-0}" = "0" ] && [ -n "$up" ]; then
      echo "$(date '+%H:%M:%S') 61b watchdog down (uptime=${up}s) -> bringing up Toutiao"
      # wait for graphics stack if very fresh boot
      [ "$up" -lt 60 ] && sleep $((60-up))
      bringup
    fi
  fi
  sleep 15
done
