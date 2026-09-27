#!/usr/bin/env bash
# provision_toutiao.sh <SERIAL> [--with-aot]
# Idempotent, board-adaptive provisioner: deploys the Toutiao delivery bundle to one OH 6.1.0.31
# DAYU600 board and brings up the feed on the physical screen with the selfheal watchdog.
# Scales to N boards: `for SN in $(hdc list targets); do provision_toutiao.sh $SN; done`.
# NEVER touches 61b06572 (user demo) — hard-skipped.
#
# Board-adaptation: host is (re)installed every run; WL_PARENT_ID is resolved dynamically at each
# launch by the bundled start-parent.sh (queries hidumper for the live imehost0 window id), so the
# same bundle works on any board regardless of its host window id. The RT is self-contained (brings
# its own libart/boot/fw/appspawn-x); it only needs an OH 6.1.0.31 DAYU600 firmware base.
# On-screen adaptation: OH's SceneBoard keyguard (SCBScreenLock) auto-fronts on any screen-off->on
# and covers the (alive) app, so a board that idles just LOOKS black. The bundled onscreen_keeper.sh
# runs as a resident daemon that keeps the screen from idling off and swipe-dismisses the keyguard
# whenever it re-fronts — this is what keeps the feed persistently on the physical screen.
set -u
SN="${1:?usage: provision_toutiao.sh <SERIAL> [--with-aot]}"
WITH_AOT=0; [ "${2:-}" = "--with-aot" ] && WITH_AOT=1
SKIP_SN="61b0657200000000000000000324012c"   # user's Toutiao demo board — never touch
if [ "$SN" = "$SKIP_SN" ]; then echo "SKIP $SN (demo board, protected)"; exit 0; fi

HDC="/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc"
BUNDLE="$(cd "$(dirname "$0")/bundle" && pwd)"
RT="/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d"
STAGE="/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d"
D="/data/local/tmp/operator45"; F="$D/selfheal48"
PROV="/data/local/tmp/tt-prov"
OUT="$HOME/a2hlab-provision/$SN"; mkdir -p "$OUT"
dev(){ gtimeout "${2:-60}" "$HDC" -t "$SN" shell "$1" 2>&1 | tr -d '\r'; }
send(){ gtimeout "${3:-120}" "$HDC" -t "$SN" file send "$1" "$2" >/dev/null 2>&1; }
recv(){ gtimeout 30 "$HDC" -t "$SN" file recv "$1" "$2" >/dev/null 2>&1; }
say(){ printf '[%s] %s\n' "$SN" "$*"; }
fail(){ say "FAIL: $*"; echo "FAIL" > "$OUT/result"; exit 1; }

# 0. reachability
gtimeout 20 "$HDC" list targets 2>/dev/null | grep -q "$SN" || fail "board not connected"
say "provisioning start"

# 1. clean (idempotent): stop watchdog + on-screen keeper, kill app/appspawn, clear lock/stop
dev "mkdir -p $F; touch $F/stop $D/stop $D/fresh48/stop $D/keeper.stop 2>/dev/null; for p in \$(cat $D/keeper.pid 2>/dev/null); do kill \$p 2>/dev/null; done; sleep 2; for p in \$(pidof com.ss.android.article.news appspawn-x); do kill -9 \$p 2>/dev/null; done; rm -rf $F/lock; rm -f $D/keeper.pid; sleep 1; echo cleaned" 30 >/dev/null

# 2. install host (idempotent — replaces whatever host is there)
send "$BUNDLE/source-host.hap" "/data/local/tmp/tt-host.hap"
r=$(dev "bm install -p /data/local/tmp/tt-host.hap" 40)
echo "$r" | grep -q "successfully" || say "WARN host install: $(echo "$r" | tail -1)"

# 3. deploy RT (extract tt-rt.tar into RT; preserve owners), + AOT if requested
dev "rm -rf $PROV; mkdir -p $PROV $RT" 20 >/dev/null
send "$BUNDLE/tt-rt.tar" "$PROV/tt-rt.tar" 300
r=$(dev "tar xpf $PROV/tt-rt.tar -C $RT && echo RT_OK" 120)
echo "$r" | grep -q RT_OK || fail "RT extract: $(echo "$r" | tail -2)"
if [ "$WITH_AOT" = 1 ]; then
  dev "mkdir -p $RT/oat/arm64" 15 >/dev/null
  for f in toutiao.art toutiao.odex toutiao.vdex; do send "$BUNDLE/aot/$f" "$RT/oat/arm64/$f" 300; done
  dev "chown -R 20010053:20010053 $RT/oat; echo AOT_OK" 20 >/dev/null; say "AOT deployed"
fi

