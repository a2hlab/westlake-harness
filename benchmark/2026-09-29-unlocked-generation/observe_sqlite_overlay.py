#!/usr/bin/env python3
"""Authorized #68 r8b comparison; execute in VM, restore top layer in finally."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parents[1]
MASTER=R.parent/'westlake-harness'
sys.path.insert(0,str(MASTER/'benchmark/2026-09-28-bms-route-deploy/batch'))
import bms_batch as b
p=argparse.ArgumentParser();p.add_argument('--state',required=True,type=Path);p.add_argument('--run',required=True);a=p.parse_args()
assert all(c.isalnum() or c in '-_' for c in a.run)
s='5ea34a4500000000000000001123012c';d=json.loads(a.state.read_text());assert d['serial']==s and d['status']=='active_verified'
o=Path.home()/'a2hlab/board'/(a.run+'-overlay');o.mkdir(parents=True,exist_ok=False)
bd=b.Board(s,str(R.parent/'westlake-inputs/tools/hdc_mac.sh'),'mac '+str(R.parent/'westlake-inputs/tools/board_note.sh'),'cx-t0',o/'commands');bd.ready();assert bd.boot==d['boot_id']
target='/system/android/framework/oh-adapter-runtime.jar';base='250958dc3f133b67fb38c5da3caf81714fd6958e2247556e327d917b1f0d3146';expected='d5000c4e19e74e3ec7a72300ed425fa2c5ba521aa4b04cb6e688e165e6ba5554'
source=Path('/Users/zhaoyue/orca/workspaces/vm-copies/r8b-runtime-jar/oh-adapter-runtime.jar');assert b.sha(source)==expected
_,txt=bd.shell('sha256sum '+target);assert txt.split()[0]==base
_,txt=bd.shell('bm dump -n net.thunderbird.android');uid=b.parse_bundle(txt,'net.thunderbird.android')['uid']
assert b.cold_stop(bd,'net.thunderbird.android',uid,o)
remote='/data/local/tmp/'+a.run+'-overlay';bd.shell('mkdir -p '+remote);bd.send(source,remote+'/runtime.jar')
_,txt=bd.shell('sha256sum '+remote+'/runtime.jar');assert txt.split()[0]==expected
receipt={'generation':d['generation'],'boot_id':bd.boot,'baseline_jar':base,'test_jar':expected,'source':str(source)}
mounted=False
try:
 bd.shell('chmod 0644 '+remote+'/runtime.jar; chcon u:object_r:system_file:s0 '+remote+'/runtime.jar')
 bd.shell('mount --bind '+remote+'/runtime.jar '+target);mounted=True
 _,txt=bd.shell('sha256sum '+target+' /proc/'+str(d['parent_pid'])+'/root'+target);receipt['applied_sha']=txt;assert all(x.split()[0]==expected for x in txt.splitlines() if x.strip())
 subprocess.run([sys.executable,str(MASTER/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'),'--execute','--serial',s,'--lane','cx-t0','--keys','fd-android,ooniprobe','--hdc-cmd',str(R.parent/'westlake-inputs/tools/hdc_mac.sh'),'--lock-cmd','mac '+str(R.parent/'westlake-inputs/tools/board_note.sh'),'--out',str(Path.home()/'a2hlab/board'/a.run),'--run-id',a.run,'--reinstall','--hilog','20','--shots','5,20','--focus-check'],check=True)
finally:
 if mounted:
  _,text=bd.shell('bm dump -n net.thunderbird.android');uid=b.parse_bundle(text,'net.thunderbird.android')['uid']
  assert b.cold_stop(bd,'net.thunderbird.android',uid,o)
  _,text=bd.shell('bm dump -n org.openobservatory.ooniprobe');ooni_uid=b.parse_bundle(text,'org.openobservatory.ooniprobe')['uid']
  assert b.cold_stop(bd,'org.openobservatory.ooniprobe',ooni_uid,o)
  _,mounts=bd.shell('cat /proc/self/mountinfo');rows=[x for x in mounts.splitlines() if ' '+target+' ' in x];assert rows and remote[len('/data'):] in rows[-1]
  bd.shell('umount '+target)
  _,txt=bd.shell('sha256sum '+target+' /proc/'+str(d['parent_pid'])+'/root'+target);receipt['restored_sha']=txt;assert all(x.split()[0]==base for x in txt.splitlines() if x.strip())
 b.save(o/'receipt.json',receipt)
print(json.dumps(receipt,indent=2))
