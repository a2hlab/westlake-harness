"""Compile the exact production pair with explicit host loader/provider seams."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--source-root',type=Path,required=True)
p.add_argument('--candidate-root',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
here=Path(__file__).resolve().parent
c=a.candidate_root/'benchmark/2026-10-20-t20-provider-link-slice'
b=a.source_root/'benchmark/2026-10-19-toutiao-video-playback'
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert sha(c/'shim/pair.c')=='610053541b996e41377aae1270f42eed52610b60e17e5e948c2f297a78aa2155','reviewed pair drift'
sources={'pair.c':c/'shim/pair.c','entry.c':c/'entry.c','entry.h':c/'entry.h','pair_fixture.c':here/'pair_fixture.c','window_module.c':b/'candidate-r14-offline/window_module.c','provider_adapter.c':b/'candidate-r15-provider-offline/provider_adapter.c'}
pins={name:sha(f) for name,f in sources.items()}
for name,f in sources.items():(a.out/name).write_bytes(f.read_bytes())
argv=['cc','-std=c11','-pthread','-I',str(c),'-I',str(c/'shim'),'-I',str(b/'candidate-r15-provider-offline'),str(here/'pair_fixture.c'),str(c/'entry.c'),str(b/'candidate-r14-offline/window_module.c'),str(b/'candidate-r15-provider-offline/provider_adapter.c'),'-o',str(a.out/'pair-test')]
def run(name,argv):
 r=subprocess.run(argv,capture_output=True,timeout=30)
 (a.out/(name+'.argv.json')).write_text(json.dumps(argv,indent=2)+'\n')
 (a.out/(name+'.stdout')).write_bytes(r.stdout);(a.out/(name+'.stderr')).write_bytes(r.stderr);(a.out/(name+'.rc')).write_text(str(r.returncode)+'\n')
 return r
r=run('compile',argv);assert r.returncode==0,r.stderr
cases={}
for name in ['success','failed_retained','mixed_provider','mixed_slots','slot_resolver_drift','unreadable_slot','wrong_owner_offset','nonplayer','foreign_same_basename','player_base_drift']:
 r=run(name,[str(a.out/'pair-test'),name]);cases[name]=r.returncode
 if name in ('nonplayer','foreign_same_basename'):
  assert r.stderr.count(b'CPU rendering path not implemented')==1,'original diagnostic must occur once over two lock calls'
assert all(sha(f)==pins[n] for n,f in sources.items()),'source changed during test'
result={'pins':pins,'cases':cases,'scope':'Real pair bind_once/ELF-GOT gates and R20/R14/R15 lifecycle; loader metadata/OH methods are seams. Owner callable methods become reference counters only after actual bind_once passes. No device claim.'}
(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
assert all(rc==0 for rc in cases.values()),cases
print(json.dumps(result,indent=2))
