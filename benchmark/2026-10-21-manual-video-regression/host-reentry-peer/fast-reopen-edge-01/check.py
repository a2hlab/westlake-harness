#!/usr/bin/env python3
"""Run three bounded, entirely local common state-machine replays.

Raw stderr stays in .private; public receipts contain only SHA/size.
Use --run-id to retain separate reruns without overwriting original logs.
"""
import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED_COMMON = 'b806eb6c1bb390be357f2ac689024bf3947217611bf637850cfc65e7538681c9'
CASES = [('missed_during_supervision', 0), ('desktop_then_host', 1),
         ('host_at_start_no_manual_event', 0)]


def metadata(path):
    data = path.read_bytes()
    return {'path': path.relative_to(HERE).as_posix(), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', default='run-01')
    args = parser.parse_args()
    if not args.run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in args.run_id):
        parser.error('run-id must be a single alphanumeric/dash/underscore name')
    before = metadata(HERE / 'common.snapshot.sh')
    if before['sha256'] != EXPECTED_COMMON:
        raise SystemExit('Production common pin mismatch; nothing executed')
    raw = HERE / '.private' / args.run_id
    public = HERE / args.run_id
    raw.mkdir(parents=True, exist_ok=False)
    public.mkdir(exist_ok=False)
    rows, traces = [], {}
    for name, expected in CASES:
        argv = ['/bin/sh', 'replay.sh', name]
        start = datetime.now(timezone.utc).isoformat()
        stdout, stderr = raw / (name + '.stdout'), raw / (name + '.stderr')
        # Files are opened BEFORE execution; bytes are streamed directly to disk.
        with stdout.open('wb') as out, stderr.open('wb') as err:
            proc = subprocess.run(argv, cwd=HERE, stdout=out, stderr=err, timeout=5)
        output = stdout.read_bytes()
        traces[name] = output.split(b'LOOP_BEGIN\n', 1)[1]
        expected_line = ('RESULT rc=0 spawns=%d after=%d epochs=0 arm=HOST_CONSUMED ticks=4' % (expected, expected)).encode()
        checks = {'rc_zero': proc.returncode == 0,
                  'expected_result': expected_line in output.splitlines(),
                  'stderr_empty': stderr.stat().st_size == 0,
                  'four_focus_samples': sum(line.startswith(b'FOCUS ') for line in output.splitlines()) == 4}
        receipt = {'case': name, 'argv': argv, 'cwd': 'package directory',
                   'started_utc': start, 'finished_utc': datetime.now(timezone.utc).isoformat(),
                   'rc': proc.returncode, 'expected_mock_spawns': expected,
                   'stdout': metadata(stdout), 'stderr': metadata(stderr), 'checks': checks}
        (raw / (name + '.command.json')).write_text(json.dumps(receipt, indent=2) + '\n')
        (public / (name + '.stdout.txt')).write_bytes(output)
        rows.append(receipt)
    same = traces['missed_during_supervision'] == traces['host_at_start_no_manual_event']
    unchanged = before == metadata(HERE / 'common.snapshot.sh')
    passed = same and unchanged and all(all(r['checks'].values()) for r in rows)
    result = {'schema': 't37-common-missed-edge/v1', 'status': 'PASS' if passed else 'FAIL',
              'meaning': 'Expected observations reproduced; not fix acceptance or device evidence',
              'cases': rows, 'lost_edge_and_no_event_loop_traces_byte_identical': same,
              'production_common_unchanged': unchanged,
              'inputs': [metadata(HERE / n) for n in ('common.snapshot.sh', 'replay.sh', 'check.py', 'source-pins.json')],
              'device_access': False, 'production_monitor_executed': False,
              'real_process_operations': False, 't38_executed': False}
    (public / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'cases': len(rows),
                      'mock_spawn_counts': [r['expected_mock_spawns'] for r in rows],
                      'loop_traces_identical': same}, sort_keys=True))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
