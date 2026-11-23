"""config.sh's child_log: the copy of a child process's log off the board, made again when it comes back empty."""

import os
import re
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / 'device' / 'config.sh'
BOARD = '/data/service/el1/public/appspawnx'

# hdc -t <serial> shell <command>: the command runs here, against a directory that stands for the board's, except
# that the first FAKE_FAILS calls return nothing at all, as a call does when the link drops for a moment.
FAKE_HDC = textwrap.dedent(f'''\
    #!/bin/bash
    calls=$(( $(cat "$FAKE_CALLS" 2>/dev/null || echo 0) + 1 )); echo $calls > "$FAKE_CALLS"
    [ $calls -le ${{FAKE_FAILS:-0}} ] && exit 1
    exec bash -c "$(printf '%s' "$4" | sed "s#{BOARD}#$FAKE_BOARD#g")"
    ''')


class ChildLogTest(unittest.TestCase):
    PID = '4242'

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.bin = root / 'bin'
        self.bin.mkdir()
        (self.bin / 'hdc').write_text(FAKE_HDC)
        (self.bin / 'hdc').chmod(0o755)
        self.board = root / 'board'
        self.board.mkdir()
        self.calls = root / 'calls'
        self.dest = root / 'logs' / 'hk-com.example.app.stderr'
        self.dest.parent.mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def board_log(self) -> Path:
        return self.board / f'adapter_child_{self.PID}.stderr'

    def child_log(self, *extra: str, fails: int = 0) -> int:
        function = re.search(r'^child_log\(\) \{\n.*?^\}\n', CONFIG.read_text(), re.S | re.M)[0]
        script = f'WHDC={self.bin}/hdc; T=serial\n{function}child_log {self.PID} {self.dest} 5 {" ".join(extra)}\n'
        env = dict(os.environ, FAKE_BOARD=str(self.board), FAKE_CALLS=str(self.calls), FAKE_FAILS=str(fails),
                   CHILD_LOG_PAUSE='0', BASH_ENV='')
        return subprocess.run(['bash', '-c', script], capture_output=True, text=True, env=env).returncode

    def leftovers(self) -> list:
        return sorted(path.name for path in self.dest.parent.iterdir() if path.name.endswith('.part'))

    def test_a_copy_that_comes_back_empty_is_made_again(self):
        self.board_log().write_text('line 1\r\nline 2\n')
        self.assertEqual(self.child_log('drop', fails=2), 0)
        self.assertEqual(self.dest.read_text(), 'line 1\nline 2\n')
        self.assertFalse(self.board_log().exists(), 'the board copy goes once a copy arrived')
        self.assertEqual(self.leftovers(), [])

    def test_an_empty_copy_never_replaces_an_earlier_one(self):
        self.dest.write_text('early copy\n')
        self.board_log().write_text('the whole log\n')
        self.assertNotEqual(self.child_log('drop', fails=3), 0)
        self.assertEqual(self.dest.read_text(), 'early copy\n')
        self.assertTrue(self.board_log().exists(), 'the board keeps its copy while none arrived')
        self.assertEqual(self.leftovers(), [])

    def test_no_file_when_no_copy_arrives(self):
        self.board_log().write_text('the whole log\n')
        self.assertNotEqual(self.child_log('drop', fails=3), 0)
        self.assertFalse(self.dest.exists())
        self.assertEqual(self.leftovers(), [])

    def test_a_board_log_that_is_missing_is_no_copy(self):
        self.assertNotEqual(self.child_log('drop'), 0)
        self.assertFalse(self.dest.exists())

    def test_without_drop_the_board_keeps_its_copy(self):
        self.board_log().write_text('the whole log\n')
        self.assertEqual(self.child_log(), 0)
        self.assertEqual(self.dest.read_text(), 'the whole log\n')
        self.assertTrue(self.board_log().exists())


if __name__ == '__main__':
    unittest.main()
