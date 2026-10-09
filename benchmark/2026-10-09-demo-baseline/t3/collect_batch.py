#!/usr/bin/env python3
"""Preserve one completed batch's raw facts and read-only identity evidence.
No board commands; outer loop determines UI verdicts from captures.
"""
import argparse,json,subprocess,hashlib,shutil,os
from pathlib import Path
HERE=Path(__file__).resolve().parent
WS=Path(os.environ.get('WORKSPACES',str(HERE.parents[3])))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('batch');ap.add_argument('--plans',choices=['plans-v1','plans-v2'],default='plans-v1');a=ap.parse_args()
 base=HERE/a.plans/a.batch;runner=base/'runner';result=json.loads((runner/'board-run-result.json').read_text())
 if result.get('before_unlock')!=0:raise SystemExit('REFUSE: batch not safely finalized')
 final=json.loads((base/'runner-after-identity/identity.json').read_text())
 if not final.get('passed') or final.get('diff'):raise SystemExit('REFUSE: final baseline not verified')
 tag=a.batch if a.plans=='plans-v1' else a.plans+'-'+a.batch
 records=sorted(runner.glob('0*/*/*/*/record.json'));view=HERE/(tag+'-facts-view');view.mkdir(exist_ok=False)
 for p in records:(view/p.parent.name).symlink_to(p.parent.resolve(),target_is_directory=True)
 for name in ['runtime-fingerprint.txt','boot-image-fingerprint.txt']:
  paths=[p.parent.parent/name for p in records]
  if paths and all(p.is_file() for p in paths) and len({p.read_bytes() for p in paths})==1:(view/name).write_bytes(paths[0].read_bytes())
 facts=subprocess.check_output(['python3',str(HERE.parents[2]/'scripts/lab/run_facts.py'),str(view)],text=True)
 (HERE/(tag+'-facts.txt')).write_text(facts)
 rows={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in records}
 summary={'records':rows,'runner':str(runner),'result':result,'final_identity':final,'UI_verdict':'outer-review-only'}
 (HERE/(tag+'-results.json')).write_text(json.dumps(summary,indent=2)+'\n')
 print(facts,end='')
if __name__=='__main__':main()
