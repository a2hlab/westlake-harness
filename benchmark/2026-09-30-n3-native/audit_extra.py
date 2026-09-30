#!/usr/bin/env python3
"""Check audio import supply and libgdx without pretending owner lookup was run."""
import hashlib,json,re,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
REA='/opt/homebrew/opt/llvm/bin/llvm-readelf'
pool=R/'bms/src/.work/b68-generation/platform-pool/system/lib64'
pkg=R.parent/'westlake-generation-n3-candidate'
inputs=Path('/Users/zhaoyue/a2hlab/app-inputs')
def elf(f):
 s=subprocess.check_output([REA,'-d','--dyn-syms',str(f)],text=True)
 imports=set();exports=set()
 for l in s.splitlines():
  v=l.split()
  if len(v)<8 or not re.match(r'^\d+:$',v[0]):continue
  name=v[7].split('@')[0]
  if v[6]=='UND' and v[4]=='GLOBAL':imports.add(name)
  elif v[6]!='UND' and v[4] in ['GLOBAL','WEAK']:exports.add(name)
 return {'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'needed':re.findall(r'\(NEEDED\).*?\[(.*?)\]',s),'imports':sorted(imports),'exports':sorted(exports)}
audio=elf(pool/'libOpenSLES.so');abi=elf(pkg/'payload/android/lib64/westlake_native/libwestlake_native_abi.so')
rows=[]
for key in ['mindustry','ppsspp']:
 files=list((inputs/key/'lib/arm64-v8a').glob('*.so'));seen=set()
 for f in files:
  e=elf(f);imports={s for s in e['imports'] if s.startswith('SL_IID_') or s=='slCreateEngine'}
  if not imports:continue
  assert imports<=set(audio['exports'])|set(abi['exports']),(key,imports-set(audio['exports'])-set(abi['exports']))
  seen|=imports;rows.append({'key':key,'elf':e['path'],'sha256':e['sha256'],'audio_imports':sorted(imports)})
 assert 'slCreateEngine' in seen,(key,'no actual consumer')
# Two libgdx consumers: empty stdc++ is a SONAME alias, never a C++ provider.
providers=[elf(pool/'libc.so'),elf(pkg/'payload/android/lib64/libbionic_compat.so'),elf(pkg/'payload/android/lib64/liblog.so'),abi]
supply=set().union(*(set(x['exports']) for x in providers));gdx=[]
for f in inputs.glob('*/lib/arm64-v8a/libgdx.so'):
 if f.parts[-4] not in ['fd-app','fd-shatteredpixeldungeon']:continue
 e=elf(f);missing=set(e['imports'])-supply
 gdx.append({'path':str(f),'sha256':e['sha256'],'needed':e['needed'],'missing_strong_symbol_names':sorted(missing)})
 assert not missing,(f,missing)
assert len(gdx)>=2,gdx
# Removing the real OH slCreateEngine or the Android extension IID is rejected.
assert 'slCreateEngine' not in set(abi['exports'])
assert 'SL_IID_ANDROIDSIMPLEBUFFERQUEUE' not in set(audio['exports'])
(P/'extra-closure.json').write_text(json.dumps({'audio':audio,'android_extensions':abi['sha256'],'consumers':rows,'gdx':gdx,'missing_audio_or_extension_negative':'rejected','device_owner_reachability':'unverified'},indent=2)+'\n')
print('PASS',len(rows),'OpenSLES consumers;',len(gdx),'libgdx consumers; absent-audio/IID negatives')
