import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import prepare_sources as p
import cli_preview

class Tests(unittest.TestCase):
    def test_static_complete_with_three_real_dynamic_unknowns(self):
        with tempfile.TemporaryDirectory(dir=p.HERE/'tmp') as td:
            out=Path(td)/'prepared'
            with patch('subprocess.run',side_effect=AssertionError('NO DEVICE/PROCESS IN MAP')):
                result=p.build(out)
            self.assertEqual((result['source_files'],result['packages'],result['unique_objects']),(824,130,954))
            self.assertEqual(result['static_gaps'],[])
            self.assertEqual({Path(r['target']).name for r in result['unknown']},{'run.sh','worker.sh','binds.tsv'})
            mapping=p.read(out/'source-files.pending.json')
            self.assertEqual((len(mapping),sum(x is None for x in mapping.values())),(824,3))
            self.assertFalse(result['execution_enabled']);self.assertEqual(result['device_calls'],0)
            request=p.read(out/'realization.request.pending.json')
            self.assertIsNone(request['user_approval']);self.assertIsNone(request['parameters']['boot_id'])
            self.assertIsNone(request['parameters']['window_id']);self.assertIsNone(request['parameter_evidence'])
            self.assertNotIn('/data/app/el1/bundle/public/com.Unity3d.BoatAttackDay/android/base.apk',mapping)

    def test_missing_original_member_or_drifted_pin_refuses(self):
        with tempfile.TemporaryDirectory(dir=p.HERE/'tmp') as td:
            root=Path(td)
            with patch.object(p,'MAP_SHA','0'*64):
                with self.assertRaisesRegex(ValueError,'source map/seal pins'):p.build(root/'badsha')
            self.assertFalse((root/'badsha').exists())
            original=p.read
            def broken(path):
                doc=original(path)
                if Path(path)==p.V1/'source-files.json':doc.pop(next(iter(doc)))
                return doc
            with patch.object(p,'read',side_effect=broken):
                with self.assertRaisesRegex(ValueError,'original811'):p.build(root/'missing')
            self.assertFalse((root/'missing').exists())

    def test_original_cli_full954_fixture_and_pending_refusal(self):
        with tempfile.TemporaryDirectory(dir=p.HERE/'tmp') as td:
            root=Path(td);p.build(root/'prepared')
            result=cli_preview.build(root/'prepared',root/'cli')
            self.assertEqual({k:v['return_code'] for k,v in result['reports'].items()},
                dict(build_seal_fixture=0,realization_fixture=0,build_seal_pending=2,realization_pending=2))
            self.assertEqual((result['source_files'],result['packages'],result['total_objects']),(824,130,954))
            self.assertTrue(result['synthetic']);self.assertFalse(result['actual_runtime_pass'])
            self.assertIsNone(result['actual_newboot']);self.assertIsNone(result['signature'])
            for name in ('MUST_NOT_EXIST.seal.json','MUST_NOT_EXIST.realization'):
                self.assertFalse((root/'cli'/name).exists())

if __name__=='__main__':
    (p.HERE/'tmp').mkdir(exist_ok=True)
    unittest.main(verbosity=2)
