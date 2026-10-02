#!/usr/bin/env python3
import hashlib
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unlanded  # noqa: E402


def git(repo, *args):
    subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True,
                   env={**os.environ, 'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@t', 'GIT_COMMITTER_NAME': 't',
                        'GIT_COMMITTER_EMAIL': 't@t'})


class UnlandedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name)
        # master is a prefix of the lane name on purpose (westlake-harness vs westlake-harness-lane)
        self.repo = self.ws / 'westlake-harness'
        self.lane = self.ws / 'westlake-harness-lane'
        for d in (self.repo, self.lane):
            (d / 'benchmark/x').mkdir(parents=True)
            git(d, 'init', '-q')
        (self.repo / 'benchmark/x/a.txt').write_text('A\n')
        (self.repo / 'benchmark/x/old.txt').write_text('master newer\n')
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-qm', 'm')
        (self.lane / 'benchmark/x/a.txt').write_text('A\n')
        old = self.lane / 'benchmark/x/old.txt'
        old.write_text('lane old\n')
        past = time.time() - 3600
        os.utime(old, (past, past))
        self.listing = self.lane / 'benchmark/x/landing-paths.txt'
        self.listing.write_text('benchmark/x/a.txt\nbenchmark/x/old.txt\n')

    def tearDown(self):
        self.tmp.cleanup()

    def rows(self, acks=None):
        return unlanded.scan(self.ws, self.repo, hours=24, acks=acks)

    def test_identical_and_master_newer_is_not_unlanded(self):
        (r,) = self.rows()
        self.assertEqual(r['status'], 'master-newer')
        self.assertEqual(r['same'], 1)

    def test_missing_file_is_unlanded_and_ack_needs_same_sha(self):
        (self.lane / 'benchmark/x/new.txt').write_text('new\n')
        self.listing.write_text(self.listing.read_text() + 'benchmark/x/new.txt\n')
        (r,) = self.rows()
        self.assertEqual(r['status'], 'UNLANDED')
        self.assertEqual(r['missing'], ['benchmark/x/new.txt'])
        key = ('westlake-harness-lane', 'benchmark/x/landing-paths.txt')
        good = hashlib.sha256(self.listing.read_bytes()).hexdigest()
        self.assertEqual(self.rows({key: good})[0]['status'], 'acked')
        self.assertEqual(self.rows({key: '0' * 64})[0]['status'], 'UNLANDED')

    def test_lane_newer_differs_is_unlanded(self):
        (self.lane / 'benchmark/x/a.txt').write_text('A2\n')
        (r,) = self.rows()
        self.assertEqual(r['status'], 'UNLANDED')
        self.assertEqual(r['lane_newer'], ['benchmark/x/a.txt'])

    def test_master_itself_is_not_scanned_as_a_lane(self):
        (self.repo / 'benchmark/x/landing-paths.txt').write_text('benchmark/x/a.txt\n')
        self.assertEqual([r['worktree'] for r in self.rows()], ['westlake-harness-lane'])


if __name__ == '__main__':
    unittest.main()
