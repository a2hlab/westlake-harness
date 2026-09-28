"""VM: remove only B6's two mounts after verifying the current candidate hashes."""
from pathlib import Path
import json,sys
r=Path(__file__).resolve().parent;sys.path.insert(0,str(r.parent/'batch'));import bms_batch as b
out=Path.home()/'a2hlab/board/b6-rollback-first-5ea';out.mkdir(exist_ok=False)
d=json.loads((r/'deployment.json').read_text())
board=b.Board(d['serial'],'/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','cx-t0',out/'commands');board.ready();assert board.boot==d['boot_id']
_,current=board.shell('sha256sum /system/android/framework/framework.jar /system/android/framework/arm64/boot-framework.oat');assert [x.split()[0] for x in current.splitlines()]==[d['expected_files']['framework.jar'],d['expected_files']['boot-framework.oat']]
for pkg in ['org.wikipedia','com.example.helloworld']:
 _,dump=board.shell('bm dump -n '+pkg);uid=b.parse_bundle(dump,pkg)['uid'];assert b.cold_stop(board,pkg,uid,out,pkg)
_,after=board.shell(d['rollback']);assert [x.split()[0] for x in after.splitlines()]==[d['old_framework_hash'],'0ff275fa856c9a7e404b3e03460aa3b514268e9ee8a3910e0549f0750cc2d7c0','250958dc3f133b67fb38c5da3caf81714fd6958e2247556e327d917b1f0d3146']
b.save(r/'rollback-first.json',{'reason':'Full boot rebuild introduced an earlier InflaterInputStream SIGSEGV; no claim that Context guard ran','after':after,'vm_evidence':str(out),'boot_id':board.boot})
print('reverted B6 framework and boot cohort; B5 runtime retained')
