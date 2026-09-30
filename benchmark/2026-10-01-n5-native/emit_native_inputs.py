#!/usr/bin/env python3
"""Bind unchanged N4-order source/DEX evidence and newly built ANL to one package."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def emit(package):
 package=package.resolve();out=package/'native-checks'
 assert not out.exists(), 'do not replace an existing build attestation'
 shutil.copytree(HERE.parent/'2026-10-01-native-predeploy-gates/inputs',out)
 manifest=json.loads((package/'package.json').read_text());identity=sha(package/'package.json')
 src=HERE/'flutter/flutter_domain.inc'
 assert 'domain->flutter_selected ? ":/system/android/lib64" : ""' in src.read_text()
 shutil.copy2(src,out/'flutter_domain.inc')
 p=out/'scan-manifest.json';d=json.loads(p.read_text())
 for profile in d['profiles']:
  old=profile['identity'];assert manifest['files'][old['artifact']]==old['artifact_sha256']
  old['package']=package.name;old['manifest_sha256']=identity
 p.write_text(json.dumps(d,indent=2)+'\n')
 p=out/'namespace-manifest.json';d=json.loads(p.read_text());d['config_sources'][0]['sha256']=sha(src)
 for domain in d['domains']:
  if domain['name']=='westlake_flutter':
   domain['search_paths'].append('/system/android/lib64');domain['permitted_paths'].append('/system/android/lib64')
  domain['source_evidence']['search_line']=35;domain['source_evidence']['permitted_line']=36
 p.write_text(json.dumps(d,indent=2)+'\n')
 p=out/'native-gates.json';d=json.loads(p.read_text());d['package_manifest_sha256']=identity
 d['initialization']['manifest']['sha256']=sha(out/'scan-manifest.json');d['namespaces']['manifest']['sha256']=sha(out/'namespace-manifest.json')
 d['namespaces']['owner_artifact']['sha256']=manifest['files']['payload/route/libapp_native_loader.so']
 p.write_text(json.dumps(d,indent=2)+'\n');return p
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('package',type=Path);a=p.parse_args();inputs=emit(a.package)
 with (HERE/'build-n1.json').open('w') as log:
  result=subprocess.run([sys.executable,str(ROOT/'scripts/lab/native_predeploy.py'),'--package',str(a.package),'--inputs',str(inputs),'--gate','N1'],stdout=log)
 raise SystemExit(result.returncode)
