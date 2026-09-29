"""VM only: install a separate negative fixture, without modifying campaign APKs."""
from pathlib import Path
import sys,json
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root.parents[1]/'batch'));import bms_batch as b
f=json.loads((root/'fixture.json').read_text());pkg=f['package']
out=Path.home()/'a2hlab/board/b5-negative-install-5ea-attempt2';out.mkdir(exist_ok=False)
board=b.Board('5ea34a4500000000000000001123012c','/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','cx-t0',out/'commands');board.ready()
_,prior=board.shell('bm dump -n '+pkg,required=False)
assert 'failed to get information' in prior,prior
_,all_bundles=board.shell('bm dump -a');assert pkg not in all_bundles
remote='/data/local/tmp/b5-alias-20260928/negative.apk'
assert b.sha(Path(f['apk']))==f['sha256']
board.send(f['apk'],remote)
_,digest=board.shell('sha256sum '+remote);assert digest.split()[0]==f['sha256']
rc,installed=board.shell('bm install -p '+remote,required=False,timeout=180)
(out/'install.txt').write_text(installed);assert rc==0 and 'success' in installed.lower(),installed
_,bundle=board.shell('bm dump -n '+pkg);(out/'bundle.txt').write_text(bundle)
info=b.parse_bundle(bundle,pkg);assert info['queryable'] and info['desktop_activity']==f['alias'],info
prep=b.prepare_sandbox(board,pkg,info['uid'],out)
b.save(root/'installation.json',{'fixture':f,'bms':info,'sandbox':prep,'serial':board.serial,'boot_id':board.boot,'vm_evidence':str(out)})
print(info,flush=True)
