#!/usr/bin/env python3
"""Offline promotion from an outer-accepted disabled package. Never executes payloads."""
import argparse,json,hashlib,shutil,os,stat,difflib
from pathlib import Path
from prepare import regular,sha,allowed_promotion,NEW,OLD,INIT,PIN,SERIAL
P=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--t120',type=Path,required=True);ap.add_argument('--acceptance',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
review=json.loads(regular(a.acceptance));parent=json.loads(regular(a.t120/'output-manifest.json'))
if review['checker_rc']!=0 or review['payload_count_verified']!=22 or review['fixed_r3_outputs_verified']!=17:raise ValueError('acceptance scope')
if sha(regular(a.t120/'output-manifest.json'))!=review['owner_shas']['output-manifest.json']:raise ValueError('acceptance parent mismatch')
a.out.mkdir(parents=True,exist_ok=False);payload=a.out/'payload';payload.mkdir()
for rel,pin in parent.items():
 parts=Path(rel).parts
 if len(parts)!=2 or parts[0]!='payload' or parts[1] in ['.','..']:raise ValueError('manifest path')
 src=a.t120/'package'/rel
 if sha(regular(src))!=pin:raise ValueError('parent drift')
 shutil.copyfile(src,payload/parts[1])
before=regular(payload/'startup.env');after=before.replace(b"STARTUP_ENABLED='0'",b"STARTUP_ENABLED='1'").replace(b"STARTUP_APPROVED_BY='DISABLED-PENDING-OUTER'",b"STARTUP_APPROVED_BY='outer(codex)'")
expected=allowed_promotion(before,after);(payload/'startup.env').write_bytes(after);(payload/'startup.expected.sha256').write_bytes(expected)
modes={}
for line in regular(payload/'members.tsv').decode().splitlines():
 pin,name,mode=line.split()
 if Path(name).name!=name or mode not in ['550','440']:raise ValueError('member mode/path')
 if sha(regular(payload/name))!=pin:raise ValueError('member bytes changed')
 modes[name]=mode
modes.update({'boot-entry.sh':'550','startup.env':'440','startup.expected.sha256':'440','members.tsv':'440','recovery.cfg':'640','rollback-inert.cfg':'640'})
rows=[]
for f in sorted(payload.iterdir()):
 mode=modes[f.name];os.chmod(f,int(mode,8))
 actual=oct(stat.S_IMODE(f.stat().st_mode))[2:]
 if actual!=mode:raise ValueError('mode application')
 rows.append({'name':f.name,'sha256':sha(regular(f)),'mode':mode,'actual_local_mode':actual,'target':NEW+'/'+f.name,'target_owner':'0:0','install':f.name not in ['recovery.cfg','rollback-inert.cfg']})
changes=[r['name'] for r in rows if parent['payload/'+r['name']]!=r['sha256']]
if sorted(changes)!=['startup.env','startup.expected.sha256']:raise ValueError('extra byte change')
for n in ['init.before.cfg','init.after.cfg','init.rollback.cfg','init.diff']:
 src=P/'prepared-01'/n;regular(src);shutil.copyfile(src,a.out/n)
