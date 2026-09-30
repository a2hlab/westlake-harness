#!/usr/bin/env python3
"""Restore only missing ZigZag sidecar mounts owned by the current ledger."""
from pathlib import Path
import argparse,json,shlex,sys
R=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--tag',default='restore-control-mounts');a=p.parse_args()
if '/' in a.tag or a.tag in ('.','..'):raise ValueError('invalid tag')
out=R/a.tag
sys.path.insert(0,'/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch')
import bms_batch as b
serial='61b0657200000000000000000324012c';board=b.Board(serial,'/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','cx-t0',out/'commands');board.ready()
ledger=Path('/Users/zhaoyue/orca/workspaces/westlake-generation-state')/serial/(board.boot+'-74d1d6d48210.json');d=json.loads(ledger.read_text());m=json.loads((Path(d['package_path'])/'package.json').read_text())
assert d['status']=='active_verified'
tops={x.split()[4]:x.split()[3] for x in board.shell('cat /proc/self/mountinfo')[1].splitlines()}
def sha(p):return board.shell('sha256sum '+shlex.quote(p))[1].split()[0]
rows=[]
for row in d['mounted']:
 if not row['source'].startswith('payload/zigzag/'):continue
 source=d['remote']+'/'+row['source'];target=row['target'];expected=m['files'][row['source']]
 assert target.startswith('/data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/')
 assert sha(source)==expected
 previous=tops.get(target)
 if previous is not None and previous!=source[len('/data'):]:raise RuntimeError('foreign mount: '+target)
 rc,raw=board.shell('if [ -f '+shlex.quote(target)+' ]; then sha256sum '+shlex.quote(target)+'; else echo ABSENT; fi')
 before=raw.split()[0]
 if before=='ABSENT':board.shell('set -C; : > '+shlex.quote(target)+' && chmod 0644 '+shlex.quote(target))
 if previous is None:board.shell('mount --bind '+shlex.quote(source)+' '+shlex.quote(target))
 assert sha(target)==expected
 rows.append(dict(row,previous_mount=previous,previous_sha256=before,restored_sha256=expected))
 b.save(out/'receipt.json',{'boot_id':board.boot,'rows':rows})
b.save(out/'receipt.json',{'boot_id':board.boot,'rows':rows})
print('verified restored sidecars',len(rows))
