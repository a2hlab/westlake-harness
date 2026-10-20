#!/usr/bin/env python3
"""Compile-only OH AArch64 ET_REL evidence. No link, no shared object, no device."""
import argparse,hashlib,json,shlex,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__)
for n in ['source-repo','sdk','t25-build','out']:p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
def sha(x):return hashlib.sha256(Path(x).read_bytes()).hexdigest()
inputs={};steps=[]
def pin(x):
 x=Path(x).resolve();inputs[str(x)]={'sha256':sha(x),'bytes':x.stat().st_size}
def run(n,argv):
 argv=list(map(str,argv));(a.out/(n+'.argv.json')).write_text(json.dumps(argv)+'\n')
 with (a.out/(n+'.stdout')).open('wb') as o,(a.out/(n+'.stderr')).open('wb') as e:r=subprocess.run(argv,stdout=o,stderr=e,timeout=90)
 (a.out/(n+'.rc')).write_text(str(r.returncode)+'\n');steps.append({'name':n,'rc':r.returncode});print(n,r.returncode,flush=True)
 if r.returncode:raise RuntimeError(n)
 return (a.out/(n+'.stdout')).read_text()
rec={'status':'INCOMPLETE','scope':'OH_ET_REL_ONLY','inputs':inputs,'steps':steps,'outputs':{}}
try:
 run('00-frozen',['python3',a.source_repo/'scripts/lab/check_frozen.py','--git',a.source_repo,'--registry',a.source_repo/'knowledge/frozen/frozen.json'])
 cc=a.sdk/'llvm/bin/clang';rd=a.sdk/'llvm/bin/llvm-readelf';old=json.loads((a.t25_build/'receipt.json').read_text())
 for tool in [cc,rd]:pin(tool);assert any(v['sha256']==sha(tool) for v in old['inputs'].values()),'tool not in accepted T25 input pins'
 flags=['--target=aarch64-linux-ohos','--sysroot='+str(a.sdk/'sysroot'),'-std=c11','-fPIC','-fvisibility=hidden','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-DR20_INTERNAL','-DR15_OH_SDK','-I'+str(P),'-I'+str(P/'derived')]
 for idx,name in enumerate(['yv12.c','derived/window_module.c','derived/provider_adapter.c','derived/entry.c','derived/pair.c','derived/geometry.c']):
  src=P/name;pin(src);obj=a.out/(src.stem+'.o')
  text=run(f'{idx+1:02}-deps',[cc,*flags,'-M','-MT',obj.name,src]).replace('\\\n',' ')
  for d in shlex.split(text.split(': ',1)[1]):pin(d)
  run(f'{idx+1:02}-compile',[cc,*flags,'-c',src,'-o',obj]);elf=run(f'{idx+1:02}-elf',[rd,'-h',obj]);assert 'AArch64' in elf and 'REL (Relocatable file)' in elf and 'ELF64' in elf
  rec['outputs'][obj.name]={'sha256':sha(obj),'bytes':obj.stat().st_size}
 for path,row in inputs.items():assert sha(path)==row['sha256'],'input changed'
 rec['status']='OH_COMPILE_ONLY_NOT_DEPLOYABLE'
finally:(a.out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
