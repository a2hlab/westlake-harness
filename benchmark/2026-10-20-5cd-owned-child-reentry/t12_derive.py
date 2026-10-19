"""Offline deterministic derivation. No device transport."""
import hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
SERIAL='5cd1e3dd00000000000000000923012c'
BOOT='0525bb05-f714-42ad-90f0-ecdb10356c4f'
PARENT=19163;BIRTH=7265322;UID=20011300;DESKTOP_UID=20010017
RUNTIME='/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d'
STAGE='/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d'
SOCKET='/dev/unix/socket/A2HSourcec91d26bfb4db4fd5a002'
OLD='/data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/boots/'+BOOT
CFG='/system/etc/init/01_westlake_u13_toutiao.cfg'
CFG_SHA='19d0201b59a6edac821feffa5f51ca8e9a08d6ba87d5bc9fd15b4e4d00775152'
RUN_SHA='5a3aef638000e49f2a966b2179d57fe7628c29a4897921209fec539bd5dc1b79'
EXE_SHA='a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c'
JIT_SHA='b42a28e7a29a53c162a43ac25eaf52c24906f1afdd179c9414882772ccac34c8'
HOST_SHA='019acf9ec9f1b701b793e883c95ea5808cf74338b02088b024cf3634c6b56279'
REQUEST_SHA='011a16259c7735dcb088fab44f569bc222675855eb722bcf945c48e06c0214ca'
DECODER_SHA='0bf966d76e038379af1fa2542746572a2c76a9bf88e17a97869682debfc36eaf'
def sha(b):return hashlib.sha256(b).hexdigest()
def need(b,msg):
 if not b:raise ValueError(msg)
def sources():
 pins=json.loads((HERE/'source-pins.json').read_text());out={}
 for p in pins:
  b=(HERE/p['path']).read_bytes();need(sha(b)==p['sha256'],'source drift '+p['path']);out[Path(p['path']).name]=b.decode()
 return out

