#!/usr/bin/env python3
"""G30 exact N4 baseline only. Never writes the historical tree or builds a candidate."""
import argparse,hashlib,json,os,platform,subprocess
from pathlib import Path
D=Path(__file__).resolve().parent
EXPECTED='d20530661a30b8af7bbfb30a6b7138d0b6a6bb5d82e6cb8d733a41ae23886c65'
PINS={'toolchain/bin/clang-15':'b107ce0366299ba5ace7095c19dfed65004415c09c57597fdf5c2b7c79ff3913','toolchain/bin/ld.lld':'8583bdc812436711a586fc4eae23cbf744606a31377fa3b28b04b639e1f403b4','sysroot/lib/aarch64-linux-ohos/libc.so':'ab5ad48a82295e6ec144aaac730bfa053e744e4903c01d51707ce0935385d905'}
SOURCES={'native_abi.c':'6cf69a57a5318058aea1d2ce69f3b3a2355aa11231d5261a85435508443c3335','bionic_stdio_compat.c':'e5cfec3dd99abb4b5b47141568ed045e4afb7f254560876d709c61ecf98c447b','native_abi.map':'362acdc8b9f469a1069f05f204e450a8d1aa8608c948edf23a3dd350a5618b72'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--workspaces',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();W=a.workspaces.resolve();O=a.out.resolve();O.mkdir(parents=True,exist_ok=False)
 R=W/'westlake-harness-bms-deploy';F=R/'bms/src/.work/b68-generation/.work/product-tls-generation/frozen';T=F/'toolchain';S=F/'sysroot';src=D/'sources/baseline';old=R/'benchmark/2026-09-30-n4-native/src';env=dict(os.environ,LD_LIBRARY_PATH=str(T/'runtime'))
 receipt={'status':'INCOMPLETE','recipe_sha256':sha(__file__),'expected':EXPECTED,'commands':[],'inputs':{},'platform':platform.platform()};dump(O/'receipt.json',receipt)
 def run(name,argv):
  dump(O/(name+'.argv.json'),{'argv':argv,'cwd':str(D),'LD_LIBRARY_PATH':env['LD_LIBRARY_PATH']})
  with (O/(name+'.stdout')).open('wb') as so,(O/(name+'.stderr')).open('wb') as se:r=subprocess.run(argv,cwd=D,env=env,stdout=so,stderr=se)
  (O/(name+'.rc')).write_text(str(r.returncode)+'\n');receipt['commands'].append({'name':name,'rc':r.returncode});dump(O/'receipt.json',receipt)
  if r.returncode:raise RuntimeError(name+' rc='+str(r.returncode))
 try:
  assert platform.system()=='Linux','original compiler requires Linux'
  for rel,h in PINS.items():assert sha(F/rel)==h,rel;receipt['inputs'][str(F/rel)]=h
  for n,h in SOURCES.items():assert sha(src/n)==h,n;receipt['inputs'][str(src/n)]=h
  cc=str(T/'bin/clang-15');run('compiler',[cc,'--version'])
  common=['--target=aarch64-linux-ohos','--sysroot='+str(S),'-B'+str(T/'bin'),'-isystem',str(S/'include/aarch64-linux-ohos'),'-fPIC','-O2','-g','-ffunction-sections','-fdata-sections','-D__OHOS__','-D_GNU_SOURCE','-I'+str(R/'benchmark/2026-09-30-n3-native/flutter/include'),'-fdebug-compilation-dir='+str(R),'-ffile-prefix-map='+str(src)+'='+str(old),'-fdebug-prefix-map='+str(src)+'='+str(old)]
  for n,obj,extra in [('native_abi.c','native_abi.o',[]),('bionic_stdio_compat.c','stdio.o',['-fno-builtin'])]:
   run('compile-'+obj,[cc]+common+['-std=c11']+extra+['-c',str(src/n),'-o',str(O/obj),'-MD','-MF',str(O/(obj+'.d'))])
  run('link',[cc,'--target=aarch64-linux-ohos','--sysroot='+str(S),'-B'+str(T/'bin'),'-B'+str(S/'lib/aarch64-linux-ohos'),'-fuse-ld=lld','-shared','-Wl,-z,defs,-z,now,-z,relro,--no-undefined,--fatal-warnings,--gc-sections,--build-id=sha1,--hash-style=both','-L'+str(S/'lib/aarch64-linux-ohos'),'-L'+str(O),'-Wl,-z,global,-soname,libwestlake_native_abi.so','-Wl,--version-script='+str(src/'native_abi.map'),str(O/'native_abi.o'),str(O/'stdio.o'),'-lc','-lpthread','-o',str(O/'libwestlake_native_abi.so'),'-Wl,--trace'])
  art=O/'libwestlake_native_abi.so';receipt['artifact']={'sha256':sha(art),'bytes':art.stat().st_size};receipt['objects']={n:sha(O/n) for n in ['native_abi.o','stdio.o']}
  assert sha(art)==EXPECTED,'BASELINE_MISMATCH '+sha(art)
  receipt['status']='BASELINE_EXACT'
 except Exception as e:receipt['error']=str(e);raise
 finally:dump(O/'receipt.json',receipt)
if __name__=='__main__':main()
