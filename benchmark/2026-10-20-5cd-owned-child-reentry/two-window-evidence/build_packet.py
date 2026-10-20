#!/usr/bin/env python3
"""Package the two completed T13 windows. Explicit --write; no device calls."""
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true');ap.add_argument('--main',type=Path,default=REPO.parent/'westlake-harness');a=ap.parse_args()
 if not a.write: print('Read-only default; --write creates a fresh evidence packet.');return
 base=Path.home()/'.local/share/westlake/toutiao-resume-20261020';out=HERE/'packet';out.mkdir(exist_ok=False)
 def alias(t):
  for x,y in [(str(base),'BASE20'),(str(a.main.resolve()),'$WORKSPACES/westlake-harness'),(str(Path.home()),'$HOME')]:t=t.replace(x,y)
  return t
 def dump(n,v):
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
 refs=[]
 def cp(p,n):
  d=out/n;d.parent.mkdir(parents=True,exist_ok=True);data=p.read_bytes() if p.suffix=='.jpeg' else alias(p.read_text()).encode();d.write_bytes(data)
  refs.append({'raw_path':'BASE20/'+str(p.relative_to(base)),'raw_sha256':sha(p),'raw_bytes':p.stat().st_size,'public_path':n,'public_sha256':sha(d),'byte_exact':data==p.read_bytes()})
 def extract(p,n,lines):
  d=out/n;d.parent.mkdir(parents=True,exist_ok=True);d.write_text(alias('\n'.join(lines))+'\n')
  refs.append({'raw_path':'BASE20/'+str(p.relative_to(base)),'raw_sha256':sha(p),'raw_bytes':p.stat().st_size,'public_path':n,'public_sha256':sha(d),'byte_exact':False,'transformation':'technical line excerpt; full original archived'})
 restorations=[];command_index=[];source_records=[]
 for wid in ['01','02']:
  raw=base/('t13-5cd-window-'+wid);prefix='window'+wid
  pre=json.loads((raw/'preflight/result.json').read_text());rst=json.loads((raw/'restore/result.json').read_text())
  assert rst['old_controls_verified'] and pre['power_original']==rst['power_original']=={'timeout':10000,'override':10000}
  expected=dict(pre['pins']);expected.update(pre['old_controls_sha256']);found={}
  for p in sorted((raw/'restore').glob('*close-unchanged.stdout')):
   t=p.read_text();v,path=t.splitlines()[0].split();k={'01_westlake_u13_toutiao.cfg':'cfg','run.sh':'run'}.get(Path(path).name,Path(path).name)
   assert v==expected[k] and re.search(r'T13_RC_[a-f0-9]+=0\s*$',t);found[k]=v
  assert found==expected
  power=next((raw/'restore').glob('*-power.stdout'));assert 'Timeout=10000ms  OverrideTimeout=10000ms' in power.read_text()
  for phase in ['preflight','apply','stop','restore']+(['term-once'] if wid=='02' else []):
   cp(raw/phase/'result.json',prefix+'/'+phase+'.json')
   for ext in ['rc','stdout','stderr']:
    cp(raw/('outer-'+phase+'.'+ext),prefix+'/outer-'+phase+'.'+('stderr.txt' if ext=='stderr' else ext))
   if phase!='apply' or wid=='02':assert (raw/('outer-'+phase+'.rc')).read_text().strip()=='0'
  for n in ['close.json','unlock.rc','unlock.stderr','held.stdout','lock.rc']:
   cp(raw/n,prefix+'/'+n.replace('.stderr','.stderr.txt'))
  cp(power,prefix+'/power-restored.txt')
  stop=next((raw/'stop').glob('*guardian-stopped.stdout'));assert re.search(r'T13_RC_[a-f0-9]+=0\s*$',stop.read_text());cp(stop,prefix+'/guardian-stopped.txt')
  restorations.append({'window':wid,'nine_pins':found,'power':rst['power_original'],'stop_rc':0,'restore_rc':0,'saved_unlock_rc':int((raw/'unlock.rc').read_text())})
  for p in sorted(raw.rglob('*')):
   if p.is_file() and (p.name.endswith(('.argv.json','.command.json','.rc','.rc.json')) or p.name.startswith('command-')):
    row={'path':'BASE20/'+str(p.relative_to(base)),'sha256':sha(p),'bytes':p.stat().st_size}
    if p.name.endswith('.rc'):row['raw_rc']=p.read_text().strip()
    elif p.name.endswith('.rc.json'):row['raw_rc']=json.loads(p.read_text())
    command_index.append(row)
  source_records.append({'window':wid,'implementation_pins':json.loads((raw/'apply/result.json').read_text())['implementation_pins']})
  facts_root=raw if wid=='01' else raw/'ui'
  cmd=[sys.executable,str(a.main/'scripts/lab/run_facts.py'),str(facts_root)];r=subprocess.run(cmd,capture_output=True);assert r.returncode==0
  (out/prefix/'facts.txt').write_bytes(r.stdout);(out/prefix/'facts.stderr.txt').write_bytes(r.stderr)
  dump(prefix+'/facts-receipt.json',{'argv':[alias(x) for x in cmd],'rc':r.returncode,'helper_sha256':sha(a.main/'scripts/lab/run_facts.py'),'stdout_sha256':hashlib.sha256(r.stdout).hexdigest()})
 w1=base/'t13-5cd-window-01';w2=base/'t13-5cd-window-02'
 correction=json.loads((w1/'unlock-correction.json').read_text());assert correction['corrective_tool_exit_code']==0 and correction['held_after_rc']==1 and correction['held_after_stdout']==''
 cp(w1/'unlock-correction.json','window01/unlock-correction.json')
 for rel in ['apply/102-adopted.argv.json','apply/102-adopted.rc.json','apply/102-adopted.stdout','apply/102-adopted.stderr','adoption-guard-trace/rc']:
  cp(w1/rel,'window01/'+rel.replace('/','--').replace('.stderr','.stderr.txt'))
 trace=(w1/'adoption-guard-trace/stdout').read_text();assert 'GUARD_OK' in trace
 extract(w1/'adoption-guard-trace/stdout','window01/guard-excerpt.txt',[x for x in trace.splitlines() if 'GUARD_OK' in x or 't13_adopted' in x or '11520 ' in x])
 cp(w1/'apply-readonly/stdout','window01/apply-readonly.txt')
 for rel in ['after-term','desktop-event','after-icon','newchild-final','parent-final']:
  p=w2/rel/'stdout';assert (w2/rel/'rc').read_text().strip()=='0'
  txt=p.read_text();assert txt.rstrip().endswith('T13_READ_COMPLETE')
  lines=[x for x in txt.splitlines() if any(k in x for k in ['reason=','AWAITING_REENTRY','OLD_CHILD_ABSENT','T13_READ_COMPLETE','19163 (','1601 (','child=','parent=','birth=','seq=','mode='])]
  extract(p,'window02/'+rel+'-excerpt.txt',lines)
 assert 'OLD_CHILD_ABSENT' in (w2/'after-term/stdout').read_text()
 assert 'AWAITING_REENTRY' in (w2/'after-term/stdout').read_text()
 assert 't13_desktop_seen' in (w2/'desktop-event/stdout').read_text()
 for rel in ['newchild-identity.json','newchild-identity-verified.json','outer-capture-reopened-feed.rc','outer-capture-reopened-feed.stderr','outer-capture-reopened-feed-verified.rc','ui/launch-once.json']:
  cp(w2/rel,'window02/'+rel.replace('/','--').replace('.stderr','.stderr.txt'))
 verified=json.loads((w2/'newchild-identity-verified.json').read_text());assert verified['parent']=={'pid':19163,'ppid':1,'birth':7265322} and verified['child']=={'pid':1601,'ppid':19163,'birth':7706984}
 for key,verdict in [('desktop','DESKTOP'),('icon-once','IME_HOST'),('reopened-feed-verified','NEWS_FEED')]:
  rec=json.loads((w2/'ui'/key/'record.json').read_text());shot=w2/'ui'/key/'screen.jpeg';assert rec['screenshots'][0]['sha256']==sha(shot)
  cp(shot,'screenshots/'+key+'.jpeg');cp(w2/'ui'/key/'record.json','records/'+key+'.json')
 assert sha(w2/'ui/reopened-feed-verified/screen.jpeg')=='c78345d8d7e5b1d9177cd8d1b134e8eaa9ac2949fc982121716034f6c3977d96'
 assert (w2/'unlock.rc').read_text().strip()=='0'
 icon=json.loads((w2/'ui/icon-once/record.json').read_text());clicks=[r for r in icon['ui_calls'] if r['command'].startswith('uitest uiInput click')];assert len(clicks)==1 and clicks[0]['remote_rc']==0 and icon['clicked']
 # Archive exact producer blobs for each observed implementation SHA; current MAIN is not a substitute for window1.
 producer=Path('benchmark/2026-10-20-5cd-owned-child-reentry');pins=[]
 for version in source_records:
  for name,expected in version['implementation_pins'].items():
   rel=str(producer/name);commits=subprocess.check_output(['git','-C',str(a.main),'log','--format=%H','--',rel],text=True).splitlines();matched=None
   for c in commits:
    blob=subprocess.check_output(['git','-C',str(a.main),'show',c+':'+rel])
    if hashlib.sha256(blob).hexdigest()==expected:matched=(c,blob);break
   assert matched,('untracked producer',name,expected)
   c,blob=matched;dst=HERE/'.private/producer-snapshots'/version['window']/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(blob)
   pins.append({'window':version['window'],'path':rel,'commit':c,'sha256':expected})
 for name in ['t13_outer_run.py','t13_outer_run_r2.py','read_t13_r2.py']:cp(base/name,'execution-source/'+name)
 dump('source-pins.json',{'sources':pins,'runtime_build':'NONE; existing runtime unchanged','wrapper_scope':'Exact historical outer recipes, not reusable admission. window1 wrapper timeout95, window2 timeout150; sources preserved.'})
 dump('restoration-check.json',{'windows':restorations,'window01_unlock_correction':{'rc':0,'held_after_rc':1,'basis':'outer correction receipt, original failed unlock retained'},'window02_unlock_rc':0,'parent_preserved':verified['parent'],'runtime_changes':0,'reboots':0,'attach':0,'video_actions':0})
 dump('raw-command-index.json',{'files':command_index,'raw_location':'Full original commands/stdout/stderr/rc retained in archive; index contains hashes, not private command contents.'})
 dump('public-source-index.json',refs)
 dump('results.json',{'token':'t13-two-window-final','status':'SCOPED_CONTROLLED_EXIT_SINGLE_ICON_FEED_OBSERVED_AND_TEMP_CONTROLS_RESTORED','window01':{'outcome':'adoption wait expired before child TERM/icon','late_guard':'GUARD_OK','screenshots':0,'original_unlock_rc':2,'corrective_unlock_rc':0,'elapsed_before_unlock':185.38334584236145,'elapsed_at_corrective_check':correction['elapsed_at_check']},'window02':{'duration_seconds':json.loads((w2/'close.json').read_text())['duration_seconds'],'parent':verified['parent'],'old_child':{'pid':31210,'birth':7485570,'exit':'controlled TERM then read-only absence'},'new_child':verified['child'],'actual_icon_clicks':1,'visual':'desktop -> IME host -> verified news feed','capture_error':'wrong supplied parent PPID19133 refused; actual PPID1 verified before new capture','facts':'Original helper output kept, 3/3 captures, alive_unknown3; process identity separate'},'limits':['One controlled-exit/manual-icon trial, not random-exit stability, cross-boot durability or permanent sealing.','Video and audio not tested.','Temporary control stop plus original power/control restoration do not assert app child was stopped.'],'remote_archive':'See archive/receipt.json; local success is not remote success.'})
 (out/'README.md').write_text('''# T13: two windows, one controlled-exit/icon/feed observation

Window 1 failed before any child TERM or icon action: its five one-second adoption polls expired. The same guardian later produced adoption evidence and the exact read-only guard returned GUARD_OK. This is a wait-budget failure, not proof that adoption never happened. The original relative-board-path unlock failed (rc2); the separate corrective receipt reports absolute-path unlock rc0 and an empty held result. Both remain preserved.

Window 2 used the reviewed 30-second identity-bound adoption wait with a 60-second recovery reserve. Guardian 21339/b7690624 adopted existing child 31210/b7485570. One authorized TERM was followed by OLD_CHILD_ABSENT and AWAITING_REENTRY, then desktop_seen and one normal icon click. Parent 19163/b7265322 remained; the new child is 1601/b7706984. Independent screenshot inspection confirms desktop, initial IME host, then a genuine news feed (c78345d8...). The first final capture refused an incorrectly supplied parent PPID19133; the raw parent stat established PPID1 and a new tag captured successfully. That failed attempt is not overwritten.

Both temporary guardians were stopped with rc0. Original seven controls, cfg/run hashes and power Timeout/OverrideTimeout10000/10000 match the preflight evidence. Window 2 closed after 526.34 seconds and saved unlock rc0. This is one controlled-exit/manual-reentry observation, not a stability, cross-boot, video, audio or permanent-install result. No runtime build/replacement, reboot or debugger attach occurred.

The original run_facts outputs are retained: window1 zero records/screenshots; window2 UI three captures with all three liveness values unknown. Separate process-stat evidence does not rewrite those counters. The three historical outer Python recipes are preserved in execution-source; they require their original private context and must not be blindly rerun. Source-pins points to exact tracked producer versions. Full original commands, logs, failed receipts and source blobs belong to the private persistent archive; public-source-index binds every public copy or excerpt to its raw SHA.
''')
 print(json.dumps({'status':'LOCAL_PACKET_CREATED','public_raw_refs':len(refs),'command_index':len(command_index),'source_refs':len(pins),'device_calls':0}))
if __name__=='__main__':main()
