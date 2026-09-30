#!/usr/bin/env python3
import hashlib,json,re,subprocess,sys,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
BATCH=HERE.parent/'2026-09-28-bms-route-deploy/batch'
sys.path.insert(0,str(BATCH))
import bms_batch as b

def main():
 root=Path.home()/'a2hlab/app-inputs';apps=b.load_apps(BATCH/'apps.json',keys='fd-seal,toutiao,subwaysurfers');rows=[]
 for entry in apps:
  meta=root/entry['key']/'app-input.json';before=b.sha(meta)
  try:
   app=b.resolve_input(root,entry)
   rows.append(dict(key=entry['key'],status='host-preflight-pass',resolved=app,input_metadata_sha256=before,metadata=str(meta),device_install='unknown; current installer extraction policy not exercised',first_screen='unknown'))
  except Exception as e:rows.append(dict(key=entry['key'],status='blocked',reason=str(e)))
  assert b.sha(meta)==before
 sdk=Path.home()/'Library/Android/sdk/build-tools/37.0.0';directory=root/'subwaysurfers';checks=[]
 for name in ['subwaysurfers.apk','subwaysurfers.config.arm64_v8a.apk']:
  p=directory/name;cert=subprocess.run([str(sdk/'apksigner'),'verify','--print-certs',str(p)],capture_output=True,text=True,check=True).stdout
  badging=subprocess.run([str(sdk/'aapt2'),'dump','badging',str(p)],capture_output=True,text=True,check=True).stdout
  signer=re.search(r'(?m)^V3.0 Signer: certificate SHA-256 digest: (\w+)',cert)
  if signer is None:signer=re.search(r'(?m)^Signer #1 certificate SHA-256 digest: (\w+)',cert)
  assert signer
  checks.append(dict(path=str(p),sha256=b.sha(p),signer_sha256=signer[1],package_line=badging.splitlines()[0]))
 assert checks[0]['signer_sha256']==checks[1]['signer_sha256']=='a0328a96ac93be7983b5bec417bd2c03f129af6f8aff39512470e66a18dd964e'
 assert all("name='com.kiloo.subwaysurf'" in x['package_line'] and "versionCode='95769'" in x['package_line'] for x in checks)
 with zipfile.ZipFile(checks[1]['path']) as z:extra=[n for n in z.namelist() if not n.startswith(('lib/','META-INF/')) and n not in ['AndroidManifest.xml']]
 result=dict(inputs=rows,subway_pair=checks,subway_split_non_native_members=extra,source_allowlist=str(b.NATIVE_DATA_EXCEPTIONS),source_allowlist_sha256=b.sha(b.NATIVE_DATA_EXCEPTIONS),batch_sha256=b.sha(BATCH/'bms_batch.py'),manifest_sha256=b.sha(BATCH/'apps.json'),policy='Only host preflight repaired. Original APKs/meta untouched. Approved data preserved, not made loadable; installed extraction/readback pending board return. New Subway identity is a cohort revision, not retroactive forecast success.',screenshots=None,alive=None)
 (HERE/'results.json').write_text(json.dumps(result,indent=2)+'\n')
 assert all(r['status']=='host-preflight-pass' for r in rows)
 print('PASS',[(r['key'],len(r['resolved']['native_sidecars']),sum(bool(x.get('payload_exception')) for x in r['resolved']['native_sidecars'])) for r in rows],'extra split members',extra)
if __name__=='__main__':main()
