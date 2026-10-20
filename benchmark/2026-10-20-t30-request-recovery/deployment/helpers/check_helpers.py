#!/usr/bin/env python3
"""Local unit/CLI refusal tests; no transport is available or invoked."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
from unittest import mock
import window_paths as w
import t30_exec

def main():
 p=argparse.ArgumentParser();p.add_argument('--main',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.main=a.main.resolve();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 here=Path(__file__).resolve().parent;d=here.parent/'final-01';cases=[]
 def fail(name,fn):
  try:fn()
  except (AssertionError,ValueError,TypeError):cases.append(name)
  else:raise AssertionError(name)
 for phase,age,ok in [(False,1199,True),(False,1200,False),(True,1200,True),(True,1799,True),(True,1800,False),(False,-1,False)]:
  name=f'budget_{phase}_{age}'
  if ok:assert w.budget({'start':1000},phase,1000+age)>0;cases.append(name)
  else:fail(name,lambda:w.budget({'start':1000},phase,1000+age))
 with mock.patch.dict(os.environ,{},clear=True):fail('default_no_transport',w.live)
 with mock.patch.dict(os.environ,{'T30_DEPLOY':str(here.parent)}):fail('pending_candidate_refused',w.final_data)
 for f in here.glob('*.py'):compile(f.read_text(),str(f),'exec')
 cases.append('all_helper_syntax')
 donor=a.main/'benchmark/2026-10-20-t29-production-peer/read_slots.py'
 expected=donor.read_text().replace('T29','T30').replace('9f3cecdeec89bd7aaa09a2d71a34f24bdc59ce41059a551144cef682526d3087','7f8d75bbf09e28e2b57a4621f1181ff944e79e462b78707c620dd67aef0b0bcb').replace('0xf488','0xf8bc')
 assert (here/'read_slots.py').read_text()==expected;cases.append('reader_only_pin_label_geometry_delta')
 pins=w.load(here/'slot-source-pins.json');assert pins['benchmark/2026-10-20-t30-request-recovery/deployment/helpers/read_slots.py']==w.sha(here/'read_slots.py');cases.append('current_reader_self_pin')
 # A local fixture tests actual command construction against the original plan hash.
 fixture=a.out/'fixture';(fixture/'apply').mkdir(parents=True)
 c={'holder':'fixture','start':100,'repo':str(a.main),'hdc':'/NONEXISTENT_T30_HDC'}
 plan={'holder':'fixture','start':100};(fixture/'apply/plan.json').write_text(json.dumps(plan))
 ad={'holder':'fixture','window_start':100,'boot':'fixture-boot','origin_apply_plan_sha256':w.sha(fixture/'apply/plan.json')};(fixture/'rollback.json').write_text(json.dumps(ad))
 with mock.patch.object(t30_exec,'WINDOW',fixture),mock.patch.object(t30_exec,'BASE',fixture),mock.patch.object(t30_exec,'deploy',return_value=d):
  argv=t30_exec.command('rollback','fixture-boot',101,202,'rollback.json','rollback',c)
  assert argv[argv.index('--apply-plan')+1]==str(fixture/'apply/plan.json');assert argv[argv.index('--start')+1]=='100';cases.append('original_apply_plan_exact_wiring')
  ad['origin_apply_plan_sha256']='0'*64;(fixture/'rollback.json').write_text(json.dumps(ad));fail('wrong_apply_plan_sha_refused',lambda:t30_exec.command('rollback','fixture-boot',101,202,'rollback.json','rollback',c))
 # Minimal exact file view for original executor before its Board import.
 view=a.out/'receipt-view'
 for role in ('bridge','shim'):
  for ref in w.load(d/(role+'-candidate.json'))['production_refs']:
   candidates=[a.main/ref['path'],next(x for x in here.parents if (x/'scripts/lab/board_note.sh').exists())/ref['path']]
   src=next(x for x in candidates if x.is_file() and w.sha(x)==ref['sha256']);dest=view/ref['path'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(src.read_bytes())
 for mode in ('preflight','apply','rollback'):
  argv=[sys.executable,str(d/'executor.py'),mode,'--execute','--repo',str(view),'--inputs',str(fixture),'--boot','OFFLINE','--parent','1','--birth','1','--hdc','/NONEXISTENT_T30_HDC','--holder','OFFLINE','--start','1','--admission',str(d/'admission.template.json'),'--out',str(a.out/'never-device')]
  r=subprocess.run(argv,capture_output=True,timeout=10)
  (a.out/(mode+'.argv.json')).write_text(json.dumps(argv));(a.out/(mode+'.stdout')).write_bytes(r.stdout);(a.out/(mode+'.stderr')).write_bytes(r.stderr);(a.out/(mode+'.rc')).write_text(str(r.returncode))
  assert r.returncode!=0 and b'shim_metadata' in r.stderr and b'TypeError' in r.stderr and not (a.out/'never-device').exists(),r.stderr
  cases.append('final_unsigned_'+mode+'_refused_before_Board')
 result={'status':'OFFLINE_PASS_NOT_RUNTIME_ADMISSION','cases':cases,'passed':len(cases),'device_calls':0,'executor_sha256':w.sha(d/'executor.py'),'reader_sha256':w.sha(here/'read_slots.py')};(a.out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
