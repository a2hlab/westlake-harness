#!/usr/bin/env python3
"""Linux-only isolated N3 ANL replay. Baseline equality gates candidate build."""
import argparse,hashlib,json,os,subprocess,platform
from pathlib import Path
D=Path(__file__).resolve().parent
EXPECTED='eebd62f2e9107e7915745280d4de85d44e4106a589508d25fa5f867007b2473c'
PINS={'toolchain/bin/clang-15':'b107ce0366299ba5ace7095c19dfed65004415c09c57597fdf5c2b7c79ff3913','toolchain/bin/ld.lld':'8583bdc812436711a586fc4eae23cbf744606a31377fa3b28b04b639e1f403b4','sysroot/lib/aarch64-linux-ohos/libc.so':'ab5ad48a82295e6ec144aaac730bfa053e744e4903c01d51707ce0935385d905'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def run(out,name,argv,cwd,env):
 dump(out/(name+'.argv.json'),{'argv':argv,'cwd':str(cwd),'LD_LIBRARY_PATH':env['LD_LIBRARY_PATH']})
 with (out/(name+'.stdout')).open('wb') as o,(out/(name+'.stderr')).open('wb') as e:r=subprocess.run(argv,cwd=cwd,env=env,stdout=o,stderr=e)
 (out/(name+'.rc')).write_text(str(r.returncode)+'\n')
 if r.returncode:raise RuntimeError(name+' rc='+str(r.returncode))
def main():
 p=argparse.ArgumentParser();p.add_argument('--workspaces',type=Path,default=D.parents[3]);p.add_argument('--out',type=Path,required=True);x=p.parse_args();W=x.workspaces.resolve();out=x.out.resolve();out.mkdir(parents=True,exist_ok=False)
 R=W/'westlake-harness-bms-deploy';F=R/'bms/src/.work/b68-generation/.work/product-tls-generation/frozen';T=F/'toolchain';S=F/'sysroot';original=R/'benchmark/2026-09-30-n3-native/flutter';cc=T/'bin/clang-15';env=dict(os.environ,LD_LIBRARY_PATH=str(T/'runtime'))
 result={'status':'INCOMPLETE','recipe_sha256':sha(__file__),'platform':platform.platform(),'pins':{},'builds':[]};dump(out/'receipt.json',result)
 try:
  assert platform.system()=='Linux','requires original Linux compiler'
  for rel,h in PINS.items():actual=sha(F/rel);assert actual==h,(rel,actual);result['pins'][rel]=actual
  for v in ['baseline','candidate']:
   O=out/v;O.mkdir();src=D/'sources'/v/'anl';b={'variant':v,'status':'INCOMPLETE','sources':{str(f.relative_to(src)):sha(f) for f in src.rglob('*') if f.is_file()}};result['builds'].append(b);dump(out/'receipt.json',result)
   common=['--target=aarch64-linux-ohos','--sysroot='+str(S),'-B'+str(T/'bin'),'-isystem',str(S/'include/aarch64-linux-ohos'),'-fPIC','-O2','-g','-ffunction-sections','-fdata-sections','-D__OHOS__','-D_GNU_SOURCE','-I'+str(src/'include')]
   # Metadata-only path mappings preserve original DWARF source/cwd identities.
   common+=['-fdebug-compilation-dir='+str(R),'-ffile-prefix-map='+str(src)+'='+str(original),'-fdebug-prefix-map='+str(src)+'='+str(original)]
   compile=[str(cc)]+common+['-std=c11','-Wall','-Wextra','-Werror','-fvisibility=hidden','-c',str(src/'app_native_loader.c'),'-o',str(O/'anl.o'),'-MD','-MF',str(O/'dependencies.d')]
   run(O,'compile',compile,D,env)
   link=[str(cc),'--target=aarch64-linux-ohos','--sysroot='+str(S),'-B'+str(T/'bin'),'-B'+str(S/'lib/aarch64-linux-ohos'),'-fuse-ld=lld','-shared','-Wl,-z,defs,-z,now,-z,relro,--no-undefined,--fatal-warnings,--gc-sections,--build-id=sha1,--hash-style=both','-L'+str(S/'lib/aarch64-linux-ohos'),'-L'+str(O),'-Wl,-soname,libapp_native_loader.so','-Wl,--version-script='+str(src/'app_native_loader.map'),str(O/'anl.o'),'-lc','-o',str(O/'libapp_native_loader.so'),'-Wl,--trace']
   run(O,'link',link,D,env)
   art=O/'libapp_native_loader.so';b['artifact']={'path':str(art),'sha256':sha(art),'bytes':art.stat().st_size};b['object_sha256']=sha(O/'anl.o')
   if v=='baseline':assert sha(art)==EXPECTED,('BASELINE_MISMATCH',sha(art),EXPECTED)
   b['status']='BASELINE_EXACT' if v=='baseline' else 'CANDIDATE_BUILT_OFFLINE';dump(out/'receipt.json',result)
  result['status']='BASELINE_EXACT_AND_CANDIDATE_BUILT_OFFLINE'
 except Exception as e:result['error']=str(e);raise
 finally:dump(out/'receipt.json',result)
if __name__=='__main__':main()
