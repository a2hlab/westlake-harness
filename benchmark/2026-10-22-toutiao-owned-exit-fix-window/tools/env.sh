# T52 window helper (zsh). Source from the worktree root. Device writes happen only via put2/rboot after LOCK.
setopt pipefail
WT=${WT:-$PWD}
R=$HOME/.local/share/westlake/t52-owned-exit-fix-window-20261022
H=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
S=5cd1e3dd00000000000000000923012c
LANE=herdr-t52
M=$(cd "$(git -C "$WT" rev-parse --path-format=absolute --git-common-dir)/.." && pwd)   # main tree from git common dir
BOARD=$M/.octos/boards/app-lighting.md
ROOT=/data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012
RA=/data/westlake-demo/toutiao/recovery-attempts
TAG=diag-maint-t52-20261022-1900
STAGE=/data/local/tmp/$TAG
BACKUP=$RA/$TAG/backup
PKG=$HOME/.local/share/westlake/t51-outer-20261022/source/benchmark/2026-10-22-toutiao-owned-exit-fix-package/package-01
PLANB=$WT/benchmark/2026-10-22-toutiao-owned-exit-fix-window/bytes
RC=/data/westlake-demo/u13/boat-v2-20261013-r4/recover-v3-boat.sh
TOOLS=$WT/benchmark/2026-10-22-toutiao-owned-exit-fix-window/tools
# rec returns the recorded command rc (nonzero if the command failed or the record was refused)
rec() { local d=$1 n=$2; shift 2; python3 $TOOLS/rec.py $R/raw/$d $n "$@" || return 90; [ "$(cat $R/raw/$d/$n.rc 2>/dev/null)" = 0 ]; }
sh_() { local d=$1 n=$2; shift 2; rec $d $n -- $H -t $S shell "$*"; }
CTRL="$ROOT/startup.env $ROOT/members.tsv $ROOT/startup.expected.sha256 $ROOT/entry.sh $ROOT/boot-entry.sh $ROOT/watchdog.sh $ROOT/route-b-owner.sh $ROOT/config-common.sh /system/etc/init/01_westlake_u13_toutiao.cfg"
MEMN="launch-common.sh real-start-parent.sh real-spawn.sh start-parent.sh spawn.sh screen-gate decoder-probe.jpeg real-start-parent-bounded.sh readiness-probe.sh"
SIX="watchdog.sh route-b-owner.sh entry.sh members.tsv startup.env startup.expected.sha256"
FP='for p in /system/bin/appspawn-x /system/android/framework/oh-adapter-runtime.jar /system/android/lib64/*.so /system/lib64/westlake/route-a/*/*.so /system/lib64/libbms.z.so /system/lib64/libapk_installer.so /system/lib64/libinstalls.z.so /system/lib64/platformsdk/libbms.z.so /system/lib64/platformsdk/libapk_installer.so /system/lib64/platformsdk/libinstalls.z.so; do for f in $p; do if [ -e "$f" ]; then sha256sum "$f"; else echo "MISSING $f"; fi; done; done'
BI='for p in /system/android/framework/arm64/* /system/android/framework/core-oj.jar /system/android/framework/core-libart.jar /system/android/framework/core-icu4j.jar /system/android/framework/okhttp.jar /system/android/framework/bouncycastle.jar /system/android/framework/apache-xml.jar /system/android/framework/adapter-mainline-stubs.jar /system/android/framework/framework.jar /system/android/framework/oh-adapter-framework.jar; do for f in $p; do if [ -e "$f" ]; then sha256sum "$f"; else echo "MISSING $f"; fi; done; done'
STATF="stat -c '%n size=%s mode=%a uid=%u gid=%g dev=%d ino=%i mtime=%Y type=%F'"
snapshot() { local d=$1
  REC_SHOW=0 sh_ $d bootid 'cat /proc/sys/kernel/random/boot_id; cat /proc/uptime; date +%s'
  REC_SHOW=0 sh_ $d ctrl "for f in $CTRL; do $STATF \$f; sha256sum \$f; done"
  REC_SHOW=0 sh_ $d members "for n in $MEMN; do f=$ROOT/\$n; $STATF \$f; sha256sum \$f; done"
  REC_SHOW=0 sh_ $d lsZ "ls -Zd $ROOT $ROOT/boots $RA /data/local/tmp; cd $ROOT; ls -Z $SIX"
  REC_SHOW=0 sh_ $d ready_chain "sha256sum /system/etc/init/00_westlake_u13_recover-v3.cfg $RC; $STATF /system/etc/init/00_westlake_u13_recover-v3.cfg $RC; param get sys.westlake.demo.u13.ready"
  REC_SHOW=0 sh_ $d fp "$FP"; REC_SHOW=0 sh_ $d bi "$BI"
  REC_SHOW=0 sh_ $d stops "for s in $ROOT/stop /data/local/tmp/operator45/selfheal48/stop $ROOT/boots/*/stop; do if [ -e \"\$s\" ] || [ -L \"\$s\" ]; then echo PRESENT \$s; else echo ABSENT \$s; fi; done"
  REC_SHOW=0 sh_ $d boots "ls $ROOT/boots"
  REC_SHOW=0 sh_ $d host "sha256sum /data/app/el1/bundle/public/org.westlake.imehost/entry.hap; echo pid=\$(pidof org.westlake.imehost || echo NONE); $STATF /data/app/el2/100/base/org.westlake.imehost /data/app/el2/100/base/org.westlake.imehost/haps/entry/files"
  REC_SHOW=0 sh_ $d bm 'bm dump -n org.westlake.imehost'
  REC_SHOW=0 sh_ $d power "hidumper -s PowerManagerService -a '-a' | grep -E 'ScreenOffTime|Current State'"
  REC_SHOW=0 sh_ $d ps 'ps -A -o PID,PPID,UID,ARGS'
  REC_SHOW=0 sh_ $d parents "$STATF /data/local/tmp $RA $ROOT $ROOT/boots; for p in $STAGE $RA/$TAG; do if [ -e \$p ] || [ -L \$p ]; then echo EXISTS \$p; else echo ABSENT \$p; fi; done; cd $ROOT; for n in $SIX; do if [ -e .\$n.new ] || [ -L .\$n.new ]; then echo EXISTS .\$n.new; else echo ABSENT .\$n.new; fi; done"
}
left() { echo $(( $(cat $R/raw/LOCK_EPOCH) + 1800 - $(date +%s) )); }
PARENTS4="/data/local/tmp $RA $ROOT $ROOT/boots"
PARENTS="$PARENTS4 $STAGE $RA/$TAG $BACKUP"
idcmd() { echo "cat /proc/sys/kernel/random/boot_id; stat -c '%n mode=%a uid=%u gid=%g dev=%d ino=%i' $1; ls -Zd $1"; }
# bind4 (preflight, read-only): bind the 4 pre-existing parents; guard4 is used before mkdir only
bind4() { sh_ 00-preflight bind4 "$(idcmd "$PARENTS4")" || return 16; sed -n 2,5p $R/raw/00-preflight/bind4.stdout > $R/raw/BOUND_PARENTS4; sed -n 6,9p $R/raw/00-preflight/bind4.stdout > $R/raw/BOUND_LABELS4; }
guard4() { local d=$1 g=$2
  rec $d ${g}_held -- bash $M/scripts/lab/board_note.sh held $S || { echo GUARD_LOCK_RC; return 12; }; grep -q "^$LANE " $R/raw/$d/${g}_held.stdout || { echo GUARD_LOCK; return 12; }
  REC_SHOW=0 sh_ $d ${g}_id "$(idcmd "$PARENTS4")" || { echo GUARD_ID_RC; return 16; }
  [ "$(head -1 $R/raw/$d/${g}_id.stdout)" = "$(cat $R/raw/PHASE_BOOT)" ] || { echo GUARD_BOOT; return 13; }
  sed -n 2,5p $R/raw/$d/${g}_id.stdout | cmp -s - $R/raw/BOUND_PARENTS4 || { echo GUARD_PARENT_ID; return 14; }
  sed -n 6,9p $R/raw/$d/${g}_id.stdout | cmp -s - $R/raw/BOUND_LABELS4 || { echo GUARD_LABEL; return 15; }
  echo GUARD4_OK; return 0; }
