#!/usr/bin/env python3
"""Local-only evidence intake; no service, build, device, or network actions."""
import hashlib,json,os,subprocess,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
WS=Path(os.environ.get('WORKSPACES',str(ROOT.parents[2])))
ROOTS={'main':WS/'westlake-harness','workspace':WS,'home':Path.home(),'sdk':Path(os.environ.get('T53_OH_SDK','/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony')),'packet':ROOT}
BASE='8bfba21cfb6658462502e6640f66577ef81db574'
def digest(b):return hashlib.sha256(b).hexdigest()
def require(ok,msg):
 if not ok:raise ValueError(msg)
refs=[]
def add(id,root,path,start,end,kind,claim):
 p=ROOTS[root]/path;b=p.read_bytes();lines=b.decode().splitlines();require(1<=start<=end<=len(lines),id+' line range')
 ref={'id':id,'root':root,'path':path,'sha256':digest(b),'bytes':len(b),'lines':[start,end],'excerpt_sha256':digest('\n'.join(lines[start-1:end]).encode()),'kind':kind,'claim':claim,'computed_git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
 if root=='main':
  obj=subprocess.run(['git','-C',str(ROOTS['main']),'show',BASE+':'+path],capture_output=True)
  ref['fixed_main_blob_matches']=obj.returncode==0 and obj.stdout==b
 refs.append(ref)
add('contract','main','specs/toutiao-video-playback/t53-owned-service-interface.spec.md',1,38,'contract','Scope and three static-only scenarios; no runtime acceptance.')
add('gap','main','benchmark/2026-10-22-toutiao-lifecycle-entry-gap/README.md',1,30,'accepted_report','Missing normal lifecycle-to-owned-service connection; callbacks already proven.')
add('t52','main','benchmark/2026-10-22-toutiao-owned-exit-fix-window/README.md',1,14,'accepted_report','Natural classification; candidate white; restored feed not close-reopen acceptance.')
add('t52-results','main','benchmark/2026-10-22-toutiao-owned-exit-fix-window/results.json',1,20,'accepted_report','T52 machine record retained; no new device interpretation.')
add('oh-source-root','main','.octos/OPS-RUNBOOK.md',54,57,'source_location','Recorded same-board OH 6.1.0.31 tree is on hw248; not accessed.')
add('prior-missing-ams','main','benchmark/2026-10-03-category-home-token/README.md',40,44,'historical_location','Names ability_manager_service.cpp; does not provide its relative implementation path or source.')
add('entry','main','benchmark/2026-10-20-toutiao-launcher-page/sources/baseline/EntryAbility.js',1,36,'implementation','Exact 9dc host source records lifecycle and loads Index; no service request.')
add('t32-receipt','main','benchmark/2026-10-20-toutiao-launcher-page/production-01.json',30,63,'accepted_report','Signed member equality includes module.json.')
add('t32-source-location','main','benchmark/2026-10-12-v1-seal-execution/5cd-host-install/source.json',1,4,'source_location','Exact historical df385 HAP at HOME alias.')
add('t32-archive','main','benchmark/2026-10-20-t32-host-page-accepted/archive-members.json',590,597,'source_location','Archived release candidate HAP entry; not a new archive retrieval.')
add('sdk-declaration','sdk','ets/api/application/UIAbilityContext.d.ts',1811,1839,'declaration','Client declaration documents visibility/permission errors; not implementation.')
add('sdk-version','sdk','ets/oh-uni-package.json',1,10,'version','Available SDK 6.1.1.125 API24; not same-board 6.1.0.31 implementation proof.')
add('vm-module','workspace','vm-copies/westlake-current/apps/imehost/module.json',1,39,'unbound_manifest','Different raw bytes; not substituted for exact signed module.')
add('vm-entry','workspace','vm-copies/westlake-current/apps/imehost/EntryAbility.js',1,36,'implementation','Byte-equal to exact T32 EntryAbility source only.')
add('spawn-client','workspace','vm-copies/westlake-current/native/host_spawn.c',1,52,'implementation','Historical native request-file transport, not ordinary app lifecycle API.')
add('spawn-server','workspace','vm-copies/westlake-current/framework/appspawn-x/src/spawn_server.cpp',419,457,'implementation','Message parse and handler dispatch; no current caller authorization binding.')
add('spawn-handler','workspace','vm-copies/westlake-current/framework/appspawn-x/src/main.cpp',300,328,'implementation','Registers the historical fork handler; never executed here.')
add('spawn-config','workspace','vm-copies/westlake-current/framework/appspawn-x/config/appspawn_x.cfg',27,60,'registration','Historical root service, root:appspawn 0660 socket; not current host permission proof.')
add('spawn-build','workspace','vm-copies/westlake-current/framework/appspawn-x/BUILD.gn',29,107,'build','Builds server sources and installs init cfg; not deployment/complete source provenance.')
add('client-build','workspace','vm-copies/westlake-current/historical/workspace/bridge-build-arm64/ime-ability-window-20260904/stage_candidate.py',66,70,'build','Historical client compilation recipe only, read as bytes, never invoked.')
add('historical-client','workspace','vm-copies/westlake-current/historical/workspace/bridge-build-arm64/ime-ability-window-20260904/host_spawn.c',1,52,'implementation','Exact byte match to client source named by historical recipe.')
add('harness-cfg','main','benchmark/2026-10-12-v1-seal-assembly/restore-v6/package-composed-disabled/payload/recovery.cfg',7,34,'harness_control','Condition + once root init entry; not ordinary app service interface.')
add('harness-entry','main','benchmark/2026-10-12-recovery-executor/payload/boot-entry.sh',11,27,'harness_control','Existing same-boot attempt refuses; no changes or execution.')
# Only read exact signed HAPs and their non-secret module member. No profile/key/argv reads.
haps=[];member=None
for root,path,expected in [('home','a2hlab-provision/ttbundle/source-host.hap','df3856387ba6971202b33e4475fde4e0fb1bf7fb33da0f4250429fe6535b014a'),('home','.local/share/westlake/toutiao-launcher-20261020/release-01/candidate-signed.hap','b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0')]:
 p=ROOTS[root]/path;require(digest(p.read_bytes())==expected,'HAP pin drift')
 with zipfile.ZipFile(p) as z:b=z.read('module.json')
 require(digest(b)=='0dbaacbe6b17eadecda308d65e77483bf87fe2971695fecac1a5b55a5d137b51','module pin drift')
 if member is not None:require(member==b,'module mismatch')
 member=b;haps.append({'root':root,'path':path,'sha256':expected,'member':'module.json','member_sha256':digest(b)})
(ROOT/'evidence/t32-signed-module.json').write_bytes(member)
add('signed-module','packet','evidence/t32-signed-module.json',1,len(member.decode().splitlines()),'bound_manifest','Exact module bytes from both df385 and b189 HAPs, agreeing with T32 receipt.')
component='oh61-bms-kit-background-launcher/foundation/ability/ability_runtime/'
missing=[]
def gap(id,local,needed,basis):
 missing.append({'id':id,'status':'missing_local_source' if local else 'unverified_binding','local_root':'workspace' if local else None,'local_path':local,'observed_exists':(ROOTS['workspace']/local).exists() if local else None,'needed':needed,'basis_refs':basis})
gap('oh-client',component+'frameworks','Exact 6.1.0.31 connectServiceExtensionAbility client implementation and IPC call chain.',['sdk-declaration','oh-source-root'])
gap('oh-server',component+'services','Exact 6.1.0.31 AbilityManager service connection dispatch and all caller identity/permission checks. Only ability_manager_service.cpp basename is previously recorded; precise nested filename is NOT source-verified locally.',['prior-missing-ams','oh-source-root'])
gap('oh-build',component+'BUILD.gn','Same-version framework/service build target graph and source membership.',['oh-source-root'])
gap('oh-registration',component+'bundle.json','Same-version component metadata, service registration/ID/profile and linked permission implementation closure.',['oh-source-root'])
gap('owned-endpoint',None,'Existing owned bridge request handler, identity validation, actual registered target name and build inclusion; signed host has no extensionAbilities registration.',['signed-module','entry','gap'])
gap('host-authorization',None,'Permission/identity admission for exact org.westlake.imehost normal token at the actual service; absence of requested special permission is not a grant or a proof all public service calls are forbidden.',['signed-module','sdk-declaration'])
gap('spawn-current-binding',None,'Exact source/artifact/config binding of this historical AppSpawnX path to the current Toutiao parent; no inference from filenames.',['spawn-config','spawn-build','harness-cfg'])
gap('spawn-app-admission',None,'Supported ordinary host client, authenticated server admission and current socket/SELinux authorization. Root internal transport is not proof; no change to permissions proposed.',['spawn-client','spawn-server','spawn-config'])
for g in missing:
 if g['local_path']:require(g['observed_exists'] is False,'missing path now present; revise report')
def candidate(id,name,client,server,perm_client,perm_server,registration,build,gaps,description):
 return {'id':id,'name':name,'status':'GAP','runtime_capability':'unknown','existing_implementation':description,'source_refs':sorted(set(client+server+perm_client+perm_server+registration+build)), 'client':{'status':'partial','refs':client},'server':{'status':'missing' if not server else 'partial','refs':server},'caller_requirements':{'client':{'status':'partial','refs':perm_client},'server':{'status':'missing' if not perm_server else 'partial','refs':perm_server}},'registration':{'status':'partial' if registration else 'missing','refs':registration},'build':{'status':'partial' if build else 'missing','refs':build},'missing_parts':gaps}
report={'schema':1,'task':'T53','status':'GAP','implementation_ready':False,'runtime_capability':'unknown','main_input_commit':BASE,'source_refs':refs,'signed_host_manifest':{'status':'EXACT_BYTES_BOUND','containers':haps,'source_ref':'signed-module','registered_abilities':['EntryAbility'],'registered_extension_abilities':[],'request_permissions':['ohos.permission.INTERNET','ohos.permission.GET_NETWORK_INFO'],'profile_authorization':'Not reread; no new token/ACL grant inferred.'},'missing_parts':missing,'upstream_source_request':{'recorded_root':'/opt/build-trees/oh610_lts_source','component':'foundation/ability/ability_runtime','version':'6.1.0.31','basis_refs':['oh-source-root','prior-missing-ams'],'known_basename':'ability_manager_service.cpp','nested_implementation_paths':'unknown; do not fabricate exact client/server permission filenames','required':'Provide the actual version-pinned client connect implementation, server dispatch + permission callees, registration and build references. No fetch was performed.'},'candidates':[candidate('service-extension','Normal UIAbilityContext service connection',['sdk-declaration'],[],['sdk-declaration','signed-module'],[],['signed-module'],[],['oh-client','oh-server','oh-build','oh-registration','owned-endpoint','host-authorization'],'Only a public declaration is locally present. No owned service handler or endpoint registration has been proven. Existing host lifecycle source is unchanged and does not emit the call.'),candidate('historical-appspawn','Historical AppSpawnX internal transport',['spawn-client','historical-client'],['spawn-server','spawn-handler'],['spawn-client','signed-module'],['spawn-config','spawn-server'],['spawn-config'],['spawn-build','client-build'],['spawn-current-binding','spawn-app-admission'],'Client, handler and recipe text exist, but they do not form a supported ordinary-host service endpoint. Historical cfg requires root/appspawn socket access; actual current caller authorization remains unknown.')], 'harness_control_separate':{'refs':['harness-cfg','harness-entry'],'conclusion':'Root condition/once and per-boot attempt are recovery controls, not a host service API; no calling recipe proposed.'},'next_step_criteria':['Close the exact-version client/server/permission/registration/build source gaps locally before considering implementation.','Bind the existing endpoint and current ordinary-host authorization without permission changes; absence stays GAP.','Only after independent acceptance of static closure may a separate implementation/window be considered; callback observations and READY labels cannot supply authority.'],'actions':{'device':0,'remote':0,'rea':0,'service_requests':0,'runtime_changes':0,'runtime_builds':0,'commit':0,'push':0},'limits':['At most two candidates; bounded local source intake only.','No claim that no service exists anywhere; no complete server source is available in inspected roots.','SDK 6.1.1.125 API24 declaration is not same-version 6.1.0.31 implementation proof.','T52 candidate remained white; restored feed and natural recovery do not prove close-reopen.']}
bm_path='.local/share/westlake/t52-execution-outer-20261022/private-raw/raw/12-final/bm.stdout'
bm_bytes=(ROOTS['home']/bm_path).read_bytes()
require(digest(bm_bytes)=='0f1f1e67e94be91a188652bb438e87232d40dfd0a936c16d58086880c5bc245b','T52 bm source drift')
add('t52-caller','home',bm_path,1,len(bm_bytes.decode().splitlines()),'runtime_observation','2026-10-22 final restored sample only; not fresh authorization or proof of service call ability.')
bm_text=bm_bytes.decode();bm=json.JSONDecoder().raw_decode(bm_text[bm_text.index('{'):])[0]['applicationInfo']
fields={k:bm[k] for k in ('appPrivilegeLevel','isSystemApp','accessTokenId','uid','appProvisionType','permissions')}
require(fields=={'appPrivilegeLevel':'normal','isSystemApp':False,'accessTokenId':537137511,'uid':20011300,'appProvisionType':'release','permissions':[]},'T52 caller facts mismatch')
report['caller_observation']={'status':'CURRENT_KNOWN_HISTORICAL_SAMPLE_NOT_FRESH','sample_date':'2026-10-22','source_ref':'t52-caller','json_pointer':'/applicationInfo','fields':fields,'outer_manifest_sha256':'60ccfa48e4280a9129fa1a3e9cb336313c7fa0cd2e023935a38d149b18319256','manifest_scope':'Outer-provided membership/verification; T53 independently hashes only this original bm.stdout.','interpretation':'HAP requestPermissions are declarations. Actual sampled permissions are empty; no system-app or root authority inferred. Does not decide whether a particular public endpoint would admit this caller.'}
for c in report['candidates']:
 c['caller_requirements']['client']['refs'].append('t52-caller');c['source_refs'].append('t52-caller')
report['main_head_observed']=subprocess.check_output(['git','-C',str(ROOTS['main']),'rev-parse','HEAD'],text=True).strip()
(ROOT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':'GAP','refs':len(refs),'candidates':2,'signed_module_sha256':digest(member)}))
