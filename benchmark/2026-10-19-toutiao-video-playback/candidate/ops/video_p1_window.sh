#!/bin/bash
# Outer-run board window for the Toutiao video P1 change (61b only). Host side; talks to the board via hdc.
# Default is PRINT-ONLY: every board command is echoed. Set EXECUTE=1 to run (outer, holding the 61b lock).
#   video_p1_window.sh preflight|stage|apply|verify|rollback
# Raw outputs are tee'd to RAW (private persistent dir); never edit them in place.
set -euo pipefail
SERIAL=${SERIAL:-61b0657200000000000000000324012c}
HERE=$(cd "$(dirname "$0")/.." && pwd)                                   # candidate/
RAW=${RAW:-$HOME/.local/share/westlake/toutiao-video-p1-window/$(date +%Y%m%dT%H%M%S)}
RT=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d  # physical root, = /data/local/tmp/asx inside the private namespace
STAGE=/data/local/tmp/ttvideo-p1-stage
DSO=libopensles_android_compat.so
DSO_SHA=9f558aaf1d48cedbc10e6774073d71177efb6d1e196fe528f0203505d1ee761f
NORM_BEFORE=ea575abea86e8afd0aebbbb6cdc1900df3ff40c5d9c40ed290e8ac1b1f9c1cf4   # run.sh d3518cef with WL_PARENT_ID normalized
NORM_AFTER=db82cc159412026d274300a4f0a80ac8bb65cfe53c69d11690cfeeb664b95561    # candidate run.sh with WL_PARENT_ID normalized
NORM='s/^export WL_PARENT_ID=[0-9]*$/export WL_PARENT_ID=N/'
EDIT='s#^\(export LD_PRELOAD=.*libwebview_bionic_shim\.so\)$#\1:/data/local/tmp/asx/libopensles_android_compat.so#'
UNEDIT='/^export LD_PRELOAD=/s#:/data/local/tmp/asx/libopensles_android_compat\.so$##'
mkdir -p "$RAW"
b() {  # b NAME 'board shell command'
  local n=$1; shift
  echo "[$n] hdc -t $SERIAL shell \"$*\"" | tee -a "$RAW/commands.log"
  [ "${EXECUTE:-0}" = 1 ] || return 0
  hdc -t "$SERIAL" shell "$*" > "$RAW/$n.stdout.txt" 2> "$RAW/$n.stderr.txt"; echo $? > "$RAW/$n.rc.txt"
  cat "$RAW/$n.stdout.txt"
}
h() {  # h NAME host command...
  local n=$1; shift
  echo "[$n] $*" | tee -a "$RAW/commands.log"
  [ "${EXECUTE:-0}" = 1 ] || return 0
  "$@" > "$RAW/$n.stdout.txt" 2> "$RAW/$n.stderr.txt"; echo $? > "$RAW/$n.rc.txt"; cat "$RAW/$n.stdout.txt"
}
case "${1:-}" in
preflight)  # read-only
  b 00-boot 'cat /proc/sys/kernel/random/boot_id; getenforce'
  b 01-runsh "ls -li $RT/run.sh; sha256sum $RT/run.sh; sed '$NORM' $RT/run.sh | sha256sum; grep -n -E '^export (LD_PRELOAD|WL_PARENT_ID)=' $RT/run.sh"
  b 02-dso-absent "ls -l $RT/$DSO 2>&1; ls -lZ $RT/libandroid_native_network_compat.so"
  b 03-entry "grep -n 'run.sh' /data/westlake-demo/toutiao/recovery-attempts/*/real-start-parent-bounded.sh 2>/dev/null | head; ls -l /system/etc/init/01_westlake_u13_toutiao.cfg; sha256sum /system/etc/init/01_westlake_u13_toutiao.cfg"
  b 04-procs "for p in ${PIDS:?set PIDS='<parent> <child>' from outer route-b-owner identification (parent comm is 'main', do not use pidof/pgrep -f)}; do echo == \$p; cut -d' ' -f1-4,22 /proc/\$p/stat; ls -li /proc/\$p/root/data/local/tmp/asx/run.sh 2>&1; grep -c libopensles_android_compat /proc/\$p/maps; done"
  echo "PASS criteria: normalized run.sh == $NORM_BEFORE (pre-change) and DSO absent; any other value -> STOP, report" ;;
