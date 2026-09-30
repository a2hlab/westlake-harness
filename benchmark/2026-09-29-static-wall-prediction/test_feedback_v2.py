#!/usr/bin/env python3
import gzip,hashlib,json,sys,unittest
from pathlib import Path
from rules_feedback_v2 import inspect,activity_rows,provider_api,boot_visibility,PROVIDER
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'benchmark/2026-09-30-v2-scanner-feedback';V2=ROOT/'benchmark/2026-09-30-v3c-r17j-prospective'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

class RuleTests(unittest.TestCase):
    def test_typed_result_launcher_and_owner_negative(self):
        method='app/Main.onStart()V'
        ins=[('0000',1,'new-instance v0, Landroid/content/Intent;'),('0002',2,'const-class v1, Lapp/Intro;'),
             ('0004',3,'invoke-direct {v0, v2, v1}, Landroid/content/Intent;.<init>:(Landroid/content/Context;Ljava/lang/Class;)V // method@0001'),
             ('0007',4,'invoke-virtual {v3, v0}, Lapp/TypedLauncher;.launch:(Landroid/content/Intent;)V // method@0002'),
             ('000a',5,'invoke-virtual {v2}, Landroid/app/Activity;.finish:()V // method@0003')]
        extras=inspect(method,'classes.dex',ins);nodes=[{'class':'app/Main','target':None},{'class':'app/Intro','target':None}]
        rows=activity_rows(extras,nodes,{'app/Main'},{'app/TypedLauncher':'androidx/activity/result/ActivityResultLauncher'},{},{method:{}})
        self.assertEqual(rows[0]['non_launcher_targets'],['app/Intro']);self.assertEqual(rows[0]['finish_lexical_order'],'after_start')
        self.assertEqual(rows[0]['verdict'],'explicit-startup-target')
        self.assertEqual(activity_rows(extras,nodes,{'app/Main'},{},{},{method:{}}),[])
    def test_branch_hint_not_proven_target(self):
        method='app/Splash.start()V'
        ins=[('0000',1,'const-class v1, Lapp/Main;'),('0002',2,'if-eqz v3, 0008 // +0006'),
             ('0004',3,'invoke-virtual {v0, v2}, Landroid/app/Activity;.startActivity:(Landroid/content/Intent;)V // method@0001')]
        rows=activity_rows(inspect(method,'classes.dex',ins),[{'class':'app/Splash','target':None},{'class':'app/Main','target':None}],{'app/Splash'},{},{},{})
        self.assertEqual(rows[0]['verdict'],'callback-or-target-candidate');self.assertEqual(rows[0]['non_launcher_targets'],[])
        self.assertEqual(rows[0]['class_hints'],['app/Main'])
    def test_provider_exact_owners_and_loader_scope(self):
        self.assertEqual(provider_api('java/util/ServiceLoader','load',''), 'service-loader-resource-verification')
        self.assertIsNone(provider_api('app/ServiceLoader','load',''))
        self.assertIsNone(provider_api('java/security/MessageDigest','getInstance',''))
        self.assertEqual(provider_api('sun/security/jca/Providers','getSunProvider',''),'direct-boot-provider')
        result=boot_visibility(set(),{PROVIDER.replace('.','/')})
        self.assertTrue(result['runtime_definition']);self.assertFalse(result['runtime_definition_repairs_boot_lookup'])
        self.assertEqual(result['boot_lookup'],'missing-in-pinned-boot-jars')
    def test_runtime_only_has_no_static_predicate(self):
        self.assertEqual(inspect('app/Renderer.draw()V','classes.dex',[('0000',1,'invoke-static {v0, v1, v2, v3}, Landroid/opengl/EGL14;.eglCreateWindowSurface:(Landroid/opengl/EGLDisplay;Landroid/opengl/EGLConfig;Ljava/lang/Object;[I)Landroid/opengl/EGLSurface; // method@0010')]),[])

class MatrixTests(unittest.TestCase):
    def test_coverage_and_known_answers(self):
        rows=json.loads((OUT/'matrix.json').read_text());self.assertEqual(len(rows),198)
        self.assertEqual(len({(r['key'],r['family']) for r in rows}),198)
        by={(r['key'],r['family']):r for r in rows}
        self.assertTrue(all(r['status']=='runtime-only' for r in rows if r['family']=='egl-window-recreation' and r['key']!='subwaysurfers'))
        self.assertEqual(by['subwaysurfers','boot-conscrypt-fallback']['status'],'unknown-input')
        for key in ['fd-droidify','newpipe','fd-catima','fd-com-amaze-filemanager','antennapod']:
            self.assertEqual(by[key,'boot-conscrypt-fallback']['status'],'conditional-startup-provider-requirement')
        data=json.load(gzip.open(OUT/'evidence/aegis.json.gz','rt'))
        self.assertTrue(any('com/beemdevelopment/aegis/ui/IntroActivity' in x['non_launcher_targets'] and x['startup_reachable']=='conditional-static' for x in data['activity']))
        for key in ['fd-android','fd-k9']:
            data=json.load(gzip.open(OUT/f'evidence/{key}.json.gz','rt'))
            self.assertTrue(any('com/fsck/k9/activity/UpgradeDatabaseActivity' in x['non_launcher_targets'] for x in data['activity']))
        data=json.loads((OUT/'results.json').read_text());self.assertEqual(data['analysis'],'post-hoc');self.assertEqual(data['prior_v2_score']['exact_correct'],30)
    def test_old_freeze_and_backtest_unchanged(self):
        guard=json.loads((OUT/'preserved-inputs.json').read_text())
        for name,expected in guard['files'].items():self.assertEqual(sha(ROOT/name),expected,name)
        frozen=json.loads((V2/'freezes/v2/freeze.json').read_text())
        for name,expected in frozen['hashes'].items():self.assertEqual(sha(V2/'freezes/v2'/name),expected,name)
        self.assertEqual(sha(V2/'freezes/v2/predictions.csv'),'be1879a15267f3c208236fce946644ea0580319b9cf8c9395218091182058bed')
        self.assertEqual(sha(V2/'backtests/v2-5ea/results.json'),'39d11aa129f5bab523a89e6f5c9d6719f22eefad43bf439de380bb49a218daca')

if __name__=='__main__':unittest.main()
