#!/usr/bin/env python3
"""Known answers: template normalisation, and multiwin's misroute on the 11 outer-signed paired runs (white <=> True).
The paired-run test is skipped when the real runs are not on this machine."""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import multiwin  # noqa: E402
import templates  # noqa: E402


class Norm(unittest.TestCase):
    def test_trace_prefix_and_numbers(self):
        a = templates.norm('[a92ab174ee968b0, 93e822, 324142e] OH callback state=3 tok=0x7f35b4c140', 'org.x')
        b = templates.norm('OH callback state=9 tok=0x1', 'org.x')
        self.assertEqual(a, b)

    def test_class_linker_collapses_to_class(self):
        self.assertEqual(templates.norm('[class_linker.cc:12] [VTLEN-EXIT] klass=org.x.Foo$1 slot=3', 'org.x'), 'CLS <PKG>.Foo$1')


class PairedMisroute(unittest.TestCase):
    def test_eleven_runs(self):
        runs = json.loads((HERE / 'pairs.json').read_text())['runs']
        ws = str(templates.lab_paths.workspaces())
        paths = [r['run'].replace('$WORKSPACES', ws) for r in runs]
        if not all((Path(p) / 'hilog.txt').is_file() for p in paths):
            self.skipTest('paired runs not present')
        got = [multiwin.analyse(p)['misroute'] for p in paths]
        self.assertEqual(got, [r['label'] == 'white' for r in runs])


if __name__ == '__main__':
    unittest.main()
