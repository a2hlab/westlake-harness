#!/usr/bin/env python3
"""Install the authorized OONI acceptance app without changing APK or installer."""
import json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'benchmark/2026-09-28-bms-route-deploy/batch'))
import bms_batch as b
out=Path.home()/'a2hlab/board/b68-install-ooni-5ea';out.mkdir(exist_ok=True)
board=b.Board('5ea34a4500000000000000001123012c',str(R.parent/'westlake-inputs/tools/hdc_mac.sh'),'mac '+str(R.parent/'westlake-inputs/tools/board_note.sh'),'cx-t0',out/'commands');board.ready()
entry=b.load_apps(R/'benchmark/2026-09-28-bms-route-deploy/batch/apps.json',keys='ooniprobe')[0]
app=b.resolve_input(Path.home()/'a2hlab/app-inputs',entry)
_,before=board.shell('bm dump -n '+app['package']);(out/'before.txt').write_text(before)
installed = 'failed to get information' not in before
if installed: assert (out/'install.txt').read_text().strip() == 'install bundle successfully.', 'existing app not installed by this attempt'
installer='/system/lib64/libapk_installer.so';_,ih=board.shell('sha256sum '+installer);(out/'installer-before.txt').write_text(ih)
if not installed:
 remote='/data/local/tmp/b68-ooni-original.apk';board.send(app['apk'],remote)
 _,h=board.shell('sha256sum '+remote);assert h.split()[0]==app['apk_sha256']
 rc,text=board.shell('bm install -p '+remote,required=False,timeout=180);(out/'install.txt').write_text(text)
 assert b.bm_success(rc,text,'install'),text
_,bundle=board.shell('bm dump -n '+app['package']);(out/'bundle.txt').write_text(bundle)
parsed=b.parse_bundle(bundle,app['package']);b.prepare_sandbox(board,app['package'],parsed['uid'],out)
_,after=board.shell('sha256sum '+installer);assert after==ih
b.save(out/'result.json',{'input':app,'bms':parsed,'installer_sha256':ih,'boot_id':board.boot})
print(out,flush=True)
