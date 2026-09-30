import hashlib,json,subprocess
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
P=R.parent/json.loads((H/'package.json').read_text())['package'];U=R.parent/'westlake-generation-n4-order-216b68fb'
def elf(p):
 s=subprocess.check_output(['llvm-readelf','--dyn-syms','--wide',str(p)],text=True);out={}
 for l in s.splitlines():
  f=l.split()
  if len(f)>7 and f[0].rstrip(':').isdigit():out[f[7]]=(f[4],f[6])
 return out
def exports(p):return {n for n,v in elf(p).items() if v[1]!='UND'}
old=exports(U/'payload/route/libbionic_compat.so');new=exports(P/'payload/route/libbionic_compat.so');assert old<=new
assert new-old=={'__gnu_strerror_r@@LIBC','android_dlopen_ext@@LIBC'}
e={n.split('@')[0] for n in exports(P/'payload/android/lib64/westlake_flutter/libEGL.so')}
imports=json.loads((H/'evidence/engine-egl-imports.json').read_text());assert all(set(v)<=e for v in imports.values())
for n in ['eglCreateWindowSurface','eglSwapBuffers','eglSwapBuffersWithDamageKHR']:assert n in exports(U/'payload/android/lib64/libhwui.so')
z=P/'payload/android/lib64/westlake_native/libz.so';zd=subprocess.check_output(['llvm-readelf','-d',str(z)],text=True)
assert 'Shared library: [libshared_libz.z.so]' in zd and 'Library soname: [libz.so]' in zd and z.stat().st_size==1904
assert sha(z)==json.loads((H/'evidence/r109c-libz.json').read_text())['sha256']
m=json.loads((P/'package.json').read_text());u=json.loads((U/'package.json').read_text());delta={k for k in m['files'].keys()|u['files'].keys() if m['files'].get(k)!=u['files'].get(k)}
assert len(delta)==8,delta
for k in m['files']:assert sha(P/k)==m['files'][k],k
out={'bionic_old_exports':len(old),'bionic_removed_exports':[],'bionic_added_exports':sorted(new-old),'engine_egl_imports_covered':{k:len(v) for k,v in imports.items()},'zlib_shell_sha256':sha(z),'changes':{k:m['files'][k] for k in sorted(delta)},'device_binding':'unverified'}
(H/'symbol-audit.json').write_text(json.dumps(out,indent=2)+'\n');print('PASS exports, all six EGL import sets, r109c zlib, all payload hashes, exact 8-file scope')
