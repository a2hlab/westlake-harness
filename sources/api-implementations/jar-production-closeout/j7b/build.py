#!/usr/bin/env python3
"""Verify the complete pinned JAR overlay source set, optionally execute its original producer."""
import argparse,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--inputs',type=Path);ap.add_argument('--out',type=Path);ap.add_argument('--run',action='store_true');a=ap.parse_args()
 lock=json.loads((HERE/'sources.lock.json').read_text())
 assert sha(HERE/'producer.py')==lock['producer_sha256'],'producer drift'
 for row in lock['sources']:assert sha(HERE/row['path'])==row['sha256'],row['path']
 summary={'source_files_verified':len(lock['sources']),'producer_sha256':lock['producer_sha256'],'device_calls':0}
 if a.inputs:
  a.inputs=a.inputs.resolve()
  assert {p.name for p in a.inputs.glob('*.jar')}==set(lock['dependency_inputs']),'unexpected/missing input JAR'
  for name,h in lock['dependency_inputs'].items():assert sha(a.inputs/name)==h,name
  summary['dependency_files_verified']=len(lock['dependency_inputs'])
 if not a.run:print(json.dumps(summary,indent=2));return
 assert a.inputs is not None and a.out is not None,'--run needs --inputs and --out'
 out=a.out.resolve();assert not out.exists(),'refuse existing output'
 out.mkdir(parents=True)
 shutil.copytree(HERE/'source-tree',out/'source-tree');shutil.copytree(HERE/'report-sources',out/'report')
 shutil.copytree(a.inputs,out/'inputs')
 env=os.environ.copy();env.update(FZ_SOURCE_ROOT=str(out/'source-tree'),FZ_REPORT_ROOT=str(out/'report'),FZ_BUILD_ROOT=str(out),FZ_REPOSITORY=os.environ.get('FZ_REPOSITORY',str(REPO)))
 argv=[sys.executable,str(HERE/'producer.py'),lock['label'],lock['baseline']]
 with (out/'producer.stdout.txt').open('wb') as stdout,(out/'producer.stderr.txt').open('wb') as stderr:
  q=subprocess.run(argv,env=env,stdout=stdout,stderr=stderr)
 result=summary|{'argv':argv,'producer_rc':q.returncode,'historical_output_sha256':lock['historical_output_sha256'],'historical_logs_recovered':False,'new_execution':True}
 artifact=out/('build-'+lock['label'])/'oh-adapter-runtime.jar'
 if artifact.exists():result.update(output_sha256=sha(artifact),output_matches_historical=sha(artifact)==lock['historical_output_sha256'])
 (out/'execution.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 raise SystemExit(q.returncode or (0 if result.get('output_matches_historical') else 2))
if __name__=='__main__':main()
