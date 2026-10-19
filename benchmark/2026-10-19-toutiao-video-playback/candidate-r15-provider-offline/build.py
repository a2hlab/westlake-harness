#!/usr/bin/env python3
"""Build host oracle or OH compile-only adapter. No shared library or resolver."""
import argparse, hashlib, json, os, shlex, shutil, struct, subprocess, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'scripts/lab/check_frozen.py').is_file())
STATUS='OFFLINE_ADAPTER_ONLY_NOT_DEPLOYABLE'
R14=HERE.parent/'candidate-r14-offline'
R14_PINS={'window_module.c':'1f42a3936449b75db6c08163c21cf68882d664065705c2d2f9afd7e2c1af4707','window_module.h':'28a88796febf5063e374fbc3d1d007a53f1004eafb24f46d6f925783724cbe32'}
OH_PINS={'clang':'6a5ec84488cd11db8118fab8160affc40b90885f82481dbc31624f561f7b72a1','llvm-readelf':'2e8ccf494ea3ef05f10f54b3299a69253815f99f8aac8d54d32f3445725b35da'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(v,s):
 if not v:raise RuntimeError(s)
def deps(text):
 out={}
 for line in text.replace('\\\n',' ').splitlines():
  if ': ' not in line:continue
  for name in shlex.split(line.split(': ',1)[1]):
   p=Path(name).resolve();need(p.is_file(),'dependency missing '+str(p));out[str(p)]=sha(p)
 need(out,'empty dependency set');return out

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--mode',choices=['host','oh'],required=True);p.add_argument('--group',choices=['all','pair','layout','failures','concurrency'],default='all');p.add_argument('--source-repo',default=str(ROOT));p.add_argument('--cc',default=os.environ.get('CC','clang'));p.add_argument('--sdk',default=os.environ.get('OH_SDK_NATIVE','/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native'));a=p.parse_args()
 out=Path(a.out).expanduser().resolve();need(not str(out).startswith(('/tmp/','/private/tmp/')),'persistent OUT required');out.mkdir(parents=True,exist_ok=False);raw=out/'raw';raw.mkdir()
 sources=[HERE/'provider_adapter.c',HERE/'provider_adapter.h',HERE/'test_adapter.c',Path(__file__),R14/'window_module.c',R14/'window_module.h']
 rec={'schema':'r15-build-v1','status':STATUS,'complete':False,'mode':a.mode,'device_calls':0,'shared_library':False,'production_binding':False,'sources':{str(x.resolve()):sha(x) for x in sources},'r14_pins':R14_PINS,'tools':{},'commands':[],'groups':{},'artifacts':{}}
 def save():(out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
 def run(name,argv):
  (raw/(name+'.command.json')).write_text(json.dumps(argv,indent=2)+'\n');start=time.time()
  with (raw/(name+'.stdout.txt')).open('wb') as so,(raw/(name+'.stderr')).open('wb') as se:
   try:rc=subprocess.run(argv,stdout=so,stderr=se,timeout=90).returncode
   except subprocess.TimeoutExpired:rc=124
   except OSError as exc:se.write((str(exc)+'\n').encode());rc=127
  (raw/(name+'.rc')).write_text(str(rc)+'\n');rec['commands'].append({'name':name,'rc':rc,'elapsed_seconds':time.time()-start,'raw':{str(x.relative_to(out)):{'sha256':sha(x),'bytes':x.stat().st_size} for x in sorted(raw.glob(name+'.*'))}});save();need(rc==0,name+' failed rc='+str(rc));return (raw/(name+'.stdout.txt')).read_text()
 try:
  for n,h in R14_PINS.items():need(sha(R14/n)==h,'R14 source drift')
  repo=Path(a.source_repo).resolve();run('00-frozen',[sys.executable,str(repo/'scripts/lab/check_frozen.py'),'--git',str(repo),'--registry',str(repo/'knowledge/frozen/frozen.json')])
  flags=['-std=c11','-Wall','-Wextra','-Werror','-pedantic','-O1','-pthread']
  if a.mode=='oh':
   sdk=Path(a.sdk).expanduser().resolve();cc=sdk/'llvm/bin/clang';readelf=sdk/'llvm/bin/llvm-readelf'
   for n,h in OH_PINS.items():need(sha(sdk/'llvm/bin'/n)==h,'OH tool drift '+n)
   flags=['--target=aarch64-linux-ohos','--sysroot='+str(sdk/'sysroot'),'-DR15_OH_SDK',*flags]
   tus=[HERE/'provider_adapter.c'];rec['tools']['readelf']={'path':str(readelf),'sha256':sha(readelf)}
  else:
   cc=Path(shutil.which(a.cc) or a.cc).resolve();tus=[R14/'window_module.c',HERE/'provider_adapter.c',HERE/'test_adapter.c']
  rec['tools']['cc']={'path':str(cc),'sha256':sha(cc)};run('01-compiler',[str(cc),'--version']);run('02-resource',[str(cc),'-print-resource-dir'])
  before={}
  for i,s in enumerate(tus):before.update(deps(run('03-deps-'+str(i),[str(cc),*flags,'-M','-MT','object',str(s)])))
  rec['dependencies_before']=before;save();objs=[]
  for i,s in enumerate(tus):
   obj=out/(s.stem+'.o');run('10-object-'+str(i),[str(cc),*flags,'-c',str(s),'-o',str(obj)]);objs.append(obj)
  if a.mode=='host':
   binary=out/'test_adapter';run('19-link-plan',[str(cc),*flags,'-###',*[str(x) for x in objs],'-o',str(binary)])
   for line in (raw/'19-link-plan.stderr').read_text().splitlines():
    if line.lstrip().startswith('"'):
     words=shlex.split(line)
     if words and Path(words[0]).is_file():rec['tools'][Path(words[0]).name]={'path':str(Path(words[0]).resolve()),'sha256':sha(words[0])}
   run('20-link',[str(cc),*flags,*[str(x) for x in objs],'-o',str(binary)]);objs.append(binary)
   for group in ['pair','layout','failures','concurrency'] if a.group=='all' else [a.group]:
    lines=run('30-'+group,[str(binary),group]);items=[json.loads(x) for x in lines.splitlines()];need(items and all(x['status']=='PASS' for x in items),'invalid oracle result');rec['groups'][group]={'cases':len(items),'status':'PASS','journal_sha256':sha(raw/('30-'+group+'.stdout.txt'))}
  else:
   run('20-readelf',[str(readelf),'--file-header','--sections','--symbols','--relocs',str(objs[0])]);data=objs[0].read_bytes();need(data[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<HH',data,16)==(1,183),'not AArch64 ET_REL');need(struct.unpack_from('<H',data,56)[0]==0,'unexpected program headers');rec['elf']={'class':'ELF64','machine':'AArch64','type':'ET_REL','program_headers':0};rec['sdk_signature_layout_assertions']='PASS_COMPILE_ONLY'
  need(all(sha(x)==h for x,h in before.items()),'source/header drift during build');need(all(sha(x)==h for x,h in rec['sources'].items()),'source drift during build');need(all(sha(x['path'])==x['sha256'] for x in rec['tools'].values()),'tool drift during build');rec['dependencies_unchanged']=True
  rec['artifacts']={x.name:{'sha256':sha(x),'bytes':x.stat().st_size} for x in objs};rec['complete']=True;save();print(json.dumps({'status':STATUS,'mode':a.mode,'groups':rec['groups'],'artifacts':rec['artifacts']}));return 0
 except Exception as exc:
  rec['error']=str(exc);save();print(str(exc),file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
