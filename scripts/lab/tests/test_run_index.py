#!/usr/bin/env python3
"""run_index: one row per (run, key) with unknown-sessionId counts; landed copies of a run are indexed once."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_index as ri  # noqa: E402

FACTS = """RUNTIME fingerprint=e953c0921536 files=119 (x)
BOOTIMAGE fingerprint=4db882a81732 files=36 (x)
wikipedia            shots 2/2  alive t5=yes t20=yes  child_hilog=56453  foreground_unconfirmed
TOTAL keys=1 screenshots_captured=2/2 alive_t5=1 alive_t20=1
"""


class RunIndex(unittest.TestCase):
    def test_build_and_query(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ['WORKSPACES'] = d
            for copy in ('lane', 'master'):
                run = Path(d) / copy / '20261001T133902-470fa595' / '61b0657200000000000000000324012c'
                (run / 'wikipedia').mkdir(parents=True)
                (run / 'facts.txt').write_text(FACTS)
                (run / 'wikipedia/hilog.txt').write_text(
                    'x E OH_WindowMgrClient: getOhNativeWindow: unknown sessionId=352\n'
                    'y E AndroidRuntime: FATAL EXCEPTION: main\n')
            idx = Path(d) / 'index.jsonl'
            self.assertEqual(ri.build([d], idx), 1)
            row = json.loads(idx.read_text().splitlines()[0])
            self.assertEqual((row['key'], row['runtime_fp'], row['alive_t20'], row['unknown_session']),
                             ('wikipedia', 'e953c0921536', 'yes', 1))
            self.assertIn('FATAL EXCEPTION', row['first_fatal'])
            self.assertTrue(row['run'].startswith('$WORKSPACES'))


if __name__ == '__main__':
    unittest.main()
