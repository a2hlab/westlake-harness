#!/usr/bin/env python3
"""Run exact checkpoint CLI with real fixture files and no board transport."""
import hashlib
import argparse
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time
import re

HERE = Path(__file__).resolve().parent
WORKSPACES = HERE.parents[2]
COMMIT = '70b6eeda5811819a6fcb03061906838ffce5f963'
PREFIX = 'benchmark/2026-10-12-recovery-executor'
OUTPUT = HERE / '.artifacts/t5-70b6-independent-attempt4'
PACKAGE = OUTPUT / 'workspaces/westlake-harness-t0' / PREFIX
RECORDER = HERE / 'record_t5_hdc.py'
CONTROL_ROOT = '/data/westlake-demo/toutiao/recovery-attempts/r1-9763171a-preview'
ALLOW_STALE_MANIFEST = False
CASES = ['positive_cli', 'preview', 'wrong_auth_pin', 'changed_plan', 'wrong_serial',
         'expired_auth', 'wrong_auth_boot', 'wrong_device_boot', 'missing_before_label',
         'null_after_label', 'partial_backup', 'preimage_drift', 'mkdir_first_failure',
         'partial_send', 'metadata_failure', 'inert_retry', 'old_stop_drift',
         'wrong_transaction', 'corrupt_backup', 'guardian_reuse', 'guardian_uid',
         'guardian_argv', 'guardian_stuck', 'rollback_positive', 'new_boot_rollback',
         'wrong_guardian_boot']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def export():
    assert not OUTPUT.exists(), 'preserve prior attempt'
    archive = subprocess.run(['git', '-C', str(WORKSPACES / 'westlake-harness-t0'),
                              'archive', COMMIT, PREFIX], check=True, capture_output=True).stdout
    destination = OUTPUT / 'workspaces/westlake-harness-t0'
    destination.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as content:
        for member in content.getmembers():
            assert not member.name.startswith('/') and '..' not in Path(member.name).parts
            assert not member.issym() and not member.islnk()
        content.extractall(destination)
    manifest = json.loads((PACKAGE / 'checkpoint-manifest.json').read_text())
    mismatches = []
    for row in manifest['files']:
        actual = sha(destination / row['path'])
        if actual != row['sha256']:
            mismatches.append({'path': row['path'], 'declared_sha256': row['sha256'], 'git_sha256': actual})
    assert not mismatches or ALLOW_STALE_MANIFEST, mismatches
    RECORDER.chmod(0o755)
    return {'commit': COMMIT, 'manifest_sha256': sha(PACKAGE / 'checkpoint-manifest.json'),
            'executor_sha256': sha(PACKAGE / 'executor.py'), 'members': len(manifest['files']),
            'git_archive_sha256': hashlib.sha256(archive).hexdigest(),
            'manifest_mismatches': mismatches, 'deployment_admission': False}


def fixture(name):
    root = OUTPUT / 'cases' / name
    root.mkdir(parents=True)
    plan_template = json.loads((PACKAGE / 'plan.disabled.json').read_text())
    selected = [row for row in plan_template['members'] if row['target'] in (
        CONTROL_ROOT + '/entry.sh',
        '/data/westlake-demo/toutiao/scripts/watchdog.sh',
        '/data/local/tmp/operator45/selfheal48/watchdog.sh',
        '/system/etc/init/01_westlake_u13_toutiao.cfg')]
    assert len(selected) == 4
    plan = dict(plan_template, execution_enabled=True, members=selected,
                hdc=str(RECORDER), prerequisites=[])
    plan['tools']['hdc'] = {'path': str(RECORDER), 'sha256': sha(RECORDER)}
    model = dict(serial=plan['serial'], boot=plan['boot_id'], objects={}, events=[],
                 cfg_metadata=selected[-1]['after'], inert_sha=sha(PACKAGE / 'payload/rollback-inert.cfg'))
    for row in selected + plan['preserved']:
        before = row['before']
        if before['exists']:
            path = Path(os.path.expandvars(before['source'].replace('$WORKSPACES', str(WORKSPACES))))
            if not path.is_absolute():
                path = WORKSPACES / 'westlake-harness' / path
                before['source'] = str(path)
            assert sha(path) == before['sha256']
            model['objects'][row['target']] = dict(before, hex=path.read_bytes().hex())
    for row in plan['members']:
        row['source'] = row['source'].replace('$PACKAGE', str(PACKAGE))
    model['directories'] = sorted({str(parent) for target in model['objects'] for parent in Path(target).parents})
    path = root / 'plan.json'
    path.write_text(json.dumps(plan, indent=2))
    auth = dict(approved_by='outer(codex)', plan_sha256=sha(path), serial=plan['serial'],
                origin_boot_id=plan['boot_id'], boot_id=plan['boot_id'],
                expires_epoch=time.time() + 600, actions=['place-only', 'one-reboot', 'rollback-safe'],
                synthetic_fixture=True)
    auth_path = root / 'synthetic-auth.json'
    auth_path.write_text(json.dumps(auth, indent=2))
    device = root / 'device.json'
    device.write_text(json.dumps(model, indent=2))
    return root, plan, path, auth_path, device


