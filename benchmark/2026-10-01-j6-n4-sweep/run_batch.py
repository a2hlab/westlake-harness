#!/usr/bin/env python3
"""Run the assigned J6+N4 shard with master batch and the original J3 key assignment."""
import argparse
from pathlib import Path
import shlex
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts/lab'))
import lab_paths

p = argparse.ArgumentParser()
p.add_argument('board', choices=['5ea', '61b'])
p.add_argument('run_id')
p.add_argument('--controls', action='store_true')
p.add_argument('--keys')
a = p.parse_args()
serial = {'5ea': '5ea34a4500000000000000001123012c', '61b': '61b0657200000000000000000324012c'}[a.board]
master = lab_paths.harness()
cmd = [sys.executable, str(master / 'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'),
       '--execute', '--serial', serial, '--lane', 'cx-t0',
       '--hdc-cmd', str(ROOT / 'benchmark/2026-09-30-n3-61b/transport/hdc_mac.sh'),
       '--lock-cmd', 'mac ' + shlex.quote(str(lab_paths.tools() / 'board_note.sh')),
       '--out', str(HERE / 'runs'), '--run-id', a.run_id,
       '--hilog', '20', '--shots', '5,20', '--focus-check']
if a.controls:
    cmd += ['--manifest', str(ROOT / 'benchmark/2026-09-30-n3-61b/controls.json'),
            '--input-root', str(lab_paths.workspaces() / 'westlake-b90-controls-inputs'), '--launch-only']
    if a.keys: cmd += ['--keys', a.keys]
else:
    keys = a.keys or (master / 'benchmark/2026-09-30-j3-u3-sweep' / ('keys-' + a.board + '.txt')).read_text().strip()
    cmd += ['--manifest', str(HERE / 'cohort-j3.json'), '--keys', keys, '--reinstall']
raise SystemExit(subprocess.call(cmd))
