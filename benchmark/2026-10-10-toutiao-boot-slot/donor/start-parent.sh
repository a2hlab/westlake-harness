#!/system/bin/sh
RT=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d
# Pin WL_PARENT_ID to the CURRENT host window id before each launch: the imehost0
# window id drifts whenever the host restarts, so a stale value drops the app
# sub-window off the physical screen. Wait briefly for the host window, then sed it in.
WID=""; n=0
while [ "$n" -lt 20 ]; do
  WID=$(hidumper -s WindowManagerService -a '-a' 2>/dev/null | grep imehost0 | while read a b c w r; do echo "$w"; break; done)
  case "$WID" in [0-9]*) break;; esac
  sleep 0.25; n=$((n+1))
done
case "$WID" in [0-9]*) sed -i "s/export WL_PARENT_ID=[0-9]*/export WL_PARENT_ID=$WID/" "$RT/run.sh";; esac
nohup /data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/source_app_namespace "$RT" 20010053 /system/bin/sh /data/local/tmp/asx/run.sh >/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/parent.log 2>&1 </dev/null & echo $!
