#!/usr/bin/env python3
"""Approved cutoff-only continuation glue around unchanged demo t4 preparation/runner.
Each fresh <=45/35 window restores Enforcing +319 before unlock; any refusal stops.
No reinstall, deployment, reboot or repair. Do not resume across a boot change.
"""
import argparse,importlib.util,json,os,subprocess,sys,time,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[2];WS=Path(os.environ.get('WORKSPACES',REPO.parent));BASE=REPO/'benchmark/2026-10-09-demo-baseline';SN='5cd1e3dd00000000000000000923012c';BOOT='a565a760-c10e-4ad4-80cd-23cd98165b28'
s=importlib.util.spec_from_file_location('post',BASE/'t4/run_post_reboot.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def note(text):subprocess.run([str(WS/'westlake-inputs/tools/board_note.sh'),'progress',str(WS/'westlake-harness/.octos/boards/app-lighting.md'),'91','cx-t0',text],check=True)
def read(p):return json.loads(p.read_text())
def records(root):
 found={}
 for p in root.glob('window-*/runner/group-*/*/*/*/record.json'):
  r=read(p)
  if r.get('finished_at'):
   assert r['key'] not in found;found[r['key']]=p
 return found

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--initial',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--wait-pid',type=int);ap.add_argument('--execute',action='store_true');a=ap.parse_args();assert a.execute
 a.out.mkdir(exist_ok=False);os.environ.update(WORKSPACES=str(WS),MAC_HOME=str(Path.home()))
 if a.wait_pid:
  while True:
   try:os.kill(a.wait_pid,0)
   except ProcessLookupError:break
   time.sleep(10)
 config=read(a.initial/'round.json');actual=records(a.initial)
 for window in config['windows']:
  w=m.expand(window);result=w.parent/'runner/board-run-result.json'
  if not result.exists():continue
  r=read(result);assert r.get('before_unlock')==0 and r.get('smoke')==0,'original window must cleanly finish'
  if r.get('stopped_after_shard'):
   log=w.parent/'runner'/(r['stopped_after_shard']+'.log');assert 'NEW-KEY CUTOFF:' in log.read_text(),'non-cutoff stopped shard: no automatic continuation'
  assert not any(read(p).get('status') in ('started','batch_interrupted') for p in (w.parent/'runner').glob('group-*/*/*/*/record.json')),'interrupted shard is not a cutoff'
 subprocess.run(['orb','-m','a2hlab','true'],check=True,timeout=20)
 for pin in config['bindings'].values():assert m.regress.sha(m.expand(pin['path']))==pin['sha256'],'input/tool drift: '+str(pin['path'])
 planroot=a.out/'prepared';c=m.prepare(m.expand(config['bindings']['manifest']['path']),m.expand(config['bindings']['tiers']['path']),m.expand(config['bindings']['install_index']['path']),planroot,config['boot_before_reboot'],m.expand(config['bindings']['smoke']['path']),count=20,serial=SN)
 apps=read(planroot/'batch-apps.json')['apps'];pending=[r for r in apps if r['key'] not in actual];pending=[r for r in pending if r['key']!='fd-organicmaps']+[r for r in pending if r['key']=='fd-organicmaps'];tiers={r['key']:r['screenshot_seconds'] for r in read(planroot/'shot-tiers.json')['apps']}
 templates=[read(m.expand(w)) for w in c['windows']];pins={k:v for t in templates for k,v in t.get('demo_ability_pins',{}).items()};c['windows']=[]
 for i in range(0,len(pending),20):
  selected=pending[i:i+20];d=a.out/('continuation-%02d'%(i//20+1));d.mkdir();p=json.loads(json.dumps(templates[0]));p.update(out=m.portable(d/'runner'),execution_enabled=False,why='Authorized v1 permissive preview continuation: only unmeasured canonical keys; same boot and same t4 driver',shards=[],demo_ability_pins={r['key']:pins[r['key']] for r in selected if r['key'] in pins})
  groups={}
  for r in selected:
   if r['key']!='fd-organicmaps':groups.setdefault((r['input_root'],tiers[r['key']]),[]).append(r['key'])
  group_rows=list(groups.items())
  for r in selected:
   if r['key']=='fd-organicmaps':group_rows.append(((r['input_root'],tiers[r['key']]),[r['key']]))
  for j,((root,tier),keys) in enumerate(group_rows):
   kf=d/('group-%02d-t%d.keys'%(j,tier));kf.write_text('\n'.join(keys)+'\n');p['shards'].append({'name':kf.stem,'manifest':m.portable(planroot/'batch-apps.json'),'input_root':root,'keys_file':m.portable(kf)})
  p['after_lock']=['python3',m.portable(HERE/'mode_hook.py'),'--round',m.portable(planroot),'--phase','apply','--out',m.portable(d/'mode-apply')];p['before_unlock']=['python3',m.portable(HERE/'mode_hook.py'),'--round',m.portable(planroot),'--phase','finish','--out',m.portable(d/'mode-finish')];m.save(d/'plan.json',p);c['windows'].append(m.portable(d/'plan.json'))
 c['window_bindings']=[m.pin(m.expand(w)) for w in c['windows']];c['bindings']['mode_hook']=m.pin(HERE/'mode_hook.py');m.save(planroot/'round.json',c);m.resolve_inputs(planroot)
 tools=planroot/'vm-tools';tools.mkdir();import shlex
 (tools/'hdc').write_text('#!/bin/sh\nexec orb -m a2hlab env WORKSPACES='+shlex.quote(str(WS))+' MAC_HOME='+shlex.quote(str(Path.home()))+' bash '+shlex.quote(str(WS/'westlake-inputs/tools/hdc_mac.sh'))+' "$@"\n');(tools/'hdc').chmod(0o755);os.environ['PATH']=str(tools)+os.pathsep+os.environ['PATH']
 # Persist exact remaining bookkeeping; no observed record is recaptured automatically.
 m.save(a.out/'continuation.json',{'initial_keys':sorted(actual),'remaining_keys':[r['key'] for r in pending],'windows':c['windows'],'same_boot':BOOT,'slots_enabled':False})
 for wp in c['windows']:
  path=m.expand(wp);p=read(path)
  for pin in c['bindings'].values():assert m.regress.sha(m.expand(pin['path']))==pin['sha256'],'fresh dispatch drift'
  subprocess.run(['orb','-m','a2hlab','true'],check=True,timeout=20)
  subprocess.run([sys.executable,str(BASE/'t4/round_identity.py'),'--round',str(planroot),'--out',str(path.parent/'pre-lock-identity')],check=True)
  note('宣布5cd v1 128续窗 '+path.parent.name+' <=45min/35min cutoff，未测键'+str(sum(len(m.expand(s['keys_file']).read_text().split()) for s in p['shards']))+'；同boot a565a760、同封存驱动，运行时0→finish1+319→UNLOCK，无Boat。')
  p['execution_enabled']=True;m.save(path,p)
  rc=subprocess.run([sys.executable,str(BASE/'t3/demo_board_run.py'),str(path)]).returncode;r=read(path.parent/'runner/board-run-result.json');assert rc==0 and r.get('before_unlock')==0 and r.get('smoke')==0,'failed window: no automatic further dispatch'
  expected={k for s in p['shards'] for k in m.expand(s['keys_file']).read_text().split()};found={read(x)['key'] for x in (path.parent/'runner').glob('group-*/*/*/*/record.json') if read(x).get('finished_at')};assert expected<=found,'cutoff again: preserve partial and stop'
  # Per-window facts use existing readout, only regular snapshots.
  subprocess.run([sys.executable,str(HERE/'readout.py'),'--round',str(a.out),'--window',path.parent.name,'--out',str(path.parent/'readout'),'--post'],check=True)
 m.save(a.out/'complete.json',{'regular_keys_initial':len(actual),'regular_keys_continuation':len(pending),'UI_verdict':'pending_outer_review','restored_enforcing_after_every_window':True})
if __name__=='__main__':main()
