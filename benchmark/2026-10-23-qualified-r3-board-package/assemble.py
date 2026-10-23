#!/usr/bin/env python3
"""T120: hash/copy approved immutable inputs, execute only the frozen package wrapper."""
import argparse,hashlib,json,shutil,subprocess,time
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--main',type=Path,required=True);ap.add_argument('--video',type=Path,required=True);ap.add_argument('--peer',type=Path,required=True);ap.add_argument('--t34',type=Path,default=Path.home()/'.local/share/westlake/t34-reentry-retirement-20261021');ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(n,d):(a.out/n).write_text(json.dumps(d,indent=2)+'\n')
def load(p):return json.loads(p.read_text())
BUILDER='0862a334f863d4de3bf3d4c4dda7ab1df7c6000e3b0e3d02e6c46f014aaf84d3'
rel=Path('benchmark/2026-10-19-toutiao-icon-reentry/generator/derive-candidate.sh');builder=REPO/rel
peer=a.peer/'benchmark/2026-10-23-explicit-board-build-inputs/review/results.json';review=load(peer)
assert sha(builder)==review['candidate_sha256']==BUILDER and review['status']=='PASS_WRAPPER_REVIEW_ONLY' and review['final_frozen_run']['passed']==review['final_frozen_run']['total']==24 and all(x['passed'] for x in review['cases'])
chainp=a.main/'benchmark/2026-10-21-t34-demo61b-video/reentry-retirement-01/deploy-package-r3-root/CHAIN.json';chain=load(chainp)
bp=a.main/'benchmark/2026-10-19-toutiao-icon-reentry/generator/base-pins.json';base=load(bp)
t116p=a.video/'benchmark/2026-10-23-current-control-fingerprint/index.json';pre=load(t116p)['boards']['5cd'];assert pre['same_boot']
t119p=a.video/'benchmark/2026-10-23-board-package-dependency-identities/results.json';addp=t119p.parent/'addendum/results.json';dep=load(t119p);add=load(addp)
assert dep['identity_stable'] and add['identity_stable'] and dep['boot_pre']==dep['boot_post']==add['boot_pre']==add['boot_post']==pre['boot_pre']==pre['boot_post']
root='/data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261023-5cd-r3';serial=pre['serial'];uid=add['host']['uid'][0];service=pre['init_cfg']['services'][0]['name']
old=a.t34/'old-suite-r3';stage=a.out/'staged';stage.mkdir();pins=[]
def cp(src,dst,expected,basis):
 actual=sha(src)
 if actual!=expected:raise ValueError('INPUT PIN MISMATCH '+str(src.relative_to(a.t34)) if src.is_relative_to(a.t34) else 'INPUT PIN MISMATCH '+src.name)
 dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst);assert sha(dst)==expected
 pins.append({'source':'$T34/'+str(src.relative_to(a.t34)) if src.is_relative_to(a.t34) else '$OWNER/'+str(src.relative_to(REPO)),'staged':str(dst.relative_to(stage)),'sha256':expected,'bytes':dst.stat().st_size,'basis':basis})
for item in base['files']:
 r=Path(base['source_roots'][item['source']])/item['source_name'];cp(old/r,stage/r,item['sha256'],'base-pins.json')
for name,dstname in [('watchdog-reentry.sh','watchdog.sh'),('reentry-common.sh','reentry-common.sh'),('reentry-seams.sh','reentry-seams.sh'),('exit-verdict.sh','exit-verdict.sh')]:
 r=Path('benchmark/2026-10-19-toutiao-icon-reentry/src')/name;cp(old/r,stage/r,chain['payload_manifest']['payload/'+dstname],'T34 CHAIN payload_manifest')
cp(builder,stage/rel,BUILDER,'T118 peer final02')
dump('input-manifest.json',pins)
fields=next(f['fields'] for f in pre['config_files'] if f['path']==pre['root']+'/startup.env');fields={k:v.strip("'") for k,v in fields.items()}
fields['STARTUP_APPROVED_BY']='DISABLED-PENDING-OUTER';fields['STARTUP_ENABLED']='0';fields['STARTUP_SERIAL']=serial
bound=[]
for key in ['STARTUP_JIT_SHA','STARTUP_REQUEST_SHA','STARTUP_NAMESPACE_SHA','STARTUP_HOST_SPAWN_SHA']:
 rows=add['declared_vs_actual'] if key in ['STARTUP_JIT_SHA','STARTUP_REQUEST_SHA'] else dep['declared_vs_actual'];r=next(x for x in rows if x['field']==key);actual=r.get('sha256',r.get('actual_sha256'));assert r['match'] is True and r.get('stable') is True and actual==fields[key];bound.append(r)
