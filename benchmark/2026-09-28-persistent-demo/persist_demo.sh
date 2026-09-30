#!/usr/bin/env bash
# persist_demo.sh <SERIAL=61b06572> {install | up | open <app> | open-all [HOLD] | list | status | toutiao}
#
# Reboot-surviving bridge-app demo for 61b06572. The 13 apps are STAGED once (their source runtimes
# live on /data, which is persistent f2fs), and any app can be opened to its first screen after a
# reboot by a fast host_spawn from the persisted runtime — no re-staging, and no Mac/VM needed at
# demo time (only `install` needs the VM).
#
#   install        : (needs VM, ~7 min) clean orphan runtimes, stage all 13 apps, record a manifest
#                    (app -> runtime suffix + socket + package). Leaves them staged, not running.
#   up             : (post-boot, no VM) start the OH host window + on-screen keeper. Run once after a reboot.
#   open <app>     : (no VM, ~1 s + render) launch one app from its persisted runtime onto the first screen.
#   open-all [HOLD]: open each of the 13 in turn (screenshot each) — used to verify after a reboot.
#   list / status  : show the manifest / what is running.
#   toutiao        : (optional) restart the Toutiao self-heal watchdog + keeper (the extra flagship item).
#
# Why this survives reboot: /data files persist (runtimes, manifest, host bundle, framework); /dev is
# tmpfs so stale sockets are cleared on boot; only processes die, and `up`+`open` re-create them.
# There is NO OS autostart (OH /system is read-only; the watchdog was a manual nohup) — `up` is the
# one manual post-boot step.
#
# HARD SAFETY: only 61b06572. 5cd1e3dd / 5ea34a45 are hard-refused.
set -u

SERIAL="${1:-61b06572}"; CMD="${2:-}"
case "$SERIAL" in 61b06572*) SERIAL=61b0657200000000000000000324012c ;; esac
case "$SERIAL" in 5cd1e3dd*|5ea34a45*) echo "REFUSE: $SERIAL is a protected board."; exit 2 ;; esac
[ "$SERIAL" = 61b0657200000000000000000324012c ] || { echo "REFUSE: only 61b06572 (got $SERIAL)"; exit 2; }
S61="$SERIAL"

HDC="/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc"
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/../../scripts/lab/lab_paths.sh" || exit 1
HDC_MAC="$WORKSPACES/westlake-inputs/tools/hdc_mac.sh"
KEEPER_SRC="$HERE/../2026-09-27-device-provisioning/onscreen_keeper.sh"
BROKER_SRC="$HERE/open_broker.sh"
HOST=org.westlake.imehost
UID_APP=20010053
RTBASE="/data/app/el2/100/base/$HOST/files"
D="/data/local/tmp/operator45"; F="$D/selfheal48"
PDIR="/data/local/tmp/persist-demo"; MANIFEST="$PDIR/manifest.txt"
TT_RT_HASH="c91d26bf"
SHOTS="$HERE/screens"; mkdir -p "$SHOTS"
# Default demo list = the 12 apps that reliably open to first screen after reboot (verified).
# burgerking (McDonald's, com.emn8...bk) spawns but CRASHES on the 61b base (shows the host launcher,
# not the app) — kept in the manifest (openable via `open burgerking` for diagnosis) but OUT of the
# default sweep. Add it back with APPS_EXTRA=burgerking if you want to include it.
APPS="${APPS:-wikipedia ooniprobe fd-com-kunzisoft-keepass-libre fd-com-amaze-filemanager fd-auxio antennapod aegis fd-netguard fd-AppManager fd-droidify fd-noice fd-fitness}"
[ -n "${APPS_EXTRA:-}" ] && APPS="$APPS $APPS_EXTRA"

