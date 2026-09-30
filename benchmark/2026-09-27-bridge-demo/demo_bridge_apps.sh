#!/usr/bin/env bash
# demo_bridge_apps.sh <SERIAL=61b06572> [HOLD=10] [RENDER_WAIT=13]
#
# Camera-friendly bridge-layer capability demo: on 61b06572, bring up each of 13 verified-LIT
# Android apps in turn (stage+launch through the westlake bridge), pull it onto the physical
# screen (dismiss the OH keyguard, host window fronted), HOLD it for the camera, snapshot it,
# then force-stop and move on. Finale: relaunch the Toutiao feed so the board is left on the
# flagship demo. Repeatable and idempotent.
#
# Bridge mechanics this shows off (per app, all handled by probe_source_app.py):
#   - a self-contained source runtime staged on-device + launched via source_app_namespace,
#   - the app's sub-window attached to the OH host window (WL_PARENT_ID / WL_SUB_WINDOW),
#   - real touch: touchfwd reads the digitizer evdev and re-injects into the bridge channel
#     (OH MMI never routes to these bridge sub-windows), so the panel is actually interactive.
#
# HARD SAFETY: only 61b06572 is allowed. 5cd1e3dd / 5ea34a45 run their own Toutiao demos and
# are hard-refused. The script never installs/removes the host (keeps the Toutiao-branded host
# df385638), so restoring Toutiao at the end is just restarting its watchdog.
set -u

SERIAL="${1:-61b06572}"
HOLD="${2:-10}"
RENDER_WAIT="${3:-13}"
case "$SERIAL" in 61b06572*) SERIAL=61b0657200000000000000000324012c ;; esac
case "$SERIAL" in
  5cd1e3dd*|5ea34a45*) echo "REFUSE: $SERIAL is a protected board (runs its own Toutiao demo)."; exit 2 ;;
esac
[ "$SERIAL" = 61b0657200000000000000000324012c ] || { echo "REFUSE: this demo only runs on 61b06572 (got $SERIAL)"; exit 2; }
S61="$SERIAL"

HDC="/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc"
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/../../scripts/lab/lab_paths.sh" || exit 1
HDC_MAC="$WORKSPACES/westlake-inputs/tools/hdc_mac.sh"
KEEPER_SRC="$HERE/../2026-09-27-device-provisioning/onscreen_keeper.sh"   # proven keyguard-dismiss daemon
D="/data/local/tmp/operator45"; F="$D/selfheal48"
RUNTAG="$(date +%m%d-%H%M%S)"
SHOTS="$HERE/screens"; mkdir -p "$SHOTS"
TT_RT_HASH="c91d26bf"    # the Toutiao RT dir prefix — never delete this one

# The 13 verified-LIT apps, in demo order (keys = app-inputs/<key> dir names).
APPS="wikipedia antennapod aegis fd-com-kunzisoft-keepass-libre fd-netguard fd-auxio fd-com-amaze-filemanager fd-AppManager fd-droidify ooniprobe fd-noice fd-fitness termux"

dev(){ gtimeout "${2:-60}" "$HDC" -t "$S61" shell "$1" 2>&1 | tr -d '\r'; }
recv(){ gtimeout 40 "$HDC" -t "$S61" file recv "$1" "$2" >/dev/null 2>&1; }
say(){ printf '[demo %s] %s\n' "$(date +%H:%M:%S)" "$*"; }
zget(){ # $1 = window name -> ZOrder (field 8), empty if absent
  dev "hidumper -s WindowManagerService -a '-a' 2>/dev/null | grep -E '$1'" 12 | awk -v w="$1" '$1 ~ ("^" w){print $8; exit}'
}

