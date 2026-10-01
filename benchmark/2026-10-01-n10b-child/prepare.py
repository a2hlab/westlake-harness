"""Build a U7-preserving child-only candidate and identity-bound native sidecars."""
import json,hashlib,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'scripts/lab'))
from deploy_generation import load_package,validate_replacement
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save=lambda p,d:p.write_text(json.dumps(d,indent=2)+'\n')
base=REPO.parent/'westlake-generation-n4-order-216b68fb';old=load_package(base)
binary=REPO.parent/'westlake-n10b-build/child-candidate/libwestlake_android_child.z.so';receipt=json.loads((HERE/'child-build-receipt.json').read_text());digest=sha(binary)
assert digest==receipt['candidate']['sha256']==receipt['repeat']['sha256']
out=REPO.parent/('westlake-generation-n10b-child-'+digest[:8]);assert not out.exists();subprocess.run(['/bin/cp','-Rc',str(base),str(out)],check=True)
m=load_package(out);target='/system/lib64/appspawn/libwestlake_android_child.z.so';artifact='payload/runtime/libwestlake_android_child.z.so';shutil.copyfile(binary,out/artifact);m['files'][artifact]=digest;m['live_hashes'][target]=digest
save(out/'package.json',m);validate_replacement(old,load_package(out),target);identity=sha(out/'package.json')
c=out/'native-checks';scan=json.loads((c/'scan-manifest.json').read_text());source='n10b-child.c';shutil.copy2(HERE/'src/sealed_child_provider_loader.c',c/source);scan['sources'][source]={'path':source,'sha256':sha(c/source),'origin':str((HERE/'src/sealed_child_provider_loader.c').relative_to(REPO)),'source_sha256':sha(c/source),'first_line':1}
scan['profiles'].append({'name':'child-owner','rule':'namespace','source':source,'identity':{'artifact':artifact}})
for p in scan['profiles']:p['identity'].update(package=out.name,manifest_sha256=identity,artifact_sha256=m['files'][p['identity']['artifact']])
save(c/'scan-manifest.json',scan);gate=json.loads((c/'native-gates.json').read_text());gate['package_manifest_sha256']=identity;gate['initialization']['manifest']['sha256']=sha(c/'scan-manifest.json');save(c/'native-gates.json',gate)
# Carry the signed U7 Java/image group without rebuilding or altering it.
bundlebase=REPO.parent/'westlake-generation-u7-executor-example';bundleout=REPO.parent/('westlake-generation-n10b-u7-'+digest[:8]);assert not bundleout.exists();subprocess.run(['/bin/cp','-Rc',str(bundlebase),str(bundleout)],check=True);shutil.rmtree(bundleout/'native');subprocess.run(['/bin/cp','-Rc',str(out),str(bundleout/'native')],check=True)
b=json.loads((bundleout/'bundle.json').read_text());b['native']['manifest']['sha256']=identity;b['rollout_ready']=False;b['rollout_blocker']='N10b child-only offline candidate; exact native exceptions and board window pending';save(bundleout/'bundle.json',b)
import generation_bundle as gb
_,_,resident=gb.validate(bundlebase)
for entry in b['reference'].values():
 paths=gb.read_fingerprint(bundlebase/entry['source']);(bundleout/entry['source']).write_text('\n'.join(sorted(f'{resident[p]}  {p}' for p in paths))+'\n');entry['sha256']=sha(bundleout/entry['source'])
save(bundleout/'bundle.json',b)
save(HERE/'package.json',{'native':out.name,'native_manifest_sha256':identity,'bundle':bundleout.name,'bundle_sha256':sha(bundleout/'bundle.json'),'child_sha256':digest,'changed_targets':[target],'device_io':False})
print(json.dumps(json.loads((HERE/'package.json').read_text())))
