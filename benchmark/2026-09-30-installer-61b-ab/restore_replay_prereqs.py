#!/usr/bin/env python3
"""Restore only previously declared ZigZag files missing after reboot, using original staged bytes."""
from pathlib import Path
import json,sys,shlex
R=Path(__file__).resolve().parent
sys.path.insert(0,'/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch')
import bms_batch as b
original=json.loads((R/'original.json').read_text());state=json.loads(Path(original['ledger']).read_text());m=json.loads((Path(original['package_path'])/'package.json').read_text())
board=b.Board(original['serial'],'/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','cx-t0',R/'replay-prereqs/commands');board.ready();rows=[];q=shlex.quote
for row in m['mounts']:
 if not row['source'].startswith('payload/zigzag/'):continue
 target=row['target'];rc,_=board.shell('test -e '+q(target),required=False)
 if rc==0:continue
 assert target.startswith('/data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/')
 source=state['remote']+'/'+row['source'];expected=m['files'][row['source']]
 assert board.shell('sha256sum '+q(source))[1].split()[0]==expected
 board.shell('test ! -e '+q(target)+' && cp -p '+q(source)+' '+q(target)+' && chmod 0644 '+q(target))
 assert board.shell('sha256sum '+q(target))[1].split()[0]==expected
 rows.append({'target':target,'before':'absent','source':source,'sha256':expected})
b.save(R/'replay-prereqs/receipt.json',{'boot_id':board.boot,'restored':rows});print('restored',len(rows),'original declared files')
