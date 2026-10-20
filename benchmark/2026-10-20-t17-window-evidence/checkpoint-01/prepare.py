#!/usr/bin/env python3
"""Local T17 checkpoint only. No archive or device calls while the window is open."""
import argparse,hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true');a=ap.parse_args()
 if not a.write:print('Read-only default; --write creates the candidate checkpoint.');return
 base=Path.home()/'.local/share/westlake/toutiao-resume-20261020';w=base/'t17-5cd-window-01';main=ROOT.parent/'westlake-harness';out=HERE/'packet';out.mkdir(exist_ok=False);refs=[]
 def clean(s):
  for x,y in [(str(base),'BASE20'),(str(main),'$WORKSPACES/westlake-harness'),(str(Path.home()),'$HOME')]:s=s.replace(x,y)
  return s
 def dump(n,x):
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(clean(json.dumps(x,indent=2))+'\n')
 def cp(p,n):
  q=out/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(clean(p.read_text()));refs.append(dict(raw_path='BASE20/'+str(p.relative_to(base)),raw_sha256=sha(p),raw_bytes=p.stat().st_size,public_path=n,public_sha256=sha(q),byte_exact=p.read_bytes()==q.read_bytes()))
 apply=json.loads((w/'apply/result.json').read_text());ad=json.loads((w/'admission.json').read_text());ctx=json.loads((w/'context.json').read_text())
 assert (w/'apply-exec.rc').read_text().strip()=='0' and apply['admission_sha256']==sha(w/'admission.json')
 assert apply['executor_sha256']==ad['executor_sha256']=='07e8e501fbf71e70883722fe3f03d47dac665f8cf13c144e8c1f00926195f549'
 assert apply['after_sha']=='11d3d671bd501205a98ee386e64bf1274501d0458a4cdb35945f7424a388244a'
 for n in ['context.json','admission.json','apply/result.json','apply/plan.json','apply-exec.argv.json','apply-exec.rc','apply-exec.stdout','apply-exec.stderr','candidate-boot.json','candidate-retry-boot.json','first-child-log.rc','first-child-log.stderr']:
  cp(w/n,'receipts/'+n.replace('/','--')+('.txt' if n.endswith('.stderr') else ''))
 first=w/'first-child-log.stdout';assert first.stat().st_size==335890 and (w/'first-child-log.rc').read_text().strip()=='0'
 present=w/'shell-1792458249905787000.stdout';missing=w/'shell-1792458283494808000.stdout'
 line=[x for x in present.read_text().splitlines() if '7754' in x and 'com.ss.android.article.news' in x];assert len(line)==1
 absent=[x for x in missing.read_text().splitlines() if '/proc/7754/stat' in x and 'No such file or directory' in x];assert len(absent)==1
 (out/'first-child-excerpt.txt').write_text('Prior complete ps row:\n'+line[0]+'\nLater stat read:\n'+absent[0]+'\n')
 dump('first-child.json',dict(boot=json.loads((w/'candidate-boot.json').read_text())['boot'],pid=7754,birth='UNKNOWN_IN_THIS_CHECKPOINT',observation='Present in ps, later proc stat absent. Outer reports natural exit; signal/cause not inferred here.',evidence=[{'path':'BASE20/'+str(x.relative_to(base)),'sha256':sha(x),'bytes':x.stat().st_size} for x in [present,missing,first,w/'first-child-log.argv.json']],log_rc=0,log_public=False))
 source=[]
 for rel in ['benchmark/2026-10-20-t17-network-reuse/executor.py','benchmark/2026-10-20-t17-network-reuse/parameters.json']:
  p=main/rel;commit=subprocess.check_output(['git','-C',str(main),'log','-1','--format=%H','--',rel],text=True).strip();blob=subprocess.check_output(['git','-C',str(main),'show',commit+':'+rel]);assert blob==p.read_bytes();source.append(dict(path=rel,commit=commit,sha256=sha(p)))
 assert source[0]['sha256']==apply['executor_sha256'] and source[1]['sha256']==ad['parameters_sha256']
 helpers=[]
 for p in sorted(base.glob('t17*.py')):helpers.append(dict(path='BASE20/'+p.name,sha256=sha(p),bytes=p.stat().st_size));cp(p,'execution-source/'+p.name)
 dump('source-pins.json',dict(sources=source,helpers=helpers,build='No build by evidence lane; R9-derived 5cd run and reused binary identities from actual T17 apply receipt. No T16 outcome transferred.'))
 dump('archive-plan.json',dict(base='BASE20',directories=['t17-5cd-window-01'],files=[Path(x['path']).name for x in helpers],direct_input_dependency='BASE20/t16-r8-candidate-inputs: only the exact files consumed by this apply argv, not old T16 observations/results.',status='WAIT_FOR_FINAL_CLOSE_NO_ARCHIVE_CREATED',required_final_evidence=['original apply-plan rollback receipt','fresh baseline identities','snapshot/supplement comparisons using this window before','actual final screenshot and visual verdict','power/parameter state','close and unlock receipts'],policy='Preserve all attempts and failures; no media URLs or raw app stderr in public packet.'))
 dump('results.json',dict(token='t17-window-evidence',status='NOT_CLOSED',holder=ctx['holder'],window_start=ctx['start'],apply_rc=0,executor_sha256=apply['executor_sha256'],run_after_sha256=apply['after_sha'],first_candidate_boot=json.loads((w/'candidate-boot.json').read_text())['boot'],first_candidate_child=7754,first_child_log_bytes=first.stat().st_size,second_candidate_boot=json.loads((w/'candidate-retry-boot.json').read_text())['boot'],second_candidate_observation='PENDING',binding='UNKNOWN_NOT_REVIEWED',video='NOT_PROVEN',audio='UNKNOWN',restoration='PENDING',unlock='PENDING',archive='NOT_CREATED',device_calls_by_lane=0))
 dump('public-source-index.json',refs)
 print(json.dumps(dict(status='NOT_CLOSED_CHECKPOINT_PREPARED',source_pins=len(source),helpers=len(helpers),device_calls=0)))
if __name__=='__main__':main()