# mkdirs: guard4 -> fresh mkdir (refuse existing) -> bind the 7 parents for all later guards
mkdirs() { local d=$1 g; guard4 $d g4_mkdir; g=$?; [ $g = 0 ] || return $g
  REC_SHOW=3 sh_ $d mkdirs "set -e; for p in $STAGE $RA/$TAG; do if [ -e \$p ] || [ -L \$p ]; then echo REFUSE_EXISTS \$p; exit 3; fi; done; mkdir $STAGE; chmod 700 $STAGE; mkdir $RA/$TAG; mkdir $BACKUP; chmod 700 $RA/$TAG $BACKUP; echo MKDIR_OK" || { echo STOP_MKDIR_RC; return 18; }
  grep -q MKDIR_OK $R/raw/$d/mkdirs.stdout || { echo STOP_MKDIR_BODY; return 18; }
  sh_ $d bind7 "$(idcmd "$PARENTS")" || return 16; sed -n 2,8p $R/raw/$d/bind7.stdout > $R/raw/BOUND_PARENTS; sed -n 9,15p $R/raw/$d/bind7.stdout > $R/raw/BOUND_LABELS; echo MKDIRS_BOUND; return 0; }
# BOUND_PARENTS / BOUND_LABELS are written once right after stage/backup creation (window step M1-mkdir).
guard() { local d=$1 g=$2 need=$3
  [ $(left) -ge $need ] || { echo "GUARD_BUDGET left=$(left) need=$need"; return 11; }
  REC_SHOW=0 rec $d ${g}_held -- bash $M/scripts/lab/board_note.sh held $S || { echo GUARD_LOCK_RC; return 12; }; grep -q "^$LANE " $R/raw/$d/${g}_held.stdout || { echo GUARD_LOCK; return 12; }
  REC_SHOW=0 sh_ $d ${g}_id "$(idcmd "$PARENTS")" || { echo GUARD_ID_RC; return 16; }
  [ "$(head -1 $R/raw/$d/${g}_id.stdout)" = "$(cat $R/raw/PHASE_BOOT)" ] || { echo GUARD_BOOT; return 13; }
  sed -n "2,8p" $R/raw/$d/${g}_id.stdout | cmp -s - $R/raw/BOUND_PARENTS || { echo GUARD_PARENT_ID; return 14; }
  sed -n "9,15p" $R/raw/$d/${g}_id.stdout | cmp -s - $R/raw/BOUND_LABELS || { echo GUARD_LABEL; return 15; }
  echo "GUARD_OK left=$(left)"; return 0; }
