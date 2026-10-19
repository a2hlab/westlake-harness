#!/usr/bin/env python3
"""Host-only static object + test executable. No shared output or deployment ABI."""
import argparse, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
STATUS='OFFLINE_MODULE_ONLY_NOT_DEPLOYABLE'
SOURCES=['window_module.c','window_module.h','test_window.c','build_host.py']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--source-repo',required=True);p.add_argument('--cc',default=os.environ.get('CC','clang'));p.add_argument('--group',choices=['all','pair','failures','concurrency'],default='all');a=p.parse_args()
 out=Path(a.out).expanduser().resolve();repo=Path(a.source_repo).expanduser().resolve()
 if str(out).startswith(('/tmp/','/private/tmp/')):raise SystemExit('persistent OUT required')
 out.mkdir(parents=True,exist_ok=False);raw=out/'raw';raw.mkdir();cc=Path(shutil.which(a.cc) or a.cc).resolve()
 receipt={'status':STATUS,'device_calls':0,'shared_library':False,'production_binding':False,'sources':{n:sha(HERE/n) for n in SOURCES},'tools':{'cc':{'path':str(cc),'sha256':sha(cc)}},'commands':[],'groups':{},'artifacts':{}}
 def save():(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 def run(name,argv,timeout=60):
  (raw/(name+'.command.json')).write_text(json.dumps(argv,indent=2)+'\n')
  start=time.time()
  with (raw/(name+'.stdout.txt')).open('wb') as so,(raw/(name+'.stderr')).open('wb') as se:
   try:r=subprocess.run(argv,stdout=so,stderr=se,timeout=timeout);rc=r.returncode
   except subprocess.TimeoutExpired:rc=124
  (raw/(name+'.rc')).write_text(str(rc)+'\n')
  receipt['commands'].append({'name':name,'rc':rc,'elapsed_seconds':time.time()-start,'raw':{str(x.relative_to(out)):sha(x) for x in sorted(raw.glob(name+'.*'))}});save()
  if rc:raise SystemExit(name+' failed rc='+str(rc))
 run('00-frozen',[sys.executable,str(repo/'scripts/lab/check_frozen.py'),'--git',str(repo),'--registry',str(repo/'knowledge/frozen/frozen.json')])
 run('01-compiler',[str(cc),'--version'])
 run('02-search',[str(cc),'-print-search-dirs'])
 run('03-include-deps',[str(cc),'-std=c11','-M',str(HERE/'window_module.c'),str(HERE/'test_window.c')])
 # Record the actual system headers consumed, including compiler resource headers.
 text=(raw/'03-include-deps.stdout.txt').read_text().replace('\\\n',' ')
 import shlex
 deps=[]
 for line in text.splitlines():
  for s in shlex.split(line.split(':',1)[-1]):
   f=Path(s)
   if f.is_file():deps.append({'path':str(f.resolve()),'sha256':sha(f)})
 receipt['header_dependencies']=list({x['path']:x for x in deps}.values());save()
 flags=['-std=c11','-Wall','-Wextra','-Werror','-pedantic','-O1','-g','-pthread']
 run('04-link-plan',[str(cc),*flags,'-###',str(HERE/'test_window.c'),str(HERE/'window_module.c'),'-o',str(out/'test_window')])
 for line in (raw/'04-link-plan.stderr').read_text().splitlines():
  if line.lstrip().startswith('"'):
   words=shlex.split(line)
   if words and Path(words[0]).is_file():receipt['tools'][Path(words[0]).name]={'path':str(Path(words[0]).resolve()),'sha256':sha(words[0])}
 save()
 run('10-module',[str(cc),*flags,'-c',str(HERE/'window_module.c'),'-o',str(out/'window_module.o')])
 run('11-test',[str(cc),*flags,str(HERE/'test_window.c'),str(out/'window_module.o'),'-o',str(out/'test_window')])
 for group in (['pair','failures','concurrency'] if a.group=='all' else [a.group]):
  run('20-'+group,[str(out/'test_window'),group],timeout=30)
  journal=[json.loads(x) for x in (raw/('20-'+group+'.stdout.txt')).read_text().splitlines()]
  assert journal and all(x['status']=='PASS' for x in journal)
  receipt['groups'][group]={'cases':len(journal),'status':'PASS','journal_sha256':sha(raw/('20-'+group+'.stdout.txt'))};save()
 receipt['artifacts']={n:{'sha256':sha(out/n),'bytes':(out/n).stat().st_size,'role':'host-only-not-deployable'} for n in ['window_module.o','test_window']};receipt['complete']=True;save()
 print(json.dumps({'status':STATUS,'groups':receipt['groups'],'receipt_sha256':sha(out/'receipt.json')}))
if __name__=='__main__':main()
