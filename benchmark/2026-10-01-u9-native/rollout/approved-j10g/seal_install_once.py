"""Install-only supplemental probe under the existing board-run lock, between shards."""
import argparse, importlib.util, json, os, shlex, sys, time, uuid
from pathlib import Path
H=Path(__file__).resolve().parent
W=Path(os.environ['WORKSPACES']);M=W/'westlake-harness'
spec=importlib.util.spec_from_file_location('master_batch',M/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
p=argparse.ArgumentParser();p.add_argument('--serial',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
# Independent one-process-per-serial exclusion, in addition to the lane board lock.
proc_lock=b.serial_process_lock(a.serial)
if proc_lock is None:sys.exit('REFUSE: active bms_batch on serial; wait for shard to finish')
a.out.mkdir(parents=True,exist_ok=False)
board=b.Board(a.serial,shlex.join(['orb','-m','a2hlab','env','MAC_HOME='+str(Path.home()),str(W/'westlake-inputs/tools/hdc_mac.sh')]),str(W/'westlake-inputs/tools/board_note.sh'),'cx-t0',a.out/'commands')
board.ready();settings=b.preflight(board,a.out)
entry=b.load_apps(M/'benchmark/2026-09-28-bms-route-deploy/batch/apps.json',keys='fd-seal')[0]
app=b.resolve_input(Path.home()/'a2hlab/app-inputs',entry)
fp=b.runtime_fingerprint(board,a.out)
assert fp=='a8cb9a5a45a6',fp
remote='/data/local/tmp/u9-seal-'+uuid.uuid4().hex
board.shell('mkdir -p '+shlex.quote(remote));target=remote+'/original.apk';board.send(app['apk'],target)
_,text=board.shell('sha256sum '+shlex.quote(target));assert text.split()[0]==app['apk_sha256']
uninstall=b.uninstall_existing(board,app,a.out)
board.shell('hilog -r');rc,text=board.shell('bm install -p '+shlex.quote(target),required=False,timeout=180)
(a.out/'install.txt').write_text(text)
hrc,_=board.shell('hilog -x > '+shlex.quote(remote+'/install-hilog.txt')+' 2>&1',required=False)
if hrc==0:board.receive(remote+'/install-hilog.txt',a.out/'install-hilog.txt')
bc,body=board.shell('bm dump -n '+shlex.quote(app['package']),required=False);(a.out/'bundle.txt').write_text(body)
board.shell('rm -f '+shlex.quote(target))
receipt={'key':'fd-seal','serial':a.serial,'boot_id':board.boot,'runtime_fp':fp,'input_apk_sha256':app['apk_sha256'],'preflight':settings,'uninstall':uninstall,'install':{'return_code':rc,'success_text':b.bm_success(rc,text,'install')},'bms_query_return_code':bc,'install_only':True,'screenshots':'not requested','u8_input_comparison':'unknown: original U8 raw record/install.txt removed; run_index files_gone=true'}
# Store portable paths while preserving the raw transport logs separately.
body=json.dumps(receipt,indent=2).replace(str(W),'$WORKSPACES').replace(str(Path.home()),'$HOME')
(a.out/'receipt.json').write_text(body+'\n');print(json.dumps(receipt['install']))
