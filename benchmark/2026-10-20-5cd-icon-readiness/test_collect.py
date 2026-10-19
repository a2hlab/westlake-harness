import copy,json,subprocess,sys,unittest
from pathlib import Path
from core import *
HERE=Path(__file__).resolve().parent
class Admission(unittest.TestCase):
    def test_exact_and_wrong_profile(self):
        p=json.loads((HERE/'profile.json').read_text());profile_check(p,SERIAL,BOOT)
        for key,value in [('uid',20011206),('serial','61b0657200000000000000000324012c'),('boot','other')]:
            q=copy.deepcopy(p);q[key]=value
            with self.subTest(key=key),self.assertRaises(Refuse):profile_check(q,SERIAL,BOOT)
        q=copy.deepcopy(p);q['files'][q['run_path']]='0'*64
        with self.assertRaises(Refuse):profile_check(q,SERIAL,BOOT)
        for key,sha in [('cfg_path',CFG),('run_path',RUN)]:
            q=copy.deepcopy(p);q[key]='/alternate';q['files']['/alternate']=sha
            with self.subTest(path=key),self.assertRaises(Refuse):profile_check(q,SERIAL,BOOT)
    def test_got_execute_refused_before_transport(self):
        r=subprocess.run([sys.executable,str(HERE/'collect.py'),'--execute','--player-elf','/nonexistent'],capture_output=True,text=True)
        self.assertNotEqual(r.returncode,0);self.assertIn('GOT disabled',r.stderr)
    def test_preview_no_device(self):
        r=subprocess.run([sys.executable,str(HERE/'collect.py')],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr);v=json.loads(r.stdout);self.assertFalse(v['execution']);self.assertEqual(v['device_calls'],0)
class Identity(unittest.TestCase):
    def test_full_name_uid_and_ambiguity(self):
        row='7000 6000 20011300 com.ss.android.article.news\n'
        self.assertEqual(select(row),{'pid':7000,'ppid':6000});self.assertIsNone(select('3966 1 0 sh\n'))
        for s in [row+row,row.replace('20011300','20011206'),row.strip()+' extra',row.replace('7000 ','bad '),row.replace('20011300 ','')]:
            with self.assertRaises(Refuse):select(s)
        self.assertIsNone(select(row.replace('com.ss.android.article.news','id.article.news')))
    def test_birth_and_memory_range(self):
        fields=['S','6000']+['0']*17+['123']
        s=stat('7000 (id.article.news) '+' '.join(fields),7000);same_stat(s,dict(s))
        with self.assertRaises(Refuse):same_stat(s,{**s,'birth':124})
        rows=maps('1000-2000 r--p 00000000 103:30 1 /known.so')
        readable_slot(rows,0x1ff8)
        for address in [0,0x1ffc,0x2000]:
            with self.assertRaises(Refuse):readable_slot(rows,address)
class Receipt(unittest.TestCase):
    def test_unknown_does_not_claim_feed(self):
        r={'serial':SERIAL,'boot':BOOT,'uid':UID,'playback':'unknown','audio':'unknown','visual_verdict':'pending_review','device_mutations':0,'app_starts':0,'attach':0}
        receipt_check(r)
        for key,value in [('playback','pass'),('visual_verdict','pass'),('attach',1),('app_starts',1)]:
            with self.subTest(key=key),self.assertRaises(Refuse):receipt_check({**r,key:value})
if __name__=='__main__':unittest.main()