put() { local d=$1 n=$2 lf=$3 mode=$4 sha=$5 sf=$STAGE/$1-$2
  [ "$(shasum -a 256 $lf | cut -d' ' -f1)" = $sha ] || { echo "LOCAL_SHA_MISMATCH $lf"; return 9; }
  REC_SHOW=1 sh_ $d ${n}_prechk "if [ -e $sf ] || [ -L $sf ] || [ -e $ROOT/.$n.new ] || [ -L $ROOT/.$n.new ]; then echo REFUSE_EXISTS; else echo FRESH; fi" || { echo "STOP prechk_rc $n"; return 3; }
  grep -q '^FRESH$' $R/raw/$d/${n}_prechk.stdout || { echo "STOP prechk $n"; return 3; }
  REC_SHOW=1 rec $d ${n}_send -- $H -t $S file send $lf $sf || { echo "STOP send_rc $n"; return 4; }
  grep -q 'FileTransfer finish' $R/raw/$d/${n}_send.stdout || { echo "STOP send $n"; return 4; }
  local g; guard $d g2_$n 60; g=$?; [ $g = 0 ] || { echo "STOP midguard $n"; return $g; }   # second guard between send and ROOT replace
  REC_SHOW=12 sh_ $d ${n}_replace "set -e; [ \"\$(sha256sum $sf | cut -d' ' -f1)\" = $sha ] || { echo STAGE_SHA_BAD; exit 5; }; T=$ROOT/.$n.new; cp $sf \$T; chmod $mode \$T; chown 0:0 \$T; chcon u:object_r:data_file:s0 \$T; [ \"\$(sha256sum \$T | cut -d' ' -f1)\" = $sha ] || { echo NEW_SHA_BAD; exit 6; }; mv \$T $ROOT/$n; echo RENAMED; sha256sum $ROOT/$n; $STATF $ROOT/$n; ls -Z $ROOT/$n" || { echo "STOP replace_rc $n (read back before deciding)"; return 7; }
  grep -q RENAMED $R/raw/$d/${n}_replace.stdout && grep -q "^$sha " $R/raw/$d/${n}_replace.stdout && grep -q "mode=$mode uid=0 gid=0" $R/raw/$d/${n}_replace.stdout && grep -q '^u:object_r:data_file:s0' $R/raw/$d/${n}_replace.stdout || { echo "STOP readback $n"; return 7; }
  echo "PUT_OK $n $sha"; return 0; }
