#!/usr/bin/env python3
"""Offline validator counterexamples. All edits are disposable local fixtures."""
import argparse,hashlib,importlib.util,json,sys,tempfile,shutil
from pathlib import Path
sys.dont_write_bytecode=True
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def run(source,payload,before,out):
 sys.path.insert(0,str(source.resolve()))
 import prepare,deploy
 rows=[]
 with tempfile.TemporaryDirectory(prefix='t38-validator-') as td:
  root=Path(td)
  try:prepare.prepare(payload,before,'be4badc3-5a79-4fa8-8758-e6aacc0ca05f',root/'disabled')
  except ValueError as e:rows.append({'case':'prepare_disabled_review_plan','exception':str(e),'plan_written':(root/'disabled/plan.json').exists()})
  local=root/'synthetic-enabled';shutil.copytree(payload,local)
  env=(local/'startup.env').read_text().replace("STARTUP_ENABLED='0'","STARTUP_ENABLED='1'").replace("STARTUP_APPROVED_BY='DISABLED-PENDING-OUTER'","STARTUP_APPROVED_BY='outer(codex)'")
  (local/'startup.env').write_text(env);(local/'startup.expected.sha256').write_text(sha(local/'startup.env')+'\n')
  folder=root/'synthetic-plan';plan=prepare.prepare(local,before,'be4badc3-5a79-4fa8-8758-e6aacc0ca05f',folder)
  import re
  f=folder/'payload/startup.env';original=f.read_text();mut=re.sub(r"STARTUP_START_PARENT_SHA='[0-9a-f]{64}'","STARTUP_START_PARENT_SHA='"+'0'*64+"'",original);assert mut!=original
  f.write_text(mut);(folder/'payload/startup.expected.sha256').write_text(sha(f)+'\n')
  for row in plan['files']:
   if row['name'] in ('startup.env','startup.expected.sha256'):row['sha256']=sha(folder/'payload'/row['name'])
  try:deploy.validate(plan,folder);outcome='accepted'
  except ValueError as e:outcome='refused:'+str(e)
  rows.append({'case':'wrong_bounded_start_leaf','validate_result':outcome})
 report={'source_sha256':sha(source/'deploy.py'),'prepare_sha256':sha(source/'prepare.py'),'cases':rows,'device_calls':0,'synthetic_authority_not_deployable':True}
 out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--payload',type=Path,required=True);ap.add_argument('--before',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();run(a.source,a.payload,a.before,a.out)
