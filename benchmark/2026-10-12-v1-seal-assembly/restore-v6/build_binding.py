#!/usr/bin/env python3
"""Pin t10+t11 source only; retain all actual5cd placement observations."""
from pathlib import Path
import hashlib,json,os,subprocess
HERE=Path(__file__).resolve().parent
WS=Path(os.environ.get('WORKSPACES',str(HERE.parents[3])))
COMMIT='c6c8f6145ae72da1331e5d461d4959532efeddd7'
REL='benchmark/2026-10-12-snapshot-path/classifier-composition/capture-feed-package'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def ref(p):return {'path':'$WORKSPACES/'+str(p.relative_to(WS)),'sha256':sha(p)}
def write(p,j):
 with p.open('x') as f:json.dump(j,f,indent=2);f.write('\n')
def main():
 t0=WS/'westlake-harness-t0';package=t0/REL
 # The commit tracks the pin record, not the persistent generated package.
 record_path=str(Path(REL).parent/'results.json')
 blob=subprocess.check_output(['git','show',COMMIT+':'+record_path],cwd=t0)
 record=json.loads(blob)
 assert record['execution_enabled'] is False and record['device_calls']==0
 for name,key in [('composition.json','composition_sha256'),('plan.disabled.json','plan_sha256')]:
  assert record[key]==sha(package/name),name
 lineage={'commit':COMMIT,'tracked_path':record_path,'tracked_blob_sha256':hashlib.sha256(blob).hexdigest(),
   'composition_sha256':record['composition_sha256'],'plan_sha256':record['plan_sha256']}
 comp=read(package/'composition.json')
 for row in comp['files']:
  p=package/row['path'];assert p.is_file() and not p.is_symlink() and sha(p)==row['sha256'] and p.stat().st_size==row['bytes']
 old=HERE.parent/'restore-v5/binding.5cd.r3.disabled.json';b=read(old)
 assert b['host_uid']==20011300 and b['startup_enabled'] is False
 b['composition_update']={'composition':ref(package/'composition.json'),'plan':ref(package/'plan.disabled.json'),
   'watchdog_sha256':comp['t10_watchdog_sha256'],'classifier_sha256':comp['classifier_sha256']}
 b['observation_provenance']['t10_t11_composition']={'commit':COMMIT,'source':b['composition_update'],'scope':'watchdog/classifier content delta; no61b before/metadata/startup authority imported'}
 # Relocate only the obsolete producer-worktree evidence reference to its landed,
 # byte-identical main-tree record. No target metadata or evidence SHA changes.
 metadata=WS/'westlake-harness/benchmark/2026-10-12-v1-seal-assembly/restore-v3/stage-donor-observations.json'
 relocations=[]
 for row in b['stage_files']:
  oldref=row['metadata_evidence'];assert sha(metadata)==oldref['sha256']
  row['metadata_evidence']={**oldref,**ref(metadata)}
  relocations.append({'target':row['target'],'old':oldref,'new':row['metadata_evidence']})
 write(HERE/'binding.5cd.composed.disabled.json',b)
 write(HERE/'source-composition-audit.json',{'source_commit':COMMIT,'git_lineage':lineage,'source':b['composition_update'],'v5_binding':ref(old),'metadata_reference_relocations':relocations,'target_before_after_unchanged':True,'device_calls':0})
 print(json.dumps({'status':'BOUND_DISABLED','binding_sha256':sha(HERE/'binding.5cd.composed.disabled.json'),'composition_sha256':sha(package/'composition.json'),'plan_sha256':sha(package/'plan.disabled.json'),'source_commit':COMMIT}))
if __name__=='__main__':main()
