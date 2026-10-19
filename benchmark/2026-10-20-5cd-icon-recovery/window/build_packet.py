#!/usr/bin/env python3
"""Package completed T12 evidence locally; never issue device commands. Explicit --write only."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true');ap.add_argument('--main',type=Path,default=REPO.parent/'westlake-harness');a=ap.parse_args()
 if not a.write:print('Read-only default; --write creates a new packet.');return
 base=Path.home()/'.local/share/westlake/toutiao-resume-20261020';raw=base/'t12-5cd-window-01';out=HERE/'packet';out.mkdir(exist_ok=False)
 def alias(s):
  for x,y in [(str(base),'BASE20'),(str(a.main.resolve()),'$WORKSPACES/westlake-harness'),(str(Path.home()),'$HOME')]:s=s.replace(x,y)
  return s
 def dump(n,x):
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
 refs=[]
 def cp(rel,dst=None):
  p=raw/rel;d=out/(dst or rel);d.parent.mkdir(parents=True,exist_ok=True)
  data=p.read_bytes() if p.suffix=='.jpeg' else alias(p.read_text()).encode();d.write_bytes(data)
  refs.append({'raw_path':'BASE20/t12-5cd-window-01/'+rel,'raw_sha256':sha(p),'raw_bytes':p.stat().st_size,'public_path':str(d.relative_to(out)),'public_sha256':sha(d),'byte_exact':data==p.read_bytes()})
 visual={'prepare':'DESKTOP','icon':'IME_HOST','feed-check':'NEWS_FEED','video-tab':'VIDEO_COVER','video-late':'SAME_VIDEO_COVER_UI_CHANGED'}
 times={}
 for k,v in visual.items():
  rec=json.loads((raw/k/'record.json').read_text());shot=rec['screenshots'][0];assert shot['sha256']==sha(raw/k/'screen.jpeg');times[k]=shot['captured_at']
  cp(k+'/screen.jpeg','screenshots/'+k+'.jpeg');cp(k+'/record.json','records/'+k+'.json')
 for n in ['close.json','post-icon/events.log.stdout','post-icon/instance.txt.stdout','close-readonly/guardian-state.stdout','close-readonly/power.stdout','close-readonly/child-status.stdout','stderr-target/command.stdout','stderr-target/tail.argv.json','stderr-target/tail.rc','stderr-target/video-first-matches.rc','video-log/first-attempt-failure.json','video-log/second.argv.json','video-modules/roles.json','ui-identity.json','unlock.rc']:
  cp(n,'evidence/'+n.replace('/','--'))
 for phase in ['preflight','apply','stop','restore']:
  cp(phase+'/result.json','evidence/'+phase+'.json');cp(phase+'.rc','evidence/'+phase+'.rc')
  assert (raw/(phase+'.rc')).read_text().strip()=='0'
 pre=json.loads((raw/'preflight/result.json').read_text());rst=json.loads((raw/'restore/result.json').read_text());assert rst['old_controls_verified'] is True
 expected=dict(pre['pins']);expected.update(pre['old_controls_sha256']);found={}
 for f in sorted((raw/'restore').glob('*close-unchanged.stdout')):
  text=f.read_text();first=text.splitlines()[0].split();key=Path(first[1]).name
  key={'01_westlake_u13_toutiao.cfg':'cfg','run.sh':'run'}.get(key,key);assert first[0]==expected[key];assert re.search(r'T12_RC_[a-f0-9]+=0\s*$',text);found[key]=first[0]
 assert found==expected
 power=(raw/'close-readonly/power.stdout').read_text();assert 'Timeout=10000ms  OverrideTimeout=10000ms' in power and pre['power_original']==rst['power_original']=={'timeout':10000,'override':10000}
 dump('restoration-check.json',{'status':'MATCH','nine_pins':found,'power_original':pre['power_original'],'power_restored':rst['power_original'],'stop_rc':0,'restore_rc':0,'unlock_rc':int((raw/'unlock.rc').read_text()),'close_status':json.loads((raw/'close.json').read_text())['status'],'signals_to_parent_or_child':0,'note':'Exact temporary guardian was stopped; no app/parent signal. No runtime restoration or reboot was needed.'})
 events=(raw/'post-icon/events.log.stdout').read_text();assert events.index('t12_desktop_seen')<events.index('reentry_spawn_ok');assert 'child=31210 child_birth=7485570 parent=19163 parent_birth=7265322' in events
 maps=raw/'video-modules/01-maps.stdout';text=maps.read_text();assert text.endswith('T12_MODULE_OK\n') and 'ttmplayer' not in text
 tail=raw/'stderr-target/tail.stdout';assert tail.read_bytes().endswith(b'T12_LOG_OK\n');partial=raw/'stderr-target/video-first-matches.stdout';assert (raw/'stderr-target/video-first-matches.rc').read_text().strip()=='HOST_TIMEOUT8'
 dump('logging-boundaries.json',{'fd2':{'kind':'regular file','dev_inode':'66352:179838','path':'/data/service/el1/public/appspawnx/adapter_child_31210.stderr'},'tail':{'bytes':tail.stat().st_size,'sha256':sha(tail),'pre_and_post_guard_complete':True,'end_marker':'T12_LOG_OK'},'first_matches':{'bytes':partial.stat().st_size,'sha256':sha(partial),'host_rc':'HOST_TIMEOUT8','post_guard_complete':False,'scope':'partial unclosed capture; not complete failure scan'},'hilog':[{'attempt':1,'host_timeout_seconds':20,'stdout_preserved':False,'source':'video-log/first-attempt-failure.json'},{'attempt':2,'host_timeout':True,'stdout_preserved':False,'timeout_source':'outer report; only second.argv.json exists, no raw completion receipt'}],'maps':{'sha256':sha(maps),'complete_guard':True,'ttmplayer_mapped_pathname_seen':False,'scope':'pathname observation only; not proof of no loader attempt, execution or alternative mapping'},'privacy':'Full stderr, partial media output, maps and command receipts are private archive members; no media URL or token is published.'})
 cmd=[sys.executable,str(a.main/'scripts/lab/run_facts.py'),str(raw)];r=subprocess.run(cmd,capture_output=True);assert r.returncode==0
 (out/'facts.txt').write_bytes(r.stdout);dump('facts-receipt.json',{'argv':[alias(x) for x in cmd],'rc':r.returncode,'stdout_sha256':hashlib.sha256(r.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(r.stderr).hexdigest(),'helper_sha256':sha(a.main/'scripts/lab/run_facts.py')})
 assert b'TOTAL keys=5 screenshots_captured=5/5 alive_t5=0 alive_last=0 alive_unknown=5' in r.stdout
 # Source references are exact committed blobs, not copied sources.
 commit='2a5dfd11f6';full=subprocess.check_output(['git','-C',str(a.main),'rev-parse',commit],text=True).strip();pins=[]
 for n in ['tool.py','ui.py','derive.py','source-pins.json']:
  rel='benchmark/2026-10-20-5cd-icon-recovery/'+n;blob=subprocess.check_output(['git','-C',str(a.main),'show',full+':'+rel]);assert blob==(a.main/rel).read_bytes()
  pins.append({'path':rel,'commit':full,'sha256':hashlib.sha256(blob).hexdigest()})
 assert pins[0]['sha256'].startswith('ca8404') and pins[1]['sha256']=='0a52e80d975306b0abbbdcde9f4dfaa49bede133b87f8a30141b4f8ec7782601'
 dump('source-pins.json',{'commit':full,'files':pins,'runtime_build':'NONE; existing runtime unchanged','source_delivery':'Already tracked on MAIN; this packet does not duplicate source trees.'})
 # Raw command index records filenames/SHA/size, never media-bearing command text.
 idx=[]
 for f in sorted(raw.rglob('*')):
  if not f.is_file():continue
  if f.name.endswith(('.argv.json','.command.json','.rc','.rc.json','.error.txt')) or (f.name.startswith('command-') and f.suffix=='.json'):
   row={'path':str(f.relative_to(raw)),'sha256':sha(f),'bytes':f.stat().st_size}
   if f.name.endswith('.rc'):row['raw_rc']=f.read_text().strip()
   elif f.name.endswith('.rc.json'):row['raw_rc']=json.loads(f.read_text())
   idx.append(row)
 dump('raw-command-index.json',{'base':'BASE20/t12-5cd-window-01','files':idx,'missing':'Two hilog stdout streams were not saved by their callers; they cannot be recovered by archiving.'})
 dump('results.json',{'token':'t12-window-final-ready','status':'FEED_OBSERVED_TEMP_CONTROL_AND_POWER_RESTORED_VIDEO_NOT_PASSED','serial':pre['serial'],'boot':pre['boot'],'parent':{'pid':19163,'birth':7265322},'child':{'pid':31210,'birth':7485570},'lock_time':'2026-10-20T07:13:53+08:00','elapsed_to_unlock_seconds':528,'elapsed_source':'outer completion report; close.json separately records elapsed_before_unlock=527, retained unchanged','actual_icon_clicks':1,'video_tab_actions':1,'visuals':visual,'video_sample_interval_seconds':times['video-late']-times['video-tab'],'video':'same cover, UI changes; NOT_PASSED','audio':'UNKNOWN','module_roles_seen':4,'android_path_count':2,'ttmplayer':'No mapped pathname seen in the saved complete maps; no stronger negative claim.','restore':'stop/restore rc0; original Timeout/OverrideTimeout=10000/10000; seven old controls plus cfg/run unchanged','runtime_changes':0,'attach':0,'parent_child_signal_calls':0,'random_exit_diagnosis':'NOT_PERFORMED','remote_archive':'pending outer execution; local receipt separate'})
 dump('public-source-index.json',refs)
 (out/'README.md').write_text('''# T12 5cd: one icon launch reaches feed; video unproven

Unlike T11, the bounded temporary-awake attempt observed desktop before a real icon transition. Guardian events record desktop_seen then reentry_spawn_ok for child 31210/birth 7485570 under the preserved parent 19163/birth 7265322. Independent inspection confirms a news feed. Initial icon capture was host, not immediate feed.

Video-tab and late captures are 50.07 seconds apart. The cover image remains the same while navigation/comment UI changes. This is not dynamic video or audio acceptance. No runtime was built or changed, no debugger attached, and no parent or child was signalled.

Stop/restore returned 0. The seven historical control hashes plus cfg/run match preflight; power Timeout and OverrideTimeout both returned to their actual original 10000ms values. The temporary guardian was stopped. Outer reports unlock after 528 seconds from 07:13:53; original close.json retains its distinct pre-unlock elapsed value 527.

## Evidence limits

- Full guarded maps contain four observed module roles, with two libandroid paths. No libttmplayer mapped pathname appears. This does not establish that the player never attempted loading or had no alternative representation.
- fd2 is a verified regular file. The tail has pre/post identity and inode guards plus T12_LOG_OK. The 2,615,032-byte first-matches output timed out at 8 seconds without its post guard and is partial evidence only.
- Both hilog attempts timed out without saved stdout. The first has a failure receipt; the second has an argv and outer-reported timeout only. Missing output is not an empty successful log.
- `facts.txt` is the original helper output: five captured images, all liveness counters unknown. Event/process evidence is described separately and does not rewrite facts.

`source-pins.json` references already committed MAIN producers. `raw-command-index.json` and the archive member manifest pin original command/rc material; large stderr/maps and any media-bearing text remain private. `archive/receipt.json` distinguishes local packing from remote verification. Prior attempts and sources remain unchanged.
''')
 print(json.dumps({'packet':str(out),'references':len(refs),'source_pins':len(pins),'command_index_entries':len(idx),'device_calls':0}))
if __name__=='__main__':main()
