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

    def test_branch_residue(self):
        """branch_residue: a.txt master-still-at-merge-base, b.txt master-changed (not reported), c.txt missing-on-master."""
        # use a single repo with a branch; lane worktree is that branch checked out
        repo = self.repo
        lane_branch = 'lane-branch'
        # base commit on master with a.txt + b.txt
        (repo / 'benchmark/x/a.txt').write_text('A\n')
        (repo / 'benchmark/x/b.txt').write_text('B\n')
        git(repo, 'add', '.')
        git(repo, 'commit', '-qm', 'base')
        # create lane branch, change a.txt + add c.txt there
        git(repo, 'checkout', '-qb', lane_branch)
        (repo / 'benchmark/x/a.txt').write_text('A-lane\n')
        (repo / 'benchmark/x/b.txt').write_text('B-lane\n')  # also edited on master below -> must not be reported
        (repo / 'benchmark/x/c.txt').write_text('C\n')
        git(repo, 'add', '.')
        git(repo, 'commit', '-qm', 'lane')
        # back to master, change b.txt
        git(repo, 'checkout', '-q', '-B', 'master', 'HEAD~1')
        (repo / 'benchmark/x/b.txt').write_text('B-master\n')
        git(repo, 'add', '.')
        git(repo, 'commit', '-qm', 'master')
        # lane worktree = lane branch checked out in a separate dir
        lane_wt = self.ws / 'westlake-harness-lane-wt'
        git(repo, 'worktree', 'add', '-q', str(lane_wt), lane_branch)
        try:
            res = unlanded.branch_residue(lane_wt, repo)
            self.assertEqual([r[0] for r in res], ['benchmark/x/a.txt', 'benchmark/x/c.txt'])
            self.assertEqual([r[1] for r in res], ['master-still-at-merge-base', 'missing-on-master'])
        finally:
            git(repo, 'worktree', 'remove', '--force', str(lane_wt))


if __name__ == '__main__':
    unittest.main()
