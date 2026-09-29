#!/usr/bin/env python3
import collections,csv,gzip,hashlib,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from scan_jni import HERE,REPO,R8HASH,REGISTRATION_SOURCE,classify,sha
from registration_sources import parse_source,symbol_matches
from scan_risks_v3 import derive,inspect_method
OUT=HERE/'v3'
from scan_io import load as read
def gate_module():
    spec=importlib.util.spec_from_file_location('gate',REPO/'scripts/lab/jni_gate.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class V3Tests(unittest.TestCase):
    def test_registration(self):
        text='''
        static const char *clsA = "android/demo/A";
        static JNINativeMethod a[] = {
          {"same", "()I", reinterpret_cast<void*>(Owner::first)},
          {"same", "(I)I", (void*)Owner::second},
        };
        static JNINativeMethod b[] = {{"same", "()I", (void*)Other::first}};
        int reg(JNIEnv* env) {
          RegisterMethodsOrDie(env, clsA, a, NELEM(a));
          RegisterMethodsOrDie(env, "android/demo/SharedA", a, NELEM(a));
          jclass c = findClassOrDie(env, "android/demo/B");
          return env->RegisterNatives(c, b, NELEM(b));
        }'''
        rows,unknown=parse_source(Path('/fixture/Owner.cpp'),text)
        self.assertFalse(unknown);self.assertEqual(len(rows),5)
        src=next(r for r in rows if r['class']=='android/demo/A' and r['signature']=='()I')
        self.assertTrue(symbol_matches(src,['_ZN7android5OwnerL5firstEP7_JNIEnv']))
        self.assertFalse(symbol_matches(src,['_ZN7android5OwnerL6secondEP7_JNIEnv']))
        table={'method':'same','signature':'()I','function_symbols':['_ZN7android5OwnerL5firstEP7_JNIEnv'],'table_address':'0x10','function_address':'0x20'}
        lib={'exports':{},'stub_bodies':{},'compiled_sources':{'Owner.cpp'},'tables_by_sig':{('same','()I'):[table]},'path':'fixture.so'}
        sources={(r['class'],r['method'],r['signature']):[r] for r in rows}
        d={'class':'android/demo/A','method':'same','signature':'()I'}
        self.assertEqual(classify(d,[lib],sources)[0],'registered')
        self.assertEqual(classify({**d,'class':'android/demo/B'},[lib],sources)[0],'unknown')
        self.assertEqual(classify(d,[{**lib,'compiled_sources':set()}],sources)[0],'unknown')
        self.assertEqual(classify(d,[{**lib,'tables_by_sig':{}}],sources)[0],'unknown')
        ambiguous='static const char *c="android/demo/A"; static const char *c="android/demo/B"; static JNINativeMethod g[]={{"f","()V",(void*)f}}; void r(){RegisterMethodsOrDie(env,c,g,1);}'
        self.assertFalse(parse_source(Path('ambiguous.cpp'),ambiguous)[0])
        for gen,result in read(OUT/'jni-results.json').items():
            for name,expected in [('nativeParseManifestJson','missing' if gen=='6cb40cd6' else 'exported'),('nativeGetSysProp','missing' if gen=='6cb40cd6' else 'exported')]:
                rows=[m for m in result['methods'] if m['class']=='adapter/activity/AppSchedulerBridge' and m['method']==name]
                self.assertEqual(len(rows),1);self.assertEqual(rows[0]['status'],expected)
            sqlite=next(m for m in result['methods'] if m['class']=='android/database/sqlite/SQLiteConnection' and m['method']=='nativeOpen')
            self.assertEqual(sqlite['status'],'stub' if gen=='6cb40cd6' else 'registered')
            promoted=[m for m in result['methods'] if m['status']=='registered' and any(any(s.get('attribution')=='explicit-class-table-registration-v3' for s in e.get('source',[])) for e in m['evidence'])]
            self.assertGreater(len(promoted),1000)

    def test_cache(self):
        gate=gate_module()
        allow=read(HERE/'jni-allowlist.json')
        frozen=read(OUT/'evidence/v2-jni-allowlist.json.gz')
        self.assertEqual(allow,frozen)
        result=read(OUT/'jni-results.json')['v3-74d1d6d4']
        verdict=gate.evaluate(result,allow)
        self.assertGreater(verdict['blocked_count'],0) # unknowns never vanish by fiat
        with tempfile.TemporaryDirectory(prefix='b10-cache-v3-') as tmp:
            t=Path(tmp);manifest=t/'package.json';manifest.write_text('{"generation":"fixture"}')
            dep=t/'dependency.py';dep.write_text('v1')
            r={'generation':'fixture','package':str(t),'package_manifest_sha256':sha(manifest),
               'scanner_sha256':sha(HERE/'scan_jni.py'),'scanner_dependencies':[{'path':str(dep),'sha256':sha(dep)}],
               'inputs':[],'source_inputs':[],'methods':[]}
            matrix=t/'matrix.json';matrix.write_text(json.dumps({'fixture':r}))
            self.assertEqual(gate.cached(matrix,t)['generation'],'fixture')
            dep.write_text('v2')
            with self.assertRaisesRegex(ValueError,'stale matrix input'):gate.cached(matrix,t)
        # Current live cache must validate all source and scanner hashes.
        self.assertEqual(gate.cached(OUT/'jni-results.json',Path(result['package']))['generation'],result['generation'])
        d={'generation':'fixture','overlay':{'sha256':'r8'},'methods':[{'id':'C.f()V','status':'unknown','reason':'ambiguous'}]}
        self.assertFalse(gate.evaluate(d,{'exceptions':[]})['pass'])

    def test_risks(self):
        calls=inspect_method('App.init()V','classes.dex',[
            ('0',1,'const-string v0, "foo" // string@1'),
            ('2',2,'invoke-static {v0}, Ljava/lang/System;.loadLibrary:(Ljava/lang/String;)V // method@1')])
        self.assertEqual(calls[0]['constant_argument'],'foo')
        branched=inspect_method('App.init()V','classes.dex',[
            ('0',1,'const-string v0, "foo" // string@1'),('1',2,'if-eqz v1, 0008 // +0007'),
            ('2',3,'invoke-static {v0}, Ljava/lang/System;.loadLibrary:(Ljava/lang/String;)V // method@1')])
        self.assertIsNone(branched[0]['constant_argument'])
        app={'key':'fixture-not-a-real-app','sha256':'fixture','manifest':{'flutter':True},'features':{'koin':{},'workmanager':{}}}
        graph={'manifest':{'application':'Fixture','providers':[],'initializers':[]},'features':{},
               'extra_calls':[{**calls[0],'startup_reachable':'yes-static'}]}
        service={'app':app['key'],'service':'notification','status':'missing',
            'startup_evidence':[{'root':{'category':'application'},'path':[]}]}
        rows=derive(app,graph,[{'entry':'lib/arm64-v8a/libx.so','needed':['libabsent.so']}],[service],set())
        self.assertEqual({r['wall'] for r in rows},{'dlopen-namespace','flutter-native-path','koin-initialization','workmanager-initialization','attach-service-contract'})
        self.assertTrue(all(r['runtime_condition'] and r['status']=='risk-candidate' for r in rows))
        self.assertTrue(next(r for r in rows if r['wall']=='attach-service-contract')['stub_ok'])
        self.assertTrue(next(r for r in rows if r['wall']=='flutter-native-path')['needs_real'])
        # Enforce architectural separation: predictions cannot read observation receipts.
        source=(HERE/'scan_risks_v3.py').read_text()
        self.assertNotIn('p73-fatal',source);self.assertNotIn('prospective-rerun',source)
        live=read(OUT/'risk-results.json')
        self.assertEqual(len({r['app'] for r in live['rows']}),20)

    def test_backtest(self):
        b=read(OUT/'backtest.json')
        self.assertEqual(len(b['p75']['rows']),12)
        self.assertEqual(b['p75']['observed_counts']['activity-theme'],2)
        self.assertEqual(b['p75']['observed_counts']['flutter-native-path'],4)
        self.assertTrue(all(r['observed_wall']!='manifest-jni' for r in b['p75']['rows']))
        for cohort in ['p75','p78']:
            for metric in b[cohort]['metrics'].values():
                if isinstance(metric,dict) and 'total' in metric:
                    self.assertLessEqual(metric['hits'],metric['total'])
        p78=b['p78']
        self.assertEqual(p78['frozen_source_sha256'],'2d8c9a5408f1419afe3609e75ef2daa1dce15032432f7a241d835d10e05d5ce1')
        self.assertEqual(sum(r['eligible'] for r in p78['rows']),1)
        self.assertFalse(next(r for r in p78['rows'] if r['app']=='fd-noice')['eligible'])
        self.assertEqual(p78['metrics']['strict_fatal_first']['total'],1)
        self.assertEqual(p78['metrics']['strict_fatal_first']['hits'],0)
        self.assertEqual(p78['metrics']['evidenced_prerequisite']['hits'],1)

if __name__=='__main__':unittest.main()
