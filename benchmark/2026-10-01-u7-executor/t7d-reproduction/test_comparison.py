import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('comparison',Path(__file__).with_name('compare_reproductions.py'))
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

class Verdicts(unittest.TestCase):
    def run_case(self,values,extra=False):
        with tempfile.TemporaryDirectory() as td:
            paths={}
            for name,value in zip(['T7d','R1','R2','R3'],values):
                root=Path(td)/name;root.mkdir();paths[name]=root
                b=bytearray(0x3e3d0);b[:8]=b'art\n108\0';struct.pack_into('<II',b,16,0x70000000,len(b))
                struct.pack_into('<II',b,88,0x100,0x100);struct.pack_into('<QQ',b,0x3e3b8,value,2)
                if name=='R3' and extra:b[400]^=1
                (root/'boot.art').write_bytes(b);(root/'other.oat').write_bytes(b'unchanged')
            ref={'outputs':{p.name:c.sha(p) for p in paths['T7d'].iterdir()}}
            return c.compare(paths,ref)
    def test_only_field_varies(self):
        r=self.run_case([1,2,3,4]);self.assertEqual(r['provenance'],'verified-with-exception');self.assertEqual(len(r['pairs']),6)
        self.assertFalse(r['deployable']);self.assertEqual(r['exception_approval'],'pending')
    def test_reproductions_agree_but_not_reference(self):
        self.assertEqual(self.run_case([1,2,2,2])['provenance'],'unknown')
    def test_other_byte_difference_stops(self):
        self.assertEqual(self.run_case([1,2,3,4],True)['provenance'],'unknown')

if __name__=='__main__':unittest.main()
