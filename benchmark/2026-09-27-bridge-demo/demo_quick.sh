#!/usr/bin/env bash
# demo_quick.sh <SERIAL=61b06572> {prep|go|restore|open <key>} [HOLD=4.5]
#
# ~1-minute quick-switch bridge demo (Approach A = concurrent pre-launch + kill-top reveal), ending
# on the Toutiao feed with ZERO wait.
#
#   prep    : (off-camera, untimed) stop the Toutiao watchdog, keep the host, then:
#             (1) cold-start Toutiao once via the watchdog, wait for the feed, and stop the watchdog
#                 (its live app intentionally remains) so Toutiao sits ALIVE at the BOTTOM of the stack;
#             (2) start the on-screen keeper (keyguard-off / screen-awake, window-neutral);
#             (3) PRE-LAUNCH the 13 demo apps concurrently in REVERSE order, so the first go-app is on
#                 top and Toutiao is underneath everything. Idempotent (alive children are skipped).
#   go      : (on-camera, ~58 s at HOLD=4.5) each app is already running & stacked; show the top one,
#             HOLD, then kill it so the next reveals (~1-2 s). After the 13th app is killed, the
#             pre-warmed Toutiao feed is revealed INSTANTLY (0 s). Then restore the watchdog+keeper for
#             self-heal (this does a one-time maintenance cold-restart) so 61b is left on Toutiao.
#   restore : stop the demo apps + relaunch the Toutiao watchdog + keeper (standalone).
#   open<k> : ad-hoc — launch one app key onto the screen (goes on top).
#
# Why A works: each app runs in its own source_app_namespace; its bridge sub-window composites into
# the host surface; last-launched is on top; killing it reveals the one below in ~1-2 s (verified).
#
# HARD SAFETY: only 61b06572. 5cd1e3dd / 5ea34a45 (their own Toutiao demos) are hard-refused.
# The host (Toutiao-branded df385638) is never reinstalled, so restore is just a watchdog restart.
set -u

SERIAL="${1:-61b06572}"; CMD="${2:-}"
case "$SERIAL" in 61b06572*) SERIAL=61b0657200000000000000000324012c ;; esac
case "$SERIAL" in 5cd1e3dd*|5ea34a45*) echo "REFUSE: $SERIAL is a protected board."; exit 2 ;; esac
[ "$SERIAL" = 61b0657200000000000000000324012c ] || { echo "REFUSE: only 61b06572 (got $SERIAL)"; exit 2; }
S61="$SERIAL"

HDC="/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc"
HDC_MAC="/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh"
HERE="$(cd "$(dirname "$0")" && pwd)"
KEEPER_SRC="$HERE/../2026-09-27-device-provisioning/onscreen_keeper.sh"
D="/data/local/tmp/operator45"; F="$D/selfheal48"
STATE_DIR="$HOME/a2hlab-quick-demo/$S61"; STATE="$STATE_DIR/state.txt"
SHOTS="$HERE/quick-screens"; mkdir -p "$STATE_DIR" "$SHOTS"

# Default demo list (go order; visually strong first). termux removed (error dialog). Override with APPS=.
APPS_DEFAULT="wikipedia ooniprobe fd-com-kunzisoft-keepass-libre fd-com-amaze-filemanager fd-auxio antennapod aegis fd-netguard fd-AppManager fd-droidify fd-noice fd-fitness burgerking"
APPS="${APPS:-$APPS_DEFAULT}"
PKG_TT="com.ss.android.article.news"

dev(){ gtimeout "${2:-60}" "$HDC" -t "$S61" shell "$1" 2>&1 | tr -d '\r'; }
recv(){ gtimeout 40 "$HDC" -t "$S61" file recv "$1" "$2" >/dev/null 2>&1; }
say(){ printf '[quick %s] %s\n' "$(date +%H:%M:%S)" "$*"; }
alive(){ [ -n "$1" ] && [ "$(dev "ls -d /proc/$1 2>/dev/null && echo A || echo G" 10 | tail -1)" = A ]; }
zget(){ dev "hidumper -s WindowManagerService -a '-a' 2>/dev/null | grep -E '$1'" 12 | awk -v w="$1" '$1 ~ ("^" w){print $8; exit}'; }
dismiss_lock(){ dev "power-shell wakeup >/dev/null 2>&1; for i in 1 2; do uinput -T -m 600 1700 600 200 300 >/dev/null 2>&1; sleep 1; done" 12 >/dev/null; }
state_child(){ awk -v a="$1" '$1==a{print $3}' "$STATE" 2>/dev/null | tail -1; }
state_parent(){ awk -v a="$1" '$1==a{print $2}' "$STATE" 2>/dev/null | tail -1; }

