#!/usr/bin/env python3
"""One isolated Java-only reproduction, pinned image and strict original JAR SHA gates."""
import argparse, hashlib, json, os, subprocess, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
IMAGE='sha256:f39400369f20f4ba610693834f148581376d05c2f321e6194d5bd2934fece4c1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--reference-repo',type=Path,default=REPO);a=p.parse_args()
 inputs=a.inputs.resolve();out=a.out.resolve();ref=a.reference_repo.resolve()
 # Only local worktree outputs. Container sees source read-only and this new output rw.
 out.relative_to(REPO);inputs.relative_to(REPO);assert not out.exists(),'existing output'
 assert (ref/'scripts/lab/check_frozen.py').is_file(),'missing original frozen gate'
 out.mkdir(parents=True);rows=[];docker=os.environ.get('DOCKER','docker')
 for name in ('j1','j7b'):
  stdout=out/(name+'.stdout.txt');stderr=out/(name+'.stderr.txt')
  args=[docker,'run','--rm','--platform','linux/amd64','--network','none','-e','PYTHONDONTWRITEBYTECODE=1','-e','FZ_REPOSITORY=/reference','-v',str(REPO)+':/repo:ro','-v',str(out)+':/run-output:rw','-v',str(ref)+':/reference:ro',IMAGE,'python3','/repo/'+str((HERE/name/'build.py').relative_to(REPO)),'--inputs','/repo/'+str(inputs.relative_to(REPO)),'--out','/run-output/'+name,'--run']
  start=time.time()
  with stdout.open('wb') as o,stderr.open('wb') as e:q=subprocess.run(args,stdout=o,stderr=e)
  logical=[x.replace(str(REPO),'${REPO}').replace(str(out),'${OUT}').replace(str(ref),'${REFERENCE_REPO}') for x in args]
  rows.append({'label':name,'argv':logical,'strict_wrapper_rc':q.returncode,'stdout':stdout.name,'stdout_sha256':sha(stdout),'stderr':stderr.name,'stderr_sha256':sha(stderr),'elapsed_seconds':round(time.time()-start,3)})
  (out/'run.json').write_text(json.dumps({'image':IMAGE,'device_calls':0,'executions':rows},indent=2)+'\n')
 print(json.dumps(rows,indent=2))
 return max(r['strict_wrapper_rc'] for r in rows)
if __name__=='__main__':raise SystemExit(main())
