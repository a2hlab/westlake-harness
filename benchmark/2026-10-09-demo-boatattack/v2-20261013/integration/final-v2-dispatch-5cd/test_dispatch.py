"""Offline argv tests only: python3 is an exit shim, never a board reader."""
import hashlib,json,os,subprocess,tempfile,unittest
from pathlib import Path
import render_wrapper as r
HERE=Path(__file__).resolve().parent
REPO=next(p for p in HERE.parents if (p/'scripts/lab/lab_paths.py').is_file())
class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.wrapper=self.root/'scripts/lab/demo_restore.sh';self.wrapper.parent.mkdir(parents=True)
        self.wrapper.write_bytes((HERE/'demo_restore.sh.candidate').read_bytes());self.bin=self.root/'bin';self.bin.mkdir();shim=self.bin/'python3';shim.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$ARGV_LOG"\n');shim.chmod(0o755)
        self.log=self.root/'argv';self.env=dict(os.environ,PATH=str(self.bin)+':'+os.environ['PATH'],ARGV_LOG=str(self.log))
    def tearDown(self):self.tmp.cleanup()
    def test_syntax_render_and_predecessor_unchanged(self):
        subprocess.run(['bash','-n',str(self.wrapper)],check=True)
        original=(HERE/'predecessor.sh.txt').read_bytes()
        self.assertIn((REPO/'scripts/lab/demo_restore.sh').read_bytes(),[original,self.wrapper.read_bytes()])
        self.assertEqual(hashlib.sha256(original).hexdigest(),r.BASE_SHA)
        self.assertEqual(self.wrapper.read_bytes(),r.render(HERE/'predecessor.sh.txt'))
        self.assertEqual(self.wrapper.read_bytes().replace((HERE/'dispatch-block.sh.txt').read_bytes(),b'',1),original)
        for name,expected in [('final-v2-candidate-r2','7b32b7a6d4fdaaee777365272850bedf7ca55ab3ecf3effda6f27876634e137d'),('final-v2-entry','2ceb237b2d4b849671f8c205b05293f02420a37b2eb9bb677dbbbcf411ce6c8f'),('final-v2-rehearsal-5cd','ee198467407a36006f9a26f824ddd2a5237551e079de5545db4bd98a63322543')]:
            path=HERE.parent/name/'freeze.json';self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),expected)
    def test_dispatch_8_cases_exact_argv(self):
        cases=[([],[],'t5/restore.py'),(['--seal','s'],['--seal','s'],'t5/restore.py'),(['--realization','r'],['--realization','r'],'r2-timeout/exact_realization.py'),(['--directory-recipe=d'],['--directory-recipe=d'],'r4b-directory-logdir/restore_recipe.py'),(['--v2-recipe','61b recipe'],['--v2-recipe','61b recipe'],'final-v2-entry/restore_entry.py'),(['--v2-recipe=61b recipe'],['--v2-recipe=61b recipe'],'final-v2-entry/restore_entry.py'),(['--v2-5cd-recipe','5cd recipe','--recipe-sha256','a'*64,'--out','new output'],['--v2-recipe','5cd recipe','--recipe-sha256','a'*64,'--out','new output'],'final-v2-rehearsal-5cd/entry/restore_entry.py'),(['--out','new output','--v2-5cd-recipe=5cd recipe','--execute'],['--out','new output','--v2-recipe=5cd recipe','--execute'],'final-v2-rehearsal-5cd/entry/restore_entry.py')]
        for argv,wanted,suffix in cases:
            with self.subTest(argv=argv):
                result=subprocess.run(['bash',str(self.wrapper),*argv],env=self.env,capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr)
                got=self.log.read_text().splitlines();self.assertTrue(got[0].endswith(suffix));self.assertEqual(got[1:],wanted)
    def test_conflicting_selectors_rejected_without_dispatch(self):
        for selector in ['--v2-recipe=x','--directory-recipe=x','--realization=x','--seal=x','--v2-5cd-recipe=x']:
            with self.subTest(selector=selector):
                result=subprocess.run(['bash',str(self.wrapper),'--v2-5cd-recipe=x',selector],env=self.env,capture_output=True,text=True)
                self.assertEqual(result.returncode,2);self.assertFalse(self.log.exists())
if __name__=='__main__':unittest.main(verbosity=2)