# 4. deploy STAGE
dev "mkdir -p $STAGE" 15 >/dev/null
send "$BUNDLE/tt-stage.tar" "$PROV/tt-stage.tar"
dev "tar xpf $PROV/tt-stage.tar -C $STAGE && chmod +x $STAGE/source_app_namespace $STAGE/host_spawn 2>/dev/null; echo STAGE_OK" 30 >/dev/null

# 5. deploy watchdog
send "$BUNDLE/tt-wd.tar" "$PROV/tt-wd.tar"
dev "tar xpf $PROV/tt-wd.tar -C $F && chmod +x $F/watchdog.sh $F/start-parent.sh $F/spawn.sh $F/screen-gate $F/onscreen_keeper.sh 2>/dev/null; echo WD_OK" 30 >/dev/null

# 6. ownership + SELinux + the mount-point dirs source_app_namespace needs.
#    source_app_namespace binds $RT/private-tmp->/data/local/tmp then $RT->/data/local/tmp/asx,
#    so $RT/private-tmp/asx must exist as a mount point (+ private-tmp/app-data/i18n owned by the uid).
dev "mkdir -p $RT/private-tmp/asx; chown -R 20010053:20010053 $RT/private-tmp; chown 20010053:20010053 $RT; restorecon -R $RT 2>/dev/null; restorecon -R $STAGE 2>/dev/null; echo PERM_OK" 40 >/dev/null

# 7. config + start watchdog (cold-starts Toutiao; start-parent.sh resolves WL_PARENT_ID for THIS board)
#    and the on-screen keeper (dismisses the OH keyguard whenever it re-fronts and covers the app;
#    re-asserts a max screen-off timeout so the screen never idles off and re-arms the keyguard).
dev "rm -f $F/stop $D/stop $D/fresh48/stop $D/keeper.stop $D/keeper.pid; rm -rf $F/lock; echo 1048576 > /proc/sys/vm/max_map_count; power-shell timeout -o 86400000 >/dev/null 2>&1; power-shell wakeup >/dev/null 2>&1; nohup /system/bin/sh $F/watchdog.sh >$D/watchdog-prov.log 2>&1 </dev/null & KDIR=$D INTERVAL=5 nohup /system/bin/sh $F/onscreen_keeper.sh >$D/keeper.out 2>&1 </dev/null & echo started" 20 >/dev/null
say "watchdog + on-screen keeper started, waiting for READY + feed on screen ..."

# 8. wait for the feed on the physical screen (up to ~150s).
#    PRIMARY signal = window ZOrder: the host window (imehost0) fronted (ZOrd>=0) AND the OH keyguard
#    (SCBScreenLock) dismissed (ZOrd<0 or absent), together with watchdog state=READY. This is the
#    definitive "app visible, nothing covering it" state and is what the keeper maintains.
#    screen-gate is kept only as a SECONDARY confirmation: it false-negatives (=unknown) on
#    video-heavy feed scroll positions, so it must NOT be the pass/fail gate on its own.
onscreen=0; gate=""; for i in $(seq 1 30); do
  sleep 5
  st=$(dev "cat $F/state 2>/dev/null" 10)
  zz=$(dev "hidumper -s WindowManagerService -a '-a' 2>/dev/null | grep -E 'SCBScreenLock|imehost0'" 12)
  hostz=$(echo "$zz" | awk '/imehost0/{print $8; exit}')
  lockz=$(echo "$zz" | awk '/SCBScreenLock/{print $8; exit}')
  dev "rm -f /data/local/tmp/tt-shot.png; snapshot_display -t png -f /data/local/tmp/tt-shot.png >/dev/null 2>&1" 15 >/dev/null
  gate=$(dev "$F/screen-gate /data/local/tmp/tt-shot.png 2>/dev/null" 10 | tail -1)
  say "  t=$((i*5))s state=$st host_z=${hostz:-none} lock_z=${lockz:-none} gate=$gate"
  if echo "$st" | grep -q READY && [ -n "$hostz" ] && [ "$hostz" -ge 0 ] 2>/dev/null \
     && { [ -z "$lockz" ] || [ "$lockz" -lt 0 ] 2>/dev/null; }; then onscreen=1; break; fi
done
recv "/data/local/tmp/tt-shot.png" "$OUT/toutiao-screen.png"

# 9. verdict — on-screen (ZOrder) is authoritative; note the gate result for the record.
if [ "$onscreen" = 1 ]; then
  say "PASS — Toutiao on physical screen (host fronted, keyguard dismissed; gate=$gate; shot: $OUT/toutiao-screen.png)"
  echo "PASS" > "$OUT/result"; exit 0
else
  dev "tail -20 $RT/private-tmp/adapter_child_*.stderr 2>/dev/null | tail -20" 15 > "$OUT/last-child-stderr.txt" 2>/dev/null
  fail "not on screen (state=$st host_z=${hostz:-none} lock_z=${lockz:-none} gate=$gate); see $OUT/toutiao-screen.png + last-child-stderr.txt"
fi
