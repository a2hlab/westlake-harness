"""Stage A observation hooks; never admit promotion or own a device transaction."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import process_selftest

HERE = Path(__file__).resolve().parent
W = HERE.parents[2]
MASTER = W / 'westlake-harness'


def expand(value):
    os.environ.setdefault('WORKSPACES', str(W))
    return os.path.expanduser(os.path.expandvars(str(value)))


def ack(plan, body):
    # Board append is a Mac-side operation. Device capture below remains in VM.
    cmd = ['bash', str(MASTER/'scripts/lab/board_append.sh'), expand(plan['board']),
           f'ACK({plan["entry"]} observed): {plan["lane"]} {plan["serial"]} {body}']
    if sys.platform != 'darwin':
        cmd = ['mac', *cmd]
    subprocess.run(cmd, check=True)


def assess(plan, root, destination, name):
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = process_selftest.report(root)
    except Exception as exc:
        data = {'runs': [], 'run_count': 0, 'passed': False, 'unknown_runs': 1,
                'selftest_error_count': 0, 'badtag_count': 0, 'probe_error_count': 0, 'error_count': 0, 'assessment_error': str(exc)}
    destination.write_text(json.dumps(data, indent=2)+'\n')
    problems = []
    for run in data['runs']:
        if run['status'] == 'unknown':
            problems.append({'record': run['record'], 'key': run['key'], 'status': 'unknown',
                             'processes': run['processes'], 'complete_hilog': run['complete_hilog']})
        for pid, row in run['processes'].items():
            if row['status'] == 'unknown' and run['status'] != 'unknown':
                problems.append({'record': run['record'], 'pid': pid, 'status': 'unknown'})
            for event in process_selftest.errors(row):
                problems.append({'record': run['record'], 'key': run['key'], 'pid': pid, **event})
    if not data['runs']:
        problems.append({'status': 'unknown', 'reason': data.get('assessment_error', 'no records')})
    ack(plan, f'{name} process_selftest report={destination}; '
              f'selftest_error={data["selftest_error_count"]}, badtag={data["badtag_count"]}, '
              f'probe_error={data["probe_error_count"]}, total_error={data["error_count"]}, unknown={data["unknown_runs"]}; '
              f'issues={json.dumps(problems, ensure_ascii=False)}; record-only,继续观察,finish无条件执行')
    print(json.dumps(data, indent=2))
    # Verdict REJECT/unknown is recorded, not propagated to the window runner.
    return data


def capture_command(plan, obs, out, cutoff):
    command = ['python3', str(MASTER/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'),
               '--execute', '--serial', plan['serial'], '--lane', plan['lane'],
               '--manifest', expand(obs['manifest']), '--input-root', os.path.expandvars(obs['input_root']),
               '--keys', obs['key'], '--reinstall', '--wait', '95', '--hilog', '95',
               '--shots', '20,45,90', '--out', str(out),
               '--hdc-cmd', str(W/'westlake-inputs/tools/hdc_mac.sh'),
               '--lock-cmd', 'mac '+str(W/'westlake-inputs/tools/board_note.sh'),
               '--stop-new-keys-at', str(cutoff)]
    # ~ input root must resolve in the VM, as in the 01:31 validated window.
    if sys.platform == 'darwin':
        return ['orb', '-m', 'a2hlab', 'env', 'WORKSPACES='+str(W),
                'MAC_HOME='+str(Path.home()), *command]
    return command


def longwait(plan, root, cutoff):
    if plan.get('execution_enabled') is not True or not plan.get('bundle_sha256'):
        raise ValueError('disabled/unbound U13 draft: capture refused')
    spec = json.loads(Path(expand(plan['longwait_observation'])).read_text())
    if spec['serial'] != plan['serial']:
        raise ValueError('auxiliary serial differs from parent window')
    result = []
    for obs in spec['observations']:
        out = root/'additional'/obs['key']
        if time.time() >= cutoff:
            row = {'key': obs['key'], 'status': 'unknown', 'reason': '35-minute new-key cutoff'}
            ack(plan, 'longwait unmeasured '+json.dumps(row))
            result.append(row)
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        with (out.parent/(obs['key']+'.log')).open('w') as log:
            rc = subprocess.run(capture_command(plan, obs, out, cutoff),
                                stdout=log, stderr=subprocess.STDOUT).returncode
        assess(plan, out, root/'selftest'/('longwait-'+obs['key']+'.json'), 'longwait-'+obs['key'])
        keys = {p.parent.name for p in out.glob('*/*/*/record.json')
                if json.loads(p.read_text()).get('status') in {'captured','foreground_unconfirmed','app_failed'}}
        wrapped = obs['key'] in keys
        result.append({'key': obs['key'], 'rc': rc, 'wrapped': wrapped, 'out': str(out)})
        (root/'longwait-result.json').write_text(json.dumps(result, indent=2)+'\n')
        if rc != 0 and not (rc == 1 and wrapped):
            return rc or 1  # infrastructure interruption; parent's finally restores
    (root/'longwait-result.json').write_text(json.dumps(result, indent=2)+'\n')
    return 0


def main(argv=None):
    p = argparse.ArgumentParser();p.add_argument('mode', choices=['shard','longwait'])
    p.add_argument('--plan', type=Path, required=True);p.add_argument('--root', type=Path, required=True)
    p.add_argument('--out', type=Path);p.add_argument('--name');p.add_argument('--cutoff', type=float)
    a=p.parse_args(argv);plan=json.loads(a.plan.read_text())
    if a.mode=='shard':
        assess(plan,a.root,a.out,a.name);return 0
    if a.cutoff is None: raise ValueError('longwait requires parent 35-minute cutoff')
    return longwait(plan,a.root,a.cutoff)

if __name__=='__main__':raise SystemExit(main())
