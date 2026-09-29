import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('deploy',ROOT/'scripts/lab/deploy_generation.py')
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)

class DeploymentGuards(unittest.TestCase):
    def maps(self, extra=''):
        route='/system/lib64/westlake/route-a/'+d.GEN+'/'
        return '\n'.join('1000-2000 r--p 00000000 00:00 1 '+p for p in [route+'libart.so',route+'libopenjdkjvm.so','/system/android/lib64/liboh_adapter_bridge.so'])+extra
    def test_single_art(self): self.assertTrue(d.check_maps(self.maps())['passed'])
    def test_second_art_instance_rejected_even_same_path(self):
        self.assertFalse(d.check_maps(self.maps('\n3000-4000 r--p 00000000 00:00 1 /system/lib64/westlake/route-a/'+d.GEN+'/libart.so'))['passed'])
    def test_system_openjdk_rejected(self):
        self.assertFalse(d.check_maps(self.maps().replace('/system/lib64/westlake/route-a/'+d.GEN+'/libopenjdkjvm.so','/system/android/lib64/libopenjdkjvm.so'))['passed'])
    def test_accepted_duplicate_bridge_mapping(self):
        self.assertTrue(d.check_maps(self.maps('\n3000-4000 r--p 00000000 00:00 1 /system/android/lib64/liboh_adapter_bridge.so'))['passed'])
    def test_missing_bridge_rejected(self): self.assertFalse(d.check_maps(self.maps().replace('liboh_adapter_bridge.so','other.so'))['passed'])
    def state(self): return {'boot_id':'boot1','remote':'/data/local/tmp/g','mounted':[{'source':'payload/android','target':'/system/android'},{'source':'payload/route/libsigchain.so','target':'/system/android/lib64/libsigchain.so'}]}
    def tops(self):return {'/system/android':'/local/tmp/g/payload/android','/system/android/lib64/libsigchain.so':'/local/tmp/g/payload/route/libsigchain.so'}
    def test_rollback_reverse_nested_mounts(self):self.assertEqual(d.rollback_order(self.state(),'boot1',self.tops()),list(reversed(self.state()['mounted'])))
    def test_no_cross_boot_rollback(self):
        with self.assertRaisesRegex(ValueError,'different boot'): d.rollback_order(self.state(),'boot2',self.tops())
    def test_do_not_unmount_another_owner_overlay(self):
        tops=self.tops();tops['/system/android']='someone_else'
        with self.assertRaisesRegex(ValueError,'mount changed'):d.rollback_order(self.state(),'boot1',tops)
    def test_reject_truncated_serial(self):
        with self.assertRaises(SystemExit) as c:d.main(['61b0657200000000000000324012c','missing','--dry-run'])
        self.assertEqual(c.exception.code,2)
    def fixture(self,root):
        name='payload/android/lib64/liboh_adapter_bridge.so';p=root/name;p.parent.mkdir(parents=True);p.write_bytes(b'fixture')
        m={'generation':d.GEN,'files':{name:d.sha(p)},'mounts':[{'source':'payload/android','target':'/system/android'}]}
        (root/'package.json').write_text(json.dumps(m));return p,m
    def test_payload_tamper(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p,m=self.fixture(root);p.write_bytes(b'tamper')
            with self.assertRaisesRegex(ValueError,'SHA mismatch'):d.load_package(root)
    def test_wrong_bridge_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);self.fixture(root)
            with self.assertRaisesRegex(ValueError,'stage/accept'):d.load_package(root)
    def test_parent_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p,m=self.fixture(root);m['files']['../outside']='0'*64;(root/'package.json').write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'unsafe package'):d.load_package(root)
    def test_unsealed_source_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p,m=self.fixture(root);m['mounts'][0]['source']='missing';(root/'package.json').write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'unsealed'):d.load_package(root)
    def test_duplicate_target_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p,m=self.fixture(root);m['mounts']*=2;(root/'package.json').write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'duplicate'):d.load_package(root)


    def transaction(self):
        x=d.Deployment.__new__(d.Deployment)
        x.board=SimpleNamespace(boot='boot1')
        x.d=self.state();x.d.update({'status':'activating','before':{'/system/bin/appspawn-x':'old'}})
        x.top_mounts=Mock(return_value=self.tops());x.stop=Mock();x.shell=Mock()
        x.hashes=Mock(return_value=x.d['before']);x.start=Mock(return_value=55);x.record=Mock()
        return x
    def test_recover_mount_completed_before_status_marker_lost(self):
        x=self.transaction();x.d['pending_mount']=x.d['mounted'].pop();x.d['pending_previous_root']=None
        x.rollback()
        self.assertEqual(x.d['status'],'rolled_back');self.assertEqual(x.d['mounted'],[])
        self.assertEqual(x.shell.call_args_list[0].args[0],'umount /system/android/lib64/libsigchain.so')
        x.start.assert_called_once_with('old')
    def test_pending_mount_not_executed_restores_only_completed_mounts(self):
        x=self.transaction();x.d['pending_mount']=x.d['mounted'].pop();x.d['pending_previous_root']=None
        x.top_mounts.return_value.pop('/system/android/lib64/libsigchain.so')
        x.rollback();x.shell.assert_called_once_with('umount /system/android')
    def test_failed_rollback_hash_never_reports_success(self):
        x=self.transaction();x.hashes.return_value={'/system/bin/appspawn-x':'wrong'}
        with self.assertRaisesRegex(RuntimeError,'rollback SHA'):x.rollback()
        self.assertNotEqual(x.d['status'],'rolled_back');x.start.assert_not_called()
    def test_repeated_deployment_verifies_without_new_mounts(self):
        with tempfile.TemporaryDirectory() as t:
            x=self.transaction();x.package=Path(t);(x.package/'package.json').write_text('{}')
            x.d.update({'status':'active_verified','package_sha256':d.sha(x.package/'package.json')})
            x.verify=Mock();x.deploy();x.verify.assert_called_once();x.shell.assert_not_called()

if __name__=='__main__':unittest.main()
