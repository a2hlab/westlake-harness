"""Assemble U10.1 final components over the immutable signed U9 bundle."""
import argparse,hashlib,json,os,shutil,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];sys.path.insert(0,str(R/'scripts/lab'))
import generation_bundle as gb
import u7_executor as u
from deploy_generation import load_package,validate_upgrade
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def approve(root, composition_path):
 """Arm the approved bundle and its drift guard together; payload/manifest stay fixed."""
 root=Path(root);composition_path=Path(composition_path)
 bundle_path=root/'bundle.json';before=bundle_path.read_bytes();previous=composition_path.read_bytes()
 b=json.loads(before);c=json.loads(previous)
 assert sha(bundle_path)==c['bundle_sha256'],'bundle drift before approval'
 assert sha(root/'native/package.json')==c['native_manifest_sha256'],'native manifest drift'
 gb.validate(root)
 b['rollout_ready']=True;b['rollout_blocker']=''
 b['window_authorization']='Outer ACK(90) 2026-10-02T01:37:54+08:00; observation only; unconditional U9 rollback'
 try:
  tmp=bundle_path.with_suffix('.json.approve-tmp');save(tmp,b);os.replace(tmp,bundle_path)
  c['rollout_ready']=True;c['bundle_sha256']=sha(bundle_path)
  c['window_authorization']=b['window_authorization']
  tmp=composition_path.with_suffix('.json.approve-tmp');save(tmp,c);os.replace(tmp,composition_path)
  assert json.loads(bundle_path.read_text())['rollout_ready'] is True
  assert sha(bundle_path)==json.loads(composition_path.read_text())['bundle_sha256']
 except BaseException:
  bundle_path.write_bytes(before);composition_path.write_bytes(previous);raise
 return c