# ---- 0. connectivity + cleanup: stop Toutiao watchdog/keeper, kill source apps (KEEP the host) ----
gtimeout 20 "$HDC" list targets 2>/dev/null | grep -q "$S61" || { echo "FAIL: 61b06572 not connected"; exit 1; }
say "bridge demo start (HOLD=${HOLD}s render_wait=${RENDER_WAIT}s runtag=$RUNTAG)"
say "stopping Toutiao watchdog + keeper, clearing source runtimes (host kept alive)"
dev "touch $F/stop $D/stop $D/fresh48/stop $D/keeper.stop 2>/dev/null; for p in \$(cat $D/keeper.pid 2>/dev/null); do kill \$p 2>/dev/null; done; sleep 2; for p in \$(pidof com.ss.android.article.news appspawn-x source_app_namespace touchfwd); do kill -9 \$p 2>/dev/null; done; sleep 1; echo host=\$(pidof org.westlake.imehost)" 30
# remove any leftover per-app source runtimes/staging from earlier demo runs, but NEVER the Toutiao
# RT *or* the Toutiao STAGE — both are named a2hlab-{source,app}-c91d26bf... and are load-bearing for
# the finale (the watchdog's start-parent.sh writes parent.log into the STAGE dir; deleting it =
# PARENT_BLOCKED). Guard both prefixes.
dev "cd /data/app/el2/100/base/org.westlake.imehost/files 2>/dev/null && for d in a2hlab-source-*; do case \"\$d\" in a2hlab-source-$TT_RT_HASH*) : ;; *) rm -rf \"\$d\" ;; esac; done; cd /data/local/tmp 2>/dev/null && for d in a2hlab-app-*; do case \"\$d\" in a2hlab-app-$TT_RT_HASH*) : ;; *) rm -rf \"\$d\" ;; esac; done; echo cleaned" 120 >/dev/null

# ---- 1. deploy + start the on-screen keeper (keyguard-dismiss + keep-awake for the whole demo) ----
gtimeout 60 "$HDC" -t "$S61" file send "$KEEPER_SRC" "$D/onscreen_keeper.sh" >/dev/null 2>&1
dev "chmod +x $D/onscreen_keeper.sh; rm -f $D/keeper.stop $D/keeper.pid; power-shell timeout -o 86400000 >/dev/null 2>&1; power-shell wakeup >/dev/null 2>&1; KDIR=$D INTERVAL=5 nohup /system/bin/sh $D/onscreen_keeper.sh >$D/keeper.out 2>&1 </dev/null & echo keeper_started" 20 >/dev/null
say "on-screen keeper started"

# ---- 2. per-app: stage+launch -> render -> on-screen -> HOLD -> snapshot -> force-stop -> reclaim ----
onscreen_count=0; idx=0; RESULTS=""
for APP in $APPS; do
  idx=$((idx+1))
  say "[$idx/13] $APP : staging+launching through the bridge ..."
  spawn=$(orb -m a2hlab bash -lc "
    W=/home/dspfac/a2hlab/source-closure/verify
    cd ~/a2hlab/manifest && python3 tools/probe_source_app.py \
      --workspace \"\$W\" --westlake-source \"\$W/westlake\" \
      --framework-report ~/a2hlab/board/$S61/framework-1/device-report.json \
      --app-input ~/a2hlab/app-inputs/$APP --app $APP \
      --hdc $HDC_MAC --serial $S61 \
      --out ~/a2hlab/board/$S61/bridgedemo/$APP-$RUNTAG \
      --webview-input \"\$W/out/webview-input-source\" 2>&1" 2>&1)
  line=$(printf '%s\n' "$spawn" | grep 'SOURCE_APP_SPAWNED' | tail -1)
  if [ -z "$line" ]; then
    say "[$idx/13] $APP : PROBE FAILED — $(printf '%s\n' "$spawn" | tail -1)"
    RESULTS="$RESULTS\n$idx\t$APP\tPROBE_FAIL"
    dev "for p in \$(pidof appspawn-x source_app_namespace touchfwd); do kill -9 \$p 2>/dev/null; done" 20 >/dev/null
    continue
  fi
  json="${line#*SOURCE_APP_SPAWNED }"
  child=$(printf '%s' "$json" | sed -n 's/.*"child": *\([0-9]*\).*/\1/p')
  parent=$(printf '%s' "$json" | sed -n 's/.*"parent": *\([0-9]*\).*/\1/p')
  rtdir=$(printf '%s' "$json" | sed -n 's/.*"runtime": *"\([^"]*\)".*/\1/p')
  stdir=$(printf '%s' "$json" | sed -n 's/.*"stage": *"\([^"]*\)".*/\1/p')
  say "[$idx/13] $APP : spawned parent=$parent child=$child; waiting ${RENDER_WAIT}s to render"
  sleep "$RENDER_WAIT"

  # pull onto the screen: wake + dismiss keyguard (keeper also does this), then check ZOrder
  dev "power-shell wakeup >/dev/null 2>&1; for i in 1 2 3; do uinput -T -m 600 1700 600 200 300 >/dev/null 2>&1; sleep 1; done; echo swept" 15 >/dev/null
  hostz=$(zget imehost0); lockz=$(zget SCBScreenLock)
  alive=$(dev "ls -d /proc/$child 2>/dev/null && echo A || echo G" 10 | tail -1)
  onscreen="no"
  if [ -n "$hostz" ] && [ "$hostz" -ge 0 ] 2>/dev/null && { [ -z "$lockz" ] || [ "$lockz" -lt 0 ] 2>/dev/null; } && [ "$alive" = A ]; then
    onscreen="yes"; onscreen_count=$((onscreen_count+1))
  fi
  say "[$idx/13] $APP : host_z=${hostz:-none} lock_z=${lockz:-none} child=${alive} on_screen=$onscreen — HOLD ${HOLD}s for camera"
  sleep "$HOLD"

  # snapshot
  shot="$SHOTS/$(printf '%02d' $idx)-$APP.png"
  dev "rm -f /data/local/tmp/demo-shot.png; snapshot_display -t png -f /data/local/tmp/demo-shot.png >/dev/null 2>&1" 15 >/dev/null
  recv "/data/local/tmp/demo-shot.png" "$shot"
  say "[$idx/13] $APP : screenshot -> $shot"
  RESULTS="$RESULTS\n$idx\t$APP\t$([ "$onscreen" = yes ] && echo ON_SCREEN || echo not_on_screen)\t$shot"

  # force-stop + reclaim this app's on-device runtime/staging (never the Toutiao RT)
  dev "for p in $parent $child \$(pidof appspawn-x source_app_namespace touchfwd); do kill -9 \$p 2>/dev/null; done; sleep 1" 20 >/dev/null
  case "$rtdir" in *a2hlab-source-$TT_RT_HASH*) : ;; *"a2hlab-source-"*) dev "rm -rf '$rtdir' '$stdir' 2>/dev/null" 60 >/dev/null ;; esac
