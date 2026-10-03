#!/usr/bin/env python3
"""generation_bundle BCP swap policy: stubs / oh-adapter-framework by default, anything else only by an exact
(segment, reference sha256, candidate sha256) row in knowledge/gates/bcp-swap-exceptions.json.

U15 (2026-10-03) changes framework.jar 3e106350 -> 9e55e286 on purpose (Bitmap.getColorSpace); image_checks refused
it as 'undeclared BCP segment swap: framework' because the allowed set was hard-coded.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
import generation_bundle as gb  # noqa: E402

REF = '3e106350d882cd1f2f6d71c3cc4e9f124412d16f50a2dcb160007c34e6dde9af'
U15 = '9e55e28623c86cc553bb2449cb18948e383a05fb0283b045d969655813b7d1b7'


class Verdict(unittest.TestCase):
    def setUp(self):
        self.excepted = {('framework', REF, U15): 'U15-FRAMEWORK-BITMAP-001'}

    def test_default_segments_need_no_row(self):
        pairs = {j: (j, 'a' * 64, 'b' * 64) for j in ['adapter-mainline-stubs', 'oh-adapter-framework']}
        self.assertEqual(gb.bcp_swap_verdict(pairs, {}), ({}, []))

    def test_exact_row_admits_the_framework_swap(self):
        matched, undeclared = gb.bcp_swap_verdict({'framework': ('framework', REF, U15)}, self.excepted)
        self.assertEqual(matched, {'framework': 'U15-FRAMEWORK-BITMAP-001'})
        self.assertEqual(undeclared, [])

    def test_any_other_hash_on_either_side_is_refused(self):
        for pair in [('framework', REF, 'c' * 64), ('framework', 'c' * 64, U15), ('core-oj', REF, U15)]:
            self.assertEqual(gb.bcp_swap_verdict({pair[0]: pair}, self.excepted), ({}, [pair[0]]), pair)


class Table(unittest.TestCase):
    def write(self, rows):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        path = Path(holder.name) / 'x.json'
        path.write_text(json.dumps({'exceptions': rows}))
        return path

    def test_only_approved_rows_count(self):
        row = dict(id='A', segment='framework', reference_sha256=REF, candidate_sha256=U15)
        self.assertEqual(gb.bcp_swap_exceptions(self.write([dict(row, status='approved')])), {('framework', REF, U15): 'A'})
        self.assertEqual(gb.bcp_swap_exceptions(self.write([dict(row, status='proposed')])), {})
        self.assertEqual(gb.bcp_swap_exceptions(Path(tempfile.gettempdir()) / 'no-such-table.json'), {})

    def test_repository_table_loads_and_carries_the_u15_row(self):
        got = gb.bcp_swap_exceptions(LAB.parents[1] / gb.BCP_SWAP_EXCEPTIONS)
        self.assertEqual(got.get(('framework', REF, U15)), 'U15-FRAMEWORK-BITMAP-001')


if __name__ == '__main__':
    unittest.main()
