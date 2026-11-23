"""device/identity.sh: the identity the board reports to apps and Google's device status, and the round's guard."""

import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / 'device' / 'identity.sh'

# hdc -t <serial> shell <command>: the command runs here, with the board's /data/ under a directory standing for it;
# its output names board paths again and ends each line with \r\n, as hdc's terminal does.
FAKE_HDC = textwrap.dedent('''\
    #!/bin/bash
    bash -c "$(printf '%s' "$4" | sed "s#/data/#$FAKE_ROOT/data/#g")" | sed "s#$FAKE_ROOT##g; s/\\\\$/\\\\r/"
    ''')
# OH's param get: the value and a space, or a failure naming errNum 106 for a parameter nobody set.
FAKE_PARAM = textwrap.dedent('''\
    #!/bin/bash
    [ "$1" = get ] || exit 1
    v=$(grep -m1 "^$2=" "$FAKE_PARAMS" | cut -d= -f2-)
    if [ -n "$v" ]; then echo "$v "; else echo "Get parameter \\"$2\\" fail! errNum is:106!"; fi
    ''')
REAL = {"ro.product.manufacturer": "HopeRun", "ro.product.model": "D600", "ro.build.version.release": "15",
        "ro.build.version.sdk": "35", "ro.soc.manufacturer": "Unisoc", "ro.soc.model": "UMS9620"}


class IdentityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.bin = root / 'bin'
        self.bin.mkdir()
        for name, text in (('hdc', FAKE_HDC), ('param', FAKE_PARAM)):
            (self.bin / name).write_text(text)
            (self.bin / name).chmod(0o755)
        self.board = root / 'board'
        self.params = root / 'params'
        self.params.write_text('')
        self.out = root / 'identity.json'

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def set_params(self, values: dict) -> None:
        self.params.write_text(''.join('%s=%s\n' % kv for kv in values.items()))

    def gservices(self, status: str, stage: str = 'efde566a') -> None:
        d = self.board / 'data/app/el2/100/base/org.westlake.playhost/files' / ('a2hlab-source-' + stage) / \
            'app-data/com.google.android.gms/westlake-gservices'
        d.mkdir(parents=True)
        (d / 'values.properties').write_text('some_flag=1\nuncertified_status=%s\nother=secret\n' % status)

    def run_identity(self, *expect: str) -> subprocess.CompletedProcess:
        env = dict(os.environ, WL_SC=str(Path(self.tmp.name) / 'sc'), HDC=str(self.bin / 'hdc'), HDC_TARGET='serial',
                   FAKE_ROOT=str(self.board), FAKE_PARAMS=str(self.params), PATH='%s:%s' % (self.bin, os.environ['PATH']),
                   BASH_ENV='')
        return subprocess.run(['bash', str(SCRIPT), str(self.out), *expect], capture_output=True, text=True, env=env)

    def test_the_identity_and_googles_status_are_recorded(self):
        self.set_params(REAL)
        self.gservices('1')
        result = self.run_identity()
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads(self.out.read_text())
        self.assertEqual(record['identity']['ro.build.version.sdk'], '35', 'the value without param get\'s space')
        self.assertEqual(record['identity']['ro.soc.model'], 'UMS9620')
        self.assertIsNone(record['identity']['ro.build.fingerprint'], 'a parameter nobody set is null')
        self.assertEqual((record['google']['uncertified_status'], record['google']['stage']), ('1', 'efde566a'))
        self.assertEqual(result.stdout.strip().splitlines()[-1],
                         'identity: HopeRun D600, Android 15 (API 35), Unisoc UMS9620; Google: allowed')
        self.assertNotIn('secret', self.out.read_text(), 'no other Gservices value is read')

    def test_a_board_that_lost_its_identity_is_not_the_expected_device(self):
        """After a reboot the parameters are gone: Westlake answers from its built-in tables."""
        self.gservices('3')
        result = self.run_identity('ro.build.version.sdk=35', 'ro.soc.model=UMS9620')
        self.assertEqual(result.returncode, 3)
        last = result.stdout.strip().splitlines()[-1]
        self.assertIn('Google: restricted', last)
        self.assertIn('NOT THE EXPECTED IDENTITY: ro.build.version.sdk=35 (board: None), ro.soc.model=UMS9620 (board: None)',
                      last)

    def test_the_expected_identity_passes(self):
        self.set_params(REAL)
        self.assertEqual(self.run_identity('ro.build.version.sdk=35', 'ro.soc.model=UMS9620').returncode, 0)
        self.assertEqual(self.run_identity('ro.build.version.sdk=34').returncode, 3)

    def test_no_play_services_data_yet(self):
        self.set_params(REAL)
        result = self.run_identity()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(self.out.read_text())['google'], {})
        self.assertIn('Google: unknown', result.stdout)


if __name__ == '__main__':
    unittest.main()
