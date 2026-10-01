#!/usr/bin/env python3
"""board_run: the dispatch text carries every fixed rule; a plan missing a field or reusing an output dir is refused."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import board_run  # noqa: E402

EXAMPLE = HERE.parents[1] / 'knowledge/smoke/example-board-run.json'


class BoardRun(unittest.TestCase):
    def test_dispatch_has_every_rule(self):
        text = board_run.dispatch_text(json.loads(EXAMPLE.read_text()), EXAMPLE)
        for rule in board_run.RULES:
            self.assertIn(rule, text)
        for must in ('--hilog', 'LOCK', '冒烟', '只跑一个', '不删'):
            self.assertIn(must, text)

    def test_missing_field_refused(self):
        with tempfile.TemporaryDirectory() as d:
            plan = json.loads(EXAMPLE.read_text()); del plan['smoke_spec']
            p = Path(d) / 'p.json'; p.write_text(json.dumps(plan))
            r = subprocess.run([sys.executable, str(HERE / 'board_run.py'), str(p)], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0); self.assertIn('plan missing smoke_spec', r.stderr)

    def test_existing_output_refused_before_lock(self):
        with tempfile.TemporaryDirectory() as d:
            plan = json.loads(EXAMPLE.read_text()); plan['out'] = d     # exists already
            p = Path(d) / 'p.json'; p.write_text(json.dumps(plan))
            r = subprocess.run([sys.executable, str(HERE / 'board_run.py'), str(p)], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0); self.assertIn('exists', r.stderr)


if __name__ == '__main__':
    unittest.main()
