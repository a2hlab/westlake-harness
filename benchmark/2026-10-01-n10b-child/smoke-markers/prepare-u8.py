"""Fresh U8 bundles: child-only control and child + real Emboss batch."""
import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=next(p for p in H.parents if (p/"scripts/lab/u7_executor.py").is_file());WS=R.parent
sys.path.insert(0,str(R/'scripts/lab'));import generation_bundle as gb
from deploy_generation import load_package,validate_upgrade
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();save=lambda p,d:p.write_text(json.dumps(d,indent=2)+'\n')
BASE=WS/'westlake-generation-u8-j9-t7e';data,old,resident=gb.validate(BASE)
child=Path(os.environ.get('N10B_CHILD_BINARY',str(WS/'westlake-n10b-build/child-candidate/libwestlake_android_child.z.so')));runtime=Path(os.environ.get('N10B_RUNTIME_BINARY',str(WS/'westlake-n10b-build/runtime-init-side-effects/candidate/runtime-out/liboh_android_runtime.so')))
child_sha=sha(child);runtime_sha=sha(runtime);mode=os.environ.get('N10B_PREPARE_MODE','all');assert mode in ['all','batch'];records=json.loads((H/'u8-package.json').read_text()) if mode=='batch' else {}
for mode in (['batch'] if mode=='batch' else ['child','batch']):
 tag=child_sha[:8] if mode=='child' else runtime_sha[:8]
 native=WS/('westlake-generation-n10b-'+mode+'-u8-'+tag);bundle=WS/('westlake-generation-n10b-'+mode+'-bundle-u8-'+tag)
 assert not native.exists() and not bundle.exists()
 subprocess.run(['/bin/cp','-Rc',str(BASE/'native'),str(native)],check=True);m=load_package(native)
 replacements={'payload/runtime/libwestlake_android_child.z.so':child}
 if mode=='batch':replacements['payload/android/lib64/liboh_android_runtime.so']=runtime
 for artifact,source in replacements.items():
  before=m['files'][artifact];digest=sha(source);shutil.copy2(source,native/artifact);m['files'][artifact]=digest
  for target,value in list(m['live_hashes'].items()):
   if value==before:m['live_hashes'][target]=digest
 save(native/'package.json',m);validate_upgrade(old,load_package(native));identity=sha(native/'package.json')
 c=native/'native-checks';scan=json.loads((c/'scan-manifest.json').read_text());src='n10b-child.c';shutil.copy2(H/'src/sealed_child_provider_loader.c',c/src);scan['sources'][src]={'path':src,'sha256':sha(c/src),'origin':str((H/'src/sealed_child_provider_loader.c').relative_to(R)),'source_sha256':sha(c/src),'first_line':1};scan['profiles'].append({'name':'child-owner','rule':'namespace','source':src,'identity':{'artifact':'payload/runtime/libwestlake_android_child.z.so'}})
 if mode=='batch':
  src='n4-order-runtime.cpp';shutil.copy2(H/'src/AndroidRuntime.cpp',c/src);scan['sources'][src].update(sha256=sha(c/src),source_sha256=sha(c/src),origin=str((H/'src/AndroidRuntime.cpp').relative_to(R)))
  for p in (H/'src/emboss').glob('*.cpp'):shutil.copy2(p,c/('emboss-'+p.name))
  for n in ['android_graphics_Typeface.cpp','asset-offsets-init.cpp']:shutil.copy2(H/'src'/n,c/n)
 for p in scan['profiles']:p['identity'].update(package=native.name,manifest_sha256=identity,artifact_sha256=m['files'][p['identity']['artifact']])
 save(c/'scan-manifest.json',scan);g=json.loads((c/'native-gates.json').read_text());g['package_manifest_sha256']=identity;g['initialization']['manifest']['sha256']=sha(c/'scan-manifest.json');save(c/'native-gates.json',g)
 subprocess.run(['/bin/cp','-Rc',str(BASE),str(bundle)],check=True);shutil.rmtree(bundle/'native');subprocess.run(['/bin/cp','-Rc',str(native),str(bundle/'native')],check=True)
 b=json.loads((bundle/'bundle.json').read_text());b['native']['manifest']['sha256']=identity;b['rollout_ready']=False;b['rollout_blocker']='Offline N10b on U8; exact exceptions and single-variable board window pending outer approval'
 for entry in b['reference'].values():
  paths=gb.read_fingerprint(BASE/entry['source']);(bundle/entry['source']).write_text('\n'.join(sorted(f'{resident[p]}  {p}' for p in paths))+'\n');entry['sha256']=sha(bundle/entry['source'])
 save(bundle/'bundle.json',b);_,_,expected=gb.validate(bundle)
 changed=sorted(p for p in resident if expected[p]!=resident[p]);records[mode]={'native':native.name,'native_manifest_sha256':identity,'bundle':bundle.name,'bundle_sha256':sha(bundle/'bundle.json'),'child_sha256':child_sha,'runtime_sha256':m['files']['payload/android/lib64/liboh_android_runtime.so'],'changed_targets':changed,'device_io':False,'baseline_bundle':BASE.name,'baseline_bundle_sha256':sha(BASE/'bundle.json')}
 assert set(p for p in changed if not p.endswith('liboh_android_runtime.so'))=={'/system/lib64/appspawn/libwestlake_android_child.z.so'}
 for member in b['boot_group']['members']+[b['runtime_jar']]:assert sha(bundle/member['source'])==member['sha256']
save(H/'u8-package.json',records);print(json.dumps(records,indent=2))