dev(){ gtimeout "${2:-60}" "$HDC" -t "$S61" shell "$1" 2>&1 | tr -d '\r'; }
recv(){ gtimeout 40 "$HDC" -t "$S61" file recv "$1" "$2" >/dev/null 2>&1; }
say(){ printf '[persist %s] %s\n' "$(date +%H:%M:%S)" "$*"; }
zget(){ dev "hidumper -s WindowManagerService -a '-a' 2>/dev/null | grep -E '$1'" 12 | awk -v w="$1" '$1 ~ ("^" w){print $8; exit}'; }
alive(){ [ -n "${1:-}" ] && [ "$(dev "ls -d /proc/$1 2>/dev/null && echo A || echo G" 10 | tail -1)" = A ]; }
dismiss_lock(){ dev "power-shell wakeup >/dev/null 2>&1; for i in 1 2; do uinput -T -m 600 1700 600 200 300 >/dev/null 2>&1; sleep 1; done" 12 >/dev/null; }
man_get(){ dev "grep -m1 \"^$1 \" $MANIFEST 2>/dev/null" 10; }   # -> "app suffix socket pkg"
ensure_host(){ # retry until the host process is up — post-boot OH services (aa/WMS) can take ~30-40s to be ready
  dev "n=0; while [ \$n -lt 30 ]; do pidof $HOST >/dev/null && break; aa start -b $HOST -a EntryAbility >/dev/null 2>&1; sleep 2; n=\$((n+1)); done; power-shell timeout -o 86400000 >/dev/null 2>&1; power-shell wakeup >/dev/null 2>&1; echo host=\$(pidof $HOST)" 90; }
start_keeper(){
  gtimeout 60 "$HDC" -t "$S61" file send "$KEEPER_SRC" "$D/onscreen_keeper.sh" >/dev/null 2>&1
  dev "mkdir -p $D; chmod +x $D/onscreen_keeper.sh; rm -f $D/keeper.stop $D/keeper.pid; KDIR=$D INTERVAL=5 nohup /system/bin/sh $D/onscreen_keeper.sh >$D/keeper.out 2>&1 </dev/null & echo keeper_on" 15 >/dev/null
}
start_broker(){
  gtimeout 60 "$HDC" -t "$S61" file send "$BROKER_SRC" "$PDIR/open_broker.sh" >/dev/null 2>&1
  dev "mkdir -p $PDIR/reqs; chmod 777 $PDIR $PDIR/reqs 2>/dev/null; chmod +x $PDIR/open_broker.sh; rm -f $PDIR/broker.stop $PDIR/broker.pid; for p in \$(cat $PDIR/broker.pid 2>/dev/null); do kill \$p 2>/dev/null; done; nohup /system/bin/sh $PDIR/open_broker.sh >$PDIR/broker.out 2>&1 </dev/null & echo broker_on" 15 >/dev/null
}
kill_demo_apps(){ dev "for p in \$(pidof appspawn-x source_app_namespace touchfwd); do kill -9 \$p 2>/dev/null; done; sleep 1" 20 >/dev/null; }

# Probe-stage one app (needs VM). Echoes the runtime suffix on success, empty on failure.
stage_app(){
  local app="$1" spawn line json runtime suffix
  orb -m a2hlab bash -lc "rm -rf ~/a2hlab/board/$S61/persistdemo/$app" >/dev/null 2>&1
  spawn=$(orb -m a2hlab bash -lc "
    W=/home/dspfac/a2hlab/source-closure/verify
    cd ~/a2hlab/manifest && python3 tools/probe_source_app.py \
      --workspace \"\$W\" --westlake-source \"\$W/westlake\" \
      --framework-report ~/a2hlab/board/$S61/framework-1/device-report.json \
      --app-input ~/a2hlab/app-inputs/$app --app $app \
      --hdc $HDC_MAC --serial $S61 \
      --out ~/a2hlab/board/$S61/persistdemo/$app \
      --webview-input \"\$W/out/webview-input-source\" 2>&1" 2>&1)
  line=$(printf '%s\n' "$spawn" | grep 'SOURCE_APP_SPAWNED' | tail -1)
  [ -z "$line" ] && return 1
  json="${line#*SOURCE_APP_SPAWNED }"
  runtime=$(printf '%s' "$json" | sed -n 's/.*"runtime": *"\([^"]*\)".*/\1/p')
  suffix="${runtime##*a2hlab-source-}"
  echo "$suffix"
}

# Fast-launch one app from its persisted runtime (no VM). Echoes child pid or empty.
open_persisted(){
  local app="$1" rec suffix socket rt stage
  rec="$(man_get "$app")"; [ -z "$rec" ] && { say "no manifest entry for $app"; return 1; }
  set -- $rec; suffix="$2"; socket="$3"
  rt="$RTBASE/a2hlab-source-$suffix"; stage="/data/local/tmp/a2hlab-app-$suffix"
  dev "
    [ -d '$rt' ] && [ -x '$stage/source_app_namespace' ] || { echo NO_RUNTIME; exit 0; }
    rm -f /dev/unix/socket/$socket 2>/dev/null
    WID=\$(hidumper -s WindowManagerService -a '-a' 2>/dev/null | grep imehost0 | while read a b c w r; do echo \$w; break; done)
    case \"\$WID\" in [0-9]*) sed -i \"s/export WL_PARENT_ID=[0-9]*/export WL_PARENT_ID=\$WID/\" '$rt/run.sh';; esac
    nohup '$stage/source_app_namespace' '$rt' $UID_APP /system/bin/sh /data/local/tmp/asx/run.sh >'$stage/parent.log' 2>&1 </dev/null &
    n=0; while [ \$n -lt 60 ]; do [ -S /dev/unix/socket/$socket ] && break; sleep 0.25; n=\$((n+1)); done
    '$stage/host_spawn' /dev/unix/socket/$socket '$stage/request.bin'
  " 40 | tr -d '\r' | sed -n 's/.*result=0 pid=\([0-9]*\).*/\1/p' | tail -1
}

