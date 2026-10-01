"""U9 board-run hooks; system services are unchanged."""
import argparse,json,os,shlex,subprocess,sys,uuid
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[3]
sys.path.insert(0,str(R/'scripts/lab'))
import lab_paths,u7_executor as u,generation_bundle as gb,check_frozen as frozen
W=lab_paths.workspaces();M=lab_paths.harness()
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def package():return W/json.loads((H/'package.json').read_text())['bundle']
def service_hashes(serial=None):
 if serial is not None:
  return json.loads((R/'benchmark/2026-10-01-installation-chain-identity/current-u9.json').read_text())['boards'][serial]['services']
 return {p:v for p,v in json.loads((H/'smoke.json').read_text())['probe']['files'].items() if Path(p).name in {'libbms.z.so','libapk_installer.so'}}
def extended_refs(plan,serial):
 refs={k:list(v) for k,v in plan['reference_paths'].items()}
 refs['runtime']=sorted(set(refs['runtime']) | set(service_hashes(serial)))
 return refs

def service_gate():
 lines,bad=frozen.check_artifacts(frozen.active(frozen.load(M/'knowledge/frozen/frozen.json')),service_hashes(),'unchanged U8 installer')
 if bad:raise RuntimeError('\n'.join(lines))
def vm(args):
 env={'MAC_HOME':str(Path.home()),'LAB_HOME':os.environ['LAB_HOME'],'WORKSPACES':str(W)}
 command=' '.join('export '+k+'='+shlex.quote(v)+';' for k,v in env.items())+' '+shlex.join(['bash',str(R/'benchmark/2026-10-01-u7-executor/board61b/run-executor.sh'),*args])
 return subprocess.run(['orb','-m','a2hlab','bash','-lc',command]).returncode
def read_baseline(serial,root):
 plan=u.prepare(package(),W/'westlake-generation-u8-j9-t7e/native')
 io=u.DeviceIO(serial,'cx-t0',root/'before-device');got,absent=io.snapshot(sorted(plan['baseline']))
 diff={p:{'expected':v,'actual':got.get(p)} for p,v in plan['baseline'].items() if got.get(p)!=v}
 service=io.hashes(sorted(service_hashes(serial)))
 save(root/'before.json',{'boot_id':io.boot,'identities':len(got),'diff':diff,'absent':absent,'fingerprints':u.fingerprints({**got,**service},extended_refs(plan,serial)),'installer':service})
 assert not diff and not absent and service==service_hashes(serial)
def apply(serial,root):
 # Confirm the unchanged frozen system-service identities before any board access.
 service_gate()
 assert json.loads((package()/'bundle.json').read_text())['rollout_ready'] is True
 journal=root/'transaction/journal.json';assert not journal.exists()
 command='export MAC_HOME='+shlex.quote(str(Path.home()))+'; export WORKSPACES='+shlex.quote(str(W))+'; '+shlex.join(['python3',str(Path(__file__).resolve()),'--read-baseline','--serial',serial,'--out',str(root)])
 subprocess.run(['orb','-m','a2hlab','bash','-lc',command],check=True)
 return vm(['--apply','--package',str(package()),'--baseline-native',str(W/'westlake-generation-u8-j9-t7e/native'),'--oatdump',str(M/'scripts/lab/oatdump_remote.sh'),'--journal',str(journal),'--out',str(root/'transaction/apply.json'),'--serial',serial,'--lane','cx-t0'])
