"""N11d single-child window: guarded baseline, continuous capture, rollback to U9."""
import argparse, hashlib, json, os, shlex, subprocess, sys, time
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
sys.path.insert(0,str(R/'scripts/lab'))
import lab_paths, deployment_native_gate
W=lab_paths.workspaces();M=lab_paths.harness()
SHA='69598037a0dbb79b82ddee0f7415784643510c6583c6dff736b655a8401e0f4f'
CHILD='/system/lib64/appspawn/libwestlake_android_child.z.so'

def save(path, data):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2)+'\n')

def verify(serial, root):
 command=['orb','-m','a2hlab','env','MAC_HOME='+str(Path.home()),'WORKSPACES='+str(W),'python3',str(R/'benchmark/2026-10-01-u9-native/rollout/approved-j10g/native_window.py'),'--verify-final','--serial',serial,'--out',str(root)]
 subprocess.run(command,check=True)


def sweep(serial,root,rollback=False):
 command=[sys.executable,str(H/'sweep_diagnostic.py'),'--serial',serial,'--lane','cx-t0','--bind',str(W/'westlake-n11d-probe-build/candidate/libwestlake_android_child.z.so')+':'+CHILD,'--out',str(root/'deploy')]
 if rollback:
  command+=['--rollback-only','--rollback-runtime-fp','565fc6fdc116','--rollback-boot-fp','4db882a81732']
 else:command+=['--no-run','--no-rollback']
 return subprocess.run(command).returncode


def stop_capture(root):
 cap=root/'capture'
 if not cap.exists():return
 (cap/'stop.flag').write_text(str(time.time()))
 for _ in range(100):
  if (cap/'done.json').exists():return
  time.sleep(.2)
 raise RuntimeError('collector did not stop; retain lock')


def approved_package():
 package=W/'westlake-generation-n11d-child-u9-69598037'
 report=json.loads((H/'approved-production-dry-run.json').read_text())
 assert report.get('gates_passed') and report.get('deployable'), 'production dry-run not deployable'
 assert report['bundle_sha256']==hashlib.sha256((package/'bundle.json').read_bytes()).hexdigest(), 'bundle changed after dry-run'
 return package


def apply(serial,root):
 assert serial=='5ea34a4500000000000000001123012c'
 assert not (root/'deploy').exists(), 'fresh output required'
 assert hashlib.sha256((W/'westlake-n11d-probe-build/candidate/libwestlake_android_child.z.so').read_bytes()).hexdigest()==SHA
 # No board command before the trusted native admission check.
 ticket=deployment_native_gate.check(approved_package()/'native')
 save(root/'native-admission.json',ticket)
 verify(serial,root/'baseline')
 capture=root/'capture'
 with (root/'collector.log').open('w') as log:
  proc=subprocess.Popen([sys.executable,str(H/'collector.py'),'--serial',serial,'--root',str(capture)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 save(root/'collector-process.json',{'pid':proc.pid})
 for _ in range(300):
  if (capture/'ready.json').exists():break
  if proc.poll() is not None:raise RuntimeError('collector failed before apply')
  time.sleep(.2)
 else:raise RuntimeError('collector did not become ready')
 deployment_native_gate.assert_unchanged(ticket)
 rc=sweep(serial,root)
 save(root/'candidate-interval.json',{'apply_return_epoch':time.time(),'return_code':rc,'child_sha256':SHA})
 return rc


def finish(serial,root):
 stop_capture(root)
 if (root/'deploy/deploy-receipt.json').exists():
  rc=sweep(serial,root,True)
  if rc:return rc
 verify(serial,root/'restored-u9')
 # Recovery evidence must use the extended installation-chain fingerprint.
 smoke=[sys.executable,str(M/'scripts/lab/activation_smoke.py'),'--serial',serial,'--lane','cx-t0','--spec',str(H/'restored-smoke.json'),'--out',str(root/'restored-smoke')]
 return subprocess.run(smoke).returncode


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--serial',required=True);p.add_argument('--root',type=Path,required=True);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--apply',action='store_true');g.add_argument('--finish',action='store_true');a=p.parse_args()
 a.root.mkdir(parents=True,exist_ok=True)
 raise SystemExit(apply(a.serial,a.root) if a.apply else finish(a.serial,a.root))
