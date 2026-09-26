#!/system/bin/sh
# Generated for one operator45 deployment. No touch injection or focus calls while alive.
D=/data/local/tmp/operator45
C=/data/local/tmp/operator45-crashes
RUNTIME=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d
STAGE=/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d
SOCKET=/dev/unix/socket/A2HSourcec91d26bfb4db4fd5a002
UID45=20010053
mkdir -p "$D" "$C"
configure_maps() {
 echo 1048576 > /proc/sys/vm/max_map_count || return 1
 [ "$(cat /proc/sys/vm/max_map_count)" = 1048576 ] || return 1
 printf '%s max_map_count=1048576\n' "$(date +%s)" >> "$D/startup-settings.log"
}
# pidof includes npth fork children whose comm is work_thread. Preserve only the
# authoritative current app PID; report PPID=1 separately from other stale children.
prepare_crash_recorder() {
 test -d "$RUNTIME/private-tmp/crash42"
}
cleanup_toutiao() {
 clean_count=0; orphan_count=0
 for stale in $(pidof com.ss.android.article.news); do
  [ "$stale" != "$child" ] || continue
  [ -r "/proc/$stale/stat" ] || continue
  before=$(cat "/proc/$stale/stat")
  rest=${before##*) }; set -- $rest; state=$1; ppid45=$2
  [ "$state" != Z ] || continue
  printf '%s\n' "$before" >> "$dest/cleanup-before.txt"
  # Recheck identity immediately before signaling; never use broad killall.
  after=$(cat "/proc/$stale/stat" 2>/dev/null)
  [ "${before##*) }" = "${after##*) }" ] || {
   b=${before##*) }; a=${after##*) }; set -- $b; shift 19; birth_before=$1
   set -- $a; [ "$#" -ge 20 ] || continue; shift 19
   [ "$birth_before" = "$1" ] || continue
  }
  if kill -9 "$stale" 2>> "$dest/cleanup-errors.txt"; then
   clean_count=$((clean_count+1))
   [ "$ppid45" != 1 ] || orphan_count=$((orphan_count+1))
   printf 'pid=%s ppid=%s signal=9\n' "$stale" "$ppid45" >> "$dest/cleanup-killed.txt"
  fi
 done
 printf 'cleaned=%s ppid1=%s preserved=%s\n' "$clean_count" "$orphan_count" "$child" > "$dest/cleanup-summary.txt"
 pidof com.ss.android.article.news > "$dest/cleanup-pidof-after.txt"
}
if [ "$1" = --cleanup-only ]; then
 child=$(cat "$D/child.pid"); stamp=$(date +%Y%m%d-%H%M%S)
 dest="$C/manual-$stamp"; mkdir -p "$dest"; cleanup_toutiao
 printf 'manual\t%s\tNA\tcleanup_SIGKILL\tpid=%s\tcleaned=%s\tppid1=%s\n' "$stamp" "$child" "$clean_count" "$orphan_count" >> "$C/INDEX"
 cat "$dest/cleanup-summary.txt"
 exit 0
fi
[ ! -e "$D/stop" ] || exit 0
mkdir "$D/guard.lock" 2>/dev/null || exit 1
trap 'rmdir "$D/guard.lock" 2>/dev/null' EXIT
trap 'exit 0' TERM INT
configure_maps || exit 1
proc_start() {
 [ -r "/proc/$1/stat" ] || return 1
 value=$(cat "/proc/$1/stat")
 rest=${value##*) }
 set -- $rest
 [ "$1" != Z ] || return 1
 shift 19
 echo "$1"
}
uptime_s() { read up rest < /proc/uptime; echo "${up%%.*}"; }
HZ45=$(getconf CLK_TCK)
child=$(cat "$D/child.pid"); born=$(proc_start "$child")
if [ -n "$born" ]; then started=$((born/HZ45)); else started=unknown; fi
pending_tries=0
late_capture() {
 [ "$pending_tries" -gt 0 ] || return
 pending_tries=$((pending_tries-1))
 find /data/log/faultlog -type f -name "*-$pending_pid-*" > "$pending_dest/fault-paths-late.txt" 2>/dev/null
 while IFS= read -r file; do [ -f "$file" ] && cp "$file" "$pending_dest/"; done < "$pending_dest/fault-paths-late.txt"
 line=$(grep -F "[WESTLAKE-REAP] child $pending_pid " "$STAGE/parent.log" | tail -n 1)
 if [ -n "$line" ]; then
  printf "%s\n" "$line" > "$pending_dest/exit-signal.txt"
  cp "$STAGE/parent.log" "$pending_dest/parent-late.log"
  while IFS= read -r row; do
   case "$row" in
    "$pending_seq	"*) printf "%s\t%s\t%s\t%s\tpid=%s\tcleaned=%s\tppid1=%s\n" "$pending_seq" "$pending_stamp" "$pending_elapsed" "$line" "$pending_pid" "$pending_cleaned" "$pending_orphans";;
    *) printf "%s\n" "$row";;
   esac
  done < "$C/INDEX" > "$C/INDEX.tmp"
  mv "$C/INDEX.tmp" "$C/INDEX"
 fi
}
seq=0
[ ! -r "$D/sequence" ] || seq=$(cat "$D/sequence")
while [ ! -e "$D/stop" ]; do
 current=$(proc_start "$child")
 if [ -n "$current" ] && [ "$current" = "$born" ]; then late_capture; sleep 3; continue; fi
 seq=$((seq+1)); echo "$seq" > "$D/sequence"
 stamp=$(date +%Y%m%d-%H%M%S); epoch=$(date +%s)
 if [ "$started" = unknown ]; then elapsed=unknown; else elapsed=$(($(uptime_s)-started)); fi
 dest="$C/$seq-$stamp"; mkdir -p "$dest"
 printf 'pid=%s\nepoch=%s\nuptime=%s\nalive_seconds=%s\n' "$child" "$epoch" "$(uptime_s)" "$elapsed" > "$dest/exit.txt"
 cp "$RUNTIME/private-tmp/adapter_child_$child.stderr" "$dest/child.stderr" 2>"$dest/copy-errors.txt"
 cp "$STAGE/parent.log" "$dest/parent.log" 2>>"$dest/copy-errors.txt"
 find /data/log/faultlog -type f -name "*-$child-*" > "$dest/fault-paths.txt" 2>>"$dest/copy-errors.txt"
 while IFS= read -r file; do [ -f "$file" ] && cp "$file" "$dest/"; done < "$dest/fault-paths.txt"
 signal=$(grep -F "[WESTLAKE-REAP] child $child " "$dest/parent.log" | tail -n 1)
 [ -n "$signal" ] || signal=unknown
 cleanup_toutiao
 printf '%s\t%s\t%s\t%s\tpid=%s\tcleaned=%s\tppid1=%s\n' "$seq" "$stamp" "$elapsed" "$signal" "$child" "$clean_count" "$orphan_count" >> "$C/INDEX"
 pending_pid=$child; pending_dest=$dest; pending_seq=$seq; pending_stamp=$stamp; pending_elapsed=$elapsed; pending_tries=40; pending_cleaned=$clean_count; pending_orphans=$orphan_count
 [ ! -e "$D/stop" ] || break
 if ! configure_maps; then
  printf '%s sysctl_failed\n' "$(date +%s)" >> "$C/ERRORS"
  sleep 3; continue
 fi
 power-shell timeout -o 86400000 > "$dest/power.txt" 2>&1
 power-shell wakeup >> "$dest/power.txt" 2>&1
 # Reuse the live preloaded parent and all app data. Only recovery foregrounds the host.
 aa start -b org.westlake.imehost -a EntryAbility > "$dest/foreground.txt" 2>&1
 parent=$(cat "$D/parent.pid")
 if ! kill -0 "$parent" 2>/dev/null || [ ! -S "$SOCKET" ]; then
  rm -f "$SOCKET"
  nohup /data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/source_app_namespace /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d 20010053 /system/bin/sh /data/local/tmp/asx/run.sh >/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/parent.log 2>&1 </dev/null & echo $! > "$D/parent-start.txt"
  parent=$(cat "$D/parent-start.txt"); echo "$parent" > "$D/parent.pid"
  n=0; while [ ! -S "$SOCKET" ] && [ "$n" -lt 40 ]; do sleep .25; n=$((n+1)); done
 fi
 # The recorder directory must remain available before child creation.
 if ! prepare_crash_recorder >> "$D/startup-settings.log" 2>&1; then
  printf '%s recorder_directory_missing parent=%s\n' "$(date +%s)" "$parent" >> "$C/ERRORS"
  sleep 3; continue
 fi
 # A2 runs in the parent's app mount namespace before child creation.
 if [ -f "$D/preseed48.enabled" ]; then
  /bin/nsenter -t "$parent" -m /system/bin/sh /data/local/tmp/asx/preseed_metasec48.sh >> "$dest/preseed48.log" 2>&1
  hook_rc=$?
  printf '%s preseed48_rc=%s parent=%s\n' "$(date +%s)" "$hook_rc" "$parent" >> "$D/startup-settings.log"
  [ "$hook_rc" = 0 ] || { sleep 3; continue; }
 fi
 /data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/host_spawn /dev/unix/socket/A2HSourcec91d26bfb4db4fd5a002 /data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/request.bin > "$dest/spawn.txt" 2>&1
 next=$(sed -n 's/.*result=0 pid=\([0-9][0-9]*\).*/\1/p' "$dest/spawn.txt" | tail -n 1)
 if [ -z "$next" ]; then printf '%s spawn_failed\n' "$(date +%s)" >> "$C/ERRORS"; sleep 3; continue; fi
 child=$next; born=$(proc_start "$child")
 if [ -n "$born" ]; then started=$((born/HZ45)); else started=unknown; fi
 echo "$child" > "$D/child.pid"
 box="/proc/$child/root/data/local/tmp/noice_tap.$child"
 : > "$box"; chown "$UID45:$UID45" "$box"; chmod 666 "$box"; ln -sf "$box" /data/local/tmp/noice_tap
 printf 'child=%s\nparent=%s\nuptime=%s\nepoch=%s\n' "$child" "$parent" "$(uptime_s)" "$(date +%s)" > "$dest/restarted.txt"
 printf '%s\n' "$RUNTIME/private-tmp/adapter_child_$child.stderr" > "$D/child.stderr.path"
 sleep 3
done
