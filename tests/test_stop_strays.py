"""config.sh's stop_strays: the board shell code that stops what failed or repeated launches left running."""

import os
import re
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / 'device' / 'config.sh'

# The board's toybox ps prints a blank header line even with empty column names, hence the callers' tail -n 1.
FAKE_PS = textwrap.dedent('''\
    #!/usr/bin/env python3
    import os, sys
    rows = [line.rstrip('\\n').split(' ', 2) for line in open(os.environ['FAKE_PROCS'])]
    args = sys.argv[1:]
    if args[:3] == ['-A', '-o', 'pid=,ppid=']:
        print()
        for pid, ppid, _ in rows:
            print(f'{pid:>6} {ppid:>5}')
    elif len(args) == 4 and args[0] == '-o' and args[2] == '-p':
        print()
        for pid, ppid, name in rows:
            if pid == args[3]:
                print(f'{ppid:>5}' if args[1] == 'ppid=' else name)
    else:
        sys.exit('fake ps: unexpected arguments %r' % args)
    ''')
FAKE_PIDOF = textwrap.dedent('''\
    #!/bin/bash
    grep " $1\\( \\|$\\)" "$FAKE_PROCS" | cut -d' ' -f1 | xargs
    ''')
FAKE_KILL = textwrap.dedent('''\
    #!/bin/bash
    [ "$1" = -9 ] && shift
    echo "$@" >> "$FAKE_KILLED"
    ''')
# hdc -t <serial> shell <command>: the command runs here, with the fake ps, pidof and kill first on the path
# (kill is a shell builtin, so it is turned off for the fake to be found).
FAKE_HDC = textwrap.dedent('''\
    #!/bin/bash
    exec bash -c "enable -n kill; $4"
    ''')


class StopStraysTest(unittest.TestCase):
    PROCESSES = [
        (1, 0, 'init'),
        (999, 1, 'org.westlake.imehost'),
        # The Play services host: its zygote and the processes it declares.
        (100, 1, 'appspawn-x --socket-name A2HSource000100'),
        (101, 100, 'com.google.android.gms'),
        (102, 100, 'com.google.android.gms.persistent'),
        # The Play Store host.
        (200, 1, 'appspawn-x --socket-name A2HSource000200'),
        (201, 200, 'com.android.vending'),
        (202, 200, 'com.android.vending:background'),
        # A launch the launcher lost track of: its app, and a helper the app started.
        (300, 1, 'appspawn-x --socket-name A2HSource000300'),
        (301, 300, 'com.example.lost'),
        (302, 301, 'com.example.lost:helper'),
        # A zygote whose app has already exited.
        (400, 1, 'appspawn-x --socket-name A2HSource000400'),
        # A zygote init has not adopted yet: some other process still owns it.
        (500, 999, 'appspawn-x --socket-name A2HSource000500'),
    ]

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.bin = root / 'bin'
        self.bin.mkdir()
        for name, text in (('ps', FAKE_PS), ('pidof', FAKE_PIDOF), ('kill', FAKE_KILL), ('hdc', FAKE_HDC)):
            (self.bin / name).write_text(text)
            (self.bin / name).chmod(0o755)
        self.procs = root / 'procs'
        self.procs.write_text(''.join(f'{pid} {ppid} {name}\n' for pid, ppid, name in self.PROCESSES))
        self.killed = root / 'killed'

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_stop_strays(self, dry: bool = False) -> list:
        function = re.search(r'^stop_strays\(\) \{\n.*?\}\n', CONFIG.read_text(), re.S | re.M)[0]
        script = f'WHDC={self.bin}/hdc; T=serial\n{function}stop_strays\n'
        env = dict(os.environ, PATH=f'{self.bin}:{os.environ["PATH"]}', FAKE_PROCS=str(self.procs),
                   FAKE_KILLED=str(self.killed), BASH_ENV='')
        env.pop('STRAYS_DRY', None)
        if dry:
            env['STRAYS_DRY'] = '1'
        result = subprocess.run(['bash', '-c', script], capture_output=True, text=True, env=env, check=True)
        return result.stdout.split('\n')[:-1]

    def killed_pids(self) -> set:
        if not self.killed.exists():
            return set()
        return {int(pid) for pid in self.killed.read_text().split()}

    def test_stops_lost_launches_with_their_processes(self):
        self.assertEqual(self.run_stop_strays(), ['stray 300 301 302', 'stray 400'])
        self.assertEqual(self.killed_pids(), {300, 301, 302, 400})

    def test_keeps_the_play_hosts_and_everything_not_adopted_by_init(self):
        self.run_stop_strays()
        for pid in (1, 999, 100, 101, 102, 200, 201, 202, 500):
            self.assertNotIn(pid, self.killed_pids())

    def test_a_dry_run_only_names_them(self):
        self.assertEqual(self.run_stop_strays(dry=True), ['stray 300 301 302', 'stray 400'])
        self.assertEqual(self.killed_pids(), set())


if __name__ == '__main__':
    unittest.main()
