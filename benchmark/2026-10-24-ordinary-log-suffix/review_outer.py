"""Read saved receipts only; cross-check summary fields against original bytes."""
import argparse
from datetime import datetime
import json
from pathlib import Path
from check_identity import KEYS, PREFIX, check, sha, verify

SERIAL = '5cd1e3dd00000000000000000923012c'
HDC = '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'

def require(condition, label):
    if not condition:
        raise ValueError(label)

def stat(data, path):
    lines = [line.split() for line in data.decode().splitlines() if line.startswith('STAT ')]
    require(len(lines) == 1 and len(lines[0]) == 8 and lines[0][-1] == path, 'invalid_stat')
    return dict(zip(('dev', 'inode', 'size', 'atime', 'mtime', 'ctime'), map(int, lines[0][1:7])))

def review(raw, old):
    summary = json.loads((raw / 'collection.json').read_text())
    require([r['pid'] for r in summary['files']] == [7011, 9860], 'unexpected_targets')
    result = check(raw)
    require(all(r['status'] == 'bound' for r in result['files']), 'checker_not_bound')
    lock = json.loads((raw / 'lock.receipt.json').read_text())
    require(lock['rc'] == 1 and lock['argv'][-2:] == ['held', SERIAL], 'lock_receipt')
    require(not (raw / 'lock.stdout').read_bytes() and not (raw / 'lock.stderr').read_bytes(), 'lock_output')
    commands = {'targets': [HDC, 'list', 'targets'], 'identity': [HDC, '-t', SERIAL, 'shell', 'cat /proc/sys/kernel/random/boot_id && cat /proc/uptime']}
    for row in summary['files']:
        pid, path = row['pid'], row['path']
        require(path == f'/data/service/el1/public/appspawnx/adapter_child_{pid}.stderr', 'wrong_path')
        for stage in ('pre', 'post'):
            commands[f'{pid}-{stage}'] = [HDC, '-t', SERIAL, 'shell', "stat -c 'STAT %d %i %s %X %Y %Z %n' " + path]
        commands[f'{pid}-payload'] = [HDC, '-t', SERIAL, 'shell', 'head -c 524288 ' + path]
    receipts = {}
    for name, expected in commands.items():
        require(json.loads((raw / (name + '.argv.json')).read_text()) == expected, name + '_argv')
        rec = json.loads((raw / (name + '.receipt.json')).read_text())
        require(rec['rc'] == 0 and 0 <= rec['elapsed_s'] <= 10, name + '_rc_or_budget')
        require(not (raw / (name + '.stderr')).read_bytes(), name + '_stderr')
        receipts[name] = rec
    require(SERIAL.encode() in (raw / 'targets.stdout').read_bytes().split(), 'target_not_listed')
    start = min(datetime.fromisoformat(r['start']) for r in receipts.values())
    end = max(datetime.fromisoformat(r['end']) for r in receipts.values())
    require(0 <= (end-start).total_seconds() <= 60, 'window_budget')
    rows = []
    pins = []
    for row in summary['files']:
        pid, path = row['pid'], row['path']
        historical = (old / f'log{pid}.stdout').read_bytes()
        before, after_head = historical.split(b'---HEAD\n', 1)
        prefix = after_head[:PREFIX]
        require(after_head[PREFIX:].startswith(b'\n---END\n'), 'historical_delimiter')
        old_pre = stat(before, path)
        old_post = stat(after_head[PREFIX+len(b'\n---END\n'):], path)
        pre = stat((raw / f'{pid}-pre.stdout').read_bytes(), path)
        post = stat((raw / f'{pid}-post.stdout').read_bytes(), path)
        payload = (raw / f'{pid}-payload.stdout').read_bytes()
        require(sha(historical) == row['old_raw_sha256'], 'old_raw_pin')
        require(prefix == (raw / f'old-{pid}.prefix').read_bytes(), 'copied_prefix_changed')
        for key, value in [('old_pre', old_pre), ('old_post', old_post), ('pre', pre), ('post', post)]:
            require(row[key] == value, 'summary_stat_' + key)
        bound = verify(old_pre, old_post, pre, post, prefix, payload)
        require(bound['status'] == 'bound' and bound['sha256'] == row['sha256'], 'raw_binding_failed')
        rows.append({'pid': pid, 'path': path, **bound, 'identity': {k: pre[k] for k in KEYS}, 'old_before_after_and_new_before_after_equal': True, 'atime_excluded': True, 'suffix_bytes': len(payload)-PREFIX, 'historical_capture_boot': before.splitlines()[0].decode()})
        pins.append({'path': f'$T109/log{pid}.stdout', 'sha256': sha(historical), 'bytes': len(historical)})
    for p in sorted(raw.iterdir()):
        if p.is_file():
            pins.append({'path': '$OUTER/' + p.name, 'sha256': sha(p.read_bytes()), 'bytes': p.stat().st_size})
    producer = raw.parent / 'collect_once.py'
    pins.append({'path': '$OUTER_PARENT/collect_once.py', 'sha256': sha(producer.read_bytes()), 'bytes': producer.stat().st_size})
    return {'status': 'BOUND_ORDINARY_FILE_EVIDENCE_ONLY', 'collection': 'outer-independent', 'files': rows, 'current_observed_boot': (raw / 'identity.stdout').read_text().splitlines()[0], 'boot_is_file_birth_proof': False, 'lock': {'rc': lock['rc'], 'at': lock['at'], 'stdout_bytes': 0, 'stderr_bytes': 0}, 'commands': receipts, 'window_elapsed_s': (end-start).total_seconds(), 'input_pins': pins, 'limits': ['No diagnosis or repair conclusion.', 'Inner timeout and unknown result remain unchanged.', 'No device command executed by this offline reviewer.']}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--raw', type=Path, required=True)
    parser.add_argument('--old', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(review(args.raw, args.old), indent=2))
