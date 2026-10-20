#!/usr/bin/env python3
"""Local in-progress evidence inventory. Never freeze, archive or call a device."""
import argparse,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true');a=ap.parse_args()
 if not a.write:print('Read-only default; --write creates an in-progress note, no manifest or archive.');return
 base=Path.home()/'.local/share/westlake/toutiao-resume-20261020';w=base/'t21-5cd-window-01';out=HERE/'observed-01';out.mkdir(exist_ok=False)
 def ref(p):return dict(path='BASE20/'+str(p.relative_to(base)),sha256=sha(p),bytes=p.stat().st_size)
 def dump(n,x):(out/n).write_text(json.dumps(x,indent=2)+'\n')
 apply=json.loads((w/'apply/result.json').read_text());rollback=json.loads((w/'rollback/result.json').read_text());assert (w/'apply-exec.rc').read_text().strip()=='0' and (w/'rollback-exec.rc').read_text().strip()=='0';assert rollback['origin_apply_plan_sha256']==sha(w/'apply/plan.json')
 childfacts=[];excerpts=[]
 for pid in [8306,11040,13834]:
  p=w/f'candidate-logs/child-{pid}.stderr';r=json.loads((w/f'candidate-logs/{pid}-receipt.json').read_text());assert sha(p)==r['sha256'] and p.stat().st_size==r['bytes'] and r['source_dead']
  for phase in ['before','recv','after']:assert (w/f'candidate-logs/{pid}-{phase}.rc').read_text().strip()=='0'
  lines=p.read_text(errors='replace').splitlines();locks=[];unlocks=[];unwrap=[];skia=[]
  for number,line in enumerate(lines,1):
   if '[WL-R20-PAIR]' in line:
    (locks if 'op=lock ' in line else unlocks).append(line);excerpts.append(dict(child=pid,line_number=number,line=line,source_sha256=sha(p)))
   if '[WL-R20-UNWRAP]' in line:unwrap.append(line)
   if 'Invalid GrBackendTexture.' in line:skia.append(number);excerpts.append(dict(child=pid,line_number=number,line=line,source_sha256=sha(p)))
  if pid==11040:
   assert len(locks)==len(unlocks)==5 and all(' rc=0 ' in l and ' map=1/0 ' in l for l in locks)
   assert all(' rc=0 ' in l and ' unmap=1/0 flush=1/0 ' in l for l in unlocks) and skia
  childfacts.append(dict(child=pid,source=ref(p),receipt=ref(w/f'candidate-logs/{pid}-receipt.json'),historical_file_source_dead=True,lock_rows=len(locks),unlock_rows=len(unlocks),unwrap_rows=len(unwrap),skia_invalid_texture_line_numbers=skia,exit_cause='NOT_INVESTIGATED'))
 slots=json.loads((w/'slots-child11040/result.json').read_text());assert slots['status']=='UNKNOWN' and slots['reads']==[] and '/proc/11040/stat: No such file or directory' in slots['error']
 before=base/'t21-readonly-01/before-snapshot/snapshot.json';s=json.loads(before.read_text());supp=base/'t21-readonly-01/before-supplement/result.json';sp=json.loads(supp.read_text())
 assert s['complete'] and s['collection_complete'] and s['plan_target_count']==518 and len(s['labels'])==812 and sp['rc']==0 and sp['targets']==26
 helpers=[base/n for n in ['t21_exec.py','t21_launch.py','t21_outer.py','t21_wait_boot.py']];assert all(p.is_file() for p in helpers)
 dump('archive-scope-plan.json',dict(status='WAIT_ROOT_CLOSE_NO_ARCHIVE',directories=['BASE20/t21-5cd-window-01','BASE20/t21-readonly-01','BASE20/t21-candidate-inputs'],helpers=[ref(p) for p in helpers],include='All original files, failures, partial hilog timeout, slot refusal and future recovery attempts; select final whole-directory contents only after close',freeze=False,archive=False))
 dump('technical-excerpts.json',excerpts);dump('children.json',childfacts)
 dump('results.json',dict(token='t21-window-evidence-in-progress',status='RECOVERY_IN_PROGRESS_NOT_CLOSED',candidate_boot=slots['boot'],parent=slots['parent'],parent_birth=slots['parent_birth'],candidate_shim_sha256=apply['shim_after_sha'],apply_rc=0,rollback_rc=0,rollback_status=rollback['status'],rollback_is_not_fresh_restoration_proof=True,child11040_pairs_rc0=5,operation_source='Candidate log rows only; not independent slot/provider or displayed-frame proof',slots='UNKNOWN_NO_READS_CHILD_STAT_ABSENT',video='NOT_PASSED',audio_this_window='UNKNOWN',candidate_feed='NOT_OBSERVED_PER_OUTER_NO_INDEPENDENT_IMAGE_REVIEW_IN_THIS_INVENTORY',restore_ui='PENDING',unlock='PENDING',before_main_targets=518,before_labels=812,supplement_targets=26,archive_created=False,manifest_created=False,device_calls=0))
 dump('source-index.json',[ref(w/n) for n in ['apply/result.json','apply/plan.json','rollback/result.json','apply-exec.rc','rollback-exec.rc','slots-child11040/result.json','candidate-diagnostics/hilog-timeout.json']]+[ref(before),ref(supp)])
 print(json.dumps(dict(status='IN_PROGRESS_NOTE_ONLY',child_logs_verified=3,pairs=5,slots='UNKNOWN',archive=False,manifest=False)))
if __name__=='__main__':main()
