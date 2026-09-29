#!/usr/bin/env python3
"""Inventory exact package + OH6.1 platform ELF closure, offline only."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
R=Path(__file__).resolve().parent
REPO=R.parents[1]
p=argparse.ArgumentParser();p.add_argument('--package',type=Path,default=Path('/Users/zhaoyue/orca/workspaces/westlake-generation-v3c-next-audio-anl'));a=p.parse_args()
POOL=REPO/'bms/src/.work/b68-generation/platform-pool'
READELF='/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin/llvm-readelf'
roots=[a.package/'payload/zigzag',a.package/'payload/android/lib64',a.package/'payload/route']+[POOL/('system/lib64/'+d) for d in ['ndk','platformsdk','chipset-sdk-sp','chipset-sdk']]+[POOL/'system/lib64',POOL/'system/lib']
index={}
for root in reversed(roots):
 for f in root.glob('*'):
  if f.is_file():index[f.name]=f
index['libc.so']=a.package/'payload/android/lib64/libc.so'
queue=['libandroid.so','libtuanjie.so','libhilog_ndk.z.so','libace_ndk.z.so'];rows={};missing=set()
while queue:
 name=queue.pop(0)
 if name in rows or name in missing:continue
 f=index.get(name)
 if f is None:missing.add(name);continue
 try:out=subprocess.check_output([READELF,'-d',str(f)],text=True,stderr=subprocess.STDOUT)
 except subprocess.CalledProcessError as e:raise RuntimeError((f,e.output))
 needed=re.findall(r'\(NEEDED\).*\[(.*?)\]',out);soname=re.findall(r'\(SONAME\).*\[(.*?)\]',out)
 rows[name]={'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'soname':soname,'needed':needed}
 queue.extend(needed)
ndk=sorted(k for k,v in rows.items() if '/system/lib64/ndk/' in v['path'])
result={'roots':[str(x) for x in roots],'seed':['libandroid.so','libtuanjie.so','libhilog_ndk.z.so','libace_ndk.z.so'],'resolved_count':len(rows),'missing':sorted(missing),'ndk_sonames':ndk,'files':rows,'scope':'DT_NEEDED only; runtime namespace and dlopen remain device-pending'}
(R/'needed-closure.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['resolved_count','missing','ndk_sonames']},indent=2))
