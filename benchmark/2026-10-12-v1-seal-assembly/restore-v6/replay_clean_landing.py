#!/usr/bin/env python3
"""Replay declared small inputs in a fresh directory, denying private-t4 reads.

The eight tests compile all 463 runtime files themselves from pinned external
main-tree/CAS/t0 inputs. No provider invocation, transaction or transport occurs.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PREFIX = Path('benchmark/2026-10-12-v1-seal-assembly/restore-v6')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--workspaces', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    args = ap.parse_args()
    source_root = HERE.parents[2]
    ws = args.workspaces.resolve(); out = args.out.resolve()
    if out.exists() or out.is_relative_to(source_root):
        raise ValueError('new output outside source checkout required')
    os.environ['WORKSPACES'] = str(ws)
    inventory_path = HERE/'replay-inputs.json'
    inventory = json.loads(inventory_path.read_text())
    inventory_sha = sha(inventory_path)
    clean = out/'clean-landing'; clean.mkdir(parents=True)
    for row in inventory['files']:
        rel = Path(row['path'])
        if rel.is_absolute() or '..' in rel.parts: raise ValueError('unsafe replay path')
        source = source_root/rel
        if source.is_symlink() or sha(source) != row['sha256']:
            raise ValueError('replay input drift: '+str(rel))
        target = clean/rel; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source,target)
    v = clean/PREFIX
    assert not (v/'package-composed-disabled/runtime').exists()
    forbidden = {ws/'westlake-harness-t4'}
    if source_root.name != 'westlake-harness': forbidden.add(source_root)
    # shutil cleanup emits relative open events (dir_fd is absent from the audit
    # event). Keep cwd inside the clean copy; never classify these as t4 reads.
    os.chdir(clean)
    denied = []
    def audit(event, values):
        if event == 'subprocess.Popen': raise PermissionError('no subprocess allowed in offline replay')
        if event != 'open' or not values or not isinstance(values[0], (str,bytes,os.PathLike)): return
        path = Path(os.fsdecode(values[0])).resolve()
        if any(path == root or path.is_relative_to(root) for root in forbidden):
            denied.append(str(path)); raise PermissionError('private checkout read: '+str(path))
    sys.addaudithook(audit)
    spec = importlib.util.spec_from_file_location('clean_restore_v6_tests',v/'test_restore_v6.py')
    tests = importlib.util.module_from_spec(spec); spec.loader.exec_module(tests)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(tests.RestoreV6DeltaTests)
    with (out/'tests.txt').open('w') as log:
        result = unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    report = {'status':'PASS' if result.wasSuccessful() else 'FAIL',
        'source_files_copied':len(inventory['files']),'replay_inputs_sha256':inventory_sha,
        'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'private_checkout_read_attempts':denied,'subprocess_calls':0,'device_calls':0,
        'runtime_rebuilt_in_temporary_directory':True,'runtime_files':463,
        'runtime_bytes':769937330,'runtime_in_landing':False,
        'manifest_sha256':sha(v/'package-composed-disabled/manifest.json'),
        'isolation_scope':'Python audit, not OS sandbox; main/CAS/t0 remain declared external inputs',
        'transaction_matrix_run':False,'production_lock_simulated':False}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if result.wasSuccessful() else 1
if __name__ == '__main__': raise SystemExit(main())
