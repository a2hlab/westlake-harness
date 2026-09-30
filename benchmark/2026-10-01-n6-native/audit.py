#!/usr/bin/env python3
import hashlib,json,subprocess
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];P=R.parent/'westlake-generation-n6-b70b3d00'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def symbols(p):
 s=subprocess.check_output(['llvm-readelf','--dyn-syms','--wide',str(p)],text=True)
 result={}
 for line in s.splitlines():
  fields=line.split()
  if len(fields)<8 or not fields[0].rstrip(':').isdigit():continue
  name=fields[7];result[name]=(fields[4],fields[6])
 return result
new=P/'payload/android/lib64/westlake_flutter/libwestlake_native_abi.so'
old=R.parent/'westlake-generation-n5-6d001bb8/payload/android/lib64/westlake_flutter/libwestlake_native_abi.so'
a,b=symbols(new),symbols(old)
exports=lambda x:{n:v for n,v in x.items() if v[1]!='UND'}
assert all(n in exports(a) for n in exports(b))
added=sorted(exports(a).keys()-exports(b).keys())
assert {n.split('@')[0] for n in added}=={'eglCreateWindowSurface','eglDestroySurface','eglSwapBuffers','eglSwapBuffersWithDamageKHR'}
new_imports=sorted(n for n,v in a.items() if v[1]=='UND' and v[0]=='GLOBAL' and n not in b)
checks=json.loads((P/'native-checks/native-gates.json').read_text());targets=['/system/lib64/chipset-sdk-sp/libc++.so','/system/lib64/libc.so']
rows={s['target']:s for s in checks['namespaces']['system_files']}
# libc can be /system/lib/ld-musl-aarch64.so.1 rather than a separate file.
libc=P/'native-checks'/rows[targets[1]]['path']
cpp=P/'native-checks'/rows[targets[0]]['path']
providers={str(p.relative_to(R.parent)):symbols(p) for p in [libc,cpp]}
resolved={n:[p for p,s in providers.items() if any(k.split('@')[0]==n.split('@')[0] and v[1]!='UND' for k,v in s.items())] for n in new_imports}
assert all(resolved.values()),resolved
out=dict(candidate_sha256=sha(new),preserved_exports=len(exports(b)),added_exports=added,new_strong_imports=resolved,provider_hashes={str(p.relative_to(R.parent)):sha(p) for p in [libc,cpp]},runtime_binding='UNVERIFIED until engine calls the copied wrapper; static exports alone do not prove binding')
(H/'symbol-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
