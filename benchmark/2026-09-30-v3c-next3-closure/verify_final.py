#!/usr/bin/env python3
"""Read-only final SHA/ledger check; Java overlay is an explicit variable."""
import argparse,hashlib,json,shlex,sys
from pathlib import Path
R=Path(__file__).resolve().parent
sys.path.insert(0,'/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch')
import bms_batch as b
p=argparse.ArgumentParser();p.add_argument('board',choices=['5cd','61b']);a=p.parse_args()
serial={'5cd':'5cd1e3dd00000000000000000923012c','61b':'61b0657200000000000000000324012c'}[a.board]
out=R/'final'
board=b.Board(serial,'/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','cx-t0',out/'commands');board.ready()
manifest=Path('/Users/zhaoyue/orca/workspaces/westlake-generation-v3c-candidate/package.json')
m=json.loads(manifest.read_text());expected=dict(m['live_hashes']);expected['/system/android/framework/oh-adapter-runtime.jar']='a5cbd8d77ad7cb1592db5d64f9ec1f7ce7da9732fdbe8c4b180c8fa1ea95c2e7'
actual={parts[1]:parts[0] for line in board.shell('sha256sum '+' '.join(map(shlex.quote,expected)))[1].splitlines() if len(parts:=line.split())==2}
if actual!=expected:raise RuntimeError('final live hashes differ')
ledger=Path('/Users/zhaoyue/orca/workspaces/westlake-generation-state')/serial/(board.boot+'-'+m['generation'][:12]+'.json');d=json.loads(ledger.read_text())
if d['status']!='active_verified' or d['package_sha256']!=hashlib.sha256(manifest.read_bytes()).hexdigest():raise RuntimeError('unexpected ledger')
actual_installer={parts[1]:parts[0] for line in board.shell('sha256sum '+' '.join(map(shlex.quote,d['installer_before'])))[1].splitlines() if len(parts:=line.split())==2}
if actual_installer!=d['installer_before']:raise RuntimeError('installer changed')
b.save(out/'receipt.json',{'serial':serial,'boot_id':board.boot,'package_sha256':d['package_sha256'],'live_sha256':actual,'installer_sha256':actual_installer,'status':d['status'],'passed':True,'java_overlay_separate':True})
print(a.board,'final verified',d['package_sha256'],flush=True)
