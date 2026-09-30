import datetime,hashlib,json,tempfile,unittest
from pathlib import Path
from update90 import HERE,dump
from rules90 import inspect_method,FAMILIES
from backtest_batch90 import evaluate,classify,frozen_predictions

class Feedback90Tests(unittest.TestCase):
 def test_rules(self):
  def call(owner,name,sig):
   return inspect_method('test/App.onCreate()V','classes.dex',[('0001',8,f'invoke-virtual {{v0, v1}}, L{owner};.{name}:{sig}')])
  cases=[('android/content/Context','registerReceiver','(Landroid/content/BroadcastReceiver;Landroid/content/IntentFilter;)Landroid/content/Intent;','common-event-jni'),('android/app/job/JobScheduler','cancel','(I)V','jobscheduler-startup'),('android/content/pm/ShortcutManager','getDynamicShortcuts','()Ljava/util/List;','shortcutmanager'),('io/flutter/embedding/engine/loader/FlutterLoader','startInitialization','(Landroid/content/Context;)V','guest-thread-ready'),('com/sun/jna/Native','loadLibrary','(Ljava/lang/String;Ljava/lang/Class;)Ljava/lang/Object;','jna-native-resource'),('android/hardware/Camera','getNumberOfCameras','()I','egl-camera-jni')]
  for owner,name,sig,fam in cases:
   rows=call(owner,name,sig);self.assertEqual(rows[0]['family'],fam);self.assertEqual(rows[0]['missing_implementation'],'unknown')
   self.assertFalse(call('app/Unrelated',name,sig))
  self.assertFalse(call('android/content/Context','registerReceiver','()V'))
  self.assertFalse(call('androidx/work/Worker','toString','()Ljava/lang/String;'))
 def test_batch(self):
  self.assertEqual(classify({'class':'unclassified','fatal':'header failed for /system/lib64/libGLESv3.so'}),'system-loader-noise')
  self.assertEqual(classify({'class':'unclassified','fatal':'No implementation found for int adapter.activity.ActivityManagerAdapter.nativeSubscribeCommonEvent'}),'common-event-jni')
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);pred=root/'pred';run=root/'run';tri=root/'triage.json'
   dump(pred/'predictions.json',[{'app':'a','apk_sha256':'a'*64,'new_family_order':['sharedpreferences-null'],'predicted_first_new_family':'sharedpreferences-null'}])
   dump(pred/'freeze.json',{'frozen_at':'2026-09-29T00:00:00+08:00','outputs':[{'path':'predictions.json','sha256':hashlib.sha256((pred/'predictions.json').read_bytes()).hexdigest()}]})
   dump(run/'plan.json',{'apps':[{'key':'a'}]});dump(run/'a/record.json',{'apk_sha256':'a'*64,'finished_at':1,'clicked_at':2,'bms':{'uid':123},'screenshots':[]})
   (run/'a/processes-t5.txt').write_text('1 0 0 appspawn-x\n')
   dump(tri,{'runs':{str(run):{'rows':[{'key':'a','class':'prefs-npe','fatal':'SharedPreferences null','exit_line':'exit','alive':False}]}}})
   with self.assertRaisesRegex(ValueError,'Full-batch'):evaluate(pred,tri,root/'bad')
   r=evaluate(pred,tri,root/'partial',allow_partial=True);self.assertFalse(r['full_batch_complete'])
   r=evaluate(pred,tri,root/'good',expected_keys=1);self.assertEqual(r['metrics']['classified_first_fatal_agreement']['hits'],1)
   (run/'a/processes-t5.txt').write_text('2 1 123 appspawn-x\n')
   r=evaluate(pred,tri,root/'survivor',expected_keys=1);self.assertEqual(r['metrics']['classified_first_fatal_agreement']['total'],0)
   (pred/'predictions.json').write_text('[]')
   with self.assertRaisesRegex(ValueError,'hash changed'):frozen_predictions(pred)
  actual=json.loads((HERE/'task90-backtest-r15c/results.json').read_text());self.assertTrue(actual['full_batch_complete']);self.assertEqual(actual['observed_keys'],66)
  from backtest85 import verify_freeze
  verify_freeze()
 def test_coverage(self):
  out=HERE/'task90-feedback-static';rows=json.loads((out/'matrix.json').read_text());self.assertEqual(len(rows),224)
  self.assertEqual(len({r['app'] for r in rows}),32)
  for key in {r['app'] for r in rows}:
   self.assertEqual({r['family'] for r in rows if r['app']==key},set(FAMILIES))
  for row in rows:
   self.assertEqual(row['missing_implementation'],'unknown');self.assertTrue((out/row['evidence']).exists())
   self.assertIn(row['startup_reachable'],['yes-static','unknown'])
  freeze=json.loads((out/'freeze.json').read_text())
  for item in freeze['outputs']:self.assertEqual(hashlib.sha256((out/item['path']).read_bytes()).hexdigest(),item['sha256'])
  pred=json.loads((out/'predictions.json').read_text());self.assertEqual(len(pred),66)
  self.assertTrue(all('outcome-informed' in r['prediction_basis'] for r in pred))

if __name__=='__main__':unittest.main()