parent=stage/Path(base['source_roots']['R'])/'real-start-parent-bounded.sh';fields['STARTUP_START_PARENT_SHA']=sha(parent)
for key,file in [('STARTUP_DECODER_SHA','screen-gate'),('STARTUP_PROBE_SHA','decoder-probe.jpeg')]:assert fields[key]==chain['payload_manifest']['payload/'+file]
config=a.out/'startup-5cd.disabled.env';config.write_text('# Explicit T120 board input; offline only.\n'+''.join(f"{k}='{v}'\n" for k,v in fields.items()))
dump('external-bindings.json',bound)
# Frozen source gate and candidate-path intersection before building.
registry=a.main/'knowledge/frozen/frozen.json';reg=load(registry)
proposed=[root+'/'+k.removeprefix('payload/') for k in chain['payload_manifest']]+[pre['init_cfg']['path']]
intersection=[]
for e in reg['entries']:
 artifacts=[x['path'] for x in e.get('artifacts',[])];sources=[x.get('repo_path',x.get('path')) for x in e.get('sources',[])]
 hits=sorted(set(proposed)&set(artifacts));intersection.append({'id':e['id'],'artifact_paths':artifacts,'registered_source_paths':sources,'artifact_intersection':hits,'source_intersection':[],'status':'not-touched' if not hits else 'requires_artifact_gate'})
dump('frozen-intersection.json',{'registry_sha256':sha(registry),'proposed_target_paths':proposed,'source_changes':'No registered source changes; copied immutable inputs and frozen wrapper only.','entries':intersection,'limitation':'No claim that8 deployed artifact sets were verified.'})
assert not any(x['artifact_intersection'] for x in intersection)
def run(tag,cmd,cwd):
 d=a.out/tag;d.mkdir();(d/'argv.json').write_text(json.dumps({'argv':cmd,'cwd':str(cwd)},indent=2)+'\n');(d/'start').write_text(str(time.time()))
 with (d/'stdout').open('wb') as o,(d/'stderr').open('wb') as e:r=subprocess.run(cmd,cwd=cwd,stdout=o,stderr=e)
 (d/'rc').write_text(str(r.returncode)+'\n');(d/'end').write_text(str(time.time()))
 if r.returncode:raise RuntimeError(tag+' rc='+str(r.returncode))
run('frozen-git',['python3','scripts/lab/check_frozen.py','--git',str(a.main.resolve())],a.main.resolve())
package=a.out/'package';cmd=['/bin/sh',str(stage/rel),'--out',str(package),'--root',root,'--serial',serial,'--owner-uid',uid,'--service',service,'--startup-template',str(config),'--startup-template-sha256',sha(config)]
run('build',cmd,stage)
g=load(package/'generation.json');assert g['armed'] is False and g['startup_enabled']==0 and g['deployable'] is False
output={str(f.relative_to(package)):sha(f) for f in sorted((package/'payload').iterdir()) if f.is_file()}
fixed={k:v for k,v in chain['payload_manifest'].items() if k not in ['payload/config-common.sh','payload/members.tsv','payload/startup.env','payload/startup.expected.sha256','payload/recovery.cfg']}
assert all(output[k]==v for k,v in fixed.items())
assert sha(parent)==fields['STARTUP_START_PARENT_SHA'];dump('output-manifest.json',output)
current={Path(x['path']).name:x.get('sha256') for x in pre['config_files']+pre['hash_only_files'] if x.get('where','root')=='root' and '/boots/' not in x['path'] and x.get('exists',True)}
changes=[{'name':Path(k).name,'current_root_sha':current.get(Path(k).name),'candidate_sha':v,'comparison':'same' if current.get(Path(k).name)==v else 'different' if current.get(Path(k).name) else 'not_in_current_index'} for k,v in output.items()]
dump('changes.json',changes)
dump('receipt.json',{'status':'BUILT_DISABLED_NOT_DEPLOYABLE','builder_sha256':BUILDER,'peer_final_sha256':sha(peer),'input_count':len(pins),'output_count':len(output),'fixed_outputs_exact':len(fixed),'generation':g,'external_evidence_boot':pre['boot_pre'],'metadata_pins':{str(p.relative_to(a.main)) if p.is_relative_to(a.main) else '$VIDEO/'+str(p.relative_to(a.video)):sha(p) for p in [chainp,bp,t116p,t119p,addp]},'init_proposal':{'current_path':pre['init_cfg']['path'],'current_sha256':pre['init_cfg']['sha256'],'service':service,'before_argv':pre['init_cfg']['services'][0]['path'],'proposed_argv':['/system/bin/sh',root+'/boot-entry.sh'],'apply':False,'warning':'Do not install generated payload/recovery.cfg; exact current init bytes required for a later reviewed minimal edit.'},'limitations':['owner_uid is metadata only;5cd runtime compatibility not verified','Historical61b success does not establish5cd behavior','No device/controller execution or deployment','No new authorization blocker; concrete package verification remains outer task']})
print('build rc0; disabled payload22; fixed outputs exact',len(fixed))