stage)  # writes only under $STAGE
  h 10-push-dso hdc -t "$SERIAL" file send "$HERE/deploy-inputs/$DSO" "$STAGE.$DSO"
  b 11-stage "mkdir -p $STAGE && mv $STAGE.$DSO $STAGE/$DSO && sha256sum $STAGE/$DSO; cp -p $RT/run.sh $STAGE/run.sh.before && sha256sum $STAGE/run.sh.before && sed '$EDIT' $STAGE/run.sh.before > $STAGE/run.sh.after && sed '$NORM' $STAGE/run.sh.after | sha256sum; diff $STAGE/run.sh.before $STAGE/run.sh.after"
  echo "PASS criteria: $STAGE/$DSO sha == $DSO_SHA; normalized run.sh.after == $NORM_AFTER; diff touches only the LD_PRELOAD line" ;;
apply)  # the change; parent restart is done by outer through the original cfg/entry path, never kill -9 appspawn-x
  b 20-backup "cp -p $RT/run.sh $RT/run.sh.ttvideo-p1.bak && sha256sum $RT/run.sh $RT/run.sh.ttvideo-p1.bak"
  b 21-install "cp $STAGE/$DSO $RT/$DSO.tmp && chown 20011206:20011206 $RT/$DSO.tmp && chmod 0644 $RT/$DSO.tmp && mv $RT/$DSO.tmp $RT/$DSO && sha256sum $RT/$DSO && ls -lZ $RT/$DSO"
  b 22-edit "cp $STAGE/run.sh.after $RT/run.sh.tmp && chown 20011206:20011206 $RT/run.sh.tmp && chmod 0755 $RT/run.sh.tmp && mv $RT/run.sh.tmp $RT/run.sh && sed '$NORM' $RT/run.sh | sha256sum && ls -li $RT/run.sh"
  echo "PASS criteria: DSO sha == $DSO_SHA; normalized run.sh == $NORM_AFTER. Then outer restarts parent via the existing entry (start-parent -> real-start-parent-bounded.sh, which re-seds only WL_PARENT_ID)." ;;
verify)  # read-only, after restart; video tap/screenshots are done by outer's capture tooling
  b 30-runsh "sed '$NORM' $RT/run.sh | sha256sum; grep -n '^export LD_PRELOAD=' $RT/run.sh"
  b 31-maps "for p in ${PIDS:?set PIDS='<new parent> <new child>'}; do echo == \$p; cut -d' ' -f1-4,22 /proc/\$p/stat; grep -E 'libopensles_android_compat|libOpenSLES|libttmplayer|libmffmpeg|libvcbasekit' /proc/\$p/maps; done"
  echo "PASS (this change only): parent maps one $RT/$DSO (seen as /data/local/tmp/asx/$DSO) + one /system/lib64/libOpenSLES.so; feed screenshot equivalent to baseline; after one video tap: no SOURCE-NATIVE-LOAD-FAIL for libttmplayer, libttmplayer in child maps, no _setSupprotSampleRates UnsatisfiedLinkError. Record next first fatal verbatim; no playback claim." ;;
rollback)
  b 40-restore "cp -p $RT/run.sh.ttvideo-p1.bak $RT/run.sh.tmp && mv $RT/run.sh.tmp $RT/run.sh && sed '$NORM' $RT/run.sh | sha256sum && rm -f $RT/$DSO && ls -l $RT/$DSO 2>&1"
  echo "fallback if .bak missing: sed -i '$UNEDIT' $RT/run.sh (normalized must return to $NORM_BEFORE)"
  echo "PASS criteria: normalized run.sh == $NORM_BEFORE; DSO absent; after outer restart via original entry, parent maps has no $DSO and feed screenshot matches baseline" ;;
*) sed -n '2,6p' "$0"; exit 2 ;;
esac
echo "raw log dir: $RAW (EXECUTE=${EXECUTE:-0})"
