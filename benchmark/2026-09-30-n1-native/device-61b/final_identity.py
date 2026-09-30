#!/usr/bin/env python3
"""Read back exact U0 identities; lock release is recorded separately by Mac."""
from pathlib import Path
import sys,json,hashlib
R=Path(__file__).resolve().parent
sys.path.insert(0,'/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch')
import bms_batch as b
board=b.Board('61b0657200000000000000000324012c','/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','cx-t0',R/'final/commands');board.ready()
base=Path('/Users/zhaoyue/orca/workspaces/westlake-runtime-asset-fd-53f00423');expected=json.loads((base/'package.json').read_text())['live_hashes'];jar=json.loads((R/'jar/original.json').read_text());expected['/system/android/framework/oh-adapter-runtime.jar']=jar['sha256']
text=board.shell('sha256sum '+' '.join(expected))[1];actual={x.split()[1]:x.split()[0] for x in text.splitlines() if len(x.split())==2}
result={'boot_id':board.boot,'expected':expected,'actual':actual,'u0_restored':actual==expected and board.boot==jar['boot_id'],'lock_released':False}
b.save(R/'final-identity.json',result)
assert result['u0_restored'], 'U0 SHA/boot mismatch'
print('PASS U0 exact SHA and r17r overlay; boot unchanged')