done

# ---- 3. finale: relaunch the Toutiao feed (restart its watchdog + keeper; host was never touched) ----
say "FINALE: relaunching Toutiao feed"
dev "for p in \$(pidof appspawn-x source_app_namespace touchfwd); do kill -9 \$p 2>/dev/null; done; touch $D/keeper.stop; for p in \$(cat $D/keeper.pid 2>/dev/null); do kill \$p 2>/dev/null; done; sleep 2" 20 >/dev/null
dev "rm -f $F/stop $D/stop $D/fresh48/stop $D/keeper.stop $D/keeper.pid; rm -rf $F/lock; power-shell timeout -o 86400000 >/dev/null 2>&1; power-shell wakeup >/dev/null 2>&1; nohup /system/bin/sh $F/watchdog.sh >$D/watchdog-demo.log 2>&1 </dev/null & KDIR=$D INTERVAL=5 nohup /system/bin/sh $D/onscreen_keeper.sh >$D/keeper.out 2>&1 </dev/null & echo tt_restarted" 20 >/dev/null
tt="no"
for i in $(seq 1 30); do
  sleep 5
  st=$(dev "cat $F/state 2>/dev/null" 10); hostz=$(zget imehost0); lockz=$(zget SCBScreenLock)
  if echo "$st" | grep -q READY && [ -n "$hostz" ] && [ "$hostz" -ge 0 ] 2>/dev/null && { [ -z "$lockz" ] || [ "$lockz" -lt 0 ] 2>/dev/null; }; then tt="yes"; break; fi
done
dev "rm -f /data/local/tmp/demo-shot.png; snapshot_display -t png -f /data/local/tmp/demo-shot.png >/dev/null 2>&1" 15 >/dev/null
recv "/data/local/tmp/demo-shot.png" "$SHOTS/99-toutiao-restored.png"

# ---- 4. summary ----
echo ""
echo "================ BRIDGE DEMO SUMMARY (61b06572, runtag $RUNTAG) ================"
printf 'idx\tapp\tresult\tshot\n'
printf "$RESULTS\n" | sed '/^$/d'
echo "-------------------------------------------------------------------------------"
echo "on-screen: $onscreen_count / 13    Toutiao restored: $tt"
echo "screens dir: $SHOTS"
echo "==============================================================================="
