import json,sys
from pathlib import Path
repo=Path(__file__).resolve().parents[3];sys.path.insert(0,str(repo/'scripts/lab'));import u7_executor as u
out=Path(__file__).resolve().parent
io=u.DeviceIO('61b0657200000000000000000324012c','cx-t0',out/'baseline-read3')
p=json.loads((out.parent/'vm-dry-run.json').read_text());got,absent=io.snapshot(sorted(p['baseline']));mounts=io.mounts()
s={'plan':p,'before_mounts':mounts,'serial':io.serial,'boot_id':io.boot}
(out/'baseline-replay-readiness.json').write_text(json.dumps(s,indent=2))
rows,sources=u.baseline_replay_plan(s);source_actual,_=io.snapshot(sorted(sources))
result={'boot_id':io.boot,'expected':len(p['baseline']),'identity_match':got==p['baseline'],'mismatch':{k:[v,got.get(k)] for k,v in p['baseline'].items() if got.get(k)!=v},'replay_source_match':source_actual==sources,'replay_rows':rows,'fingerprints':u.fingerprints(got,p['reference_paths']),'processes':io.ps()}
(out/'baseline.json').write_text(json.dumps(result,indent=2));print({k:result[k] for k in ['boot_id','expected','identity_match','mismatch','replay_source_match','fingerprints']})
