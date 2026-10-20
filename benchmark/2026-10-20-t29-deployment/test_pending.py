#!/usr/bin/env python3
"""Actual checker mutations and exact executor admission sentinels; offline only."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

P = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('t29_pending_checker', P / 'check_final.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)
local = P.parents[1]
ROOT = Path(os.environ.get('T29_SOURCE_ROOT', str(local)))
if not (ROOT / 'benchmark/2026-10-20-t28-shim-deployment').exists():
    ROOT = local.parent / 'westlake-harness'

class Pending(unittest.TestCase):
    def test_template_and_actual_executor(self):
        check.validate(P, ROOT)
        base = Path.home() / '.local/share/westlake/t29-deployment-tests'
        base.mkdir(parents=True, exist_ok=True)
        out = Path(tempfile.mkdtemp(prefix='sentinel-', dir=base))
        runs = check.run_sentinels(P, out)
        self.assertEqual(len(runs), 18)
        check.save(out / 'results.json', {'runs': runs, 'device_calls': 0})

    def test_mutations_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            for case in ('executor', 'fixed-four', 'selfpin', 'stale-offset', 'fresh-approval'):
                root = Path(tmp) / case
                shutil.copytree(P, root, ignore=shutil.ignore_patterns('__pycache__', 'checks'))
                if case == 'executor':
                    with (root / 'executor.py').open('a') as f:
                        f.write('\n# drift\n')
                else:
                    name = {'fixed-four': 'parameters.json', 'selfpin': 'admission.template.json',
                            'stale-offset': 'three-slot-admission.json',
                            'fresh-approval': 'admission.template.json'}[case]
                    value = check.load(root / name)
                    if case == 'fixed-four': value['artifacts'][0]['after_sha256'] = 'f' * 64
                    if case == 'selfpin': value['parameters_sha256'] = 'f' * 64
                    if case == 'stale-offset': value['slots'][0]['candidate_export_offset'] = '0xe3b0'
                    if case == 'fresh-approval': value['approved_by'] = 'outer(codex)'
                    check.save(root / name, value)
                    # Keep selfpins consistent so field-specific checks, not only hash drift, reject.
                    if case in ('fixed-four', 'stale-offset'):
                        ad = check.load(root / 'admission.template.json')
                        key = 'parameters_sha256' if case == 'fixed-four' else 'three_slot_requirements_sha256'
                        ad[key] = check.sha(root / name)
                        check.save(root / 'admission.template.json', ad)
                with self.subTest(case=case), self.assertRaises(AssertionError):
                    check.validate(root, ROOT)

if __name__ == '__main__':
    unittest.main()
