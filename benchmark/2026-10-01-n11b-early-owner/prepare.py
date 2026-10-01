"""Stage only the new child over U8; never authorize a rollout."""
import hashlib,json,os,shutil,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];W=Path(os.environ.get('WORKSPACES',R.parent))
sys.path.insert(0,str(R/'scripts/lab'))
import generation_bundle as gb,u7_executor as u
from deploy_generation import load_package,validate_upgrade
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save=lambda p,d:p.write_text(json.dumps(d,indent=2)+'\n')
base=W/'westlake-generation-u8-j9-t7e';_,old,resident=gb.validate(base)
binary=W/'westlake-n11b-early-owner-build/candidate/libwestlake_android_child.z.so';digest=sha(binary)
out=W/('westlake-generation-n11b-child-u8-'+digest[:8]);assert not out.exists();shutil.copytree(base,out)
n=out/'native';m=load_package(n);key='payload/runtime/libwestlake_android_child.z.so';before=m['files'][key];shutil.copy2(binary,n/key);m['files'][key]=digest
for p,v in m['live_hashes'].items():
 if v==before:m['live_hashes'][p]=digest
save(n/'package.json',m);validate_upgrade(old,load_package(n));manifest=sha(n/'package.json')
c=n/'native-checks';scan=json.loads((c/'scan-manifest.json').read_text());source=H/'src/sealed_child_provider_loader.c';name='n11b-child.c';shutil.copy2(source,c/name)
scan['sources'][name]={'path':name,'sha256':sha(source),'origin':str(source.relative_to(R)),'source_sha256':sha(source),'first_line':1}
scan['profiles'].append({'name':'n11b-early-owner','rule':'namespace','source':name,'identity':{'artifact':key}})
for p in scan['profiles']:p['identity'].update(package=out.name,manifest_sha256=manifest,artifact_sha256=m['files'][p['identity']['artifact']])
save(c/'scan-manifest.json',scan);g=json.loads((c/'native-gates.json').read_text());g['package_manifest_sha256']=manifest;g['initialization']['manifest']['sha256']=sha(c/'scan-manifest.json');save(c/'native-gates.json',g)
b=json.loads((out/'bundle.json').read_text());b['native']['manifest']['sha256']=manifest;b['rollout_ready']=False;b['rollout_blocker']='N11b child-only; native findings and window require outer approval';save(out/'bundle.json',b)
_,_,expected=gb.validate(out);changes={p:[resident[p],expected[p]] for p in resident if resident[p]!=expected[p]};assert set(changes)=={'/system/lib64/appspawn/libwestlake_android_child.z.so'}
plan=u.prepare(out,base/'native');save(H/'package.json',{'bundle':out.name,'native_manifest_sha256':manifest,'bundle_sha256':sha(out/'bundle.json'),'changes':changes,'identity_count':len(plan['expected']),'fingerprints':u.fingerprints(plan['expected'],plan['reference_paths']),'rollout_ready':False,'device_io':False});print(out.name,manifest,len(plan['expected']))
