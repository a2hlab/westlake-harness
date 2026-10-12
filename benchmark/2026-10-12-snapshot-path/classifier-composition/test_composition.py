#!/usr/bin/env python3
"""Actual 24-member composition replay; old classifier is a mechanical fixture only."""
from pathlib import Path
import importlib.util,json,tempfile,unittest

D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('combined',D/'compose.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
WORKSPACES=D.parents[2].parent
ROOT=WORKSPACES/'westlake-harness/benchmark/2026-10-12-v1-seal-execution'

class CompositionTests(unittest.TestCase):
    def inputs(self):
        return [ROOT/'r3-package',ROOT/'inputs/capture-base-plan.json',
                '5d9e0b1045c0e200c6f41e42d61bf5219bbe08fa4289055e23b3a73b8fa2a190',
                ROOT/'inputs/capture-worker-preimage.json',
                '7747341e23e9f5d8077f07f6458dd29b02f3d6ac36cefee6e30a00153f583317']
    def test_real_base_preserves_scope_and_startup(self):
        old=ROOT/'r3-package/payload/screen-gate-feed'
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'disabled-fixture'
            result=m.compose(*self.inputs(),old,m.sha(old),out)
            self.assertFalse(result['execution_enabled']);self.assertEqual(result['members'],24)
            before=json.loads((ROOT/'inputs/capture-base-plan.json').read_text())
            after=json.loads((out/'plan.disabled.json').read_text())
            self.assertEqual([x['target'] for x in before['members']],[x['target'] for x in after['members']])
            for a,b in zip(before['members'],after['members']):
                self.assertEqual(a['after'],b['after']);self.assertEqual(a['before'],b['before'])
                self.assertEqual(b['sha256'],m.sha(out/b['source'].removeprefix('$PACKAGE/')))
            base_policy=(ROOT/'r3-package/payload/startup.env').read_text().splitlines()
            policy=(out/'payload/startup.env').read_text().splitlines()
            keep=lambda lines:[x for x in lines if not x.startswith(('STARTUP_MEMBERS_SHA=','STARTUP_DECODER_SHA='))]
            self.assertEqual(keep(base_policy),keep(policy))
            self.assertEqual((out/'payload/watchdog.sh').read_bytes(),(D.parent/'candidate/watchdog.sh').read_bytes())
            self.assertEqual((out/'payload/screen-gate-feed').read_bytes(),old.read_bytes())
            self.assertIn(m.sha(out/'payload/members.tsv'),(out/'payload/startup.env').read_text())
            self.assertEqual((out/'payload/startup.expected.sha256').read_text().strip(),m.sha(out/'payload/startup.env'))
            self.assertEqual((out/'executor.py').read_bytes(),(ROOT/'r3-package/executor.py').read_bytes())
    def test_wrong_classifier_pin_refused_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'never-created'
            with self.assertRaises(ValueError):m.compose(*self.inputs(),ROOT/'r3-package/payload/screen-gate-feed','0'*64,out)
            self.assertFalse(out.exists())
    def test_non_arm_artifact_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bad=root/'not-arm';bad.write_bytes(b'not an ARM artifact')
            with self.assertRaises(ValueError):m.compose(*self.inputs(),bad,m.sha(bad),root/'never-created')
            self.assertFalse((root/'never-created').exists())

if __name__=='__main__':unittest.main(verbosity=2)
