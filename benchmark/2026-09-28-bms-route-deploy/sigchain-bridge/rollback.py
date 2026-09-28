"""VM only: verify candidate and remove only the B6 libsigchain mount."""
from pathlib import Path
import sys,json
r=Path(__file__).resolve().parent;sys.path.insert(0,str(r.parent/'batch'));import bms_batch as b
out=Path.home()/'a2hlab/board/b6-musl-rollback-5ea';out.mkdir(exist_ok=False)
d=json.loads((r/'deployment.json').read_text());g=json.loads((r/'symbol-gate.json').read_text())
board=b.Board(d['serial'],'/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','cx-t0',out/'commands');board.ready();assert board.boot==d['boot_id']
_,sha=board.shell('sha256sum '+d['target']);assert sha.split()[0]==g['new_sha256']
for pkg in ['org.wikipedia','com.example.helloworld','com.a2hlab.bridge.zigzag']:
 _,dump=board.shell('bm dump -n '+pkg);assert b.cold_stop(board,pkg,b.parse_bundle(dump,pkg)['uid'],out,pkg)
board.shell(d['rollback']);_,after=board.shell('sha256sum '+d['target']);assert after.split()[0]==g['old_sha256'];b.save(r/'rollback.json',{'after':after,'boot_id':board.boot,'vm_evidence':str(out)})
