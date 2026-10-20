#!/usr/bin/env python3
"""Run exact original 14 logger modes and two independent error-budget regressions."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
MODES = ['pipe', 'fd2_rebind', 'sink_drift', 'epipe', 'eintr', 'short', 'hot_new',
         'parallel', 'reserve', 'total', 'epochs', 'long', 'refunref', 'invalid_consumer']

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cmds = []
    def run(name, argv, expected_rc=0):
        with (out / (name + '.stdout')).open('wb') as stdout, (out / (name + '.stderr')).open('wb') as stderr:
            rc = subprocess.run(argv, cwd=HERE, stdout=stdout, stderr=stderr).returncode
        cmds.append(dict(name=name, argv=argv, rc=rc))
        if rc != expected_rc:
            raise RuntimeError(f'{name} failed: {rc}')
    try:
        run('build-original-counterexample', ['cc', '-std=c11', '-I', 'source',
            'counterexample/test_observe29c.original.c', '-lpthread', '-o', str(out / 'original-counterexample')])
        run('original-counterexample-refunref', [str(out / 'original-counterexample'), 'refunref'], expected_rc=-6)
        run('build-original14', ['cc', '-std=c11', '-Wall', '-Wextra', '-Wno-unused-parameter',
            '-fvisibility=hidden', '-I', 'source',
            'tests/test_observe29c.c', '-lpthread', '-o', str(out / 'original14')])
        for mode in MODES:
            run('original14-' + mode, [str(out / 'original14'), mode])
            assert f'PASS observe29c {mode}' in (out / ('original14-' + mode + '.stdout')).read_text()
        run('build-budget', ['cc', '-std=c11', '-Wall', '-Wextra', '-fvisibility=hidden',
            '-I', 'source', 'tests/test_failure_budget.c',
            'source/observe29c.c', '-lpthread', '-o', str(out / 'budget')])
        for mode in ['ref', 'unref']:
            run('budget-' + mode, [str(out / 'budget'), mode])
            lines = (out / ('budget-' + mode + '.stderr')).read_text().splitlines()
            records = [line for line in lines if 'side=consumer p=' in line]
            assert len(records) == 4
            for ordinal, line in enumerate(records, 1):
                assert f' c={ordinal} ' in line
                rc = (-29 if mode == 'ref' else -31) if ordinal > 2 else 0
                assert f' {mode}=1/1/{rc} ' in line
            assert len([line for line in lines if 'FIRST_LIMIT' in line]) == 1
        status = 'PASS_HOST_ONLY_13_UNCHANGED_1_CORRECTED_PLUS_2_BUDGET_MODES'
    finally:
        inputs = {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(HERE.rglob('*')) if p.is_file() and p.suffix in ('.c', '.h', '.py')}
        (out / 'receipt.json').write_text(json.dumps(dict(status=locals().get('status', 'FAILED'),
            time=time.time(), commands=cmds, inputs=inputs, new_device_calls=0), indent=2) + '\n')
    print(status)

if __name__ == '__main__':
    main()
