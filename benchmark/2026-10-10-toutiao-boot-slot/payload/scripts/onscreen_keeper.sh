#!/system/bin/sh
# onscreen_keeper.sh — keep the Toutiao host on the physical screen on an OH DAYU600 board.
#
# Root cause it defends against: OH's SceneBoard keyguard (SCBScreenLock) auto-fronts on any
# screen-off->on and covers the (alive) imehost0 host window, which the operator/watchdog is
# told never to touch once READY. This daemon owns the "keep it unlocked" job:
#   - re-asserts a max screen-off timeout + full brightness every tick (so the screen never idles
#     off, which is what re-arms the keyguard),
#   - if SCBScreenLock is fronted (ZOrd >= 0), swipe-dismisses it and re-fronts imehost0.
# It only acts when the lock is actually covering (event-driven), so it does not fight a real user.
#
# Layout mirrors the selfheal watchdog: nohup-resident, heartbeat log, stop-file honored.
KDIR="${KDIR:-/data/local/tmp/operator45}"
LOG="$KDIR/keeper.log"
STOP="$KDIR/keeper.stop"
HB="$KDIR/keeper.hb"
INTERVAL="${INTERVAL:-5}"
LOCK_WIN="SCBScreenLock"
HOST_WIN="imehost0"
mkdir -p "$KDIR"
echo "$$" > "$KDIR/keeper.pid"
log(){ echo "$(date '+%m-%d %H:%M:%S') $*" >> "$LOG"; }
log "keeper start pid=$$ interval=${INTERVAL}s"

# ZOrder of a window ($1) from WindowManagerService, or empty if the window is absent.
# Columns: WindowName DisplayId Pid WinId Type Mode Flag ZOrd ...  -> ZOrd is field 8.
# The board shell has no awk/tr (musl minimal rootfs), so split with the `set --` builtin.
zord(){
  line="$(hidumper -s WindowManagerService -a '-a' 2>/dev/null | grep "^$1" | head -1)"
  [ -z "$line" ] && return 0
  set -- $line
  echo "$8"
}

while :; do
  [ -f "$STOP" ] && { log "stop file present -> exit"; rm -f "$KDIR/keeper.pid"; exit 0; }
  date +%s > "$HB"

  # 1) never let the screen idle off (this is what re-arms the keyguard). Cheap, idempotent.
  power-shell timeout -o 86400000 >/dev/null 2>&1
  power-shell display -o 255      >/dev/null 2>&1

  # 2) only intervene if the keyguard is actually covering the host.
  lz="$(zord "$LOCK_WIN")"
  case "$lz" in
    ''|-*) : ;;                     # absent or ZOrd<0 => dismissed, nothing to do
    *)                              # ZOrd>=0 => keyguard is fronted, covering the app
      log "keyguard fronted (ZOrd=$lz) -> wake+swipe-dismiss"
      power-shell wakeup >/dev/null 2>&1
      # swipe up from lower-center to top; twice (some keyguards need a confirm swipe)
      uinput -T -m 600 1700 600 200 300 >/dev/null 2>&1; sleep 1
      uinput -T -m 600 1700 600 200 300 >/dev/null 2>&1; sleep 1
      hz="$(zord "$HOST_WIN")"
      log "after-dismiss lock=$(zord "$LOCK_WIN") host=$hz"
      ;;
  esac
  sleep "$INTERVAL"
done