for n in ['init.before.cfg','init.after.cfg','init.rollback.cfg']:os.chmod(a.out/n,0o550)
if sha(regular(a.out/'init.rollback.cfg'))!=PIN:raise ValueError('rollback mismatch')
(a.out/'startup.diff').write_text(''.join(difflib.unified_diff(before.decode().splitlines(True),after.decode().splitlines(True),fromfile='disabled/startup.env',tofile='promotion/startup.env')))
manifest={'parent_output_manifest_sha256':sha(regular(a.t120/'output-manifest.json')),'acceptance_sha256':sha(regular(a.acceptance)),'files':rows,'init_before_sha256':PIN,'init_after_sha256':sha(regular(a.out/'init.after.cfg')),'init_mode':'550','changed_payload_bytes':changes,'fixed_payloads_unchanged':20,'original_T34_fixed17_unchanged':True,'parent_bytes_unchanged':all(sha(regular(a.t120/'package'/k))==v for k,v in parent.items())}
(a.out/'package-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
stage='/data/local/tmp/t121-5cd-r3';hdc='/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'
def command(shell):return [hdc,'-t',SERIAL,'shell',shell]
checks=[]
for r in rows:
 if not r['install']:continue
 f=r['target'];checks.append({'name':r['name'],'file_send_argv':[hdc,'-t',SERIAL,'file','send','$PROMOTION/payload/'+r['name'],stage+'/'+r['name']],'install_after_locked_preflight_argv':command("set -e; test -d "+NEW+"; test ! -L "+NEW+"; test ! -L "+f+"; test -f "+stage+'/'+r['name']+"; test ! -L "+stage+'/'+r['name']+"; test \"$(sha256sum "+stage+'/'+r['name']+" | cut -d' ' -f1)\" = "+r['sha256']+"; cp "+stage+'/'+r['name']+' '+f+"; chmod "+r['mode']+' '+f+"; chown 0:0 "+f+"; test \"$(sha256sum "+f+" | cut -d' ' -f1)\" = "+r['sha256']+"; stat -c '%n %a %u %g %F' "+f),'expected_readback':{'sha256':r['sha256'],'mode':r['mode'],'uid':0,'gid':0,'regular_file':True}})
plan={'status':'CONCRETE_OFFLINE_PROMOTION_DEVICE_EXECUTION_DISABLED','package_manifest_sha256':sha(regular(a.out/'package-manifest.json')),'serial':SERIAL,'root':NEW,'old_root_preserved':OLD,'budget_seconds':900,'rollback_reserve_seconds':180,'init':{'target':INIT,'service':'westlake-u13-toutiao-overlay','argv_index':1,'before':OLD+'/boot-entry.sh','after':NEW+'/boot-entry.sh','before_sha256':PIN,'after_sha256':manifest['init_after_sha256'],'mode':'550','uid':0,'gid':0,'generated_recovery_cfg_forbidden':True},'artifact_alias':'$PROMOTION = this promotion directory; local aliases must be bound by CC before execution','payload_commands':checks,'init_and_rollback_commands':{'send_candidate':[hdc,'-t',SERIAL,'file','send','$PROMOTION/init.after.cfg',stage+'/init.after.cfg'],'send_rollback':[hdc,'-t',SERIAL,'file','send','$PROMOTION/init.rollback.cfg',stage+'/init.rollback.cfg'],'verify_current':command('sha256sum '+INIT+"; stat -c '%n %a %u %g %F' "+INIT+'; ls -Z '+INIT),'reboot':command('reboot')},'execution_requirements':['Outer must confirm concrete package/plan SHA before CC sole-writer execution. No new user permission request.','CC fresh held/boot/init/oldROOT/host/network and ancestor non-symlink checks; drift refuses before writes.','NewROOT must be absent or exactly match the approved complete installed file set; create directories using the reviewed CC method and verify ownership/labels.','Stage all20 installable files, apply declared modes, verify each SHA/stat before init switch; screen-gate550 is mandatory.','Init replacement and rollback must use the existing reviewed CC system-write method preserving original SELinux label and mount state; these current values are not supplied here. No guessed remount/chcon command.','Before init change persist rollback bytes and verify staged original SHA19d0201b; after change verify SHA/mode/owner/label, reseal original mount state.','Unknown write outcome: stop new writes and reconcile read-only, no automatic repeat.','One software reboot and ordinary desktop icon click; sample10/30/60/90/120. No direct app launch.','On failure restore exact original init via same method, verify SHA/mode/label, reboot to oldROOT, restore fresh power values, verify lock release.'],'rollback':{'source':'init.rollback.cfg','sha256':PIN,'preserve_old_root':True,'candidate_root_cleanup':'No automatic deletion; keep evidence until reviewed.'},'pending_execution_bindings':['Fresh mount/SELinux/directory metadata and concrete existing CC atomic init write/restore method','Fresh lock/boot/power/network/host checks'],'actions':{'device':0,'runtime_execution':0}}
(a.out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps({'package_sha256':sha(regular(a.out/'package-manifest.json')),'plan_sha256':sha(regular(a.out/'plan.json')),'mode_readbacks':len(rows),'changed_payload_bytes':changes,'parent_unchanged':manifest['parent_bytes_unchanged']}))
