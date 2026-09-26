#!/system/bin/sh
D=/data/local/tmp/operator45
F=$D/selfheal48
C=/data/local/tmp/operator45-crashes
RUNTIME=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d
STAGE=/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d
SOCKET=/dev/unix/socket/A2HSourcec91d26bfb4db4fd5a002
PKG=com.ss.android.article.news
child=; parent=
mkdir -p "$F" "$C"
[ ! -e "$F/stop" ] || exit 0
uptime_s(){ read up rest < /proc/uptime; echo "${up%%.*}"; }
birth(){
 [ -n "$1" ] && [ -r "/proc/$1/stat" ] || return 1
 v=$(cat "/proc/$1/stat"); rest=${v##*) }; set -- $rest
 [ "$1" != Z ] || return 1
 shift 19; echo "$1"
}
# Single supervisor. A stale lock is reclaimed only after PID/birth fails.
if ! mkdir "$F/lock" 2>/dev/null; then
 read owner owner_birth < "$F/lock/owner" || exit 2
 [ "$(birth "$owner")" != "$owner_birth" ] || exit 2
 rm -f "$F/lock/owner"; rmdir "$F/lock" || exit 2
 mkdir "$F/lock" || exit 2
fi
echo "$$ $(birth $$)" > "$F/lock/owner"
trap 'rm -f "$F/lock/owner"; rmdir "$F/lock" 2>/dev/null' EXIT
trap 'touch "$F/stop"; exit 0' TERM INT
echo $$ > "$F/guardian.pid"
touch "$D/stop" "$D/fresh48/stop"
event(){ echo "$(uptime_s) $*" >> "$F/events.log"; }
clean_all(){
 cleaned=0; orphans=0
 seen=" "
 for p in $child $parent $(pidof "$PKG" appspawn-x); do
  case "$seen" in *" $p "*) continue;; esac
  seen="$seen$p "
  b=$(birth "$p"); [ -n "$b" ] || continue
  row=$(cat "/proc/$p/stat"); rest=${row##*) }; set -- $rest; pp=$2
  [ "$(birth "$p")" = "$b" ] || continue
  kill -9 "$p" 2>/dev/null && cleaned=$((cleaned+1))
  [ "$pp" != 1 ] || orphans=$((orphans+1))
 done
 n=0
 while [ -n "$(pidof "$PKG" appspawn-x)" ] && [ "$n" -lt 20 ]; do sleep .1; n=$((n+1)); done
 [ -z "$(pidof "$PKG" appspawn-x)" ] || return 1
 [ -z "$(birth "$child")" ] && [ -z "$(birth "$parent")" ] || return 1
 avail=$(sed -n 's/^MemAvailable: *\([0-9]*\).*/\1/p' /proc/meminfo)
 event "CLEANED count=$cleaned ppid1=$orphans app=0 parent=0 available_kib=$avail"
 [ "$avail" -gt 1048576 ]
}
prepare_profile(){
 if [ "$mode" = fresh ]; then
  # Preserve the original consent data once. Rotate only our disposable profiles.
  if [ ! -e "$RUNTIME/operator-selfheal-original" ]; then
   old="$RUNTIME/operator-selfheal-original"
  else
   old="$RUNTIME/operator-selfheal-previous"
   rm -rf "$old" || return 1
  fi
  mkdir -p "$old" || return 1
  for p in app-data data webview-t-data; do
   [ ! -e "$RUNTIME/$p" ] || mv "$RUNTIME/$p" "$old/$p" || return 1
  done
 fi
 mkdir -p "$RUNTIME/data/dalvik-cache/arm64" "$RUNTIME/app-data/$PKG/code_cache" "$RUNTIME/app-data/$PKG/app_webview" "$RUNTIME/app-data/org.westlake.imehost" "$RUNTIME/webview-t-data" || return 1
 chown -R 20010053:20010053 "$RUNTIME/data" "$RUNTIME/app-data" "$RUNTIME/webview-t-data"
 chcon -R u:object_r:data_app_el2_file:s0 "$RUNTIME/app-data/$PKG"
}
archive_exit(){
 # Cleanup is complete before any subsequent launch; capture original logs before overwrite.
 stamp=$(date +%Y%m%d-%H%M%S); dest="$C/selfheal-$seq-$stamp"; mkdir -p "$dest"
 cp "$F/instance.txt" "$dest/instance.txt"
 cp "$RUNTIME/private-tmp/adapter_child_$child.stderr" "$dest/child.stderr" 2>"$dest/copy-errors.txt"
 cp "$STAGE/parent.log" "$dest/parent.log" 2>>"$dest/copy-errors.txt"
 hex=$(printf '%x' "$child")
 find "$RUNTIME/private-tmp/crash42" -type f -name "event-$hex-*" > "$dest/fault-paths.txt"
 find /data/log/faultlog -type f -name "*-$child-*" >> "$dest/fault-paths.txt" 2>/dev/null
 while IFS= read -r f; do cp "$f" "$dest/" 2>>"$dest/copy-errors.txt"; done < "$dest/fault-paths.txt"
 reap=$(grep -F "[WESTLAKE-REAP] child $child " "$dest/parent.log" | tail -1)
 printf '%s\t%s\t%s\t%s\t%s\tpid=%s\tparent=%s\tcleaned=%s\tppid1=%s\tmode=%s\n' "selfheal-$seq" "$stamp" "$elapsed" "$reason" "${reap:-unknown}" "$child" "$parent" "$cleaned" "$orphans" "$mode" >> "$C/INDEX"
 echo "$detected" > "$F/recovery-start"
 event "EXIT seq=$seq pid=$child elapsed=$elapsed reason=$reason archive=$dest"
}
seq=$(cat "$F/sequence" 2>/dev/null); seq=${seq:-0}
mode=fresh; failures=0
while [ ! -e "$F/stop" ]; do
 clean_all || { echo CLEANUP_BLOCKED > "$F/state"; touch "$F/stop"; break; }
 seq=$((seq+1)); echo "$seq" > "$F/sequence"
 prepare_profile || { echo PROFILE_BLOCKED > "$F/state"; touch "$F/stop"; break; }
 echo 1048576 > /proc/sys/vm/max_map_count
 [ "$(cat /proc/sys/vm/max_map_count)" = 1048576 ] || break
 timeout 5 power-shell timeout -o 86400000 > "$F/power.log" 2>&1
 timeout 5 power-shell wakeup >> "$F/power.log" 2>&1
 timeout 5 aa start -b org.westlake.imehost -a EntryAbility > "$F/foreground.log" 2>&1
 rm -f "$SOCKET"
 timeout 15 /system/bin/sh "$F/start-parent.sh" > "$F/parent-start.txt"
 parent=$(cat "$F/parent-start.txt")
 n=0; while [ ! -S "$SOCKET" ] && [ "$n" -lt 40 ]; do sleep .25; n=$((n+1)); done
 [ -S "$SOCKET" ] || { event PARENT_FAILED; clean_all; echo PARENT_BLOCKED > "$F/state"; touch "$F/stop"; break; }
 timeout 15 /system/bin/sh "$F/spawn.sh" > "$F/spawn.txt" 2>&1
 child=$(sed -n 's/.*result=0 pid=\([0-9][0-9]*\).*/\1/p' "$F/spawn.txt" | tail -1)
 born=$(birth "$child"); [ -n "$born" ] || { event SPAWN_FAILED; clean_all; echo SPAWN_BLOCKED > "$F/state"; touch "$F/stop"; break; }
 started=$(uptime_s); ready=0; feed_count=0; last_action=0; last_metrics=0
 echo "$child" > "$D/child.pid"; echo "$parent" > "$D/parent.pid"
 echo "$RUNTIME/private-tmp/adapter_child_$child.stderr" > "$D/child.stderr.path"
 printf 'child=%s\nparent=%s\nbirth=%s\nstarted=%s\nseq=%s\nmode=%s\n' "$child" "$parent" "$born" "$started" "$seq" "$mode" > "$F/instance.txt"
 cp "$F/instance.txt" "$F/instance-$seq.txt"
 echo BOOTSTRAP > "$F/state"; event "START seq=$seq child=$child parent=$parent mode=$mode"
 hex=$(printf '%x' "$child")
 while [ ! -e "$F/stop" ]; do
  now=$(uptime_s); reason=process_exit
  [ "$(birth "$child")" = "$born" ] || break
  # Signal6 can be a survived background event. Only recorded SIG11 forces cleanup.
  fatal=0
  for meta in "$RUNTIME"/private-tmp/crash42/event-"$hex"-*.txt; do
   [ -f "$meta" ] || continue
   grep -q 'signal=0xb$' "$meta" || continue
   stamphex=$(sed -n 's/^\[CRASH42\] monotonic_ns=//p' "$meta")
   [ -n "$stamphex" ] && [ "$((stamphex/1000000000))" -ge "$started" ] && fatal=1
  done
  if [ "$fatal" = 1 ]; then reason=recorded_SIG11; break; fi
  if [ $((now-last_metrics)) -ge 10 ]; then
   apps=$(pidof "$PKG" | wc -w); parents=$(pidof appspawn-x | wc -w)
   avail=$(sed -n 's/^MemAvailable: *\([0-9]*\).*/\1/p' /proc/meminfo)
   rss=$(sed -n 's/^VmRSS:[[:space:]]*\([0-9]*\).*/\1/p' /proc/$child/status)
   echo "$now seq=$seq child=$child apps=$apps parents=$parents rss_kib=$rss available_kib=$avail" >> "$F/metrics.log"
   if [ "$apps" -gt 1 ] || [ "$parents" -gt 1 ]; then reason=process_count_violation; break; fi
   last_metrics=$now
  fi
  # Once ready, absolutely no screenshot/touch/focus action: operator owns UI.
  if [ "$ready" = 0 ]; then
   label=unknown
   if timeout 4 snapshot_display -t png -f "$F/current.png" > "$F/snapshot.log" 2>&1; then label=$(timeout 2 "$F/screen-gate" "$F/current.png"); fi
   echo "$now seq=$seq label=$label" >> "$F/ui.log"
   [ "$(birth "$child")" = "$born" ] || { reason=process_exit; break; }
   if [ $((now-last_action)) -ge 10 ]; then
    case "$label" in
     privacy) cp "$F/current.png" "$F/consent-$seq.png"; timeout 3 uinput -T -d 600 1273 -u 600 1273; last_action=$now; event "CONSENT seq=$seq";;
     login) cp "$F/current.png" "$F/login-$seq.png"; timeout 3 uinput -T -d 55 92 -u 55 92; last_action=$now; event "DISMISS_LOGIN seq=$seq";;
    esac
   fi
   if [ "$label" = feed ]; then feed_count=$((feed_count+1)); else feed_count=0; fi
   if [ "$feed_count" -ge 2 ]; then
    ready=1; failures=0; cp "$F/current.png" "$F/feed-$seq.png"; echo READY > "$F/state"
    recovery=$(cat "$F/recovery-start" 2>/dev/null); recovery_s=initial; [ -z "$recovery" ] || recovery_s=$((now-recovery))
    event "READY seq=$seq child=$child startup_s=$((now-started)) recovery_s=$recovery_s"
   elif [ $((now-started)) -ge 180 ]; then reason=bootstrap_timeout; break; fi
  fi
  sleep 3
 done
 [ ! -e "$F/stop" ] || break
 detected=$(uptime_s); elapsed=$((detected-started))
 clean_all || { echo CLEANUP_BLOCKED > "$F/state"; touch "$F/stop"; break; }
 archive_exit
 [ "$elapsed" -ge 180 ] && [ "$ready" = 1 ] || mode=fresh
 failures=$((failures+1))
 # Bounded backoff rather than an orphan-generating tight relaunch loop.
 if [ "$failures" -ge 3 ]; then event "BACKOFF seconds=30"; sleep 30; fi
 sleep 1
done
event STOPPED
# stop prevents relaunch and releases lock; live app intentionally remains for operator.
