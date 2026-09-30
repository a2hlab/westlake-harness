#!/usr/bin/env python3
"""Fresh-install the unchanged control APK, then restore its ledger-owned five binds."""
import json,shlex,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parent
sys.path.insert(0,'/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch')
import bms_batch as b
out=R/'zigzag-clean';out.mkdir(exist_ok=False)
board=b.Board('61b0657200000000000000000324012c','/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','cx-t0',out/'commands');board.ready()
entry=next(x for x in json.loads((R.parent/'controls.json').read_text())['apps'] if x['key']=='zigzag')
app=b.resolve_input(Path('/Users/zhaoyue/orca/workspaces/westlake-b90-controls-inputs'),entry)
remote='/data/local/tmp/cx-t0-asset-fd-zigzag.apk'
board.send(app['apk'],remote)
assert board.shell('sha256sum '+remote)[1].split()[0]==app['apk_sha256']
receipt={'boot_id':board.boot,'apk_sha256':app['apk_sha256'],'uninstall':b.uninstall_existing(board,app,out)}
rc,text=board.shell('bm install -p '+remote,required=False,timeout=180)
(out/'install.txt').write_text(text)
assert b.bm_success(rc,text,'install')
bundle=b.parse_bundle(board.shell('bm dump -n '+app['package'])[1],app['package'])
assert b.cold_stop(board,app['package'],bundle['uid'],out)
receipt['sandbox']=b.prepare_sandbox(board,app['package'],bundle['uid'],out)
receipt['installed_sha256']=board.shell('sha256sum /data/app/el1/bundle/public/'+app['package']+'/android/base.apk')[1].split()[0]
assert receipt['installed_sha256']==app['apk_sha256']
board.shell('rm -f '+remote)
subprocess.run([sys.executable,str(R/'restore_control_mounts.py'),'--tag','zigzag-clean-mounts'],check=True)
receipt['clean_install']=True
b.save(out/'receipt.json',receipt)
print('clean ZigZag plus original binds verified')
