"""Host-only temporary fixtures; no fixture acceptance or view is published."""
import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import consume,increment

class ConsumerTests(unittest.TestCase):
 def test_pending_cli_rejects_before_views(self):
  with tempfile.TemporaryDirectory(prefix='api-core-test-',dir=increment.HERE) as tmp:
   out=Path(tmp)/'formal'
   r=subprocess.run([sys.executable,str(increment.HERE/'increment.py'),'build','--request',str(increment.HERE/'request.pending.json'),'--out',str(out)],capture_output=True,text=True)
   self.assertEqual(r.returncode,2);self.assertFalse(out.exists())
 def test_authority_wrong_board_boot_runtime_fixture_and_partial(self):
  authority={'status':'ACCEPT_SCOPED_STARTUP_NONREGRESSION_WITH_EXISTING_LIMITATIONS','reviewer':'outer(codex)','serial':consume.SERIAL,'boot_id':consume.BOOT,'candidate_runtime_sha256':consume.RUNTIME,'canonical_keys':128,'driver_exited':True,'driver_exit_code':None,'scope':'startup/screenshots only','limitations':['fixture test retains original raw failures']}
  mutations=[('serial','5ea34a4500000000000000001123012c'),('boot_id','00000000-0000-0000-0000-000000000000'),('candidate_runtime_sha256','0'*64),('fixture',True),('canonical_keys',127),('driver_exited',False),('driver_exit_code',0),('status','PENDING'),('limitations',[])]
  with tempfile.TemporaryDirectory(prefix='fixture-authority-') as tmp:
   path=Path(tmp)/'fixture-not-publishable.json'
   for key,value in mutations:
    doc=copy.deepcopy(authority);doc[key]=value;path.write_text(json.dumps(doc))
    with self.subTest(key=key),patch.object(consume,'pin',return_value=path):
     with self.assertRaises(ValueError):consume.consume({'schema':'api-final61b-evidence-request/v1','execution_enabled':False,'authority':{'path':'fixture-only','sha256':'0'*64}})
 def test_facts_key_tier_completeness(self):
  _,tiers=consume.base()
  text='\n'.join(f'{key} shots 2/2  alive t5=no t{tier}=no  foreground_unconfirmed' for key,tier in tiers.items())+'\nTOTAL keys=128 screenshots_captured=256/256 alive_t5=0 alive_t10=0 alive_t20=0\n'
  self.assertIn('256/256',consume.validate_facts(text,tiers))
  for bad in [text.replace('256/256','255/256'),text.replace('t20=no','t10=no',1),text.split('\n',1)[1],text+text.splitlines()[0]+'\n']:
   with self.assertRaises(ValueError):consume.validate_facts(bad,tiers)
 def test_record_and_shot_schema_without_device(self):
  apps,tiers=consume.base();key=next(iter(apps));app=apps[key];tier=tiers[key]
  with tempfile.TemporaryDirectory(prefix='fixture-record-') as tmp:
   p=Path(tmp);record=p/'fixture-record.json';image=p/'fixture-image';image.write_bytes(b'UNIT_FIXTURE_NOT_REAL_IMAGE')
   shots=[{'path':str(image),'sha256':'1'*64,'scheduled_seconds':t,'captured':True} for t in (5,tier)]
   doc={'serial':consume.SERIAL,'boot_id':consume.BOOT,'key':key,'package':app['package'],'apk_sha256':app['apk_sha256'],'status':'foreground_unconfirmed','screenshots':shots}
   record.write_text(json.dumps(doc));row={'key':key,'record':{'path':str(record),'sha256':'2'*64},'record_status':doc['status'],'shots':shots}
   def fixture_pin(ref):return Path(ref['path']) # Explicit unit substitution only; production pin remains strict.
   keys,count,_=consume.row_objects([row],apps,tiers,fixture_pin);self.assertEqual((keys,count),({key},2))
   for mutation in ['missing-shot','duplicate-key','wrong-board','relabeled-status','wrong-apk']:
    rows=copy.deepcopy([row]);actual=copy.deepcopy(doc)
    if mutation=='missing-shot':rows[0]['shots'].pop()
    elif mutation=='duplicate-key':rows.append(copy.deepcopy(row))
    elif mutation=='wrong-board':actual['serial']='5ea34a4500000000000000001123012c'
    elif mutation=='wrong-apk':actual['apk_sha256']='0'*64
    else:rows[0]['record_status']='PASS'
    record.write_text(json.dumps(actual))
    with self.subTest(mutation=mutation),self.assertRaises(ValueError):consume.row_objects(rows,apps,tiers,fixture_pin)
 def test_production_pin_hash_and_path_refuse(self):
  with self.assertRaises(ValueError):consume.pin({'path':'$WORKSPACES/westlake-harness/benchmark/2026-10-13-api-progress-r6-full128/views/api-progress.json','sha256':'0'*64})
  with self.assertRaises(ValueError):consume.pin({'path':'relative.json','sha256':'0'*64})
 def test_original_detached_completion_without_global_rc_fixture_only(self):
  driver_ref=consume.read(increment.HERE/'base-pins.json')[6]
  original_pin=consume.pin;actual_driver=original_pin(driver_ref)
  with tempfile.TemporaryDirectory(prefix='UNIT_FIXTURE_ONLY-detach-',dir=increment.HERE) as tmp:
   # Temporary fake workspace makes this fixture portable even when the
   # code checkout is outside WORKSPACES. Production path gates stay exact.
   def fixture_pin(ref):return actual_driver if ref==driver_ref else original_pin(ref)
   with patch.object(consume,'WS',Path(tmp)),patch.object(consume,'pin',side_effect=fixture_pin):
    root=Path(tmp)/'round';root.mkdir();(root/'round-complete.json').write_text(json.dumps({'recorded_keys':128,'UI_verdict':'pending_outer_review'}));records={}
    for number in range(1,9):
     window=root/f'window-{number:02d}';runner=window/'runner';runner.mkdir(parents=True)
     result=runner/'board-run-result.json';result.write_text(json.dumps({'smoke':0,'after_lock':0,'before_unlock':0}))
     for phase in ('pre-lock-identity','before-identity','after-identity'):
      folder=window/phase;folder.mkdir();(folder/'identity.json').write_text(json.dumps({'synthetic':False,'passed':True,'diff':{},'serial':consume.SERIAL,'boot_before':consume.BOOT,'boot_after':consume.BOOT}))
     path=runner/'fixture-only-key'/'record.json';path.parent.mkdir();path.write_text('{}');records[f'fixture-{number}']={'path':str(path),'sha256':consume.sha(path)}
    result=consume.detached_completion(records)
    self.assertIsNone(result['driver_exit_code']);self.assertEqual(len(result['windows']),8)
    self.assertEqual(sum(len(r['identity_receipts']) for r in result['windows']),24)
    bad=root/'window-08/runner/board-run-result.json';bad.write_text(json.dumps({'smoke':0,'after_lock':0,'before_unlock':1}))
    with self.assertRaisesRegex(ValueError,'rc failed'):consume.detached_completion(records)
    bad.write_text(json.dumps({'smoke':0,'after_lock':0,'before_unlock':0}))
    (root/'round-complete.json').write_text(json.dumps({'recorded_keys':127}))
    with self.assertRaisesRegex(ValueError,'completion'):consume.detached_completion(records)
 def test_original_nativepeer_shape_and_drift_refusal_fixture_only(self):
  apps,tiers=consume.base();key=next(iter(apps));app=apps[key]
  with tempfile.TemporaryDirectory(prefix='UNIT_FIXTURE_ONLY-peer-') as tmp:
   p=Path(tmp);image=p/'fixture-only-image';image.write_bytes(b'UNIT_FIXTURE_ONLY')
   rec=p/'fixture-only-record.json';rec.write_text(json.dumps({'apk_sha256':app['apk_sha256'],'screenshots':[{'scheduled_seconds':tiers[key],'sha256':consume.sha(image),'captured':True}]}))
   ref={'path':str(rec),'sha256':consume.sha(rec)};records={key:ref}
   row={'key':key,'record_sha256':ref['sha256'],'boot_id':consume.BOOT,'actual_image':str(image),'actual_image_sha256':consume.sha(image),'verdict':'UNIT_FIXTURE_ONLY','observation':'UNIT_FIXTURE_ONLY; no published acceptance'}
   doc={'status':'ACCEPT_SCOPED_UNIT_FIXTURE_ONLY','rows':[row]}
   def fixture_pin(ref):return Path(ref['path'])
   with patch.object(consume,'pin',side_effect=fixture_pin):
    keys,raw=consume.peer_rows(doc,apps,tiers,records);self.assertEqual(keys,{key});self.assertEqual(raw[0]['observation'],row['observation'])
    self.assertIn('absent',raw[0]['apk_basis'])
    for field,value in [('record_sha256','0'*64),('boot_id','wrong-boot'),('apk_sha256','0'*64),('actual_image_sha256','0'*64),('reviewed_scheduled_seconds',20 if tiers[key]==10 else 10)]:
     bad=copy.deepcopy(doc);bad['rows'][0][field]=value
     with self.subTest(field=field),self.assertRaises(ValueError):consume.peer_rows(bad,apps,tiers,records)
 def test_two_route_identity_and_complete_closeout(self):
  apps,tiers=consume.base();key=next(iter(apps));records={key:{'path':'fixture-only-record','sha256':'1'*64}}
  with tempfile.TemporaryDirectory(prefix='fixture-review-') as tmp:
   p=Path(tmp)/'fixture-review.json';p.write_text(json.dumps({'schema':consume.BMS_SCHEMA,'rows':[{'key':key,'shots':[{'personally_viewed':True},{'personally_viewed':True}],'note':'fixture only'}]}))
   with patch.object(consume,'pin',return_value=p),patch.object(consume,'row_objects',return_value=({key},2,records)):
    with self.assertRaisesRegex(ValueError,'actual128'):consume.review_route([{'path':'fixture-only','sha256':'0'*64}],apps,tiers,records)
   p.write_text(json.dumps({'observer_checkpoint':{},'visual_result':{'reviewed_keys':127,'reviewed_actual_images':254}}))
   observer=Path(tmp)/'fixture-observer.json';observer.write_text(json.dumps({'schema':consume.BMS_SCHEMA,'rows':[{'key':k} for k in apps]}))
   with patch.object(consume,'pin',side_effect=[p,observer]):
    with self.assertRaisesRegex(ValueError,'closeout'):consume.review_route([{'path':'fixture-only','sha256':'0'*64}],apps,tiers,records)
 def test_original_render_chain_and_cross_tree_consistency_fixture_only(self):
  # This shape test reuses real315 inputs but injects a UNIT_FIXTURE_ONLY row,
  # renders to two temporary trees and deletes both; no actual acceptance claim.
  source=increment.PARENT/'increment.py';ref={'path':'$WORKSPACES/'+str(source.relative_to(consume.WS)),'sha256':consume.sha(source),'supports':'UNIT_FIXTURE_ONLY renderer evidence; not actual61b acceptance'}
  binding={'authority':{'status':'UNIT_FIXTURE_ONLY_NOT_ACCEPTED','limitations':['UNIT_FIXTURE_ONLY; no actual61b verdict']},'authority_pin':{k:ref[k] for k in ('path','sha256')},'facts_total':'UNIT_FIXTURE_ONLY','evidence':[ref]}
  parent_before={str(p):consume.sha(p) for p in (increment.PARENT/'views').iterdir() if p.is_file()}
  with tempfile.TemporaryDirectory(prefix='fixture-render-') as tmp:
   one=Path(tmp)/'one';two=Path(tmp)/'moved-tree';one.mkdir();two.mkdir()
   a=increment.render(one,binding);b=increment.render(two,binding)
   self.assertEqual(a['old_rows_unchanged'],314);self.assertEqual(a['changed_fields'],sorted(consume.FIELDS));self.assertEqual(b['validated_rows'],315)
   for name in ['API-PROGRESS.zh.md','index.html','index.en.html','api-progress.csv','api-progress.json']:
    self.assertEqual((one/'views'/name).read_bytes(),(two/'views'/name).read_bytes())
  self.assertEqual(parent_before,{str(p):consume.sha(p) for p in (increment.PARENT/'views').iterdir() if p.is_file()})

if __name__=='__main__':unittest.main()
