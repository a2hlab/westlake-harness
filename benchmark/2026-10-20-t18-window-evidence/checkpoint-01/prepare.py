#!/usr/bin/env python3
"""T18 bounded local checkpoint; whole-window archive waits for final close."""
import argparse,hashlib,json,subprocess,sys,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true');a=ap.parse_args()
 if not a.write:print('Read-only default; --write creates fresh checkpoint, never a tar.');return
 base=Path.home()/'.local/share/westlake/toutiao-resume-20261020';w=base/'t18-5cd-window-01';repo=ROOT.parent/'westlake-harness';out=HERE/'packet-final';out.mkdir(exist_ok=False);refs=[]
 def clean(s):
  for x,y in [(str(base),'BASE20'),(str(repo),'$WORKSPACES/westlake-harness'),(str(Path.home()),'$HOME')]:s=s.replace(x,y)
  return re.sub(r'/Users/[^/\s\"\']+','$RECORDED_SDK_BUILD_HOME',s)
 def dump(n,x):
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(clean(json.dumps(x,indent=2))+'\n')
 def ref(p):return dict(path='BASE20/'+str(p.relative_to(base)),sha256=sha(p),bytes=p.stat().st_size)
 def cp(p,n):
  q=out/n;q.parent.mkdir(parents=True,exist_ok=True);data=p.read_bytes();q.write_bytes(data if p.suffix=='.jpeg' else clean(data.decode()).encode());refs.append(dict(**ref(p),public_path=n,public_sha256=sha(q),byte_exact=data==q.read_bytes()))
 apply=json.loads((w/'apply/result.json').read_text());ad=json.loads((w/'admission.json').read_text());rb=json.loads((w/'rollback/result.json').read_text());plan=json.loads((w/'observer-plan.json').read_text())
 assert (w/'apply-exec.rc').read_text().strip()=='0' and (w/'rollback-exec.rc').read_text().strip()=='0'
 assert apply['admission_sha256']==sha(w/'admission.json') and apply['executor_sha256']==ad['executor_sha256']
 assert rb['origin_apply_plan_sha256']==sha(w/'apply/plan.json')
 for n in ['context.json','admission.json','apply/result.json','apply/plan.json','rollback/result.json','rollback/plan.json','candidate-ready-retry-boot.json','candidate-video-profile/profile.json','observer-plan.json']:
  cp(w/n,'receipts/'+n.replace('/','--'))
 for stem in ['apply-exec','rollback-exec','candidate-profile-exec','candidate-video-profile-exec','observer-exec']:
  for suffix in ['argv.json','rc','stdout','stderr']:cp(w/(stem+'.'+suffix),'receipts/'+stem+'.'+suffix+('.txt' if suffix=='stderr' else ''))
 assert (w/'candidate-profile-exec.rc').read_text().strip()!='0' and 'missing exact mapping' in (w/'candidate-profile-exec.stderr').read_text()
 source=[]
 rels=['benchmark/2026-10-20-t18-bridge-deployment/'+n for n in ['executor.py','parameters.json','executor-source-pins.json','bridge-candidate.json']]+[plan['observer_path'],'benchmark/2026-10-20-t18-audiotrack-production/results.json','benchmark/2026-10-20-t18-audiotrack-production/build.py']
 for rel in rels:
  p=repo/rel;commit=subprocess.check_output(['git','-C',str(repo),'log','-1','--format=%H','--',rel],text=True).strip();blob=subprocess.check_output(['git','-C',str(repo),'show',commit+':'+rel]);assert blob==p.read_bytes();source.append(dict(path=rel,commit=commit,sha256=sha(p),bytes=p.stat().st_size))
 assert source[0]['sha256']==ad['executor_sha256'] and source[1]['sha256']==ad['parameters_sha256'] and source[2]['sha256']==ad['source_pins_sha256'] and source[3]['sha256']==ad['bridge_candidate_sha256']
 assert source[4]['sha256']==plan['observer_sha256']
 dump('source-build-pins.json',dict(files=source,bridge_binary_sha256=apply['bridge_after_sha'],bridge_candidate_field_role='bridge_candidate_sha256 pins the candidate JSON, not the DSO bytes',builds_by_evidence_lane=0))
 private=w/'shell-1792461648389936000.stdout';line=apply['bridge_after_sha']+'  /proc/6538/root/data/local/tmp/asx/liboh_adapter_bridge.so';assert line in private.read_text();(out/'private-bridge-sha.txt').write_text(line+'\n');dump('private-bridge-source.json',ref(private))
 d=w/'candidate-video-log-range';r=json.loads((d/'result.json').read_text());p=d/'selected.raw';assert p.stat().st_size==r['selected_bytes']==r['source_end']-r['source_start']==6639414 and sha(p)==r['sha256'];assert r['profile_sha256']==sha(w/'candidate-video-profile/profile.json');cp(d/'result.json','range/result.json');dump('range/private-source-index.json',[ref(p) for p in sorted(d.iterdir()) if p.is_file()])
 peer=ROOT.parent/'westlake-harness-api-progress-peer/benchmark/2026-10-20-t18-observer-peer/runtime-log-review.json';pr=json.loads(peer.read_text());assert pr['input']['selected_sha256']==r['sha256'] and pr['input']['selected_bytes']==r['selected_bytes']
 # Independently match only the peer's fixed literal counts/offsets; no URL extraction.
 raw=p.read_bytes()
 for key,e in pr['evidence'].items():
  hits=[];offset=0
  for line in raw.splitlines(keepends=True):
   if e['literal'].encode() in line:hits.append((offset,line.rstrip(b'\r\n').decode()))
   offset+=len(line)
  assert len(hits)==e['count'],key
  if hits:assert hits[0][0]==e['first']['selected_byte_offset'] and hits[-1][0]==e['last']['selected_byte_offset'],key
 (out/'range/runtime-log-review.json').write_bytes(peer.read_bytes())
 dump('range/peer-binding.json',dict(source='$WORKSPACES/westlake-harness-api-progress-peer/benchmark/2026-10-20-t18-observer-peer/runtime-log-review.json',sha256=sha(peer),bytes=peer.stat().st_size,byte_exact=True,literal_counts_and_first_last_offsets_verified=True))

 obs=json.loads((w/'observer-execution/observe/result.json').read_text());outer=json.loads((w/'observer-execution/result.json').read_text())
 assert obs['fromSurface_count']==obs['lock_count']==0 and 'no stop reply packet' in obs['error'] and obs['cleanup']['verified'] is False
 assert outer['cleanup']['verified'] is True and outer['cleanup']['owned_server_gone'] and outer['cleanup']['child_identity_tracer0_nonstopped'] and outer['cleanup']['errors']==[] and outer['host_rc']==2
 for n in ['result.json','host.argv.json','host.stdout','host.stderr','observe/result.json','observe/exception.txt','observe/lldb-commands.jsonl','observe/events.jsonl']:
  cp(w/'observer-execution'/n,'observer/'+n.replace('/','--')+('.txt' if n.endswith('.stderr') else ''))
 commands=w/'observer-execution/commands';cmdindex=[]
 for p in sorted(commands.iterdir()):
  if p.is_file():cmdindex.append(ref(p))
 for i in [140,145,150,155,160,165]:
  for suffix in ['json','stdout.txt','stderr.txt']:
   p=commands/f'command-{i:05}.{suffix}'
   if p.exists():cp(p,'observer/cleanup/'+p.name)
 dump('observer/private-command-index.json',cmdindex)
 dump('observer/verdict.json',dict(status='NO_STOP_REPLY_ZERO_SAMPLES',host_cleanup_verified=False,host_cleanup_errors_preserved=True,outer_finally_cleanup_verified=True,owned_server_gone=True,child_same_identity_tracer0_nonstopped=True,host_rc=2,fromSurface_samples=0,lock_samples=0,object_observation='UNKNOWN',no_tool_failure_cause_assigned=True))
 shots=[]
 for name,v in [('capture-1792461609011228000','REAL_NEWS_FEED'),('capture-1792461763033549000','VIDEO_PAGE_SAME_COVER_SUBJECT_NOT_PLAYBACK_PROOF')]:
  p=w/name/'screen.jpeg';m=json.loads((w/name/'screenshot.json').read_text());assert m['sha256']==sha(p);cp(p,'images/'+name+'.jpeg');cp(w/name/'screenshot.json','images/'+name+'.json');shots.append(dict(source=name,sha256=sha(p),actual_image_read=True,verdict=v))
 dump('images/review.json',shots)
 cmd=[sys.executable,str(repo/'scripts/lab/run_facts.py'),str(w)];fr=subprocess.run(cmd,capture_output=True);assert fr.returncode==0;(out/'facts.txt').write_bytes(fr.stdout);(out/'facts.stderr.txt').write_bytes(fr.stderr);dump('facts-receipt.json',dict(argv=[clean(x) for x in cmd],rc=0,helper_sha256=sha(repo/'scripts/lab/run_facts.py'),scope='Checkpoint counts only; no invented records or liveness.'))
 helpers=[]
 for p in sorted(base.glob('t18*.py')):cp(p,'execution-source/'+p.name);helpers.append(ref(p))
 dump('archive-plan.json',dict(status='WAITING_FINAL_CLOSE_NO_TAR',whole_directories=['BASE20/t18-5cd-window-01'],helpers=helpers,additional_inputs='Only exact files used by actual apply argv and observer-plan module/tool input pins; preserve original bytes and raw errors. Reference existing build archives rather than importing unrelated build trees.',include_failures=['initial ready timeout','first profile missing exact mapping','observer no stop reply','host cleanup errors and separate outer finally success','all rollback/restoration retries'],required_before_packaging=['close/unlock/held receipt','fresh baseline exact five-file restoration and compat absence','same-window snapshot518+supplement26 comparisons','actual final feed screenshot','power and parameter state'],public_policy='No media URL/token, full stderr or large binary in public whitelist.'))
 dump('results.json',dict(token='t18-window-evidence',status='NOT_CLOSED',candidate_boot=plan['boot'],parent=plan['parent'],child=plan['child'],bridge_binary_sha256=apply['bridge_after_sha'],apply_rc=0,range_bytes=r['selected_bytes'],range_sha256=r['sha256'],video='NOT_PASSED',audio='UNKNOWN',observer='NO_STOP_REPLY',observer_samples=0,host_cleanup_verified=False,outer_cleanup_verified=True,rollback_rc=0,restoration='PENDING_FRESH_BASELINE_AND_FEED',unlock='PENDING',archive='NOT_CREATED',runtime_log_conclusions=pr['conclusions'],device_calls_by_lane=0))
 dump('public-source-index.json',refs);print(json.dumps(dict(status='CHECKPOINT_READY_NOT_CLOSED',public_copies=len(refs),source_pins=len(source),device_calls=0)))
if __name__=='__main__':main()
