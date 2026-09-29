#!/usr/bin/env python3
import copy, importlib.util, json, os, re, subprocess, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from scan_jni import HERE,REPO,PACKAGES,R8HASH,classify,scan
from scan_apps import method_scan
from scan_io import load
spec=importlib.util.spec_from_file_location('jni_gate',REPO/'scripts/lab/jni_gate.py');gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
class StaticTests(unittest.TestCase):
 def test_jni_matrix_known_answers(self):
  d=load(HERE/'jni-results.json')
  def status(g,cls,m):return next(x['status'] for x in d[g]['methods'] if x['class']==cls and x['method']==m)
  for method in ['nativeParseManifestJson','nativeGetSysProp']:
   self.assertEqual(status('6cb40cd6','adapter/activity/AppSchedulerBridge',method),'missing')
   self.assertIn(status('v3-74d1d6d4','adapter/activity/AppSchedulerBridge',method),gate.COVERED)
  self.assertEqual(status('6cb40cd6','android/database/sqlite/SQLiteConnection','nativeOpen'),'stub')
  self.assertIn(status('v3-74d1d6d4','android/database/sqlite/SQLiteConnection','nativeOpen'),gate.COVERED)
  self.assertEqual([sum(x['counts'].values()) for x in d.values()],[5406,5406])
 def test_jni_gate_blocks_new_missing(self):
  matrix=load(HERE/'jni-results.json');baseline=matrix['v3-74d1d6d4']
  # Test-only approval for existing unresolved methods; production approvals stay unchanged.
  exceptions=[{'method':m['id'],'generation':baseline['generation'],'overlay_sha256':R8HASH,'status':m['status'],'approval':'approved','approved_by':'unit-test-fixture-only','reason':'exercise subtraction, not a real approval','evidence':['fixture']} for m in baseline['methods'] if m['status'] not in gate.COVERED]
  with tempfile.TemporaryDirectory(prefix='b10-negative-') as td:
   td=Path(td);allow=td/'allow.json';allow.write_text(json.dumps({'exceptions':exceptions}))
   positive=subprocess.run([sys.executable,str(REPO/'scripts/lab/jni_gate.py'),'--package',baseline['package'],'--matrix',str(HERE/'jni-results.json'),'--allowlist',str(allow)],capture_output=True,text=True)
   self.assertEqual(positive.returncode,0,positive.stdout[:500])
   package=td/'package';package.mkdir();meta=json.loads((PACKAGES['v3-74d1d6d4']/'package.json').read_text())
   # Real fixture package: remove every copy of bridge ELF, not a forged CSV status.
   removed=[k for k in meta['files'] if k.endswith('/liboh_adapter_bridge.so')]
   self.assertTrue(removed)
   for rel in list(meta['files']):
    if rel in removed:del meta['files'][rel];continue
    dest=package/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.symlink_to(PACKAGES['v3-74d1d6d4']/rel)
   (package/'package.json').write_text(json.dumps(meta))
   negative=subprocess.run([sys.executable,str(REPO/'scripts/lab/jni_gate.py'),'--package',str(package),'--allowlist',str(allow)],capture_output=True,text=True)
   self.assertEqual(negative.returncode,1,negative.stdout[:500])
   result=json.loads(negative.stdout)
   self.assertTrue(any('AppSchedulerBridge.nativeParseManifestJson' in x['method'] for x in result['blockers']))
   (HERE/'evidence/gate-negative.json').write_text(json.dumps({'positive_exit':positive.returncode,'negative_exit':negative.returncode,'removed_package_files':removed,'blocked_count':result['blocked_count'],'manifest_method':[x for x in result['blockers'] if 'AppSchedulerBridge.nativeParseManifestJson' in x['method']]},indent=2)+'\n')
  draft=load(HERE/'jni-allowlist.json');self.assertFalse(gate.evaluate(baseline,draft)['pass'])
  self.assertGreater(gate.evaluate(baseline,draft)['excepted_count'],0)
 def test_unknown_marked_not_guessed(self):
  decl={'class':'android/example/Dynamic','method':'nativeX','signature':'()I'}
  self.assertEqual(classify(decl,[],{})[0],'unknown')
  calls,_,_=method_scan('example',[('0000',1,'invoke-static {v0}, Landroid/os/ServiceManager;.getService:(Ljava/lang/String;)Landroid/os/IBinder; // method@0001')],'classes.dex',0,set())
  self.assertEqual(calls[0]['service'],'unknown');self.assertTrue(calls[0]['reason'])
  compat=[('0000',1,'const-class v2, Landroid/os/UserManager; // type@0010'),('0002',2,'invoke-static {v0, v2}, Landroidx/core/content/ContextCompat;.getSystemService:(Landroid/content/Context;Ljava/lang/Class;)Ljava/lang/Object; // method@0001')]
  self.assertEqual(method_scan('example',compat,'classes.dex',0,set())[0][0]['service'],'user')
  # Literal is killed by register overwrite and by a control-flow join.
  ins=[('0000',1,'const-string v0, "notification" // string@0000'),('0002',2,'move-result-object v0'),('0003',3,'invoke-static {v0}, Landroid/os/ServiceManager;.getService:(Ljava/lang/String;)Landroid/os/IBinder; // method@0001')]
  self.assertEqual(method_scan('example',ins,'classes.dex',0,set())[0][0]['service'],'unknown')
  for d in load(HERE/'jni-results.json').values():
   for m in d['methods']:
    if m['status']=='unknown':self.assertTrue(m['reason'])
 def test_service_matrix_known_gaps(self):
  d=load(HERE/'service-results.json');self.assertEqual(len({x['app'] for x in d}),20)
  etar=[x for x in d if x['app']=='fd-etar' and x['service']=='notification'];self.assertTrue(etar)
  self.assertIn(etar[0]['status'],{'missing','westlake-only'})
  user=[x for x in d if x['service']=='user'];self.assertTrue(user)
  self.assertTrue(all(x['status'] in {'provided','r8b-stub'} for x in user))
  self.assertTrue(all(x['calls'] and x['apk_sha256'] for x in d))
 def test_prediction_backtest(self):
  d=load(HERE/'results.json');b=d.get('legacy_backtest',d['backtest']);scored=[x for x in b['rows'] if x['eligible']]
  self.assertEqual(b['total'],len(scored));self.assertEqual(b['hits'],sum(x['hit'] for x in scored));self.assertGreater(b['total'],0)
  self.assertEqual({x['task'] for x in b['rows']},{63,65,68,69,71})
  ranks=d['predictions']['ranking']
  for name in ['stub_ok_ranking','needs_real_ranking']:
   group=d['predictions'][name];self.assertEqual([x['startup_affected_apps'] for x in group],sorted([x['startup_affected_apps'] for x in group],reverse=True))
  self.assertTrue(all(x['startup_affected_apps']<=x['full_reference_apps'] for x in ranks))
  self.assertTrue(all(x['reason'] for x in b['rows']));self.assertTrue(all(x['copy_source'] for x in ranks))
 def test_startup_reachability(self):
  from scan_reachability import compute_paths
  methods={
   'app/App.onCreate()V':{'edges':[{'target':'app/Init.init()V','kind':'invoke-static'}]},
   'app/Init.init()V':{'edges':[{'target':'app/Init.init()V','kind':'invoke-static'}]},
   'app/Settings.onClick()V':{'edges':[]},
  }
  roots=[{'method':'app/App.onCreate()V','category':'application'}]
  paths,_,_=compute_paths(methods,{}, {}, roots)
  self.assertIn('app/Init.init()V',paths);self.assertNotIn('app/Settings.onClick()V',paths)
  methods['app/App.onCreate()V']['edges']=[{'target':'api/Listener.call()V','kind':'invoke-interface'}]
  methods['app/One.call()V']={'edges':[]};methods['app/Two.call()V']={'edges':[]}
  paths,unresolved,_=compute_paths(methods,{}, {'app/One':['api/Listener'],'app/Two':['api/Listener']},roots)
  self.assertNotIn('app/One.call()V',paths);self.assertEqual(unresolved['ambiguous_dispatch'],1)
  services=load(HERE/'service-results.json')
  self.assertTrue(any(x['startup_reachable']=='unknown' for x in services))
  self.assertTrue(any(x['startup_reachable']=='yes-static' for x in services))
  for row in services:
   self.assertEqual(row['startup_call_count'],len(row['startup_evidence']))
   if row['startup_reachable']=='yes-static':self.assertTrue(row['startup_evidence'])
 def test_typeface_exception_is_candidate(self):
  allow=load(HERE/'jni-allowlist.json')
  candidates=[x for x in allow['exceptions'] if 'nativePrimeDefaultTypeface' in x['method']]
  self.assertEqual(len(candidates),2)
  self.assertTrue(all(x['approval']=='approved' and x['approved_by'] for x in candidates))
  self.assertTrue(all(x['evidence'][0]['line']==3819 for x in candidates))
 def test_build_silent_skip_fails(self):
  audit=load(HERE/'build-audit.json')
  for f in set(x['file'] for x in audit['changed']):subprocess.run(['bash','-n',str(REPO/f)],check=True)
  script=(REPO/'bms/src/adapter/build/inner/compile_oh_adapter_bridge.sh').read_text()
  begin=script.index('for src in \\\n    "$ADAPTER_ROOT/framework/package-manager/jni/oh_bundle_mgr_client.cpp"')
  segment=script[begin:script.index('\ndone',begin)+5]
  files=['oh_bundle_mgr_client.cpp','apk_manifest_jni.cpp','apk_manifest_parser.cpp','axml_parser.cpp']
  cases=[]
  with tempfile.TemporaryDirectory(prefix='b10-build-') as td:
   base=Path(td);folder=base/'framework/package-manager/jni';folder.mkdir(parents=True)
   for f in files:(folder/f).touch()
   env={**os.environ,'ADAPTER_ROOT':td}
   self.assertEqual(subprocess.run(['bash','-c',segment],env=env,capture_output=True).returncode,0)
   for f in files:
    p=folder/f;p.unlink();r=subprocess.run(['bash','-c',segment],env=env,capture_output=True,text=True)
    self.assertNotEqual(r.returncode,0);self.assertIn(str(p),r.stderr)
    cases.append({'removed':f,'exit':r.returncode,'reported_path':str(p)});p.touch()
  (HERE/'evidence/build-negatives.json').write_text(json.dumps({'scope':'Actual source collection loop from compile_oh_adapter_bridge.sh, four omissions independently; full cross-compilation not run','cases':cases,'shell_syntax_files':len(set(x['file'] for x in audit['changed']))},indent=2)+'\n')
if __name__=='__main__':unittest.main()
