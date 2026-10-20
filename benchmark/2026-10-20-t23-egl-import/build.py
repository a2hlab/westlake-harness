#!/usr/bin/env python3
"""Relink exact T20 objects unchanged, then add two EGL translation units. No device."""
import argparse,hashlib,json,shlex,subprocess,sys
from pathlib import Path
P=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
a=argparse.ArgumentParser();a.add_argument('--repo',type=Path,required=True);a.add_argument('--sdk',type=Path,required=True);a.add_argument('--inputs',type=Path,required=True);a.add_argument('--t20-build',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--execute',action='store_true');x=a.parse_args()
if not x.execute:print(json.dumps({'execute':False,'device_calls':0,'adds':'EGL trio and native fence only'}));sys.exit()
x.out.mkdir(parents=True,exist_ok=False);raw=x.out/'raw';raw.mkdir();r={'status':'INCOMPLETE','device_calls':0,'commands':[],'inputs':{},'outputs':{}}
def save():(x.out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
def need(v,m):
 if not v:raise RuntimeError(m)
def pin(p):p=Path(p).resolve();r['inputs'][str(p)]={'sha256':sha(p),'bytes':p.stat().st_size}
def run(n,args):
 args=list(map(str,args));(raw/(n+'.argv.json')).write_text(json.dumps(args,indent=2)+'\n')
 with (raw/(n+'.stdout')).open('wb') as so,(raw/(n+'.stderr')).open('wb') as se:
  try:rc=subprocess.run(args,stdout=so,stderr=se,timeout=90).returncode
  except subprocess.TimeoutExpired:rc=124
  except OSError as e:se.write(str(e).encode());rc=127
 (raw/(n+'.rc')).write_text(str(rc)+'\n');r['commands'].append({'name':n,'rc':rc});save();need(rc==0,n);return (raw/(n+'.stdout')).read_text()
try:
 run('00-frozen',[sys.executable,x.repo/'scripts/lab/check_frozen.py','--git',x.repo,'--registry',x.repo/'knowledge/frozen/frozen.json'])
 rec=x.t20_build/'receipt.json';cmd=x.t20_build/'raw/30-candidate-link.argv.json';pin(rec);pin(cmd);old=json.loads(rec.read_text())
 for name,entry in old['artifacts'].items():
  if name.endswith('.o') or name=='candidate.so':need(sha(x.t20_build/name)==entry['sha256'],'T20 artifact drift '+name);pin(x.t20_build/name)
 need(sha(x.t20_build/'candidate.so')=='5cc23582d8cd8f28b24f89dc9bcf439de2177c0be33bb4783dd1baad3ab32eca','exact T20')
 link=json.loads(cmd.read_text());oldrun=Path(link[-1]).parent
 def remap(v):
  if str(oldrun) in v:return v.replace(str(oldrun),str(x.t20_build))
  for marker in ('/source-closure/verify/','/a2hlab/ws/'):
   if marker in v:
    prefix='--sysroot=' if v.startswith('--sysroot=') else '-Wl,--version-script=' if v.startswith('-Wl,--version-script=') else ''
    return prefix+str(x.inputs)+'/'+v.split(marker,1)[1]
  return v
 link=[remap(v) for v in link];cc=x.sdk/'llvm/bin/clang';link[0]=str(cc);link[-1]=str(x.out/'baseline.so')
 for p in [cc,x.sdk/'llvm/bin/ld.lld',x.sdk/'llvm/bin/llvm-readelf',P/'egl_import.c',P/'egl_import.h',P/'exact_binding.h',P/'platform.c',Path(__file__)]:pin(p)
 for v in link:
  q=Path(v.split('=',1)[1] if v.startswith('-Wl,--version-script=') else v)
  if q.is_file():pin(q)
 for n in ['libc.so','libdl.a']:pin(x.inputs/'toolchains/ohos-sdk/native/sysroot/usr/lib/aarch64-linux-ohos'/n)
 run('01-baseline-link',link);need(sha(x.out/'baseline.so')==sha(x.t20_build/'candidate.so'),'baseline must equal T20')
 flags=['--target=aarch64-linux-ohos','--sysroot='+str(x.sdk/'sysroot'),'-fPIC','-fvisibility=hidden','-O2','-Wall','-Wextra','-Werror']
 for n in ['egl_import','platform']:
  deps=run('10-deps-'+n,[cc,*flags,'-M','-MT','object',P/(n+'.c')]).replace('\\\n',' ')
  for path in shlex.split(deps.split(': ',1)[1]):pin(path)
 save()
 for n in ['egl_import','platform']:run('20-compile-'+n,[cc,*flags,'-c',P/(n+'.c'),'-o',x.out/(n+'.o')])
 new=link.copy();idx=new.index('-Wl,--as-needed');new[idx:idx]=[str(x.out/'egl_import.o'),str(x.out/'platform.o')];new[-1]=str(x.out/'candidate.so');run('30-candidate-link',new)
 rd=x.sdk/'llvm/bin/llvm-readelf';before=run('40-baseline-elf',[rd,'-h','-d','--dyn-syms','--wide',x.out/'baseline.so']);after=run('41-candidate-elf',[rd,'-h','-d','--dyn-syms','--wide',x.out/'candidate.so'])
 def defs(s):
  rows=set()
  for l in s.splitlines():
   f=l.split()
   if len(f)>=8 and f[0].endswith(':') and f[4] in ('GLOBAL','WEAK') and f[6]!='UND':rows.add((f[3],f[4],f[5],f[7]))
  return rows
 missing=defs(before)-defs(after);added=defs(after)-defs(before);need(not missing,'removed defined exports');need({t[3].split('@')[0] for t in added}=={'eglGetNativeClientBufferANDROID','eglCreateImageKHR','eglDestroyImageKHR','eglDupNativeFenceFDANDROID'},'unexpected new exports');r['new_exports']=sorted(added)
 needed=lambda s:[l.strip() for l in s.splitlines() if '(NEEDED)' in l];need(needed(before)==needed(after),'NEEDED changed');need('TEXTREL' not in after,'TEXTREL')
 for path,pinvalue in r['inputs'].items():need(sha(path)==pinvalue['sha256'],'input changed during build')
 for n in ['baseline.so','egl_import.o','platform.o','candidate.so']:r['outputs'][n]={'sha256':sha(x.out/n),'bytes':(x.out/n).stat().st_size}
 r['status']='EGL_IMPORT_CANDIDATE_NOT_DEVICE_VALIDATED';save();print(json.dumps(r['outputs']['candidate.so']))
except Exception as e:r['error']=str(e);save();raise
