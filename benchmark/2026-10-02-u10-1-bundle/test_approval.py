import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('u101_prepare', Path(__file__).with_name('prepare.py'))
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class ApprovalPair(unittest.TestCase):
    def fixture(self, td):
        root = Path(td) / 'bundle'
        (root / 'native').mkdir(parents=True)
        prepare.save(root / 'native/package.json', {'files': {}})
        prepare.save(root / 'bundle.json', {'rollout_ready': False})
        composition = Path(td) / 'composition.json'
        prepare.save(composition, {'bundle_sha256': prepare.sha(root / 'bundle.json'),
                                  'native_manifest_sha256': prepare.sha(root / 'native/package.json'),
                                  'rollout_ready': False})
        return root, composition

    def test_approval_updates_both_guard_inputs_without_native_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root, composition = self.fixture(td)
            native = (root / 'native/package.json').read_bytes()
            with patch.object(prepare.gb, 'validate', return_value=({}, {}, {})):
                prepare.approve(root, composition)
            c = json.loads(composition.read_text())
            self.assertTrue(c['rollout_ready'])
            self.assertTrue(json.loads((root / 'bundle.json').read_text())['rollout_ready'])
            self.assertEqual(c['bundle_sha256'], prepare.sha(root / 'bundle.json'))
            self.assertEqual((root / 'native/package.json').read_bytes(), native)

    def test_second_write_failure_restores_both_originals(self):
        with tempfile.TemporaryDirectory() as td:
            root, composition = self.fixture(td)
            bundle_before = (root / 'bundle.json').read_bytes()
            composition_before = composition.read_bytes()
            replace = prepare.os.replace
            def fail_second(src, dst):
                if Path(dst) == composition:
                    raise OSError('injected composition write failure')
                return replace(src, dst)
            with patch.object(prepare.gb, 'validate', return_value=({}, {}, {})), patch.object(prepare.os, 'replace', fail_second):
                with self.assertRaises(OSError):
                    prepare.approve(root, composition)
            self.assertEqual((root / 'bundle.json').read_bytes(), bundle_before)
            self.assertEqual(composition.read_bytes(), composition_before)

    def test_native_review_rebinds_policy_bundle_and_composition_atomically(self):
        for injected in [False, True]:
            with tempfile.TemporaryDirectory() as td:
                root, composition = self.fixture(td)
                policy = root / 'policy.json'; prepare.save(policy, {'native': {}})
                bundle = json.loads((root / 'bundle.json').read_text())
                bundle['static_checks'] = {'policy': {'source': 'policy.json', 'sha256': prepare.sha(policy)}}
                prepare.save(root / 'bundle.json', bundle)
                c = json.loads(composition.read_text()); c['bundle_sha256'] = prepare.sha(root / 'bundle.json'); prepare.save(composition, c)
                originals = [p.read_bytes() for p in [policy, root / 'bundle.json', composition]]
                review = {'candidate_sha256': 'a'*64, 'deployed_sha256': 'b'*64, 'delta_sha256': 'c'*64,
                    'approved_by': 'outer(claude)', 'evidence': ['board exact approval']}
                replace = prepare.os.replace
                def fail_last(src, dst):
                    if injected and Path(dst) == composition: raise OSError('injected final write failure')
                    return replace(src, dst)
                with patch.object(prepare.gb, 'validate', return_value=({}, {}, {'/system/bin/appspawn-x': 'a'*64})), patch.object(prepare.os, 'replace', fail_last):
                    if injected:
                        with self.assertRaises(OSError): prepare.approve(root, composition, native_reviews={'/system/bin/appspawn-x': review})
                        self.assertEqual(originals, [p.read_bytes() for p in [policy, root / 'bundle.json', composition]])
                    else:
                        prepare.approve(root, composition, native_reviews={'/system/bin/appspawn-x': review})
                        self.assertEqual(json.loads(policy.read_text())['native']['/system/bin/appspawn-x'], review)
                        self.assertEqual(json.loads((root / 'bundle.json').read_text())['static_checks']['policy']['sha256'], prepare.sha(policy))
                        self.assertEqual(json.loads(composition.read_text())['bundle_sha256'], prepare.sha(root / 'bundle.json'))


if __name__ == '__main__':
    unittest.main()
