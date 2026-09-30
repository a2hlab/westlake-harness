#!/usr/bin/env python3
"""Read-only Flutter ELF preflight; owner reachability is a separate device gate."""
import argparse, hashlib, json, re, subprocess
from pathlib import Path
from collections import deque
P=argparse.ArgumentParser();P.add_argument('--inputs',type=Path,required=True);P.add_argument('--package',type=Path,required=True);P.add_argument('--pool',type=Path,required=True);P.add_argument('--out',type=Path,required=True);P.add_argument('--candidate',type=Path);a=P.parse_args()
keys=['fd-fluffychat','fd-immich','fd-kitchenowl','fd-libre','fd-saber','localsend']
roots=[a.package/'payload/android/lib64',a.package/'payload/route']+[a.pool/('system/lib64'+s) for s in ['','/platformsdk','/chipset-sdk','/chipset-sdk-sp','/ndk']]
index={}
for root in roots:
 for f in sorted(root.glob('*.so*')):
  if f.is_file():index.setdefault(f.name,f)
# Proposed owner resolution. Do not pretend the empty GLES facade has exports.
index['libandroid.so']=a.package/'payload/android/lib64/liboh_android_runtime.so'
index['libGLESv2.so']=a.pool/'system/lib64/platformsdk/libGLESv3.so'
# OH libc owns dl/m. Record alias rather than mark physical absence as success.
index['libdl.so']=a.pool/'system/lib64/libc.so';index['libm.so']=index['libdl.so']
if a.candidate:
 for soname,filename in [('libandroid.so','libwestlake_flutter_android.so'),('libGLESv2.so','libwestlake_flutter_gles2.so'),('libjnigraphics.so','libwestlake_flutter_jnigraphics.so')]:
  index[soname]=a.candidate/soname
cache={}
def elf(f):
 k=str(f)
 if k not in cache:
  s=subprocess.check_output(['llvm-readelf','-d','--dyn-syms','--version-info',k],text=True)
  syms=[]
  for l in s.splitlines():
   m=re.match(r'\s*\d+:\s+\S+\s+\d+\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)',l)
   if m:
    typ,bind,vis,ndx,name=m.groups()
    syms.append(dict(name=name,base=name.split('@')[0],version=name.split('@')[-1] if '@' in name else None,bind=bind,visibility=vis,undefined=ndx=='UND'))
  cache[k]={'path':k,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'needed':re.findall(r'\(NEEDED\).*\[(.*?)\]',s),'soname':re.findall(r'\(SONAME\).*\[(.*?)\]',s),'symbols':syms}
 return cache[k]
reports=[]
for key in keys:
 own={f.name:f for f in (a.inputs/key/'lib/arm64-v8a').glob('*.so')}
 engine=own['libflutter.so'];todo=deque([engine,a.pool/'system/lib64/libc.so']);seen=set();edges=[];missing=[]
 # Explicit preload supply, not proof that namespace will inherit these owners.
 for n in ['libbionic_compat.so','libwestlake_bionic_pthread_bridge.so','libwestlake_native_abi.so','libc.so','liblog.so']:
  if n in index:todo.append(index[n])
 while todo:
  f=todo.popleft()
  if str(f) in seen:continue
  seen.add(str(f));r=elf(f)
  for n in r['needed']:
   target=own.get(n) or index.get(n);edges.append({'from':str(f),'needed':n,'to':str(target) if target and target.exists() else None})
   if target and target.exists():todo.append(target)
   else:missing.append({'from':str(f),'needed':n})
 exports={}
 for f in seen:
  for s in cache[f]['symbols']:
   if not s['undefined'] and s['bind'] in ['GLOBAL','WEAK'] and s['visibility'] in ['DEFAULT','PROTECTED']:
    exports.setdefault(s['base'],[]).append({'path':f,'version':s['version'],'name':s['name']})
 imports=[s for s in elf(engine)['symbols'] if s['undefined'] and s['bind']=='GLOBAL']
 absent=[];versions=[];matches=[]
 for s in imports:
  providers=exports.get(s['base'],[])
  if not providers:absent.append(s['name'])
  elif s['version'] and not any(p['version']==s['version'] for p in providers):versions.append({'import':s['name'],'providers':providers})
  else:matches.append({'import':s['name'],'providers':providers})
 reports.append({'key':key,'engine':str(engine),'engine_sha256':elf(engine)['sha256'],'needed':elf(engine)['needed'],'strong_imports':len(imports),'missing_symbols':absent,'version_not_exact':[{'import':v['import'],'provider_versions':sorted({str(q['version']) for q in v['providers']})} for v in versions],'matched_imports':[m['import'] for m in matches],'missing_needed':missing,'closure_nodes':len(seen),'closure_paths':sorted(seen)})
a.out.mkdir(parents=True,exist_ok=True)
(a.out/'engines.json').write_text(json.dumps(reports,indent=2)+'\n')
(a.out/'elf-inputs.json').write_text(json.dumps([{k:v for k,v in r.items() if k!='symbols'} for r in cache.values()],indent=2)+'\n')
summary=[{k:r[k] for k in ['key','engine_sha256','needed','strong_imports','missing_symbols','closure_nodes']}|{'version_not_exact_count':len(r['version_not_exact']),'missing_needed_names':sorted({x['needed'] for x in r['missing_needed']})} for r in reports]
(a.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
