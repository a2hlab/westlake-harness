#!/usr/bin/env python3
"""pair_sheet window2 known-answer: the 11 named sweep keys all pair, smoke keys excluded, verdict left blank."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import pair_sheet  # noqa: E402

WORKSPACES = Path(__file__).resolve().parents[4]
WINDOW2 = (WORKSPACES / 'westlake-harness-u7-executor/benchmark/2026-10-02-u10-1-t8-rerun'
           / 'window2/boards/u101-t8-A2-20261002T065106')
EXPECTED = {'fd-tusky', 'fd-seal', 'fd-stk', 'aegis', 'fd-catima', 'fd-com-kunzisoft-keepass-libre',
            'fd-feeder', 'fd-fitness', 'fd-mpv', 'fd-tasks', 'ooniprobe'}


class PairSheet(unittest.TestCase):
    @unittest.skipUnless(WINDOW2.is_dir(), 'window2 run dir not present')
    def test_window2_known_answer(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(pair_sheet.main(['--run', str(WINDOW2), '--no-sheet', '--out', d]), 0)
            data = json.loads((Path(d) / 'pair-sheet.json').read_text())
        keys = {p['key'] for p in data['pairs']}
        self.assertTrue(EXPECTED.issubset(keys), f'missing expected keys: {sorted(EXPECTED - keys)}')
        self.assertNotIn('helloworld', keys)  # smoke shard skipped
        self.assertNotIn('zigzag', keys)      # smoke shard skipped
        for p in data['pairs']:
            self.assertEqual(p['window_verdict'], '')     # never auto-judged
            self.assertIsNotNone(p['u9_verdict'])         # every paired key resolved its U9 verdict
            self.assertIn('u9_t20', p)
            self.assertIn('window_t20', p)


if __name__ == '__main__':
    unittest.main()