# put2: guard then put; caller MUST check rc: put2 ...; rc=$?; [ $rc = 0 ] || stop
put2() { local d=$1 n=$2 g; guard $d g_$n 120; g=$?; [ $g = 0 ] || return $g; put "$@"; }
# rboot: caller runs guard first and checks rc; timer starts before target boot; timeout is never resent
rboot() { local d=$1; local old=$(cat $R/raw/PHASE_BOOT); local t0=$(date +%s) i=0; echo $t0 > $R/raw/$d/BOOT_T0
  local trc=0; REC_TIMEOUT=40 REC_SHOW=2 rec $d target_boot -- $H -t $S target boot || trc=$?
  [ $trc = 0 ] || echo "TARGET_BOOT_RC_NONZERO rc=$trc (no resend; polling read-only, result will be flagged)"
  while [ $(( $(date +%s) - t0 )) -lt 180 ]; do i=$((i+1)); sleep 5
    REC_TIMEOUT=10 REC_SHOW=0 rec $d poll${i}_targets -- $H list targets >/dev/null
    grep -q $S $R/raw/$d/poll${i}_targets.stdout || continue
    REC_TIMEOUT=10 REC_SHOW=0 rec $d poll${i}_boot -- $H -t $S shell 'cat /proc/sys/kernel/random/boot_id; cat /proc/uptime' >/dev/null
    local nb=$(head -1 $R/raw/$d/poll${i}_boot.stdout)
    if echo "$nb" | grep -qE '^[0-9a-f-]{36}$' && [ "$nb" != "$old" ]; then echo "NEWBOOT $nb after $(( $(date +%s) - t0 ))s"; echo $nb > $R/raw/$d/NEW_BOOT; [ $trc = 0 ] && return 0; return 17; fi
  done; echo "BOOT_WAIT_TIMEOUT (no resend; read-only judgement next)"; return 8; }
keep() { REC_SHOW=0 sh_ $1 $2_ovr power-shell timeout -o 600000; REC_SHOW=0 sh_ $1 $2_ver "hidumper -s PowerManagerService -a '-a' | grep -E 'ScreenOffTime|Current State'"; grep -q 'OverrideTimeout=600000ms' $R/raw/$1/$2_ver.stdout || echo "WARN override not verified $2"; }
lay() { local d=$1 t=$2 f=$STAGE/ui-$1-$2.json; REC_SHOW=0 sh_ $d ${t}_lay "rm -f $f; uitest dumpLayout -p $f"; keep $d ${t}_lay
  REC_SHOW=0 rec $d ${t}_rl -- $H -t $S file recv $f $R/raw/$d/$t.json; python3 $TOOLS/ui.py $R/raw/$d/$t.json $R/raw/$d/$t.ui.json >/dev/null
  python3 -c "import json;r=json.load(open('$R/raw/$d/$t.ui.json'));print('$t',r['workspace'],r['icon_count'],'lock',r['lock_ids'],'desk',r['valid_desktop'],'target',bool(r['target']),r.get('target_actionable'),r.get('target_center'))"; }
shot() { local d=$1 t=$2 f=$STAGE/ui-$1-$2.jpeg; REC_SHOW=0 sh_ $d ${t}_shot "rm -f $f; snapshot_display -f $f"; REC_SHOW=0 rec $d ${t}_rs -- $H -t $S file recv $f $R/raw/$d/$t.jpeg; shasum -a 256 $R/raw/$d/$t.jpeg | cut -c1-16; }
desk() { local d=$1; REC_SHOW=0 sh_ $d wake power-shell wakeup; keep $d wake; REC_SHOW=0 sh_ $d home uitest uiInput keyEvent Home; keep $d home; sleep 1; lay $d d0; }
