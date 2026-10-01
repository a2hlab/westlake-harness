#!/usr/bin/env python3
"""land.py: lands listed files + doc lines with gates green, rolls back on a red gate, refuses unsafe paths."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

LAND = Path(__file__).resolve().parents[1] / 'land.py'


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True)


class Land(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.repo, self.wt = root / 'master', root / 'lane'
        lab = self.repo / 'scripts/lab'
        lab.mkdir(parents=True)
        (lab / 'check_user_paths.py').write_text('import os,sys\nsys.exit(int(os.environ.get("FAKE_PATH_GATE","0")))\n')
        (lab / 'check_frozen.py').write_text('import sys\nsys.exit(0)\n')
        (self.repo / 'README.md').write_text('| x | y |\n|---|---|\n| **`benchmark/a/`** | **a** |\n\ntail\n')
        (self.repo / '.octos').mkdir()
        (self.repo / '.octos/KNOWLEDGE-DIGEST.md').write_text('# digest\n')
        git(self.repo, 'init', '-q'); git(self.repo, 'add', '.')
        git(self.repo, '-c', 'user.name=t', '-c', 'user.email=t@e', 'commit', '-qm', 'init')
        b = self.wt / 'benchmark/b'
        b.mkdir(parents=True)
        (b / 'results.json').write_text('{}\n')
        (b / 'test_b.py').write_text('import sys\nsys.exit(0)\n')
        (b / 'documentation.json').write_text('{"README.md": ["| **`benchmark/b/`** | **b** |"], '
                                              '".octos/KNOWLEDGE-DIGEST.md": ["- b line"]}')
        (b / 'landing-paths.txt').write_text('benchmark/b/results.json\nbenchmark/b/test_b.py\n'
                                             'benchmark/b/documentation.json\n')
        git(self.wt, 'init', '-q')

    def tearDown(self):
        self.tmp.cleanup()

    def land(self, listing='benchmark/b/landing-paths.txt', *extra, gate='0'):
        env = dict(os.environ, LAND_REPO=str(self.repo), FAKE_PATH_GATE=gate,
                   GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@e', GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@e')
        return subprocess.run([sys.executable, str(LAND), str(self.wt), listing, '-m', 'land b', *extra],
                               capture_output=True, text=True, env=env)

    def test_lands_files_and_doc_lines(self):
        r = self.land()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('LANDED', r.stdout)
        readme = (self.repo / 'README.md').read_text().split('\n')
        self.assertEqual(readme[3], '| **`benchmark/b/`** | **b** |')       # right after the last bold row
        self.assertIn('- b line', (self.repo / '.octos/KNOWLEDGE-DIGEST.md').read_text())
        self.assertIn('benchmark/b/results.json', git(self.repo, 'show', '--name-only', 'HEAD').stdout)

    def test_red_gate_rolls_back(self):
        r = self.land(gate='1')
        self.assertEqual(r.returncode, 1)
        self.assertIn('NOT LANDED', r.stderr)
        self.assertFalse((self.repo / 'benchmark/b/results.json').exists())
        self.assertNotIn('benchmark/b', (self.repo / 'README.md').read_text())
        self.assertEqual(git(self.repo, 'rev-list', '--count', 'HEAD').stdout.strip(), '1')

    def test_refuses_overwriting_cited_evidence(self):
        (self.repo / 'benchmark/b').mkdir(parents=True)
        (self.repo / 'benchmark/b/results.json').write_text('{"approved": 1}\n')
        (self.repo / 'knowledge/gates').mkdir(parents=True)
        (self.repo / 'knowledge/gates/x.json').write_text('{"rows": [{"evidence": ["benchmark/b/results.json"]}]}')
        git(self.repo, 'add', '.'); git(self.repo, '-c', 'user.name=t', '-c', 'user.email=t@e', 'commit', '-qm', 'ev')
        r = self.land()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('cite these files as evidence', r.stderr)
        self.assertEqual((self.repo / 'benchmark/b/results.json').read_text(), '{"approved": 1}\n')

    def test_large_file_refused(self):
        (self.wt / 'benchmark/b/hilog.txt').write_bytes(b'x' * (1024 * 1024 + 1))
        (self.wt / 'l.txt').write_text('benchmark/b/hilog.txt\n')
        r = self.land('l.txt')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('over 1024 KiB', r.stderr)
        self.assertFalse((self.repo / 'benchmark/b/hilog.txt').exists())

    def test_preflight_reports_without_copying(self):
        r = self.land('benchmark/b/landing-paths.txt', '--preflight')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('preflight OK', r.stdout)
        self.assertFalse((self.repo / 'benchmark/b/results.json').exists())

    def test_gate_registry_needs_flag_and_dotdot_refused(self):
        (self.wt / 'knowledge/gates').mkdir(parents=True)
        (self.wt / 'knowledge/gates/x.json').write_text('{}')
        (self.wt / 'l.txt').write_text('knowledge/gates/x.json\n../evil\n')
        r = self.land('l.txt')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('--allow-gates', r.stderr)
        self.assertIn('not a safe relative path', r.stderr)


if __name__ == '__main__':
    unittest.main()
