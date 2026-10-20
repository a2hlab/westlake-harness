#!/usr/bin/env python3
"""Append a closed T17 evidence packet using local receipts only."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true');a=ap.parse_args()
 if not a.write:print('Read-only default; --write creates a fresh final packet.');return
 base=Path.home()/'.local/share/westlake/toutiao-resume-20261020';w=base/'t17-5cd-window-01';mainrepo=ROOT.parent/'westlake-harness'
 for d in ['checkpoint-01','checkpoint-02']:
  assert all(sha(ROOT/x['path'])==x['sha256'] for x in json.loads((HERE/d/'manifest.json').read_text())['files'])
 close=json.loads((w/'close.json').read_text());assert close['status']=='CLOSED_RESTORED_BASELINE_FEED_VERIFIED' and close['approved_by']=='outer(codex)' and close['unlocked'] and close['elapsed_seconds']<1800
 assert (w/'close-unlock.rc').read_text().strip()=='0' and (w/'close-held-after.rc').read_text().strip()=='1' and not (w/'close-held-after.stdout').read_bytes().strip()
 out=HERE/'final';out.mkdir(exist_ok=False);refs=[]
 def clean(s):
  for x,y in [(str(base),'BASE20'),(str(mainrepo),'$WORKSPACES/westlake-harness'),(str(Path.home()),'$HOME')]:s=s.replace(x,y)
  return s
 def dump(n,x):
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(clean(json.dumps(x,indent=2))+'\n')
 def cp(p,n):
  q=out/n;q.parent.mkdir(parents=True,exist_ok=True);data=p.read_bytes();q.write_bytes(data if p.suffix=='.jpeg' else clean(data.decode()).encode());refs.append(dict(raw_path='BASE20/'+str(p.relative_to(base)),raw_sha256=sha(p),raw_bytes=len(data),public_path=n,public_sha256=sha(q),byte_exact=data==q.read_bytes()))
 names=['close.json','final-snapshot-review.json','rollback-admission.json','rollback/plan.json','rollback/result.json','rollback-exec.argv.json','rollback-exec.rc','rollback-exec.stdout','rollback-exec.stderr','restored-readiness-retry-boot.json']+[p.name for p in sorted(w.glob('close-*'))]
 for n in names:cp(w/n,'receipts/'+n.replace('/','--')+('.txt' if n.endswith('.stderr') else ''))
 rb=json.loads((w/'rollback/result.json').read_text());assert rb['origin_apply_plan_sha256']==sha(w/'apply/plan.json') and (w/'rollback-exec.rc').read_text().strip()=='0'
 before=json.loads((w/'before-snapshot/snapshot.json').read_text());after=json.loads((w/'restored-snapshot/snapshot.json').read_text());fields=['plan_sha256','collection_sha256','bind_targets','init_configs','labels','sha','params','selinux_enforce'];eq={k:before[k]==after[k] for k in fields};assert all(eq.values())
 for s in [before,after]:assert s['complete'] and s['collection_complete'] and s['plan_target_count']==518 and len(s['labels'])==812
 assert after['boot_id']==close['boot']=='04564c50-0d6e-4420-8db4-b9581b3658f7'
 supp=[]
 for name in ['before-supplement','restored-supplement']:
  d=w/name;r=json.loads((d/'result.json').read_text());assert r['rc']==0 and r['targets']==26
  for n,pin in r['raw'].items():assert sha(d/n)==pin['sha256'] and (d/n).stat().st_size==pin['bytes']
  b=(d/'stdout.raw').read_bytes();assert b.startswith(b'T16_SUPPLEMENT_BOOT ') and b.endswith(b'T16_SUPPLEMENT_COMPLETE\n');supp.append(b)
 assert supp[0].split(b'\n',1)[1]==supp[1].split(b'\n',1)[1]
 dump('restoration-comparison.json',dict(scope='544 = 518 + 26; 812 main snapshot labels',before_sha256=sha(w/'before-snapshot/snapshot.json'),restored_sha256=sha(w/'restored-snapshot/snapshot.json'),equal=eq,supplement26_equal_except_boot_line=True,supplement_sha256=[sha(w/n/'stdout.raw') for n in ['before-supplement','restored-supplement']],not_compared=['boot ID','PID/process tables','uptime','raw mount strings']))
 identity=w/'shell-1792459400740282000.stdout';text=identity.read_text();assert text.rstrip().endswith('T17_SHELL_COMPLETE');ids=[]
 for line,pid,ppid,birth in zip(text.splitlines()[:2],[10470,12232],[1,10470],[26828,28159]):
  m=re.fullmatch(r'(\d+) \((.*)\) (.*)',line);v=m[3].split();assert int(m[1])==pid and int(v[1])==ppid and int(v[19])==birth and v[0] not in ['Z','X','x'];ids.append(dict(pid=pid,ppid=ppid,birth=birth,state=v[0]))
 for k in ['before_sha','media_before_sha','player_before_sha']:assert text.count(rb[k]+'  ')==2
 assert text.count('COMPAT_ABSENT')==2 and text.count('mnt:[4026533005]')==2 and '\ntrue \n' in text and 'errNum is:106!' in text
 power=w/'shell-1792459441134324000.stdout';assert 'Timeout=10000ms  OverrideTimeout=10000ms' in power.read_text()
 for p in [identity,power,w/'shell-1792459376447717000.stdout']:
  stem=p.name.removesuffix('.stdout');assert (w/(stem+'.rc')).read_text().strip()=='0'
  for suffix in ['argv.json','rc','stdout','stderr']:cp(w/(stem+'.'+suffix),'identity/'+stem+'.'+suffix+('.txt' if suffix=='stderr' else ''))
 shots=[]
 for d,v in [('capture-1792459364127132000','EMPTY_LOADING_SHELL_NOT_FEED'),('capture-1792459409162951000','REAL_NEWS_FEED')]:
  p=w/d/'screen.jpeg';m=json.loads((w/d/'screenshot.json').read_text());assert sha(p)==m['sha256'];cp(p,'images/'+d+'.jpeg');cp(w/d/'screenshot.json','images/'+d+'.json');shots.append(dict(path=d,sha256=sha(p),independent_visual_verdict=v))
 assert shots[-1]['sha256']==close['restored_feed_sha256']=='6d14aca2e87c8de99a4ee12c99d1e4631aef6aecda412f070c6809779be7078b';dump('images/index.json',shots)
 cmd=[sys.executable,str(mainrepo/'scripts/lab/run_facts.py'),str(w)];r=subprocess.run(cmd,capture_output=True);assert r.returncode==0;(out/'facts.txt').write_bytes(r.stdout);(out/'facts.stderr.txt').write_bytes(r.stderr);dump('facts-receipt.json',dict(argv=[clean(x) for x in cmd],rc=r.returncode,helper_sha256=sha(mainrepo/'scripts/lab/run_facts.py'),note='Unmodified record-based counts; no inferred liveness or synthesized records.'))
 helpers=[]
 for p in sorted(base.glob('t17*.py')):cp(p,'execution-source/'+p.name);helpers.append(dict(path='BASE20/'+p.name,sha256=sha(p)))
 dump('results.json',dict(token='t17-window-evidence',status=close['status'],approved_by=close['approved_by'],elapsed_seconds=close['elapsed_seconds'],restored_boot=close['boot'],identities=ids,physical_private_original_sha=True,compat_absent=True,mount_namespace='mnt:[4026533005]',power=[10000,10000],ready=True,debug_log_parameter='ABSENT_ERR106',paired_binding='MATCH',video='NOT_PASSED',audio='UNKNOWN',observer='GUARD_REFUSED_BEFORE_STAGE_ATTACH_FORWARD',observer_samples=0,continuous_images='RELAUNCHED_FEED_NOT_VIDEO_CONTINUITY',mirror_rows=254,mirror_cap=256,global_network_error_absence='NOT_ESTABLISHED',unlock_rc=0,held_after_rc=1,held_after_empty=True,restored_feed_sha256=shots[-1]['sha256'],checkpoints=[dict(path=d,sha256=sha(HERE/d/'manifest.json')) for d in ['checkpoint-01','checkpoint-02']],archive='Local archive receipt; remote pending until actual outer receipt.',device_calls_by_lane=0))
 dump('public-source-index.json',refs)
 dump('raw-archive-allowlist.json',dict(base='BASE20',directories=['t17-5cd-window-01','t17-observer-preparation','t16-r8-candidate-inputs'],files=[p.name for p in sorted(base.glob('t17*')) if p.is_file()],scope='Entire T17 window including all failures/retries, observer guard, audio-sources-read and close; T17 helpers/preparation; only reused input artifacts, not old T16 outcomes.'))
 for x in json.loads((HERE/'checkpoint-01/packet/source-pins.json').read_text())['sources']:
  blob=subprocess.check_output(['git','-C',str(mainrepo),'show',x['commit']+':'+x['path']]);assert hashlib.sha256(blob).hexdigest()==x['sha256'];p=HERE/'.private/producer-snapshots'/x['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(blob)
 print(json.dumps(dict(status='FINAL_CREATED',device_calls=0,helpers=len(helpers))))
if __name__=='__main__':main()
