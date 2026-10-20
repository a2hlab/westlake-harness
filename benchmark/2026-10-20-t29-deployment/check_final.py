#!/usr/bin/env python3
"""T29 pending-data checker. No new deployment logic; final production is not admitted."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

P = Path(__file__).resolve().parent
EXECUTOR = '693448c26cb72002031f58cca467691f09ac61674b2c76353eb71bd44a5b63bb'
SELF_PINS = {
    'executor_sha256': 'executor.py', 'parameters_sha256': 'parameters.json',
    'source_pins_sha256': 'executor-source-pins.json',
    'readonly_inputs_sha256': 'readonly-inputs.json',
    'bridge_candidate_sha256': 'bridge-candidate.json',
    'shim_candidate_sha256': 'shim-candidate.json',
    'three_slot_requirements_sha256': 'three-slot-admission.json',
    'bridge_binding_requirements_sha256': 'bridge-binding-pending.json',
}

def load(p):
    return json.loads(p.read_text())

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(p, value):
    p.write_text(json.dumps(value, indent=2) + '\n')

def validate(root, repo):
    assert sha(root / 'executor.py') == EXECUTOR, 'transaction changed'
    for item in load(root / 'unchanged-pins.json'):
        assert sha(root / item['file']) == item['sha256'], item['file']
        assert (root / item['file']).read_bytes() == (repo / item['donor']).read_bytes(), item['file']
    params = load(root / 'parameters.json')
    old = load(root / 'donor-t28-parameters.json')
    assert len(params['artifacts']) == 6
    for key in ('serial', 'uid', 'desktop_uid', 'runtime', 'cfg_path', 'cfg_sha256',
                'apk_sha256', 'runtime_exe_sha256', 'run_derivation'):
        assert params[key] == old[key], key
    assert params['artifacts'][:4] == old['artifacts'][:4], 'four fixed artifacts changed'
    assert params['historical_identity_only'] == {} and params['approved_by'] is None
    for index, role in ((4, 'bridge'), (5, 'shim')):
        c = load(root / (role + '-candidate.json'))
        assert c['path'] == old['artifacts'][index]['path']
        assert c['before_sha256'] == old['artifacts'][index]['before_sha256']
        assert params['artifacts'][index]['path'] == c['path']
        assert params['artifacts'][index]['before_sha256'] == c['before_sha256']
        assert params['artifacts'][index]['after_sha256'] is None
        assert params['artifacts'][index]['after_bytes'] is None
        assert c['after_sha256'] is None and c['after_bytes'] is None, role + ' must remain pending'
        assert c['production_refs'] == [] and c['build_status'] == 'UNAPPROVED'
        assert c['production_receipt'] is None and c['artifact_location'] is None
    ad = load(root / 'admission.template.json')
    for key in ('approved_by', 'boot', 'holder', 'window_start', 'parent_mnt',
                'origin_apply_plan_sha256', 'bridge_metadata', 'shim_metadata',
                'fresh_three_slot_receipt_sha256'):
        assert ad[key] is None, key
    assert ad['host'] == {'pid': None, 'birth': None, 'uid': 20011300}
    assert ad['recovery_no_parent'] is False
    for key, name in SELF_PINS.items():
        assert ad[key] == sha(root / name), key
    assert ad['providers'] == load(root / 'readonly-inputs.json')['providers']
    slots = load(root / 'three-slot-admission.json')
    assert slots['candidate_sha256'] is None
    assert slots['player_sha256'] == params['artifacts'][3]['after_sha256']
    assert [(x['symbol'], x['player_slot']) for x in slots['slots']] == [
        ('ANativeWindow_setBuffersGeometry', '0x472048'),
        ('ANativeWindow_lock', '0x472490'),
        ('ANativeWindow_unlockAndPost', '0x472760')]
    assert all(x['candidate_export_offset'] is None and x['actual_slot_value'] is None
               and x['matched'] is False for x in slots['slots'])
    binding = load(root / 'bridge-binding-pending.json')
    for key in ('bridge_sha256', 'shim_sha256', 'consumer_jni_and_got_receipt',
                'public_binding_receipt', 'actual_provider_instance_receipt'):
        assert binding[key] is None, key
    assert all(x is None for x in binding['owner_offsets'].values())
    assert all(x is None for x in binding['owner_slots'].values())
    return ['exact executor and six donor support files', 'four fixed artifacts unchanged',
            'both candidates, offsets and production receipts pending',
            'fresh admission empty; all self pins match']

def run_sentinels(root, out):
    """Exercise the exact executor, including the otherwise masked missing-shim branch.

    Synthetic receipts exist ONLY in fixture copies. The repository contains no Board
    implementation. Every call must fail before its import, not merely fail to find HDC.
    """
    repo = out / 'synthetic-repo'
    repo.mkdir()
    ref = repo / 'synthetic-receipt.json'
    save(ref, {'fixture_only': True, 'production': False})
    runs = []
    cases = [('both-missing', 'candidate pin required'),
             ('bridge-missing', 'candidate pin required'),
             ('shim-missing', 'shim candidate pin required'),
             ('bridge-closure-missing', 'production closure required'),
             ('shim-closure-missing', 'shim production closure required')]
    for case, expected in cases:
        fixture = out / case
        fixture.mkdir()
        shutil.copyfile(root / 'executor.py', fixture / 'executor.py')
        assert sha(fixture / 'executor.py') == EXECUTOR
        for role in ('bridge', 'shim'):
            c = load(root / (role + '-candidate.json'))
            missing = case == 'both-missing' or case == role + '-missing'
            if not missing:
                c.update(after_sha256=('a' if role == 'bridge' else 'b') * 64,
                         build_status='PRODUCTION_BUILD_VERIFIED',
                         production_refs=[{'path': ref.name, 'sha256': sha(ref)}])
            if case == role + '-closure-missing':
                c['production_refs'] = []
            save(fixture / (role + '-candidate.json'), c)
        for mode in ('preflight', 'apply', 'rollback'):
            argv = [sys.executable, str(fixture / 'executor.py'), mode, '--execute',
                    '--boot', 'OFFLINE_SENTINEL', '--parent', '1', '--birth', '1',
                    '--hdc', '/NONEXISTENT_T29_NO_DEVICE', '--holder', 'OFFLINE_SENTINEL',
                    '--out', str((out / 'never-created-device-output').resolve()),
                    '--repo', str(repo), '--inputs', str(repo),
                    '--admission', str(root / 'admission.template.json'), '--start', '1']
            result = subprocess.run(argv, capture_output=True, timeout=10)
            prefix = fixture / mode
            save(prefix.with_suffix('.argv.json'), argv)
            prefix.with_suffix('.stdout').write_bytes(result.stdout)
            prefix.with_suffix('.stderr').write_bytes(result.stderr)
            prefix.with_suffix('.rc').write_text(str(result.returncode) + '\n')
            assert result.returncode != 0
            assert ('AssertionError: ' + expected).encode() in result.stderr, result.stderr
            assert b'bms_batch' not in result.stderr, 'reached Board import'
            assert not (out / 'never-created-device-output').exists()
            runs.append({'case': case, 'mode': mode, 'rc': result.returncode,
                         'expected': expected, 'stderr_sha256': sha(prefix.with_suffix('.stderr'))})
    for mode in ('preflight', 'apply', 'rollback'):
        argv = [sys.executable, str(root / 'executor.py'), mode]
        result = subprocess.run(argv, capture_output=True, timeout=10)
        prefix = out / (mode + '-preview')
        save(prefix.with_suffix('.argv.json'), argv)
        prefix.with_suffix('.stdout').write_bytes(result.stdout)
        prefix.with_suffix('.stderr').write_bytes(result.stderr)
        prefix.with_suffix('.rc').write_text(str(result.returncode) + '\n')
        assert result.returncode == 0 and json.loads(result.stdout)['device_calls'] == 0
        runs.append({'case': 'preview', 'mode': mode, 'rc': 0})
    return runs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-root', '--repo', dest='repo', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    assert a.out.is_absolute() and not str(a.out).startswith(('/tmp/', '/private/tmp/'))
    checks = validate(P, a.repo)
    a.out.mkdir(parents=True, exist_ok=False)
    runs = run_sentinels(P, a.out)
    result = {'status': 'PENDING_TEMPLATE_CHECKED_NOT_ADMISSION', 'checks': checks,
              'runs': runs, 'device_calls': 0, 'transaction_tests_rerun': False,
              'executor_sha256': sha(P / 'executor.py'),
              'pending': ['bridge/shim final bytes SHA and sizes', 'public paired production refs',
                          'new bridge owner/GOT and shim export offsets',
                          'fresh T29 baseline and outer admission']}
    save(a.out / 'results.json', result)
    print(json.dumps(result))

if __name__ == '__main__':
    main()
