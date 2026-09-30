"""Frozen policy must refuse before dispatch or board mutation."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import deploy_generation as d
import check_frozen

class FrozenDeployTests(unittest.TestCase):
    def test_real_registry_rejects_changed_installer(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)
            (package/'package.json').write_text(json.dumps({'live_hashes':{
                '/system/lib64/libbms.z.so':'0'*64}}))
            with self.assertRaisesRegex(RuntimeError,'frozen API package'):
                d.check_frozen_package(package)

    def test_unrelated_package_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            package=Path(tmp)
            (package/'package.json').write_text(json.dumps({'live_hashes':{
                '/system/android/lib64/liboh_android_runtime.so':'0'*64}}))
            d.check_frozen_package(package)

    def test_gate_runs_before_dry_run_or_dispatch(self):
        for flags in [[],['--dry-run'],['--upgrade'],['--rollback'],
                      ['--replace','/system/bin/appspawn-x'],
                      ['--add','/system/android/lib64/libnew.so']]:
            with self.subTest(flags=flags), patch.object(d,'load_package',return_value={}), \
                 patch.object(d,'check_frozen_package',side_effect=RuntimeError('blocked')) as gate, \
                 patch.object(d.subprocess,'call') as dispatch, \
                 patch.object(d,'Deployment') as board:
                with self.assertRaisesRegex(RuntimeError,'blocked'):
                    d.main(['61b0657200000000000000000324012c','/tmp/package',*flags])
                gate.assert_called_once()
                dispatch.assert_not_called()
                board.assert_not_called()

    def test_raw_rollback_hash_and_absence_are_refused(self):
        path='/system/lib64/libbms.z.so'
        for hashes, absent in [({path:'0'*64},[]),({},[path])]:
            with self.assertRaisesRegex(RuntimeError,'rollback'):
                d.check_frozen_restore(hashes,absent)

    def test_matching_rollback_is_allowed(self):
        entries=check_frozen.load(Path(d.__file__).resolve().parents[2]/'knowledge/frozen/frozen.json')
        hashes={a['path']:a['sha256'] for e in entries for a in e.get('artifacts',[])}
        d.check_frozen_restore(hashes)

    def test_single_rollback_checks_before_stop(self):
        deploy=d.Deployment.__new__(d.Deployment)
        deploy.d={'single_replacements':[{'target':'/system/lib64/libx.so',
          'remote':'/data/test/x','previous_root':'/old','previous_package':'/tmp/old'}]}
        with patch.object(deploy,'top_mounts',return_value={'/system/lib64/libx.so':'/test/x'}), \
             patch.object(d,'load_package',return_value={}), \
             patch.object(d,'check_frozen_package',side_effect=RuntimeError('blocked')), \
             patch.object(deploy,'stop') as stop:
            with self.assertRaisesRegex(RuntimeError,'blocked'): deploy.rollback_single()
            stop.assert_not_called()

if __name__=='__main__':unittest.main()