launch_app(){ # $1=app -> "PARENT CHILD" on success (goes on top), empty on failure. Fresh --out.
  local app="$1" spawn line json parent child
  orb -m a2hlab bash -lc "rm -rf ~/a2hlab/board/$S61/quickdemo/$app" >/dev/null 2>&1
  spawn=$(orb -m a2hlab bash -lc "
    W=/home/dspfac/a2hlab/source-closure/verify
    cd ~/a2hlab/manifest && python3 tools/probe_source_app.py \
      --workspace \"\$W\" --westlake-source \"\$W/westlake\" \
      --framework-report ~/a2hlab/board/$S61/framework-1/device-report.json \
      --app-input ~/a2hlab/app-inputs/$app --app $app \
      --hdc $HDC_MAC --serial $S61 \
      --out ~/a2hlab/board/$S61/quickdemo/$app \
      --webview-input \"\$W/out/webview-input-source\" 2>&1" 2>&1)
  line=$(printf '%s\n' "$spawn" | grep 'SOURCE_APP_SPAWNED' | tail -1)
  [ -z "$line" ] && return 1
  json="${line#*SOURCE_APP_SPAWNED }"
  parent=$(printf '%s' "$json" | sed -n 's/.*"parent": *\([0-9]*\).*/\1/p')
  child=$(printf '%s' "$json" | sed -n 's/.*"child": *\([0-9]*\).*/\1/p')
  echo "$parent $child"
}

start_keeper(){
  gtimeout 60 "$HDC" -t "$S61" file send "$KEEPER_SRC" "$D/onscreen_keeper.sh" >/dev/null 2>&1
  dev "chmod +x $D/onscreen_keeper.sh; rm -f $D/keeper.stop $D/keeper.pid; KDIR=$D INTERVAL=5 nohup /system/bin/sh $D/onscreen_keeper.sh >$D/keeper.out 2>&1 </dev/null & echo on" 15 >/dev/null
}
warm_toutiao_bottom(){ # cold-start Toutiao via watchdog, wait READY, stop watchdog (live app stays). echoes news pid.
  dev "rm -f $F/stop $D/stop $D/fresh48/stop; rm -rf $F/lock; power-shell timeout -o 86400000 >/dev/null 2>&1; power-shell wakeup >/dev/null 2>&1; nohup /system/bin/sh $F/watchdog.sh >$D/watchdog-quick.log 2>&1 </dev/null & echo wd_on" 20 >/dev/null
  local st=""; for i in $(seq 1 40); do sleep 5; st=$(dev "cat $F/state 2>/dev/null" 10); say "  warming Toutiao t=$((i*5))s state=$st" >&2; echo "$st" | grep -q READY && break; done
  dev "touch $F/stop" 10 >/dev/null   # watchdog exits; line 164: live app intentionally remains
  sleep 1; dev "pidof $PKG_TT" 10 | tail -1
}

