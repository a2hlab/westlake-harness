"""Offline acceptance checks; proposed exceptions cannot authorize deployment."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import generation_bundle as bundle
import u7_executor as executor
import native_predeploy
from native_gate_common import apply_exceptions

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda name: json.loads((HERE / name).read_text())
NATIVE = REPO.parent / read('package.json')['package']
BUNDLE = REPO.parent / read('bundle-plan.json')['package']
READER = os.environ.get('NATIVE_READELF', '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin/llvm-readelf')


class IdentityTests(unittest.TestCase):
    def test_child_recipe_reproduces_deployed_bytes_and_candidate(self):
        expected = read('evidence/u7-complete-expected.json')['runtime_files']
        inputs, receipt = read('child-inputs.json'), read('child-build-receipt.json')
        self.assertEqual(inputs['child_baseline'], expected['/system/lib64/appspawn/libwestlake_android_child.z.so'])
        self.assertEqual(receipt['baseline']['sha256'], inputs['child_baseline'])
        self.assertEqual(receipt['candidate']['sha256'], receipt['repeat']['sha256'])
        changed = {k for k,v in receipt['baseline']['objects'].items() if receipt['candidate']['objects'][k] != v}
        self.assertEqual(changed, {'sealed_child_provider_loader.o'})
        manifest = json.loads((NATIVE / 'package.json').read_text())
        self.assertEqual(manifest['files']['payload/runtime/libwestlake_android_child.z.so'], receipt['candidate']['sha256'])

    def test_abort_abi_and_retained_text(self):
        self.assertTrue(read('bionic-section-audit.json')['text_unchanged'])
        receipt = read('bionic-link-receipt.json')
        self.assertEqual(receipt['runs']['1']['sha256'], receipt['runs']['2']['sha256'])
        library = NATIVE / 'payload/android/lib64/libbionic_compat.so'
        self.assertEqual(sha(library), receipt['runs']['1']['sha256'])
        symbols = subprocess.check_output([READER, '-Ws', str(library)], text=True)
        self.assertIn('android_set_abort_message@@LIBC', symbols)
        consumer = read('consumer-audit.json')['fd-meet']
        self.assertTrue(any('android_set_abort_message@LIBC' in x for x in consumer['matching_undefined']))


class PackageTests(unittest.TestCase):
    def test_batch_preserves_u7_java_images_and_art(self):
        plan = executor.prepare(BUNDLE, REPO.parent / 'westlake-generation-n4-order-216b68fb')
        recorded = read('bundle-plan.json')
        self.assertEqual(len(plan['expected']), 314)
        self.assertEqual(executor.fingerprints(plan['baseline'], plan['reference_paths']), recorded['baseline_fingerprints'])
        self.assertEqual(executor.fingerprints(plan['expected'], plan['reference_paths']), recorded['target_fingerprints'])
        baseline = read('evidence/u7-complete-expected.json')['runtime_files']
        for path in baseline:
            if '/framework/' in path or path.endswith(('/libart.so', '/liboh_adapter_bridge.so', '/liboh_android_runtime.so', '/libwestlake_android_runtime_provider.so')):
                self.assertEqual(plan['expected'][path], baseline[path], path)
        self.assertNotIn('/system/android/lib64/libz.so', plan['expected'])
        self.assertIn('/system/android/lib64/westlake_native/libz.so', plan['expected'])
        self.assertEqual(plan['build_receipt']['status'], 'verified-with-exception')
        # outer approved the 185 bound exceptions (master c9036596a, board ACK(95) 10:24:37)
        self.assertTrue(plan['rollout_ready'])

    def test_inapplicable_donors_are_not_mislabeled_repairs(self):
        decisions = {s['id']:s for s in read('donor-decisions.json')['slots']}
        self.assertTrue(decisions['bitmap-color-space']['n10_decision'].startswith('excluded'))
        self.assertTrue(decisions['unity-mediandk']['n10_decision'].startswith('excluded'))
        imports = read('consumer-audit.json')['subwaysurfers']['matching_undefined']
        self.assertTrue(any('GLOBAL' in s and 'AMediaCodec_' in s for s in imports))
        self.assertEqual(read('bitvector-assessment.json')['status'], 'excluded-libart-boundary')


class GateTests(unittest.TestCase):
    def test_production_gate_passes_only_through_the_approved_bound_exceptions(self):
        # before outer approval this was REJECT with N1 31 / N2 154 rejected and 0 excepted; the outer loop
        # approved exactly those 185 findings for this manifest (master c9036596a, board ACK(95) 10:24:37)
        report = native_predeploy.check_package(NATIVE, NATIVE/'native-checks/native-gates.json', readelf=READER)
        self.assertFalse(report['errors'])
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['package_manifest_sha256'], read('package.json')['manifest_sha256'])
        self.assertEqual({g:r['rejected'] for g,r in report['gates'].items()}, {'N1':0, 'N2':0})
        self.assertEqual({g:r['excepted'] for g,r in report['gates'].items()}, {'N1':31, 'N2':154})
        self.assertFalse(report['device_access'])

    def test_proposal_is_not_approval_and_binds_every_finding(self):
        proposal = read('exception-proposal.json')
        self.assertEqual(proposal['status'], 'proposal-not-authorized')
        report = read('native-gate.json')
        observed = {(g,x['issue_id']) for g,r in report['gates'].items() for x in r['findings']}
        self.assertEqual(observed, {(x['gate'],x['issue_id']) for x in proposal['exceptions']})
        for row in proposal['exceptions']:
            self.assertEqual(row['package_manifest_sha256'], sha(NATIVE/'package.json'))
            self.assertEqual(row['inputs_sha256'], report['inputs_sha256'])
            self.assertNotIn('approved_by', row)
        with self.assertRaisesRegex(ValueError, 'approved_by'):
            apply_exceptions('N1', [], sha(NATIVE/'package.json'), report['inputs_sha256'], proposal)


if __name__ == '__main__':
    unittest.main()