def derive(root,desktop_uid,deadline):
 need(re.fullmatch('/data/westlake-demo/toutiao/recovery-attempts/icon-manual-5cd-t12-[a-z0-9-]+',root),'new root')
 need(type(desktop_uid)==int and desktop_uid==DESKTOP_UID and type(deadline)==int and deadline>0,'desktop/deadline')
 src=sources();w=src['watchdog-reentry.sh']
 a=w.index(' # Original first-launch chain:');b=w.index('\n rc_reentry_loop\n}',a)
 w=w[:a]+' # T12: an existing parent does not authorize an immediate spawn.\n state AWAITING_REENTRY existing_parent_wait_actual_desktop_icon'+w[b:]
 old='rc_stop_present() { [ -e "$F/stop" ] || [ -L "$F/stop" ]; }'
 need(w.count(old)==1,'stop seam drift')
 new='''t12_deadline_stop() {
 if [ -e "$F/stop" ] || [ -L "$F/stop" ]; then return 0; fi
 t12_now=$(uptime_s) || { write_exact "$F/stop" uptime_unreadable; return 0; }
 if [ "$t12_now" -ge "$TT_DEADLINE_UPTIME" ]; then write_exact "$F/stop" deadline; return 0; fi
 return 1
}
rc_stop_present() {
 t12_deadline_stop && return 0
 if [ "$seq" -ge 1 ]; then write_exact "$F/stop" single_launch_complete; return 0; fi
 return 1
}'''
 w=w.replace(old,new)
 old=' do_spawn_started=1\n if ! timeout 15 sh'
 need(w.count(old)==1,'spawn fence seam drift')
 w=w.replace(old,' t12_deadline_stop && { do_reason=t12_stop_before_spawn; return 2; }\n do_spawn_started=1\n if ! timeout 15 sh')
 need(w.count(' while [ ! -e "$F/stop" ]; do')==1,'monitor drift')
 w=w.replace(' while [ ! -e "$F/stop" ]; do',' while ! t12_deadline_stop; do')
 old=' rc_owned_result=$(rc_parse_owned_window "$F/wms-owned.txt" "$child $ow_extra") || rc_owned_result=unknown'
 need(w.count(old)==1,'owned seam drift')
 w=w.replace(old,' ow_ids=$ow_extra\n [ "$child" = none ] || ow_ids="$child $ow_ids"\n rc_owned_result=$(rc_parse_owned_window "$F/wms-owned.txt" "$ow_ids") || rc_owned_result=unknown')
 # Existing-parent admission is mandatory; disable the unused new-parent branch.
 old=' parent=${TT_PARENT_PID:-none}; parent_birth=${TT_PARENT_BIRTH:-none}'
 need(w.count(old)==1,'parent seam drift')
 w=w.replace(old,old+f'\n [ "$parent:$parent_birth" = "{PARENT}:{BIRTH}" ] || {{ state OWNER_REFUSED t12_exact_existing_parent; return 2; }}')
 cfg=f'''#!/system/bin/sh
# New T12 authority; no old attempt sourced or modified.
fail(){{ printf '[T12] REFUSE %s\\n' "$*" >&2; exit 2; }}
[ "$HERE" = '{root}' ] || fail wrong_root
[ "$(cat /proc/sys/kernel/random/boot_id)" = '{BOOT}' ] || fail boot
AUTH_RUNTIME='{RUNTIME}'
AUTH_STAGE='{STAGE}'
AUTH_SOCKET='{SOCKET}'
AUTH_UID={UID}
AUTH_BOOT='{BOOT}'
AUTH_STATE_ROOT='{root}'
AUTH_PARENT_MODE=existing
AUTH_JIT_SHA='{JIT_SHA}'
AUTH_HOST_SPAWN_SHA='{HOST_SHA}'
AUTH_REQUEST_SHA='{REQUEST_SHA}'
TT_PARENT_PID={PARENT}
TT_PARENT_BIRTH={BIRTH}
export PATH=/system/bin:/bin:/system/xbin
t12_launch_guard(){{
 [ ! -e \"$AUTH_STATE_ROOT/stop\" ] && [ ! -L \"$AUTH_STATE_ROOT/stop\" ] || fail t12_stop
 [ ! -e '{OLD}/stop' ] && [ ! -L '{OLD}/stop' ] || fail old_attempt_stop
 [ ! -e '{OLD.rsplit('/boots/',1)[0]}/stop' ] && [ ! -L '{OLD.rsplit('/boots/',1)[0]}/stop' ] || fail old_root_stop
 read t12_up t12_rest < /proc/uptime || fail uptime_unreadable
 [ \"${{t12_up%%.*}}\" -lt {deadline} ] || fail t12_deadline
}}
'''
 entry=f'''#!/system/bin/sh
set -eu
HERE=$(dirname "$0")
. "$HERE/config-common.sh"
[ ! -e "$HERE/stop" ] && [ ! -L "$HERE/stop" ] && [ ! -e "$HERE/lock" ]
while read hash name; do [ "$(sha256sum "$HERE/$name" | cut -d' ' -f1)" = "$hash" ]; done < "$HERE/members.tsv"
. "$HERE/launch-common.sh"
parent_owned {PARENT} {BIRTH}
[ -z "$(rb_owned_pids)" ]
export TT_PROC=/proc TT_RECOVERY_EXECUTE=1 TT_EXPECT_BOOT='{BOOT}' TT_OWNER_UID={UID}
export TT_STATE_ROOT='{root}' TT_RUNTIME='{RUNTIME}' TT_STAGE='{STAGE}' TT_SOCKET='{SOCKET}'
export TT_PARENT_PID={PARENT} TT_PARENT_BIRTH={BIRTH} TT_DESKTOP_UID={desktop_uid}
export TT_MAX_ATTEMPTS=1 TT_MAX_POLLS=0 TT_DEADLINE_UPTIME={deadline}
unset TT_CHILD_PID TT_CHILD_BIRTH TT_OPERATOR_ROOT
exec /system/bin/sh "$HERE/watchdog.sh"
'''
 payload={n:src[n] for n in ['route-b-owner.sh','launch-common.sh','real-spawn.sh','readiness-probe.sh','reentry-common.sh','reentry-seams.sh','exit-verdict.sh']}
 spawn=src['spawn-prepared.sh']
 need(spawn.count('timeout 8 /bin/nsenter')==1 and spawn.count('exec /system/bin/sh \"$HERE/real-spawn.sh\"')==1,'spawn wrapper seam')
 spawn=spawn.replace('timeout 8 /bin/nsenter','t12_launch_guard\ntimeout 8 /bin/nsenter').replace('exec /system/bin/sh \"$HERE/real-spawn.sh\"','t12_launch_guard\nexec /system/bin/sh \"$HERE/real-spawn.sh\"')
 reentry=src['reentry-common.sh'];old='[ \"$rc_arm\" = DESKTOP_SEEN ] || rc_arm=DESKTOP_SEEN'
 need(reentry.count(old)==1,'desktop state seam')
 payload['reentry-common.sh']=reentry.replace(old,'if [ \"$rc_arm\" != DESKTOP_SEEN ]; then rc_arm=DESKTOP_SEEN; rc_event t12_desktop_seen; fi')
 payload.update({'spawn.sh':spawn,'config-common.sh':cfg,'watchdog.sh':w,'entry.sh':entry})
 members={n:sha(s.encode()) for n,s in payload.items()};members['screen-gate']=DECODER_SHA
 payload['members.tsv']=''.join(f'{h} {n}\n' for n,h in sorted(members.items()))
 return payload