def main():
 p=argparse.ArgumentParser();p.add_argument('--workspaces',type=Path,default=os.environ.get('WORKSPACES',R.parent));p.add_argument('--out',type=Path,required=True);p.add_argument('--host',type=Path);p.add_argument('--approve',action='store_true');a=p.parse_args();w=a.workspaces.resolve()
 if a.approve:
  print(json.dumps(approve(a.out,H/'composition.json')));return
 assert a.host is not None,'--host required for assembly'
 base=w/'westlake-generation-u9-j10g-238ffc14';_,old,resident=gb.validate(base)
 source=w/'westlake-harness-bms/benchmark/2026-10-01-u10-native-shims'
 jar=w/'westlake-generation-u11-staging/oh-adapter-runtime-u11i.jar';assert sha(jar)=='5ae3dd29d45c2270e8a53a9dc4bbeeca8972b9b092f91898a15d605bc1cc0108'
 hostreceipt=json.loads((a.host.parent/'host-build-receipt.json').read_text());assert sha(a.host)==hostreceipt['runs'][0]['sha256'];assert hostreceipt['runtime_generation']==old['generation'];assert hostreceipt['child_sha256']==old['files']['payload/runtime/libwestlake_android_child.z.so']
 replacements={'libbionic_compat.so':source/'.artifacts/libbionic_compat-candidate.so','libnativeloader.so':w/'westlake-inputs/generations/u10.1-policy-repro/u10.1-build/libnativeloader.so','appspawn-x':a.host}
 expected_sha={'libbionic_compat.so':'015aa3a632eabe057bd8d6ce0e0ff181209da7dcab8de22409a79addc0a56d58','libnativeloader.so':'0718f01e237d322b5a16a1858265f8cc05cddd5ddca6d1ceb28bcc33023913a9','appspawn-x':'65cc3535ebf22bdf664b3c8ddf932ccd7f42d936be1c861e1221a80b12a00284'}
 for name,path in replacements.items():assert sha(path)==expected_sha[name],name+' input drift'
 assert not a.out.exists();shutil.copytree(base,a.out);n=a.out/'native';m=load_package(n);changed=[]
 for relative,previous in list(m['files'].items()):
  name=Path(relative).name
  if name not in replacements:continue
  dst=n/relative;dst.chmod(dst.stat().st_mode|0o200);shutil.copyfile(replacements[name],dst);m['files'][relative]=sha(dst);changed.append({'file':relative,'before':previous,'after':sha(dst)})
 # All aliases use the actual final payload bytes, including directory-owned targets not originally live_hashes.
 for target,previous in list(m['live_hashes'].items()):
  name=Path(target).name
  if name in replacements:m['live_hashes'][target]=sha(replacements[name])
 for name in ['libbionic_compat.so','libnativeloader.so']:
  for target in ['/system/android/lib64/'+name,'/system/lib64/westlake/route-a/'+m['generation']+'/'+name]:m['live_hashes'][target]=sha(replacements[name])
 m.update(variant='U10.1 SoundPool-preserving policy + host r3 + compat over signed U9',rollout_ready=False,rollout_blocker='Offline assembly; new native findings and window admission require outer review')
 save(n/'package.json',m);validate_upgrade(old,load_package(n));manifest=sha(n/'package.json')
 c=n/'native-checks';scan=json.loads((c/'scan-manifest.json').read_text())
 def add_source(name,path):
  shutil.copyfile(path,c/name);scan['sources'][name]={'path':name,'sha256':sha(path),'origin':'$WORKSPACES/'+str(path.relative_to(w)),'source_sha256':sha(path),'first_line':1}
 add_source('n4-host.c',source/'host-r3/candidate-stock-host.c')
 add_source('u10-1-resident-compat.h',source/'host-r3/resident-compat.h')
 policy=w/'westlake-inputs/generations/u10.1-policy-repro/native-loader-u10.1'
 add_source('u10-1-native-loader.cpp',policy/'src/native_loader.cpp')
 add_source('u10-1-native-policy.h',policy/'include/nativeloader/native_bridge_policy.h')
 scan['profiles'].append({'name':'u10-1-resident-compat','rule':'namespace','source':'u10-1-resident-compat.h','identity':{'artifact':'payload/runtime/appspawn-x'}})
 scan['profiles'].append({'name':'u10-1-native-loader-policy','rule':'namespace','source':'u10-1-native-loader.cpp','identity':{'artifact':'payload/route/libnativeloader.so'}})
 for p in scan['profiles']:p['identity'].update(package=a.out.name,manifest_sha256=manifest,artifact_sha256=m['files'][p['identity']['artifact']])
 save(c/'scan-manifest.json',scan)
 gates=json.loads((c/'native-gates.json').read_text());gates['package_manifest_sha256']=manifest;gates['initialization']['manifest']['sha256']=sha(c/'scan-manifest.json');save(c/'native-gates.json',gates)
 b=json.loads((a.out/'bundle.json').read_text());b['native']['manifest']['sha256']=manifest
 for member in [b['runtime_jar']]:
  if member['target']=='/system/android/framework/oh-adapter-runtime.jar':
   dst=a.out/member['source'];dst.chmod(dst.stat().st_mode|0o200);shutil.copyfile(jar,dst);member['sha256']=sha(jar)
 b['rollout_ready']=False;b['rollout_blocker']='U10.1 offline candidate; native exceptions and separate board authorization pending';save(a.out/'bundle.json',b)
 baseline_plan=u.prepare(base,w/'westlake-generation-u8-j9-t7e/native')
 for key in ['runtime','boot']:
  f=a.out/b['reference'][key]['source'];paths=gb.read_fingerprint(f)
  f.write_text(''.join(baseline_plan['expected'][q]+'  '+q+'\n' for q in sorted(paths)))
  b['reference'][key]['sha256']=sha(f)
 save(a.out/'bundle.json',b)
 _,_,expected=gb.validate(a.out);changes={p:[resident.get(p),v] for p,v in expected.items() if resident.get(p)!=v}
 assert set(changes)=={'/system/bin/appspawn-x','/system/android/framework/oh-adapter-runtime.jar'}|{root+'/'+name for root in ['/system/android/lib64','/system/lib64/westlake/route-a/'+m['generation']] for name in ['libbionic_compat.so','libnativeloader.so']},'unexpected board delta'
 save(H/'composition.json',{'base':'U9','round':'U10.1','package':'$WORKSPACES/'+str(a.out.relative_to(w)),'native_manifest_sha256':manifest,'bundle_sha256':sha(a.out/'bundle.json'),'generation':m['generation'],'changed_members':changed,'board_changes':changes,'core_identity_count':312,'identity_count':316,'identity_assertions':318,'offline_only':True,'rollout_ready':False,'OpenSLES':'deferred U11','libjnigraphics':'deferred U11 by outer ACK 21:37:06'})
 plan=u.prepare(a.out,base/'native');services=json.loads((R/'benchmark/2026-10-01-installation-chain-identity/current-u9.json').read_text());boards={}
 for serial,row in services['boards'].items():
  e=plan['expected']|row['services'];assert len(e)==316
  extended=[q for q in e if q in plan['reference_paths']['runtime'] or q in row['services']]
  boards[serial]={'expected':e,'fingerprints':u.fingerprints(e,{'runtime':extended,'boot':plan['reference_paths']['boot']}),'legacy_fingerprints':u.fingerprints(e,plan['reference_paths']),'identity_assertions':318,'unique_paths':316}
  (H/('expected-'+serial[:8]+'.txt')).write_text(''.join(e[q]+'  '+q+'\n' for q in sorted(e)))
 save(H/'expected-run.json',{'boards':boards})
 print(json.dumps({'native_manifest_sha256':manifest,'bundle_sha256':sha(a.out/'bundle.json'),'changed_board_paths':len(changes),'identity_count':len(expected)}))
if __name__=='__main__':main()
