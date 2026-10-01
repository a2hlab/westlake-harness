"""Assemble offline U9 native + separately declared installer component."""
import argparse,hashlib,json,os,shutil,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];W=Path(os.environ.get('WORKSPACES',R.parent))
sys.path.insert(0,str(R/'scripts/lab'));import generation_bundle as gb,u7_executor as u
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def check(root):
 data,_,_=gb.validate(root);gb.member(root,data['service_group']['manifest'])
 for row in data['service_group']['members']:gb.member(root,row)
 manifest=json.loads((root/data['service_group']['manifest']['source']).read_text())
 for name,digest in {**manifest['candidate'],**manifest['rollback']}.items():
  if sha(root/'installer'/name)!=digest:raise ValueError('service SHA mismatch: '+name)
 if data.get('rollout_ready') is not False or manifest['deployable'] is not False:raise ValueError('offline candidate cannot authorize foundation rollout')
 if data['service_group']['handled_by_u7_executor'] is not False:raise ValueError('service activation not implemented by appspawn-only executor')
 plan=u.prepare(root,W/'westlake-generation-u8-j9-t7e/native')
 return {'identities':len(plan['expected']),'fingerprints':u.fingerprints(plan['expected'],plan['reference_paths']),'service_deployable':False,'device_io':False}
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists()
 source=W/'westlake-generation-n10b-deployable-u8-ac59dec0'
 if sha(source/'native/package.json')!='a118aca0fb3a097eec3a1f7209c5e41d4308c351c8ae604580a0df0db2724050':raise ValueError('N10b source manifest changed')
 shutil.copytree(source,a.out);component=a.out/'installer';component.mkdir()
 build=W/'westlake-u9-native-build-r3/candidate/libapk_installer.so';original=W/'westlake-installer-background-launcher-6aadb8b4'
 for src,name in [(build,'libapk_installer.so'),(original/'libapk_installer.so','rollback-libapk_installer.so'),(original/'libbms.z.so','libbms.z.so')]:shutil.copy2(src,component/name)
 shutil.copy2(H/'installer-component.json',component/'component.json');shutil.copy2(H/'bundle-template.json',a.out/'bundle.json')
 print(json.dumps(check(a.out),indent=2))
if __name__=='__main__':main()
