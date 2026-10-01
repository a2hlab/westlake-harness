"""Run the master sweep primitive unchanged; record a failed parent-count guard."""
import importlib.util,json,sys,time
from pathlib import Path
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parents[1]/'scripts/lab'))
import lab_paths
p=lab_paths.harness()/'scripts/lab/sweep_bind_deploy.py'
spec=importlib.util.spec_from_file_location('master_sweep_n11d',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
original=m.parent_up
def observed(hdc,serial):
 value=original(hdc,serial)
 if value!='1':
  out=Path(sys.argv[sys.argv.index('--out')+1]);out.mkdir(parents=True,exist_ok=True)
  proof={'epoch':time.time(),'value':value,'raw_ps':m.sh(hdc,serial,'ps -ef'),'count_command':'ps -ef | grep appspawn-x | grep -v grep | grep -c root','primitive_sha256':__import__('hashlib').sha256(p.read_bytes()).hexdigest()}
  (out/'parent-count-failure.json').write_text(json.dumps(proof,indent=2)+'\n')
 return value
m.parent_up=observed
raise SystemExit(m.main())
