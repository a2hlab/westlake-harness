import hashlib,json,unittest
from pathlib import Path
from rules import FAMILIES,inspect_method,manifest_providers,provider_gaps
HERE=Path(__file__).resolve().parent
class FeedbackTests(unittest.TestCase):
 def test_rules(self):
  def call(owner,name,sig):
   return inspect_method('app/Documents.<init>()V','classes.dex',[('0010',12,f'invoke-virtual {{v0, v1}}, L{owner};.{name}:{sig}')])
  cases=[('android/app/Service','startForeground','(ILandroid/app/Notification;)V','service-foreground-null'),('android/os/BatteryManager','getIntProperty','(I)I','battery-service-null'),('android/os/SystemVibrator','getInfo','()Landroid/os/VibratorInfo;','vibrator-info-null'),('android/app/PendingIntent','getBroadcast','(Landroid/content/Context;ILandroid/content/Intent;I)Landroid/app/PendingIntent;','pendingintent-null'),('android/app/AlarmManager','cancel','(Landroid/app/PendingIntent;)V','alarm-initialization-null'),('android/os/Process','getElapsedCpuTime','()J','process-cpu-jni'),('android/provider/DocumentsProvider','<init>','()V','documents-provider-permission'),('android/os/Environment','getExternalStorageDirectory','()Ljava/io/File;','storage-initializer')]
  for owner,name,sig,fam in cases:
   row=call(owner,name,sig);self.assertEqual(row[0]['family'],fam);self.assertEqual(row[0]['runtime_failure'],'unknown')
   self.assertFalse(call('app/Unrelated',name,sig))
  raw='''E: manifest
  E: application
    E: provider
      A: android:name=".Documents"
    E: provider
      A: android:name=".Safe"
      A: android:permission="android.permission.MANAGE_DOCUMENTS"
    E: provider
      A: android:name=".Other"
'''
  ps=manifest_providers(raw,'app')
  calls=call('android/provider/DocumentsProvider','<init>','()V')
  calls.append({**calls[0],'method':'app/Safe.<init>()V'})
  gaps=provider_gaps(ps,calls)
  self.assertEqual([g['is_gap'] for g in gaps],[True,False,False])
  self.assertEqual(gaps[-1]['verdict'],'unknown-provider-inheritance')
 def test_matrix(self):
  rows=json.loads((HERE/'matrix.json').read_text())
  self.assertEqual(len(rows),256);self.assertEqual(len({r['app'] for r in rows}),32)
  for key in {r['app'] for r in rows}:self.assertEqual({r['family'] for r in rows if r['app']==key},set(FAMILIES))
  for row in rows:
   self.assertTrue((HERE/row['evidence']).exists());self.assertEqual(row['runtime_null_or_missing_implementation'],'unknown')
  freeze=json.loads((HERE/'freeze.json').read_text())
  for x in freeze['outputs']:self.assertEqual(hashlib.sha256((HERE/x['path']).read_bytes()).hexdigest(),x['sha256'])
  pre=HERE.parent/'2026-09-30-r16-prospective'
  for line in (pre/'SHA256SUMS').read_text().splitlines():
   h,n=line.split('  ',1);self.assertEqual(hashlib.sha256((pre/n).read_bytes()).hexdigest(),h,n)
if __name__=='__main__':unittest.main()
