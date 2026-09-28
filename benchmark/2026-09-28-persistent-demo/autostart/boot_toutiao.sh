#!/system/bin/sh
# wl_toutiao boot autostart — mirrors provision_toutiao.sh steps 6+7 (known-good).
# RT/STAGE/watchdog persist in /data across reboot; only the asx bind-mount + daemons
# need rebuilding. The missing piece in the earlier version was step 6 (mount-point
# dirs + chown + restorecon): source_app_namespace binds $RT -> /data/local/tmp/asx,
# so $RT/private-tmp/asx must exist and be owned by the app uid or the child SIGTERMs.
exec >/data/local/tmp/operator45/boot_toutiao.log 2>&1
echo "[boot] start $(date) uptime=$(cut -d. -f1 /proc/uptime)"
RT="/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d"
STAGE="/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d"
D="/data/local/tmp/operator45"; F="$D/selfheal48"

# settle: wait for /data mounted + framework up
sleep 40
n=0; while [ $n -lt 30 ]; do [ -d "$RT" ] && [ -f "$F/watchdog.sh" ] && break; sleep 2; n=$((n+1)); done
echo "[boot] RT present after ${n} tries"

# --- provision step 6: mount-point dirs + ownership + SELinux + max_map_count ---
mkdir -p "$RT/private-tmp/asx"
chown -R 20010053:20010053 "$RT/private-tmp"
chown 20010053:20010053 "$RT"
restorecon -R "$RT" 2>/dev/null
restorecon -R "$STAGE" 2>/dev/null
echo 1048576 > /proc/sys/vm/max_map_count 2>/dev/null
echo "[boot] step6 done asx=$(ls -ld $RT/private-tmp/asx 2>&1)"

# --- provision step 7: clear stops, screen on, start watchdog + on-screen keeper ---
rm -f "$F/stop" "$D/stop" "$D/fresh48/stop" "$D/keeper.stop" "$D/keeper.pid"
rm -rf "$F/lock"
power-shell timeout -o 86400000 >/dev/null 2>&1
power-shell wakeup >/dev/null 2>&1
nohup /system/bin/sh "$F/watchdog.sh" >"$D/watchdog-boot.log" 2>&1 </dev/null &
KDIR="$D" INTERVAL=5 nohup /system/bin/sh "$F/onscreen_keeper.sh" >"$D/keeper.out" 2>&1 </dev/null &
echo "[boot] watchdog+keeper launched uptime=$(cut -d. -f1 /proc/uptime)"
