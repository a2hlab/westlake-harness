#!/usr/bin/env python3
"""T23 local evidence packaging. Explicit fresh output; no device commands."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from compare_restore import compare
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true');a=ap.parse_args()
 if not a.write:print('Preview only; --write creates fresh final local evidence.');return
 base=Path.home()/'.local/share/westlake/toutiao-resume-20261020';w=base/'t23-5cd-window-01';readonly=base/'t23-readonly-01';repo=ROOT.parent/'westlake-harness'
 c=json.loads((w/'close.json').read_text());assert c['unlocked'] and c['status']=='CLOSED_RUNTIME_RESTORED_UI_NOT_RECOVERED' and c['elapsed']<1800
 assert (w/'unlock.rc').read_text().strip()=='0' and (w/'held-after-unlock.rc').read_text().strip()=='1' and not (w/'held-after-unlock.stdout').read_bytes().strip()
 out=HERE/'final';out.mkdir(exist_ok=False);refs=[]
 def clean(t):return t.replace(str(base),'BASE20').replace(str(repo),'$WORKSPACES/westlake-harness').replace(str(Path.home()),'$HOME')
 def dump(n,v):
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(clean(json.dumps(v,indent=2))+'\n')
 def cp(p,n):
  q=out/n;q.parent.mkdir(parents=True,exist_ok=True);b=p.read_bytes();q.write_bytes(b if p.suffix=='.jpeg' else clean(b.decode()).encode());refs.append({'path':'BASE20/'+str(p.relative_to(base)),'sha256':sha(p),'bytes':len(b),'public_path':n,'public_sha256':sha(q),'byte_exact':b==q.read_bytes()})
 for n in ['close.json','close-preunlock.json','context.json','admission.json','rollback-admission.json','apply/plan.json','apply/result.json','rollback/plan.json','rollback/result.json','candidate-boot.json','restored-boot-boot.json','human-audio-receipt.json','playback-review.json','quick-r2/result.json','restoration-comparison.json']:
  cp(w/n,'receipts/'+n.replace('/','--'))
 for stem in ['apply-exec','rollback-exec','unlock','held-after-unlock']:
  for suffix in ['argv.json','stdout','stderr','rc']:
   p=w/(stem+'.'+suffix)
   if p.exists():cp(p,'receipts/'+p.name+('.txt' if suffix=='stderr' else ''))
 for stem in ['apply-exec','rollback-exec']:assert (w/(stem+'.rc')).read_text().strip()=='0'
 rb=json.loads((w/'rollback/result.json').read_text());assert rb['origin_apply_plan_sha256']==sha(w/'apply/plan.json')
 identity=w/c['identity_raw'];assert sha(identity)==c['identity_sha256'];text=identity.read_text()
 for key in ['before_sha','bridge_before_sha','media_before_sha','player_before_sha','shim_before_sha']:assert text.count(rb[key]+'  ')==2
 assert 'COMPAT_ABSENT' in text and 'Timeout=10000ms  OverrideTimeout=10000ms' in text and 'errNum is:106!' in text and text.rstrip().endswith('T23_SHELL_COMPLETE')
 stem=identity.name.removesuffix('.stdout');assert (w/(stem+'.rc')).read_text().strip()=='0'
 for suffix in ['argv.json','stdout','stderr','rc']:cp(w/(stem+'.'+suffix),'restoration/'+stem+'.'+suffix+('.txt' if suffix=='stderr' else ''))
 comparison=compare(readonly/'before-snapshot-r2/snapshot.json',w/'restored-snapshot/snapshot.json',readonly/'before-supplement',w/'restored-supplement','9f6d75bb-8e7f-4058-be3c-af28b834463e',c['restored_boot']);assert comparison['status']=='EQUAL';dump('independent-restoration-comparison.json',comparison)
 cp(readonly/'snapshot-first-timeout.json','failures/snapshot-first-timeout.json');cp(w/'candidate-full-log-prefix/transport.json','failures/full-prefix-timeout.json')
 assert json.loads((w/'candidate-full-log-prefix/transport.json').read_text())['timed_out']
 logs=[]
 for n in ['candidate-prefix-file','candidate-prefix-file-02']:
  d=w/n;r=json.loads((d/'result.json').read_text());assert sha(d/'selected.raw')==r['sha256'] and (d/'selected.raw').stat().st_size==r['selected_bytes'];assert r['immutability_not_proven'] is True
  for phase in ['copy','receive','after']:assert (d/(phase+'.rc')).read_text().strip()=='0'
  for p in sorted(d.iterdir()):
   if p.suffix!='.raw':cp(p,'log-receipts/'+n+'/'+p.name+('.txt' if p.suffix=='.stderr' else ''))
  logs.append({'path':'BASE20/t23-5cd-window-01/'+n+'/selected.raw','sha256':r['sha256'],'bytes':r['selected_bytes'],'complete_selected_prefix':True,'immutability_not_proven':True})
 dump('private-log-index.json',logs)
 playback=json.loads((w/'playback-review.json').read_text());assert playback['status']=='NOT_PASSED';shots=[]
 for row in playback['screenshots']:
  p=Path(row['path']);assert sha(p)==row['sha256'];name='images/'+row['cycle']+'-'+str(row['offset'])+'.jpeg';cp(p,name);shots.append({'cycle':row['cycle'],'offset':row['offset'],'sha256':row['sha256'],'public_path':name})
 assert len(shots)==8 and len({s['sha256'] for s in shots if s['cycle']=='cycle-observation-01'})==1
 for n in ['cycle-observation-01','cycle-observation-02']:cp(w/n/'result.json','cycles/'+n+'.json')
 cp(w/'capture-1792467730657113000/screen.jpeg','images/candidate-feed.jpeg');cp(w/'restored-icon/after-icon.jpeg','images/restored-host.jpeg');cp(w/'restored-icon/record.json','restored-icon-record.json');cp(w/'candidate-icon/record.json','candidate-icon-record.json')
 dump('image-review.json',{'reviewer':'independent Codex lane','actual_images_read':['candidate-feed','cycle1 offset0 (other three byte-identical)','cycle2 offsets0,10,20','restored-host'],'cycle1':'four byte-identical still images; no dynamic visual proof','cycle2':'tutorial overlay then black content; UI/progress change is not video-frame motion','restored':'Westlake IME host only','audio':'user-confirmed audible this window; exact clip unknown; possible user touch','video':'NOT_PASSED','cycle_images':shots})
 run=subprocess.run([sys.executable,str(repo/'scripts/lab/run_facts.py'),str(w)],capture_output=True);assert run.returncode==0;(out/'facts.txt').write_bytes(run.stdout);(out/'facts.stderr.txt').write_bytes(run.stderr)
 dump('facts-receipt.json',{'rc':run.returncode,'helper_sha256':sha(repo/'scripts/lab/run_facts.py'),'record_schema_only':True,'cycle_images_separately_indexed':8,'no_synthetic_records':True,'note':'capture directories without record.json are outside run_facts denominator'})
 helpers=sorted(base.glob('t23_*.py'));assert helpers
 for p in helpers:cp(p,'execution-source/'+p.name)
 manifest=json.loads((base/'t23-candidate-inputs/manifest.json').read_text())
 for name,pin in manifest.items():assert sha(base/'t23-candidate-inputs'/name)==pin['sha256'] and (base/'t23-candidate-inputs'/name).stat().st_size==pin['bytes']
 cp(base/'t23-candidate-inputs/manifest.json','candidate-inputs.json')
 source=[]
 for dirname in ['2026-10-20-t23-shim-deployment','2026-10-20-t23-egl-import']:
  d=repo/'benchmark'/dirname
  for p in sorted(d.iterdir()):
   if p.is_file() and p.suffix in ['.py','.c','.h','.json','.sh','.md']:
    rel=p.relative_to(repo);dest=HERE/'.private/producer-snapshots'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes());source.append({'path':str(rel),'sha256':sha(p),'bytes':p.stat().st_size})
 dump('source-build-pins.json',source)
 dump('results.json',{'status':c['status'],'elapsed_seconds':c['elapsed'],'approved_by':'outer(codex)','candidate_boot':'af001b38-659a-4f1f-9dd7-b85960587a2c','restored_boot':c['restored_boot'],'runtime_writes':'root actual six-state apply and rollback, both rc0','candidate_feed':'VISIBLE','video':'NOT_PASSED','audio':'USER_CONFIRMED_AUDIBLE_THIS_WINDOW_CLIP_UNKNOWN','possible_user_touch':True,'restored_ui':'HOST_ONLY_NOT_FEED','snapshot_8_fields':'EQUAL','supplement26':'EQUAL_EXCEPT_BOOT','power':'10000/10000','parameter':'ABSENT_ERR106','unlocked':True,'unlock_rc':0,'held_after_rc':1,'failed_lane_handoff':'exact MAIN held returned1 due kill0 EPERM; subsequent read-only HDC timed out rc124 without completion marker; root resumed sole execution','lane_device_attempts_during_handoff':1,'lane_runtime_writes':0,'archive_remote':'PENDING'})
 dump('raw-archive-allowlist.json',{'directories':['t23-5cd-window-01','t23-readonly-01','t23-candidate-inputs'],'files':[p.name for p in helpers],'scope':'whole closed window including first snapshot timeout/r2, both copied full-prefix logs and prior failed stream, all raw commands, human audio and playback review, all t23 helpers'})
 dump('source-index.json',refs)
 print(json.dumps({'status':'FINAL_LOCAL_EVIDENCE_PREPARED','root_helpers':len(helpers),'source_build_files':len(source),'facts':run.stdout.decode().splitlines()[-1]}))
if __name__=='__main__':main()
