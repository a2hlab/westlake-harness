import contextlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_user_paths

# Built at run time so this file itself holds no home path for the gate to flag.
HOME_PATH = '/' + 'home' + '/someone'
MAC_PATH = '/' + 'Users' + '/someone'


def table(d, entries=()):
    t = pathlib.Path(d) / 'exceptions.json'
    t.write_text(json.dumps({'exceptions': list(entries)}))
    return str(t)


def run(d, entries=(), files=None):
    rels = files or [str(p.relative_to(d)) for p in sorted(pathlib.Path(d).rglob('*'))
                     if p.is_file() and p.name != 'exceptions.json']
    return gate(['--root', str(d), '--exceptions', table(d, entries)] + rels)


def gate(argv):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return check_user_paths.main(argv)


def write(d, rel, text):
    p = pathlib.Path(d) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


class GateTests(unittest.TestCase):
    def test_repo_passes(self):
        self.assertEqual(gate([]), 0)

    def test_violation_is_caught(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, 'tools/run.sh', f'#!/bin/bash\nHDC={MAC_PATH}/orca/workspaces/westlake-inputs/tools/hdc_mac.sh\n')
            self.assertEqual(run(d), 1)

    def test_default_expansion_and_bare_home_are_caught(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, 'a.sh', 'W=${WORKSPACES:-' + MAC_PATH + '/orca/workspaces}\n')
            write(d, 'b/Dockerfile', 'ENV HOME=' + HOME_PATH + '\n')
            self.assertEqual(run(d, files=['a.sh']), 1)
            self.assertEqual(run(d, files=['b/Dockerfile']), 1)

    def test_excepted_prefix_is_allowed_only_where_scoped(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, 'vendor/x.sh', f'CC={HOME_PATH}/toolchain/clang\n')
            allow = {'pattern': HOME_PATH, 'reason': 'r', 'evidence': 'e'}
            self.assertEqual(run(d, [allow]), 0)
            self.assertEqual(run(d, [dict(allow, files=['vendor/*'])]), 0)
            self.assertEqual(run(d, [dict(allow, files=['other/*'])]), 1)
            self.assertEqual(run(d, [dict(allow, pattern=HOME_PATH[:-1])]), 1)   # a shorter name is not a prefix match

    def test_excepted_file_glob_is_exempt(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, 'benchmark/x/evidence/receipt.env', f'apk={MAC_PATH}/payload/app.apk\n')
            self.assertEqual(run(d), 1)
            self.assertEqual(run(d, [{'pattern': 'benchmark/*/evidence/*', 'reason': 'r', 'evidence': 'e'}]), 0)

    def test_docs_and_non_homes_are_not_hits(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, 'notes.md', f'moved from {MAC_PATH}/orca\n')
            write(d, 'data.json', json.dumps({'p': HOME_PATH + '/x'}))
            write(d, 'ok.sh', 'D=/storage/Users/currentUser/Download\nH=$HOME/a2hlab\nV=/home/$USER/x\n'
                              'case $p in /Users/*) ;; esac\n# minimize/home/recents\n')
            self.assertEqual(run(d), 0)

    def test_symlink_target_is_checked(self):
        with tempfile.TemporaryDirectory() as d:
            os.symlink(MAC_PATH + '/bin/tool', os.path.join(d, 'tool'))
            self.assertEqual(run(d, files=['tool']), 1)

    def test_malformed_table_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, 'ok.sh', 'echo ok\n')
            self.assertEqual(run(d, [{'pattern': HOME_PATH, 'reason': 'r'}]), 2)
            self.assertEqual(run(d, [{'pattern': 'a/*', 'reason': 'r', 'evidence': 'e', 'files': ['b/*']}]), 2)


class LabPathsTests(unittest.TestCase):
    """WORKSPACES resolves the same from scripts/lab/ and from its mirror westlake-inputs/tools/."""

    def layout(self, root):
        lab = root / 'westlake-harness/scripts/lab'
        mirror = root / 'westlake-inputs/tools'
        for d in (lab, mirror):
            d.mkdir(parents=True)
            for f in ('lab_paths.py', 'lab_paths.sh'):
                shutil.copy2(HERE / f, d / f)
        return lab, mirror

    def env(self):
        e = dict(os.environ)
        e.pop('WORKSPACES', None)
        return e

    def test_python_walk_up_from_both_locations(self):
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t).resolve()
            for d in self.layout(root):
                out = subprocess.run([sys.executable, '-c', 'import lab_paths; print(lab_paths.workspaces())'],
                                     cwd='/', env=dict(self.env(), PYTHONPATH=str(d)),
                                     capture_output=True, text=True, check=True).stdout.strip()
                self.assertEqual(out, str(root))

    def test_bash_walk_up_from_both_locations(self):
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t).resolve()
            for d in self.layout(root):
                script = d / 'probe.sh'
                script.write_text('. "$(dirname "${BASH_SOURCE[0]}")/lab_paths.sh" || exit 1\necho "$WORKSPACES"\n')
                out = subprocess.run(['bash', str(script)], cwd='/', env=self.env(),
                                     capture_output=True, text=True, check=True).stdout.strip()
                self.assertEqual(out, str(root))

    def test_env_override_and_failure(self):
        with tempfile.TemporaryDirectory() as t:
            lone = pathlib.Path(t).resolve() / 'x'
            lone.mkdir()
            shutil.copy2(HERE / 'lab_paths.sh', lone / 'lab_paths.sh')
            (lone / 'probe.sh').write_text('. "$(dirname "$0")/lab_paths.sh" || exit 3\necho "$WORKSPACES"\n')
            out = subprocess.run(['bash', str(lone / 'probe.sh')], env=dict(self.env(), WORKSPACES='/w'),
                                 capture_output=True, text=True).stdout.strip()
            self.assertEqual(out, '/w')
            r = subprocess.run(['bash', str(lone / 'probe.sh')], env=self.env(), capture_output=True, text=True)
            self.assertEqual(r.returncode, 3)


if __name__ == '__main__':
    unittest.main()
