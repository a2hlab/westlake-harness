"""U9 board-run hooks; system services are unchanged."""
import argparse,json,os,shlex,subprocess,sys,uuid
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[2]
sys.path.insert(0,str(R/'scripts/lab'))
import lab_paths,u7_executor as u,generation_bundle as gb,check_frozen as frozen
W=lab_paths.workspaces();M=lab_paths.harness()
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def package():return W/json.loads((H/'package.json').read_text())['bundle']
def service_hashes():
 return {p:v for p,v in json.loads((H/'smoke.json').read_text())['probe']['files'].items() if Path(p).name in {'libbms.z.so','libapk_installer.so'}}
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
 service=io.hashes(sorted(service_hashes()))
 save(root/'before.json',{'boot_id':io.boot,'identities':len(got),'diff':diff,'absent':absent,'fingerprints':u.fingerprints(got,plan['reference_paths']),'installer':service})
 assert not diff and not absent and service==service_hashes()
def apply(serial,root):
 # Confirm the unchanged frozen system-service identities before any board access.
 service_gate()
 assert json.loads((package()/'bundle.json').read_text())['rollout_ready'] is True
 journal=root/'transaction/journal.json';assert not journal.exists()
 command='export MAC_HOME='+shlex.quote(str(Path.home()))+'; export WORKSPACES='+shlex.quote(str(W))+'; '+shlex.join(['python3',str(Path(__file__).resolve()),'--read-baseline','--serial',serial,'--out',str(root)])
 subprocess.run(['orb','-m','a2hlab','bash','-lc',command],check=True)
 return vm(['--apply','--package',str(package()),'--baseline-native',str(W/'westlake-generation-u8-j9-t7e/native'),'--oatdump',str(M/'scripts/lab/oatdump_remote.sh'),'--journal',str(journal),'--out',str(root/'transaction/apply.json'),'--serial',serial,'--lane','cx-t0'])
def finish(serial,root):
 journal=root/'transaction/journal.json';smoke=root/'runner/smoke/smoke-result.json'
 ok=smoke.is_file() and json.loads(smoke.read_text()).get('passed') is True
 if ok:
  command='export MAC_HOME='+shlex.quote(str(Path.home()))+'; export WORKSPACES='+shlex.quote(str(W))+'; '+shlex.join(['python3',str(Path(__file__).resolve()),'--verify-final','--serial',serial,'--out',str(root)])
  return subprocess.run(['orb','-m','a2hlab','bash','-lc',command]).returncode
 if journal.exists():
  rc=vm(['--rollback','--journal',str(journal),'--out',str(root/('rollback-'+uuid.uuid4().hex+'.json')),'--serial',serial,'--lane','cx-t0'])
  if rc:return rc
 command='export MAC_HOME='+shlex.quote(str(Path.home()))+'; export WORKSPACES='+shlex.quote(str(W))+'; '+shlex.join(['python3',str(Path(__file__).resolve()),'--read-baseline','--serial',serial,'--out',str(root/'rollback-verified')])
 return subprocess.run(['orb','-m','a2hlab','bash','-lc',command]).returncode

def verify_final(serial,root):
 plan=u.prepare(package(),W/'westlake-generation-u8-j9-t7e/native');io=u.DeviceIO(serial,'cx-t0',root/'final-device')
 wanted={**plan['expected'],**service_hashes()};got,absent=io.snapshot(sorted(wanted))
 diff={p:{'expected':v,'actual':got.get(p)} for p,v in wanted.items() if got.get(p)!=v}
 save(root/'final-u9.json',{'identities':len(got),'diff':diff,'absent':absent,'fingerprints':u.fingerprints(got,plan['reference_paths']),'boot_id':io.boot})
 assert not diff and not absent
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--serial',required=True,choices=sorted(lab_paths.boards('oh')));p.add_argument('--out',type=Path,required=True)
 g=p.add_mutually_exclusive_group(required=True)
 for name in ['apply','finish','read-baseline','verify-final','service-gate']:g.add_argument('--'+name,action='store_true')
 a=p.parse_args()
 if a.service_gate:service_gate()
 elif a.read_baseline:read_baseline(a.serial,a.out)
 elif a.verify_final:verify_final(a.serial,a.out)
 else:sys.exit(apply(a.serial,a.out) if a.apply else finish(a.serial,a.out))
