#!/usr/bin/env python3
"""Resume authorized APK-only 5cd captures after a clean bounded-window cutoff.
Fresh plans reuse demo_board_run; any smoke/final/transport rejection stops.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
WS = Path(os.environ.get('WORKSPACES', HERE.parents[2]))
SERIAL = '5cd1e3dd00000000000000000923012c'

def read(p):
    return json.loads(Path(p).read_text())

def expand(p):
    return Path(os.path.expandvars(str(p).replace('$WORKSPACES', str(WS))))

def clean_cutoff(plan, result):
    """Partial rc=1 is resumable only when the batch itself records its cutoff.
    Infrastructure/cleanup/started records never use this exception.
    """
    name = result.get('stopped_after_shard')
    if not name or not result.get('stop_new_keys_at') or time.time() < result['stop_new_keys_at']:
        return False
    shard = next((r for r in result.get('shards', []) if r['name'] == name), {})
    if shard.get('rc') != 1:
        return False
    folder = expand(plan['out']) / name
    summaries = list(folder.glob('*/*/summary.json'))
    if len(summaries) != 1:
        return False
    summary = read(summaries[0])
    if not summary.get('stopped_at_new_key_deadline') or summary.get('batch_error'):
        return False
    rows = list(folder.glob('*/*/*/record.json'))
    return bool(rows) and all(read(p).get('finished_at') and
        read(p).get('status') not in ('started', 'batch_interrupted') for p in rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--round', type=Path, required=True)
    ap.add_argument('--first-plan', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--previous-plan', type=Path, action='append', default=[])
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--authorization', required=True)
    a = ap.parse_args()
    if not a.execute or not a.authorization.strip():
        ap.error('explicit execution and authorization required')
    cfg = read(a.round / 'round.json')
    if cfg['serial'] != SERIAL or any(v['enabled'] for v in cfg['special_slots'].values()):
        raise ValueError('5cd only; both special slots must be disabled')
    a.out.mkdir(exist_ok=False)
    os.environ.update(WORKSPACES=str(WS), MAC_HOME=str(Path.home()))
    os.environ['PATH'] = str((a.round / 'vm-tools').resolve()) + os.pathsep + os.environ['PATH']
    previous = [p.resolve() for p in a.previous_plan] + [a.first_plan.resolve()]
    result_path = expand(read(previous[0])['out']) / 'board-run-result.json'
    while not result_path.exists():
        if (HERE / 'STOP').exists():
            raise RuntimeError('host STOP requested; do not open continuation')
        time.sleep(5)
    note = WS / 'westlake-inputs/tools/board_note.sh'
    board = WS / 'westlake-harness/.octos/boards/app-lighting.md'
    identity = HERE.parent / '2026-10-09-demo-baseline/t4/round_identity.py'
    supervisor = HERE.parent / '2026-10-09-demo-baseline/t3/demo_board_run.py'
    for iteration in range(1, 12):
        if (HERE / 'STOP').exists():
            raise RuntimeError('host STOP requested; previous window evidence preserved')
        result = read(result_path)
        if result.get('before_unlock') != 0 or result.get('smoke') != 0 or (result.get('stopped_after_shard') and not clean_cutoff(read(previous[-1]), result)):
            raise RuntimeError('prior window rejection; do not take next lock')
        for _ in range(10):
            held = subprocess.run([str(note), 'held', SERIAL], capture_output=True, text=True)
            if held.returncode != 0 and not held.stdout.strip():
                break
            time.sleep(1)
        else:
            raise RuntimeError('board remains held; do not write')
        for binding in cfg['bindings'].values():
            if hashlib.sha256(expand(binding['path']).read_bytes()).hexdigest() != binding['sha256']:
                raise RuntimeError('dispatch input changed: ' + binding['path'])
        prepared = a.out / ('continuation-%02d' % iteration)
        cmd = [sys.executable, str(HERE / 'prepare_remaining.py'), '--round', str(a.round),
               '--out', str(prepared), '--keys-per-window', '64']
        for p in previous:
            cmd += ['--previous-plan', str(p)]
        subprocess.run(cmd, check=True)
        data = read(prepared / 'continuation.json')
        if not data['pending']:
            (a.out / 'complete.json').write_text(json.dumps({'regular_finished': len(data['finished']),
                'plans': [str(p).replace(str(WS), '$WORKSPACES') for p in previous],
                'UI_verdict': 'pending_outer_review'}, indent=2) + '\n')
            print('ALL 128 regular records finished; outer image review pending', flush=True)
            return 0
        subprocess.run(['orb', '-m', 'a2hlab', 'true'], timeout=20, check=True)
        subprocess.run([sys.executable, str(identity), '--round', str(a.round),
                        '--out', str(prepared / 'pre-lock-identity')], check=True)
        path = expand(data['plans'][0])
        plan = read(path)
        plan['execution_enabled'] = True
        path.write_text(json.dumps(plan, indent=2) + '\n')
        subprocess.run([str(note), 'progress', str(board), '91', 'cx-t0',
             '宣布5cd continuation-%02d <=45min/35min；仅未测key按root+shot档顺序launch-only，U13/Enforcing不换件；授权=' % iteration + a.authorization], check=True)
        with (prepared / 'runner.log').open('w') as log:
            rc = subprocess.run([sys.executable, str(supervisor), str(path)], stdout=log, stderr=subprocess.STDOUT).returncode
        result_path = expand(plan['out']) / 'board-run-result.json'
        if rc and not (result_path.is_file() and read(result_path).get('before_unlock') == 0 and clean_cutoff(plan, read(result_path))):
            raise RuntimeError('continuation supervisor failed; inspect final/lock disposition')
        previous.append(path)
        print('finished continuation', iteration, flush=True)
    raise RuntimeError('bounded continuation count exceeded; preserve evidence')

if __name__ == '__main__':
    raise SystemExit(main())
