#!/usr/bin/env python3
"""Copy only the explicit landing, rebuild from pinned inputs, run frozen 8 tests.

Local-only reproducer. No provider invocation, transaction or device transport.
The legacy t4 metadata ref is resolved to the landed identical v3 JSON for this
reproducer only; the frozen binding/provider and its exact seal gate are unedited.
"""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
import unittest

HERE = Path(__file__).resolve().parent
PREFIX = Path('benchmark/2026-10-12-v1-seal-assembly')
MANIFEST_SHA = '0c5da8dadaec9e6fc4969d06f884b6204ce5601297f18f76b25fc0407f0d8ab5'
FREEZE_SHA = '756c57e899ff89855f12bc174fdcd35c1e10fdd01ffb5d11b01501e193087ed8'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text())
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--workspaces', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    source_root = HERE.parents[3]
    workspaces = args.workspaces.resolve(); out = args.out.resolve()
    if out.exists(): raise ValueError('new output directory required')
    if out.is_relative_to(source_root): raise ValueError('output must be outside the source checkout')
    os.environ['WORKSPACES'] = str(workspaces)
    inventory = read(HERE/'source-inventory.json')
    out.mkdir(parents=True); clean = out/'clean-landing'; clean.mkdir()
    copied = []
    for row in inventory['files']:
        rel = Path(row['path'])
        if rel.is_absolute() or '..' in rel.parts: raise ValueError('unsafe landing path')
        source = source_root/rel
        if not source.is_file() or source.is_symlink() or sha(source) != row['sha256']:
            raise ValueError('missing or drifted landed source: '+str(rel))
        target = clean/rel; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target); copied.append(str(rel))
    v = clean/PREFIX/'restore-v5'; v4 = clean/PREFIX/'restore-v4'
    assert sha(v/'freeze.json') == FREEZE_SHA
    for row in read(v/'freeze.json')['files']:
        assert sha(clean/row['path']) == row['sha256'], row['path']
    assert not (v/'package-r3-disabled/runtime').exists()
    assert not (v4/'package-r2b-disabled/runtime').exists()

    # After explicit landing import, any access to a private t4 checkout or the
    # original source checkout is a hard failure. The actual main input archive,
    # CAS and independently frozen t0 sources remain declared read dependencies.
    forbidden = {workspaces/'westlake-harness-t4'}
    if source_root.name != 'westlake-harness': forbidden.add(source_root)
    denied = []; shell_calls = []
    def audit(event, values):
        if event == 'subprocess.Popen':
            executable, argv, _, _ = values
            valid = executable == 'bash' and argv[:2] == ['bash', '-c'] and len(argv) in (3, 6)
            if len(argv) == 6:
                valid = valid and argv[3] == 'helper-only' and Path(argv[4]).resolve().is_relative_to(clean)
            if not valid: raise PermissionError('unexpected child process in local delta suite')
            shell_calls.append({'executable': executable, 'argument_count': len(argv)})
        if event != 'open' or not values or not isinstance(values[0], (str, bytes, os.PathLike)): return
        path = Path(os.fsdecode(values[0])).resolve()
        if any(path == root or path.is_relative_to(root) for root in forbidden):
            denied.append(str(path)); raise PermissionError('unlanded private checkout access: '+str(path))
    sys.addaudithook(audit)
    tests = load(v/'test_restore_v5.py', 'clean_landed_v5_tests')
    provider = tests.p
    old_resolve = provider.resolve
    legacy = '$WORKSPACES/westlake-harness-t4/'+str(PREFIX/'restore-v3/stage-donor-observations.json')
    landed = clean/PREFIX/'restore-v3/stage-donor-observations.json'
    assert sha(landed) == '00551807bb579ccfa28aa369480a22d610063492c7425aebb11578beb6173b0e'
    def resolve(reference, base):
        if reference == legacy: return landed
        return old_resolve(reference, base)
    provider.resolve = resolve
    rebuilt = out/'rebuilt-from-pinned-inputs'
    with (out/'compile.txt').open('w') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        result = provider.compile_package(v/'binding.5cd.r3.disabled.json', rebuilt)
        print(json.dumps(result))
    # Reproduction must reproduce the original exact package, not a new fixture.
    assert sha(rebuilt/'manifest.json') == MANIFEST_SHA, 'recompiled manifest differs from frozen v5'
    manifest = read(rebuilt/'manifest.json')
    for row in manifest['files']:
        source = rebuilt/row['path']; assert sha(source) == row['sha256'] and source.stat().st_size == row['bytes']
    # The clean landing supplies small controls. Only omitted large runtime files
    # are hydrated, exclusively from this fresh pinned-input compile.
    package = v/'package-r3-disabled'
    for row in manifest['files']:
        target = package/row['path']
        if target.exists():
            assert sha(target) == row['sha256'], row['path']
        else:
            assert row['path'].startswith('runtime/'), 'missing small landing member: '+row['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(rebuilt/row['path'], target)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(tests.RestoreV5DeltaTests)
    with (out/'tests.txt').open('w') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        test_result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    report = {'status': 'PASS' if test_result.wasSuccessful() else 'FAIL',
              'source_files_copied': len(copied), 'source_inventory_sha256': inventory['content_sha256'],
              'freeze_sha256': FREEZE_SHA, 'rebuilt_manifest_sha256': sha(rebuilt/'manifest.json'),
              'manifest_files_verified': len(manifest['files']), 'tests_run': test_result.testsRun,
              'failures': len(test_result.failures), 'errors': len(test_result.errors),
              'private_checkout_reads_denied': denied, 'audited_shell_calls': shell_calls,
              'isolation_scope': 'Python audit plus frozen reviewed shell snippets; not an OS sandbox',
              'runtime_hydrated_from_fresh_compile': True,
              'metadata_relocation': {'original_ref': legacy, 'landed_path': str(landed), 'sha256': sha(landed)},
              'device_calls': 0, 'transaction_matrix_run': False, 'production_lock_simulated': False}
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    return 0 if test_result.wasSuccessful() else 1

if __name__ == '__main__': raise SystemExit(main())
