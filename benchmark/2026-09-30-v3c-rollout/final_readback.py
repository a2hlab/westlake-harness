import json,shlex,sys
from pathlib import Path
R=Path(__file__).resolve().parent
sys.path.insert(0,'/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch')
import bms_batch as b
serial='5cd1e3dd00000000000000000923012c'
board=b.Board(serial,'/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','cx-t0',R/'final-readback-commands');board.ready()
if board.boot!='a42f2d6c-d29d-40aa-8145-51b4f85d0187':raise RuntimeError('boot changed')
p=Path('/Users/zhaoyue/orca/workspaces/westlake-generation-v3c-candidate/package.json')
if b.sha(p)!='668e4f7c74bfe635c57ca7133e1373acb0c675959d5953a20708e70293d27107':raise RuntimeError('manifest changed')
expected=json.loads(p.read_text())['live_hashes'];expected['/system/android/framework/oh-adapter-runtime.jar']='2b201bda4655fb36498d87b64c0389249b96e04a74f3e42567e5633f2a27bae1'
rc,text=board.shell('sha256sum '+' '.join(map(shlex.quote,expected)))
actual={line.split()[1]:line.split()[0] for line in text.splitlines()}
if rc or actual!=expected:raise RuntimeError('final SHA differs')
b.save(R/'final-readback.json',{'serial':serial,'boot_id':board.boot,'sha256_passed':True,'actual':actual,'external_jar':'original r17c'})
print('final declared SHA readback passed')
