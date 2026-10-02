#!/usr/bin/env python3
"""Offline U12 draft; no arming, device calls, builds or exception registry changes."""
import argparse,copy,hashlib,json,shutil,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];W=R.parent
sys.path.insert(0,str(R/'scripts/lab'))
import generation_bundle as gb,u7_executor as u,installation_chain
BASE=W/'westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle'
DEST=W/'westlake-inputs/generations/u12-native-draft-icu1e206531-media8fc0752d-policy2a6ec73f-v4/bundle'
PINS={'libicu_jni.so':'1e206531ad5994b7d3fe332a050d53163a8ab5cf954b9314d748d7ff2ae8ae8f','libmediandk.so':'8fc0752dd561a62992268981164c5e75c87ceb802f93d6d0b958c23b54ddaa58','libnativeloader.so':'2a6ec73fd87239ae90ba6464727649f5a4d73aab7588dda392df8803c2e76c4e'}
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n')
def portable(p):return str(p).replace(str(W),'$WORKSPACES')
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=DEST);a=p.parse_args();out=a.out
 assert gb.sha(BASE/'bundle.json')=='190afedd3ddb250752e67b83d19669b6a952eb04cd69db5edf0b06eafe119736'
 donor=W/'westlake-harness-bms/benchmark/2026-10-02-u12-mediandk'
 sources={'libicu_jni.so':W/'westlake-inputs/generations/u12-icu-1e206531.so','libmediandk.so':donor/'.artifacts/libmediandk-build1.so','libnativeloader.so':donor/'.artifacts/policy/candidate1/libnativeloader-candidate.so'}
 for name,src in sources.items():assert gb.sha(src)==PINS[name],name+' input drift'
 assert not out.exists(),'fresh output directory required'
 shutil.copytree(BASE,out);n=out/'native';old=json.loads((BASE/'native/package.json').read_text());m=copy.deepcopy(old)
 replacements={'payload/android/lib64/libicu_jni.so':sources['libicu_jni.so'],'payload/android/lib64/libmediandk.so':sources['libmediandk.so'],'payload/android/lib64/libnativeloader.so':sources['libnativeloader.so'],'payload/route/libnativeloader.so':sources['libnativeloader.so']}
 for rel,src in replacements.items():
  dst=n/rel;dst.parent.mkdir(parents=True,exist_ok=True)
  if dst.exists():dst.chmod(dst.stat().st_mode|0o200)
  shutil.copyfile(src,dst);m['files'][rel]=gb.sha(dst)
 for target in ['/system/android/lib64/libicu_jni.so','/system/android/lib64/libmediandk.so','/system/android/lib64/libnativeloader.so','/system/lib64/westlake/route-a/'+m['generation']+'/libnativeloader.so']:m['live_hashes'][target]=PINS[Path(target).name]
 m.update(rollout_ready=False,variant='U12 partial native draft on U10.1T8',rollout_blocker='Pending N11h-r2 / U12 Java+images / combined predictions / exact registry admission / outer window review')
 save(n/'package.json',m);manifest=gb.sha(n/'package.json');u.native.validate_upgrade(old,u.native.load_package(n))
 checks=n/'native-checks';scan=json.loads((checks/'scan-manifest.json').read_text())
 def source(name,src,artifact):
  shutil.copyfile(src,checks/name);scan['sources'][name]={'path':name,'sha256':gb.sha(src),'origin':portable(src),'source_sha256':gb.sha(src),'first_line':1}
  scan['profiles'].append({'name':name,'rule':'namespace','source':name,'identity':{'artifact':artifact}})
 for name in ['candidate.c','objects.c.inc']:source('u12-mediandk-'+name,donor/name,'payload/android/lib64/libmediandk.so')
 # Keep existing loader scanning pinned to the actual candidate's source snapshot.
 for name,src in [('u10-1-native-loader.cpp',donor/'inputs/native-loader/src/native_loader.cpp'),('u10-1-native-policy.h',donor/'.artifacts/policy/candidate1/source/include/nativeloader/native_bridge_policy.h')]:
  shutil.copyfile(src,checks/name);scan['sources'][name].update(sha256=gb.sha(src),source_sha256=gb.sha(src),origin=portable(src))
 for profile in scan['profiles']:profile['identity'].update(manifest_sha256=manifest,artifact_sha256=m['files'][profile['identity']['artifact']])
 save(checks/'scan-manifest.json',scan);gate=json.loads((checks/'native-gates.json').read_text());gate['package_manifest_sha256']=manifest;gate['initialization']['manifest']['sha256']=gb.sha(checks/'scan-manifest.json');save(checks/'native-gates.json',gate)
 b=json.loads((out/'bundle.json').read_text());b['native']['manifest']['sha256']=manifest;b['rollout_ready']=False;b['rollout_blocker']=m['rollout_blocker'];b['assembly_pending']=['N11h-r2','U12 runtime0482c9b1','U12 stubs without android.net','U12 paired rebaked boot group','combined U12 predictions','outer exception admission']
 b['static_checks']['baseline_bundle_sha256']=gb.sha(BASE/'bundle.json')
 # No static exceptions are carried from a different comparison pair. New-member refusal stays visible.
 policy={'jars':{},'native':{}};save(out/'static-policy-u12-draft.json',policy);b['static_checks']['policy']={'source':'static-policy-u12-draft.json','sha256':gb.sha(out/'static-policy-u12-draft.json')}
 # Rebase reference identities to the promoted effective view (not its old U9 references).
 _,_,resident=gb.validate(BASE)
 effective=u.effective_files(old,'native/');base_data=json.loads((BASE/'bundle.json').read_text());effective.update({row['target']:row for row in base_data['boot_group']['members']})
 for row in b['image_gate_reference']['members']:
  current=effective[row['target']];dst=out/row['source'];dst.chmod(dst.stat().st_mode|0o200);shutil.copyfile(BASE/current['source'],dst);row['sha256']=gb.sha(dst)
 for k in ['runtime','boot']:
  ref=out/b['reference'][k]['source'];paths=gb.read_fingerprint(ref);ref.write_text(''.join(resident[path]+'  '+path+'\n' for path in sorted(paths)));b['reference'][k]['sha256']=gb.sha(ref)
 save(out/'bundle.json',b)
 baseline_rows=u.effective_files(old);new_rows=u.effective_files(m);delta={p:{'before':baseline_rows.get(p,{}).get('sha256'),'after':r['sha256']} for p,r in new_rows.items() if baseline_rows.get(p,{}).get('sha256')!=r['sha256']}
 assert len(delta)==4 and len([v for v in delta.values() if v['before'] is None])==1
 assert m['files']['payload/zigzag/libmediandk.so']==old['files']['payload/zigzag/libmediandk.so']
 plan=u.prepare(out,BASE/'native')
 recovery=json.loads((R/'benchmark/2026-10-02-u10-1-t8-rerun/expected-run.json').read_text());boards={}
 for serial,board in recovery['boards'].items():
  expected=dict(board['expected']);assert len(expected)==316
  for path,row in delta.items():expected[path]=row['after']
  runtime=sorted(set(plan['reference_paths']['runtime'])|set(installation_chain.PATHS)|{'/system/android/lib64/libmediandk.so'})
  boards[serial]={'expected':expected,'identity_assertions':319,'unique_paths':317,'fingerprints':u.fingerprints(expected,{'runtime':runtime,'boot':plan['reference_paths']['boot']})}
 save(H/'recovery-u101t8.json',recovery)
 composition={'state':'DRAFT_INCOMPLETE','execution_enabled':False,'rollout_ready':False,'package':portable(out),'base_bundle':portable(BASE),'base_bundle_sha256':gb.sha(BASE/'bundle.json'),'base_native_manifest_sha256':gb.sha(BASE/'native/package.json'),'native_manifest_sha256':manifest,'bundle_sha256':gb.sha(out/'bundle.json'),'board_changes':delta,'pending':b['assembly_pending'],'candidate_boards':boards,'restore_state':'U10.1T8','restore_identity_assertions':318,'inputs':{k:{'path':portable(p),'sha256':PINS[k]} for k,p in sources.items()}}
 save(H/'composition.json',composition);save(H/'prepare-plan.json',plan)
 print(json.dumps({k:v for k,v in composition.items() if k not in ['candidate_boards','inputs']},indent=2))
if __name__=='__main__':main()
