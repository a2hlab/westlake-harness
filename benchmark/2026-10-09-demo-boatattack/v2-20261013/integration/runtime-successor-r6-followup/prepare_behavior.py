"""Offline reset-baseline supplement; only a fresh disabled window may be amended."""
import argparse,hashlib,json,os
from pathlib import Path
HERE=Path(__file__).resolve().parent;WS=Path(os.environ['WORKSPACES']).resolve()
OLD_RUNNER='8c8f89e2216816c2d2a4be452b1367560fb311c0a82a35466ba74682affd6aa1'
def need(x,msg):
 if not x:raise ValueError(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def read(p):return json.loads(Path(p).read_text())
def ref(p):return dict(path='$WORKSPACES/'+str(Path(p).resolve().relative_to(WS)),sha256=sha(p))
INSERT='''  # Independent supplement: normalize the starting state; do not relabel original R6 evidence.
  review=Path(os.path.expandvars(plan['reset_baseline_approval']))
  need(review.resolve()==(out/'reset-baseline.approval.json').resolve() and not review.exists(),'fresh exact baseline-review path')
  rec['evidence_group']='reset-baseline-supplement-not-original-cadence'
  rec['target_window']=window('baseline-reset');guard()
  reset_cmd='uinput -T -c 1584 1074 200'
  rc,text=b.shell(reset_cmd,required=False)
  rec['baseline_reset']={'command':reset_cmd,'injection_rc':rc,'response':text,'visual_response':'pending_human'}
  save(out/'record.json',rec);need(rc==0,'baseline reset injection failed')
  guard();shot('reset-baseline');rec['images']['reset-baseline']['target_window']=window('reset-baseline')
  rec['status']='WAITING_FOR_BASELINE_REVIEW';save(out/'record.json',rec)
  wait_until=min(start+plan['max_runtime_seconds'],time.monotonic()+45)
  while not review.exists():
   need(time.monotonic()<wait_until and (authority is None or time.time()<authority['expires_epoch']),'baseline visual review timeout')
   time.sleep(.1)
  approved=json.loads(review.read_text())
  need(approved.get('approved_by')=='outer(codex)' and approved.get('verdict')=='WATER_FACING_COURSE','baseline not visually accepted')
  need(approved.get('boot_id')==plan['boot_id'] and approved.get('child')==identity and approved.get('image_sha256')==sha(out/'reset-baseline.jpeg'),'baseline review identity/image pin')
  rec['baseline_review']=approved;rec['baseline_review_sha256']=sha(review)
  rec['status']='STARTING';save(out/'record.json',rec)
  # No cadence replay or extra sleep. Original five commands follow immediately under unchanged guards.
'''
def build(window):
 need(not (window/'run').exists() and not (window/'board-run').exists(),'never amend running/output window')
 runner=window/'interaction_runner.py';need(sha(runner)==OLD_RUNNER,'exact r6 runner source')
 q=read(window/'request.json');plan=read(window/'interaction.plan.disabled.json')
 need(plan['execution_enabled'] is False and plan['serial']=='5ea34a4500000000000000001123012c' and plan['uid']==20011062,'disabled actual5ea plan')
 source=runner.read_text();needle='  for n,(name,cmd) in enumerate(TOUCHES,1):';need(source.count(needle)==1,'one original five-touch loop')
 output=window/'interaction_reset_baseline.py';need(not output.exists(),'fresh supplement')
 output.write_text(source.replace(needle,INSERT+needle))
 plan['reset_baseline_approval']=q['out']+'/boat/reset-baseline.approval.json';plan['scope']='independent reset-baseline supplement; original R6 group remains partial; no runtime change or repeated cadence'
 newplan=window/'interaction.reset-baseline.disabled.json';save(newplan,plan)
 old=q['interaction_plan'];q['interaction_plan']=ref(newplan)['path'];q['programs']['interaction']=ref(output)
 q['input_pins']=[r for r in q['input_pins'] if r['path']!=old]+[ref(newplan),ref(runner),ref(Path(__file__))]
 save(window/'request.json',q)
 auth=read(window/'authorization.required.json');need(auth['approved_by'] is None,'cannot change approved request');auth['request_sha256']=sha(window/'request.json');save(window/'authorization.required.json',auth)
 save(window/'supplement-derivation.json',dict(status='DISABLED_PENDING_REVIEW',original=ref(runner),derived=ref(output),only_change='baseline reset + separately pinned human review before unchanged TOUCHES loop',device_calls=0,original_group_accepted=False))
 print(json.dumps(dict(runner=ref(output),request=ref(window/'request.json'),device_calls=0)))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--window',type=Path,required=True);a=p.parse_args();build(a.window)
