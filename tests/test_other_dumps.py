"""config.sh's other_dumps: the crash dumps of an app's other processes, by pid, process name and launch time."""

import os
import re
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / 'device' / 'config.sh'

# hdc -t <serial> shell <command>: the command runs here, with the board's /data/ under a directory standing for it;
# its output names board paths again, and ends each line with \r\n, as hdc's terminal does.
FAKE_HDC = textwrap.dedent('''\
    #!/bin/bash
    bash -c "$(printf '%s' "$4" | sed "s#/data/#$FAKE_ROOT/data/#g")" | sed "s#$FAKE_ROOT##g; s/\\$/\\r/"
    ''')


class OtherDumpsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.bin = root / 'bin'
        self.bin.mkdir()
        (self.bin / 'hdc').write_text(FAKE_HDC)
        (self.bin / 'hdc').chmod(0o755)
        self.root = root / 'board'
        for d in ('data/local/tmp', 'data/log/faultlog/temp', 'data/log/faultlog/faultlogger'):
            (self.root / d).mkdir(parents=True)
        mark = self.root / 'data/local/tmp/ev-launch.mark'
        mark.write_text('')
        os.utime(mark, (1000, 1000))
        self.log = root / 'logs' / 'hk-com.example.app.stderr'
        self.log.parent.mkdir()
        self.log.write_text('\n'.join([
            '[WL-PROC] started com.example.app:push pid=777',
            '[WL-PROC] started com.example.app:svc pid=778',
            '[WL-PROC] started com.example.app:old pid=779',
            '[WL-PROC] started com.example.app:quiet pid=780',
        ]) + '\n')
        self.out = root / 'logs' / 'hk-com.example.app.processes'

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def dump(self, where: str, name: str, pid: int, process: str, mtime: int) -> None:
        path = self.root / 'data/log/faultlog' / where / name
        path.write_text(f'Timestamp:2026-11-23 10:51:58.663\nPid:{pid}\nUid:20010054\n'
                        f'Process name:{process}\nReason:Signal:SIGSEGV(SEGV_MAPERR)\n')
        os.utime(path, (mtime, mtime))

    def other_dumps(self) -> None:
        function = re.search(r'^other_dumps\(\) \{\n.*?^\}\n', CONFIG.read_text(), re.S | re.M)[0]
        script = f'WHDC={self.bin}/hdc; T=serial\n{function}other_dumps {self.log} {self.out}\n'
        env = dict(os.environ, FAKE_ROOT=str(self.root), BASH_ENV='')
        subprocess.run(['bash', '-c', script], capture_output=True, text=True, env=env, check=True)

    def saved(self) -> list:
        return sorted(path.name for path in self.out.iterdir()) if self.out.exists() else []

    def test_saves_the_dump_of_each_process_that_crashed_since_the_launch(self):
        self.dump('temp', 'cppcrash-777-2000', 777, 'com.example.app:push', 2000)
        self.other_dumps()
        self.assertEqual(self.saved(), ['com.example.app:push-777.cppcrash'])
        text = (self.out / 'com.example.app:push-777.cppcrash').read_text()
        self.assertIn('Process name:com.example.app:push\n', text)
        self.assertNotIn('\r', text)

    def test_a_reused_pid_of_another_app_is_not_its_dump(self):
        self.dump('faultlogger', 'cppcrash-org.host-20010054-2.log', 778, 'com.other.app', 2000)
        self.other_dumps()
        self.assertEqual(self.saved(), [])

    def test_a_dump_from_before_the_launch_is_not_its_dump(self):
        self.dump('temp', 'cppcrash-779-900', 779, 'com.example.app:old', 900)
        self.other_dumps()
        self.assertEqual(self.saved(), [])

    def test_no_dump_no_directory(self):
        self.other_dumps()
        self.assertFalse(self.out.exists())


if __name__ == '__main__':
    unittest.main()
