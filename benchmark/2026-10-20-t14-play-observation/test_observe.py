import json,subprocess,sys,tempfile,unittest
from pathlib import Path
from framing import script,decode
from observe import ui_command,profile,power,SERIAL,RUN

TOKEN='b'*32


class ObservationTests(unittest.TestCase):
    def test_merged_frame_real_dd(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'log').write_bytes(b'old'+b'\x00\xffactual error\n')
            command=script(str(p/'log'),3,15,TOKEN,str(p/'dd.err'),'true')
            q=subprocess.run(['/bin/sh','-c',command+' 2>&1'],capture_output=True)
            result=decode(q.stdout,15,TOKEN,q.returncode)
            self.assertEqual(result['status'],'BOUNDED_BYTES_COMPLETE')
            self.assertEqual(result['payload'],b'\x00\xffactual error\n')
            self.assertTrue((p/'dd.err').read_bytes())

    def test_dd_error_short_read_missing_marker_fail(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'short').write_bytes(b'x')
            for source in [p/'missing',p/'short']:
                command=script(str(source),0,10,TOKEN,str(p/'dd.err'),'true')
                q=subprocess.run(['/bin/sh','-c',command+' 2>&1'],capture_output=True)
                self.assertEqual(decode(q.stdout,10,TOKEN,q.returncode)['status'],'PARTIAL_UNVERIFIED')
            self.assertEqual(decode(b'',0,TOKEN,0)['status'],'PARTIAL_UNVERIFIED')

    def test_timeout_prefix_never_complete(self):
        try:subprocess.run([sys.executable,'-c','import os,time;os.write(1,b"partial");time.sleep(2)'],capture_output=True,timeout=.1)
        except subprocess.TimeoutExpired as e:
            self.assertEqual(e.stdout,b'partial')
            self.assertEqual(decode(e.stdout,7,TOKEN,None,True)['status'],'PARTIAL_UNVERIFIED')

    def test_identity_and_coordinates_reject(self):
        p={'width':1200,'height':1920}
        self.assertEqual(ui_command('play',[1,2],p,'c'*64,'c'*64,[]),'uitest uiInput click 1 2')
        for coords,reviewed,used in [([1,2],'d'*64,[]),([1,2],'c'*64,['play']),([1200,2],'c'*64,[])]:
            with self.assertRaises(ValueError):ui_command('play',coords,p,reviewed,'c'*64,used)
        with self.assertRaises(ValueError):profile({'serial':'61b','boot':'x'})

    def test_power_strict(self):
        self.assertEqual(power('ScreenOffTime: Timeout=10000ms OverrideTimeout=10000ms'),(10000,10000))
        with self.assertRaises(ValueError):power('unknown')

    def test_preview_zero_device(self):
        from observe import sha
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);receipt=p/'receipt';receipt.write_text('readonly fixture')
            proc={'pid':2,'ppid':1,'birth':3,'uid':20011300,'exe_sha256':'a'*64,'mnt':'mnt:[2]'}
            obj={'serial':SERIAL,'boot':'a'*8+'-'+'b'*4+'-'+'c'*4+'-'+'d'*4+'-'+'e'*12,'run_path':RUN,'run_sha256':'f'*64,'readonly_receipt_sha256':sha(receipt),'parent':dict(proc,pid=10,uid=0),'child':dict(proc,pid=11,ppid=10),'host':dict(proc,pid=12),'init_mnt':'mnt:[1]','width':1200,'height':1920}
            pf=p/'profile';pf.write_text(json.dumps(obj));root=p/'no-output'
            q=subprocess.run([sys.executable,str(Path(__file__).with_name('observe.py')),'begin','--repo',d,'--profile',str(pf),'--receipt',str(receipt),'--root',str(root)],capture_output=True)
            self.assertEqual(q.returncode,0,q.stderr);self.assertEqual(json.loads(q.stdout)['device_calls'],0);self.assertFalse(root.exists())


if __name__=='__main__':unittest.main()
