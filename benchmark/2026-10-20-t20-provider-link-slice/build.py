#!/usr/bin/env python3
"""Reproducible host checks + real OH PIC DSO. No device loading or symbol resolver."""
import argparse,hashlib,json,os,shlex,shutil,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(v,s):
 if not v:raise RuntimeError(s)
def main():
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--repo',type=Path,default=HERE.parents[1]);p.add_argument('--sdk',type=Path,default=Path('/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native'));p.add_argument('--out',type=Path);a=p.parse_args()
 if not a.execute:print(json.dumps({'device_calls':0,'execute':False,'production_route':False}));return
 need(a.out and a.out.is_absolute() and not str(a.out).startswith(('/tmp/','/private/tmp/')),'persistent new out');a.out.mkdir(parents=True,exist_ok=False);raw=a.out/'raw';raw.mkdir();repo=a.repo.resolve();sdk=a.sdk.resolve()
 r14=repo/'benchmark/2026-10-19-toutiao-video-playback/candidate-r14-offline';r15=repo/'benchmark/2026-10-19-toutiao-video-playback/candidate-r15-provider-offline'
 rec={'status':'LINK_SLICE_NOT_DEPLOYABLE','complete':False,'device_calls':0,'commands':[],'inputs':{},'artifacts':{}}
 def save():(a.out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
 def pin(f):f=Path(f).resolve();rec['inputs'][str(f)]={'sha256':sha(f),'bytes':f.stat().st_size}
 def run(name,argv):
  (raw/(name+'.argv.json')).write_text(json.dumps(list(map(str,argv)),indent=2)+'\n')
  with (raw/(name+'.stdout')).open('wb') as so,(raw/(name+'.stderr')).open('wb') as se:
   try:rc=subprocess.run(list(map(str,argv)),stdout=so,stderr=se,timeout=90).returncode
   except subprocess.TimeoutExpired:rc=124
   except OSError as e:se.write(str(e).encode());rc=127
  (raw/(name+'.rc')).write_text(str(rc)+'\n');rec['commands'].append({'name':name,'rc':rc});save();need(rc==0,name+' failed');return (raw/(name+'.stdout')).read_text()
 try:
  for rel,digest in json.loads((HERE/'source-pins.json').read_text()).items():need(sha(repo/rel)==digest,'source drift '+rel);pin(repo/rel)
  for n in ['entry.c','entry.h','exports.map','test_entry.c','source-pins.json','build.py']:pin(HERE/n)
  run('00-frozen',[sys.executable,repo/'scripts/lab/check_frozen.py','--git',repo,'--registry',repo/'knowledge/frozen/frozen.json'])
  cc=sdk/'llvm/bin/clang';rd=sdk/'llvm/bin/llvm-readelf';ld=sdk/'llvm/bin/ld.lld'
  for tool,digest in [(cc,'6a5ec84488cd11db8118fab8160affc40b90885f82481dbc31624f561f7b72a1'),(rd,'2e8ccf494ea3ef05f10f54b3299a69253815f99f8aac8d54d32f3445725b35da')]:need(sha(tool)==digest,'SDK drift');pin(tool)
  pin(ld);host=Path(shutil.which('clang')).resolve();pin(host)
  common=['-std=c11','-Wall','-Wextra','-Werror','-pedantic','-O2','-pthread','-I'+str(r15)]
  tus=[r14/'window_module.c',r15/'provider_adapter.c',HERE/'entry.c']
  hostcmd=[host,*common,tus[0],tus[1],HERE/'test_entry.c','-o',a.out/'test_entry'];run('01-host-build',hostcmd);run('02-host-run',[a.out/'test_entry'])
  flags=['--target=aarch64-linux-ohos','--sysroot='+str(sdk/'sysroot'),'-DR15_OH_SDK','-fPIC','-fvisibility=hidden',*common]
  for i,tu in enumerate(tus):
   text=run('10-deps-'+str(i),[cc,*flags,'-M','-MT','object',tu]).replace('\\\n',' ')
   for path in shlex.split(text.split(': ',1)[1]):pin(path)
  objs=[]
  for i,tu in enumerate(tus):
   obj=a.out/(tu.stem+'.o');run('20-compile-'+str(i),[cc,*flags,'-c',tu,'-o',obj]);objs.append(obj)
  output=a.out/'libwestlake_r20_window.so'
  link=[cc,'--target=aarch64-linux-ohos','--sysroot='+str(sdk/'sysroot'),'-fuse-ld=lld','-shared','-Wl,-z,defs','-Wl,--version-script='+str(HERE/'exports.map'),'-Wl,-soname,libwestlake_r20_window.so',*objs,'-o',output]
  run('30-link-plan',[*link,'-###']);plan=(raw/'30-link-plan.stderr').read_text();commands=[shlex.split(x) for x in plan.splitlines() if x.lstrip().startswith('"')];need(len(commands)==1,'one linker command');args=commands[0]
  dirs=[Path(x[2:]) for x in args if x.startswith('-L')]
  for x in args:
   f=Path(x)
   if f.is_absolute() and f.is_file():pin(f)
   if x.startswith('-l'):
    names=[x[3:]] if x.startswith('-l:') else ['lib'+x[2:]+ext for ext in ['.so','.a']];found=next((d/n for d in dirs for n in names if (d/n).is_file()),None);need(found,'library input '+x);pin(found)
  save();run('31-link',link);text=run('32-readelf',[rd,'-h','-d','--dyn-syms',output]);need('DYN (Shared object file)' in text and 'AArch64' in text,'actual OH DSO')
  defined=[]
  for line in text.splitlines():
   f=line.split()
   if len(f)>=8 and f[0].endswith(':') and f[4] in ('GLOBAL','WEAK') and f[6]!='UND' and f[3]=='FUNC':defined.append(f[7].split('@')[0])
  need(set(defined)=={'r20_create','r20_destroy','r20_lock','r20_unlock','r20_report'},'export surface');need('TEXTREL' not in text,'text relocations')
  rec['exports']=sorted(defined);rec['needed']=[x.strip() for x in text.splitlines() if '(NEEDED)' in x]
  for path,x in rec['inputs'].items():need(sha(path)==x['sha256'],'input drift '+path)
  for f in [*objs,output,a.out/'test_entry']:rec['artifacts'][f.name]={'sha256':sha(f),'bytes':f.stat().st_size}
  rec['complete']=True;save();print(json.dumps({'status':rec['status'],'artifacts':rec['artifacts'],'exports':rec['exports'],'needed':rec['needed']}))
 except Exception as ex:rec['error']=str(ex);save();raise
if __name__=='__main__':main()