case "$CMD" in
  prep)
    gtimeout 20 "$HDC" list targets 2>/dev/null | grep -q "$S61" || { echo "FAIL: 61b06572 not connected"; exit 1; }
    say "clean slate (stop watchdog/keeper, kill source apps, keep host)"
    dev "touch $F/stop $D/stop $D/fresh48/stop $D/keeper.stop 2>/dev/null; for p in \$(cat $D/keeper.pid 2>/dev/null); do kill \$p 2>/dev/null; done; sleep 2; for p in \$(pidof $PKG_TT appspawn-x source_app_namespace touchfwd); do kill -9 \$p 2>/dev/null; done; sleep 1; echo host=\$(pidof org.westlake.imehost)" 30
    say "warming Toutiao at the BOTTOM (cold-start via watchdog, then stop watchdog; live app remains)"
    ttpid="$(warm_toutiao_bottom)"
    [ -n "$ttpid" ] && say "Toutiao warm at bottom (news pid=$ttpid)" || say "WARN: Toutiao did not reach READY; finale will cold-start (fallback)"
    start_keeper
    # launch the 13 apps in REVERSE go-order so APPS[0] ends on top, Toutiao stays underneath.
    rev=""; for a in $APPS; do rev="$a $rev"; done
    : > "$STATE.tmp"; echo "__toutiao__ - ${ttpid:-}" >> "$STATE.tmp"
    for app in $rev; do
      c=$(state_child "$app")
      if [ -n "$c" ] && alive "$c"; then say "skip $app (child $c alive)"; echo "$app $(state_parent "$app") $c" >> "$STATE.tmp"; continue; fi
      say "prep launching $app ..."
      pc=$(launch_app "$app") || { say "  $app PROBE FAILED"; echo "$app FAIL FAIL" >> "$STATE.tmp"; continue; }
      set -- $pc; echo "$app $1 $2" >> "$STATE.tmp"; say "  $app up (parent=$1 child=$2)"
    done
    mv "$STATE.tmp" "$STATE"
    live=0; for app in $APPS; do c=$(state_child "$app"); alive "$c" && live=$((live+1)); done
    mem=$(dev "grep MemAvailable /proc/meminfo" 10)
    say "PREP DONE: $live/$(echo $APPS | wc -w | tr -d ' ') apps stacked, Toutiao at bottom; $mem"
    say "next: $0 61b06572 go [HOLD]"
    ;;

  go)
    HOLD="${3:-4.5}"
    RENDER_WAIT="${RENDER_WAIT:-13}"     # first-frame wait after a fresh (re)launch
    REWARM_LAST="${REWARM_LAST:-0}"      # force fresh relaunch of the last N go-apps (deepest-buried,
                                         # most likely to have lost their surface). Trades ~30s/app for correctness.
    [ -f "$STATE" ] || { echo "FAIL: no prep state ($STATE). Run prep first."; exit 1; }
    dismiss_lock
    total=$(echo $APPS | wc -w | tr -d ' '); idx=0; shown=0; RESULTS=""
    t0=$(date +%s)
    for app in $APPS; do
      idx=$((idx+1))
      c=$(state_child "$app"); p=$(state_parent "$app")
      # A pre-warmed app that was buried a long time can be process-alive but surface-reclaimed (shows
      # the app below instead). Relaunch fresh when it's dead, or when it's among the deepest REWARM_LAST.
      deep=0; [ "$REWARM_LAST" -gt 0 ] && [ "$idx" -gt "$((total-REWARM_LAST))" ] && deep=1
      if ! alive "$c" || [ "$deep" = 1 ]; then
        say "[$idx/$total] $app -> fresh relaunch (dead or deep), wait ${RENDER_WAIT}s for first frame"
        [ -n "$p" ] && [ -n "$c" ] && dev "kill -9 $p $c 2>/dev/null" 10 >/dev/null
        pc=$(launch_app "$app") && { set -- $pc; p=$1; c=$2; sleep "$RENDER_WAIT"; }
      else
        sleep 1
      fi
      hostz=$(zget imehost0)
      shot="$SHOTS/$(printf '%02d' $idx)-$app.png"
      dev "rm -f /data/local/tmp/q.png; snapshot_display -t png -f /data/local/tmp/q.png >/dev/null 2>&1" 12 >/dev/null
      recv "/data/local/tmp/q.png" "$shot"
      onscr="no"; { [ -n "$hostz" ] && [ "$hostz" -ge 0 ] 2>/dev/null && alive "$c"; } && { onscr="yes"; shown=$((shown+1)); }
      say "[$idx/$total] $app on_screen=$onscr host_z=${hostz:-none} child=$c -> HOLD ${HOLD}s"
      RESULTS="$RESULTS\n$idx\t$app\t$([ "$onscr" = yes ] && echo ON_SCREEN || echo MISS)\t$shot"
      sleep "$HOLD"
      dev "kill -9 $p $c 2>/dev/null" 10 >/dev/null   # kill this app -> next (or Toutiao) reveals
      sleep 1.2
    done
    # --- finale: the pre-warmed Toutiao (bottom) should now be revealed with ZERO wait ---
    ttpid=$(state_child __toutiao__)
    if alive "$ttpid"; then
      reveal="INSTANT (0s, pre-warmed at bottom)"; say "FINALE: Toutiao revealed INSTANTLY (news pid=$ttpid alive)"
    else
      say "FINALE fallback: pre-warmed Toutiao gone -> cold-starting (~20-30s)"
      dev "rm -f $F/stop $D/stop $D/fresh48/stop; rm -rf $F/lock; nohup /system/bin/sh $F/watchdog.sh >$D/watchdog-quick.log 2>&1 </dev/null & echo wd" 20 >/dev/null
      cs0=$(date +%s); for i in $(seq 1 40); do sleep 5; st=$(dev "cat $F/state 2>/dev/null" 10); say "  toutiao cold t=$((i*5))s state=$st"; echo "$st" | grep -q READY && break; done
      dev "touch $F/stop" 10 >/dev/null; reveal="COLD-START ($(( $(date +%s)-cs0 ))s waited)"
    fi
    dev "rm -f /data/local/tmp/q.png; snapshot_display -t png -f /data/local/tmp/q.png >/dev/null 2>&1" 12 >/dev/null
    recv "/data/local/tmp/q.png" "$SHOTS/99-toutiao-finale.png"
    tHOLD_end=$(date +%s); sleep "${FINALE_HOLD:-$HOLD}"   # hold on the feed for the camera (FINALE_HOLD overrides)
    t1=$(date +%s)
    # restore watchdog + keeper for self-heal (one-time maintenance cold-restart of Toutiao)
    say "restoring watchdog + keeper for self-heal (may cold-restart Toutiao once)"
    dev "for p in \$(pidof appspawn-x source_app_namespace touchfwd); do kill -9 \$p 2>/dev/null; done; touch $D/keeper.stop; for p in \$(cat $D/keeper.pid 2>/dev/null); do kill \$p 2>/dev/null; done; sleep 2; rm -f $F/stop $D/stop $D/fresh48/stop $D/keeper.stop $D/keeper.pid; rm -rf $F/lock; power-shell timeout -o 86400000 >/dev/null 2>&1; power-shell wakeup >/dev/null 2>&1; nohup /system/bin/sh $F/watchdog.sh >$D/watchdog-restore.log 2>&1 </dev/null & KDIR=$D INTERVAL=5 nohup /system/bin/sh $D/onscreen_keeper.sh >$D/keeper.out 2>&1 </dev/null & echo restored" 20 >/dev/null
    rm -f "$STATE"
    echo ""
    echo "================ QUICK GO SUMMARY (61b06572) ================"
    printf 'idx\tapp\tresult\tshot\n'; printf "$RESULTS\n" | sed '/^$/d'
    echo "------------------------------------------------------------"
    echo "apps on-screen: $shown / $total"
    echo "app sequence wall time (first app shown -> last app killed): $((tHOLD_end-t0))s"
    echo "GO wall time incl finale hold: $((t1-t0))s (HOLD=${HOLD}s)"
    echo "Toutiao finale reveal: $reveal   (shot 99-toutiao-finale.png)"
    echo "watchdog+keeper restored -> 61b left on Toutiao with self-heal"
    echo "screens: $SHOTS"
    echo "============================================================"
    ;;

  restore)
    say "restoring Toutiao (stop demo apps, restart watchdog + keeper)"
    dev "for p in \$(pidof appspawn-x source_app_namespace touchfwd); do kill -9 \$p 2>/dev/null; done; touch $D/keeper.stop; for p in \$(cat $D/keeper.pid 2>/dev/null); do kill \$p 2>/dev/null; done; sleep 2" 25 >/dev/null
    dev "rm -f $F/stop $D/stop $D/fresh48/stop $D/keeper.stop $D/keeper.pid; rm -rf $F/lock; power-shell timeout -o 86400000 >/dev/null 2>&1; power-shell wakeup >/dev/null 2>&1; nohup /system/bin/sh $F/watchdog.sh >$D/watchdog-quick.log 2>&1 </dev/null & KDIR=$D INTERVAL=5 nohup /system/bin/sh $D/onscreen_keeper.sh >$D/keeper.out 2>&1 </dev/null & echo tt" 20 >/dev/null
    rm -f "$STATE"
    for i in $(seq 1 30); do sleep 5; st=$(dev "cat $F/state 2>/dev/null" 10); hostz=$(zget imehost0); say "  restore t=$((i*5))s state=$st host_z=${hostz:-none}"; echo "$st" | grep -q READY && [ -n "$hostz" ] && [ "$hostz" -ge 0 ] 2>/dev/null && { say "Toutiao restored"; break; }; done
    ;;

  open)
    KEY="${3:?usage: $0 61b06572 open <app-key>}"
    start_keeper; dismiss_lock
    say "open $KEY ..."; pc=$(launch_app "$KEY") || { echo "FAIL: could not launch $KEY"; exit 1; }
    set -- $pc; sleep 2; dismiss_lock
    dev "rm -f /data/local/tmp/q.png; snapshot_display -t png -f /data/local/tmp/q.png >/dev/null 2>&1" 12 >/dev/null
    recv "/data/local/tmp/q.png" "$SHOTS/open-$KEY.png"
    say "open $KEY up (parent=$1 child=$2); shot $SHOTS/open-$KEY.png"
    ;;

  *) echo "usage: $0 61b06572 {prep|go [HOLD]|restore|open <key>}"; exit 2 ;;
esac