def run_cli(plan, auth, device, out, extra=()):
    argv = [sys.executable, str(PACKAGE / 'executor.py'), '--execute', '--plan', str(plan),
            '--authorization', str(auth), '--authorization-sha256', sha(auth), '--out', str(out), *extra]
    result = subprocess.run(argv, env={**os.environ, 'WORKSPACES': str(WORKSPACES),
                                      'RECOVERY_TEST_DEVICE': str(device), 'PYTHONDONTWRITEBYTECODE': '1'},
                            capture_output=True, text=True, timeout=60)
    return result


def update_ticket(plan_path, auth_path, plan, mutation=None):
    plan_path.write_text(json.dumps(plan, indent=2))
    auth = json.loads(auth_path.read_text())
    auth['plan_sha256'] = sha(plan_path)
    if mutation:
        auth.update(mutation)
    auth_path.write_text(json.dumps(auth, indent=2))


def main(argv=None):
    global COMMIT, OUTPUT, PACKAGE, ALLOW_STALE_MANIFEST
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', default=COMMIT)
    parser.add_argument('--attempt', default='t5-review-' + time.strftime('%Y%m%dT%H%M%S'))
    parser.add_argument('--case', action='append', choices=CASES)
    parser.add_argument('--review-stale-manifest', action='store_true')
    arguments = parser.parse_args(argv)
    assert re.fullmatch('[0-9a-f]{40}', arguments.commit), 'immutable full commit required'
    assert re.fullmatch('[A-Za-z0-9._-]+', arguments.attempt), 'local attempt name only'
    COMMIT = arguments.commit
    ALLOW_STALE_MANIFEST = arguments.review_stale_manifest
    OUTPUT = HERE / '.artifacts' / arguments.attempt
    PACKAGE = OUTPUT / 'workspaces/westlake-harness-t0' / PREFIX
    receipt = export()
    print(json.dumps(receipt), flush=True)
    results = []
    cases = arguments.case or CASES
    for name in cases:
        root, plan, plan_path, auth, device = fixture(name)
        model = json.loads(device.read_text())
        if name == 'null_after_label':
            plan['members'][1]['after']['label'] = None
            update_ticket(plan_path, auth, plan)
        if name == 'wrong_serial':
            plan['serial'] = '5ea34a4500000000000000001123012c'
            update_ticket(plan_path, auth, plan)
        if name == 'expired_auth':
            update_ticket(plan_path, auth, plan, {'expires_epoch': 1})
        if name == 'wrong_auth_boot':
            update_ticket(plan_path, auth, plan, {'boot_id': '00000000-0000-0000-0000-000000000001'})
        if name == 'wrong_device_boot':
            model['boot'] = '00000000-0000-0000-0000-000000000001'
        if name == 'missing_before_label':
            del plan['members'][1]['before']['label']
            update_ticket(plan_path, auth, plan)
        if name == 'changed_plan':
            plan_path.write_text(plan_path.read_text() + '\n')
        if name == 'preimage_drift':
            model['objects'][plan['members'][1]['target']]['mode'] = '777'
        faults = {'partial_send': 'send_partial', 'partial_backup': 'backup_partial',
                  'mkdir_first_failure': 'mkdir_first_failure', 'metadata_failure': 'metadata_failure'}
        if name in faults:
            model['fault'] = faults[name]
        device.write_text(json.dumps(model, indent=2))
        out = root / 'transaction'
        if name == 'preview':
            process = subprocess.run([sys.executable, str(PACKAGE / 'executor.py'), '--plan', str(plan_path)],
                                     capture_output=True, text=True, check=False)
        elif name == 'wrong_auth_pin':
            process = run_cli(plan_path, auth, device, out, ('--authorization-sha256', '0' * 64))
        else:
            process = run_cli(plan_path, auth, device, out)
        (root / 'apply.stdout.txt').write_text(process.stdout)
        (root / 'apply.stderr.txt').write_text(process.stderr)
        model = json.loads(device.read_text())
        row = {'case': name, 'apply_exit': process.returncode, 'apply_stderr': process.stderr,
               'send_count': model.get('send_count', 0), 'real_plan_sha256': sha(plan_path),
               'real_auth_sha256': sha(auth), 'synthetic': True,
               'transport_calls': len(model['events']), 'root_exists_after_apply': CONTROL_ROOT in model['directories']}
        if name == 'positive_cli' and process.returncode != 0:
            row['reviewer_status'] = 'baseline/adaptor failure; do not grade negatives'
            results.append(row)
            break
        rollback_cases = {'partial_send', 'inert_retry', 'mkdir_first_failure', 'metadata_failure',
                          'wrong_transaction', 'corrupt_backup', 'guardian_reuse', 'guardian_uid',
                          'guardian_argv', 'guardian_stuck', 'rollback_positive', 'new_boot_rollback',
                          'wrong_guardian_boot', 'old_stop_drift'}
        if name in rollback_cases:
            if name == 'inert_retry' and process.returncode == 0:
                model['fault'] = 'inert_then_fail'
            else:
                model.pop('fault', None)
            if name in ('guardian_reuse', 'guardian_uid', 'guardian_argv', 'guardian_stuck', 'wrong_guardian_boot'):
                state = CONTROL_ROOT + '/boots/' + model['boot']
                lock_boot = model['boot'] if name != 'wrong_guardian_boot' else '00000000-0000-0000-0000-000000000001'
                data = ('444 555 ' + lock_boot + '\n').encode()
                model['objects'][state + '/lock/owner'] = dict(exists=True, sha256=hashlib.sha256(data).hexdigest(),
                        mode='600', uid=0, gid=0, label='u:object_r:data_file:s0', hex=data.hex())
                model['directories'] = sorted(set(model['directories']) | {state, state + '/lock', CONTROL_ROOT + '/boots'})
                model['fault'] = name
            if name == 'old_stop_drift':
                model['objects'][plan['preserved'][0]['target']]['mode'] = '777'
            if name == 'new_boot_rollback':
                model['boot'] = '00000000-0000-0000-0000-000000000001'
                update_ticket(plan_path, auth, plan, {'boot_id': model['boot']})
            if name == 'wrong_transaction':
                transaction = json.loads((out / 'transaction.json').read_text())
                transaction['plan_sha256'] = '0' * 64
                (out / 'transaction.json').write_text(json.dumps(transaction))
            if name == 'corrupt_backup':
                (out / 'backup-001').write_bytes(b'corrupt')
            device.write_text(json.dumps(model, indent=2))
            writes_before = model.get('send_count', 0)
            rollback = run_cli(plan_path, auth, device, out, ('--action', 'rollback'))
            (root / 'rollback.stderr.txt').write_text(rollback.stderr)
            row['rollback_exit'] = rollback.returncode
            row['rollback_stderr'] = rollback.stderr
            model = json.loads(device.read_text())
            row['rollback_sends'] = model.get('send_count', 0) - writes_before
            row['rollback_receipt_exists'] = (out / 'rollback.json').exists()
            row['root_stop_exists'] = CONTROL_ROOT + '/stop' in model['objects']
            row['restored_aliases'] = {member['target']: model['objects'].get(member['target'], {}).get('sha256') == member['before']['sha256']
                                     for member in plan['members'] if member['before']['exists'] and '/watchdog.sh' in member['target']}
            if name == 'inert_retry':
                model = json.loads(device.read_text())
                model.pop('fault', None)
                device.write_text(json.dumps(model, indent=2))
                retry = run_cli(plan_path, auth, device, out, ('--action', 'rollback'))
                (root / 'retry.stderr.txt').write_text(retry.stderr)
                row.update(retry_exit=retry.returncode, retry_stderr=retry.stderr)
        results.append(row)
        print(json.dumps(row), flush=True)
        (OUTPUT / 'first-results.json').write_text(json.dumps({'receipt': receipt, 'cases': results}, indent=2))
    (OUTPUT / 'first-results.json').write_text(json.dumps({'receipt': receipt, 'cases': results}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
