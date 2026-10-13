"""Offline request assembly from root window3 r4 exact sources. No transport."""
import argparse,json
from pathlib import Path
import candidate_identity as c

def prepare(out):
 c.need(not out.exists(),'fresh request directory required');out.mkdir(parents=True)
 window=c.MAIN/'benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/candidate-window3'
 plan_path=window/'plan.json';plan=c.read(plan_path);freeze_path=c.R4/'freeze.json'
 c.need(c.sha(plan_path)=='8ee3a7e4ea6bb68a7482b3aafb635920bc1e1716a01cc2161b4acfc05a2a18b1','root r4 actual plan pin')
 rows=[];protected={}
 def add(target,path):rows.append({'target':target,'sha256':c.sha(path),'source':c.pin(path)})
 for row in plan['members']:
  target=row['target'];source=c.expand(row['source'].replace('$PACKAGE',str(window/'package')))
  c.need(c.sha(source)==row['sha256'],'root frozen member drift')
  add(target,source)
 for row in plan['binds']:
  if row['target'] in c.CHANGES:continue
  source=next(r['source'] for r in rows if r['target']==row['source']);add(row['target'],c.pinned(source))
 final=c.MAIN/'benchmark/2026-10-12-v1-seal-execution/seal-final-20261013/source-files.json';sources=c.read(final)
 for target in ['/system/etc/westlake-u13-recover-v3.sh','/data/westlake-demo/u13/selinux-mode','/data/westlake-demo/u13/u13-recover-table.json','/data/westlake-demo/u13/u13-recover-table.tsv']:
  source=c.expand(sources[target]['path']);add(target,source);protected[target]=c.sha(source)
 current=c.expand(plan['members'][-1]['before']['source']);protected[c.CFG]=c.sha(current)
 p=out/'protected.json';p.write_text(json.dumps(protected,indent=2)+'\n')
 request={'serial':plan['serial'],'baseline':c.pin(c.BASE),'placement_plan':c.pin(plan_path),'r4_freeze':c.pin(freeze_path),'current_cfg':c.pin(current),'protected_files':c.pin(p),'additional_files':rows,'absent_files':[{'target':c.ROUTEB,'exists':False,'evidence':c.pin(plan_path)}],'baseline_smoke':c.pin(c.MAIN/'benchmark/2026-10-03-u13-stage-b/61b/smoke-61b.json'),'status':'OFFLINE_EXPECTED_CANDIDATE_NOT_LIVE_EVIDENCE','source_note':'Original U13 controls use pinned final source bytes as expected identity; live hook must read all paths. No historical 128 pass is copied.'}
 (out/'request.json').write_text(json.dumps(request,indent=2)+'\n');return out/'request.json'
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();print(prepare(a.out))
