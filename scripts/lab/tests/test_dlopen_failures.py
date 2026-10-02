#!/usr/bin/env python3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dlopen_failures as df  # noqa: E402


class NsBase(unittest.TestCase):
    def test_strips_pid_suffix(self):
        self.assertEqual(df.ns_base('westlake.anl.app.29496.2'), 'westlake.anl.app')

    def test_keeps_base(self):
        self.assertEqual(df.ns_base('westlake.anl.app'), 'westlake.anl.app')

    def test_strips_only_trailing_pair(self):
        self.assertEqual(df.ns_base('a.b.123.4'), 'a.b')


class Scan(unittest.TestCase):
    def test_aggregates_per_lib(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            k1 = root / 'run' / 'ser' / 'key-one'
            k2 = root / 'run' / 'ser' / 'key-two'
            k1.mkdir(parents=True)
            k2.mkdir(parents=True)
            (k1 / 'hilog.txt').write_text(
                '10-02 01:00:00.000 100 100 W C03f07/MUSL-LDSO: load libicui18n.so failed, namespace=westlake.anl.app.29496.2, errno=2\n'
                '10-02 01:00:01.000 100 100 W C03f07/MUSL-LDSO: load libicui18n.so failed, namespace=westlake.anl.app.29496.2, errno=2\n')
            (k2 / 'hilog.txt').write_text(
                '10-02 01:00:00.000 100 100 W C03f07/MUSL-LDSO: load libfoo.so failed, namespace=westlake.sealed.child.12345.1, errno=2\n'
                '10-02 01:00:01.000 100 100 W C03f07/MUSL-LDSO: load libicui18n.so failed, namespace=westlake.anl.app.11111.3, errno=2\n')
            rows = df.scan([root])
            by_lib = {r['lib']: r for r in rows}
            self.assertEqual(by_lib['libicui18n.so']['key_count'], 2)
            self.assertEqual(by_lib['libfoo.so']['key_count'], 1)
            self.assertEqual(by_lib['libicui18n.so']['ns'], ['westlake.anl.app'])
            self.assertEqual(by_lib['libfoo.so']['ns'], ['westlake.sealed.child'])
            self.assertEqual(by_lib['libicui18n.so']['errno'], ['2'])
            # sorted by key count desc: libicui18n.so first
            self.assertEqual(rows[0]['lib'], 'libicui18n.so')


if __name__ == '__main__':
    unittest.main()
