#!/system/bin/sh
# Outer-owned locked experiment. No HDC, lock management, broad signals or data deletion here.
set -eu
fail(){ printf 'BACK51_REFUSE %s\n' "$*" >&2; exit 2; }
[ "$#" = 7 ] || fail arguments
ACTION=$1; PARENT=$2; PBIRTH=$3; CHILD=$4; CBIRTH=$5; AUDIT=$6; WANT=$7
BOOT=c9436daa-b3ca-44dc-985f-9ee03445567a
RT=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d
STAGE=/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d
JAR=$RT/fw/adapter-runtime-bcp.jar
OLD=ea5d8b277f1207c928d289196876ad69505d73ab586815daccbda7080169523e
NEW=ae82e987b708441b3d6069ad04cb81e7846401a09fc9f34a84e854cc79783c33
SPAWNER=a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c
RUN=5a3aef638000e49f2a966b2179d57fe7628c29a4897921209fec539bd5dc1b79
case "$ACTION" in preflight|stop|apply|rollback|start|ready|spawn) :;; *) fail action;; esac
case "$AUDIT" in /data/local/tmp/back51-*) :;; *) fail audit_path;; esac
case "$AUDIT" in *..*|*[!a-zA-Z0-9_/-]*) fail audit_path;; esac
case "$WANT" in "$OLD"|"$NEW") :;; *) fail requested_SHA;; esac
for n in "$PARENT" "$PBIRTH" "$CHILD" "$CBIRTH"; do case "$n" in ''|*[!0-9]*) fail numeric_identity;; esac; done
[ "$PARENT" -gt 1 ] && [ "$PBIRTH" -gt 0 ] || fail parent_identity
back51_sha(){ sha256sum "$1" | cut -d' ' -f1; }
meta(){ stat -c '%u:%g|%a|%C' "$1"; }
birth(){ row=$(cat "/proc/$1/stat") || return 1; rest=${row##*) }; set -- $rest; [ "$#" -ge 20 ] || return 1; shift 19; printf '%s\n' "$1"; }
ppid(){ row=$(cat "/proc/$1/stat") || return 1; rest=${row##*) }; set -- $rest; [ "$#" -ge 20 ] || return 1; printf '%s\n' "$2"; }
base(){
 [ "$(cat /proc/sys/kernel/random/boot_id)" = "$BOOT" ] || fail boot
 [ "$(birth 5079)" = 8050 ] || fail host_birth
 [ "$(back51_sha "$RT/run.sh")" = "$RUN" ] || fail run_SHA
 [ "$(back51_sha "$STAGE/source_app_namespace")" = 60b89e1102225280e7a92831d07ebe0fa274323f1225cd7014c8813a8411f04c ] || fail namespace_SHA
 [ "$(back51_sha "$RT/appspawn-x")" = "$SPAWNER" ] || fail spawner_SHA
 [ "$(back51_sha "$STAGE/host_spawn")" = 019acf9ec9f1b701b793e883c95ea5808cf74338b02088b024cf3634c6b56279 ] || fail spawn_SHA
 [ "$(back51_sha "$STAGE/request.bin")" = 011a16259c7735dcb088fab44f569bc222675855eb722bcf945c48e06c0214ca ] || fail request_SHA
 [ "$(back51_sha "$RT/prepare_jit50.sh")" = b42a28e7a29a53c162a43ac25eaf52c24906f1afdd179c9414882772ccac34c8 ] || fail jit_SHA
 [ "$(stat -c '%u:%g' "$RT/app-data/com.ss.android.article.news")" = 20011300:20011300 ] || fail package_owner
 [ -f "$JAR" ] && [ ! -L "$JAR" ] || fail jar_type
 [ "$(meta "$JAR")" = '20011300:20011300|644|u:object_r:appdat:s0' ] || fail jar_meta
 dump=$(timeout 3 hidumper -s WindowManagerService -a '-a') || fail wms
 row=$(printf '%s\n' "$dump" | grep '^imehost0[[:space:]]') || fail host_window
 [ "$(printf '%s\n' "$row" | wc -l)" -eq 1 ] || fail host_duplicate
 set -- $row
 [ "${3:-}:${4:-}" = 5079:29 ] || fail host_pid_wid
 [ "$(grep -c '^export WL_PARENT_ID=29$' "$RT/run.sh")" = 1 ] || fail run_WID
}
owned(){
 [ "$1" -gt 1 ] && [ "$(birth "$1")" = "$2" ] || fail process_birth
 [ "$(back51_sha /proc/$1/exe)" = "$SPAWNER" ] || fail process_exe
 [ "$(stat -L -c '%d:%i' /proc/$1/root/data/local/tmp/asx/run.sh)" = "$(stat -c '%d:%i' "$RT/run.sh")" ] || fail process_runtime
 [ "$(readlink /proc/$1/ns/mnt)" != "$(readlink /proc/1/ns/mnt)" ] || fail private_ns
 uidrow=$(grep '^Uid:' /proc/$1/status) || fail uid_read
 set -- $uidrow
 [ "$#" = 5 ] || fail uid_fields
 case "$2:$3:$4:$5" in 0:0:0:0|20011300:20011300:20011300:20011300) :;; *) fail process_uid;; esac
}
children(){
 # Exact ps parser, including unknown children. Never treat read/parse failure as empty.
 rows=$(ps -A -o PID,PPID) || fail ps
 header=0
 while read -r p q extra; do
  if [ "$header" = 0 ]; then [ "$p:$q" = PID:PPID ] && [ -z "$extra" ] || fail ps_header; header=1; continue; fi
  case "$p:$q" in ''|*[!0-9:]*) fail ps_fields;; esac
  [ -n "$p" ] && [ -n "$q" ] && [ -z "$extra" ] || fail ps_fields
  if [ "$q" = "$PARENT" ]; then [ "$p" = "$CHILD" ] && [ "$CHILD" != 0 ] || fail unexpected_child; fi
  if [ "$CHILD" != 0 ] && [ "$q" = "$CHILD" ]; then fail unexpected_descendant; fi
 done <<ROWS
$rows
ROWS
 [ "$header" = 1 ] || fail empty_ps
}
stop_one(){
 owned "$1" "$2"
 if [ "$1" = "$CHILD" ]; then
  [ "$(ppid "$1")" = "$PARENT" ] || fail child_ppid_before_signal
  grep -Eq '^Uid:[[:space:]]+20011300[[:space:]]+20011300[[:space:]]+20011300[[:space:]]+20011300[[:space:]]*$' /proc/$1/status || fail child_uid_before_signal
 fi
 [ "$(birth "$1")" = "$2" ] || fail signal_birth_changed
 printf 'BACK51_SIGNAL_INTENT pid=%s birth=%s signal=TERM\n' "$1" "$2"
 kill -TERM "$1" || fail term
 i=0
 while [ -e "/proc/$1/stat" ]; do
  [ "$(birth "$1")" = "$2" ] || fail pid_reused
  i=$((i+1)); [ "$i" -le 10 ] || fail term_timeout_no_escalation
  sleep 1
 done
}
absent(){
 [ ! -e /proc/$PARENT/stat ] || fail old_parent_present
 [ "$CHILD" = 0 ] || [ ! -e /proc/$CHILD/stat ] || fail old_child_present
 # Refuse any other live consumer of this private runtime, including unplanned parent.
 for d in /proc/[0-9]*; do
  [ -e "$d/root/data/local/tmp/asx/run.sh" ] || continue
  x=$(stat -L -c '%d:%i' "$d/root/data/local/tmp/asx/run.sh") || fail consumer_read
  [ "$x" != "$(stat -c '%d:%i' "$RT/run.sh")" ] || fail unexpected_runtime_consumer
 done
}
base
case "$ACTION" in
 preflight|stop)
  owned "$PARENT" "$PBIRTH"; children
  [ "$(back51_sha "$JAR")" = "$WANT" ] || fail expected_JAR
  [ "$(back51_sha /proc/$PARENT/root/data/local/tmp/asx/fw/adapter-runtime-bcp.jar)" = "$WANT" ] || fail parent_JAR
  if [ "$CHILD" != 0 ]; then owned "$CHILD" "$CBIRTH"; [ "$(ppid "$CHILD")" = "$PARENT" ] || fail child_ppid; fi
  if [ "$ACTION" = stop ]; then
   if [ "$CHILD" != 0 ]; then stop_one "$CHILD" "$CBIRTH"; fi
   CHILD=0; children; stop_one "$PARENT" "$PBIRTH"; absent
  fi;;
 apply|rollback)
  absent
  [ -d "$AUDIT" ] && [ ! -L "$AUDIT" ] || fail audit_dir
  if [ "$ACTION" = apply ]; then
   [ "$WANT" = "$OLD" ] || fail apply_before
   [ "$(back51_sha "$JAR")" = "$OLD" ] || fail original_SHA
   [ ! -e "$AUDIT/original.jar" ] || fail backup_exists
   cp -p "$JAR" "$AUDIT/original.jar" || fail backup
   [ "$(back51_sha "$AUDIT/original.jar")" = "$OLD" ] || fail backup_SHA
   SOURCE=$AUDIT/candidate.jar; AFTER=$NEW
  else
   [ "$WANT" = "$NEW" ] || fail rollback_before
   SOURCE=$AUDIT/original.jar; AFTER=$OLD
  fi
  [ -f "$SOURCE" ] && [ ! -L "$SOURCE" ] && [ "$(back51_sha "$SOURCE")" = "$AFTER" ] || fail source_SHA
  [ "$(back51_sha "$JAR")" = "$WANT" ] || fail before_SHA
  BEFORE=$(stat -c '%d:%i|%u:%g|%a|%C' "$JAR") || fail before_meta
  TEMP=$JAR.back51-stage
  [ ! -e "$TEMP" ] && [ ! -L "$TEMP" ] || fail stage_exists
  cp "$SOURCE" "$TEMP" || fail stage_copy
  chown 20011300:20011300 "$TEMP" && chmod 644 "$TEMP" && chcon u:object_r:appdat:s0 "$TEMP" || fail stage_metadata
  [ "$(back51_sha "$TEMP")" = "$AFTER" ] && [ "$(meta "$TEMP")" = '20011300:20011300|644|u:object_r:appdat:s0' ] || fail stage_readback
  base; absent
  [ "$(back51_sha "$JAR")" = "$WANT" ] && [ "$(stat -c '%d:%i|%u:%g|%a|%C' "$JAR")" = "$BEFORE" ] || fail CAS
  printf 'BACK51_RENAME_INTENT before=%s after=%s\n' "$WANT" "$AFTER"
  mv "$TEMP" "$JAR" || fail rename
  [ "$(back51_sha "$JAR")" = "$AFTER" ] && [ "$(meta "$JAR")" = '20011300:20011300|644|u:object_r:appdat:s0' ] || fail final_readback;;
 start)
  absent
  [ "$(back51_sha "$JAR")" = "$WANT" ] || fail start_JAR
  [ -d "$AUDIT" ] && [ ! -L "$AUDIT" ] && [ ! -e "$AUDIT/parent.log" ] || fail fresh_parent_log
  # Original real-start-parent-bounded argv, without its unnecessary sed or log truncation.
  nohup "$STAGE/source_app_namespace" "$RT" 20011300 /system/bin/sh /data/local/tmp/asx/run.sh >"$AUDIT/parent.log" 2>&1 </dev/null &
  new=$!
  printf 'BACK51_NEW_PARENT_LAUNCHED pid=%s\n' "$new";;
 ready)
  [ "$CHILD" = 0 ] || fail ready_requires_zero_child
  owned "$PARENT" "$PBIRTH"; children
  [ "$(back51_sha /proc/$PARENT/root/data/local/tmp/asx/fw/adapter-runtime-bcp.jar)" = "$WANT" ] || fail ready_JAR
  grep -q 'Listening on /dev/unix/socket/A2HSourcec91d26bfb4db4fd5a002' "$AUDIT/parent.log" || fail parent_not_ready
  printf 'BACK51_PARENT_READY pid=%s birth=%s\n' "$PARENT" "$PBIRTH";;
 spawn)
  [ "$CHILD" = 0 ] || fail spawn_requires_zero_child
  owned "$PARENT" "$PBIRTH"; children
  [ "$(back51_sha "$JAR")" = "$WANT" ] && [ "$(back51_sha /proc/$PARENT/root/data/local/tmp/asx/fw/adapter-runtime-bcp.jar)" = "$WANT" ] || fail spawn_JAR
  timeout 8 /bin/nsenter -t "$PARENT" -m -- /system/bin/sh /data/local/tmp/asx/prepare_jit50.sh || fail JIT
  base; owned "$PARENT" "$PBIRTH"; children
  if "$STAGE/host_spawn" /dev/unix/socket/A2HSourcec91d26bfb4db4fd5a002 "$STAGE/request.bin"; then
   printf 'BACK51_HOST_SPAWN_RC=0\n'
  else
   spawn_rc=$?; printf 'BACK51_HOST_SPAWN_RC=%s\n' "$spawn_rc"; exit "$spawn_rc"
  fi;;
esac
printf 'BACK51_VERIFIED action=%s boot=%s\n' "$ACTION" "$BOOT"
