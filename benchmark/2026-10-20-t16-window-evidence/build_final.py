#!/usr/bin/env python3
"""Verify local closed-window receipts and append a final packet; never access devices."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true');a=ap.parse_args()
 if not a.write:print('Read-only default. --write creates a fresh final packet.');return
 base=Path.home()/'.local/share/westlake/toutiao-resume-20261020';w=base/'t16-5cd-window-01';main=ROOT.parent/'westlake-harness'
 checkpoint=HERE/'candidate-checkpoint-01';frozen=json.loads((checkpoint/'manifest.json').read_text())
 assert all(sha(ROOT/x['path'])==x['sha256'] for x in frozen['files'])
 close=json.loads((w/'close.json').read_text());assert close['status']=='CLOSED_RESTORED_BASELINE_FEED_VERIFIED' and close['approved_by']=='outer(codex)' and close['elapsed_seconds']<1800 and close['unlocked']
 assert (w/'unlock.rc').read_text().strip()=='0' and (w/'unlocked-readback.rc').read_text().strip()=='1' and not (w/'unlocked-readback.stdout').read_bytes().strip()
 out=HERE/'final';out.mkdir(exist_ok=False);refs=[]
 def clean(t):
  for x,y in [(str(base),'BASE20'),(str(main),'$WORKSPACES/westlake-harness'),(str(Path.home()),'$HOME')]:t=t.replace(x,y)
  return t
 def dump(n,x):
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(clean(json.dumps(x,indent=2))+'\n')
 def cp(p,n):
  q=out/n;q.parent.mkdir(parents=True,exist_ok=True);data=p.read_bytes();q.write_bytes(data if p.suffix=='.jpeg' else clean(data.decode()).encode())
  refs.append(dict(raw_path='BASE20/'+str(p.relative_to(base)),raw_sha256=sha(p),raw_bytes=len(data),public_path=n,public_sha256=sha(q),byte_exact=data==q.read_bytes()))
 for n in ['close.json','final-snapshot-review.json','rollback-admission.json','rollback/plan.json','rollback/result.json','rollback.rc','rollback.stdout','rollback.stderr','restored-boot.json','restored-retry-boot.json','unlock.argv.json','unlock.rc','unlock.stdout','unlock.stderr','unlocked-readback.rc','unlocked-readback.stdout','unlocked-readback.stderr']:
  cp(w/n,'receipts/'+n.replace('/','--')+('.txt' if n.endswith('.stderr') else ''))
 rb=json.loads((w/'rollback/result.json').read_text());assert rb['origin_apply_plan_sha256']==sha(w/'apply/plan.json') and (w/'rollback.rc').read_text().strip()=='0'
 comparisons=[];before=json.loads((base/'t16-before-snapshot-v2/snapshot.json').read_text())
 fields=['plan_sha256','collection_sha256','bind_targets','init_configs','labels','sha','params','selinux_enforce']
 original_supp=(base/'t16-before-supplement/stdout.raw').read_bytes();assert original_supp.startswith(b'T16_SUPPLEMENT_BOOT ') and original_supp.endswith(b'T16_SUPPLEMENT_COMPLETE\n')
 for snapname,suppname in [('t16-restored-snapshot','t16-restored-supplement'),('t16-restored-retry-snapshot','t16-restored-retry-supplement')]:
  sp=base/snapname/'snapshot.json';s=json.loads(sp.read_text());eq={k:before[k]==s[k] for k in fields};assert all(eq.values())
  assert s['collection_complete'] and s['complete'] and s['plan_target_count']==518 and len(s['labels'])==812
  sr=base/suppname/'result.json';rr=json.loads(sr.read_text());body=(base/suppname/'stdout.raw').read_bytes();assert rr['rc']==0 and rr['targets']==26 and rr['boot']==s['boot_id']
  for n,pin in rr['raw'].items():assert sha(base/suppname/n)==pin['sha256'] and (base/suppname/n).stat().st_size==pin['bytes']
  assert body.split(b'\n',1)[1]==original_supp.split(b'\n',1)[1]
  comparisons.append(dict(boot=s['boot_id'],snapshot_sha256=sha(sp),supplement_receipt_sha256=sha(sr),supplement_stdout_sha256=sha(base/suppname/'stdout.raw'),equal=eq,targets=518,labels=812,supplement26_equal_except_boot_line=True))
 assert comparisons[-1]['boot']==close['boot']=='cc7ff863-c697-4ad7-9c82-36c908187194'
 dump('restoration-comparison.json',dict(before_snapshot_sha256=sha(base/'t16-before-snapshot-v2/snapshot.json'),original_target_scope=544,split=[518,26],restores=comparisons,not_compared=['PID/process tables','uptime','mount raw strings','boot_id'],note='Reboot changes are expected; compare only the eight recorded invariant fields and supplement body.'))
 final=w/'shell-1792457857468972000.stdout';text=final.read_text();assert text.rstrip().endswith('T16_SHELL_COMPLETE')
 stem=final.name.removesuffix('.stdout');assert (w/(stem+'.rc')).read_text().strip()=='0'
 statlines=text.splitlines()[:2];identities=[]
 for line,pid,ppid,birth in zip(statlines,[10160,11911],[1,10160],[20717,22041]):
  m=re.fullmatch(r'(\d+) \((.*)\) (.*)',line);assert int(m[1])==pid;v=m[3].split();assert int(v[1])==ppid and int(v[19])==birth and v[0] not in ['Z','X','x'];identities.append(dict(pid=pid,ppid=ppid,birth=birth,state=v[0]))
 for key in ['before_sha','media_before_sha','player_before_sha']:assert text.count(rb[key]+'  ')==2,key
 assert text.count('COMPAT_ABSENT')==2 and text.count('mnt:[4026533005]')==2
 assert 'Timeout=10000ms  OverrideTimeout=10000ms' in text and '\ntrue \n' in text and 'errNum is:106!' in text
 for suffix in ['argv.json','rc','stdout','stderr']:cp(w/(stem+'.'+suffix),'identity/'+stem+'.'+suffix+('.txt' if suffix=='stderr' else ''))
 # Only technical guardian lines are excerpted; full process/window raw remains private.
 old=base/'t16-restored-current-read.txt';lines=old.read_text().splitlines();events=[line for line in lines if 'boot=676c315b-' in line and 'reason=' in line]
 assert any('child=7656 child_birth=10601' in x and 'OWNER_REFUSED' in x for x in events)
 (out/'first-restore-events.txt').write_text('\n'.join(events)+'\n')
 dump('first-restore-failure.json',dict(raw_path='BASE20/'+old.name,raw_sha256=sha(old),boot='676c315b-a17f-4c31-b204-78cb70bbb84b',child={'pid':7656,'birth':10601},observation='Outer reports natural exit; raw guardian records OWNER_REFUSED child_identity_changed_no_signal. No feed acceptance or causal diagnosis.'))
 shots=[]
 for directory,verdict in [('capture-1792457654018907000','SPLASH_ADVERTISEMENT_NOT_FEED'),('capture-1792457836456601000','REAL_NEWS_FEED')]:
  image=w/directory/'screen.jpeg';meta=w/directory/'screenshot.json';m=json.loads(meta.read_text());assert m['sha256']==sha(image)
  cp(image,'images/'+directory+'.jpeg');cp(meta,'images/'+directory+'.json');shots.append(dict(source=directory,sha256=sha(image),captured_at=m['captured_at'],independent_visual_review=verdict))
 assert shots[0]['sha256'].startswith('5cfcd938') and shots[1]['sha256']==close['restored_feed_sha256']=='7714468a3aad1a58870d7c41c60624b262b1c1e1176db6602943b0972649959d'
 dump('images/index.json',shots)
 cmd=[sys.executable,str(main/'scripts/lab/run_facts.py'),str(w)];r=subprocess.run(cmd,capture_output=True);assert r.returncode==0
 (out/'facts.txt').write_bytes(r.stdout);(out/'facts.stderr.txt').write_bytes(r.stderr)
 dump('facts-receipt.json',dict(argv=[clean(x) for x in cmd],rc=r.returncode,helper_sha256=sha(main/'scripts/lab/run_facts.py'),note='Original record-based counts, no inferred liveness; screenshot.json producers are separately bound by SHA.'))
 dump('results.json',dict(token='t16-window-evidence',status='CLOSED_RESTORED_BASELINE_FEED_VERIFIED',approved_by=close['approved_by'],elapsed_seconds=close['elapsed_seconds'],restored_boot=close['boot'],identities=identities,physical_and_private_sha={k:rb[k] for k in ['before_sha','media_before_sha','player_before_sha']},compat_absent_physical_and_private=True,mount_namespace='mnt:[4026533005]',power_restored=[10000,10000],ready=True,debug_log_parameter='ABSENT_ERR106',unlock_rc=0,held_readback_rc=1,held_output_empty=True,restored_feed_sha256=shots[-1]['sha256'],video='NOT_PASSED',audio='UNKNOWN',paired_bindings='UNKNOWN_NOT_MEASURED',random_exit_cause='NOT_INVESTIGATED',snapshot_scope='544=518+26;812 labels on the main snapshot',candidate_checkpoint_sha256=sha(checkpoint/'manifest.json'),archive='See archive/receipt.json; remote is pending until outer verification.'))
 dump('public-source-index.json',refs)
 # Archive selection is frozen to this task, not all BASE20 content.
 dirs=['t16-5cd-window-01','t16-before-snapshot-v2','t16-before-supplement','t16-restored-snapshot','t16-restored-supplement','t16-restored-retry-snapshot','t16-restored-retry-supplement','t16-5cd-inputs-readonly','t16-5cd-startup-readonly','t16-real-ready-readonly','t16-r8-candidate-inputs']
 files=[p.name for p in sorted(base.glob('t16*')) if p.is_file() and p.name!='t16-strings-landing.txt']
 dump('raw-archive-allowlist.json',dict(base='BASE20',directories=dirs,files=files,scope='Only T16 original window, inputs, snapshots/supplements, named reads and actual helpers. No unrelated historical tree.'))
 sourcepins=json.loads((checkpoint/'packet/source-build-pins.json').read_text())['sources']
 for x in sourcepins:
  blob=subprocess.check_output(['git','-C',str(main),'show',x['commit']+':'+x['path']]);assert hashlib.sha256(blob).hexdigest()==x['sha256'];p=HERE/'.private/producer-snapshots'/x['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(blob)
 assert all(sha(ROOT/x['path'])==x['sha256'] for x in frozen['files'])
 print(json.dumps(dict(status='FINAL_CREATED',candidate_checkpoint_unchanged=True,restored_feed_verified=True,device_calls=0)))
if __name__=='__main__':main()
