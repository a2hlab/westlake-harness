#!/usr/bin/env python3
"""T34 rollback, normal-icon evidence and exact restoration gate before unlock."""
from common import *
ORIGINAL={'run.sh':'6afd6fba3d0b34165a49f176a4dacecfbdc344bde54daa455ea9718b7206484f','liboh_adapter_bridge.so':'d4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b','lib/arm64-v8a/libmffmpeg.so':'fecf91e1fcda600661f501ce76a97456ad7e330b584013f2b742afb680b337c9','lib/arm64-v8a/libttmplayer.so':'b427614d57e4a7279f362b3f341de3cdd4b9f9a8859257016bcda24e5f6d3a02','webview-t-lib/libwebview_bionic_shim.so':'85c789f48b2bc0c31658c9dc591cd27784cc0ddfe559005e8d36d1d7d220476a'}
CFG='/system/etc/init/01_westlake_u13_toutiao.cfg'
HAP='/data/app/el1/bundle/public/org.westlake.imehost/entry.hap'

def verify_text(text,parent,boot,controls,cfg,hap,debug_rc):
 hashes={p:h for h,p in re.findall(r'^([0-9a-f]{64})\s+(\S+)$',text,re.M)}
 for rel,h in ORIGINAL.items():
  assert hashes[RT+'/'+rel]==h and hashes[f'/proc/{parent["pid"]}/root/data/local/tmp/asx/'+rel]==h
 assert hashes[CFG]==cfg and hashes[HAP]==hap
 assert len(controls)==18 and all(hashes[p]==h for p,h in controls.items())
 assert text.count('PHYSICAL_COMPAT_ABSENT\n')==1 and text.count('PRIVATE_COMPAT_ABSENT\n')==1
 assert re.search(r'\bTimeout=30000ms\s+OverrideTimeout=86400000ms\b',text)
 assert re.search(r'^DEBUG_PROCESS_RC='+str(debug_rc)+r'$',text,re.M)
 assert 'Get parameter "debug.ttplayer.log.enable" fail! errNum is:106!' in text
 assert 'RESTORE_IDENTITY_MATCH\n' in text
 return {'status':'EXACT_RESTORE_VERIFIED','boot':boot,'parent':parent,'physical_private_five_sha':True,'compat_physical_private_absent':True,'guardian_sha_matches':18,'cfg_hap_match':True,'power':[30000,86400000],'debug_absent_errNum':106}

def restore(d):
 pre=d.boot();ad=json.loads((d.w/'rollback-admission.json').read_text());assert pre==ad['boot'];d.held()
 _,out,_=d.raw('rollback',d.op,300);assert b'PHYSICAL_FILES_RESTORED_REQUIRES_FRESH_BOOT' in out
 new=d.reboot(pre)
 d.ui(new,'restored-icon','launch',30)
 # This action occurs after every uitest action, never in parallel with icon UI.
 d.ui(new,'original-power','power',0)
 parent,host,child,wid,init=d.discover(new,include_child=False)
 freshpath=d.w/'data/fresh.json';assert digest(freshpath)==d.origin['fresh_data_sha256'];fresh=json.loads(freshpath.read_text())
 controls=fresh['controls'];assert len(controls)==18
 assert fresh['power']=={'timeout':30000,'override':86400000} or fresh['power']=={'timeout_ms':30000,'override_ms':86400000},'Unexpected original power'
 assert digest(d.w/'data/run61b.before.reference.sh')==ORIGINAL['run.sh']
 guard=f'test "$(cat /proc/sys/kernel/random/boot_id)" = {q(new)}\n'+d.cv.process_guard(parent)
 guard+=f'test "$(readlink /proc/1/ns/mnt)" = {q(init)}\n'
 script=guard
 for role,root in [('PHYSICAL',RT),('PRIVATE',f'/proc/{parent["pid"]}/root/data/local/tmp/asx')]:
  for rel in ORIGINAL:script+='sha256sum '+q(root+'/'+rel)+'\n'
  for rel in ['libopensles_android_compat.so','lib/arm64-v8a/libopensles_android_compat.so']:
   script+=f'test ! -e {q(root+"/"+rel)} || exit 81\ntest ! -L {q(root+"/"+rel)} || exit 81\n'
  script+='echo '+role+'_COMPAT_ABSENT\n'
 for path in [*controls,CFG,HAP]:script+='sha256sum '+q(path)+'\n'
 script+=f'''envrows=$(strings /proc/{parent['pid']}/environ)
wids=$(printf '%s\\n' "$envrows" | sed -n 's/^WL_PARENT_ID=//p')
printf 'WL_PARENT_ID=%s\\n' "$wids"
test "$wids" = {wid}
power-shell dump -s
set +e
debug=$(param get debug.ttplayer.log.enable 2>&1); debug_rc=$?
set -e
printf 'DEBUG_PROCESS_RC=%s\\n%s\\n' "$debug_rc" "$debug"
'''+guard+'echo RESTORE_IDENTITY_MATCH\n'
 _,text=d.shell('final-restore-verification',script,60)
 verdict=verify_text(text,parent,new,controls,fresh['cfg_sha256'],fresh['hap_sha256'],fresh['debug_get_process_rc'])
 # No claims about feed/video: photos are preserved for outer human review.
 verdict.update(visual_verdict='PENDING_OUTER_REVIEW',holder=d.holder,start=d.start)
 dump(d.out/'recover-verdict.json',verdict)
 d.held();d.raw('unlock',['bash',str(d.repo/'scripts/lab/board_note.sh'),'unlock',str(d.repo/'.octos/boards/app-lighting.md'),SERIAL,d.holder.split()[0]],20)
 rc,body,_=d.raw('held-after',['bash',str(d.repo/'scripts/lab/board_note.sh'),'held',SERIAL],15,True)
 assert rc==1 and not body.strip(),'Unlock not independently confirmed'
 dump(d.out/'closed.json',{'status':'RESTORED_UNLOCKED','boot':new,'holder':d.holder,'start':d.start,'closed_at':time.time(),'elapsed_seconds':time.time()-d.start,'held_after_rc':rc,'ui':'actual normal-icon screenshots; visual verdict pending'})
if __name__=='__main__':entry(restore,True)
