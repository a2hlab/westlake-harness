#!/usr/bin/env python3
"""One offline T26+T27 link, preceded by exact T25 baseline reproduction.
No deployment action. T27 must provide its frozen source manifest and glue.
"""
import argparse,hashlib,json,os,re,shlex,subprocess,sys
from pathlib import Path
P=Path(__file__).resolve().parent
BASELINE='2a867f78905bdc37020bec36c951f628c6393456a1770514c1d73f974fd3d5bc'
PLAYER='0b4d95c5f9d96826a95ede998df20be037299eaf6fbfcd1cd2afa39793ba9471'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(v,m):
 if not v:raise RuntimeError(m)
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for key in ['repo','sdk','t25-build','t27','joint-glue','consumer','player','out']:ap.add_argument('--'+key,type=Path,required=True)
 ap.add_argument('--execute',action='store_true');ap.add_argument('--path-map',action='append',default=[])
 a=ap.parse_args()
 if not a.execute:print(json.dumps({'execute':False,'device_calls':0,'status':'WAIT_FROZEN_T27_JOINT_GLUE','baseline':BASELINE}));return
 a.out.mkdir(parents=True,exist_ok=False);raw=a.out/'raw';raw.mkdir();rec={'status':'INCOMPLETE','device_calls':0,'inputs':{},'commands':[],'outputs':{}}
 def save():(a.out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
 def pin(p):
  p=Path(p).resolve();need(p.is_file(),'missing input '+str(p));rec['inputs'][str(p)]={'sha256':sha(p),'bytes':p.stat().st_size};return p
 def run(n,cmd,env=None):
  cmd=list(map(str,cmd));(raw/(n+'.argv.json')).write_text(json.dumps(cmd,indent=2)+'\n')
  with (raw/(n+'.stdout')).open('wb') as so,(raw/(n+'.stderr')).open('wb') as se:
   try:rc=subprocess.run(cmd,stdout=so,stderr=se,timeout=120,env=env).returncode
   except subprocess.TimeoutExpired:rc=124
   except OSError as e:se.write(str(e).encode());rc=127
  (raw/(n+'.rc')).write_text(str(rc)+'\n');rec['commands'].append({'name':n,'rc':rc});save();need(rc==0,n);return (raw/(n+'.stdout')).read_text()
 mappings=[x.split('=',1) for x in a.path_map];need(all(len(x)==2 and x[0] for x in mappings),'path-map OLD=NEW')
 def remap(v):
  for old,new in sorted(mappings,key=lambda x:len(x[0]),reverse=True):v=v.replace(old,new)
  return v
 try:
  run('00-frozen',[sys.executable,a.repo/'scripts/lab/check_frozen.py','--git',a.repo,'--registry',a.repo/'knowledge/frozen/frozen.json'])
  old=json.loads(pin(a.t25_build/'receipt.json').read_text());need(old['status']=='OFFLINE_CANDIDATE_NOT_DEPLOYMENT_AUTHORIZED','T25 incomplete')
  need(sha(a.t25_build/'candidate.so')==BASELINE and old['outputs']['candidate.so']['sha256']==BASELINE,'wrong T25 baseline')
  for path,row in old['inputs'].items():need(sha(pin(remap(path)))==row['sha256'],'T25 input drift '+path)
  for path,row in old['outputs'].items():need(sha(pin(a.t25_build/path))==row['sha256'],'T25 output drift '+path)
  need(sha(pin(a.player))==PLAYER,'exact player mismatch');need(sha(pin(a.consumer))=='a11c9154ca16dd7acf5e3ea99727ae37c25b1b4494a9133816bc58c553c128e2','exact HWUI mismatch')
  cc=pin(a.sdk/'llvm/bin/clang');rd=pin(a.sdk/'llvm/bin/llvm-readelf');pin(a.sdk/'llvm/bin/ld.lld');pin(a.sdk/'llvm/bin/llvm-nm')
  # Joint glue is a small explicit source manifest; no implied use of a mutable
  # T27 directory. Its producer must pin the complete CPU/import wiring.
  joint=json.loads(pin(a.joint_glue).read_text());need(joint['status']=='OFFLINE_JOINT_GLUE_FROZEN','joint glue not frozen')
  need(joint['t26_mali_target']==12 and joint['player_sha256']==PLAYER,'joint semantic identity')
  roots={'T26':P,'T27':a.t27}
  for row in joint['inputs']:
   base=roots[row['root']].resolve();path=(base/row['path']).resolve();need(path.is_relative_to(base),'joint path escape');need(sha(pin(path))==row['sha256'],'joint source drift')
  argvpath=pin(a.t25_build/'raw/30-candidate-link.argv.json');link=[remap(x) for x in json.loads(argvpath.read_text())];link[0]=str(cc);link[-1]=str(a.out/'baseline.so')
  for value in link:
   p=Path(value.split('=',1)[1] if value.startswith('-Wl,--version-script=') else value)
   if p.is_file():pin(p)
  run('01-baseline-link',link);need(sha(a.out/'baseline.so')==BASELINE,'T25 relink not byte identical')
  flags=['--target=aarch64-linux-ohos','--sysroot='+str(a.sdk/'sysroot'),'-std=c11','-fPIC','-fvisibility=hidden','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-D_GNU_SOURCE=1','-DWL_T27_OBSERVER','-DR20_INTERNAL','-DR15_OH_SDK','-I'+str(P),'-I'+str(P/'derived'),'-I'+str(a.t27)]
  replacements={};extra=[];snap=a.out/'source-snapshot';snap.mkdir()
  for idx,unit in enumerate(joint['units']):
   base=roots[unit['root']].resolve();src=(base/unit['path']).resolve();need(src.is_relative_to(base),'unit escape');pin(src)
   obj=a.out/unit['object'];need(obj.parent==a.out and obj.suffix=='.o','object path')
   deps=run(f'10-deps-{idx}',[cc,*flags,'-M','-MT',obj.name,src]).replace('\\\n',' ')
   for d in shlex.split(deps.split(': ',1)[1]):pin(d)
   run(f'20-compile-{idx}',[cc,*flags,'-c',src,'-o',obj]);(snap/(str(idx)+'-'+src.name)).write_bytes(src.read_bytes())
   if unit.get('replaces'):need(unit['replaces'] not in replacements,'duplicate replacement');replacements[unit['replaces']]=str(obj)
   else:extra.append(str(obj))
  need(set(replacements)=={'r14.o','r15.o','entry.o','pair.o','geometry.o','egl_import.o','platform.o'},'exact seven successor objects')
  candidate=[];seen=set()
  for x in link:
   n=Path(x).name
   if n in replacements:need(n not in seen,'ambiguous old object');seen.add(n);candidate.append(replacements[n])
   else:candidate.append(x)
  need(seen==set(replacements),'old object missing');candidate[candidate.index('-Wl,--as-needed'):candidate.index('-Wl,--as-needed')]=extra;candidate[-1]=str(a.out/'candidate.so');run('30-candidate-link',candidate)
  before=run('40-baseline-elf',[rd,'--elf-output-style=GNU','-h','-d','--dyn-syms','--wide',a.out/'baseline.so']);after=run('41-candidate-elf',[rd,'--elf-output-style=GNU','-h','-d','--dyn-syms','--wide',a.out/'candidate.so'])
  def definitions(s):
   return {tuple(f[i] for i in [3,4,5,7]) for line in s.splitlines() if len(f:=line.split())>=8 and f[0].endswith(':') and f[4] in ('GLOBAL','WEAK') and f[6]!='UND'}
  need(len(definitions(before))==78 and definitions(before)==definitions(after),'78 exports/version tuples changed or empty parser')
  needed=lambda s:[x.strip() for x in s.splitlines() if '(NEEDED)' in x]
  need(len(needed(before))>0 and needed(before)==needed(after) and 'TEXTREL' not in after,'dependency/textrel drift or empty parser')
  exports={}
  for name in ['ANativeWindow_lock','ANativeWindow_unlockAndPost','ANativeWindow_setBuffersGeometry']:
   rows=[l.split() for l in after.splitlines() if l.split() and l.split()[-1]==name+'@@LIBC'];need(len(rows)==1,'unique versioned '+name);exports[name]=hex(int(rows[0][1],16))
  rec['export_offsets']=exports;rec['abi']={'exports_equal':True,'needed_equal':True,'runtime':'UNKNOWN'}
  for path,row in rec['inputs'].items():need(sha(path)==row['sha256'],'input changed during build '+path)
  for p in a.out.glob('*.o'):rec['outputs'][p.name]={'sha256':sha(p),'bytes':p.stat().st_size}
  for n in ['baseline.so','candidate.so']:rec['outputs'][n]={'sha256':sha(a.out/n),'bytes':(a.out/n).stat().st_size}
  rec['status']='OFFLINE_CANDIDATE_NOT_DEPLOYMENT_AUTHORIZED';save();print(json.dumps(rec['outputs']))
 except Exception as e:rec['error']=str(e);save();raise
if __name__=='__main__':main()
