"""T8 paired images/BCP admission and exact U9 rollback, without device access."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/lab'))
import generation_bundle as b
import u7_executor as u


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


fmt = load('t8_format_fixture', ROOT / 'benchmark/2026-10-01-u7-executor/test_format.py')
tx_tests = load('t8_transaction_fixture', ROOT / 'benchmark/2026-10-01-u7-executor/test_executor.py')


class ImageTests(unittest.TestCase):
    def setUp(self):
        self.f = fmt.Bundle('test_complete_group_and_rollback')
        self.f.setUp()
        self.addCleanup(self.f.tearDown)
        self.root, self.d = self.f.root, self.f.d
        manifest = json.loads((self.root/'native/package.json').read_text())
        manifest['prerequisites']={}
        for j in b.JARS+['oh-adapter-runtime']:
            rel = 'payload/android/framework/' + j + '.jar'
            p = self.root/'native'/rel
            p.parent.mkdir(parents=True, exist_ok=True)
            # Underlay is deliberately different from the effective baseline and candidate.
            p.write_bytes(('underlay:'+j).encode())
            manifest['files'][rel] = b.sha(p)
        p = self.root/'native/package.json'
        p.write_text(json.dumps(manifest))
        self.d['native']['manifest']['sha256'] = b.sha(p)
        framework = self.root/'members/oh-adapter-framework.jar'
        framework.write_bytes(b'new-framework')
        self.d['boot_group']['members'].append(dict(source='members/'+framework.name,
            target=b.FW+framework.name, sha256=b.sha(framework)))
        references = []
        for target in sorted(b.IMAGE_TARGETS|b.BCP_TARGETS):
            p = self.root/'baseline'/Path(target).name
            p.parent.mkdir(exist_ok=True)
            # For unchanged jars the effective baseline matches the candidate underlay.
            payload = ('underlay:'+p.stem).encode() if target in b.BCP_TARGETS else b'U9-image'
            if p.name in ('adapter-mainline-stubs.jar','oh-adapter-framework.jar'):
                payload = ('effective-U9:'+p.name).encode()
            p.write_bytes(payload)
            references.append(dict(source=str(p.relative_to(self.root)), target=target, sha256=b.sha(p)))
        self.d['image_gate_reference'] = dict(members=references)
        p = self.root/self.d['reference']['boot']['source']
        p.write_text(''.join(r['sha256']+'  '+r['target']+'\n' for r in references))
        self.d['reference']['boot']['sha256'] = b.sha(p)
        self.f.write()

    def test_two_jar_group_and_effective_reference(self):
        data, manifest, expected = b.validate(self.root)
        self.assertEqual(len(data['boot_group']['members']), 29)
        bcps = b.bcp_members(self.root, data, manifest)
        self.assertEqual(bcps['oh-adapter-framework'].read_bytes(), b'new-framework')
        self.assertEqual(expected[b.FW+'oh-adapter-framework.jar'], b.sha(bcps['oh-adapter-framework']))

    def test_prepare_stages_all_29_new_members_and_keeps_u9_images(self):
        _,manifest,_=b.validate(self.root)
        with patch.object(u.native,'load_package',return_value=manifest):
            plan=u.prepare(self.root,self.root/'native')
        targets=b.IMAGE_TARGETS|{b.FW+'adapter-mainline-stubs.jar',b.FW+'oh-adapter-framework.jar'}
        changed={r['target']:r for r in plan['changes']}
        self.assertTrue(targets<=changed.keys())
        for target in targets:
            self.assertEqual(plan['expected'][target],changed[target]['sha256'])
            self.assertNotEqual(plan['baseline'][target],plan['expected'][target])
        self.assertEqual(plan['baseline'][b.FW+'arm64/boot.art'],b.sha(self.root/'baseline/boot.art'))

    def test_reference_must_match_baseline_and_be_complete(self):
        for kind in ('tampered', 'missing', 'wrong-baseline'):
            with self.subTest(kind=kind):
                original = json.loads(json.dumps(self.d))
                row = self.d['image_gate_reference']['members'][0]
                p = self.root/row['source']
                old = p.read_bytes()
                if kind == 'tampered': p.write_bytes(b'wrong')
                elif kind == 'missing': self.d['image_gate_reference']['members'].pop()
                else: row['sha256'] = 'f'*64
                self.f.write()
                with self.assertRaises(ValueError): b.validate(self.root)
                p.write_bytes(old)
                self.d.clear(); self.d.update(original)
        self.f.write()

    def test_framework_cannot_swap_without_reference(self):
        self.d.pop('image_gate_reference'); self.f.write()
        with self.assertRaisesRegex(ValueError,'effective image reference'): b.validate(self.root)

    def test_gates_read_new_images_both_new_jars_and_effective_u9(self):
        calls = []
        def g1(image, reference, swaps):
            self.assertEqual((image/'arm64/boot.art').read_bytes(), b'x')
            self.assertEqual((reference/'arm64/boot.art').read_bytes(), b'U9-image')
            self.assertEqual((reference/'adapter-mainline-stubs.jar').read_bytes(), b'effective-U9:adapter-mainline-stubs.jar')
            self.assertEqual(set(swaps), {'adapter-mainline-stubs','oh-adapter-framework'})
            calls.append('G1'); return True
        def g2(image, reference, tool, old_bcp, new_bcp, *args):
            self.assertEqual((Path(new_bcp)/'oh-adapter-framework.jar').read_bytes(), b'new-framework')
            self.assertEqual((Path(new_bcp)/'adapter-mainline-stubs.jar').read_bytes(), b'x')
            self.assertEqual(Path(old_bcp), reference)
            calls.append('G2'); return True
        loader = SimpleNamespace(create_module=lambda spec: None,
            exec_module=lambda m: (setattr(m,'gate_g1',g1),setattr(m,'gate_g2',g2)))
        # Keep importlib's real module construction while replacing only the trusted checker loader.
        spec = importlib.util.spec_from_loader('fixture_gate', loader)
        with patch.object(b.importlib.util,'spec_from_file_location', return_value=spec):
            report = b.image_checks(self.root, 'oatdump')
        self.assertTrue(report['G1'] and report['G2'])
        self.assertEqual(calls, ['G1','G2'])
        self.assertEqual(report['reference_kind'],'effective-baseline')

    def test_receipt_binds_framework_overlay_not_native_underlay(self):
        _, manifest, _ = b.validate(self.root)
        inputs = {j+'.jar': b.sha(p) for j,p in b.bcp_members(self.root,self.d,manifest).items()}
        receipt = dict(status='unknown',input_jars=inputs,
            outputs={Path(r['target']).name:r['sha256'] for r in self.d['boot_group']['members'] if r['target'] in b.IMAGE_TARGETS})
        p = self.root/'receipt.json';p.write_text(json.dumps(receipt))
        self.d['paired_build_receipt']=dict(source=p.name,sha256=b.sha(p))
        self.assertEqual(u.receipt_check(self.root,self.d,manifest)['status'],'unknown')
        receipt['input_jars']['oh-adapter-framework.jar']=b.sha(self.root/'native/payload/android/framework/oh-adapter-framework.jar')
        p.write_text(json.dumps(receipt));self.d['paired_build_receipt']['sha256']=b.sha(p)
        with self.assertRaisesRegex(ValueError,'input_jars'):u.receipt_check(self.root,self.d,manifest)


class PairedRollbackTests(unittest.TestCase):
    def plan(self):
        p = tx_tests.fixture()
        framework = b.FW+'oh-adapter-framework.jar'
        p['baseline'][framework]='4'*64;p['expected'][framework]='5'*64
        p['changes'].append(dict(source='framework',target=framework,sha256='5'*64))
        return p

    def test_entire_t8_success_then_exact_u9_restore(self):
        p=self.plan();io=tx_tests.Fake(p)
        with tempfile.TemporaryDirectory() as td:
            tx=u.Transaction(io,Path(td)/'j',p);tx.apply()
            for target in b.IMAGE_TARGETS|{b.FW+'adapter-mainline-stubs.jar',b.FW+'oh-adapter-framework.jar'}:
                self.assertEqual(io.values[target],p['expected'][target])
            self.assertEqual(io.log.count('stop'),1)
            tx.rollback();self.assertEqual(io.values,p['baseline']);self.assertEqual(io.stack,io.original)

    def test_loss_at_every_image_or_jar_boundary_restores_u9(self):
        p=self.plan()
        for n,row in enumerate(p['changes'],1):
            if row['target'] not in b.IMAGE_TARGETS|{b.FW+'adapter-mainline-stubs.jar',b.FW+'oh-adapter-framework.jar'}:continue
            for when in ('before','after'):
                with self.subTest(target=row['target'],when=when),tempfile.TemporaryDirectory() as td:
                    io=tx_tests.Fake(p);io.fail=(when,n);tx=u.Transaction(io,Path(td)/'j',p)
                    with self.assertRaises(RuntimeError):tx.apply()
                    self.assertEqual(io.values,p['baseline']);self.assertEqual(io.stack,io.original)
                    self.assertEqual(tx.state['status'],'rolled_back')


if __name__=='__main__':unittest.main()
