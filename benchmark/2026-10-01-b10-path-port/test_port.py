#!/usr/bin/env python3
import hashlib
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPORT = json.loads((HERE / 'results.json').read_text())


class RelocationTests(unittest.TestCase):
    def test_relocated_imports(self):
        targets = {
            'finalize.py': ['BASE', 'WL', 'INV', 'WLSRC', 'WORKSPACE'],
            'finalize_v3.py': ['BASE', 'P75', 'P78'],
            'extract_unified_failures.py': ['SOURCE', 'RUN'],
            'collect_results.py': ['DEFAULT'],
            'prepare.py': ['W', 'SRC'],
        }
        self.assertEqual(set(targets), {Path(item['path']).name for item in REPORT['temporary_files']
                                      if item['action'] == 'ported' and item['path'].endswith('.py')})
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / 'relocated-workspaces'
            for item in REPORT['temporary_files']:
                path = ROOT / item['path']
                if path.name not in targets:
                    continue
                code = ('import runpy,sys; from pathlib import Path; '
                        'sys.path.insert(0,sys.argv[1]); '
                        'data=runpy.run_path(sys.argv[2]); '
                        'parent=Path(sys.argv[3]); '
                        'assert all(data[name].is_relative_to(parent) '
                        'for name in sys.argv[4:])')
                with self.subTest(path=path.name):
                    subprocess.run([sys.executable, '-c', code, str(path.parent),
                                    str(path), str(workspace.parent), *targets[path.name]],
                                   env={**os.environ, 'WORKSPACES': str(workspace)}, check=True)


class PreservationTests(unittest.TestCase):
    def test_exception_delta_and_hashes(self):
        before = json.loads((HERE / 'registry-before.json').read_text())
        current = json.loads((ROOT / 'knowledge/gates/user-path-exceptions.json').read_text())
        removed = {item['path'] for item in REPORT['temporary_files'] if item['action'] == 'ported'}
        expected = []
        for entry in before['exceptions']:
            if 'B10 landing' in entry['reason'] and 'TEMPORARY' in entry['reason']:
                entry['files'] = [path for path in entry['files'] if path not in removed]
                if not entry['files']:
                    continue
            expected.append(entry)
        before['exceptions'] = expected
        self.assertEqual(before, current)
        self.assertEqual((REPORT['ported'], REPORT['retained']), (6, 4))
        for item in REPORT['temporary_files'] + REPORT['permanent_frozen_copies']:
            data = (ROOT / item['path']).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), item['after_sha256'])
            if item.get('action') == 'ported':
                self.assertNotEqual(item['before_sha256'], item['after_sha256'])
                self.assertNotIn(b'/Users/' + b'zhaoyue', data)
                self.assertNotIn(b'/home/' + b'alvin', data)
            else:
                self.assertEqual(item['before_sha256'], item['after_sha256'])
            for evidence in item.get('freeze_evidence', []):
                path = ROOT / evidence
                content = gzip.decompress(path.read_bytes()).decode() if path.suffix == '.gz' else path.read_text()
                self.assertIn(item['before_sha256'], content)


if __name__ == '__main__':
    unittest.main()
