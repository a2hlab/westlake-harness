#!/usr/bin/env python3
import argparse,hashlib,json,subprocess,shutil
from pathlib import Path
P=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--observer',type=Path,required=True);p.add_argument('--source-repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
expected={'observer.c':'0a31347c0c8499d5109b9ef73c84b1dab42ea78fac58c7ece08a884dc0814521','observer.h':'d60cf01a30a600348451de6b9b25a86ab5a1a2ff651fa1bddfe04ef6d1cf516b'}
snapshot=a.out/'observer';snapshot.mkdir();pins={};steps=[]
def sha(x):return hashlib.sha256(Path(x).read_bytes()).hexdigest()
for n,h in expected.items():assert sha(a.observer/n)==h;shutil.copyfile(a.observer/n,snapshot/n);pins[str(a.observer/n)]=h
for q in P.rglob('*'):
 if q.is_file() and '.private' not in q.parts and q.suffix in ('.c','.h','.py'):pins[str(q)]=sha(q)
def run(name,cmd):
 cmd=list(map(str,cmd));(a.out/(name+'.argv.json')).write_text(json.dumps(cmd)+'\n')
 with (a.out/(name+'.stdout')).open('wb') as o,(a.out/(name+'.stderr')).open('wb') as e:r=subprocess.run(cmd,stdout=o,stderr=e)
 (a.out/(name+'.rc')).write_text(str(r.returncode)+'\n');steps.append({'name':name,'rc':r.returncode});print(name,r.returncode,flush=True)
 if r.returncode:raise RuntimeError(name)
run('00-frozen',['python3',a.source_repo/'scripts/lab/check_frozen.py','--git',a.source_repo,'--registry',a.source_repo/'knowledge/frozen/frozen.json'])
cc=shutil.which('clang');base=[cc,'-std=c11','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-pthread','-D_GNU_SOURCE=1','-DWL_T27_OBSERVER','-I'+str(P),'-I'+str(P/'derived'),'-I'+str(snapshot)]
run('10-observation-build',base+[P/'test_observation.c',snapshot/'observer.c','-o',a.out/'test_observation'])
run('11-observation-test',[a.out/'test_observation'])
run('20-joint-route-build',base+[P/'test_route.c',P/'derived/window_module.c',P/'derived/provider_adapter.c',P/'derived/entry.c',P/'observation.c',snapshot/'observer.c','-o',a.out/'test_route'])
for name in ['valid','wrong_caller','wrong_lock','wrong_unlock','wrong_geometry','rgb','unknown','unmap_failure','flush_failure','precheck_failure']:
 run('21-route-'+name,[a.out/'test_route',name])
for q,h in pins.items():assert sha(q)==h,'source changed '+q
(a.out/'receipt.json').write_text(json.dumps({'status':'JOINT_HOST_ONLY','pins':pins,'steps':steps},indent=2)+'\n')
