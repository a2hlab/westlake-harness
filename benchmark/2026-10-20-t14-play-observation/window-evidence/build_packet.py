#!/usr/bin/env python3
"""Closed T14 evidence packaging; default read-only, no device commands."""
import argparse,hashlib,importlib.util,json,re,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true');ap.add_argument('--main',type=Path,default=ROOT.parent/'westlake-harness');a=ap.parse_args()
 if not a.write:print('Read-only default; --write creates a new packet.');return
 base=Path.home()/'.local/share/westlake/toutiao-resume-20261020';raw=base/'t14-5cd-window-01';out=HERE/'packet';out.mkdir(exist_ok=False)
 def alias(t):
  for x,y in [(str(base),'BASE20'),(str(a.main.resolve()),'$WORKSPACES/westlake-harness'),(str(Path.home()),'$HOME')]:t=t.replace(x,y)
  return t
 def dump(n,v):
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
 refs=[]
 def cp(p,n):
  d=out/n;d.parent.mkdir(parents=True,exist_ok=True);b=p.read_bytes() if p.suffix=='.jpeg' else alias(p.read_text()).encode();d.write_bytes(b)
  refs.append({'raw_path':'BASE20/'+str(p.relative_to(base)),'raw_sha256':sha(p),'raw_bytes':p.stat().st_size,'public_path':n,'public_sha256':sha(d),'byte_exact':b==p.read_bytes()})
 close=json.loads((raw/'close.json').read_text());state=json.loads((raw/'window/state.json').read_text());profile=json.loads((raw/'profile.json').read_text())
 assert close['power_restored'] and close['board_lock_released'] and state['restored'] and not state['recovery_required'] and state['power_original']==[10000,10000]
 assert state['profile_sha256']==sha(raw/'profile.json') and (raw/'unlock.rc').read_text().strip()=='0'
 shots=[];verdicts=['LOCK_SCREEN','NEWS_FEED','VIDEO_TAB_COVER_AND_CONTROLS','SAME_COVER_UI_CHANGED','PLAY_CARD_REPOSITIONED_PAUSE_MUTED_CONTROLS','IDENTICAL_POST_PLAY_IMAGE']
 for i,row in enumerate(close['screenshots']):
  meta=raw/row['path'];rec=json.loads(meta.read_text());image=meta.parent/'screen.jpeg';assert row['sha256']==rec['sha256']==sha(image) and row['captured_at']==rec['captured_at']
  cp(image,f'screenshots/{i+1:02d}.jpeg');cp(meta,f'screenshots/{i+1:02d}.json')
  shots.append({'index':i+1,'source':row['path'],'sha256':sha(image),'captured_at':rec['captured_at'],'independent_visual_review':verdicts[i]})
 assert len(shots)==6 and shots[-1]['sha256']==shots[-2]['sha256']=='ac4cc7ed7b3ceda7cd646a6242954be34868c02a1eb4da9bce3c7cd46970f8ae'
 interval=shots[-1]['captured_at']-shots[-2]['captured_at']
 for n in ['close.json','profile.json','window/state.json','unlock.rc','holder.stdout','held-after.txt']:
  cp(raw/n,'evidence/'+n.replace('/','--'))
 # Copy only small outer action receipts; private command logs remain in the archive.
 for f in sorted(raw.glob('*outer-*')):
  if f.suffix in ['.rc','.stdout','.stderr']:cp(f,'outer-actions/'+f.name+('.txt' if f.suffix=='.stderr' else ''))
 actions=[]
 for f in sorted(raw.glob('*outer-*.argv.json')):
  stem=f.name.removesuffix('.argv.json');rc=int((f.parent/(stem+'.rc')).read_text());assert rc==0
  actions.append({'argv_path':'BASE20/'+str(f.relative_to(base)),'argv_sha256':sha(f),'rc':rc})
 delta_dir=next((raw/'window').glob('*-log-read'));delta=json.loads((delta_dir/'delta-result.json').read_text());recipe=delta['recipe']
 assert delta['status']=='BOUNDED_BYTES_COMPLETE' and delta['whole_window'] is False and recipe['truncated_by_cap'] and recipe['selected_bytes']==65536
 selected=delta_dir/'selected.raw';assert selected.stat().st_size==65536
 framed=[]
 for f in (delta_dir/'commands').glob('*.stdout.txt'):
  data=f.read_bytes();m=re.match(rb'T14_BEGIN_([0-9a-f]{32}):65536\n',data)
  if m:framed.append((f,data,m.group(1).decode()))
 assert len(framed)==1
 f,data,token=framed[0];command=f.with_name(f.name.removesuffix('.stdout.txt')+'.json');command_meta=json.loads(command.read_text())
 rc=command_meta['exit_code'];assert rc==0,command_meta.keys()
 spec=importlib.util.spec_from_file_location('t14_frame',a.main/'benchmark/2026-10-20-t14-play-observation/framing.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 decoded=mod.decode(data,65536,token,rc);assert decoded['status']=='BOUNDED_BYTES_COMPLETE' and decoded['payload']==selected.read_bytes()
 cp(delta_dir/'delta-result.json','evidence/delta-result.json')
 dump('bounded-log-check.json',{'status':'BOUNDED_BYTES_COMPLETE','frame_raw_path':'BASE20/'+str(f.relative_to(base)),'frame_sha256':sha(f),'command_sha256':sha(command),'host_rc':rc,'decoder_sha256':sha(a.main/'benchmark/2026-10-20-t14-play-observation/framing.py'),'selected_sha256':sha(selected),'selected_bytes':65536,'source_offset':recipe['source_offset'],'snapshot_end':recipe['snapshot_end'],'interval_bytes':recipe['snapshot_end']-recipe['source_offset'],'truncated_by_cap':True,'whole_interval_complete':False,'first_fatal':'UNKNOWN','payload_public':False})
 restore=next((raw/'window').glob('*-restore'));power=[]
 for f in (restore/'commands').glob('*.stdout.txt'):
  if 'Timeout=10000ms  OverrideTimeout=10000ms' in f.read_text(errors='replace'):power.append(f)
 assert len(power)==1;cp(power[0],'evidence/power-restored.txt')
 cmd=[sys.executable,str(a.main/'scripts/lab/run_facts.py'),str(raw/'window')];r=subprocess.run(cmd,capture_output=True);assert r.returncode==0
 (out/'facts.txt').write_bytes(r.stdout);(out/'facts.stderr.txt').write_bytes(r.stderr)
 dump('facts-receipt.json',{'argv':[alias(x) for x in cmd],'rc':r.returncode,'helper_sha256':sha(a.main/'scripts/lab/run_facts.py'),'schema_limit':'Producer emits screenshot.json, no record.json. Helper 0/0 is not the actual screenshot count. No synthetic records created.','actual_screenshot_receipts_verified':6,'liveness_counts':'UNKNOWN'})
 dump('screenshot-index.json',{'images':shots,'post_play_interval_seconds':interval,'post_play_identical_sha':True,'video':'NOT_VERIFIED','audio':'UNKNOWN'})
 sources=[]
 relbase=Path('benchmark/2026-10-20-t14-play-observation')
 source_paths=[relbase/n for n in ['observe.py','framing.py','source-pins.json']]
 source_paths.extend(Path(n) for n in json.loads((a.main/relbase/'source-pins.json').read_text()))
 for rel in source_paths:
  blob=(a.main/rel).read_bytes();commit=subprocess.check_output(['git','-C',str(a.main),'log','-1','--format=%H','--',str(rel)],text=True).strip();tracked=subprocess.check_output(['git','-C',str(a.main),'show',commit+':'+str(rel)]);assert tracked==blob
  sources.append({'path':str(rel),'commit':commit,'sha256':sha(a.main/rel)});dst=HERE/'.private/producer-snapshots'/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(blob)
 for n in ['t14_prepare.py','t14_run.py']:cp(base/n,'execution-source/'+n)
 dump('source-pins.json',{'sources':sources,'runtime_build':'NONE; no runtime change','scope':'Historical execution recipes and exact tracked sources, not reusable live authorization.'})
 index=[]
 for f in sorted(raw.rglob('*')):
  if f.is_file() and (f.name.endswith(('.argv.json','.rc','.rc.json')) or f.name.startswith('command-')):index.append({'path':'BASE20/'+str(f.relative_to(base)),'sha256':sha(f),'bytes':f.stat().st_size})
 dump('raw-command-index.json',index);dump('public-source-index.json',refs)
 dump('results.json',{'token':'t14-observation-packet','status':'CLOSED_UI_OBSERVED_VIDEO_NOT_VERIFIED','duration_seconds':close['duration_seconds'],'profile':profile,'used_actions':state['used'],'screenshots_from_original_receipts':6,'record_json_count':0,'facts_liveness':'UNKNOWN','video':'NOT_VERIFIED','audio':'UNKNOWN','post_play_identical_image_interval_seconds':interval,'first_fatal':'UNKNOWN_CAPPED_LOG_RANGE','power_restored':[10000,10000],'unlock_rc':0,'signals':0,'runtime_changes':0,'reboots':0,'attach':0,'later_native_supplement':'EXCLUDED; separately produced, no inferred contents','archive':'See archive/receipt.json for actual local/remote verification state','outer_actions':actions})
 (out/'README.md').write_text('''# T14: existing child UI observation, playback unverified

This 292.89-second window used the existing child1601/b7706984 and parent19163/b7265322 on boot0525bb05. Six original screenshot receipts and JPEG hashes are verified; all images were independently read. The first is the lock screen, followed by a news feed, video-tab cards and the post-play card. UI/control changes are visible, but the final two full JPEGs are byte-identical 39.63 seconds apart. This does not establish moving video or audible playback. A visible pause/mute control is not a playback verdict.

The saved frame is complete only for its selected65536 bytes. It covers the first64KiB of a30863473-byte log interval, not the complete interaction. Exact framing, host rc, payload SHA and post marker were checked using the original decoder. The first fatal event remains unknown; absence in this prefix cannot exclude later errors. Media-bearing selected bytes remain private.

The producer writes screenshot.json rather than record.json. The original run_facts output therefore reports zero recognized records; it is retained unchanged. Actual six-image evidence comes from the six original screenshot receipts. No synthetic record or alive counter is created. Original profile/process guards are separate evidence.

Restore returned rc0, original power Timeout/OverrideTimeout10000/10000 was read back, and unlock returned rc0. No runtime build/replacement, app signal, reboot or debugger attach occurred. This packet contains only this completed window, its exact historical wrappers and source references. Later native supplements are separate and are not claimed here. Complete raw command/output material is in the persistent private archive; no media URL/token is published.
''')
 print(json.dumps({'packet':'created','refs':len(refs),'screenshots':len(shots),'interval':interval,'device_calls':0}))
if __name__=='__main__':main()
