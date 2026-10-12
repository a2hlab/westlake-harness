import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('directory_prepare', HERE / 'prepare.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class SourceMetadataTests(unittest.TestCase):
    def setUp(self):
        source = HERE / 'inputs/source/001-source-directories.stdout'
        self.actual = source.read_text()

    def test_actual_source_exact_metadata(self):
        metadata, boot = p.source_metadata(self.actual)
        self.assertEqual(metadata, {'mode': '755', 'uid': 20011206, 'gid': 20011206, 'label': 'u:object_r:appdat:s0'})
        self.assertEqual(boot, '9f5af7c8-d359-4c25-99c6-63206b50cf0a')

    def test_source_drift_is_rejected(self):
        row = next(line for line in self.actual.splitlines() if line.endswith(' ' + p.TARGET))
        for replacement in (row.replace('drwxr-xr-x', 'lrwxr-xr-x'),
                            row.replace('20011206', '20011300'),
                            row.replace('appdat', 'data_file'),
                            row.replace('drwxr-xr-x', 'drwx------')):
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                p.source_metadata(self.actual.replace(row, replacement))
        with self.assertRaises(ValueError):
            p.source_metadata(self.actual + row + '\n')
        with self.assertRaises(ValueError):
            p.source_metadata(self.actual.replace('755 20011206 20011206 directory', '755 20011206 20011206 regular file'))
        with self.assertRaises(ValueError):
            p.source_metadata(self.actual.replace('9f5af7c8-d359-4c25-99c6-63206b50cf0a', '6e0e331f-dc28-4851-b082-709a3a1d515b', 1))


if __name__ == '__main__':
    unittest.main()
