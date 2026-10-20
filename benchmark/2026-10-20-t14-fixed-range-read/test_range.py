import json, subprocess, sys, tempfile, unittest
from pathlib import Path
import read_range as r

class RangeTests(unittest.TestCase):
    def run_frame(self, data, start=4099, end=13111, guard='true'):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); source=root/'log';source.write_bytes(data)
            p=r.plan(start,end);token='a'*32
            cmd=r.script(str(source),p,token,str(root/'diagnostic'),guard)
            got=subprocess.run(['sh','-c',cmd],capture_output=True)
            return got,p,token
    def test_real_binary_fixed_end(self):
        data=bytes(range(256))*100
        got,p,t=self.run_frame(data)
        self.assertEqual(r.decode(got.stdout,p,t,got.returncode,False),data[4099:13111])
        self.assertEqual(p['trim'],3)
    def test_short_read_rc_zero_refused(self):
        got,p,t=self.run_frame(b'a'*5000)
        self.assertEqual(got.returncode,0)
        with self.assertRaises(ValueError):r.decode(got.stdout,p,t,0,False)
    def test_dd_error_refused(self):
        with tempfile.TemporaryDirectory() as td:
            p=r.plan(1,5000);t='b'*32
            got=subprocess.run(['sh','-c',r.script(td+'/missing',p,t,td+'/diag','true')],capture_output=True)
            self.assertIn(b'T15_END_',got.stdout)
            with self.assertRaises(ValueError):r.decode(got.stdout,p,t,got.returncode,False)
    def test_missing_marker_or_guard_refused(self):
        got,p,t=self.run_frame(bytes(range(256))*100)
        with self.assertRaises(ValueError):r.decode(got.stdout[:-1],p,t,0,False)
        got,p,t=self.run_frame(bytes(range(256))*100,guard='false')
        self.assertNotEqual(got.returncode,0);self.assertEqual(got.stdout,b'')
    def test_timeout_keeps_raw(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)
            got=r.capture([sys.executable,'-c','import os,time;os.write(1,b"abc\\x00");os.write(2,b"err");time.sleep(2)'],out,.1)
            self.assertTrue(got['timed_out']);self.assertEqual((out/'stdout.raw').read_bytes(),b'abc\0')
            self.assertEqual((out/'stderr.raw').read_bytes(),b'err')
    def test_preview_and_boundaries(self):
        got=subprocess.run([sys.executable,str(Path(r.__file__))],capture_output=True,check=True)
        self.assertEqual(json.loads(got.stdout)['device_calls'],0)
        for start,end in ((3,3),(-1,4),(1,67108866)):
            with self.assertRaises(ValueError):r.plan(start,end)
    def test_postguard_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);src=root/'source';src.write_bytes(bytes(range(256))*100)
            p=r.plan(4099,13111);t='c'*32
            guard=f'test ! -e {td}/once; touch {td}/once'
            got=subprocess.run(['sh','-c',r.script(str(src),p,t,str(root/'diag'),guard)],capture_output=True)
            self.assertNotEqual(got.returncode,0)
            with self.assertRaises(ValueError):r.decode(got.stdout,p,t,got.returncode,False)

if __name__=='__main__':unittest.main()
