#!/usr/bin/env python3
import argparse,hashlib,json,subprocess,shutil
from pathlib import Path
P=Path(__file__).resolve().parent
CASES=['valid','wrong_caller','wrong_lock','wrong_unlock','wrong_geometry','rgb','unknown','geometry_failure','unmap_failure','flush_failure','alloc_failure','format_refuse','precheck_failure','abort_failure','owner_release_failure','rgbx','rgbx_format0','rgbx_geometry_failure','rgbx_bad_format','rgbx_precheck','rgbx_unmap','rgbx_flush']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--observer',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);steps=[]
def run(n,c):
 c=list(map(str,c));(a.out/(n+'.argv.json')).write_text(json.dumps(c)+'\n')
 with (a.out/(n+'.stdout')).open('wb') as o,(a.out/(n+'.stderr')).open('wb') as e:r=subprocess.run(c,stdout=o,stderr=e)
 (a.out/(n+'.rc')).write_text(str(r.returncode)+'\n');steps.append(dict(name=n,rc=r.returncode));print(n,r.returncode,flush=True)
 if r.returncode:raise SystemExit(r.returncode)
inputs={str(f):sha(f) for f in P.rglob('*') if f.is_file() and '.private' not in f.parts and f.suffix in ('.c','.h','.py')}
for n,h in [('observer.c','0a31347c0c8499d5109b9ef73c84b1dab42ea78fac58c7ece08a884dc0814521'),('observer.h','d60cf01a30a600348451de6b9b25a86ab5a1a2ff651fa1bddfe04ef6d1cf516b')]:assert sha(a.observer/n)==h;inputs[str(a.observer/n)]=h
run('00-frozen',['python3',a.repo/'scripts/lab/check_frozen.py','--git',a.repo,'--registry',a.repo/'knowledge/frozen/frozen.json'])
base=[shutil.which('clang'),'-std=c11','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-pthread','-D_GNU_SOURCE=1','-I'+str(P),'-I'+str(P/'derived'),'-I'+str(a.observer)]
run('10-core-build',base+[P/'test_rgbx.c',P/'rgbx.c','-o',a.out/'test_rgbx']);run('11-core-test',[a.out/'test_rgbx'])
run('20-route-build',base+['-DWL_T27_OBSERVER',P/'test_route.c',P/'derived/window_module.c',P/'derived/provider_adapter.c',P/'derived/entry.c',P/'rgbx.c',P/'observation.c',a.observer/'observer.c','-o',a.out/'test_route'])
for case in CASES:run('21-'+case,[a.out/'test_route',case])
for f,h in inputs.items():assert sha(Path(f))==h
(a.out/'receipt.json').write_text(json.dumps(dict(status='HOST_ONLY_PASS',inputs=inputs,commands=steps,route_cases=CASES),indent=2)+'\n')
