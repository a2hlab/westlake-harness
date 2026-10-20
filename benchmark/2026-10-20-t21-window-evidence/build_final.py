#!/usr/bin/env python3
"""Create final T21 public evidence from existing local raw only."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true');a=ap.parse_args()
 if not a.write:print('Read-only default; --write creates a fresh final packet.');return
 base=Path.home()/'.local/share/westlake/toutiao-resume-20261020';w=base/'t21-5cd-window-01';readonly=base/'t21-readonly-01';repo=ROOT.parent/'westlake-harness'
 c=json.loads((w/'close.json').read_text());assert c['status']=='CLOSED_RUNTIME_RESTORED_UI_NOT_RECOVERED' and c['elapsed_seconds']<1800 and abs(c['unlocked_at']-c['start']-c['elapsed_seconds'])<.01
 assert (w/'close-unlock.rc').read_text().strip()=='2' and (w/'close-unlock-retry.rc').read_text().strip()=='0' and not (w/'close-held-after.stdout').read_bytes().strip()
 out=HERE/'final';out.mkdir(exist_ok=False);refs=[]
 def clean(s):return s.replace(str(base),'BASE20').replace(str(repo),'$WORKSPACES/westlake-harness').replace(str(Path.home()),'$HOME')
 def dump(n,x):
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(clean(json.dumps(x,indent=2))+'\n')
 def cp(p,n):
  q=out/n;q.parent.mkdir(parents=True,exist_ok=True);b=p.read_bytes();q.write_bytes(b if p.suffix=='.jpeg' else clean(b.decode()).encode());refs.append(dict(path='BASE20/'+str(p.relative_to(base)),sha256=sha(p),bytes=len(b),public_path=n,public_sha256=sha(q),byte_exact=b==q.read_bytes()))
 names=['close.json','close-before-unlock-attempt.json','context.json','admission.json','rollback-admission.json','final-snapshot-review.json','before-readonly-source.json','candidate-boot.json','restored-boot.json','apply/result.json','apply/plan.json','rollback/result.json','rollback/plan.json','slots-child11040/result.json','candidate-diagnostics/hilog-timeout.json']+[p.name for p in sorted(w.glob('close-*')) if p.name!='close-before-unlock-attempt.json']
 for n in names:cp(w/n,'receipts/'+n.replace('/','--')+('.txt' if n.endswith('.stderr') else ''))
 for stem in ['apply-exec','rollback-exec']:
  assert (w/(stem+'.rc')).read_text().strip()=='0'
  for x in ['argv.json','stdout','stderr','rc']:cp(w/(stem+'.'+x),'receipts/'+stem+'.'+x+('.txt' if x=='stderr' else ''))
 rb=json.loads((w/'rollback/result.json').read_text());assert rb['origin_apply_plan_sha256']==sha(w/'apply/plan.json')
 before=readonly/'before-snapshot/snapshot.json';after=w/'restored-snapshot/snapshot.json';bs=json.loads(before.read_text());rs=json.loads(after.read_text());fields=['plan_sha256','collection_sha256','bind_targets','init_configs','labels','sha','params','selinux_enforce'];eq={k:bs[k]==rs[k] for k in fields};assert all(eq.values())
 for s in [bs,rs]:assert s['complete'] and s['collection_complete'] and s['plan_target_count']==518 and len(s['labels'])==812
 assert rs['boot_id']==c['restored_boot'];supp=[]
 for d in [readonly/'before-supplement',w/'restored-supplement']:
  r=json.loads((d/'result.json').read_text());assert r['rc']==0 and r['targets']==26
  for n,pin in r['raw'].items():assert sha(d/n)==pin['sha256'] and (d/n).stat().st_size==pin['bytes']
  b=(d/'stdout.raw').read_bytes();assert b.startswith(b'T16_SUPPLEMENT_BOOT ') and b.endswith(b'T16_SUPPLEMENT_COMPLETE\n');supp.append(b)
 assert supp[0].split(b'\n',1)[1]==supp[1].split(b'\n',1)[1]
 dump('restoration-comparison.json',dict(equal=eq,supplement26_equal_except_boot_line=True,main_targets=518,main_labels=812,before_sha256=sha(before),after_sha256=sha(after),raw_pid_boot_uptime_not_required_equal=True))
 identity=w/'shell-1792465480383927000.stdout';text=identity.read_text()
 for k in ['before_sha','bridge_before_sha','media_before_sha','player_before_sha','shim_before_sha']:assert text.count(rb[k]+'  ')==2,k
 assert 'COMPAT_ABSENT' in text and text.rstrip().endswith('T21_SHELL_COMPLETE')
 power=w/'shell-1792465643433521000.stdout';assert 'Timeout=10000ms  OverrideTimeout=10000ms' in power.read_text() and 'errNum is:106!' in power.read_text()
 for p in [identity,power]:
  stem=p.name.removesuffix('.stdout');assert (w/(stem+'.rc')).read_text().strip()=='0'
  for x in ['argv.json','stdout','stderr','rc']:cp(w/(stem+'.'+x),'restoration/'+stem+'.'+x+('.txt' if x=='stderr' else ''))
 dead=w/'restored-last-child';dr=json.loads((dead/'receipt.json').read_text());assert sha(dead/'child.stderr')==dr['sha256'] and (dead/'child.stderr').stat().st_size==dr['bytes'] and dr['child']==14567 and dr['dead']
 for n in ['before','after','recv']:assert (dead/(n+'.rc')).read_text().strip()=='0'
 assert (dead/'before.stdout').read_bytes()==(dead/'after.stdout').read_bytes()
 lines=[l for l in (dead/'child.stderr').read_text(errors='replace').splitlines() if 'MediaPlayer.native_init' in l];assert lines
 (out/'baseline-native-init-excerpt.txt').write_text('\n'.join(lines)+'\n');cp(dead/'receipt.json','baseline-log-receipt.json');dump('baseline-log-source.json',dict(path='BASE20/t21-5cd-window-01/restored-last-child/child.stderr',sha256=sha(dead/'child.stderr'),bytes=dr['bytes'],scope='Restored baseline child log only; no random-exit diagnosis'))
 shot=w/'capture-1792465592932837000/screen.jpeg';assert sha(shot)==c['final_screenshot_sha256'];cp(shot,'images/restored-host.jpeg');cp(shot.parent/'screenshot.json','images/restored-host.json');dump('images/review.json',dict(actual_image_read=True,sha256=sha(shot),verdict='WESTLAKE_IME_HOST_ONLY_NOT_FEED'))
 facts=subprocess.run([sys.executable,str(repo/'scripts/lab/run_facts.py'),str(w)],capture_output=True);assert facts.returncode==0 and facts.stdout==(w/'facts.txt').read_bytes();cp(w/'facts.txt','facts.txt');(out/'facts.stderr.txt').write_bytes(facts.stderr)
 dump('facts-receipt.json',dict(rc=0,helper_sha256=sha(repo/'scripts/lab/run_facts.py'),matches_original_facts=True,no_synthesized_records=True))
 # Bind immutable MAIN excerpts; retain exact blobs privately rather than reinterpreting them.
 tech=Path('benchmark/2026-10-20-t21-first-live-pair');sourcepins=[]
 for rel in subprocess.check_output(['git','-C',str(repo),'ls-tree','-r','--name-only','ecc26cb9ed','--',str(tech)],text=True).splitlines():
  data=subprocess.check_output(['git','-C',str(repo),'show','ecc26cb9ed:'+rel]);p=HERE/'.private/producer-snapshots'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);sourcepins.append(dict(path=rel,commit='ecc26cb9ed',sha256=sha(p),bytes=len(data)))
 dump('main-technical-evidence.json',sourcepins)
 for name in ['t21_exec.py','t21_launch.py','t21_outer.py','t21_wait_boot.py']:cp(base/name,'execution-source/'+name)
 inp=base/'t21-candidate-inputs';im=json.loads((inp/'manifest.json').read_text())
 for n,pin in im['files'].items():assert sha(inp/n)==pin['sha256'] and (inp/n).stat().st_size==pin['bytes']
 cp(inp/'manifest.json','candidate-inputs.json')
 dump('results.json',dict(token='t21-window-evidence-final',status=c['status'],approved_by='outer(codex)',elapsed_seconds=c['elapsed_seconds'],candidate_boot=c['candidate_boot'],restored_boot=c['restored_boot'],apply_rc=0,rollback_rc=0,original_files_restored=5,compat_absent=True,snapshot_main_targets=518,supplement_targets=26,main_labels=812,power=[10000,10000],debug_parameter='ABSENT_ERR106',candidate11040_log_pairs_rc0=5,subsequent_log='Skia Invalid GrBackendTexture 1200x2132',independent_four_slots='UNKNOWN_NO_READS_CHILD_EXITED',video='NOT_PASSED',audio_this_window='UNKNOWN',candidate_feed='NOT_OBSERVED',restored_ui='HOST_ONLY_NOT_FEED',baseline_failure='MediaPlayer.native_init missing in child14567 log',unlock_initial_rc=2,unlock_retry_rc=0,held_after_empty=True,held_after_rc='NOT_SEPARATELY_RECORDED',device_calls_by_lane=0,archive_remote='PENDING'))
 dump('source-index.json',refs)
 dump('raw-archive-allowlist.json',dict(directories=['t21-5cd-window-01','t21-readonly-01','t21-candidate-inputs'],files=['t21_exec.py','t21_launch.py','t21_outer.py','t21_wait_boot.py'],scope='Entire original directories including all retries/failures and complete snapshot/supplement; no unrelated windows'))
 print(json.dumps(dict(status='FINAL_READY_FOR_ARCHIVE',device_calls=0)))
if __name__=='__main__':main()
