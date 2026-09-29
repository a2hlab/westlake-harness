import tempfile
import unittest
from pathlib import Path

import bms_batch

UID = 20010112
PARENT = 100


class FakeBoard:
    """ps shows the app until kill -9 has been issued for every app PID."""

    def __init__(self, rows):
        self.rows = rows
        self.killed = []

    def shell(self, command, required=True, **kw):
        if command.startswith('ps '):
            alive = [r for r in self.rows if r[0] not in self.killed]
            return 0, 'PID PPID UID NAME\n' + '\n'.join(f'{p} {pp} {u} {n}' for p, pp, u, n in alive)
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


if __name__ == '__main__':
    unittest.main()
