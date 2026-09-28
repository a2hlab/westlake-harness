"""Run control attempts sequentially on one held board, never a blocked-app shard."""
import json
import subprocess
import sys
from pathlib import Path
import t0_collect as c
import t0_batch

serial, run_id = sys.argv[1:]
if serial not in c.ALLOWED_SERIALS or not c.re.fullmatch(r'[a-zA-Z0-9_-]+', run_id):
    raise SystemExit('invalid serial/run_id')
c.SERIAL = serial
root = Path(__file__).resolve().parents[3]
manifest = json.loads((root / 'benchmark/2026-09-28-blocker-triage/manifest.json').read_text())
keys = [x['key'] for x in manifest['controls']] + ['markor']
base = Path.home() / 'a2hlab/ws' / ('out-appsweep-t0-' + run_id) / serial
base.mkdir(parents=True, exist_ok=True)
def notify(n, key, state):
    print(f'{serial} {n}/14 {key} {state}', flush=True)
    command = c.TOOLS + 'board_note.sh progress /Users/zhaoyue/orca/workspaces/westlake-harness/.octos/boards/app-lighting.md 10 cx-t0 ' + c.shlex.quote(f'2/5 {serial[:8]} 对照 {n}/14 {key} {state}; 只存取证，待外环读图')
    subprocess.run(['mac', 'bash', '-c', command], check=True)
raise SystemExit(t0_batch.run(keys, run_id, base, notify))
