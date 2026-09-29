import json
import tempfile
import unittest
from pathlib import Path

import bms_batch


class FakeBoard:
    def __init__(self, text):
        self.text = text

    def shell(self, command, required=True):
        return 0, self.text


A = 'a' * 64
B = 'b' * 64


class RuntimeFingerprintTests(unittest.TestCase):
    def test_same_files_in_any_order_give_same_fingerprint(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            one = bms_batch.runtime_fingerprint(FakeBoard(f'{A}  /x.so\n{B}  /y.so\n'), Path(d1))
            two = bms_batch.runtime_fingerprint(FakeBoard(f'{B}  /y.so\r\n{A}  /x.so\r\n'), Path(d2))
            self.assertEqual(one, two)
            self.assertEqual(len(one), 12)

    def test_one_swapped_library_changes_fingerprint(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            one = bms_batch.runtime_fingerprint(FakeBoard(f'{A}  /x.so\n'), Path(d1))
            two = bms_batch.runtime_fingerprint(FakeBoard(f'{B}  /x.so\n'), Path(d2))
            self.assertNotEqual(one, two)

    def test_unreadable_board_gives_none_not_a_guess(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(bms_batch.runtime_fingerprint(FakeBoard('sha256sum: not found\n'), Path(d)))

    def test_facts_lead_with_fingerprint(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            bms_batch.runtime_fingerprint(FakeBoard(f'{A}  /x.so\n'), out)
            key = out/'app'
            key.mkdir()
            (key/'record.json').write_text(json.dumps({'status': 'foreground_unconfirmed', 'screenshots': []}))
            bms_batch.write_facts(out)
            first = (out/'facts.txt').read_text().splitlines()[0]
            self.assertTrue(first.startswith('RUNTIME fingerprint='), first)
            self.assertIn('files=1', first)


if __name__ == '__main__':
    unittest.main()
