"""Exercise real CLI control flow; device boundary must remain untouched on refusal."""
from pathlib import Path
import contextlib,hashlib,io,json,sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/lab'))
import deploy_generation as deploy
import deployment_native_gate as gate

class Hook(unittest.TestCase):
 def test_all_forward_modes_refuse_before_device(self):
  for mode in ([],['--dry-run'],['--upgrade'],['--replace','/system/android/lib64/libx.so'],['--add','/system/android/lib64/libx.so']):
   with self.subTest(mode=mode),patch.object(deploy,'load_package',return_value={'generation':'a'*64}),patch.object(deploy,'check_frozen_package'),patch.object(gate,'check',side_effect=RuntimeError('N1/N2 refused')),patch.object(deploy,'Deployment') as board,patch.object(deploy.subprocess,'call') as orb,contextlib.redirect_stdout(io.StringIO()) as stdout:
    with self.assertRaisesRegex(RuntimeError,'refused'):deploy.main([sorted(deploy.SERIALS)[0],'/not-used',*mode])
    board.assert_not_called();orb.assert_not_called();self.assertNotIn('"passed": true',stdout.getvalue())
 def test_pass_dryrun_does_not_dispatch(self):
  manifest={'generation':'a'*64,'files':{'x':'b'*64},'mounts':[]}
  with patch.object(deploy,'load_package',return_value=manifest),patch.object(deploy,'check_frozen_package'),patch.object(gate,'check',return_value={'binding':'c','package':'unused','report':{}}),patch.object(deploy,'Deployment') as board,patch.object(deploy.subprocess,'call') as orb,contextlib.redirect_stdout(io.StringIO()) as stdout:
   deploy.main([sorted(deploy.SERIALS)[0],'/unused','--dry-run','--upgrade'])
   self.assertTrue(json.loads(stdout.getvalue())['passed']);board.assert_not_called();orb.assert_not_called()
 def test_missing_reader_refuses(self):
  with patch.object(gate,'binding',return_value='stable'),patch.dict(gate.os.environ,{},clear=True),patch.object(gate.shutil,'which',return_value=None):
   with self.assertRaisesRegex(RuntimeError,'requires host readelf'):gate.check(Path('/unused'))
 def test_recovery_target_checked_before_dispatch(self):
  with patch.object(deploy,'load_package',return_value={'generation':'a'*64}),patch.object(deploy,'check_frozen_package'),patch.object(gate,'check',side_effect=[{'binding':'new'},RuntimeError('recovery rejected')]) as checked,patch.object(deploy,'Deployment') as board,patch.object(deploy.subprocess,'call') as orb:
   with self.assertRaisesRegex(RuntimeError,'recovery rejected'):deploy.main([sorted(deploy.SERIALS)[0],'/candidate','--recovery-package','/underlay'])
   self.assertEqual([c.args[0] for c in checked.call_args_list],[Path('/candidate'),Path('/underlay')]);board.assert_not_called();orb.assert_not_called()
 def test_missing_inputs_refuse_before_orb(self):
  with tempfile.TemporaryDirectory() as td,patch.object(deploy,'load_package',return_value={'generation':'a'*64}),patch.object(deploy,'check_frozen_package'),patch.object(deploy,'Deployment') as board,patch.object(deploy.subprocess,'call') as orb:
   with self.assertRaisesRegex(RuntimeError,'inputs missing'):deploy.main([sorted(deploy.SERIALS)[0],td,'--dry-run'])
   board.assert_not_called();orb.assert_not_called()
 def test_rollback_gates_restored_package(self):
  with patch.object(deploy,'load_package',return_value={'generation':'a'*64}),patch.object(deploy,'check_frozen_package') as frozen,patch.object(gate,'restore_target',return_value=(Path('/restore'),{'path':'state'})) as target,patch.object(gate,'check',side_effect=RuntimeError('restore refused')) as check,patch.object(deploy,'Deployment') as board,patch.object(deploy.subprocess,'call') as orb:
   with self.assertRaisesRegex(RuntimeError,'restore refused'):deploy.main([sorted(deploy.SERIALS)[0],'/failed','--rollback','--rollback-state','receipt.json'])
   frozen.assert_called_once_with(Path('/restore'));check.assert_called_once_with(Path('/restore'),None);board.assert_not_called();orb.assert_not_called()
 def test_restore_identity_and_single_target(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);old=root/'old';old.mkdir();(old/'package.json').write_text('{}');state=root/'state.json'
   previous={'package_path':str(old),'package_sha256':gate.sha(old/'package.json')}
   d={'serial':'s','generation':'g','status':'active_verified','boot_id':'boot','previous_deployment':previous,'single_replacements':[{'target':'/target','previous_package':str(old),'previous_package_sha256':previous['package_sha256']}]};state.write_text(json.dumps(d))
   self.assertEqual(gate.restore_target(state,'s','g')[0],old);self.assertEqual(gate.restore_target(state,'s','g','/target')[0],old)
   for serial,gen,target in [('wrong','g',None),('s','bad',None),('s','g','/wrong')]:
    with self.assertRaises(RuntimeError):gate.restore_target(state,serial,gen,target)
   (old/'package.json').write_text('{"changed":1}')
   with self.assertRaisesRegex(RuntimeError,'changed'):gate.restore_target(state,'s','g')
 def test_bound_inputs_artifact_and_code_drift(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);(p/'native-checks').mkdir();(p/'native-checks/native-gates.json').write_text('{}');(p/'x').write_bytes(b'elf')
   (p/'package.json').write_text(json.dumps({'files':{'x':gate.sha(p/'x')}}));before=gate.binding(p)
   (p/'native-checks/native-gates.json').write_text('{"changed":true}')
   self.assertNotEqual(before,gate.binding(p));(p/'x').write_bytes(b'corrupt')
   with self.assertRaisesRegex(RuntimeError,'file changed'):gate.binding(p)
 def test_raw_restore_not_implicitly_approved(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'s.json';p.write_text(json.dumps({'serial':'s','generation':'g','status':'active','boot_id':'b'}))
   with self.assertRaisesRegex(RuntimeError,'recovery needed'):gate.restore_target(p,'s','g')
 def test_postpass_drift_stops_before_board(self):
  m={'generation':'a'*64};ticket={'package':'/unused','binding':'a'}
  with patch.object(deploy,'load_package',return_value=m),patch.object(deploy,'check_frozen_package'),patch.object(gate,'check',return_value=ticket),patch.object(gate,'assert_unchanged',side_effect=RuntimeError('changed after preflight')),patch.object(deploy.platform,'system',return_value='Linux'),patch.object(deploy,'Deployment') as board,patch.dict(sys.modules,{'bms_batch':object()}):
   with self.assertRaisesRegex(RuntimeError,'changed after preflight'):deploy.main([sorted(deploy.SERIALS)[0],'/unused'])
   board.assert_not_called()
if __name__=='__main__':unittest.main()
