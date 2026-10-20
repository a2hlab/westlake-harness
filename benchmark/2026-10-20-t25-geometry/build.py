#!/usr/bin/env python3
"""Exact T23 object relink baseline, then add one geometry TU. Offline only."""
import argparse,hashlib,json,os,re,shlex,subprocess,sys
from pathlib import Path
P=Path(__file__).resolve().parent
EXPECTED='a9abaf09ce020c45dea5a30d1030a8ae7f939a2f4434cd6ff3aec53cfc9726b6'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(v,msg):
 if not v:raise RuntimeError(msg)
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for key in ['repo','sdk','t23-build','consumer','player','out']:ap.add_argument('--'+key,type=Path,required=True)
 ap.add_argument('--path-map',action='append',default=[],metavar='OLD=NEW')
 ap.add_argument('--execute',action='store_true');a=ap.parse_args()
 if not a.execute:print(json.dumps({'execute':False,'device_calls':0,'baseline':EXPECTED,'adds':'one geometry TU only'}));return
 a.out.mkdir(parents=True,exist_ok=False);raw=a.out/'raw';raw.mkdir();rec={'status':'INCOMPLETE','device_calls':0,'inputs':{},'commands':[],'outputs':{}}
 def save():(a.out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
 def pin(p):
  p=Path(p).resolve();require(p.is_file(),'missing input '+str(p));rec['inputs'][str(p)]={'sha256':sha(p),'bytes':p.stat().st_size}
 def run(name,argv,env=None):
  argv=list(map(str,argv));(raw/(name+'.argv.json')).write_text(json.dumps(argv,indent=2)+'\n')
  with (raw/(name+'.stdout')).open('wb') as so,(raw/(name+'.stderr')).open('wb') as se:
   try:rc=subprocess.run(argv,stdout=so,stderr=se,timeout=120,env=env).returncode
   except subprocess.TimeoutExpired:rc=124
   except OSError as exc:se.write(str(exc).encode());rc=127
  (raw/(name+'.rc')).write_text(str(rc)+'\n');rec['commands'].append({'name':name,'rc':rc});save();require(rc==0,name);return (raw/(name+'.stdout')).read_text()
 maps=[x.split('=',1) for x in a.path_map];require(all(len(x)==2 and x[0] for x in maps),'path-map needs OLD=NEW')
 def remap(s):
  for old,new in maps:s=s.replace(old,new)
  return s
 try:
  run('00-frozen',[sys.executable,a.repo/'scripts/lab/check_frozen.py','--git',a.repo,'--registry',a.repo/'knowledge/frozen/frozen.json'])
  oldfile=a.t23_build/'receipt.json';pin(oldfile);old=json.loads(oldfile.read_text())
  require(old['outputs']['candidate.so']['sha256']==EXPECTED and sha(a.t23_build/'candidate.so')==EXPECTED,'not exact T23 production02')
  for name,value in old['inputs'].items():
   p=Path(remap(name));require(p.is_file(),'missing T23 input '+str(p));require(sha(p)==value['sha256'],'T23 input drift '+str(p));pin(p)
  for name,value in old['outputs'].items():
   p=a.t23_build/name;require(sha(p)==value['sha256'],'T23 object drift '+name);pin(p)
  cc=a.sdk/'llvm/bin/clang';rd=a.sdk/'llvm/bin/llvm-readelf';nm=a.sdk/'llvm/bin/llvm-nm'
  for p in [cc,a.sdk/'llvm/bin/ld.lld',rd,nm,a.sdk/'llvm/bin/llvm-cxxfilt',a.repo/'scripts/lab/abi_diff.py',a.repo/'scripts/lab/check_frozen.py',a.repo/'knowledge/frozen/frozen.json',P/'geometry.c',P/'geometry.h',P/'build.py',a.consumer,a.player]:pin(p)
  require(sha(a.consumer)=='a11c9154ca16dd7acf5e3ea99727ae37c25b1b4494a9133816bc58c553c128e2','wrong exact HWUI consumer')
  params=a.repo/'benchmark/2026-10-20-t23-shim-deployment/parameters.json';pin(params)
  params_data=json.loads(params.read_text());player_rows=[r for r in params_data['artifacts'] if r.get('path')=='lib/arm64-v8a/libttmplayer.so'];require(len(player_rows)==1,'unique player record');player_row=player_rows[0];require(sha(a.player)==player_row['after_sha256'],'player SHA not exact T23 player')
  reloc=run('01-exact-player-relocations',[rd,'-r','--wide',a.player])
  for off,name in [('472490','ANativeWindow_lock'),('472760','ANativeWindow_unlockAndPost'),('472048','ANativeWindow_setBuffersGeometry')]:
   require(any(line.split() and int(line.split()[0],16)==int(off,16) and name in line.split() for line in reloc.splitlines() if re.match(r'^[0-9a-fA-F]+\s',line)), 'missing exact player relocation '+name)
  cmd=a.t23_build/'raw/30-candidate-link.argv.json';pin(cmd);link=[remap(v) for v in json.loads(cmd.read_text())];link[0]=str(cc);link[-1]=str(a.out/'baseline.so')
  for v in link:
   q=Path(v.split('=',1)[1] if v.startswith('-Wl,--version-script=') else v)
   if q.is_file():pin(q)
  run('02-baseline-link',link);require(sha(a.out/'baseline.so')==EXPECTED,'baseline byte reproduction failed')
  flags=['--target=aarch64-linux-ohos','--sysroot='+str(a.sdk/'sysroot'),'-fPIC','-fvisibility=hidden','-O2','-Wall','-Wextra','-Werror']
  deps=run('10-geometry-dependencies',[cc,*flags,'-M','-MT','geometry.o',P/'geometry.c']).replace('\\\n',' ')
  for d in shlex.split(deps.split(': ',1)[1]):pin(d)
  snapshot=a.out/'source-snapshot';snapshot.mkdir()
  for name in ['geometry.c','geometry.h','build.py']:(snapshot/name).write_bytes((P/name).read_bytes())
  save();run('20-compile-geometry',[cc,*flags,'-c',P/'geometry.c','-o',a.out/'geometry.o'])
  candidate=link.copy();idx=candidate.index('-Wl,--as-needed');candidate[idx:idx]=[str(a.out/'geometry.o')];candidate[-1]=str(a.out/'candidate.so');run('30-candidate-link',candidate)
  before=run('40-baseline-elf',[rd,'-h','-d','--dyn-syms','--wide',a.out/'baseline.so']);after=run('41-candidate-elf',[rd,'-h','-d','--dyn-syms','--wide',a.out/'candidate.so'])
  def defs(s):
   result=set()
   for line in s.splitlines():
    f=line.split()
    if len(f)>=8 and f[0].endswith(':') and f[4] in ('GLOBAL','WEAK') and f[6]!='UND':result.add((f[3],f[4],f[5],f[7]))
   return result
  olddefs,newdefs=defs(before),defs(after);require(len(olddefs)==77,'expected 77 old exports');require(olddefs<=newdefs,'old exports changed')
  require(newdefs-olddefs=={('FUNC','GLOBAL','DEFAULT','ANativeWindow_setBuffersGeometry@@LIBC')},'unexpected added exports')
  needed=lambda s:[x.strip() for x in s.splitlines() if '(NEEDED)' in x]
  require(needed(before)==needed(after),'DT_NEEDED changed');require('TEXTREL' not in after,'TEXTREL')
  env=os.environ.copy();env['PATH']=str(a.sdk/'llvm/bin')+os.pathsep+env.get('PATH','')
  run('42-abi-consumer',[sys.executable,a.repo/'scripts/lab/abi_diff.py','--old',a.out/'baseline.so','--new',a.out/'candidate.so','--consumer',a.consumer,'--consumer',a.player,'--json',a.out/'abi.json'],env)
  rec['abi']={'old_exports':len(olddefs),'new_exports':len(newdefs),'added':[list(x) for x in sorted(newdefs-olddefs)],'needed_unchanged':True,'textrel':False,'actual_runtime_geometry':'UNKNOWN','mixed765':'REJECTED_BY_PLAYER_GOT_GATE','raw_oh':'UNSUPPORTED'}
  for path,value in rec['inputs'].items():require(sha(path)==value['sha256'],'input mutated during build '+path)
  for name in ['baseline.so','geometry.o','candidate.so','abi.json']:rec['outputs'][name]={'sha256':sha(a.out/name),'bytes':(a.out/name).stat().st_size}
  rec['status']='OFFLINE_CANDIDATE_NOT_DEPLOYMENT_AUTHORIZED';save();print(json.dumps(rec['outputs']))
 except Exception as exc:rec['error']=str(exc);save();raise
if __name__=='__main__':main()
