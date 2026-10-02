"""Admission and infrastructure before experiment LOCK; cleanup uses its own lock."""
import argparse,importlib.util,json,os,subprocess,sys,uuid
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
sys.path.insert(0,str(H));sys.path.insert(0,str(R/'scripts/lab'))
import prepare as c,window_hook as hook,board_run

def prelock(plan,root):
 assert plan['execution_enabled'] is True,'outer approval pending; do not LOCK'
 assert board_run.precheck_problem(plan['offline_precheck']) is None,'offline hypothesis/evidence invalid'
 assert plan['package_manifest_sha256']==hook.composition()[0]['package_manifest_sha256']
 subprocess.run(['orb','-m','a2hlab','true'],check=True,timeout=25)
 subprocess.run(['orb','-m','a2hlab','python3','-c','import hashlib,pathlib,sys; assert hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest()==sys.argv[2]',str(c.PKG/'package.json'),c.gb.sha(c.PKG/'package.json')],check=True,timeout=25)
 targets=subprocess.run(['orb','-m','a2hlab','bash',str(c.lab_paths.tools()/'hdc_mac.sh'),'list','targets'],check=True,capture_output=True,text=True,timeout=25)
 assert c.SERIAL in targets.stdout.split(),'61b absent; no lock taken'
 # Exercise the same production VM tools (DEX/readelf/LLVM + shared scratch).
 spec=importlib.util.spec_from_file_location('promoted_infra',R/'benchmark/2026-10-02-u10-1-t8-rerun/promotion_dispatch.py');infra=importlib.util.module_from_spec(spec);spec.loader.exec_module(infra)
 tools=infra.vm_tools_preflight(c.W)
 root.mkdir(parents=True,exist_ok=True)
 hook.vm(['python3',str(H/'window_hook.py'),'--action','dry-run','--root',str(root)])
 c.save(root/'infra.json',{'orb':'PASS','hdc':'PASS','shared_package_sha':'PASS','vm_tools':tools,'device_write':False})

def cleanup_before_experiment(board,root):
 note=str(c.lab_paths.tools()/'board_note.sh')
 subprocess.run([note,'lock',board,c.SERIAL,'cx-t0','N11h pre-lock Toutiao guarded recovery'],check=True)
 held=subprocess.run([note,'held',c.SERIAL],check=True,capture_output=True,text=True).stdout.split()
 assert held and held[0]=='cx-t0'
 # Any ownership/hash/transport failure retains the recovery lock. Never pass it
 # off as the experimental lock or unlock a partially verified cleanup.
 hook.vm(['python3',str(H/'window_hook.py'),'--action','cleanup','--root',str(root)])
 subprocess.run([note,'unlock',board,c.SERIAL,'cx-t0'],check=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('plan',type=Path);p.add_argument('--detach',action='store_true',required=True);a=p.parse_args()
 plan=json.loads(a.plan.read_text());root=Path(os.path.expandvars(plan['out'])).parent
 assert not root.exists(),'fresh N11H_RUN_ID required'
 prelock(plan,root/'prelock')
 cleanup_before_experiment(os.path.expandvars(plan['board']),root/'residual-recovery')
 subprocess.run([sys.executable,str(c.M/'scripts/lab/board_run.py'),str(a.plan.resolve()),'--detach'],check=True)
if __name__=='__main__':main()
