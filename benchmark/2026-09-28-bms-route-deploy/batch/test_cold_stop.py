import tempfile
import unittest
from pathlib import Path

import bms_batch

UID = 20010112
PARENT = 100


class FakeBoard:
    """ps shows the app until kill -9 has been issued for every app PID.

    `readlink /proc/<pid>/exe` is modelled too: appspawn-x processes default to the real U13 daemon binary
    (/system/bin/appspawn-x) unless overridden via `exes` (e.g. a Route B byte-copy at /data/local/tmp/asx)."""

    def __init__(self, rows, exes=None):
        self.rows = rows
        self.killed = []
        self.exes = dict(exes or {})
        for p, pp, u, n in rows:
            if n == 'appspawn-x':
                self.exes.setdefault(p, '/system/bin/appspawn-x')

    def shell(self, command, required=True, **kw):
        if command.startswith('ps '):
            alive = [r for r in self.rows if r[0] not in self.killed]
            return 0, 'PID PPID UID NAME\n' + '\n'.join(f'{p} {pp} {u} {n}' for p, pp, u, n in alive)
        if command.startswith('readlink /proc/'):
            return 0, self.exes.get(int(command.split('/')[2]), '') + '\n'
        if 'kill -9' in command:
            self.killed.append(int(command.rsplit(' ', 1)[1]))
        return 0, ''


def rows(*extra):
    return [(PARENT, 1, 0, 'appspawn-x'), (500, PARENT, UID, 'appspawn-x')] + list(extra)


class ColdStopTests(unittest.TestCase):
    def run_stop(self, board):
        with tempfile.TemporaryDirectory() as d:
            return bms_batch.cold_stop(board, 'org.videolan.vlc', UID, Path(d))

    def test_app_with_forked_helper_is_stopped(self):
        board = FakeBoard(rows((501, 500, UID, 'sh')))
        self.assertTrue(self.run_stop(board))
        self.assertEqual(board.killed, [501, 500])

    def test_plain_app_child_is_stopped(self):
        board = FakeBoard(rows())
        self.assertTrue(self.run_stop(board))
        self.assertEqual(board.killed, [500])

    def test_foreign_process_with_app_uid_is_refused(self):
        board = FakeBoard(rows((700, 1, UID, 'sh')))
        with self.assertRaises(bms_batch.AppFailure):
            self.run_stop(board)
        self.assertEqual(board.killed, [])

    def test_route_b_spawner_in_parents_excluded_by_exe(self):
        # #91: a Route B byte-copy spawner runs uid0/ppid1/NAME=appspawn-x too; counted naively it makes
        # len(parents)==2 and no root classifies. It must be excluded by exe so the app still cold-stops.
        board = FakeBoard(rows((888, 1, 0, 'appspawn-x')),
                          exes={888: '/data/local/tmp/asx/appspawn-x'})
        self.assertTrue(self.run_stop(board))
        self.assertEqual(board.killed, [500])          # only the app root; the daemon/Route B spawner untouched

    def test_renamed_app_root_is_stopped(self):
        # a root whose comm was renamed to the bundle name (SetProcessName) is still the daemon's app-UID child.
        board = FakeBoard([(PARENT, 1, 0, 'appspawn-x'), (500, PARENT, UID, 'com.example.hel')])
        self.assertTrue(self.run_stop(board))
        self.assertEqual(board.killed, [500])

    def test_late_fork_survivor_is_rekilled(self):
        # #91: a heavy app (fd-organicmaps) forks a helper DURING teardown; after the app root is killed the helper
        # reparents to init (ppid=1) and so was not in the initial sweep. The old 2 s poll-only path saw it still
        # alive and returned False ("cleanup could not be verified"). The settle loop must re-kill app-UID survivors.
        class LateForkBoard(FakeBoard):
            def __init__(self, *a, **kw):
                super().__init__(*a, **kw)
                self.ps_calls = 0
            def shell(self, command, required=True, **kw):
                if command.startswith('ps '):
                    self.ps_calls += 1
                    if self.ps_calls == 2 and (600, 1, UID, 'sh') not in self.rows:
                        self.rows.append((600, 1, UID, 'sh'))  # late fork, reparented to init after root death
                return super().shell(command, required=required, **kw)
        board = LateForkBoard(rows())
        self.assertTrue(self.run_stop(board))
        self.assertEqual(board.killed, [500, 600])  # app root, then the late fork re-killed on the next pass


if __name__ == '__main__':
    unittest.main()
