import hashlib,json,tempfile,unittest
from pathlib import Path
from audit_run import audit_run,record_facts,projected_hashes,observations_from_run,launcher_verified
from score import HERE,effective_profile,score
SERIAL='5ea34a4500000000000000001123012c'
BOOT='51812b02-ec64-4d36-821c-ffd94531fb45'
class AuditTests(unittest.TestCase):
 def fixture(self,root):
  run=root/SERIAL;run.mkdir();profile=effective_profile(HERE/'freezes/v2',HERE/'execution-amendment-5ea.json');package=json.loads((HERE/'freezes/v2/evidence/v3c-package.json').read_text());expected,_=projected_hashes(package,profile)
  text='\n'.join(sorted(h+'  '+path for path,h in expected.items()));short=hashlib.sha256(text.encode()).hexdigest()[:12]
  (run/'runtime-fingerprint.txt').write_text(text+'\n');(run/'facts.txt').write_text('RUNTIME fingerprint='+short+' files='+str(len(expected))+' (runtime-fingerprint.txt)\nTOTAL\n');(run/'baseline.json').write_text(json.dumps({'boot_id':BOOT,'runtime_fingerprint':short}))
  lines=['Wed Sep 30 03:34:55 CST 2026',BOOT,'foundation=979']
  for path in ['/system/lib64/','/proc/979/root/system/lib64/']:
   for name,h in profile['installer_sha256'].items():lines.append(h+'  '+path+name)
  (run/'installer-readback.txt').write_text('\n'.join(lines)+'\n');return run,profile
 def test_profile(self):
  with tempfile.TemporaryDirectory() as tmp:
   run,profile=self.fixture(Path(tmp));result=audit_run(run);self.assertTrue(result['verified'],result['errors']);self.assertEqual(result['runtime_projection']['matched'],87)
   frozen=json.loads((HERE/'freezes/v2/profile.json').read_text());self.assertNotIn(SERIAL,frozen['boards']);self.assertIn(SERIAL,profile['boards'])
   folder=run/'example';folder.mkdir();r={'key':'example','package':'app.example','boot_id':BOOT,'bms':{'uid':123},'screenshots':[]};(folder/'record.json').write_text(json.dumps(r));(folder/'processes-t5.txt').write_text('PID PPID UID NAME\n10 1 123 appspawn-x\n11 10 123 sh\n12 1 456 appspawn-x\n')
   info=record_facts(folder/'record.json',result);self.assertTrue(info['processes']['t5']['alive']);self.assertEqual(len(info['processes']['t5']['app_processes']),1);self.assertEqual(len(info['processes']['t5']['same_uid_helpers']),1);self.assertIsNone(info['grant_verified']);self.assertEqual(info['captured_count'],0)
   self.assertTrue(launcher_verified('anki','com.ichi2.anki.IntentHandler'));self.assertFalse(launcher_verified('anki','leakcanary.internal.activity.LeakActivity'));self.assertTrue(launcher_verified('wikipedia','org.wikipedia.DefaultIcon'))
   r.update(serial=SERIAL,clicked=True,clicked_at=1790710772.0,native_assembly={'status':'not_needed'})
   (folder/'record.json').write_text(json.dumps(r))
   obs,facts=observations_from_run([{'key':'example','grant_verified':True,'clicked_at':'2027-01-01T00:00:00+00:00','lit':'yes','screenshot_evidence':str(folder/'missing.jpeg')}],run,result)
   from finalize_backtest import select_first_attempts
   later=Path(tmp)/'later';later.mkdir();(run/'summary.json').write_text(json.dumps({'records':[{'key':'example','lit':False}]}));(later/'summary.json').write_text(json.dumps({'records':[{'key':'example','lit':True},{'key':'new'}]}));selected,duplicates,_=select_first_attempts([run,later]);self.assertEqual(selected['example'],run);self.assertEqual(selected['new'],later);self.assertEqual(len(duplicates),1)
   self.assertIsNone(obs[0]['grant_verified']);self.assertNotEqual(obs[0]['clicked_at'],'2027-01-01T00:00:00+00:00');self.assertIsNone(obs[0]['screenshot_evidence']);self.assertTrue(obs[0]['runtime_audit_verified'])
   r['serial']='wrong';(folder/'record.json').write_text(json.dumps(r));self.assertIn('record_board_unknown_or_mismatch',record_facts(folder/'record.json',result)['errors'])
 def test_rejection(self):
  for name,change,reason in [('facts.txt',lambda t:t.replace('fingerprint=','fingerprint=000000000000'),'facts_header_invalid'),('runtime-fingerprint.txt',lambda t:t.replace('0509fe235a7883b5cd9b57477221cb868465de944c6f70ed0cf2835b0fe4a97c','0'*64,1),'runtime_hash_mismatch'),('installer-readback.txt',lambda t:t.replace('7048c7c50a828fc744b5f06e4e9ec50ac317a2272f33789249fc63e43a655a18','1'*64),'libapk_installer.so:hash_mismatch'),('installer-readback.txt',lambda t:t.replace(BOOT,'11111111-1111-1111-1111-111111111111'),'installer_boot_unknown_or_mismatch')]:
   with tempfile.TemporaryDirectory() as tmp:
    run,profile=self.fixture(Path(tmp));path=run/name;path.write_text(change(path.read_text()));result=audit_run(run);self.assertFalse(result['verified']);self.assertIn(reason,result['errors'])
  with tempfile.TemporaryDirectory() as tmp:
   run,profile=self.fixture(Path(tmp));(run/'installer-readback.txt').unlink();result=audit_run(run);self.assertIn('installer_readback_missing',result['errors'])
   p={'key':'x','apk_sha256':'exact','forecast':'亮','prior_wall':'wall','progress_checkpoint':'step'}
   o=dict(key='x',board=SERIAL,apk_sha256='exact',**{k:profile[k] for k in ['package_sha256','jar_sha256','installer_sha256']},grant_verified=None,select_launcher_verified=True,batch_sidecars_enabled=True,profile_evidence='facts',runtime_audit_verified=False,clicked_at='2026-09-30T05:00:00+08:00',lit='yes',alive=True)
   r=score([p],[o],profile,'2026-09-30T03:00:00+08:00')['rows'][0];self.assertFalse(r['eligible']);self.assertIn('grant_verified_unknown',r['reasons']);self.assertIn('runtime_audit_unverified',r['reasons']);self.assertEqual(r['observed'],'unknown')
if __name__=='__main__':unittest.main()