case "$CMD" in
  install)
    gtimeout 20 "$HDC" list targets 2>/dev/null | grep -q "$S61" || { echo "FAIL: 61b06572 not connected"; exit 1; }
    say "install: stop Toutiao watchdog (keep host), clean orphan runtimes, stage $(echo $APPS|wc -w|tr -d ' ') apps"
    dev "touch $F/stop $D/stop $D/fresh48/stop $D/keeper.stop 2>/dev/null; for p in \$(cat $D/keeper.pid 2>/dev/null); do kill \$p 2>/dev/null; done; sleep 2; for p in \$(pidof com.ss.android.article.news appspawn-x source_app_namespace touchfwd); do kill -9 \$p 2>/dev/null; done; echo host=\$(pidof $HOST)" 30
    # remove orphan per-app runtimes/stages (keep the Toutiao delivery c91d26bf)
    dev "cd $RTBASE 2>/dev/null && for d in a2hlab-source-*; do case \"\$d\" in a2hlab-source-$TT_RT_HASH*) : ;; *) rm -rf \"\$d\";; esac; done; cd /data/local/tmp 2>/dev/null && for d in a2hlab-app-*; do case \"\$d\" in a2hlab-app-$TT_RT_HASH*) : ;; *) rm -rf \"\$d\";; esac; done; echo cleaned" 120 >/dev/null
    start_keeper; ensure_host >/dev/null
    dev "mkdir -p $PDIR; : > $MANIFEST" 10 >/dev/null
    ok=0; n=0
    for app in $APPS; do
      n=$((n+1)); say "[$n] staging $app ..."
      suffix="$(stage_app "$app")" || { say "  $app STAGE FAILED"; echo "$app FAIL FAIL FAIL" >> "$SHOTS/../install.log"; continue; }
      socket="A2HSource${suffix:0:20}"
      pkg=$(dev "grep -m1 ASX_LAUNCH_PKG $RTBASE/a2hlab-source-$suffix/run.sh 2>/dev/null" 10 | sed -n 's/.*ASX_LAUNCH_PKG=//p')
      dev "echo '$app $suffix $socket $pkg' >> $MANIFEST" 10 >/dev/null
      ok=$((ok+1)); say "  $app staged (suffix=$suffix socket=$socket pkg=$pkg)"
      kill_demo_apps   # keep the runtime, stop the running instance
    done
    recv "$MANIFEST" "$HERE/manifest.txt"
    say "INSTALL DONE: $ok/$n apps staged + recorded in $MANIFEST (persists across reboot)"
    say "after a reboot: '$0 61b06572 up' then '$0 61b06572 open <app>' (or open-all)"
    ;;

  up)
    say "post-boot bring-up: host window + keeper + open-broker"
    ensure_host; start_keeper; start_broker; dismiss_lock
    say "UP: host=$(dev "pidof $HOST" 10) broker=$(dev "cat $PDIR/broker.pid 2>/dev/null" 10)"
    say "  open via command: $0 61b06572 open <app>"
    say "  open via broker : drop the key at $PDIR/reqs/<key>  (HAP icons use this)"
    ;;

  broker-stop)
    dev "touch $PDIR/broker.stop; for p in \$(cat $PDIR/broker.pid 2>/dev/null); do kill \$p 2>/dev/null; done; echo stopped" 10
    ;;

  req)  # manually drop a broker request (simulates a HAP icon tap) — for testing the broker path
    KEY="${3:?usage: $0 61b06572 req <app-key-or-pkg>}"
    dev "echo > $PDIR/reqs/$KEY; echo dropped $KEY" 10
    ;;

  open)
    APP="${3:?usage: $0 61b06572 open <app>}"
    ensure_host >/dev/null; dismiss_lock; kill_demo_apps
    say "open $APP ..."
    child="$(open_persisted "$APP")"
    [ -z "$child" ] && { echo "FAIL: could not open $APP (no runtime? run install)"; exit 1; }
    sleep 13; dismiss_lock
    dev "rm -f /data/local/tmp/po.png; snapshot_display -t png -f /data/local/tmp/po.png >/dev/null 2>&1" 12 >/dev/null
    recv "/data/local/tmp/po.png" "$SHOTS/open-$APP.png"
    say "open $APP: child=$child host_z=$(zget imehost0) shot=$SHOTS/open-$APP.png"
    ;;

  open-all)
    HOLD="${3:-4}"
    ensure_host >/dev/null; dismiss_lock
    total=$(echo $APPS|wc -w|tr -d ' '); i=0; shown=0
    for app in $APPS; do
      i=$((i+1)); kill_demo_apps
      say "[$i/$total] open $app"
      child="$(open_persisted "$app")"
      if [ -z "$child" ]; then say "  $app FAILED to spawn"; continue; fi
      sleep 13; dismiss_lock
      dev "rm -f /data/local/tmp/po.png; snapshot_display -t png -f /data/local/tmp/po.png >/dev/null 2>&1" 12 >/dev/null
      recv "/data/local/tmp/po.png" "$SHOTS/$(printf '%02d' $i)-$app.png"
      hostz=$(zget imehost0); alive "$child" && [ -n "$hostz" ] && [ "$hostz" -ge 0 ] 2>/dev/null && shown=$((shown+1))
      say "  [$i/$total] $app child=$child host_z=${hostz:-none} shot=$SHOTS/$(printf '%02d' $i)-$app.png"
      sleep "$HOLD"
    done
    say "OPEN-ALL DONE: $shown/$total apps reached the screen (verify screenshots in $SHOTS/)"
    ;;

  broker-all)
    # Drive EVERY manifest app through the real HAP channel (open.req -> broker -> fast-open),
    # one at a time, screenshotting each. This is the icon-path end-to-end sweep. HOLD=arg3 (default 3).
    HOLD="${3:-3}"
    ensure_host >/dev/null; start_broker; dismiss_lock
    keys=$(dev "cut -d' ' -f1 $MANIFEST" 10)
    total=$(echo $keys | wc -w | tr -d ' '); i=0; shown=0
    for app in $keys; do
      i=$((i+1))
      dev "echo $app > $PDIR/open.req" 10 >/dev/null      # exactly what the HAP icon does
      sleep 15                                             # broker fast-open + first-frame render
      dev "rm -f /data/local/tmp/po.png; snapshot_display -t png -f /data/local/tmp/po.png >/dev/null 2>&1" 12 >/dev/null
      recv "/data/local/tmp/po.png" "$SHOTS/broker-$(printf '%02d' $i)-$app.png"
      pkg=$(dev "grep -m1 \"^$app \" $MANIFEST" 10 | sed 's/.* //'); live=$(dev "pidof $pkg" 10)
      [ -n "$live" ] && shown=$((shown+1))
      say "[$i/$total] $app pkg=$pkg live_pid=${live:-none} shot=$SHOTS/broker-$(printf '%02d' $i)-$app.png"
      sleep "$HOLD"
    done
    say "BROKER-ALL DONE: $shown/$total apps have a live process after broker-open (eyeball screenshots for render)"
    ;;

  list)   dev "cat $MANIFEST 2>/dev/null" 10 ;;
  status) dev "echo host=\$(pidof $HOST) keeper=\$(ps -ef|grep onscreen_keeper|grep -v grep|wc -l) demo_apps=\$(pidof appspawn-x|wc -w); echo manifest:; cat $MANIFEST 2>/dev/null" 15 ;;
  toutiao)
    dev "rm -f $F/stop $D/stop $D/fresh48/stop $D/keeper.stop $D/keeper.pid; rm -rf $F/lock; power-shell timeout -o 86400000 >/dev/null 2>&1; nohup /system/bin/sh $F/watchdog.sh >$D/watchdog-persist.log 2>&1 </dev/null & KDIR=$D INTERVAL=5 nohup /system/bin/sh $D/onscreen_keeper.sh >$D/keeper.out 2>&1 </dev/null & echo tt_on" 20
    say "Toutiao watchdog + keeper restarted"
    ;;
  *) echo "usage: $0 61b06572 {install | up | open <app> | open-all [HOLD] | broker-all [HOLD] | req <key> | broker-stop | list | status | toutiao}"; exit 2 ;;
esac
