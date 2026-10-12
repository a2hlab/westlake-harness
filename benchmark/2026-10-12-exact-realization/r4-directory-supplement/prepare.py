#!/usr/bin/env python3
"""Prepare one empty-directory supplement from existing local evidence only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
RUNTIME = '/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d'
TARGET = RUNTIME + '/webview-t-data'
SOURCE_SERIAL = '61b0657200000000000000000324012c'
TARGET_SERIAL = '5cd1e3dd00000000000000000923012c'
ORIGIN_SHA = 'dfd4e5c242b9327ab07a29abf4f2c9ef9640097078703ae4a811cceab7d35f7c'
PLAN_SHA = '088dd4cdf67438426dae214671375a5001aedc86ea8ed807ea354f3c536d1592'
EXECUTOR_SHA = '496fa979f4af71b8c01c44a474aed4074b64544d5d1eb500709c649679831d0d'
BOOT = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}')


def need(ok, why):
    if not ok:
        raise ValueError(why)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def workspace():
    return Path(os.environ.get('WORKSPACES', HERE.parents[3])).resolve()


def pin(path):
    path = Path(path).resolve()
    if path.is_relative_to(HERE):
        return {'path': str(path.relative_to(HERE)), 'sha256': digest(path)}
    return {'path': '$WORKSPACES/' + str(path.relative_to(workspace())), 'sha256': digest(path)}


def read_record(path, serial):
    path = Path(path)
    need(path.is_file() and not path.is_symlink(), 'record absent or symlink')
    record = json.loads(path.read_text())
    argv = record['argv']
    need(record['exit'] == 0 and argv[1:4] == ['-t', serial, 'shell'], 'record transport/serial differs')
    out, err = path.with_suffix('.stdout'), path.with_suffix('.stderr')
    need(digest(out) == record['stdout_sha256'] and digest(err) == record['stderr_sha256'], 'raw record SHA mismatch')
    need(err.read_bytes() == b'', 'transport stderr not empty')
    text = out.read_text()
    need(text.rstrip().endswith('RE_REMOTE_RC=0'), 'remote status absent/nonzero')
    return text, {'receipt': pin(path), 'stdout': pin(out), 'stderr': pin(err)}


def source_metadata(text):
    lines = text.splitlines()
    boots = [line for line in lines if BOOT.fullmatch(line)]
    need(len(boots) == 2 and boots[0] == boots[1] and lines[0] == boots[0], 'source sameboot evidence missing')
    rows = [line.split() for line in lines if line.split() and line.split()[-1] == TARGET]
    need(len(rows) == 1, 'source directory row missing/duplicate')
    row = rows[0]
    need(row[0] == 'drwxr-xr-x' and row[2:5] == ['20011206', '20011206', 'u:object_r:appdat:s0'], 'source type/mode/uid/gid/label differs')
    need(lines.count('755 20011206 20011206 directory') == 1, 'source stat evidence differs')
    return {'mode': '755', 'uid': 20011206, 'gid': 20011206, 'label': row[4]}, boots[0]


def prepare(args):
    need(not args.out.exists() and args.out.parent.is_dir(), 'fresh output required')
    need(digest(args.origin_realization) == ORIGIN_SHA, 'original 487 proof drift')
    origin = json.loads(args.origin_realization.read_text())
    params = origin['parameters']
    need(params['serial'] == TARGET_SERIAL and params['host_uid'] == params['host_gid'] == 20011300, 'target identity differs')
    need(digest(args.prepared_plan) == PLAN_SHA, 'original enabled plan drift')
    plan = json.loads(args.prepared_plan.read_text())
    need(len(plan['members']) == 487, 'original member set differs')
    source, src_refs = read_record(args.source_record, SOURCE_SERIAL)
    metadata, source_boot = source_metadata(source)
    target, dst_refs = read_record(args.target_record, TARGET_SERIAL)
    need(BOOT.fullmatch(args.boot_id) and target.splitlines()[0] == args.boot_id, 'target historical boot differs')
    need('ls: ' + TARGET + ': No such file or directory' in target, 'historical explicit absence evidence missing')
    need('20011300:20011300' in target.splitlines(), 'target observed host owner missing')
    executor = args.prepared_plan.parent / 'executor.py'
    need(digest(executor) == EXECUTOR_SHA, 'frozen transport executor drift')
    driver = dict(plan['tools']['driver'])
    driver_path = Path(driver['path'].replace('$WORKSPACES', str(workspace())))
    need(digest(driver_path) == driver['sha256'], 'driver pin drift')
    after = dict(metadata, uid=params['host_uid'], gid=params['host_gid'])
    manifest = {
        'schema': 'exact-directory-supplement/v1', 'synthetic': False, 'execution_enabled': False,
        'executor_sha256': digest(HERE / 'directory_transaction.py'),
        'serial': TARGET_SERIAL, 'boot_id': args.boot_id, 'target': TARGET,
        'before': {'exists': False}, 'after': after, 'source_metadata': metadata,
        'evidence': {'source_receipt': src_refs['receipt'], 'source_stdout': src_refs['stdout'],
                     'source_stderr': src_refs['stderr'], 'target_receipt': dst_refs['receipt'],
                     'target_stdout': dst_refs['stdout'], 'target_stderr': dst_refs['stderr']},
        'origin_realization': pin(args.origin_realization),
        'tools': {'executor': pin(executor), 'driver': pin(driver_path)},
    }
    with args.out.open('x') as stream:
        json.dump(manifest, stream, indent=2); stream.write('\n')
    report = {'status': 'OFFLINE_DIRECTORY_SUPPLEMENT_NOT_AUTHORIZED', 'manifest': pin(args.out),
              'generator': pin(__file__), 'source_boot': source_boot, 'target_historical_boot': args.boot_id,
              'source_evidence': src_refs, 'target_evidence': dst_refs,
              'prepared_plan': pin(args.prepared_plan), 'content_copied': False,
              'existing_487_proof_modified': False, 'device_calls': 0,
              'limitation': 'Target historical sample has one boot reading; executor must freshly prove boot, parent and target state before writing.'}
    args.out.with_name(args.out.stem + '.preparation.json').write_text(json.dumps(report, indent=2) + '\n')
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for arg in ('source-record', 'target-record', 'origin-realization', 'prepared-plan', 'out'):
        ap.add_argument('--' + arg, type=Path, required=True)
    ap.add_argument('--boot-id', required=True)
    args = ap.parse_args()
    try:
        prepare(args)
        print('OFFLINE_DIRECTORY_SUPPLEMENT sha256=' + digest(args.out)); return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('REJECT ' + str(exc)); return 2


if __name__ == '__main__':
    raise SystemExit(main())
