import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from delta import snapshot, read_recipe, capture, MAX_DELTA

BIND = 'a'*64
MARK = 'DELTA_'+'b'*32


class DeltaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.log = self.root/'child log'
        self.log.write_bytes(b'a'*4095)

    def tearDown(self):
        self.temp.cleanup()

    def snap(self, binding=BIND):
        st = self.log.stat()
        return snapshot(str(self.log), f'{st.st_dev}:{st.st_ino}:{st.st_size}', binding)

    def execute(self, recipe):
        # macOS stat syntax differs; replace metadata command only, not dd/guards.
        script = recipe['script']
        script = script.replace('stat -L -c %d:%i', 'stat -L -f %d:%i')
        script = script.replace('stat -L -c %s', 'stat -L -f %z')
        return capture(['/bin/sh', '-c', script], self.root/'out', recipe, 2)

    def test_exact_offset_and_growth_after_snapshot(self):
        before = self.snap()
        delta = bytes(range(256))*33
        with self.log.open('ab') as f: f.write(delta)
        recipe = read_recipe(before, self.snap(), 'true', MARK)
        with self.log.open('ab') as f: f.write(b'AFTER_SNAPSHOT'*100)
        got = self.execute(recipe)
        self.assertEqual(got['status'], 'BOUNDED_BYTES_COMPLETE')
        self.assertEqual((self.root/'out/selected.raw').read_bytes(), delta)

    def test_cap_is_exact_and_reports_unread_tail(self):
        before = self.snap()
        with self.log.open('ab') as f: f.write(b'x'*(MAX_DELTA+100))
        recipe = read_recipe(before, self.snap(), 'true', MARK)
        got = self.execute(recipe)
        self.assertTrue(recipe['truncated_by_cap'])
        self.assertEqual(got['selected_bytes'], MAX_DELTA)

    def test_truncation_and_identity_drift_refuse(self):
        before = self.snap()
        self.log.write_bytes(b'no')
        with self.assertRaises(ValueError): read_recipe(before, self.snap(), 'true', MARK)
        self.log.write_bytes(b'x'*5000)
        with self.assertRaises(ValueError): read_recipe(before, self.snap('c'*64), 'true', MARK)

    def test_failed_guard_preserves_failure_not_success(self):
        recipe = read_recipe(self.snap(), self.snap(), 'false', MARK)
        got = self.execute(recipe)
        self.assertEqual(got['status'], 'PARTIAL_UNVERIFIED')
        self.assertFalse(got['postguard_marker'])

    def test_replaced_file_refuses_before_dd(self):
        before = self.snap()
        self.log.rename(self.root/'old')
        self.log.write_bytes(b'x'*5000)
        with self.assertRaises(ValueError):
            read_recipe(before, self.snap(), 'true', MARK)

    def test_empty_delta_has_identity_checks(self):
        recipe = read_recipe(self.snap(), self.snap(), 'true', MARK)
        got = self.execute(recipe)
        self.assertEqual(got['status'], 'BOUNDED_BYTES_COMPLETE')
        self.assertEqual(got['selected_bytes'], 0)

    def test_timeout_retains_real_partial_stdout(self):
        before = self.snap()
        self.log.write_bytes(b'x'*5000)
        recipe = read_recipe(before, self.snap(), 'true', MARK)
        got = capture([sys.executable, '-c',
                       'import os,time;os.write(1,b"partial");time.sleep(2)'],
                      self.root/'out', recipe, .1)
        self.assertTrue(got['host_timeout'])
        self.assertEqual((self.root/'out/stdout.raw').read_bytes(), b'partial')
        self.assertEqual(got['status'], 'PARTIAL_UNVERIFIED')


if __name__ == '__main__': unittest.main()
