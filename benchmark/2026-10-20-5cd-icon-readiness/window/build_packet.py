#!/usr/bin/env python3
"""Local evidence packaging only. Default/help never writes; --write creates a fresh packet."""
import argparse,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true');ap.add_argument('--main',type=Path,default=REPO.parent/'westlake-harness');a=ap.parse_args()
 if not a.write:print('No writes. Use --write to create a fresh packet.');return
 base=Path.home()/'.local/share/westlake/toutiao-resume-20261020';raw=base/'t11-5cd-window-01';out=HERE/'packet';out.mkdir(exist_ok=False)
 def alias(s):
  for x,y in [(str(base),'BASE20'),(str(a.main.resolve()),'$WORKSPACES/westlake-harness'),(str(Path.home()),'$HOME')]:s=s.replace(x,y)
  return s
 def dump(name,x):
  p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
 refs=[]
 def copy(src,dst,verbatim=False):
  p=out/dst;p.parent.mkdir(parents=True,exist_ok=True)
  data=src.read_bytes() if verbatim else alias(src.read_text()).encode();p.write_bytes(data)
  refs.append({'source':alias(str(src.resolve())),'raw_sha256':sha(src),'raw_bytes':src.stat().st_size,'public_path':dst,'public_sha256':sha(p),'byte_exact':src.read_bytes()==data})
 close=json.loads((raw/'close.json').read_text());assert close['status']=='NOT_READY_START_FAILED_BEFORE_CHILD' and close['elapsed_seconds']==366
 copy(raw/'close.json','close.json',True)
 visual={'actual-icon':'IME_HOST','focus-check':'LOCK_SCREEN','unlock-before':'LOCK_SCREEN','feed-check':'LOCK_SCREEN'}
 shots=[]
 for key,v in visual.items():
  p=raw/key/'screen.jpeg';r=json.loads((raw/key/'record.json').read_text());assert r['screenshots'][0]['sha256']==sha(p)
  copy(p,'screenshots/'+key+'.jpeg',True);copy(raw/key/'record.json','records/'+key+'.json')
  shots.append({'key':key,'sha256':sha(p),'visual':v,'review':'assistant inspected original image; not a feed or playback claim'})
 copy(raw/'icon/record.json','records/icon.json')
 for n in ['guardian-close.stdout','guardian-close.rc','icon.stderr','icon.rc','before.rc','after-ui.rc','unlock-launch.rc','unlock-launch.stdout','before-command.private.json','after-ui-command.private.json','collector-admission.json','launch-once.json']:
  copy(raw/n,'evidence/'+n.replace('.private','').replace('.stderr','.stderr.txt'))
 for phase in ['before-icon','after-ui']:copy(raw/phase/'result.json','evidence/'+phase+'.json',True)
 clickfiles=[]
 for phase in ['icon','actual-icon']:
  for p in (raw/phase/'commands').glob('*.json'):
   try:r=json.loads(p.read_text())
   except Exception:continue
   if any('uiInput click ' in str(x) for x in r.get('argv',[])):clickfiles.append((phase,p,r))
 assert len(clickfiles)==1 and clickfiles[0][0]=='actual-icon' and clickfiles[0][2]['exit_code']==0
 copy(clickfiles[0][1],'evidence/actual-icon-click-command.json')
 cmd=[sys.executable,str(a.main/'scripts/lab/run_facts.py'),str(raw)]
 r=subprocess.run(cmd,capture_output=True);assert r.returncode==0
 (out/'facts.txt').write_bytes(r.stdout);(out/'facts.stderr.txt').write_bytes(r.stderr)
 dump('facts-command.json',{'argv':[alias(x) for x in cmd],'rc':r.returncode,'helper_sha256':sha(a.main/'scripts/lab/run_facts.py')})
 assert b'TOTAL keys=5 screenshots_captured=4/4 alive_t5=0 alive_last=0 alive_unknown=5' in r.stdout
 sourcepins=[]
 for role,root,names in [('before-only-703',base/'t11-before-reviewed-70377471f',['core.py','collect.py','profile.json','admission.json']),('after-ui-r2',a.main/'benchmark/2026-10-20-5cd-icon-readiness',['core.py','collect.py','profile.json']),('outer-ui',base,['t11_ui.py','t11_unlock_launch.py'])]:
  for n in names:
   p=root/n;copy(p,'sources/'+role+'/'+n,True);sourcepins.append({'role':role,'name':n,'sha256':sha(p),'path':'sources/'+role+'/'+n})
 assert sha(a.main/'benchmark/2026-10-20-5cd-icon-readiness/collect.py')=='67ece6192f7eba020d5424fc9038df98965a2922ace788dd4e8a376b42aeb7cd'
 dump('source-provenance.json',{'runtime_source':'none; no new runtime or build','producer_sources':sourcepins,'qualification':'Historical execution snapshots, not general rerun entry points; old collector was before-only. New collector was after-ui. Source snapshots do not imply execution of unvisited branches.'})
 guardian=(raw/'guardian-close.stdout').read_text();assert 'START_FAILED' in guardian and 'parent=19163 parent_birth=7265322' in guardian and 'seq=0' in guardian and 'spawn_command_nonzero' in guardian
 dump('results.json',{'token':'t11-window-final-ready','status':close['status'],'boot':close['boot'],'serial':close['serial'],'locked_at':close['locked_at'],'closed_at':close['closed_at'],'elapsed_seconds':366,'actual_icon_clicks':1,'first_launch':{'rc':1,'selected':False,'clicked':False,'reason':'launcher focus rejected settings PID 8289; screenshot is lock screen'},'after_ui':{'collector_rc':2,'status':'NO_BUSINESS_CHILD'},'guardian':{'state':'START_FAILED','seq':0,'reason':'spawn_command_nonzero','parent':19163,'parent_birth':7265322,'child':'none','note':'parent identity comes from event line; state header parent=none is preserved'},'visuals':shots,'feed':'NOT_OBSERVED; terminal lockscreen cannot establish feed-failure causality','playback':'NOT_PASSED_NOT_TESTED','alive':'unknown from run_facts; no fabricated alive count','runtime_source_build':'NONE','deployment':False,'reboot':False,'attach':False,'got_read':False,'settings_mutation':False,'video_click':False,'random_exit_diagnosis':'NOT_PERFORMED','raw_archive':'separate archive/receipt.json; no remote success implied'})
 dump('public-source-index.json',refs)
 (out/'README.md').write_text('''# T11 5cd window: start failed before a business child

The initial launch was rejected by the launcher-focus guard before selecting or clicking an icon. The associated image is a lock screen, not an application failure. The outer operator then used the separately preserved unlock helper and clicked the exact host icon once on desktop page 9. Its first image shows **Westlake IME host**. The final image is another lock screen; it cannot establish why a feed was not observed.

The 366-second window closed at 06:43:18 on 2026-10-20. Both collectors reported no business child. The historical before-only collector returned 0; the fixed after-ui collector returned 2. Guardian raw evidence says `START_FAILED`, sequence 0, `spawn_command_nonzero`; its event identifies parent 19163/birth 7265322, while the state header retains `parent=none`. No child-exit cause is inferred.

`facts.txt` is the unmodified output of MAIN run_facts over the actual five record directories: four captured images, five unknown liveness results. The failed first launch has zero screenshots and is retained. Images were inspected independently: three lock screens and one host screen. There is no feed or playback success claim.

## Evidence and source boundary

- `close.json`, `results.json`, `evidence/`, `records/`, and `screenshots/` bind the actual window.
- `source-provenance.json` distinguishes the frozen 703 before-only producer from the fixed 67ece after-ui collector and the two historical outer UI scripts. Scripts are execution evidence, not portable authorization to replay this window.
- `public-source-index.json` binds original SHA/size and sanitized public bytes. Private paths use BASE20, WORKSPACES and HOME aliases. Original bytes and command stdout/stderr/rc remain in the raw archive.
- No runtime source/build, deployment, reboot, debugger attach, GOT read, settings change, or video tap occurred. UI wake, unlock swipe, desktop navigation, one icon click and screenshots did occur.
- Archive status is recorded separately; local packing must not be described as remote verification.

No frozen implementation, earlier review, API table, or device was changed by this evidence review. Startup-chain analysis belongs to the separately assigned lane.
''')
 print(json.dumps({'packet':str(out),'source_files':len(sourcepins),'public_refs':len(refs),'device_calls':0}))
if __name__=='__main__':main()
