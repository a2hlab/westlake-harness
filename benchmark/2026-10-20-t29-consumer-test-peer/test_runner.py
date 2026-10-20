import importlib.util,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('peer_replay',P/'replay.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
repo=P.parents[1]
ROOT=Path(os.environ.get('T29_SOURCE_ROOT',str(repo)))
if not (ROOT/mod.REL).exists():ROOT=repo.parent/'westlake-harness'
class RealFixture(unittest.TestCase):
    def test_baseline_and_actual_same_source_control(self):
        base=Path.home()/'.local/share/westlake/t29-consumer-test-peer/tests';base.mkdir(parents=True,exist_ok=True)
        out=Path(tempfile.mkdtemp(dir=base))/'replay'
        r=subprocess.run([sys.executable,str(P/'replay.py'),'--source-root',str(ROOT),
                          '--consumer-source-dir',str(ROOT/mod.REL),'--out',str(out)],capture_output=True,timeout=60)
        self.assertEqual(r.returncode,0,r.stderr.decode())
        result=json.loads((out/'results.json').read_text());self.assertEqual(result['cases'],40)
        self.assertEqual(result['status'],'DERIVED_BEHAVIOR_MATCH')
        self.assertEqual(result['baseline']['sources'],result['candidate']['sources'])
        rows=json.loads((out/'baseline/observations.json').read_text())
        # Existing semantic assertions reject changed call/exception behavior.
        rows[0]['events'].append('attach:42:errno-in=37')
        with self.assertRaises(AssertionError):mod.assert_baseline(rows)
    def test_missing_consumer_rejected(self):
        base=Path.home()/'.local/share/westlake/t29-consumer-test-peer/tests';base.mkdir(parents=True,exist_ok=True)
        tmp=tempfile.mkdtemp(prefix='missing-',dir=base)
        out=Path(tmp)/'run'
        r=subprocess.run([sys.executable,str(P/'replay.py'),'--source-root',str(ROOT),
                          '--consumer-source-dir',str(Path(tmp)/'absent'),'--out',str(out)],capture_output=True,timeout=60)
        (Path(tmp)/'caller.stdout').write_bytes(r.stdout)
        (Path(tmp)/'caller.stderr').write_bytes(r.stderr)
        (Path(tmp)/'caller.rc').write_text(str(r.returncode)+'\n')
        self.assertNotEqual(r.returncode,0)
        self.assertTrue((out/'baseline/run.rc').exists())
        self.assertFalse((out/'results.json').exists())
if __name__=='__main__':unittest.main()
