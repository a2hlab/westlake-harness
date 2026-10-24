import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

D = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('wmc_stage', D/'stage.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class SafetyTests(unittest.TestCase):
    def archive(self, entries):
        b = io.BytesIO()
        with tarfile.open(fileobj=b, mode='w') as t:
            for name, kind, target in entries:
                info = tarfile.TarInfo(name)
                info.type, info.linkname = kind, target
                t.addfile(info)
        b.seek(0)
        with tarfile.open(fileobj=b) as t:
            return m.checked_members(t)

    def test_traversal_and_absolute_paths(self):
        for name in ('../escape','safe/../../escape','/absolute','safe/../escape','safe\\escape'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.archive([(name,tarfile.REGTYPE,'')])

    def test_links_and_devices_rejected(self):
        for kind in (tarfile.SYMTYPE,tarfile.LNKTYPE,tarfile.CHRTYPE,tarfile.FIFOTYPE):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.archive([('safe',kind,'../../escape')])

    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            self.archive([('same',tarfile.REGTYPE,''),('same',tarfile.REGTYPE,'')])

    def test_regular_path_allowed(self):
        self.assertEqual(list(self.archive([('ORB_WS/a/b',tarfile.REGTYPE,'')])), ['ORB_WS/a/b'])

    def test_collision_hash_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);src=d/'src';dst=d/'dst';src.write_bytes(b'a');dst.write_bytes(b'b')
            row={'sha256':m.sha(src),'bytes':1}
            with self.assertRaises(ValueError):m.put(src,dst,row)
            self.assertEqual(dst.read_bytes(),b'b')

if __name__ == '__main__':unittest.main()
