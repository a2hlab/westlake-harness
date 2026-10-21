#!/usr/bin/env python3
"""Replay four pinned U13 policy commands in a fresh private directory only."""
import argparse, datetime, json, os, subprocess
from pathlib import Path
from prepare_inputs import HERE, REPO, WS, AUTHOR, REL, BASELINE, sha, save, expand, alias

def run(directory, tag, argv, cwd, allowed=(0,)):
 log=directory/'commands'/tag;log.mkdir(parents=True,exist_ok=False)
 argv=list(map(str,argv));save(log/'argv.json',{'argv':argv,'cwd':str(cwd),'started':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 with (log/'stdout').open('wb',buffering=0) as stdout, (log/'stderr').open('wb',buffering=0) as stderr:
  proc=subprocess.Popen(argv,cwd=cwd,stdout=stdout,stderr=stderr)
  rc=proc.wait()
 record={'tag':tag,'rc':rc,'ended':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv_sha256':sha(log/'argv.json'),'stdout_sha256':sha(log/'stdout'),'stderr_sha256':sha(log/'stderr'),'raw':str(log)}
 save(log/'result.json',record);print(tag,'rc',rc,flush=True)
 if rc not in allowed:raise RuntimeError(f'{tag}: rc={rc}; original logs: {log}')
 return record

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run',default='build-01');args=ap.parse_args();assert Path(args.run).name==args.run
 runroot=HERE/'.private'/args.run;runroot.mkdir(parents=True,exist_ok=False)
 receipt=json.loads((HERE/'upstream/policy-build-receipt.json').read_text());pins=json.loads((HERE/'source-pins.json').read_text())
 for group in ['upstream','files']:
  for name,h in pins[group].items():assert sha(HERE/name)==h,name
 for p,h in receipt['toolchain'].items():assert sha(expand(p))==h,p
 for p,h in receipt['reused_inputs'].items():assert sha(expand(p))==h,p
 records=[];artifacts={};summary={'status':'BUILDING','records':records,'artifacts':artifacts,'run':str(runroot)}
 try:
  records.append(run(runroot,'frozen',[ 'python3',WS/'westlake-harness/scripts/lab/check_frozen.py','--git',WS/'westlake-harness'],runroot))
  recipes=[r['command'] for r in receipt['commands'] if 'policy-candidate1-' in r['raw_path']];assert len(recipes)==4
  oldsrc=AUTHOR/REL/'sources/candidate/policy';oldout=AUTHOR/REL/'.artifacts/policy/candidate1'
  for variant in ['baseline','candidate']:
   source=HERE/'sources'/variant;output=runroot/variant;(output/'candidate').mkdir(parents=True)
   records.append(run(runroot,variant+'-policy',['python3',source/'tests/verify_bridge_policy.py'],runroot))
   for i,recipe in enumerate(recipes):
    argv=[expand(v).replace(str(oldout),str(output)).replace(str(oldsrc),str(source)) for v in recipe]
    if '-c' in argv:argv+=['-fdebug-compilation-dir='+str(AUTHOR)]
    records.append(run(runroot,f'{variant}-{i}',argv,runroot))
   elf=output/'libnativeloader-candidate.so';artifacts[variant]={'path':str(elf),'sha256':sha(elf),'bytes':elf.stat().st_size,'objects':{p.name:sha(p) for p in sorted((output/'candidate').glob('*.o'))}}
   save(runroot/'receipt.json',summary)
   if variant=='baseline':assert sha(elf)==BASELINE,f'baseline complete SHA mismatch: {sha(elf)} expected {BASELINE}'
  summary['status']='BASELINE_IDENTICAL_CANDIDATE_BUILT'
 finally:
  save(runroot/'receipt.json',summary)
  public=json.loads(json.dumps(summary).replace(str(HERE),'$G18').replace(str(WS),'$WORKSPACES').replace(str(Path.home()),'$HOME'))
  save(HERE/(args.run+'-receipt.json'),public)
 print(json.dumps(public['artifacts'],indent=2))
if __name__=='__main__':main()
