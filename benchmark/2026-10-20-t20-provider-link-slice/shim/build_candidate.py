#!/usr/bin/env python3
"""Exact85 baseline relink then original-source plus paired unit. No device calls."""
import argparse,hashlib,importlib.util,json,os,shlex,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;TOP=HERE.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(v,s):
 if not v:raise RuntimeError(s)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');ap.add_argument('--inputs',type=Path,required=True);ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--sdk',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 if not a.execute:print(json.dumps({'execute':False,'device_calls':0,'same_shim_route':True}));return
 w=a.inputs.resolve();repo=a.repo.resolve();sdk=a.sdk.resolve();out=a.out.absolute();need(not str(out).startswith(('/tmp/','/private/tmp/')),'persistent output');out.mkdir(parents=True,exist_ok=False);raw=out/'raw';raw.mkdir()
 rec={'status':'INCOMPLETE','device_calls':0,'commands':[],'inputs':{},'artifacts':{}}
 def save():(out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
 def pin(p):p=Path(p).resolve();rec['inputs'][str(p)]={'sha256':sha(p),'bytes':p.stat().st_size}
 def run(n,args):
  args=list(map(str,args));(raw/(n+'.argv.json')).write_text(json.dumps(args,indent=2)+'\n')
  with (raw/(n+'.stdout')).open('wb') as so,(raw/(n+'.stderr')).open('wb') as se:
   try:rc=subprocess.run(args,stdout=so,stderr=se,timeout=90).returncode
   except subprocess.TimeoutExpired:rc=124
   except OSError as e:se.write(str(e).encode());rc=127
  (raw/(n+'.rc')).write_text(str(rc)+'\n');rec['commands'].append({'name':n,'rc':rc});save();need(rc==0,n+' failed');return (raw/(n+'.stdout')).read_text()
 try:
  run('00-frozen',[sys.executable,repo/'scripts/lab/check_frozen.py','--git',repo,'--registry',repo/'knowledge/frozen/frozen.json'])
  for rel,h in json.loads((TOP/'source-pins.json').read_text()).items():need(sha(repo/rel)==h,'R14/R15 drift');pin(repo/rel)
  for p in [HERE/'original.c',HERE/'original.map',HERE/'derive.py',HERE/'candidate.c',HERE/'pair.c',TOP/'entry.c',TOP/'entry.h',Path(__file__)]:pin(p)
  need(sha(HERE/'original.c')=='45f0b40c168acfd47d1b83d97dc8b11aa55ae300d9e40744859785278411c92f','original source')
  cc=sdk/'llvm/bin/clang';ld=sdk/'llvm/bin/ld.lld';rd=sdk/'llvm/bin/llvm-readelf'
  need(sha(cc)=='6a5ec84488cd11db8118fab8160affc40b90885f82481dbc31624f561f7b72a1','compiler')
  for p in [cc,ld,rd]:pin(p)
  record=w/'out-ability38/webview-gles-order/build.json';pin(record);cmds=json.loads(record.read_text())['commands']
  def mapped(x):
   head,sep,value=x.rpartition('=') if '=' in x else ('','',x)
   for marker in ('/source-closure/verify/','/a2hlab/ws/'):
    if marker in value:return head+sep+str(w)+'/'+value.split(marker,1)[1]
   return x
  link=[mapped(x) for x in cmds[1]];link[0]=str(cc);old=w/'out-npthrefuse49/obj/webview_bionic_shim.c.o';need(sha(old)=='0063481765b0fe96e6c19524cdc35951d48355b168ab81e43938ab4a4fc1660a','original object')
  idx=link.index(str(w/'out-ability38/webview-gles-order/webview_bionic_shim.c.o'));link[idx]=str(old);link[-1]=str(out/'baseline.so')
  for x in link:
   if Path(x).is_file():pin(x)
   if x.startswith('-Wl,--version-script='):pin(x.split('=',1)[1])
  for n in ['libc.so','libdl.a']:pin(w/'toolchains/ohos-sdk/native/sysroot/usr/lib/aarch64-linux-ohos'/n)
  save();run('01-baseline-link',link);need(sha(out/'baseline.so')=='85c789f48b2bc0c31658c9dc591cd27784cc0ddfe559005e8d36d1d7d220476a','exact baseline85')
  src=out/'baseline-src';src.mkdir();(src/'webview_bionic_shim.c').write_bytes((HERE/'original.c').read_bytes())
  oldflags=['--target=aarch64-linux-ohos','--sysroot='+str(w/'toolchains/ohos-sdk/native/sysroot'),'-fPIC','-O2','-Wall','-Wextra','-Werror']
  run('02-original-compile',[cc,*oldflags,'-c',src/'webview_bionic_shim.c','-o',out/'baseline-c.o'])
  compare=repo/'benchmark/2026-10-20-t18-audiotrack-production/build.py';pin(compare);sp=importlib.util.spec_from_file_location('t18_compare',compare);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);left=old.read_bytes();right=(out/'baseline-c.o').read_bytes();sa=m.sections(left);sb=m.sections(right);need(len(sa)==len(sb),'original section count');allowed=set();changes=[]
  for (name,ha,ba),(name2,hb,bb) in zip(sa,sb):
   need(name==name2 and ha==hb,'original section headers')
   if ha[1]==8:continue # SHT_NOBITS occupies no file bytes.
   if ba!=bb:
    need(name=='.comment' and not ha[2]&2,'original code/data drift '+name);allowed.update(range(ha[4],ha[4]+ha[5]));changes.append(name)
  diff={i for i,(x,y) in enumerate(zip(left,right)) if x!=y};need(len(left)==len(right) and diff<=allowed,'bytes outside comment differ')
  rec['original_object_compare']={'old':sha(old),'new':sha(out/'baseline-c.o'),'changed_sections':changes,'changed_bytes':len(diff),'nobits_not_file_bytes':True,'all_other_bytes_equal':True};save()
  r14=repo/'benchmark/2026-10-19-toutiao-video-playback/candidate-r14-offline';r15=repo/'benchmark/2026-10-19-toutiao-video-playback/candidate-r15-provider-offline'
  flags=['--target=aarch64-linux-ohos','--sysroot='+str(sdk/'sysroot'),'-fPIC','-fvisibility=hidden','-DR15_OH_SDK','-DR20_INTERNAL','-O2','-Wall','-Wextra','-Werror','-I'+str(r15),'-I'+str(TOP)]
  jobs=[(HERE/'candidate.c',oldflags,'candidate-c.o'),(r14/'window_module.c',flags,'r14.o'),(r15/'provider_adapter.c',flags,'r15.o'),(TOP/'entry.c',flags,'entry.o'),(HERE/'pair.c',flags,'pair.o')]
  for i,(tu,f,obj) in enumerate(jobs):
   deps=run('10-deps-'+str(i),[cc,*f,'-M','-MT','object',tu]).replace('\\\n',' ')
   for path in shlex.split(deps.split(': ',1)[1]):pin(path)
  save()
  for i,(tu,f,obj) in enumerate(jobs):run('20-compile-'+str(i),[cc,*f,'-c',tu,'-o',out/obj])
  candidate=link.copy();candidate[idx]=str(out/'candidate-c.o');candidate[idx+1:idx+1]=[str(out/n) for n in ['r14.o','r15.o','entry.o','pair.o']];candidate[-1]=str(out/'candidate.so');run('30-candidate-link',candidate)
  def symbols(text):
   rows=[]
   for line in text.splitlines():
    f=line.split()
    if len(f)>=8 and f[0].endswith(':') and f[4] in ('GLOBAL','WEAK'):rows.append((f[3],f[4],f[5],f[6]=='UND',f[7]))
   return sorted(rows)
  before=run('40-baseline-elf',[rd,'-h','-d','--dyn-syms','--wide',out/'baseline.so']);after=run('41-candidate-elf',[rd,'-h','-d','--dyn-syms','--wide',out/'candidate.so']);need('TEXTREL' not in after,'text relocations')
  rec['symbols_before']=symbols(before);rec['symbols_after']=symbols(after)
  defs=lambda text:sorted(x for x in symbols(text) if not x[3]);need(defs(before)==defs(after),'defined export ABI drift')
  rec['new_imports']=sorted(set(symbols(after))-set(symbols(before)));rec['needed_before']=[l.strip() for l in before.splitlines() if '(NEEDED)' in l];rec['needed_after']=[l.strip() for l in after.splitlines() if '(NEEDED)' in l];need(rec['needed_before']==rec['needed_after'],'NEEDED drift')
  for path,x in rec['inputs'].items():need(sha(path)==x['sha256'],'input changed '+path)
  for n in ['baseline.so','baseline-c.o','candidate-c.o','r14.o','r15.o','entry.o','pair.o','candidate.so']:p=out/n;rec['artifacts'][n]={'sha256':sha(p),'bytes':p.stat().st_size}
  rec['status']='PAIRED_SHIM_CANDIDATE_NOT_DEVICE_VALIDATED';save();print(json.dumps({'status':rec['status'],'candidate':rec['artifacts']['candidate.so'],'new_imports':rec['new_imports'],'needed':rec['needed_after']}))
 except Exception as e:rec['error']=str(e);save();raise
if __name__=='__main__':main()
