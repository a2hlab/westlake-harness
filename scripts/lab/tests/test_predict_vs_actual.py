#!/usr/bin/env python3
"""predict_vs_actual: covered clusters become lit?, baseline lit must stay lit, compare classes each key."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import predict_vs_actual as pva  # noqa: E402

CLUSTERS = {'clusters': [{'name': 'appcompat', 'keys': ['knot'], 'coverage': {'j10b': 'action bar'}},
                         {'name': 'other', 'keys': ['x'], 'coverage': {}}]}


class Predict(unittest.TestCase):
    def test_predict_and_compare(self):
        base = {'hw': 'lit', 'knot': 'dead', 'x': 'dead', 'w': 'lit'}
        rows = pva.predict(base, CLUSTERS, {'j10b'}, [], {}, {'w'})
        pred = {r['key']: r['prediction'] for r in rows}
        self.assertEqual(pred, {'hw': 'lit', 'knot': 'lit?', 'x': 'dead', 'w': 'flaky'})
        out = {r['key']: r['result'] for r in pva.compare(rows, {'hw': 'dead', 'knot': 'dead', 'x': 'lit', 'w': 'dead'})}
        self.assertEqual(out, {'hw': 'regression', 'knot': 'missed-wall', 'x': 'unexpected-lit', 'w': 'flaky'})

    def test_cover_and_observed(self):
        rows = pva.predict({'x': 'dead', 'y': 'dead'}, CLUSTERS, {'j10b'}, [('other', 'j10b')],
                           {'y': ('lit', 'window r3')}, set())
        self.assertEqual({r['key']: r['prediction'] for r in rows}, {'x': 'lit?', 'y': 'lit'})


if __name__ == '__main__':
    unittest.main()