def finish(serial,root,planfile):
 journal=root/'transaction/journal.json';smoke=root/'runner/smoke/smoke-result.json'
 ok=smoke.is_file() and json.loads(smoke.read_text()).get('passed') is True
 if ok and planfile:
  import re
  plan=json.loads(planfile.read_text())
  partial=plan.get('partial_retention', {})
  approved_partial=(partial.get('approved_ack') == 'ACK(80) 2026-10-01T18:33:43+0800' and partial.get('outer_read_confirmed') is True)
  if approved_partial:
   facts=[f for f in (root/'runner').glob('*/*/*/facts.txt') if 'smoke' not in f.relative_to(root/'runner').parts]
   if not facts or not all(re.search(r'^TOTAL keys=([1-9]\d*) ', f.read_text(), re.M) for f in facts):ok=False
   save(root/'partial-retention.json', {'outer_read_confirmed':True, 'facts':[str(f) for f in facts], 'reason':'45-minute cutoff; remaining keys move to a later window'})
  else:
   for shard in plan['shards']:
    wanted=len(Path(os.path.expandvars(shard['keys_file'])).read_text().split())
    facts=list((root/'runner'/shard['name']).glob('*/*/facts.txt'))
    matches=[re.search(r'^TOTAL keys=(\d+) ',f.read_text(),re.M) for f in facts]
    if len(matches)!=1 or not matches[0] or int(matches[0].group(1))!=wanted:ok=False
 if ok:
  command='export MAC_HOME='+shlex.quote(str(Path.home()))+'; export WORKSPACES='+shlex.quote(str(W))+'; '+shlex.join(['python3',str(Path(__file__).resolve()),'--verify-final','--serial',serial,'--out',str(root)])
  return subprocess.run(['orb','-m','a2hlab','bash','-lc',command]).returncode
 if journal.exists():
  rc=vm(['--rollback','--journal',str(journal),'--out',str(root/('rollback-'+uuid.uuid4().hex+'.json')),'--serial',serial,'--lane','cx-t0'])
  if rc:return rc
 command='export MAC_HOME='+shlex.quote(str(Path.home()))+'; export WORKSPACES='+shlex.quote(str(W))+'; '+shlex.join(['python3',str(Path(__file__).resolve()),'--read-baseline','--serial',serial,'--out',str(root/'rollback-verified')])
 return subprocess.run(['orb','-m','a2hlab','bash','-lc',command]).returncode

def verify_final(serial,root):
 if sys.platform == 'darwin':
  command='export MAC_HOME='+shlex.quote(str(Path.home()))+'; export WORKSPACES='+shlex.quote(str(W))+'; '+shlex.join(['python3',str(Path(__file__).resolve()),'--verify-final','--serial',serial,'--out',str(root)])
  subprocess.run(['orb','-m','a2hlab','bash','-lc',command],check=True)
  return
 plan=u.prepare(package(),W/'westlake-generation-u8-j9-t7e/native');io=u.DeviceIO(serial,'cx-t0',root/'final-device')
 wanted={**plan['expected'],**service_hashes(serial)};got,absent=io.snapshot(sorted(wanted))
 diff={p:{'expected':v,'actual':got.get(p)} for p,v in wanted.items() if got.get(p)!=v}
 core_diff={p:{'expected':v,'actual':got.get(p)} for p,v in plan['expected'].items() if got.get(p)!=v}
 service_diff={p:{'expected':v,'actual':got.get(p)} for p,v in service_hashes(serial).items() if got.get(p)!=v}
 save(root/'final-u9.json',{'identities':len(got),'identity_assertions':len(plan['expected'])+len(service_hashes(serial)),'core_identities':len(plan['expected']),'service_assertions':len(service_hashes(serial)),'overlapping_service_paths':sorted(set(plan['expected']) & set(service_hashes(serial))),'core_diff':core_diff,'service_diff':service_diff,'diff':diff,'absent':absent,'fingerprints':u.fingerprints(got,extended_refs(plan,serial)),'boot_id':io.boot})
 assert not core_diff and not service_diff and not diff and not absent
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--serial',required=True,choices=sorted(lab_paths.boards('oh')));p.add_argument('--out',type=Path,required=True);p.add_argument('--plan',type=Path)
 g=p.add_mutually_exclusive_group(required=True)
 for name in ['apply','finish','read-baseline','verify-final','service-gate']:g.add_argument('--'+name,action='store_true')
 a=p.parse_args()
 if a.service_gate:service_gate()
 elif a.read_baseline:read_baseline(a.serial,a.out)
 elif a.verify_final:verify_final(a.serial,a.out)
 else:sys.exit(apply(a.serial,a.out) if a.apply else finish(a.serial,a.out,a.plan))
