"""T13: minimal T12 derivation; no transport. Exact existing-child adoption."""
import re
import t12_derive as base
from t12_derive import *
CHILD=31210
CHILD_BIRTH=7485570

def child_function():
 w=sources()['watchdog-reentry.sh']
 return w[w.index('child_owned() {'):w.index('\ncapture_init() {')]

def ownership_probe():
 """Execute the frozen full ownership functions, without a device-side file."""
 s=sources();common=s['launch-common.sh']
 common=common[common.index('private_namespace() {'):common.index('# Existing parent reuse')]
 return (f'RB_PROC=/proc; PROC=/proc; RB_RUNTIME={RUNTIME}; RUNTIME={RUNTIME}; RB_OWNER_UID={UID}; parent={PARENT};\n'
         +s['route-b-owner.sh']+'\n'+common+child_function()+f'\nparent_owned {PARENT} {BIRTH}; child_owned {CHILD} {CHILD_BIRTH}; test "$(rb_owned_pids)" = {CHILD};\n')

def derive(root,desktop_uid,deadline):
 need(re.fullmatch('/data/westlake-demo/toutiao/recovery-attempts/icon-manual-5cd-t13-[a-z0-9-]+',root),'new T13 root')
 alias=root.replace('icon-manual-5cd-t13-','icon-manual-5cd-t12-',1)
 payload={n:s.replace(alias,root) for n,s in base.derive(alias,desktop_uid,deadline).items()}
 w=payload['watchdog.sh'];src=sources()['watchdog-reentry.sh']
 a=src.index(' # Original first-launch chain:');b=src.index('\n rc_reentry_loop\n}',a)
 tail=src[a:b]
 tail=tail.replace(' # Original first-launch chain: exactly one spawn, unchanged behaviour.',' # T13: frozen R2 adoption branch; no first-launch fallback.')
 start=tail.index('\n else\n  do_one_launch;');end=tail.index('\n fi\n # Supervise',start)
 tail=tail[:start]+'\n else\n  state OWNER_REFUSED t13_missing_exact_child_no_fallback; return 2'+tail[end:]
 tail=tail.replace(' verify_exact "$F/lock/owner"', ' t12_deadline_stop && { state STOPPED deadline_before_adoption; return 0; }\n verify_exact "$F/lock/owner"')
 tail=tail.replace('  child=$TT_CHILD_PID; child_birth=${TT_CHILD_BIRTH:-none}',f'  child=$TT_CHILD_PID; child_birth=${{TT_CHILD_BIRTH:-none}}\n  [ "$child:$child_birth" = "{CHILD}:{CHILD_BIRTH}" ] || {{ state OWNER_REFUSED t13_fixed_child; return 2; }}')
 tail=tail.replace('  seq=$((seq+1)); write_exact "$F/sequence" "$seq"; instance', '''  [ "$seq" = 0 ] || { state OWNER_REFUSED t13_fresh_sequence_required; return 2; }
  seq=$((seq+1)); write_exact "$F/sequence" "$seq"; instance
  write_exact "$F/adopted" "$$ $self_birth $BOOT $parent $parent_birth $child $child_birth $seq"
  event t13_adopted''')
 old=' # T12: an existing parent does not authorize an immediate spawn.\n state AWAITING_REENTRY existing_parent_wait_actual_desktop_icon'
 need(w.count(old)==1,'adoption seam');w=w.replace(old,tail)
 w=w.replace('if [ "$seq" -ge 1 ];','if [ "$seq" -ge 2 ];')
 # No second external attempt even when an early spawn failure was classified fail.
 old=' do_spawn_started=1\n if ! timeout 15 sh'
 new=''' [ ! -e "$F/spawn.intent" ] && [ ! -L "$F/spawn.intent" ] || { do_reason=t13_spawn_intent_exists; do_spawn_started=1; return 2; }
 (set -C; printf '%s\\n' "$BOOT $parent $parent_birth $seq" > "$F/spawn.intent") || { do_reason=t13_spawn_intent_unknown; do_spawn_started=1; return 2; }
 verify_exact "$F/spawn.intent" "$BOOT $parent $parent_birth $seq"
 t12_deadline_stop && { do_reason=t13_stop_after_intent; do_spawn_started=1; return 2; }
 do_spawn_started=1
 if ! timeout 15 sh'''
 need(w.count(old)==1,'spawn intent seam');w=w.replace(old,new)
 payload['watchdog.sh']=w
 entry=payload['entry.sh'].replace('[ -z "$(rb_owned_pids)" ]',f'. "$HERE/child-guard.sh"\nparent={PARENT}\nchild_owned {CHILD} {CHILD_BIRTH}\n[ "$(rb_owned_pids)" = {CHILD} ]')
 entry=entry.replace('unset TT_CHILD_PID TT_CHILD_BIRTH TT_OPERATOR_ROOT',f'export TT_CHILD_PID={CHILD} TT_CHILD_BIRTH={CHILD_BIRTH}\nunset TT_OPERATOR_ROOT')
 payload['entry.sh']=entry
 payload['reentry-common.sh']=payload['reentry-common.sh'].replace('t12_desktop_seen','t13_desktop_seen')
 payload['child-guard.sh']=child_function()+'\n'
 # Readonly adopted-instance proof used immediately before TERM and icon intent.
 payload['adoption-guard.sh']=f'''#!/system/bin/sh
# config-common + launch-common must have been sourced first.
t13_adoption_guard() {{
 t12_launch_guard
 parent_owned {PARENT} {BIRTH} || return 1
 [ ! -L "$HERE/adopted" ] && [ -f "$HERE/adopted" ] || return 1
 read t13_gp t13_gb t13_boot t13_pp t13_pb t13_cp t13_cb t13_sq t13_extra < "$HERE/adopted" || return 1
 [ "$t13_boot:$t13_pp:$t13_pb:$t13_cp:$t13_cb:$t13_sq:$t13_extra" = '{BOOT}:{PARENT}:{BIRTH}:{CHILD}:{CHILD_BIRTH}:1:' ] || return 1
 case "$t13_gp:$t13_gb" in *[!0-9:]*|:*) return 1;; esac
 [ "$t13_gp" -gt 1 ] && [ -n "$t13_gb" ] || return 1
 [ "$(rb_birth "$t13_gp")" = "$t13_gb" ] || return 1
 [ "$(rb_uid "$t13_gp")" = 0:0:0:0 ] || return 1
 [ "$(readlink "$PROC/$t13_gp/exe")" = /system/bin/sh ] || return 1
 [ "$(timeout 2 strings "$PROC/$t13_gp/cmdline")" = "$(printf '/system/bin/sh\\n%s' "$HERE/watchdog.sh")" ] || return 1
 [ ! -L "$HERE/lock" ] && [ ! -L "$HERE/lock/owner" ] || return 1
 [ "$(cat "$HERE/lock/owner")" = "$t13_gp $t13_gb $t13_boot" ] || return 1
 [ ! -L "$HERE/sequence" ] && [ "$(cat "$HERE/sequence")" = 1 ] || return 1
 [ ! -L "$HERE/instance.txt" ] || return 1
 [ "$(cat "$HERE/instance.txt")" = "$(printf 'boot_id=%s\\nchild=%s\\nparent=%s\\nbirth=%s\\nparent_birth=%s\\nseq=1\\nmode=preserve' '{BOOT}' '{CHILD}' '{PARENT}' '{CHILD_BIRTH}' '{BIRTH}')" ] || return 1
 [ "$(rb_birth "$t13_gp")" = "$t13_gb" ]
}}
'''
 payload['term-once.sh']=f'''#!/system/bin/sh
set -eu
HERE=$(dirname "$0")
. "$HERE/config-common.sh"
. "$HERE/launch-common.sh"
. "$HERE/child-guard.sh"
. "$HERE/adoption-guard.sh"
parent={PARENT}
t13_term_once() {{
 t13_adoption_guard || return 2
 child_owned {CHILD} {CHILD_BIRTH} || return 2
 [ ! -e "$HERE/term.intent" ] && [ ! -L "$HERE/term.intent" ] || return 2
 (set -C; printf '%s\\n' '{BOOT} {PARENT} {BIRTH} {CHILD} {CHILD_BIRTH} TERM' > "$HERE/term.intent") || return 2
 [ "$(cat "$HERE/term.intent")" = '{BOOT} {PARENT} {BIRTH} {CHILD} {CHILD_BIRTH} TERM' ] || return 2
 t13_adoption_guard || return 2
 child_owned {CHILD} {CHILD_BIRTH} || return 2
 rb_signal {CHILD} {CHILD_BIRTH} TERM
}}
t13_term_once
'''
 payload.pop('members.tsv')
 members={n:sha(s.encode()) for n,s in payload.items()};members['screen-gate']=DECODER_SHA
 payload['members.tsv']=''.join(f'{h} {n}\n' for n,h in sorted(members.items()))
 return payload
