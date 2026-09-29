import csv,gzip,json,unittest
from pathlib import Path
from observations import missing_id,registration_id
from publish import classify
from gate import evaluate
from graph import build_masks
from westlake import scalar_tables
HERE=Path(__file__).resolve().parent

class GapTests(unittest.TestCase):
    def test_rules(self):
        self.assertEqual(classify('unknown',[{'attempt':True}],[])[0],'registration_attempt_only')
        self.assertEqual(classify('registered',[{}],[{}]),('unbound_observed','binding_gap'))
        self.assertEqual(missing_id('No implementation found for long android.os.Process.getElapsedCpuTime() (tried x)'), 'android/os/Process.getElapsedCpuTime()J')
        a=registration_id('OH_RegHook: a.B::f(I)J -> fn=123 (lib=/x.so pageOff=0x1)')[0]
        z=registration_id('OH_RegHook: a.B::f()J -> fn=123 (lib=/x.so pageOff=0x1)')[0]
        self.assertNotEqual(a,z)
        strict={'inventory_sha256':'abc','declaration_count':1,'covered_count':0,'methods':[{'id':'a','status':'unknown'}]}
        e={'id':'a','status':'unknown','inventory_sha256':'abc','approval':'draft','approved_by':'outer','reason':'reviewed condition','evidence':['file:1']}
        self.assertFalse(evaluate(strict,{'exceptions':[e]})['pass'])
        e['approval']='approved';self.assertTrue(evaluate(strict,{'exceptions':[e]})['pass'])
        e['inventory_sha256']='other';self.assertFalse(evaluate(strict,{'exceptions':[e]})['pass'])
        masks,_=build_masks({'A.f()V':{'edges':[{'target':'A.n()V'}]}},{},['A.n()V'],1)
        self.assertEqual(masks['A.f()V'],1)
        self.assertNotIn('B.unrelated()V',masks)
        self.assertIn('method[]',scalar_tables('JNINativeMethod method = {"x","()V", fn}; RegisterNatives(c,&method,1);'))

    def test_inventory(self):
        rows=list(csv.DictReader((HERE/'jni-all.csv').open()))
        inv=json.load(gzip.open(HERE/'evidence/native-inventory.json.gz','rt'))
        ids={r['id'] for r in rows}
        self.assertEqual(ids,{m['id'] for m in inv['methods']})
        self.assertEqual(len(rows),5406);self.assertEqual(len(rows),len(ids))
        coverage=json.loads((HERE/'app-coverage.json').read_text());self.assertEqual(len(coverage),66)
        self.assertEqual(sum(a['status']=='scanned' for a in coverage),65)
        self.assertEqual([a['key'] for a in coverage if a['status']=='unknown'],['subwaysurfers'])
        gaps=list(csv.DictReader((HERE/'jni-gap.csv').open()))
        self.assertTrue(all(r['reachability']!='unreachable' for r in gaps))
        cpu=next(r for r in rows if r['id']=='android/os/Process.getElapsedCpuTime()J')
        self.assertEqual(cpu['status'],'unbound_observed');self.assertIn('oh_process_cpu_time.cpp',cpu['westlake_sources'])
        fileobs=next(r for r in rows if r['id']=='android/os/FileObserver$ObserverThread.init()I')
        self.assertIn('class_library_services.cpp',fileobs['westlake_sources'])
        self.assertEqual(next(r for r in rows if r['id']=='java/lang/Class.getNameNative()Ljava/lang/String;')['status'],'implementation_present')
        self.assertFalse(evaluate(json.loads((HERE/'jni-strict.json').read_text()),json.loads((HERE/'jni-exceptions.json').read_text()))['pass'])

if __name__=='__main__':unittest.main()
