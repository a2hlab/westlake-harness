#!/usr/bin/env python3
import argparse,subprocess,json,hashlib,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--source-repo',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
steps=[]
def source_pins():
 return [{'path':str(q.relative_to(HERE)),'sha256':hashlib.sha256(q.read_bytes()).hexdigest()} for q in sorted(HERE.rglob('*')) if q.is_file() and '.private' not in q.parts and q.suffix in ('.c','.h','.py')]
before=source_pins()
(a.out/'sources-before.json').write_text(json.dumps(before,indent=2)+'\n')
def run(name,cmd):
 (a.out/(name+'.argv.json')).write_text(json.dumps(cmd)+'\n')
 with (a.out/(name+'.stdout')).open('wb') as o,(a.out/(name+'.stderr')).open('wb') as e:r=subprocess.run(cmd,stdout=o,stderr=e)
 (a.out/(name+'.rc')).write_text(str(r.returncode)+'\n');steps.append({'name':name,'rc':r.returncode});print(name,r.returncode,flush=True)
 if r.returncode:raise SystemExit(r.returncode)
run('00-frozen',['python3',str(a.source_repo/'scripts/lab/check_frozen.py')])
cc=shutil.which('clang');assert cc
run('01-compiler',[cc,'--version'])
base=[cc,'-std=c11','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-pthread','-I'+str(HERE),'-I'+str(HERE/'derived')]
run('10-core-build',base+[str(HERE/'test_yv12.c'),'-o',str(a.out/'test_yv12')])
run('11-core-test',[str(a.out/'test_yv12')])
if (HERE/'test_route.c').exists():
 run('20-route-build',base+[str(HERE/'test_route.c'),str(HERE/'derived/window_module.c'),str(HERE/'derived/provider_adapter.c'),str(HERE/'derived/entry.c'),'-o',str(a.out/'test_route')])
 for name in ['valid','wrong_caller','wrong_lock','wrong_unlock','wrong_geometry','rgb','unknown','geometry_failure','unmap_failure','flush_failure','alloc_failure','format_refuse','precheck_failure','abort_failure','owner_release_failure']:
  run('21-route-'+name,[str(a.out/'test_route'),name])
assert before==source_pins(), 'source changed during real build/test'
files=[q for q in HERE.rglob('*') if q.is_file() and '.private' not in q.parts and q.suffix in ('.c','.h','.py')]
(a.out/'receipt.json').write_text(json.dumps({'status':'HOST_ONLY','steps':steps,'binaries':[{'name':n,'sha256':hashlib.sha256((a.out/n).read_bytes()).hexdigest()} for n in ['test_yv12','test_route'] if (a.out/n).exists()],'compiler_sha256':hashlib.sha256(Path(cc).resolve().read_bytes()).hexdigest(),'sources':[{'path':str(q.relative_to(HERE)),'sha256':hashlib.sha256(q.read_bytes()).hexdigest()} for q in files]},indent=2)+'\n')
